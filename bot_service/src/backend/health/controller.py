"""Health REST controller module"""

# from common.controller import APIRouter
from fastapi import APIRouter, Request
from fastapi.responses import Response
from health.manager import HealthServiceManager
from health.models import HealthResponse


class HealthRestController:
    """Implements health REST controller"""

    def __init__(self, health_service_manager: HealthServiceManager) -> None:
        super().__init__()
        self._health_service_manager = health_service_manager

    def prepare(self, app: APIRouter) -> None:
        """
        Prepare the health REST controller.
        """

        app.tags = ["health"]

        @app.get(
            "/health",
        )
        async def health(request: Request, response: Response) -> HealthResponse:
            """Returns the health response"""
            ping_response = await self._health_service_manager.ping()
            return ping_response
