from database.connection import DatabaseConnection

_db_conn = DatabaseConnection()


def get_db():
    """FastAPI dependency that yields a SQLAlchemy session per request."""
    with _db_conn.get_db() as session:
        yield session
