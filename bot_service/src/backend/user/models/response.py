"""Contains the user API response models."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PaginationResponse(BaseModel):
    """Represents the pagination response model."""

    current_page: int
    page_size: int
    total_count: int
    total_pages: int
    has_next: bool
    has_prev: bool

    model_config = ConfigDict(from_attributes=True)


class UserResponse(BaseModel):
    """Represents the user API Request"""

    id: int
    email: str
    full_name: str | None = None
    is_active: bool
    is_email_verified: bool = False
    created_at: datetime
    updated_at: datetime
    role_id: int | None = None

    model_config = ConfigDict(
        from_attributes=True,
    )


class RoleResponse(BaseModel):
    """Represents the role API response model."""

    id: int
    name: str
    description: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserRoleResponse(BaseModel):
    """Represents the user role API response model."""

    id: int
    user_id: int
    role_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RoleListResponse(BaseModel):
    """Represents the role list API response model."""

    roles: list[RoleResponse]
    pagination: PaginationResponse


class UserRoleListResponse(BaseModel):
    """Represents the user role list API response model."""

    user_roles: list[UserRoleResponse]
    pagination: PaginationResponse


class UserListResponse(BaseModel):
    """Represents the user list API response model."""

    users: list[UserResponse]
    pagination: PaginationResponse


class EmailSentResponse(BaseModel):
    """Represents an email sent response."""

    message: str
    success: bool

    model_config = ConfigDict(from_attributes=True)


class EmailVerificationResponse(BaseModel):
    """Represents an email verification response."""

    message: str
    success: bool
    user_id: int | None = None

    model_config = ConfigDict(from_attributes=True)


class PasswordResetResponse(BaseModel):
    """Represents a password reset response."""

    message: str
    success: bool

    model_config = ConfigDict(from_attributes=True)


class InvitationResponse(BaseModel):
    """Represents a user invitation response."""

    message: str
    success: bool

    model_config = ConfigDict(from_attributes=True)
