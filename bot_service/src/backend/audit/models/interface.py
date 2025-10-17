from datetime import datetime
from enum import Enum

from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict


class CreateAuditLogInterface(PydanticBaseModel):
    """Interface for creating an audit log entry."""

    name: str
    user_id: int | None = None
    target_id: int | None = None
    action_type: str
    target_type: str
    status: str
    detail: str | None = None
    ip_address: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    request_id: str | None = None

    model_config = ConfigDict(from_attributes=True)
