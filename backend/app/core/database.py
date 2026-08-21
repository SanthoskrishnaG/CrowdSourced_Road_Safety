
from typing import Generator
# pyrefly: ignore [missing-import]
from sqlalchemy import create_engine
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# Create engine
# If using postgresql, we might need pool configurations
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # Check if connection is alive before using
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative base
Base = declarative_base()


def get_db() -> Generator:
    """
    Dependency generator for database sessions.
    Ensures that session is closed after the request lifecycle.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
