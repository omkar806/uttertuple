import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from common.logger import logger, tracer
from database.manager import Base, DatabaseServiceManager
from exceptions.db import DBException, RecordExistsException, RecordNotFoundException
from exceptions.user import InactiveUser
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    inspect,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from user.models.interface import User as UserInterface
from user.models.interface import UserCreate
from user.models.request import UserUpdateRequest


class Role(Base):
    """Represents the role model."""

    __tablename__ = "roles"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), unique=True)
    description = Column(String(2000), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    users = relationship("User", back_populates="role")

    def object_as_dict(obj):
        return {c.key: getattr(obj, c.key) for c in inspect(obj).mapper.column_attrs}


class User(Base):
    """Represents the user model."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(2000), unique=True)
    full_name = Column(String(500), nullable=True)
    hashed_password = Column(String(2000))
    is_active = Column(Boolean, default=True)
    is_email_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    meta_data = Column(JSON, nullable=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)

    role = relationship("Role", back_populates="users")
    audit_logs = relationship("AuditLog", back_populates="users")

    def object_as_dict(obj):
        return {c.key: getattr(obj, c.key) for c in inspect(obj).mapper.column_attrs}


class EmailVerificationToken(Base):
    """Represents email verification tokens for user registration."""

    __tablename__ = "email_verification_tokens"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String(255), unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    user = relationship("User")

    def object_as_dict(obj):
        return {c.key: getattr(obj, c.key) for c in inspect(obj).mapper.column_attrs}


class PasswordResetToken(Base):
    """Represents password reset tokens."""

    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String(255), unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    user = relationship("User")

    def object_as_dict(obj):
        return {c.key: getattr(obj, c.key) for c in inspect(obj).mapper.column_attrs}


class UserInvitation(Base):
    """Represents user invitations."""

    __tablename__ = "user_invitations"

    id = Column(Integer, primary_key=True)
    email = Column(String(2000), nullable=False)
    token = Column(String(255), unique=True, nullable=False)
    invited_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_accepted = Column(Boolean, default=False)
    accepted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    invited_by = relationship("User", foreign_keys=[invited_by_user_id])
    role = relationship("Role")

    def object_as_dict(obj):
        return {c.key: getattr(obj, c.key) for c in inspect(obj).mapper.column_attrs}


class UserModelService:
    def __init__(self, database_service_manager: DatabaseServiceManager):
        super().__init__()
        self.database_manager = database_service_manager
        self.current_db = self.database_manager.postgres_db_service()
        self.current_db_engine = self.current_db.engine

    def get_user(self, email: str = None) -> UserInterface:
        """
        Retrieves a user from the database based on the username.

        Args:
            db (Session): The database session.
            username (str, optional): The username of the user to retrieve.

        Returns:
            User: The user object if found, otherwise None.
        """
        try:
            with tracer.start_as_current_span(f"UserServiceManager.get_user.{email}"):
                with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
                    db_user = db.query(User).filter(User.email == email).first()

                    if db_user:
                        role_id = db_user.role_id
                        role_name = db_user.role.name if db_user.role else None

                        user = UserInterface(
                            id=db_user.id,
                            email=db_user.email,
                            full_name=db_user.full_name,
                            hashed_password=db_user.hashed_password,
                            is_active=db_user.is_active,
                            is_email_verified=db_user.is_email_verified,
                            created_at=db_user.created_at,
                            updated_at=db_user.updated_at,
                            role=role_name,
                            role_id=role_id,
                        )
                        return user
                    raise RecordNotFoundException("User not found")
        except DBException as e:
            raise DBException(f"Could not get user due to {e}")

    def get_users(
        self,
        user_id: int = None,
        email: str = None,
        username: str = None,
        is_active: bool = None,
        created_after: datetime = None,
        created_before: datetime = None,
        updated_after: datetime = None,
        updated_before: datetime = None,
        sort_by: str = "id",
        sort_order: str = "asc",
        page: int = 1,
        page_size: int = 10,
    ) -> dict[str, Any]:
        """Get a paginated list of users.

        Args:
            user_id (int, optional): The ID of the user to retrieve. Defaults to None.
            email (str, optional): The email of the user to retrieve. Defaults to None.
            username (str, optional): The username of the user to retrieve. Defaults to None.
            is_active (bool, optional): Whether to retrieve active users only. Defaults to None.
            created_after (datetime, optional): Only retrieve users created after this date. Defaults to None.
            created_before (datetime, optional): Only retrieve users created before this date. Defaults to None.
            updated_after (datetime, optional): Only retrieve users updated after this date. Defaults to None.
            updated_before (datetime, optional): Only retrieve users updated before this date. Defaults to None.
            sort_by (str, optional): The field to sort by. Defaults to "id".
            sort_order (str, optional): The sort order, either "asc" or "desc". Defaults to "asc".
            page (int, optional): The page number to retrieve. Defaults to 1.
            page_size (int, optional): The number of users per page. Defaults to 10.

        Raises:
            RecordNotFoundException: If no users match the criteria.
            DBException: If there is a database error.

        Returns:
            dict: A paginated list of users.
        """
        try:
            with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
                query = db.query(User)

                # Filtering
                if user_id is not None:
                    query = query.filter(User.id == user_id)
                if email is not None:
                    query = query.filter(User.email.ilike(f"%{email}%"))
                if is_active is not None:
                    query = query.filter(User.is_active == is_active)
                if created_after is not None:
                    query = query.filter(User.created_at >= created_after)
                if created_before is not None:
                    query = query.filter(User.created_at <= created_before)
                if updated_after is not None:
                    query = query.filter(User.updated_at >= updated_after)
                if updated_before is not None:
                    query = query.filter(User.updated_at <= updated_before)

                # Get total count before pagination
                total_count = query.count()

                # Sorting
                valid_sort_columns = ["id", "email", "is_active", "created_at", "updated_at"]
                if sort_by not in valid_sort_columns:
                    sort_by = "created_at"

                sort_column = getattr(User, sort_by)
                if sort_order.lower() == "desc":
                    query = query.order_by(sort_column.desc())
                else:
                    query = query.order_by(sort_column.asc())

                # Pagination
                offset = (page - 1) * page_size
                db_users = query.offset(offset).limit(page_size).all()

                # Calculate pagination metadata
                total_pages = (total_count + page_size - 1) // page_size
                has_next = page < total_pages
                has_prev = page > 1

                pagination_metadata = {"current_page": page, "page_size": page_size, "total_count": total_count, "total_pages": total_pages, "has_next": has_next, "has_prev": has_prev}

                if db_users:
                    return {
                        "users": [
                            UserInterface(
                                id=user.id,
                                email=user.email,
                                full_name=user.full_name,
                                hashed_password=user.hashed_password,
                                is_active=user.is_active,
                                is_email_verified=user.is_email_verified,
                                created_at=user.created_at,
                                updated_at=user.updated_at,
                                role=user.role.name if user.role else None,
                                role_id=user.role_id,
                            )
                            for user in db_users
                        ],
                        "pagination": pagination_metadata,
                    }
                raise RecordNotFoundException("No users found")
        except DBException as e:
            raise DBException(f"Could not get users due to {str(e)}")

    def get_active_user(self, email: str = None) -> User | None:
        """
        Retrieves a user from the database based on the email.

        Args:
            db (Session): The database session.
            email (str, optional): The email of the user to retrieve.

        Returns:
            User: The user object if found, otherwise None.
        """
        try:
            with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
                db_user = db.query(User).filter(User.email == email, User.is_active == True).first()  # noqa: E712
                return db_user
            raise RecordNotFoundException("Active user not found")
        except DBException as e:
            raise DBException(f"Could not get active user due to {e}")

    def get_user_by_email(self, email: str = None) -> User | None:
        """
        Retrieves a user from the database based on the username.

        Args:
            db (Session): The database session.
            username (str, optional): The username of the user to retrieve.

        Returns:
            User: The user object if found, otherwise None.
        """
        try:
            with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
                db_user = db.query(User).filter(User.email == email).first()
                return db_user
            raise RecordNotFoundException("User not found")
        except DBException as e:
            raise DBException(f"Could not get user by email due to {e}")

    def create_user(self, user: UserCreate) -> User:
        """Creates a new user in the database.

        Args:
            user (UserCreate): The user creation request.

        Raises:
            RecordExistsException: If a user with the same email already exists.
            DBException: If there is a database error.

        Returns:
            User: The created user.
        """
        try:
            with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
                db_user = User(
                    # email=1, # Uncomment this line to test the simulate db error
                    email=user.email,
                    full_name=user.full_name,
                    hashed_password=user.password,
                    role_id=user.role_id,
                )
                db.add(db_user)
                db.commit()
                db.refresh(db_user)
                return db_user

        except IntegrityError as e:
            raise RecordExistsException(f"User with email {user.email} already exists.")

        except DBException as e:
            raise DBException(f"Could not create user due to {e}")

    def delete_user(self, email: str) -> User:
        """Deletes a user from the database.

        Args:
            email (str): The email of the user to delete.

        Raises:
            InactiveUser: If the user is inactive.
            RecordNotFoundException: If no user was found with the given email.
            DBException: If there is a database error.

        Returns:
            User: The deleted user.
        """
        try:
            with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
                db_user = db.query(User).filter(User.email == email, User.is_active == True).first()

                if not db_user:
                    raise InactiveUser("No user was found with this email.")

                db_user.is_active = False
                db_user.updated_at = datetime.now(UTC)
                db.commit()
                return db_user
            raise RecordNotFoundException("User not found")
        except DBException as e:
            raise DBException(f"Could not delete user due to {str(e)}")

    def activate_user(self, user_email: int) -> User:
        """Activates a user in the database.

        Args:
            user (User): The user to activate.

        Raises:
            RecordNotFoundException: If the user is not found.
            DBException: If there is a database error.

        Returns:
            User: The activated user.
        """
        try:
            with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
                db_user = db.query(User).filter(User.email == user_email).first()

                if db_user:
                    db_user.is_active = True
                    db_user.updated_at = datetime.now(UTC)
                    db.commit()
                    db.refresh(db_user)
                    return db_user

            raise RecordNotFoundException("User not found")
        except DBException as e:
            raise DBException(f"Could not activate user due to {str(e)}")

    def update_user_role(self, user_id: int, role_id: int) -> User:
        """Updates a user's role.

        Args:
            user_id (int): The ID of the user to update.
            role_id (int): The ID of the role to assign.

        Raises:
            RecordNotFoundException: If the user is not found.
            DBException: If there is a database error.

        Returns:
            User: The updated user.
        """
        try:
            with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
                db_user = db.query(User).filter(User.id == user_id).first()
                if db_user:
                    db_user.role_id = role_id
                    db_user.updated_at = datetime.now(UTC)
                    db.commit()
                    db.refresh(db_user)
                    return db_user
                raise RecordNotFoundException("User not found")

        except DBException as e:
            raise DBException(f"Could not update user role due to {str(e)}")

    def get_users_by_role(
        self,
        role_id: int = None,
        role_name: str = None,
        sort_by: str = "id",
        sort_order: str = "asc",
        page: int = 1,
        page_size: int = 10,
    ) -> dict[str, Any]:
        """Retrieves users by role.

        Args:
            role_id (int, optional): The ID of the role to filter by. Defaults to None.
            role_name (str, optional): The name of the role to filter by. Defaults to None.
            sort_by (str, optional): The field to sort by. Defaults to "id".
            sort_order (str, optional): The order to sort by (asc or desc). Defaults to "asc".
            page (int, optional): The page number to retrieve. Defaults to 1.
            page_size (int, optional): The number of items per page. Defaults to 10.

        Raises:
            RecordNotFoundException: If no users are found.
            DBException: If there is a database error.

        Returns:
            dict: A list of users matching the role filter.
        """
        try:
            with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
                query = db.query(User).join(Role, User.role_id == Role.id)

                # Filtering
                if role_id is not None:
                    query = query.filter(User.role_id == role_id)
                if role_name is not None:
                    query = query.filter(Role.name.ilike(f"%{role_name}%"))

                # Get total count before pagination
                total_count = query.count()

                # Sorting
                valid_sort_columns = ["id", "email", "created_at", "updated_at"]
                if sort_by not in valid_sort_columns:
                    sort_by = "created_at"

                sort_column = getattr(User, sort_by)
                if sort_order.lower() == "desc":
                    query = query.order_by(sort_column.desc())
                else:
                    query = query.order_by(sort_column.asc())

                # Pagination
                offset = (page - 1) * page_size
                db_users = query.offset(offset).limit(page_size).all()

                # Calculate pagination metadata
                total_pages = (total_count + page_size - 1) // page_size
                has_next = page < total_pages
                has_prev = page > 1

                pagination_metadata = {"current_page": page, "page_size": page_size, "total_count": total_count, "total_pages": total_pages, "has_next": has_next, "has_prev": has_prev}

                if db_users:
                    return {
                        "users": [
                            UserInterface(
                                id=user.id,
                                email=user.email,
                                full_name=user.full_name,
                                hashed_password=user.hashed_password,
                                is_active=user.is_active,
                                is_email_verified=user.is_email_verified,
                                created_at=user.created_at,
                                updated_at=user.updated_at,
                                role=user.role.name if user.role else None,
                                role_id=user.role_id,
                            )
                            for user in db_users
                        ],
                        "pagination": pagination_metadata,
                    }
                raise RecordNotFoundException("No users found")
        except DBException as e:
            raise DBException(f"Could not get users by role due to {str(e)}")

    def add_role(self, role: str, description: str) -> Role:
        """
        Add a new role to the database.

        Args:
            role (str): The name of the role.
            description (str): The description of the role.

        Raises:
            RecordExistsException: If the role already exists.
            DBException: If there is a database error.

        Returns:
            Role: The created role.
        """
        try:
            with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
                db_role = Role(name=role, description=description)
                db.add(db_role)
                db.commit()
                db.refresh(db_role)
                return db_role

        except IntegrityError as e:
            raise RecordExistsException("Role already exists")

        except DBException as e:
            raise DBException(f"Could not add role due to {str(e)}")

    def delete_role_by_name(self, role_name: str) -> Role:
        """
        Delete a role from the database by its name.

        Args:
            role_name (str): The name of the role to delete.

        Raises:
            RecordNotFoundException: If the role is not found.
            DBException: If there is a database error.

        Returns:
            Role: The deleted role.
        """
        try:
            with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
                db_role = db.query(Role).filter(Role.name == role_name).first()
                if db_role:
                    db.delete(db_role)
                    db.commit()
                    return db_role
                raise RecordNotFoundException("Role not found")
        except DBException as e:
            raise DBException(f"Could not delete role due to {str(e)}")

    def get_roles(
        self,
        role_name: str = None,
        role_id: int = None,
        description: str = None,
        created_after: datetime = None,
        created_before: datetime = None,
        updated_after: datetime = None,
        updated_before: datetime = None,
        sort_by: str = "id",
        sort_order: str = "asc",
        page: int = 1,
        page_size: int = 10,
    ):
        """
        Get roles from the database with optional filtering and pagination.

        Args:
            role_name (str, optional): The name of the role to filter by.
            role_id (int, optional): The ID of the role to filter by.
            description (str, optional): The description to filter by.
            created_after (datetime, optional): Filter by creation date after this date.
            created_before (datetime, optional): Filter by creation date before this date.
            updated_after (datetime, optional): Filter by update date after this date.
            updated_before (datetime, optional): Filter by update date before this date.
            sort_by (str, optional): The field to sort by (default is "id").
            sort_order (str, optional): The sort order ("asc" or "desc", default is "asc").
            page (int, optional): The page number for pagination (default is 1).
            page_size (int, optional): The number of results per page (default is 10).

        Returns:
            List[Role]: A list of roles matching the filters.
        """
        try:
            with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
                query = db.query(Role)

                # Filtering
                if role_id is not None:
                    query = query.filter(Role.id == role_id)
                if role_name is not None:
                    query = query.filter(Role.name.ilike(f"%{role_name}%"))
                if description is not None:
                    query = query.filter(Role.description.ilike(f"%{description}%"))
                if created_after is not None:
                    query = query.filter(Role.created_at >= created_after)
                if created_before is not None:
                    query = query.filter(Role.created_at <= created_before)
                if updated_after is not None:
                    query = query.filter(Role.updated_at >= updated_after)
                if updated_before is not None:
                    query = query.filter(Role.updated_at <= updated_before)

                # Get total count before pagination
                total_count = query.count()

                # Sorting
                valid_sort_columns = ["id", "name", "description", "created_at", "updated_at"]
                if sort_by not in valid_sort_columns:
                    sort_by = "created_at"

                sort_column = getattr(Role, sort_by)
                if sort_order.lower() == "desc":
                    query = query.order_by(sort_column.desc())
                else:
                    query = query.order_by(sort_column.asc())

                # Pagination
                offset = (page - 1) * page_size
                db_roles = query.offset(offset).limit(page_size).all()

                # Calculate pagination metadata
                total_pages = (total_count + page_size - 1) // page_size
                has_next = page < total_pages
                has_prev = page > 1

                pagination_metadata = {"current_page": page, "page_size": page_size, "total_count": total_count, "total_pages": total_pages, "has_next": has_next, "has_prev": has_prev}

                if db_roles:
                    return {"roles": [role.object_as_dict() for role in db_roles], "pagination": pagination_metadata}
                raise RecordNotFoundException("No roles found")
        except DBException as e:
            raise DBException(f"Could not get roles due to {str(e)}")

    def update_user(self, current_email: str, user: UserUpdateRequest) -> User:
        """Update a user's information in the database.

        Args:
            current_email (str): The email of the user to update.
            user (UserUpdateRequest): The updated user information.

        Raises:
            RecordNotFoundException: If the user is not found.
            DBException: If there is a database error.

        Returns:
            UserUpdateRequest: The updated user information.
        """
        try:
            with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
                db_user = db.query(User).filter(User.email == current_email).first()
                if db_user:
                    db_user.email = user.email if user.email else db_user.email
                    db_user.hashed_password = user.password if user.password else db_user.hashed_password
                    db_user.updated_at = datetime.now(UTC)
                    db.commit()
                    db.refresh(db_user)
                    return db_user
                raise RecordNotFoundException("User not found")
        except DBException as e:
            raise DBException(f"Could not update user due to {str(e)}")

    def update_user_by_id(self, user_id: int, user: UserUpdateRequest) -> User:
        """Update a user's information in the database.

        Args:
            user_id (int): The ID of the user to update.
            user (UserUpdateRequest): The updated user information.

        Raises:
            RecordNotFoundException: If the user is not found.
            DBException: If there is a database error.

        Returns:
            UserUpdateRequest: The updated user information.
        """
        try:
            with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
                db_user = db.query(User).filter(User.id == user_id).first()
                if db_user:
                    db_user.hashed_password = user.password if user.password else db_user.hashed_password
                    db_user.updated_at = datetime.now(UTC)
                    db.commit()
                    db.refresh(db_user)
                    return db_user
                raise RecordNotFoundException("User not found")
        except DBException as e:
            raise DBException(f"Could not update user due to {str(e)}")

    def reset_password(self, email: str, hashed_password: str) -> User:
        """
        Reset a user's password in the database.

        Args:
            email (str): The email of the user whose password is to be reset.
            hashed_password (str): The new hashed password.

        Raises:
            RecordNotFoundException: If the user is not found.
            DBException: If there is a database error.

        Returns:
            User: The updated user information.
        """
        try:
            with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
                db_user = db.query(User).filter(User.email == email).first()
                if db_user:
                    db_user.hashed_password = hashed_password
                    db_user.updated_at = datetime.now(UTC)
                    db.commit()
                    db.refresh(db_user)
                    return UserInterface(
                        id=db_user.id,
                        email=db_user.email,
                        full_name=db_user.full_name,
                        hashed_password=db_user.hashed_password,
                        is_active=db_user.is_active,
                        is_email_verified=db_user.is_email_verified,
                        created_at=db_user.created_at,
                        updated_at=db_user.updated_at,
                        role=db_user.role.name if db_user.role else None,
                        role_id=db_user.role_id,
                    )
                raise RecordNotFoundException("User not found")
        except DBException as e:
            raise DBException(f"Could not reset password due to {str(e)}")

    # Email verification methods
    def create_email_verification_token(self, user_id: int) -> str:
        """Create an email verification token for a user."""
        try:
            with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
                # Generate a unique token
                token = secrets.token_urlsafe(32)
                # Token expires in 24 hours
                expires_at = datetime.now(UTC) + timedelta(hours=24)

                verification_token = EmailVerificationToken(user_id=user_id, token=token, expires_at=expires_at)

                db.add(verification_token)
                db.commit()
                return token
        except Exception as e:
            raise DBException(f"Could not create email verification token: {str(e)}")

    def verify_email_token(self, token: str) -> int:
        """Verify an email token and return user_id if valid."""
        try:
            with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
                verification_token = db.query(EmailVerificationToken).filter(EmailVerificationToken.token == token, EmailVerificationToken.is_used == False, EmailVerificationToken.expires_at > datetime.now(UTC)).first()

                if not verification_token:
                    raise RecordNotFoundException("Invalid or expired verification token")

                # Mark token as used
                verification_token.is_used = True

                # Mark user email as verified
                user = db.query(User).filter(User.id == verification_token.user_id).first()
                if user:
                    user.is_email_verified = True
                    user.updated_at = datetime.now(UTC)

                db.commit()
                return verification_token.user_id
        except DBException as e:
            raise e
        except Exception as e:
            raise DBException(f"Could not verify email token: {str(e)}")

    # Password reset methods
    def create_password_reset_token(self, email: str) -> str:
        """Create a password reset token for a user."""
        try:
            with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
                # Find user by email
                user = db.query(User).filter(User.email == email).first()
                if not user:
                    raise RecordNotFoundException("User not found")

                # Generate a unique token
                token = secrets.token_urlsafe(32)
                # Token expires in 1 hour
                expires_at = datetime.now(UTC) + timedelta(hours=1)

                reset_token = PasswordResetToken(user_id=user.id, token=token, expires_at=expires_at)

                db.add(reset_token)
                db.commit()
                return token
        except DBException as e:
            raise e
        except Exception as e:
            raise DBException(f"Could not create password reset token: {str(e)}")

    def verify_password_reset_token(self, token: str) -> int:
        """Verify a password reset token and return user_id if valid."""
        try:
            with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
                reset_token = db.query(PasswordResetToken).filter(PasswordResetToken.token == token, PasswordResetToken.is_used == False, PasswordResetToken.expires_at > datetime.now(UTC)).first()

                if not reset_token:
                    raise RecordNotFoundException("Invalid or expired reset token")

                return reset_token.user_id
        except Exception as e:
            raise DBException(f"Could not verify password reset token: {str(e)}")

    def use_password_reset_token(self, token: str, new_hashed_password: str) -> bool:
        """Use a password reset token to change password."""
        try:
            with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
                reset_token = db.query(PasswordResetToken).filter(PasswordResetToken.token == token, PasswordResetToken.is_used == False, PasswordResetToken.expires_at > datetime.now(UTC)).first()

                if not reset_token:
                    raise RecordNotFoundException("Invalid or expired reset token")

                # Mark token as used
                reset_token.is_used = True

                # Update user password
                user = db.query(User).filter(User.id == reset_token.user_id).first()
                if user:
                    user.hashed_password = new_hashed_password
                    user.updated_at = datetime.now(UTC)

                db.commit()
                return True
        except DBException as e:
            raise e
        except Exception as e:
            raise DBException(f"Could not use password reset token: {str(e)}")

    # User invitation methods
    def create_user_invitation(self, email: str, invited_by_user_id: int, role_id: int) -> str:
        """Create a user invitation."""
        try:
            with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
                # Check if user already exists
                existing_user = db.query(User).filter(User.email == email).first()
                if existing_user:
                    raise RecordExistsException("User already exists")

                # Check if there's already a pending invitation
                existing_invitation = db.query(UserInvitation).filter(UserInvitation.email == email, UserInvitation.is_accepted == False, UserInvitation.expires_at > datetime.now(UTC)).first()

                if existing_invitation and existing_invitation.is_accepted == False and existing_invitation.expires_at > datetime.now():
                    raise RecordExistsException("Pending invitation already exists")

                # Generate a unique token
                token = secrets.token_urlsafe(32)
                # Token expires in 7 days
                expires_at = datetime.now(UTC) + timedelta(days=7)

                invitation = UserInvitation(email=email, token=token, invited_by_user_id=invited_by_user_id, role_id=role_id, expires_at=expires_at)

                db.add(invitation)
                db.commit()
                db.refresh(invitation)
                return token
        except DBException as e:
            raise e
        except Exception as e:
            raise DBException(f"Could not create user invitation: {str(e)}")

    def get_user_invitation(self, token: str) -> dict:
        """Get user invitation by token."""
        try:
            with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
                invitation = db.query(UserInvitation).filter(UserInvitation.token == token, UserInvitation.is_accepted == False, UserInvitation.expires_at > datetime.now(UTC)).first()

                if not invitation:
                    raise RecordNotFoundException("Invalid or expired invitation")

                return {"id": invitation.id, "email": invitation.email, "role_id": invitation.role_id, "invited_by_user_id": invitation.invited_by_user_id, "expires_at": invitation.expires_at, "created_at": invitation.created_at}
        except DBException as e:
            raise e
        except Exception as e:
            raise DBException(f"Could not get user invitation: {str(e)}")

    def accept_user_invitation(self, token: str, hashed_password: str, full_name: str | None = None) -> UserInterface:
        """Accept a user invitation and create the user account."""
        try:
            with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
                invitation = db.query(UserInvitation).filter(UserInvitation.token == token, UserInvitation.is_accepted == False, UserInvitation.expires_at > datetime.now(UTC)).first()

                if not invitation:
                    raise RecordNotFoundException("Invalid or expired invitation")

                # Check if user already exists (shouldn't happen but safety check)
                existing_user = db.query(User).filter(User.email == invitation.email).first()
                if existing_user:
                    raise RecordExistsException("User already exists")

                # Create the user
                new_user = User(email=invitation.email, full_name=full_name, hashed_password=hashed_password, is_active=True, is_email_verified=True, role_id=invitation.role_id)  # Email is verified through invitation

                db.add(new_user)

                # Mark invitation as accepted
                invitation.is_accepted = True
                invitation.accepted_at = datetime.now(UTC)

                db.commit()
                db.refresh(new_user)

                # Return the created user
                role_name = new_user.role.name if new_user.role else None
                return UserInterface(
                    id=new_user.id,
                    email=new_user.email,
                    full_name=new_user.full_name,
                    hashed_password=new_user.hashed_password,
                    is_active=new_user.is_active,
                    is_email_verified=new_user.is_email_verified,
                    created_at=new_user.created_at,
                    updated_at=new_user.updated_at,
                    role=role_name,
                    role_id=new_user.role_id,
                )
        except DBException as e:
            raise e
        except Exception as e:
            raise DBException(f"Could not accept user invitation: {str(e)}")

    def delete_user_invitation_by_token(self, token: str) -> bool:
        """Delete a user invitation by its token.

        Returns True if deleted, False if not found."""
        try:
            with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
                invitation = db.query(UserInvitation).filter(UserInvitation.token == token).first()
                if not invitation:
                    return False
                db.delete(invitation)
                db.commit()
                return True
        except DBException as e:
            raise e
        except Exception as e:
            raise DBException(f"Could not delete user invitation: {str(e)}")
