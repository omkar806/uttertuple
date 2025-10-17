"""Implements the default configuration"""

import configparser
import os
import socket

from common.data_model import Configuration as ConfigurationModel


class Configuration:
    """Represents the default configuration"""

    def __init__(self):
        """
        Initialize the configuration with default values.
        """
        config_obj = {
            "application_name": os.environ.get("APPLICATION_NAME", "fantanstic_app"),
            "environment": os.environ.get("ENVIRONMENT", "local"),
            "logger_configuration": {"log_level": os.environ.get("LOG_LEVEL", "DEBUG"), "enable_rich_logger": os.environ.get("ENABLE_RICH_LOGGER", 0), "enable_json_filelogger": os.environ.get("ENABLE_JSON_FILELOGGER", 0)},
            "server_configuration": {
                "host": os.environ.get("HOST", "0.0.0.0"),  # nosec
                "port": os.environ.get("PORT", "8081"),  # nosec
                "proxy_url": os.environ.get("PROXY_URL", f'http://{os.environ.get("HOST", "0.0.0.0")}:{os.environ.get("PORT", "8081")}'),  # nosec
            },
            "openai_configuration": {
                "api_key": os.environ.get("OPENAI_API_KEY", "SAMPLE_OPENAI_API_KEY"),
                "model_name": os.environ.get("OPENAI_MODEL_NAME", "SAMPLE_OPENAI_MODEL_NAME"),
                "embedding_model_name": os.environ.get("OPENAI_EMBEDDING_MODEL_NAME", "SAMPLE_OPENAI_EMBEDDING_MODEL_NAME"),
                "context_window": int(os.environ.get("OPENAI_CONTEXT_WINDOW", 100)),
            },
            "azureai_configuration": {
                "api_key": os.environ.get("AZURE_API_KEY", "SAMPLE_AZURE_API_KEY"),
                "type": os.environ.get("AZURE_API_TYPE", "SAMPLE_AZURE_API_TYPE"),
                "base": os.environ.get("AZURE_API_BASE", "SAMPLE_AZURE_API_BASE"),
                "version": os.environ.get("AZURE_API_VERSION", "SAMPLE_AZURE_API_VERSION"),
                "deployment_name": os.environ.get("AZURE_DEPLOYMENT_NAME", "SAMPLE_AZURE_DEPLOYMENT_NAME"),
                "embedding_deployment_name": os.environ.get("AZURE_EMBEDDING_DEPLOYMENT_NAME", "SAMPLE_AZURE_EMBEDDING_DEPLOYMENT_NAME"),
                "model_name": os.environ.get("AZURE_MODEL_NAME", "SAMPLE_AZURE_MODEL_NAME"),
            },
            "perplexityai_configuration": {
                "api_key": os.environ.get("PERPLEXITY_API_KEY", "SAMPLE_PERPLEXITY_API_KEY"),
                "model_name": os.environ.get("PERPLEXITY_MODEL_NAME", "SAMPLE_PERPLEXITY_MODEL_NAME"),
                "api_base": os.environ.get("PERPLEXITY_API_BASE", "SAMPLE_PERPLEXITY_API_BASE"),
            },
            "anthropicai_configuration": {
                "api_key": os.environ.get("ANTHROPIC_API_KEY", "SAMPLE_ANTHROPIC_API_KEY"),
                "model_name": os.environ.get("ANTHROPIC_MODEL_NAME", "SAMPLE_ANTHROPIC_MODEL_NAME"),
            },
            "geminiai_configuration": {
                "api_key": os.environ.get("GEMINI_API_KEY", "SAMPLE_GEMINI_API_KEY"),
                "model_name": os.environ.get("GEMINI_MODEL_NAME", "SAMPLE_GEMINI_MODEL_NAME"),
            },
            "pinecone_configuration": {
                "api_key": os.environ.get("PINECONE_API_KEY", "SAMPLE_PINECONE_API_KEY"),
                "index": os.environ.get("PINECONE_INDEX", "SAMPLE_PINECONE_INDEX"),
                "namespace": os.environ.get("PINECONE_NAMESPACE", "SAMPLE_PINECONE_NAMESPACE"),
                "spec_cloud": os.environ.get("PINECONE_SPEC_CLOUD", "aws"),
                "spec_region": os.environ.get("PINECONE_SPEC_REGION", "us-west-2"),
                "metric": os.environ.get("PINECONE_METRIC", "cosine"),
                "timeout": os.environ.get("PINECONE_TIMEOUT", 10),
            },
            "common_configuration": {
                "max_retries": os.environ.get("MAX_RETRIES", 5),
            },
            "mongodb_configuration": {
                "host": os.environ.get("MONGODB_HOST", "SAMPLE_MONGODB_HOST"),
                "port": os.environ.get("MONGODB_PORT", 27017),
                "username": os.environ.get("MONGODB_USERNAME", "SAMPLE_MONGODB_USERNAME"),
                "password": os.environ.get("MONGODB_PASSWORD", "SAMPLE_MONGODB_PASSWORD"),
                "db": os.environ.get("MONGODB_DB", "SAMPLE_MONGODB_DB"),
            },
            "postgresql_configuration": {
                "host": os.environ.get("POSTGRES_HOST"),
                "port": int(os.environ.get("POSTGRES_PORT")),
                "username": os.environ.get("POSTGRES_USERNAME"),
                "password": os.environ.get("POSTGRES_PASSWRD"),
                "db": os.environ.get("POSTGRES_DATABASE"),
                "app_schema": os.environ.get("POSTGRES_APP_SCHEMA", "public"),
            },
            "sqlserver_configuration": {
                "host": os.environ.get("SQLSERVER_HOST", "localhost"),
                "port": int(os.environ.get("SQLSERVER_PORT", 1433)),
                "username": os.environ.get("SQLSERVER_USERNAME", "sa"),
                "password": os.environ.get("SQLSERVER_PASSWRD", "Password123"),
                "db": os.environ.get("SQLSERVER_DB", "master"),
                "app_schema": os.environ.get("SQLSERVER_APP_SCHEMA", "dbo"),
            },
            "sqlite_configuration": {
                "db_path": os.environ.get("SQLITE_DB", "sqlite.db"),
            },
            "opensearch_configuration": {
                "host": os.environ.get("OPENSEARCH_HOST", "localhost"),
                "port": int(os.environ.get("OPENSEARCH_PORT", 9200)),
                "username": os.environ.get("OPENSEARCH_USERNAME", "admin"),
                "password": os.environ.get("OPENSEARCH_PASSWORD", "admin"),
                "use_ssl": os.getenv("OPENSEARCH_USE_SSL", "True").lower() in ("true", "1", "t"),
                "verify_certs": os.getenv("OPENSEARCH_VERIFY_CERTS", "True").lower() in ("true", "1", "t"),
                "index_name": os.environ.get("OPENSEARCH_INDEX_NAME", "index"),
            },
            "langfuse_configuration": {
                "env": os.environ.get("LANGFUSE_ENV", "local"),
            },
            "pocketbase_configuration": {
                "url": os.environ.get("POCKETBASE_URL", "http://localhost:8090"),
                "admin_email": os.environ.get("POCKETBASE_ADMIN_USERNAME", "admin@example.com"),
                "admin_password": os.environ.get("POCKETBASE_ADMIN_PASSWORD", "your_secure_password"),
            },
            # "observability_configuration": {
            #     "enable_otel_collector": os.getenv("ENABLE_OTEL_COLLECTOR", "False").lower() in ("true", "1", "t"),
            #     "otel_agent_hostname": os.environ.get("OTEL_AGENT_HOSTNAME", "http://localhost"),
            #     "otel_http_agent_port": int(os.environ.get("OTEL_HTTP_AGENT_PORT", 4318)),
            #     "otel_grpc_agent_port": int(os.environ.get("OTEL_GRPC_AGENT_PORT", 4317)),
            # },
            "redis_configuration": {
                "host": os.environ.get("REDIS_HOST", "localhost"),
                "port": int(os.environ.get("REDIS_PORT", "6379")),
                "db": int(os.environ.get("REDIS_DB", "0")),
                "password": os.environ.get("REDIS_PASSWORD", None),
                "queue_name": os.environ.get("REDIS_QUEUE_NAME", "transcription_jobs"),
                "cache_ttl_seconds": int(os.environ.get("REDIS_CACHE_TTL_SECONDS", "5")),  # 30 minutes
                "cache_pool_max_size": int(os.environ.get("REDIS_CACHE_POOL_MAX_SIZE", "20")),
                "cache_namespace": os.environ.get("REDIS_CACHE_NAMESPACE", "main"),
            },
            "custom_oauth_configuration": {
                "secret_key": os.environ.get(
                    "CUSTOM_OAUTH_SECRET_KEY",
                ),
                "algorithm": os.environ.get("CUSTOM_OAUTH_ALGORITHM", "HS256"),
                "access_token_expire_seconds": int(os.environ.get("CUSTOM_OAUTH_ACCESS_TOKEN_EXPIRE_SECONDS", 3600)),
                "refresh_token_expire_seconds": int(os.environ.get("CUSTOM_OAUTH_REFRESH_TOKEN_EXPIRE_SECONDS", 86400)),
                "enable_bootstrap_admin": int(os.environ.get("CUSTOM_OAUTH_BOOTSTRAP_ADMIN", 1)),
                "bootstrap_admin_email": os.environ.get("CUSTOM_OAUTH_BOOTSTRAP_ADMIN_EMAIL"),
                "bootstrap_admin_password": os.environ.get("CUSTOM_OAUTH_BOOTSTRAP_ADMIN_PASSWORD"),
            },
            "audit_log_configuration": {
                "group": os.environ.get("AUDIT_LOG_GROUP", "audit_g"),
                "consumer": os.environ.get("AUDIT_LOG_CONSUMER", f"{socket.gethostname()}:{os.getpid()}"),
                "stream": os.environ.get("AUDIT_LOG_STREAM", "audit:events"),
                # Maximum batch size for bulk processing
                "batch_size": int(os.environ.get("AUDIT_LOG_BATCH_SIZE", 100)),
                # wait up to AUDIT_LOG_BLOCK_MS seconds for new messages
                "block_ms": int(os.environ.get("AUDIT_LOG_BLOCK_MS", 2000)),
                # Minimum batch size before processing (unless timeout)
                "min_batch_size": int(os.environ.get("AUDIT_LOG_MIN_BATCH_SIZE", 5)),
                # Max time to wait before processing any accumulated messages
                "batch_timeout": float(os.environ.get("AUDIT_LOG_BATCH_TIMEOUT", 5.0)),
            },
            "smtp_configuration": {
                "host": os.environ.get("SMTP_HOST", "YOUR_SMTP_HOST"),
                "port": int(os.environ.get("SMTP_PORT", "465")),
                "username": os.environ.get("SMTP_USERNAME", "YOUR_SMTP_USERNAME"),
                "password": os.environ.get("SMTP_PASSWORD", "YOUR_SMTP_PASSWORD"),
                "use_tls": os.environ.get("SMTP_USE_TLS", "True").lower() in ("true", "1", "t"),
                "from_email": os.environ.get("SMTP_FROM_EMAIL", "YOUR_SMTP_FROM_EMAIL"),
                "from_name": os.environ.get("SMTP_FROM_NAME", "YOUR_SMTP_FROM_NAME"),
            },
        }
        self._configuration = ConfigurationModel(**config_obj)
        self._config = configparser.ConfigParser()  # Read the config.ini file
        self._config.read(os.environ.get("CONFIG_INI_PATH"))

    def configuration(self):
        """Returns the configuration"""
        return self._configuration

    def config_ini(self):
        """Returns the config from ini file"""
        return self._config


# Initialize the Configuration instance
# config = Configuration()

# Export the methods as standalone functions
# def get_configuration():
#     return config.configuration()

# def get_config_ini():
#     return config.config_ini()
