from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel as PydanticBaseModel
from user.models.interface import RoleSortEnum, UserSortEnum


class UserCreateRequest(PydanticBaseModel):
    """Represents the user API Request"""

    email: str
    password: str
    full_name: str | None = None


class UserUpdateRequest(PydanticBaseModel):
    """Represents the user update API request"""

    # email: str | None = None
    full_name: str | None = None
    password: str | None = None


class UserUpdateRequestWithRole(PydanticBaseModel):
    """Represents the user update API request"""

    full_name: str | None = None
    password: str | None = None
    role_id: int | None = None


class RoleCreateRequest(PydanticBaseModel):
    """Represents a role create API request"""

    name: str
    description: str | None = None


class RoleRequest(PydanticBaseModel):
    """Represents a role request model for filtering and pagination"""

    role_name: str | None = None
    role_id: int | None = None
    description: str | None = None
    created_after: datetime | None = None
    created_before: datetime | None = None
    updated_after: datetime | None = None
    updated_before: datetime | None = None
    sort_by: RoleSortEnum = RoleSortEnum.id
    sort_order: Literal["asc", "desc"] = "desc"
    page: int = 1
    page_size: int = 10


class UsersRequest(PydanticBaseModel):
    """Represents a user request model for filtering and pagination"""

    user_id: int | None = None
    email: str | None = None
    is_active: bool | None = None
    created_after: datetime | None = None
    created_before: datetime | None = None
    updated_after: datetime | None = None
    updated_before: datetime | None = None
    sort_by: UserSortEnum = UserSortEnum.id
    sort_order: Literal["asc", "desc"] = "desc"
    page: int = 1
    page_size: int = 10


class UserRoleRequest(PydanticBaseModel):
    """Represents a user-role filtering request for pagination and search"""

    user_id: int | None = None
    role_name: str | None = None
    role_id: int | None = None
    created_after: datetime | None = None
    created_before: datetime | None = None
    updated_after: datetime | None = None
    updated_before: datetime | None = None
    sort_by: str
    sort_order: Literal["asc", "desc"] = "desc"
    page: int = 1
    page_size: int = 10


class UserRoleCreateRequest(PydanticBaseModel):
    """Represents a user-role create API request"""

    user_id: int
    role_id: int
    role_name: str


class ForgotPasswordRequest(PydanticBaseModel):
    """Represents a forgot password request"""

    email: str


class ResetPasswordRequest(PydanticBaseModel):
    """Represents a reset password request with token"""

    token: str
    new_password: str


class VerifyEmailRequest(PydanticBaseModel):
    """Represents an email verification request"""

    token: str


class UserInvitationRequest(PydanticBaseModel):
    """Represents a user invitation request"""

    email: str
    role_id: int


class AcceptInvitationRequest(PydanticBaseModel):
    """Represents an accept invitation request"""

    token: str
    password: str
    full_name: str | None = None
