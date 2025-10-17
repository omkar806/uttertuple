"""Contains the audit API response models."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    """Response model for a single audit log entry."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: Optional[str] = None
    user_id: Optional[int] = None
    target_id: Optional[int] = None
    action_type: str
    target_type: str
    status: str
    detail: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    request_id: Optional[str] = None


class AuditLogListResponse(BaseModel):
    """Response model for audit log list."""

    audit_logs: List[AuditLogResponse]
    total_count: int
    page_size: int
    page: int
    has_more: bool
