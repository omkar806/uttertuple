from datetime import datetime
from typing import Any, Dict, List, Optional

from audit.models.interface import CreateAuditLogInterface
from common.logger import logger, tracer
from database.manager import Base, DatabaseServiceManager
from exceptions.db import DBException
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, desc
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    name = Column(String(200))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    target_id = Column(Integer, nullable=True)
    action_type = Column(String(100), nullable=False)
    target_type = Column(String(100), nullable=False)
    status = Column(String(100), nullable=False)
    detail = Column(Text, nullable=True)
    ip_address = Column(String(2000), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    request_id = Column(String(64), index=True)

    users = relationship("User", back_populates="audit_logs")


class AuditModelService:

    def __init__(self, database_service_manager: DatabaseServiceManager):
        super().__init__()
        self.database_manager = database_service_manager
        self.current_db = self.database_manager.postgres_db_service()
        self.current_db_engine = self.current_db.engine
        self.engine = self.current_db_engine

    def create_audit_log(self, audit_log: CreateAuditLogInterface) -> AuditLog:
        try:
            with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
                db.add(audit_log)
                db.commit()
                db.refresh(audit_log)
                return audit_log
        except DBException as e:
            raise DBException(f"Could not create audit log due to {e}")

    def create_audit_logs(self, audit_logs: list[dict]) -> bool:
        """
        Bulk insert audit logs using bulk_insert_mappings for better performance.
        Takes a list of dictionaries instead of ORM objects.
        """
        try:
            with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
                db.bulk_insert_mappings(AuditLog, audit_logs)
                db.commit()
                return True
        except Exception as e:
            logger.exception(f"Could not create audit logs in bulk due to {e}")
            return False

    def get_audit_logs(
        self,
        page_size: int = 100,
        page: int = 0,
        user_id: Optional[int] = None,
        action_type: Optional[str] = None,
        target_type: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        current_user_id: Optional[int] = None,
        is_admin: bool = False,
    ) -> Dict[str, Any]:
        """
        Retrieve audit logs with filtering capabilities.
        Non-admin users can only see their own audit logs.
        """
        try:
            with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
                query = db.query(AuditLog)

                # Role-based filtering: non-admins can only see their own logs
                if not is_admin and current_user_id:
                    query = query.filter(AuditLog.user_id == current_user_id)

                # Apply filters
                if user_id is not None:
                    query = query.filter(AuditLog.user_id == user_id)
                if action_type:
                    query = query.filter(AuditLog.action_type == action_type)
                if target_type:
                    query = query.filter(AuditLog.target_type == target_type)
                if status:
                    query = query.filter(AuditLog.status == status)
                if start_date:
                    query = query.filter(AuditLog.created_at >= start_date)
                if end_date:
                    query = query.filter(AuditLog.created_at <= end_date)

                # Get total count for pagination info
                total_count = query.count()

                # Apply pagination and ordering
                audit_logs = query.order_by(desc(AuditLog.created_at)).offset(page * page_size).limit(page_size).all()

                # Check if there are more records
                has_more = (page * page_size + page_size) < total_count

                return {"audit_logs": audit_logs, "total_count": total_count, "page_size": page_size, "page": page, "has_more": has_more}

        except Exception as e:
            logger.exception(f"Could not retrieve audit logs due to {e}")
            raise DBException(f"Could not retrieve audit logs due to {e}")

    def get_user_audit_logs(
        self, user_id: int, page_size: int = 100, page: int = 0, action_type: Optional[str] = None, target_type: Optional[str] = None, status: Optional[str] = None, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Retrieve audit logs for a specific user.
        """
        try:
            with self.current_db.get_custom_db_contxt_session(self.current_db_engine) as db:
                query = db.query(AuditLog).filter(AuditLog.user_id == user_id)

                # Apply filters
                if action_type:
                    query = query.filter(AuditLog.action_type == action_type)
                if target_type:
                    query = query.filter(AuditLog.target_type == target_type)
                if status:
                    query = query.filter(AuditLog.status == status)
                if start_date:
                    query = query.filter(AuditLog.created_at >= start_date)
                if end_date:
                    query = query.filter(AuditLog.created_at <= end_date)

                # Get total count for pagination info
                total_count = query.count()

                # Apply pagination and ordering
                audit_logs = query.order_by(desc(AuditLog.created_at)).offset(page * page_size).limit(page_size).all()

                # Check if there are more records
                has_more = (page * page_size + page_size) < total_count

                return {"audit_logs": audit_logs, "total_count": total_count, "page_size": page_size, "page": page, "has_more": has_more}

        except Exception as e:
            logger.exception(f"Could not retrieve user audit logs due to {e}")
            raise DBException(f"Could not retrieve user audit logs due to {e}")
