import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager

# Ensure workspace root is in sys.path for ML subsystem import
project_root = str(Path(__file__).resolve().parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.core.middleware import SecurityHeadersMiddleware, RateLimiterMiddleware, RequestLoggingMiddleware
from app.core.exceptions import (
    http_exception_handler,
    validation_exception_handler,
    unhandled_exception_handler
)
from app.api.v1.router import api_router

# Initialize structured logging
setup_logging()
logger = get_logger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure upload directory exists
    os.makedirs(settings.UPLOAD_DIRECTORY, exist_ok=True)
    logger.info(f"Road Infrastructure Platform starting in [{settings.ENVIRONMENT.upper()}] mode.")
    yield
    # Shutdown logic
    logger.info("Road Infrastructure Platform shutting down.")


app = FastAPI(
    title="AI-Powered Crowdsourced Road Infrastructure Monitoring & Management Platform",
    description=(
        "Production-ready API backend for reporting, verifying, tracking, prioritizing, "
        "and resolving municipal road infrastructure hazards (potholes, streetlights, garbage, flooding, etc.)."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Exception Handlers for consistent API error responses
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

# Register Middlewares (Order of execution: RequestLogging -> RateLimiter -> SecurityHeaders -> CORS)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RateLimiterMiddleware, requests_per_minute=settings.RATE_LIMIT_PER_MINUTE)
app.add_middleware(SecurityHeadersMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static upload directory for evidence assets
os.makedirs(settings.UPLOAD_DIRECTORY, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIRECTORY), name="uploads")

# Include API v1 router under /api/v1/
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
def read_root():
    return {
        "name": "AI-Powered Crowdsourced Road Infrastructure Monitoring & Management Platform",
        "message": (
            "Welcome to the AI-Powered Crowdsourced Road Infrastructure Monitoring "
            "& Management Platform API"
        ),
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "docs": "/docs",
        "health": "/api/v1/health/healthz"
    }
