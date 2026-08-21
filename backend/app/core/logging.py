import sys
import logging
from typing import Any, Dict
from app.core.config import settings

# Sensitive keys to redact if ever passed in log contexts
SENSITIVE_KEYS = {"password", "token", "access_token", "secret", "authorization", "secret_key"}


class StructuredFormatter(logging.Formatter):
    """
    Structured application log formatter with contextual field formatting
    and automatic redaction of sensitive credentials.
    """
    def format(self, record: logging.LogRecord) -> str:
        # Mask sensitive attributes in record.__dict__
        for k in SENSITIVE_KEYS:
            if hasattr(record, k):
                setattr(record, k, "***REDACTED***")

        timestamp = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        level = record.levelname
        module = record.name
        message = record.getMessage()

        # Check for any extra attributes
        extras = {
            k: v for k, v in record.__dict__.items()
            if k not in logging.LogRecord("", 0, "", 0, "", (), None).__dict__
            and not k.startswith("_")
            and k not in SENSITIVE_KEYS
        }

        extra_str = f" | {extras}" if extras else ""
        return f"[{timestamp}] [{level}] [{module}]: {message}{extra_str}"


def setup_logging():
    """
    Initializes application root and module loggers.
    """
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers to avoid duplicate output
    root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    handler.setFormatter(StructuredFormatter())
    root_logger.addHandler(handler)

    # Silence verbose third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("passlib").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Returns a configured logger instance for a given module name.
    """
    return logging.getLogger(name)
