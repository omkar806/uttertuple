from datetime import datetime
from enum import Enum

from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict


class User(PydanticBaseModel):
    """Represents the user model."""

    id: int
    email: str
    full_name: str | None = None
    hashed_password: str
    is_active: bool
    is_email_verified: bool = False
    created_at: datetime
    updated_at: datetime
    role: str
    role_id: int | None = None

    # model_config = ConfigDict(
    #     from_attributes=True,
    # )


class UserCreate(PydanticBaseModel):
    """Represents the user creation model."""

    email: str
    password: str
    full_name: str | None = None
    role_id: int

    model_config = ConfigDict(
        from_attributes=True,
    )


class RoleSortEnum(str, Enum):
    """Represents the role sorting options."""

    id = "id"
    name = "name"
    description = "description"
    created_at = "created_at"
    updated_at = "updated_at"


class UserSortEnum(str, Enum):
    """Represents the user sorting options."""

    id = "id"
    email = "email"
    created_at = "created_at"
    updated_at = "updated_at"


class DefaultUserRoleEnum(str, Enum):
    """Represents the default user roles."""

    admin = "admin"
    member = "member"
