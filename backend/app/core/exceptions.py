from typing import Any, Optional, Dict
from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("app.exceptions")


def format_error_response(
    status_code: int,
    code: str,
    message: str,
    details: Optional[Any] = None
) -> JSONResponse:
    """
    Standardizes error responses across all API endpoints while maintaining
    full backward compatibility with FastAPI detail convention.
    """
    content = {
        "success": False,
        "detail": message,
        "error": {
            "code": code,
            "message": message,
            "details": details
        }
    }
    return JSONResponse(status_code=status_code, content=content)


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """
    Handles FastAPI / Starlette HTTPExceptions.
    """
    # Map status code to standard string code
    code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        409: "CONFLICT",
        413: "PAYLOAD_TOO_LARGE",
        422: "UNPROCESSABLE_ENTITY",
        429: "RATE_LIMIT_EXCEEDED",
        500: "INTERNAL_SERVER_ERROR",
    }

    code = code_map.get(exc.status_code, f"HTTP_{exc.status_code}")
    message = str(exc.detail) if exc.detail else "An error occurred."
    
    logger.warning(f"HTTP Exception [{exc.status_code} - {code}]: {message} at {request.url.path}")
    return format_error_response(status_code=exc.status_code, code=code, message=message)


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handles Pydantic request validation errors.
    """
    errors = exc.errors()
    simplified_errors = []
    for err in errors:
        loc = " -> ".join([str(l) for l in err.get("loc", [])])
        msg = err.get("msg", "Invalid value")
        simplified_errors.append({"field": loc, "message": msg})

    logger.warning(f"Validation Error at {request.url.path}: {simplified_errors}")
    return format_error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="VALIDATION_ERROR",
        message="Request validation failed. Please check input parameters.",
        details=simplified_errors
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catches any unhandled exceptions and prevents stack trace leakage in production.
    """
    logger.exception(f"Unhandled Server Error at {request.url.path}: {str(exc)}")

    # In development, provide message detail; in production, keep generic
    if settings.ENVIRONMENT == "development" or settings.DEBUG:
        message = f"Internal server error: {str(exc)}"
        details = {"exception_type": exc.__class__.__name__}
    else:
        message = "An unexpected server error occurred. Please contact system administrator."
        details = None

    return format_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="INTERNAL_SERVER_ERROR",
        message=message,
        details=details
    )
