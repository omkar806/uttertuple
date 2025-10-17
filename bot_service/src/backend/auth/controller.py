"""Auth REST controller module"""

"""Auth REST controller module"""

from datetime import timedelta

# from common.controller import APIRouter
from typing import Annotated

from audit.manager import AuditService
from audit.models.interface import CreateAuditLogInterface
from auth.manager import AuthServiceManager
from auth.models.request import RefreshTokenRequest, Token
from common.logger import logger, tracer
from exceptions.db import DBException, RecordNotFoundException
from fastapi import APIRouter, Depends, HTTPException, Request, Security, status
from fastapi.security import OAuth2PasswordRequestForm
from user.models.interface import User


class AuthRestController:
    """Implements auth REST controller"""

    def __init__(self, auth_service_manager: AuthServiceManager, audit_service: AuditService) -> None:
        super().__init__()
        self.auth_service_manager = auth_service_manager
        self.custom_oauth2_service = self.auth_service_manager.get_custom_oauth_service()
        self.audit_service = audit_service

    def prepare(self, app: APIRouter) -> None:

        # Factory that lets you pass extra args (e.g., roles)
        def get_current_user_with_roles(roles: list[str] | None = None, scopes: list[str] | None = None):
            """
            Dependency that retrieves the current user and checks their roles and scopes.
            """

            def dep(current_user: Annotated[User, Security(self.custom_oauth2_service.get_current_user, scopes=scopes)]):
                """
                Dependency that retrieves the current user and checks their roles and scopes.
                """
                if not current_user.is_active:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Logged in user is inactive")
                if roles and current_user.role not in roles:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
                return current_user

            return dep

        @app.post("/token", tags=["auth"])
        def login_for_access_token(
            form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
            request: Request,
        ) -> Token:
            """
            Get a token for the user.
            """
            request_id = request.state.request_id or "unknown"
            span_attributes = {
                "name": f"{request.method} {request.url.path}",
                "request_id": request_id,
                "action_type": "write",
                "target_type": "user",
                "status": "attempted",
                "ip_address": request.client.host,
                "detail": f"Generating token for user {form_data.username}",
            }

            with tracer.start_as_current_span(f"AuthRestController.login_for_access_token.{request_id}", attributes=span_attributes) as span:
                try:
                    user = self.custom_oauth2_service.authenticate_user(form_data.username, form_data.password)
                    if not user:
                        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
                    access_token_expires = timedelta(seconds=self.custom_oauth2_service.ACCESS_TOKEN_EXPIRE_SECONDS)
                    refresh_token_expires = timedelta(seconds=self.custom_oauth2_service.REFRESH_TOKEN_EXPIRE_SECONDS)
                    access_token, exp = self.custom_oauth2_service.create_access_token(
                        data={"sub": user.email, "scopes": form_data.scopes},
                        expires_delta=access_token_expires,
                    )
                    if form_data.scopes and "offline_access" in form_data.scopes:
                        refresh_token, exp = self.custom_oauth2_service.create_access_token(
                            data={"sub": user.email, "scopes": form_data.scopes},
                            expires_delta=refresh_token_expires,
                        )
                        return Token(access_token=access_token, refresh_token=refresh_token, token_type="bearer", scope=" ".join(form_data.scopes), userId=str(user.id), exp=int(exp.timestamp()))  # nosec: B106

                    return Token(access_token=access_token, token_type="bearer", scope=" ".join(form_data.scopes), userId=str(user.id), exp=int(exp.timestamp()))  # nosec: B106
                except RecordNotFoundException as e:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User not found")
                except HTTPException as e:
                    raise e
                except Exception as e:
                    logger.exception(f"Error generating token: {str(e)}")
                    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")
                finally:
                    self.audit_service.log(**CreateAuditLogInterface.model_validate(span_attributes).model_dump())

        @app.post("/token/refresh", tags=["auth"])
        def refresh_access_token(refresh_request: RefreshTokenRequest, request: Request) -> Token:
            """
            Refresh an access token using a refresh token.
            """
            request_id = request.state.request_id or "unknown"
            span_attributes = {
                "name": f"{request.method} {request.url.path}",
                "request_id": request_id,
                "action_type": "write",
                "target_type": "user",
                "status": "attempted",
                "ip_address": request.client.host,
                "detail": f"Refreshing token",
            }

            with tracer.start_as_current_span(f"AuthRestController.refresh_access_token.{request_id}", attributes=span_attributes) as span:

                try:
                    user, scopes = self.custom_oauth2_service.verify_refresh_token(refresh_request.refresh_token)

                    access_token_expires = timedelta(seconds=self.custom_oauth2_service.ACCESS_TOKEN_EXPIRE_SECONDS)
                    refresh_token_expires = timedelta(seconds=self.custom_oauth2_service.REFRESH_TOKEN_EXPIRE_SECONDS)

                    access_token, exp = self.custom_oauth2_service.create_access_token(
                        data={"sub": user.email, "scopes": scopes},
                        expires_delta=access_token_expires,
                    )

                    # Generate a new refresh token if offline_access is in scopes
                    if scopes and "offline_access" in scopes:
                        new_refresh_token, _ = self.custom_oauth2_service.create_access_token(
                            data={"sub": user.email, "scopes": scopes},
                            expires_delta=refresh_token_expires,
                        )
                        return Token(access_token=access_token, refresh_token=new_refresh_token, token_type="bearer", scope=" ".join(scopes) if isinstance(scopes, list) else scopes, userId=str(user.id), exp=int(exp.timestamp()))  # nosec: B106

                    return Token(access_token=access_token, token_type="bearer", scope=" ".join(scopes) if isinstance(scopes, list) else scopes, userId=str(user.id), exp=int(exp.timestamp()))  # nosec: B106

                except Exception as e:
                    logger.exception(f"Error refreshing token: {str(e)}")
                    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

                finally:
                    self.audit_service.log(**CreateAuditLogInterface.model_validate(span_attributes).model_dump())

        @app.get("/users/me/", response_model=User, tags=["auth"])
        def read_users_me(
            current_user: Annotated[User, Depends(get_current_user_with_roles([]))],
        ):
            """
            Get current user information.
            """
            return current_user

        @app.get("/users/me/role/test", tags=["auth"])
        def read_own_role(current_user: Annotated[User, Depends(get_current_user_with_roles(roles=["admin"], scopes=[]))]):  # noqa: F841, ASYNC124
            """Role check endpoint"""
            try:
                return {"item_id": "Foo", "owner": current_user.email}
            except DBException as e:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
            except Exception as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

        @app.get("/users/me/scope/test", tags=["auth"])
        def read_own_scope(current_user: Annotated[User, Depends(get_current_user_with_roles(roles=[], scopes=["profile"]))]):  # noqa: F841, ASYNC124
            """Scope check endpoint"""
            try:
                return {"item_id": "Foo", "owner": current_user.email}
            except DBException as e:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
            except Exception as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
