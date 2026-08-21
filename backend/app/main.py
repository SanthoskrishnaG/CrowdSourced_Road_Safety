import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager

# Ensure workspace root is in sys.path for ML subsystem import
project_root = str(Path(__file__).resolve().parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.api.v1.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create upload directory if it does not exist
    os.makedirs(settings.UPLOAD_DIRECTORY, exist_ok=True)
    yield
    # Cleanup logic (if any) goes here

app = FastAPI(
    title="AI-Powered Crowdsourced Road Infrastructure Monitoring & Management Platform",
    description=(
        "API backend for reporting, verifying, tracking, and resolving road "
        "infrastructure problems (potholes, streetlights, garbage, etc.)."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Set up CORS middleware (to allow testing from simple frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static upload directory
os.makedirs(settings.UPLOAD_DIRECTORY, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIRECTORY), name="uploads")

# Include API v1 router under /api/v1/
app.include_router(api_router, prefix="/api/v1")



@app.get("/")
def read_root():
    return {
        "message": (
            "Welcome to the AI-Powered Crowdsourced Road Infrastructure Monitoring "
            "& Management Platform API"
        ),
        "docs": "/docs"
    }
