from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker,Session
from database.schemas import Base
import os
"""
from config.settings import (
    DB_NAME,DB_HOST,DB_PASSWORD,DB_PORT,DB_USER,DB_POOL_SIZE,DB_MAX_OVERFLOW,DB_ECHO
)
"""
import logging as logger
logger.basicConfig(logger.INFO)
from contextlib import contextmanager
from dotenv import load_dotenv
load_dotenv()

db_url= os.getenv("DATABASE_URL")

DB_POOL_SIZE = 5
DB_MAX_OVERFLOW = 10
DB_ECHO = True   # while developing
class DatabaseConnection:

    def __init__(self):
        self.localSession=None
        self.db_url=db_url
        self.engine=self.init_db()

    def init_db(self):
        """Create a database connection and session."""
        try:
            self.engine=create_engine(self.db_url,pool_size=DB_POOL_SIZE,max_overflow=DB_MAX_OVERFLOW,echo=DB_ECHO,pool_pre_ping=True)
            self.localSession=sessionmaker(bind=self.engine,expire_on_commit=False)
            from database.schemas import Base
            Base.metadata.create_all(bind=self.engine)
            logger.success("Database Initialized")
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

            
"""
if __name__ == "__main__":
    import uuid
    from datetime import datetime
    from database.schemas import Accounts  
    import  logging  as logger
    logger.basicConfig(logger.INFO)

    # Initialize the database connection
    db = DatabaseConnection()
"""
    