import logging
import os
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from pythonjsonlogger import jsonlogger
from rich.logging import RichHandler


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter for log records."""

    def add_fields(self, log_record, record, message_dict):
        """Add custom fields to the log record."""
        super().add_fields(log_record, record, message_dict)

        span = trace.get_current_span()

        if span and span.is_recording():
            span_context = span.get_span_context()
            log_record["trace_id"] = "{trace:032x}".format(trace=span_context.trace_id)
            log_record["span_id"] = "{span:016x}".format(span=span_context.span_id)
        # else:
        #     log_record["trace_id"] = None
        #     log_record["span_id"] = None

        # Extract span attributes and add them to log record
        if hasattr(span, "_attributes") and span._attributes:
            for key, value in span._attributes.items():
                # Prefix span attributes to avoid conflicts
                log_record[f"span.{key}"] = value

        # Handle multiline messages by adding trace info to each line
        if "exc_info" in message_dict:
            if isinstance(message_dict["exc_info"], str):
                lines = message_dict["exc_info"].split("\n")
                message_dict["exc_info"] = "\n".join([f"[trace_id: {log_record.get('trace_id')}][span_id: {log_record.get('span_id')}] {line}" for line in lines])


class Logger:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        logs_path = Path("./logs")
        logs_dir_path = logs_path.cwd().parent / "logs"
        logs_dir_path.mkdir(exist_ok=True, parents=True)

        self.fmt_file = "%(levelname)4s %(asctime)s [%(filename)s:%(funcName)s:%(lineno)d] %(message)s"
        self.fmt_shell = "%(levelname)-8s %(asctime)4s [%(filename)s:%(funcName)s:%(lineno)d] %(message)s"
        self.fmt_rich = "%(message)s"
        self.fmt_json = CustomJsonFormatter()
        trace.set_tracer_provider(TracerProvider())
        self.tracer = trace.get_tracer(__name__)

        self.rich_shell_handler = RichHandler()
        self.shell_handler = logging.StreamHandler()
        self.file_handler = TimedRotatingFileHandler(logs_dir_path / "logger.log", when="midnight", backupCount=30)
        self.file_handler.suffix = r"%Y-%m-%d.log"

    def set_level(self, logger: logging.Handler, level: int):
        """
        Set the logging level for the specified logger.
        """
        logger.setLevel(level)
        return logger

    def set_formatter(self, logger: logging.Handler, formatter):
        """
        Set the formatter for the specified logger.
        """
        parsed_formatter = logging.Formatter(formatter)
        logger.setFormatter(parsed_formatter)
        return logger

    def set_json_formatter(self, logger: logging.Handler, formatter):
        """
        Set the json formatter for the specified logger.
        """
        logger.setFormatter(formatter)
        return logger

    def add_handler(self, handler: logging.Handler):
        """
        Add a logging handler to the logger.
        """
        self.logger.addHandler(handler)

    def prepare_loggers(self):
        """
        Prepare the loggers for the application.
        """

        # set global level for all logger
        self.set_level(self.logger, os.getenv("LOG_LEVEL", logging.DEBUG))

        # set formatter for handlers & add handlers
        if os.getenv("ENABLE_RICH_LOGGER"):
            self.set_formatter(self.rich_shell_handler, self.fmt_rich)
            self.add_handler(self.rich_shell_handler)
        else:
            self.set_formatter(self.shell_handler, self.fmt_shell)
            self.add_handler(self.shell_handler)

        if os.getenv("ENABLE_JSON_FILELOGGER"):
            self.set_json_formatter(self.file_handler, self.fmt_json)
        else:
            self.set_formatter(self.file_handler, self.fmt_file)

        self.add_handler(self.file_handler)

        return self.logger

    def get_trace(self):
        """
        Get the tracer instance.
        """
        return self.tracer


_logger_instance = Logger()
logger = _logger_instance.prepare_loggers()
tracer = _logger_instance.get_trace()
