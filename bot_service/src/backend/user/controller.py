"""User REST controller module"""

from typing import Annotated

from aiocache import Cache, cached
from aiocache.serializers import PickleSerializer
from audit.db_models import AuditModelService
from audit.manager import AuditService
from audit.models.request import AuditLogRequest
from audit.models.response import AuditLogListResponse, AuditLogResponse
from auth.manager import AuthServiceManager
from common.logger import logger, tracer
from common.utils import custom_key_builder
from database.manager import DatabaseServiceManager
from exceptions.db import DBException, RecordExistsException
from exceptions.user import InactiveUser, UserExists
from fastapi import APIRouter, Depends, HTTPException, Request, Security, status
from monitoring.prometheus import OPERATION_TIME, REQUEST_COUNT
from user.manager import UserServiceManager
from user.models.interface import User
from user.models.request import (
    AcceptInvitationRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    RoleCreateRequest,
    RoleRequest,
    UserCreateRequest,
    UserInvitationRequest,
    UsersRequest,
    UserUpdateRequest,
    UserUpdateRequestWithRole,
    VerifyEmailRequest,
)
from user.models.response import (
    EmailSentResponse,
    EmailVerificationResponse,
    InvitationResponse,
    PasswordResetResponse,
    RoleListResponse,
    RoleResponse,
    UserListResponse,
    UserResponse,
)


