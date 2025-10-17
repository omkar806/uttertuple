from typing import List

from audit.db_models import AuditModelService
from audit.manager import AuditService
from audit.models.interface import CreateAuditLogInterface
from common.configuration import Configuration
from common.logger import logger, tracer
from common.utils import get_password_hash_using_argon
from email_service.manager import EmailServiceManager
from exceptions.db import RecordExistsException
from exceptions.user import InactiveUser, UserExists
from opentelemetry import trace
from user.db_models import Role, User, UserModelService
from user.models.interface import DefaultUserRoleEnum
from user.models.interface import User as UserInterface
from user.models.interface import UserCreate
from user.models.request import UserUpdateRequest, UserUpdateRequestWithRole


class UserServiceManager:
    """Implements the health service manager"""

    def __init__(
        self,
        user_db_model_service: UserModelService,
        audit_service: AuditService,
        config: Configuration,
        email_service_manager: EmailServiceManager,
    ) -> None:
        """
        Initializes the User service manager.

        Args:
            user_db_model_service: User database model service.
            audit_service: Audit service.
            config: Configuration.
            email_service_manager: Email service manager.
        """
        self.user_db_model_service = user_db_model_service
        self.audit_service = audit_service
        self.config = config
        self.email_service_manager = email_service_manager
        self.bootstrap_admin_user()

    def bootstrap_admin_user(self):
        """
        Bootstraps the admin user in the database.
        """
        try:
            span_attributes = {
                "name": "ADMIN & DEFAULT ROLE USER CREATION",
                "user_id": 1,
                "target_id": 1,
                "action_type": "write",
                "target_type": "user",
                "status": "attempted",
                "ip_address": "",
                "detail": "",
                "request_id": "unknown",
            }
            with tracer.start_as_current_span("UserServiceManager.bootstrap_admin_user", attributes=span_attributes) as span:
                if self.config.configuration().custom_oauth_configuration.enable_bootstrap_admin:
                    member_role = self.add_role(DefaultUserRoleEnum.member.value, "Member role")
                    admin_role = self.add_role(DefaultUserRoleEnum.admin.value, "Administrator role")

                    admin_user_request = UserCreate(email=self.config.configuration().custom_oauth_configuration.bootstrap_admin_email, password=self.config.configuration().custom_oauth_configuration.bootstrap_admin_password, role_id=admin_role.id)
                    db_admin_user = self.add_user(admin_user_request)

                    update_admin_user_request = UserUpdateRequestWithRole(role_id=admin_user_request.role_id)
                    self.update_user(admin_user_request.email, db_admin_user.get("id"), update_admin_user_request)

                    return
                logger.critical("Bootstrap admin user / admin role / admin user role is disabled, admin user will not be created !")
        except (UserExists, RecordExistsException) as e:
            logger.info(f"Bootstrap user already exists. Skipping bootstrap. {str(e)}")
        except Exception as e:
            logger.exception(f"Error bootstrapping user due {str(e)}, bootstrap admin credentials will not work !")

    def add_user(self, user: UserCreate):
        """
        Adds a user to the database.

        Args:
            user: The user to add to the database.
        """

        parent_span = trace.get_current_span()
        parent_span_attributes = getattr(parent_span, "_attributes", {})

        db_user_email = self.user_db_model_service.get_user_by_email(email=user.email)

        if db_user_email and db_user_email.is_active or db_user_email and db_user_email.is_active:
            raise UserExists("An active user with this username/email already exists.")

        if not db_user_email:
            member_roles = self.user_db_model_service.get_roles(role_name=DefaultUserRoleEnum.member.value)
            if member_roles and member_roles.get("roles"):
                role_id = member_roles["roles"][0]["id"]
            else:
                # Create member role if it doesn't exist
                member_role = self.add_role(DefaultUserRoleEnum.member.value, "Member role")
                role_id = member_role.id

            new_db_user = UserCreate(password=get_password_hash_using_argon(user.password), email=user.email, role_id=role_id)
            db_user = self.user_db_model_service.create_user(user=new_db_user)
            role_info = self.user_db_model_service.get_roles(role_id=role_id)
            role_name = role_info["roles"][0]["name"] if role_info and role_info.get("roles") else None

            parent_span_attributes.update({"target_id": db_user.id, "name": "ADDING USER"})
            self.audit_service.log(**CreateAuditLogInterface.model_validate(parent_span_attributes).model_dump())
            return UserInterface(
                id=db_user.id,
                email=db_user.email,
                hashed_password=db_user.hashed_password,
                is_active=db_user.is_active,
                created_at=db_user.created_at,
                updated_at=db_user.updated_at,
                role_id=db_user.role_id,
                role=role_name,
            ).model_dump()

        if db_user_email:
            db_user = self.user_db_model_service.activate_user(user=user)
            parent_span_attributes.update({"target_id": db_user.id})
            self.audit_service.log(**CreateAuditLogInterface.model_validate(parent_span_attributes).model_dump())
            UserInterface
            return UserInterface(
                id=db_user.id,
                email=db_user.email,
                hashed_password=db_user.hashed_password,
                is_active=db_user.is_active,
                created_at=db_user.created_at,
                updated_at=db_user.updated_at,
                role_id=db_user.role_id,
                role=role_name,
            ).model_dump()

    def get_user(self, email: str) -> User:
        """
        Retrieves a user from the database based on the username.

        Args:
            db (Session): The database session.
            username (str, optional): The username of the user to retrieve.

        Returns:
            User: The user object if found, otherwise None.
        """
        parent_span = trace.get_current_span()
        parent_span_attributes = getattr(parent_span, "_attributes", {})

        with tracer.start_as_current_span(f"UserServiceManager.get_user.{email}") as span:
            logger.info(f"Trying to fetch user details from db")

            db_user = self.user_db_model_service.get_user(email=email)
            if not db_user:
                raise InactiveUser("No user was found with this email.")

            parent_span_attributes.update({"target_id": db_user.id})
            self.audit_service.log(**CreateAuditLogInterface.model_validate(parent_span_attributes).model_dump())
            parent_span_attributes = getattr(parent_span, "_attributes", {})
            return db_user

    def get_active_user(self, username: str) -> User:
        """
        Retrieves a user from the database based on the username.

        Args:
            db (Session): The database session.
            username (str, optional): The username of the user to retrieve.

        Returns:
            User: The user object if found, otherwise None.
        """
        db_user = self.user_db_model_service.get_active_user(username=username)
        if not db_user:
            raise InactiveUser("No active user was found with this username.")
        return db_user

    def delete_user(self, email: str) -> User:
        """
        Deletes a user from the database.

        Args:
            db (Session): The database session.
            db_user: The user to delete from the database.
        """
        parent_span = trace.get_current_span()
        parent_span_attributes = getattr(parent_span, "_attributes", {})
        deleted_db_user = self.user_db_model_service.delete_user(email=email)
        self.audit_service.log(**CreateAuditLogInterface.model_validate(parent_span_attributes).model_dump())
        return deleted_db_user

    def add_role(self, name: str, description: str) -> Role:
        """
        Adds a role to the database.

        Args:
            name (str): The name of the role to add.

        Returns:
            Role: The created role.
        """
        parent_span = trace.get_current_span()
        parent_span_attributes = getattr(parent_span, "_attributes", {})
        role = self.user_db_model_service.add_role(role=name, description=description)

        parent_span_attributes.update({"target_id": role.id})
        self.audit_service.log(**CreateAuditLogInterface.model_validate(parent_span_attributes).model_dump())

        return role

    def delete_role_by_name(self, name: str) -> Role:
        """
        Deletes a role from the database by name.

        Args:
            name (str): The name of the role to delete.

        Returns:
            Role: The deleted role.
        """
        parent_span = trace.get_current_span()
        parent_span_attributes = getattr(parent_span, "_attributes", {})
        db_role = self.user_db_model_service.delete_role_by_name(role_name=name)
        parent_span_attributes.update({"target_id": db_role.id})
        self.audit_service.log(**CreateAuditLogInterface.model_validate(parent_span_attributes).model_dump())
        return db_role

    def get_roles(
        self,
        role_name: str = None,
        role_id: int = None,
        description: str = None,
        created_after: str = None,
        created_before: str = None,
        updated_after: str = None,
        updated_before: str = None,
        sort_by: str = "id",
        sort_order: str = "asc",
        page: int = 1,
        page_size: int = 10,
    ):
        """
        Retrieves roles from the database with filtering, sorting, and pagination.

        Args:
            role_name (str, optional): The name of the role to filter by.
            role_id (int, optional): The ID of the role to filter by.
            description (str, optional): The description to filter by.
            created_after (str, optional): Filter roles created after this date.
            created_before (str, optional): Filter roles created before this date.
            updated_after (str, optional): Filter roles updated after this date.
            updated_before (str, optional): Filter roles updated before this date.
            sort_by (str): The column to sort by. Default is "id".
            sort_order (str): The sort order ("asc" or "desc"). Default is "asc".
            page (int): The page number (1-indexed). Default is 1.
            page_size (int): The number of roles per page. Default is 10.

        Returns:
            dict: A dictionary containing roles and pagination metadata.
        """
        parent_span = trace.get_current_span()
        parent_span_attributes = getattr(parent_span, "_attributes", {})
        self.audit_service.log(**CreateAuditLogInterface.model_validate(parent_span_attributes).model_dump())
        roles = self.user_db_model_service.get_roles(
            role_name=role_name,
            role_id=role_id,
            description=description,
            created_after=created_after,
            created_before=created_before,
            updated_after=updated_after,
            updated_before=updated_before,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size,
        )
        return roles

    def update_user_role(self, user_id: int, role_id: int) -> User:
        """
        Updates a user's role.

        Args:
            user_id (int): The ID of the user to update.
            role_id (int): The ID of the role to assign.

        Returns:
            User: The updated user.
        """
        db_user_role = self.user_db_model_service.update_user_role(user_id=user_id, role_id=role_id)
        parent_span = trace.get_current_span()
        parent_span_attributes = getattr(parent_span, "_attributes", {})
        parent_span_attributes.update({"target_id": db_user_role.id})
        self.audit_service.log(**CreateAuditLogInterface.model_validate(parent_span_attributes).model_dump())
        return db_user_role

    def get_users(
        self,
        user_id: int = None,
        email: str = None,
        username: str = None,
        is_active: bool = None,
        created_after: str = None,
        created_before: str = None,
        updated_after: str = None,
        updated_before: str = None,
        sort_by: str = "id",
        sort_order: str = "asc",
        page: int = 1,
        page_size: int = 10,
    ):
        """
        Retrieves users from the database with filtering, sorting, and pagination.

        Args:
            user_id (int, optional): The ID of the user to filter by.
            email (str, optional): The email to filter by.
            username (str, optional): The username to filter by.
            is_active (bool, optional): Filter by active status.
            created_after (str, optional): Filter users created after this date.
            created_before (str, optional): Filter users created before this date.
            updated_after (str, optional): Filter users updated after this date.
            updated_before (str, optional): Filter users updated before this date.
            sort_by (str): The column to sort by. Default is "id".
            sort_order (str): The sort order ("asc" or "desc"). Default is "asc".
            page (int): The page number (1-indexed). Default is 1.
            page_size (int): The number of users per page. Default is 10.

        Returns:
            dict: A dictionary containing users and pagination metadata.
        """

        db_users = self.user_db_model_service.get_users(
            user_id=user_id,
            email=email,
            username=username,
            is_active=is_active,
            created_after=created_after,
            created_before=created_before,
            updated_after=updated_after,
            updated_before=updated_before,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size,
        )
        parent_span = trace.get_current_span()
        parent_span_attributes = getattr(parent_span, "_attributes", {})
        self.audit_service.log(**CreateAuditLogInterface.model_validate(parent_span_attributes).model_dump())
        return db_users

    def update_user(self, current_email: str, current_user_id: int, user_data: UserUpdateRequest | UserUpdateRequestWithRole) -> User:
        """
        Updates a user in the database.

        Args:
            user_id (int): The ID of the user to update.
            user_data (UserUpdate): The new data for the user.
            is_admin (bool): When True, allows role changes.

        Returns:
            User: The updated user object.
        """

        parent_span = trace.get_current_span()
        parent_span_attributes = getattr(parent_span, "_attributes", {})

        if user_data.password:
            user_data.password = get_password_hash_using_argon(user_data.password)

        if isinstance(user_data, UserUpdateRequestWithRole) and user_data.role_id is not None:
            self.update_user_role(current_user_id, user_data.role_id)

        user = self.user_db_model_service.update_user_by_id(current_user_id, user_data)
        self.audit_service.log(**CreateAuditLogInterface.model_validate(parent_span_attributes).model_dump())

        # final_email = user_data.email if user_data.email else current_email
        # updated_user = self.user_db_model_service.get_user(email=final_email)
        return user

    def reset_password(self, email: str, new_password: str) -> User:
        """
        Resets the password for a user.

        Args:
            email (str): The email of the user to reset the password for.
            new_password (str): The new password for the user.

        Returns:
            User: The user object with the updated password.
        """

        parent_span = trace.get_current_span()
        parent_span_attributes = getattr(parent_span, "_attributes", {})

        hashed_password = get_password_hash_using_argon(new_password)
        db_user = self.user_db_model_service.reset_password(email=email, hashed_password=hashed_password)

        parent_span_attributes.update({"target_id": db_user.id})
        self.audit_service.log(**CreateAuditLogInterface.model_validate(parent_span_attributes).model_dump())
        return db_user

    # Email verification methods
    async def send_registration_confirmation(self, user_id: int, email: str, user_name: str) -> bool:
        """Send registration confirmation email with verification token."""
        try:
            # Create verification token
            token = self.user_db_model_service.create_email_verification_token(user_id)

            # Send email
            success = await self.email_service_manager.send_registration_confirmation(email=email, user_name=user_name, verification_token=token)

            return success
        except Exception as e:
            logger.error(f"Failed to send registration confirmation: {str(e)}")
            return False  # noqa : ASYNC910

    def verify_email_address(self, token: str) -> int:
        """Verify email address using token."""
        try:
            user_id = self.user_db_model_service.verify_email_token(token)
            logger.info(f"Email verified successfully for user {user_id}")
            return user_id
        except Exception as e:
            logger.error(f"Email verification failed: {str(e)}")
            raise e

    # Password reset methods
    async def send_password_reset_email(self, email: str) -> bool:
        """Send password reset email."""
        try:
            # Check if user exists
            user = self.get_user(email)
            if not user:
                # Don't reveal whether user exists or not for security
                return True  # noqa : ASYNC910

            # Create reset token
            token = self.user_db_model_service.create_password_reset_token(email)

            # Send email
            success = await self.email_service_manager.send_password_reset(
                email=email, user_name=user.email, reset_token=token, base_url=self.config.configuration().server_configuration.proxy_url  # Using email as name since we don't have separate name field
            )

            return success
        except Exception as e:
            logger.error(f"Failed to send password reset email: {str(e)}")
            return False  # noqa : ASYNC910

    def reset_password_with_token(self, token: str, new_password: str) -> bool:
        """Reset password using reset token."""
        try:
            # Hash the new password
            hashed_password = get_password_hash_using_argon(new_password)

            # Use the token to reset password
            success = self.user_db_model_service.use_password_reset_token(token, hashed_password)

            if success:
                logger.info("Password reset successfully with token")

            return success
        except Exception as e:
            logger.error(f"Password reset with token failed: {str(e)}")
            raise e

    # User invitation methods
    async def send_user_invitation(self, email: str, invited_by_user_id: int, role_id: int, inviter_name: str) -> dict:
        """Send user invitation email using existing DB functions; if email fails, delete the created invitation record to keep DB clean."""
        try:
            token = None
            # Create invitation (DB layer persists it)
            token = self.user_db_model_service.create_user_invitation(email, invited_by_user_id, role_id)

            # Try sending email
            success = await self.email_service_manager.send_user_invitation(email=email, invitee_name=email, inviter_name=inviter_name, invitation_token=token, base_url=self.config.configuration().server_configuration.proxy_url)

            if not success:
                # Cleanup invitation row on failure
                try:
                    self.user_db_model_service.delete_user_invitation_by_token(token)
                except Exception as e:
                    logger.warning(f"Failed to cleanup invitation for {email}: {str(e)}")
                return {"success": False, "token": None, "message": "Failed to send invitation"}

            return {"success": True, "token": token, "message": "Invitation sent successfully"}
        except Exception as e:
            if token:
                self.user_db_model_service.delete_user_invitation_by_token(token)
            logger.error(f"Failed to send user invitation: {str(e)}")
            raise e

    def get_invitation_details(self, token: str) -> dict:
        """Get invitation details by token."""
        try:
            return self.user_db_model_service.get_user_invitation(token)
        except Exception as e:
            logger.error(f"Failed to get invitation details: {str(e)}")
            raise e

    def accept_invitation(self, token: str, password: str, full_name: str | None = None) -> UserInterface:
        """Accept user invitation and create account."""
        try:
            # Hash the password
            hashed_password = get_password_hash_using_argon(password)

            # Accept invitation and create user
            user = self.user_db_model_service.accept_user_invitation(token, hashed_password, full_name)

            logger.info(f"User invitation accepted and account created for {user.email}")
            return user
        except Exception as e:
            logger.error(f"Failed to accept invitation: {str(e)}")
            raise e

    def register_user_with_email_verification(self, user: UserCreate) -> dict:
        """Register a user and send email verification (modified add_user method)."""
        try:
            # Create user with is_email_verified=False initially
            parent_span = trace.get_current_span()
            parent_span_attributes = getattr(parent_span, "_attributes", {})

            db_user_email = self.user_db_model_service.get_user_by_email(email=user.email)

            if db_user_email and db_user_email.is_active:
                raise UserExists("An active user with this username/email already exists.")

            if db_user_email and not db_user_email.is_active:
                self.user_db_model_service.activate_user(user.email)
                db_user = db_user_email

            if not db_user_email:
                member_roles = self.user_db_model_service.get_roles(role_name=DefaultUserRoleEnum.transcriber.value)
                if member_roles and member_roles.get("roles"):
                    role_id = member_roles["roles"][0]["id"]
                else:
                    # Create member role if it doesn't exist
                    member_role = self.add_role(DefaultUserRoleEnum.transcriber.value, "Transcriber role")
                    role_id = member_role.id

                # # Override role_id if provided
                # if user.role_id:
                #     role_id = user.role_id

                hashed_password = get_password_hash_using_argon(user.password)
                db_user = self.user_db_model_service.create_user(UserCreate(email=user.email, password=hashed_password, role_id=role_id))

            # Create and send verification email
            verification_token = self.user_db_model_service.create_email_verification_token(db_user.id)

            parent_span_attributes.update({"target_id": db_user.id})
            self.audit_service.log(**CreateAuditLogInterface.model_validate(parent_span_attributes).model_dump())

            return {"user": db_user, "verification_token": verification_token, "requires_email_verification": True}
        except Exception as e:
            logger.exception(f"Failed to register user with email verification: {str(e)}")
            raise e
