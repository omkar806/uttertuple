# Application startup
import asyncio
import time
import warnings
from argparse import ArgumentParser
from contextlib import asynccontextmanager
from uuid import uuid4

import uvicorn

# from audit.controller import AuditRestController
from audit.db_models import AuditModelService
from audit.manager import AuditService
from auth.controller import AuthRestController
from auth.manager import AuthServiceManager
from common.configuration import Configuration
from common.logger import logger, tracer
from database.manager import Base, DatabaseServiceManager
from dotenv import load_dotenv
from email_service.manager import EmailServiceManager
from fastapi import APIRouter, FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from health.controller import HealthRestController
from health.manager import HealthServiceManager
from LLM.manager import LLMServiceManager
from user.controller import UserRestController
from user.db_models import UserModelService
from user.manager import UserServiceManager

warnings.filterwarnings("ignore", category=UserWarning)


# from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

parser = ArgumentParser(description="Runs the application")
parser.add_argument("-e", "--env", help="Path to .env file", default="./etc/.env")
args = parser.parse_args()
load_dotenv(args.env)

logger.info("Starting application ...")

config = Configuration()
config_env = config.configuration()
config_ini = config.config_ini()
app_router = APIRouter()

database_service_manager = DatabaseServiceManager(config)

try:
    if Base:
        logger.info("Trying creating base tables..", extra={"tags": "create_base_tables"})
        Base.metadata.create_all(bind=database_service_manager.postgres_db_service().engine)

except BaseException as e:
    error = {"error": e}
    logger.critical(f"Could not create base tables due to \n {error}, db operations won't work!")


email_service_manager = EmailServiceManager(config)


audit_db_model_service = AuditModelService(database_service_manager)
audit_service_manager = AuditService(audit_db_model_service, database_service_manager, config)
user_db_model_service = UserModelService(database_service_manager)
user_service_manager = UserServiceManager(user_db_model_service, audit_service_manager, config, email_service_manager)

auth_service_manager = AuthServiceManager(config, user_db_model_service)
auth_rest_controller = AuthRestController(auth_service_manager, audit_service_manager)
auth_rest_controller.prepare(app_router)

user_rest_controller = UserRestController(user_service_manager, database_service_manager, auth_service_manager, audit_service_manager)
user_rest_controller.prepare(app_router)

health_service_manager = HealthServiceManager()


health_rest_controller = HealthRestController(health_service_manager).prepare(app_router)

llm_service_manager = LLMServiceManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # start the redis consumer
    audit_service_manager.start()
    yield
    # stop the redis consumer
    audit_service_manager.stop()


app = FastAPI(lifespan=lifespan)


app.add_middleware(GZipMiddleware, minimum_size=1000, compresslevel=5)
# app.add_middleware(HTTPSRedirectMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = time.perf_counter() - start_time
    logger.info(f"{request.method} {request.url} completed in {process_time: .4f}s")
    response.headers["X-Process-Time"] = str(f"{process_time: .4f}s")
    return response


@app.middleware("http")
async def timeout_middleware(request: Request, call_next):
    """
    Middleware to add a timeout to requests
    """
    try:
        return await asyncio.wait_for(call_next(request), timeout=10)
    except asyncio.TimeoutError:
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"message": "Request timed out"})  # noqa: ASYNC910


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """
    Middleware to add a request ID to each request
    """
    request_id = uuid4().hex
    with tracer.start_as_current_span("request"):
        request.state.request_id = request_id
        span_attributes = {"X-Request-ID": request_id}
        logger.info(f"Starting api call for url: {request.url}", extra=span_attributes)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


app.include_router(app_router, prefix="/v1/api")

if __name__ == "__main__":
    # uvicorn.run("main:app", host=config_env.server_configuration.host, timeout_keep_alive=600, port=int(config_env.server_configuration.port), reload=True, workers=1)
    uvicorn.run(app, host=config_env.server_configuration.host, timeout_keep_alive=600, port=int(config_env.server_configuration.port))
