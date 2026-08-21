import time
import collections
from typing import Dict, Deque
from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("app.middleware")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Applies production security headers to all HTTP responses.
    """
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)

        # Basic XSS and sniffing protection
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # HSTS in production environments
        if settings.ENVIRONMENT == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    In-memory sliding window rate limiter per client IP address.
    """
    def __init__(self, app, requests_per_minute: int = 120):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.client_records: Dict[str, Deque[float]] = collections.defaultdict(collections.deque)

    async def dispatch(self, request: Request, call_next):
        # Exclude testing environment, health check, and static assets from rate limiting
        if settings.ENVIRONMENT == "testing":
            return await call_next(request)

        path = request.url.path
        if path.startswith("/api/v1/health") or path.startswith("/uploads") or path == "/":
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        if client_ip == "testclient":
            return await call_next(request)
        now = time.time()
        window_start = now - 60.0

        # Clean old timestamps
        timestamps = self.client_records[client_ip]
        while timestamps and timestamps[0] < window_start:
            timestamps.popleft()

        if len(timestamps) >= self.requests_per_minute:
            logger.warning(f"Rate limit exceeded for client IP: {client_ip} on path: {path}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "success": False,
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Too many requests. Please slow down.",
                        "details": {"retry_after_seconds": 60}
                    }
                },
                headers={"Retry-After": "60"}
            )

        timestamps.append(now)
        return await call_next(request)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Logs API request lifecycle, HTTP method, path, status code, and latency in milliseconds.
    """
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        duration_ms = round((time.time() - start_time) * 1000, 2)

        # Log request at appropriate log level
        client_ip = request.client.host if request.client else "unknown"
        if response.status_code >= 400:
            logger.warning(
                f"{request.method} {request.url.path} returned {response.status_code} ({duration_ms}ms) from IP {client_ip}"
            )
        else:
            logger.info(
                f"{request.method} {request.url.path} returned {response.status_code} ({duration_ms}ms)"
            )

        response.headers["X-Process-Time"] = f"{duration_ms}ms"
        return response
