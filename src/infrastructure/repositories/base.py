"""
Base repository
"""
import sqlite3
from typing import Any, List, Optional, Tuple
from infrastructure.logging_config import get_logger

logger = get_logger(__name__)

class BaseRepository:
    """Base repository with SQLite connection"""
    
    def __init__(self, db_path: str):
        if not db_path:
            raise ValueError("Database path cannot be empty.")
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Create tables if not exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                default_currency TEXT DEFAULT 'USD',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS wallets (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                owner_id TEXT NOT NULL,
                currency TEXT DEFAULT 'USD',
                current_balance REAL DEFAULT 0,
                icon TEXT,
                color TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (owner_id) REFERENCES users(id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                icon TEXT,
                color TEXT,
                is_system INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS labels (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                color TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(user_id, name)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id TEXT PRIMARY KEY,
                wallet_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                category_id TEXT,
                type TEXT NOT NULL,
                amount REAL NOT NULL,
                currency TEXT NOT NULL,
                date TEXT NOT NULL,
                note TEXT,
                to_wallet_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (wallet_id) REFERENCES wallets(id),
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (category_id) REFERENCES categories(id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_analyses (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                analysis_type TEXT NOT NULL,
                result TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def get_connection(self) -> sqlite3.Connection:
        """Get database connection"""
        return sqlite3.connect(self.db_path)
    
    def execute(self, query: str, params: Tuple = ()) -> sqlite3.Cursor:
        """Execute query"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        conn.close()
        return cursor
    
    def fetch_one(self, query: str, params: Tuple = ()) -> Optional[dict]:
        """Fetch one result"""
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, params)
        result = cursor.fetchone()
        conn.close()
        return dict(result) if result else None
    
    def fetch_all(self, query: str, params: Tuple = ()) -> List[dict]:
        """Fetch all results"""
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        return [dict(row) for row in results]
