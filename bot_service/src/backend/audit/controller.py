"""User REST controller module"""

from typing import Annotated

from audit.manager import AuditService
from auth.manager import AuthServiceManager
from common.logger import logger, tracer
from database.manager import DatabaseServiceManager
from exceptions.db import DBException, RecordExistsException
from fastapi import APIRouter, Depends, HTTPException, Request, Security, status
from monitoring.prometheus import OPERATION_TIME, REQUEST_COUNT
from user.models.interface import User


class AuditRestController:
    """Implements audit REST controller"""

    def __init__(self, audit_service_manager: AuditService, database_service_manager: DatabaseServiceManager, auth_service_manager: AuthServiceManager) -> None:
        super().__init__()
        self.audit_service_manager = audit_service_manager
        self.current_db = database_service_manager.postgres_db_service()
        self.current_db_engine = self.current_db.engine
        self.auth_service_manager = auth_service_manager
        self.custom_oauth2_service = self.auth_service_manager.get_custom_oauth_service()

    def prepare(self, app: APIRouter) -> None:
        """
        Prepare the audit REST controller.
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

        # @app.get("/users/audit/logs", status_code=status.HTTP_200_OK, tags=["audit"])
        # async def get_audit_logss(request: Request, page_size: int = 100, page: int = 0, auth_user: Annotated[User, Depends(get_current_user_with_roles(roles=["admin", "superadmin"]))] = None):
        #     """Get audit logs."""
        #     request_id = request.state.request_id or "unknown"
        #     logger.info(f"Request ID: {request_id} - Fetching audit logs with page size {page_size} and page {page}")
        #     with tracer.start_as_current_span("get_audit_logs"):
        #         try:
        #             with OPERATION_TIME.labels(request.method, request.url.path).time():
        #                 result = self.audit_service_manager.get_audit_logs(db_engine=self.current_db_engine, page_size=page_size, page=page)
        #                 REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_200_OK).inc()
        #                 return result
        #         except DBException as e:
        #             logger.error(f"Request ID: {request_id} - Database error while fetching audit logs: {str(e)}")
        #             REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_500_INTERNAL_SERVER_ERROR).inc()
        #             raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error")
        #         except Exception as e:
        #             logger.error(f"Request ID: {request_id} - Unexpected error while fetching audit logs: {str(e)}")
        #             REQUEST_COUNT.labels(request.method, request.url.path, status.HTTP_500_INTERNAL_SERVER_ERROR).inc()
        #             raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected error")