class UserRestController:
    """Implements health REST controller"""

    def __init__(self, user_service_manager: UserServiceManager, database_service_manager: DatabaseServiceManager, auth_service_manager: AuthServiceManager, audit_service: AuditService = None) -> None:
        super().__init__()
        self.user_service_manager = user_service_manager
        self.current_db = database_service_manager.postgres_db_service()
        self.current_db_engine = self.current_db.engine
        self.auth_service_manager = auth_service_manager
        self.audit_service = audit_service
        self.audit_db_model_service = None
        if audit_service:
            self.audit_db_model_service = audit_service.audit_db_model_service
        self.custom_oauth2_service = self.auth_service_manager.get_custom_oauth_service()
        self.redis_cache_config = self.auth_service_manager.config.configuration().redis_configuration

    def prepare(self, app: APIRouter) -> None:
        """
        Prepare the user REST controller.
        """

        def get_current_user_with_roles(roles: list[str] | None = None, scopes: list[str] | None = None):
            def dep(current_user: Annotated[User, Security(self.custom_oauth2_service.get_current_user, scopes=scopes)]):
                if not current_user.is_active:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
                # if roles and not any(role in roles for role in current_user.role):
                if roles and current_user.role not in roles:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
                return current_user

            return dep

        @app.post("/create_user", status_code=status.HTTP_200_OK, tags=["user_me", "admin"], response_model=UserResponse)
        def create_user(request: Request, user_create_request: UserCreateRequest = Depends()):  # noqa: F841, ASYNC124
            """Create a new user.

            Args:
                request (Request): The request object.
                user_create_request (UserCreateRequest, optional): The user creation request body. Defaults to Depends().

            Raises:
                HTTPException: If the user already exists.
                HTTPException: If there is a database error.

            Returns:
                UserResponse: The created user.
            """

            request_id = request.state.request_id or "unknown"
            span_attributes = {
                "name": f"{request.method} {request.url.path}",
                "action_type": "write",
                "target_type": "user",
                "status": "attempted",
                "ip_address": request.client.host,
                "detail": f"Creating user {user_create_request.email}",
                "request_id": request_id,
            }
            with tracer.start_as_current_span(f"UserRestController.create_user.{user_create_request.email}", attributes=span_attributes):
                try:
                    with OPERATION_TIME.labels(request.url.path, "api").time():
                        user = self.user_service_manager.add_user(user_create_request)
                        REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_200_OK).inc()
                    return user  # noqa: ASYNC910

                except (UserExists, DBException) as e:
                    REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_400_BAD_REQUEST).inc()
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

                except BaseException as e:
                    logger.exception(f"Could not create user due to {e}")
                    REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_500_INTERNAL_SERVER_ERROR).inc()
                    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

        @app.put("/user/reset_password", status_code=status.HTTP_200_OK, tags=["user_me"], response_model=UserResponse)
        def reset_password(request: Request, email: str, new_password: str):  # noqa: F841, ASYNC124
            """Reset the password for the user.

            Args:
                request (Request): The request object.
                email (str): The email of the user.
                new_password (str): The new password for the user.

            Raises:
                HTTPException: If the user is inactive.
                HTTPException: If there is a database error.

            Returns:
                UserResponse: The updated user.
            """

            # get request id from middleware
            request_id = request.state.request_id or "unknown"
            span_attributes = {
                "name": f"{request.method} {request.url.path}",
                "user_id": None,  # TODO: get user id from auth_user
                "target_id": None,  # TODO: get target id from request
                "action_type": "write",
                "target_type": "user",
                "status": "attempted",
                "ip_address": request.client.host,
                "detail": f"Resetting password for {email}",
                "request_id": request_id,
            }
            with tracer.start_as_current_span(f"UserRestController.reset_password.{email}", attributes=span_attributes):
                try:
                    with OPERATION_TIME.labels(request.url.path, "api").time():
                        updated_user = self.user_service_manager.reset_password(email=email, new_password=new_password)
                        REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_200_OK).inc()
                        return updated_user
                except (InactiveUser, DBException) as e:
                    REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_400_BAD_REQUEST).inc()
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
                except Exception as e:
                    logger.exception(
                        f"Could not reset password due to {str(e)}",
                    )
                    REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_500_INTERNAL_SERVER_ERROR).inc()
                    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

        @app.get(
            "/user/me",
            status_code=status.HTTP_200_OK,
            tags=["user_me"],
            response_model=UserResponse,
            deprecated=True,
        )
        @cached(
            key_builder=custom_key_builder,
            ttl=self.redis_cache_config.cache_ttl_seconds,
            cache=Cache.REDIS,
            serializer=PickleSerializer(),
            namespace=self.redis_cache_config.cache_namespace,
            endpoint=self.redis_cache_config.host,
            port=self.redis_cache_config.port,
            db=self.redis_cache_config.db,
            pool_max_size=self.redis_cache_config.cache_pool_max_size,
        )
        async def get_user(request: Request, auth_user: Annotated[User, Depends(get_current_user_with_roles(roles=[], scopes=[]))]):  # noqa: ASYNC124
            """Get user details.

            Args:
                request (Request): The request object.
                auth_user (Annotated[User, Depends, optional): The authenticated user. Defaults to [], scopes=[]))].

            Raises:
                HTTPException: If the user is inactive.
                HTTPException: If there is a database error.

            Returns:
                UserResponse: The user details.
            """
            # get request id from middleware
            request_id = request.state.request_id or "unknown"
            span_attributes = {
                "name": f"{request.method} {request.url.path}",
                "user_id": auth_user.id,
                "target_id": auth_user.id,
                "action_type": "read",
                "target_type": "user",
                "status": "attempted",
                "ip_address": request.client.host,
                "detail": f"Fetching user details for {auth_user.email}",
                "request_id": request_id,
            }
            with tracer.start_as_current_span(f"UserRestController.get_user.{auth_user.email}", attributes=span_attributes):

                logger.info(f"Fetching user details for {auth_user.email}")

                try:
                    with OPERATION_TIME.labels(request.url.path, "api").time():
                        db_user = self.user_service_manager.get_user(email=auth_user.email)
                        REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_200_OK).inc()
                        return db_user  # noqa: ASYNC910

                except (InactiveUser, DBException) as e:
                    REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_400_BAD_REQUEST).inc()
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

                except Exception as e:
                    logger.exception(f"Could not fetch user details due to {e}", extra={"email": auth_user.email})
                    REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_500_INTERNAL_SERVER_ERROR).inc()
                    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

        @app.put("/user/me", status_code=status.HTTP_200_OK, tags=["user_me"], response_model=UserResponse)
        def update_user(request: Request, user_data: UserUpdateRequest, auth_user: Annotated[User, Depends(get_current_user_with_roles(roles=[], scopes=[]))]):  # noqa: F841, ASYNC124
            """Update user details.

            Args:
                request (Request): The request object.
                user_data (UserUpdateRequest): The user data to update.
                auth_user (Annotated[User, Depends, optional): The authenticated user. Defaults to [], scopes=[]))].

            Raises:
                HTTPException: If the user is inactive.
                HTTPException: If there is a database error.

            Returns:
                UserResponse: The updated user..
            """
            request_id = request.state.request_id or "unknown"
            span_attributes = {
                "name": f"{request.method} {request.url.path}",
                "user_id": auth_user.id,
                "target_id": auth_user.id,
                "action_type": "write",
                "target_type": "user",
                "status": "attempted",
                "ip_address": request.client.host,
                "detail": f"Updating user details for {auth_user.email}",
                "request_id": request_id,
            }
            with tracer.start_as_current_span(f"UserRestController.update_user.{auth_user.email}", attributes=span_attributes) as span:
                logger.info(f"Updating user details for {auth_user.email}")

                try:
                    with OPERATION_TIME.labels(request.url.path, "api").time():
                        updated_user = self.user_service_manager.update_user(current_email=auth_user.email, current_user_id=auth_user.id, user_data=user_data)
                        REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_200_OK).inc()
                        return updated_user
                except (InactiveUser, DBException) as e:
                    REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_400_BAD_REQUEST).inc()
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
                except Exception as e:
                    REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_500_INTERNAL_SERVER_ERROR).inc()
                    logger.exception(
                        f"Could not update user due to {str(e)}",
                    )
                    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

        @app.delete("/user/me", status_code=status.HTTP_200_OK, tags=["user_me"], response_model=UserResponse)
        def delete_current_user(request: Request, auth_username: Annotated[User, Depends(get_current_user_with_roles(roles=[], scopes=[]))]):  # noqa: F841, ASYNC124
            """Delete the current user.

            Args:
                request (Request): The request object.
                auth_username (Annotated[User, Depends, optional): The authenticated user. Defaults to [], scopes=[]))].

            Raises:
                HTTPException: If the user is inactive.
                HTTPException: If there is a database error.

            Returns:
                UserResponse: The deleted user.
            """
            request_id = request.state.request_id or "unknown"
            span_attributes = {
                "name": f"{request.method} {request.url.path}",
                "user_id": auth_username.id,
                "target_id": auth_username.id,
                "action_type": "write",
                "target_type": "user",
                "status": "attempted",
                "ip_address": request.client.host,
                "detail": f"Deleting user {auth_username.email}",
                "request_id": request_id,
            }
            with tracer.start_as_current_span(f"UserRestController.delete_user.{auth_username.email}", attributes=span_attributes) as span:
                logger.info(f"Deleting user {auth_username.email}")

                try:
                    with OPERATION_TIME.labels(request.url.path, "api").time():
                        db_user = self.user_service_manager.delete_user(email=auth_username.email)
                        REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_200_OK).inc()
                        return db_user  # noqa: ASYNC910

                except (InactiveUser, DBException) as e:
                    REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_400_BAD_REQUEST).inc()
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

                except Exception as e:
                    REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_500_INTERNAL_SERVER_ERROR).inc()
                    logger.exception(f"Could not delete user due to {str(e)}")
                    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

        # User CRUD via Admin
        @app.delete(
            "/delete_user",
            status_code=status.HTTP_200_OK,
            tags=["admin"],
            response_model=UserResponse,
        )
        def delete_user(request: Request, email: str, auth_username: Annotated[User, Depends(get_current_user_with_roles(roles=["admin"], scopes=[]))]):  # noqa: F841, ASYNC124
            """Delete a user.

            Args:
                request (Request): The request object.
                email (str): The email of the user to delete.
                auth_username (Annotated[User, Depends, optional): The authenticated user. Defaults to ["admin"], scopes=[]))].

            Raises:
                HTTPException: If the user is inactive.
                HTTPException: If there is a database error.

            Returns:
                UserResponse: The deleted user.
            """
            request_id = request.state.request_id or "unknown"
            span_attributes = {
                "name": f"{request.method} {request.url.path}",
                "request_id": request_id,
                "user_id": auth_username.id,
                "target_id": auth_username.id,
                "action_type": "write",
                "target_type": "user",
                "status": "attempted",
                "ip_address": request.client.host,
                "detail": f"Deleting user {auth_username.email}",
                "request_id": request_id,
            }

            with tracer.start_as_current_span(f"UserRestController.delete_user.{email}", attributes=span_attributes) as span:
                logger.info(f"Deleting user {email}")
                try:
                    with OPERATION_TIME.labels(request.url.path, "api").time():
                        db_user = self.user_service_manager.delete_user(email=email)
                        REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_200_OK).inc()
                        return db_user  # noqa: ASYNC910

                except (InactiveUser, DBException) as e:
                    REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_400_BAD_REQUEST).inc()
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

                except Exception as e:
                    REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_500_INTERNAL_SERVER_ERROR).inc()
                    logger.exception(f"Could not delete user due to {str(e)}")
                    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

        @app.put("/user/update", status_code=status.HTTP_200_OK, tags=["admin"], response_model=UserResponse)
        def update_user(request: Request, current_email: str, current_user_id: int, user_update: UserUpdateRequestWithRole, auth_username: Annotated[User, Depends(get_current_user_with_roles(roles=["admin"], scopes=[]))]):  # noqa: F841, ASYNC124
            """Update a user.

            Args:
                request (Request): The request object.
                current_email (str): The email of the user to update.
                user_update (UserUpdateRequest): The updated user data.
                auth_username (Annotated[User, Depends, optional): The authenticated user. Defaults to ["admin"], scopes=[]))].

            Raises:
                HTTPException: If the user is inactive.
                HTTPException: If there is a database error.

            Returns:
                UserResponse: The updated user.
            """

            request_id = request.state.request_id or "unknown"
            span_attributes = {
                "name": f"{request.method} {request.url.path}",
                "request_id": request_id,
                "user_id": auth_username.id,
                "target_id": auth_username.id,
                "action_type": "write",
                "target_type": "user",
                "status": "attempted",
                "ip_address": request.client.host,
                "detail": f"Updating user {auth_username.email}",
            }

            with tracer.start_as_current_span(f"UserRestController.update_user.{current_email}", attributes=span_attributes) as span:

                try:
                    with OPERATION_TIME.labels(request.url.path, "api").time():
                        updated_user = self.user_service_manager.update_user(current_email=current_email, current_user_id=current_user_id, user_data=user_update)
                        REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_200_OK).inc()
                        return updated_user

                except (InactiveUser, DBException) as e:
                    REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_400_BAD_REQUEST).inc()
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

                except Exception as e:
                    REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_500_INTERNAL_SERVER_ERROR).inc()
                    logger.exception(
                        f"Could not update user due to {str(e)}",
                    )
                    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

        # ----- Roles APIs -----
        @app.post(
            "/roles",
            status_code=status.HTTP_200_OK,
            tags=["roles", "admin"],
            response_model=RoleResponse,
        )
        def create_role(
            request: Request,
            role_request: RoleCreateRequest,
            auth_user: Annotated[User, Depends(get_current_user_with_roles(roles=["admin"], scopes=[]))],  # noqa: F841, ASYNC124
        ):
            """Create a new role.

            Args:
                request (Request): The request object.
                role_request (RoleCreateRequest): The role data.
                auth_user (Annotated[User, Depends]): The authenticated user.

            Raises:
                HTTPException: If the role already exists.
                HTTPException: If there is a database error.
                HTTPException: If the user is not authorized.

            Returns:
                RoleResponse: The created role.
            """

            request_id = request.state.request_id or "unknown"
            span_attributes = {
                "name": f"{request.method} {request.url.path}",
                "request_id": request_id,
                "user_id": auth_user.id,
                "action_type": "write",
                "target_type": "role",
                "status": "attempted",
                "ip_address": request.client.host,
                "detail": f"Creating role {role_request.name}",
            }

            with tracer.start_as_current_span(f"UserRestController.create_role.{role_request.name}", attributes=span_attributes) as span:
                try:
                    with OPERATION_TIME.labels(request.url.path, "api").time():
                        role = self.user_service_manager.add_role(
                            role_request.name,
                            role_request.description,
                        )
                    REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_200_OK).inc()
                    return role
                except RecordExistsException as e:
                    REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_400_BAD_REQUEST).inc()
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

                except DBException as e:
                    REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_400_BAD_REQUEST).inc()
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
                except Exception as e:
                    REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_500_INTERNAL_SERVER_ERROR).inc()
                    logger.exception(
                        f"Could not create role due to {str(e)}",
                    )
                    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

        @app.get(
            "/roles",
            status_code=status.HTTP_200_OK,
            tags=["roles", "admin"],
            response_model=RoleListResponse,
        )
        @cached(
            key_builder=custom_key_builder,
            ttl=self.redis_cache_config.cache_ttl_seconds,
            cache=Cache.REDIS,
            serializer=PickleSerializer(),
            namespace=self.redis_cache_config.cache_namespace,
            endpoint=self.redis_cache_config.host,
            port=self.redis_cache_config.port,
            db=self.redis_cache_config.db,
            pool_max_size=self.redis_cache_config.cache_pool_max_size,
        )
        async def get_roles(request: Request, auth_user: Annotated[User, Depends(get_current_user_with_roles(roles=["admin"], scopes=[]))], role_request: RoleRequest = Depends()):  # noqa: F841, ASYNC124
            """Get roles.

            Args:
                request (Request): The request object.
                auth_user (Annotated[User, Depends]): The authenticated user.
                role_request (RoleRequest, optional): The role request object. Defaults to Depends().

            Raises:
                HTTPException: If an error occurs while fetching roles.

            Returns:
                RoleListResponse: The list of roles.
            """

            request_id = request.state.request_id or "unknown"
            span_attributes = {
                "name": f"{request.method} {request.url.path}",
                "request_id": request_id,
                "user_id": auth_user.id,
                "action_type": "read",
                "target_type": "role",
                "status": "attempted",
                "ip_address": request.client.host,
                "detail": f"Fetching roles",
            }
            with tracer.start_as_current_span(f"UserRestController.get_roles.{request_id}", attributes=span_attributes) as span:
                try:
                    with OPERATION_TIME.labels(request.url.path, "api").time():
                        roles = self.user_service_manager.get_roles(**role_request.model_dump())
                        REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_200_OK).inc()
                        return roles  # noqa: ASYNC910
                except DBException as e:
                    REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_400_BAD_REQUEST).inc()
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
                except Exception as e:
                    REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_500_INTERNAL_SERVER_ERROR).inc()
                    logger.exception(
                        f"Could not fetch roles due to {str(e)}",
                    )
                    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

        @app.delete(
            "/roles",
            status_code=status.HTTP_200_OK,
            tags=["roles", "admin"],
            response_model=RoleResponse,
        )
        def delete_role(
            request: Request,
            name: str,
            auth_user: Annotated[User, Depends(get_current_user_with_roles(roles=["admin"], scopes=[]))],  # noqa: F841, ASYNC124
        ):
            """Delete a role.

            Args:
                request (Request): The request object.
                name (str): The name of the role to delete.
                auth_user (Annotated[User, Depends]): The authenticated user.

            Raises:
                HTTPException: If the role does not exist.
                HTTPException: If there is a database error.

            Returns:
                RoleResponse: The deleted role.
            """
            request_id = request.state.request_id or "unknown"
            span_attributes = {
                "name": f"{request.method} {request.url.path}",
                "request_id": request_id,
                "user_id": auth_user.id,
                "action_type": "delete",
                "target_type": "role",
                "status": "attempted",
                "ip_address": request.client.host,
                "detail": f"Deleting role {name}",
            }
            with tracer.start_as_current_span(f"UserRestController.delete_role.{request_id}", attributes=span_attributes) as span:
                try:
                    with OPERATION_TIME.labels(request.url.path, "api").time():
                        role = self.user_service_manager.delete_role_by_name(name)
                        REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_200_OK).inc()
                        return role
                except DBException as e:
                    REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_400_BAD_REQUEST).inc()
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
                except Exception as e:
                    REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_500_INTERNAL_SERVER_ERROR).inc()
                    logger.exception(
                        f"Could not delete role due to {str(e)}",
                    )
                    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

        @app.get(
            "/users",
            status_code=status.HTTP_200_OK,
            tags=["admin"],
            response_model=UserListResponse,
        )
        @cached(
            key_builder=custom_key_builder,
            ttl=self.redis_cache_config.cache_ttl_seconds,
            cache=Cache.REDIS,
            serializer=PickleSerializer(),
            namespace=self.redis_cache_config.cache_namespace,
            endpoint=self.redis_cache_config.host,
            port=self.redis_cache_config.port,
            db=self.redis_cache_config.db,
            pool_max_size=self.redis_cache_config.cache_pool_max_size,
        )
        async def get_all_users(request: Request, auth_user: Annotated[User, Depends(get_current_user_with_roles(roles=["admin"], scopes=[]))], users_request: UsersRequest = Depends()):  # noqa: F841, ASYNC124
            """Get all users with filtering, sorting, and pagination.

            Args:
                request (Request): The request object.
                auth_user (Annotated[User, Depends, optional): The authenticated user. Defaults to ["admin"], scopes=[]))].
                users_request (UsersRequest, optional): The users request object. Defaults to Depends().

            Raises:
                HTTPException: If there is a database error.
                HTTPException: If the user is not found.

            Returns:
                UserListResponse: The list of users.
            """
            request_id = request.state.request_id or "unknown"
            span_attributes = {
                "name": f"{request.method} {request.url.path}",
                "request_id": request_id,
                "user_id": auth_user.id,
                "action_type": "get",
                "target_type": "user",
                "status": "attempted",
                "ip_address": request.client.host,
            }
            with tracer.start_as_current_span(f"UserRestController.get_all_users.{request_id}", attributes=span_attributes) as span:
                try:
                    with OPERATION_TIME.labels(request.url.path, "api").time():
                        users = self.user_service_manager.get_users(**users_request.model_dump())
                        REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_200_OK).inc()
                        return users  # noqa: ASYNC910
                except DBException as e:
                    REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_400_BAD_REQUEST).inc()
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
                except Exception as e:
                    REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_500_INTERNAL_SERVER_ERROR).inc()
                    logger.exception(
                        f"Could not fetch users due to {str(e)}",
                    )
                    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

        # Email verification endpoints
        @app.post("/user/register-with-verification", status_code=status.HTTP_201_CREATED, tags=["user_registration", "user_verification"], response_model=EmailSentResponse)
        async def register_with_email_verification(request: Request, user_create_request: UserCreateRequest = Depends()):
            """Register a new user and send email verification."""
            request_id = request.state.request_id or "unknown"
            span_attributes = {
                "name": f"{request.method} {request.url.path}",
                "action_type": "write",
                "target_type": "user",
                "status": "attempted",
                "ip_address": request.client.host,
                "detail": f"Registering user with email verification {user_create_request.email}",
                "request_id": request_id,
            }
            with tracer.start_as_current_span(f"UserRestController.register_with_email_verification.{user_create_request.email}", attributes=span_attributes):
                try:
                    with OPERATION_TIME.labels(request.url.path, "api").time():
                        # Register user with email verification disabled initially
                        result = self.user_service_manager.register_user_with_email_verification(user_create_request)

                        # Send verification email
                        email_sent = await self.user_service_manager.send_registration_confirmation(user_id=result["user"].id, email=user_create_request.email, user_name=user_create_request.email)

                        REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_201_CREATED).inc()
                        return EmailSentResponse(message="Registration successful. Please check your email to verify your account.", success=email_sent)
                except Exception as e:
                    logger.exception(f"Could not register user due to {e}")
                    REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_400_BAD_REQUEST).inc()
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

        @app.post("/user/verify-email", status_code=status.HTTP_200_OK, tags=["user_verification", "user_registration"], response_model=EmailVerificationResponse)
        def verify_email(request: Request, verify_request: VerifyEmailRequest):
            """Verify user email address."""
            request_id = request.state.request_id or "unknown"
            span_attributes = {
                "name": f"{request.method} {request.url.path}",
                "action_type": "write",
                "target_type": "user",
                "status": "attempted",
                "ip_address": request.client.host,
                "detail": "Verifying email address",
                "request_id": request_id,
            }
            with tracer.start_as_current_span(f"UserRestController.verify_email.{request_id}", attributes=span_attributes):
                try:
                    with OPERATION_TIME.labels(request.url.path, "api").time():
                        user_id = self.user_service_manager.verify_email_address(verify_request.token)
                        REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_200_OK).inc()
                        return EmailVerificationResponse(message="Email verified successfully", success=True, user_id=user_id)
                except Exception as e:
                    REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_400_BAD_REQUEST).inc()
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

        # Password reset endpoints
        @app.post("/user/forgot-password", status_code=status.HTTP_200_OK, tags=["user_password"], response_model=EmailSentResponse)
        async def forgot_password(request: Request, forgot_request: ForgotPasswordRequest):
            """Send password reset email."""
            request_id = request.state.request_id or "unknown"
            span_attributes = {
                "name": f"{request.method} {request.url.path}",
                "action_type": "write",
                "target_type": "user",
                "status": "attempted",
                "ip_address": request.client.host,
                "detail": f"Password reset requested for {forgot_request.email}",
                "request_id": request_id,
            }
            with tracer.start_as_current_span(f"UserRestController.forgot_password.{forgot_request.email}", attributes=span_attributes):
                try:
                    with OPERATION_TIME.labels(request.url.path, "api").time():
                        email_sent = await self.user_service_manager.send_password_reset_email(forgot_request.email)
                        REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_200_OK).inc()
                        # Always return True for security reasons
                        return EmailSentResponse(message="If your email exists in our system, you will receive a password reset link.", success=True)
                except Exception as e:
                    REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_200_OK).inc()
                    # Always return success for security reasons
                    return EmailSentResponse(message="If your email exists in our system, you will receive a password reset link.", success=True)  # noqa: ASYNC910

        @app.post("/user/reset-password-with-token", status_code=status.HTTP_200_OK, tags=["user_password"], response_model=PasswordResetResponse)
        def reset_password_with_token(request: Request, reset_request: ResetPasswordRequest):
            """Reset password using reset token."""
            request_id = request.state.request_id or "unknown"
            span_attributes = {
                "name": f"{request.method} {request.url.path}",
                "action_type": "write",
                "target_type": "user",
                "status": "attempted",
                "ip_address": request.client.host,
                "detail": "Resetting password with token",
                "request_id": request_id,
            }
            with tracer.start_as_current_span(f"UserRestController.reset_password_with_token.{request_id}", attributes=span_attributes):
                try:
                    with OPERATION_TIME.labels(request.url.path, "api").time():
                        success = self.user_service_manager.reset_password_with_token(reset_request.token, reset_request.new_password)
                        REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_200_OK).inc()
                        return PasswordResetResponse(message="Password reset successfully", success=success)
                except Exception as e:
                    REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_400_BAD_REQUEST).inc()
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

        # Audit log endpoints
        @app.get("/audit/logs", status_code=status.HTTP_200_OK, tags=["audit"], response_model=AuditLogListResponse)
        async def get_audit_logs(request: Request, auth_user: Annotated[User, Depends(get_current_user_with_roles(roles=["admin"], scopes=[]))], audit_request: AuditLogRequest = Depends()):  # noqa: F841, ASYNC124
            """Get audit logs with role-based filtering.

            Admin users can view all audit logs with optional filtering.
            Regular users can only view their own audit logs.

            Args:
                request (Request): The request object.
                audit_request (AuditLogRequest): The audit log request with filters.
                auth_user (User): The authenticated user.

            Returns:
                AuditLogListResponse: The filtered audit logs with pagination info.
            """
            request_id = request.state.request_id or "unknown"
            span_attributes = {
                "name": f"{request.method} {request.url.path}",
                "action_type": "read",
                "target_type": "audit_log",
                "status": "attempted",
                "ip_address": request.client.host,
                "detail": f"Fetching audit logs (admin: {auth_user.role == 'admin'})",
                "request_id": request_id,
                "user_id": auth_user.id,
            }

            with tracer.start_as_current_span(f"UserRestController.get_audit_logs.{request_id}", attributes=span_attributes):
                try:
                    if not self.audit_db_model_service:
                        REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_503_SERVICE_UNAVAILABLE).inc()
                        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Audit service not available")

                    with OPERATION_TIME.labels(request.url.path, "api").time():
                        # Check if user is admin
                        is_admin = auth_user.role in ["admin", "superadmin"]

                        result = self.audit_db_model_service.get_audit_logs(
                            page_size=audit_request.page_size,
                            page=audit_request.page,
                            user_id=audit_request.user_id,
                            action_type=audit_request.action_type,
                            target_type=audit_request.target_type,
                            status=audit_request.status,
                            start_date=audit_request.start_date,
                            end_date=audit_request.end_date,
                            current_user_id=auth_user.id,
                            is_admin=is_admin,
                        )

                        # Convert to response models
                        audit_logs_response = [AuditLogResponse.model_validate(audit_log) for audit_log in result["audit_logs"]]

                        response = AuditLogListResponse(audit_logs=audit_logs_response, total_count=result["total_count"], page_size=result["page_size"], page=result["page"], has_more=result["has_more"])

                        REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_200_OK).inc()
                        return response  # noqa: ASYNC910

                except HTTPException:
                    raise
                except DBException as e:
                    logger.error(f"Request ID: {request_id} - Database error while fetching audit logs: {str(e)}")
                    REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_500_INTERNAL_SERVER_ERROR).inc()
                    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error")
                except Exception as e:
                    logger.error(f"Request ID: {request_id} - Unexpected error while fetching audit logs: {str(e)}")
                    REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_500_INTERNAL_SERVER_ERROR).inc()
                    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected error")

        @app.get("/users/audit/logs", status_code=status.HTTP_200_OK, tags=["audit"], response_model=AuditLogListResponse)
        async def get_user_audit_logs(request: Request, user_id: int, auth_user: Annotated[User, Depends(get_current_user_with_roles(roles=["admin", "member"], scopes=[]))], audit_request: AuditLogRequest = Depends()):  # noqa: F841, ASYNC124
            """Get audit logs for a specific user with role-based access control.

            Admin users can view audit logs for any user.
            Regular users can only view their own audit logs.

            Args:
                request (Request): The request object.
                user_id (int): The ID of the user whose audit logs to retrieve.
                audit_request (AuditLogRequest): The audit log request with filters.
                auth_user (User): The authenticated user.

            Returns:
                AuditLogListResponse: The filtered audit logs for the specified user.
            """
            request_id = request.state.request_id or "unknown"
            span_attributes = {
                "name": f"{request.method} {request.url.path}",
                "action_type": "read",
                "target_type": "audit_log",
                "target_id": user_id,
                "status": "attempted",
                "ip_address": request.client.host,
                "detail": f"Fetching audit logs for user {user_id}",
                "request_id": request_id,
                "user_id": auth_user.id,
            }

            with tracer.start_as_current_span(f"UserRestController.get_user_audit_logs.{user_id}.{request_id}", attributes=span_attributes):
                try:
                    if not self.audit_db_model_service:
                        REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_503_SERVICE_UNAVAILABLE).inc()
                        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Audit service not available")

                    with OPERATION_TIME.labels(request.url.path, "api").time():
                        result = self.audit_db_model_service.get_user_audit_logs(
                            user_id=auth_user.id,
                            page_size=audit_request.page_size,
                            page=audit_request.page,
                            action_type=audit_request.action_type,
                            target_type=audit_request.target_type,
                            status=audit_request.status,
                            start_date=audit_request.start_date,
                            end_date=audit_request.end_date,
                        )

                        # Convert to response models
                        audit_logs_response = [AuditLogResponse.model_validate(audit_log) for audit_log in result["audit_logs"]]

                        response = AuditLogListResponse(audit_logs=audit_logs_response, total_count=result["total_count"], page_size=result["page_size"], page=result["page"], has_more=result["has_more"])

                        REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_200_OK).inc()
                        return response  # noqa: ASYNC910

                except HTTPException:
                    raise
                except DBException as e:
                    logger.error(f"Request ID: {request_id} - Database error while fetching user audit logs: {str(e)}")
                    REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_500_INTERNAL_SERVER_ERROR).inc()
                    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error")
                except Exception as e:
                    logger.error(f"Request ID: {request_id} - Unexpected error while fetching user audit logs: {str(e)}")
                    REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_500_INTERNAL_SERVER_ERROR).inc()
                    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected error")

        # User invitation endpoints
        @app.post("/user/invite", status_code=status.HTTP_200_OK, tags=["user_admin", "admin"], response_model=InvitationResponse)
        async def invite_user(request: Request, invitation_request: UserInvitationRequest, auth_user: Annotated[User, Depends(get_current_user_with_roles(roles=["admin"], scopes=[]))]):
            """Invite a new user (admin only)."""
            request_id = request.state.request_id or "unknown"
            span_attributes = {
                "name": f"{request.method} {request.url.path}",
                "action_type": "write",
                "target_type": "user",
                "status": "attempted",
                "ip_address": request.client.host,
                "detail": f"Inviting user {invitation_request.email}",
                "request_id": request_id,
                "user_id": auth_user.id,
            }
            with tracer.start_as_current_span(f"UserRestController.invite_user.{invitation_request.email}", attributes=span_attributes):
                try:
                    with OPERATION_TIME.labels(request.url.path, "api").time():
                        result = await self.user_service_manager.send_user_invitation(
                            email=invitation_request.email,
                            invited_by_user_id=auth_user.id,
                            role_id=invitation_request.role_id,
                            inviter_name=auth_user.email,
                        )
                        REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_200_OK).inc()
                        # Could add invitation ID if needed
                        return InvitationResponse(message=result["message"], success=result["success"])
                except Exception as e:
                    REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_400_BAD_REQUEST).inc()
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

        @app.get("/user/invitation/{token}", status_code=status.HTTP_200_OK, tags=["user_invitation"])
        @cached(
            key_builder=custom_key_builder,
            ttl=self.redis_cache_config.cache_ttl_seconds,
            cache=Cache.REDIS,
            serializer=PickleSerializer(),
            namespace=self.redis_cache_config.cache_namespace,
            endpoint=self.redis_cache_config.host,
            port=self.redis_cache_config.port,
            db=self.redis_cache_config.db,
            pool_max_size=self.redis_cache_config.cache_pool_max_size,
        )
        async def get_invitation_details(request: Request, token: str):  # noqa: ASYNC124
            """Get invitation details by token."""
            request_id = request.state.request_id or "unknown"
            span_attributes = {
                "name": f"{request.method} {request.url.path}",
                "action_type": "read",
                "target_type": "invitation",
                "status": "attempted",
                "ip_address": request.client.host,
                "detail": "Getting invitation details",
                "request_id": request_id,
            }
            with tracer.start_as_current_span(f"UserRestController.get_invitation_details.{request_id}", attributes=span_attributes):
                try:
                    with OPERATION_TIME.labels(request.url.path, "api").time():
                        details = self.user_service_manager.get_invitation_details(token)
                        REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_200_OK).inc()
                        return details  # noqa: ASYNC910
                except Exception as e:
                    REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_400_BAD_REQUEST).inc()
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

        @app.post("/user/accept-invitation", status_code=status.HTTP_201_CREATED, tags=["user_invitation"], response_model=UserResponse)
        def accept_invitation(request: Request, accept_request: AcceptInvitationRequest):
            """Accept user invitation and create account."""
            request_id = request.state.request_id or "unknown"
            span_attributes = {
                "name": f"{request.method} {request.url.path}",
                "action_type": "write",
                "target_type": "user",
                "status": "attempted",
                "ip_address": request.client.host,
                "detail": "Accepting user invitation",
                "request_id": request_id,
            }
            with tracer.start_as_current_span(f"UserRestController.accept_invitation.{request_id}", attributes=span_attributes):
                try:
                    with OPERATION_TIME.labels(request.url.path, "api").time():
                        user = self.user_service_manager.accept_invitation(accept_request.token, accept_request.password, accept_request.full_name)
                        REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_201_CREATED).inc()
                        return UserResponse(id=user.id, email=user.email, full_name=user.full_name, is_active=user.is_active, is_email_verified=user.is_email_verified, role_id=user.role_id)
                except Exception as e:
                    REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_400_BAD_REQUEST).inc()
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
