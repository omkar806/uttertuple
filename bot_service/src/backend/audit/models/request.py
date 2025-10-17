from datetime import datetime
from typing import Annotated, Literal, Optional

from pydantic import BaseModel as PydanticBaseModel
from pydantic import Field
from user.models.interface import RoleSortEnum, UserSortEnum


class AuditLogRequest(PydanticBaseModel):
    """Request model for audit log queries."""

    page_size: int = Field(default=100, ge=1, le=1000, description="Number of records to return")
    page: int = Field(default=0, ge=0, description="Page number")
    user_id: Optional[int] = Field(default=None, description="Filter by user ID")
    action_type: Optional[str] = Field(default=None, description="Filter by action type (e.g., 'read', 'write', 'delete')")
    target_type: Optional[str] = Field(default=None, description="Filter by target type (e.g., 'user', 'role', 'invitation')")
    status: Optional[str] = Field(default=None, description="Filter by status (e.g., 'attempted', 'success', 'failed')")
    start_date: Optional[datetime] = Field(default=None, description="Filter by start date")
    end_date: Optional[datetime] = Field(default=None, description="Filter by end date")
