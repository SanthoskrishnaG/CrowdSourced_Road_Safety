from sqlalchemy import text
from app.core.database import engine


def test_database_connection():
    """
    Verifies that the application can successfully connect to the configured
    PostgreSQL database and execute a query.
    """
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1")).scalar()
            assert result == 1
    except Exception as e:
        # If the DB is not yet running (e.g. running tests locally before docker compose up),
        # this test will raise an error, which is correct because the DB must be reachable.
        raise AssertionError(f"Could not connect to database on {engine.url}: {e}")
