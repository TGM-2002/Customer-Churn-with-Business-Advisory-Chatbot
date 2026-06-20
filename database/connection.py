#database/connection.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker,Session
from database.schemas import Base
import os

from config.settings import DATABASE_URL,DB_POOL_SIZE,DB_MAX_OVERFLOW,DB_ECHO
import logging as logger
logger.basicConfig(
    level=logger.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
from contextlib import contextmanager

class DatabaseConnection:

    def __init__(self):
        self.localSession=None
        self.db_url=DATABASE_URL
        self.engine=self.init_db()

    def init_db(self):
        """Create a database connection and session."""
        try:
            self.engine=create_engine(self.db_url,pool_size=DB_POOL_SIZE,max_overflow=DB_MAX_OVERFLOW,echo=DB_ECHO,pool_pre_ping=True)
            self.localSession=sessionmaker(bind=self.engine,expire_on_commit=False)
            from database.schemas import Base
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database Initialized")
            return self.engine
        except Exception as e:
            logger.error(f"Failed to Initialize DB:{e}")
            raise

    @contextmanager
    def get_db(self):
        session=self.localSession()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database Error : {e}")
            raise
        finally:
            session.close()

            
