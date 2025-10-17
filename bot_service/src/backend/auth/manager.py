from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from argon2.exceptions import VerifyMismatchError
from auth.models.interface import TokenData
from common.configuration import Configuration
from common.logger import logger
from common.utils import verify_password_using_argon
from exceptions.db import DBException, RecordNotFoundException
from fastapi import Depends, HTTPException, status
from fastapi.security import (
    HTTPBasic,
    OAuth2PasswordBearer,
    SecurityScopes,
)
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from pydantic import ValidationError
from user.db_models import UserModelService
from user.models.interface import User

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/v1/api/token",
    scopes={"me": "Read information about the current user.", "items": "Read items.", "openid": "OpenID Connect scope", "email": "Email scope", "profile": "Profile scope", "offline_access": "Offline access scope"},
)

basic_security = HTTPBasic()


class CustomOAuthService:
    def __init__(self, config: Configuration, user_db_model_service: UserModelService):
        super().__init__()
        self.user_db_model_service = user_db_model_service
        self.config = config
        self.SECRET_KEY = self.config.configuration().custom_oauth_configuration.secret_key
        self.ALGORITHM = self.config.configuration().custom_oauth_configuration.algorithm
        self.ACCESS_TOKEN_EXPIRE_SECONDS = self.config.configuration().custom_oauth_configuration.access_token_expire_seconds
        self.REFRESH_TOKEN_EXPIRE_SECONDS = self.config.configuration().custom_oauth_configuration.refresh_token_expire_seconds

    def create_access_token(self, data: dict, expires_delta: timedelta | None = None):
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=15)
        to_encode.update(
            {
                "exp": expire,
                "iat": datetime.now(timezone.utc),
                "sub": data.get("sub"),
                "scope": data.get("scopes"),
                "roles": data.get("roles", []),
            }
        )
        encoded_jwt = jwt.encode(to_encode, self.SECRET_KEY, algorithm=self.ALGORITHM)
        return encoded_jwt, expire

    def get_current_user(self, security_scopes: SecurityScopes, token: Annotated[dict, Depends(oauth2_scheme)]):
        """
        Get the current user from the token.
        """

        try:
            credentials_exception = HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
            )

            decoded_token: dict = jwt.decode(token, self.SECRET_KEY, algorithms=[self.ALGORITHM], options={"require": ["exp"]})

            username = decoded_token.get("sub")
            user = self.user_db_model_service.get_user(username)

            if username is None:
                raise credentials_exception
            token_scopes: str = decoded_token.get("scope", "")

            token_data = TokenData(scopes=token_scopes, username=username)
            user_roles = user.role

            for scope in security_scopes.scopes:
                if scope not in token_data.scopes:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Not enough permissions",
                    )
        except ExpiredSignatureError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")

        except (InvalidTokenError, ValidationError, DBException, RecordNotFoundException) as e:
            logger.exception(f"Could not validate creds due to : {str(e)}")
            raise credentials_exception

        return User(id=user.id, email=user.email, hashed_password=user.hashed_password, is_active=user.is_active, created_at=user.created_at, updated_at=user.updated_at, role=user_roles, role_id=user.role_id)

    async def get_current_user_from_token(self, token: str):
        """
        Get the current user from a token string (for direct streaming authentication).
        """
        try:
            credentials_exception = HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
            )

            decoded_token: dict = jwt.decode(token, self.SECRET_KEY, algorithms=[self.ALGORITHM], options={"require": ["exp"]})

            username = decoded_token.get("sub")
            if username is None:
                raise credentials_exception

            user = self.user_db_model_service.get_user(username)

            return User(id=user.id, email=user.email, hashed_password=user.hashed_password, is_active=user.is_active, created_at=user.created_at, updated_at=user.updated_at, role=user.role, role_id=user.role_id)  # noqa: ASYNC910

        except ExpiredSignatureError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")

        except (InvalidTokenError, ValidationError, DBException, RecordNotFoundException) as e:
            logger.exception(f"Could not validate token due to : {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
            )

    def authenticate_user(self, email: str, password: str):
        """
        Authenticate a user by email and password.
        """
        try:
            user = self.user_db_model_service.get_user(email)
            if not user:
                return False
            if not verify_password_using_argon(password, user.hashed_password):
                return False
            return user
        except VerifyMismatchError:
            logger.warning(f"Password verification failed for the email: {email}")
            return False

    def verify_refresh_token(self, refresh_token: str):
        """
        Verify a refresh token and return user information.
        """
        try:
            credentials_exception = HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate refresh token",
            )

            decoded_token: dict = jwt.decode(refresh_token, self.SECRET_KEY, algorithms=[self.ALGORITHM], options={"require": ["exp"]})
            username = decoded_token.get("sub")

            if username is None:
                raise credentials_exception

            user = self.user_db_model_service.get_user(username)
            if not user:
                raise credentials_exception

            return user, decoded_token.get("scopes", [])

        except ExpiredSignatureError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token has expired")
        except (InvalidTokenError, ValidationError, DBException, RecordNotFoundException) as e:
            logger.exception(f"Could not validate refresh token due to : {str(e)}")
            raise credentials_exception


class AuthServiceManager:
    def __init__(self, config: Configuration, user_db_model_service: UserModelService):
        self.config = config
        self.user_db_model_service = user_db_model_service
        self._custom_oauth_service = CustomOAuthService(self.config, self.user_db_model_service)

    def get_custom_oauth_service(self) -> CustomOAuthService:
        """
        Get the custom OAuth service.
        """
        return self._custom_oauth_service
