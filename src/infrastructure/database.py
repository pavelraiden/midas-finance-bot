"""
Database abstraction layer for SQLite.
"""
import sqlite3
from typing import List, Optional, Any
from infrastructure.logging_config import get_logger

logger = get_logger(__name__)


class Database:
    """SQLite database wrapper"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.connection = None
        self._connect()
    
    def _connect(self):
        """Create database connection"""
        try:
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row
            logger.info(f"Connected to database: {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def execute(self, query: str, params: tuple = None) -> sqlite3.Cursor:
        """Execute a query"""
        try:
            cursor = self.connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            self.connection.commit()
            return cursor
        except Exception as e:
            logger.error(f"Query execution failed: {e}\nQuery: {query}\nParams: {params}")
            raise
    
    def fetch_one(self, query: str, params: tuple = None) -> Optional[sqlite3.Row]:
        """Fetch one row"""
        cursor = self.execute(query, params)
        return cursor.fetchone()
    
    def fetch_all(self, query: str, params: tuple = None) -> List[sqlite3.Row]:
        """Fetch all rows"""
        cursor = self.execute(query, params)
        return cursor.fetchall()
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")
