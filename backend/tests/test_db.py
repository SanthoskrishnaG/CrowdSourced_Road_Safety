import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from app.core.database import engine


def test_database_connection():
    """
    Verifies that the application can successfully connect to the configured
    PostgreSQL database and execute a query. Skips if database is unreachable.
    """
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1")).scalar()
            assert result == 1
    except OperationalError as e:
        pytest.skip(f"Database at {engine.url} is unreachable. Skipping integration test: {e}")
    except Exception as e:
        raise AssertionError(f"Database test encountered an unexpected error on {engine.url}: {e}")

