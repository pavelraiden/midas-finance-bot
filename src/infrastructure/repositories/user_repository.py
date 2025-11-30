"""
User repository
"""
from typing import Optional
from datetime import datetime
import uuid

from .base import BaseRepository


class UserRepository(BaseRepository):
    """User repository."""
    
    def create_user(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        default_currency: str = "USD"
    ) -> str:
        """Create a new user."""
        user_id = f"user_{telegram_id}"
        
        query = """
            INSERT OR REPLACE INTO users (id, telegram_id, username, first_name, last_name, default_currency)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        
        self.execute(query, (user_id, telegram_id, username, first_name, last_name, default_currency))
        return user_id
    
    def get_user_by_telegram_id(self, telegram_id: int) -> Optional[dict]:
        """Get user by Telegram ID."""
        query = "SELECT * FROM users WHERE telegram_id = ?"
        return self.fetch_one(query, (telegram_id,))
    
    def get_user_by_id(self, user_id: str) -> Optional[dict]:
        """Get user by ID."""
        query = "SELECT * FROM users WHERE id = ?"
        return self.fetch_one(query, (user_id,))
