"""
Wallet repository
"""
from typing import Optional, List
from datetime import datetime
import uuid

from .base import BaseRepository


class WalletRepository(BaseRepository):
    """Wallet repository."""
    
    def create_wallet(
        self,
        name: str,
        owner_id: str,
        currency: str = "USD",
        icon: Optional[str] = None,
        color: Optional[str] = None
    ) -> str:
        """Create a new wallet."""
        wallet_id = f"wallet_{owner_id}_default"
        
        query = """
            INSERT OR REPLACE INTO wallets (id, name, owner_id, currency, current_balance, icon, color)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        
        self.execute(query, (wallet_id, name, owner_id, currency, 0.0, icon, color))
        return wallet_id
    
    def get_wallet_by_id(self, wallet_id: str) -> Optional[dict]:
        """Get wallet by ID."""
        query = "SELECT * FROM wallets WHERE id = ?"
        return self.fetch_one(query, (wallet_id,))
    
    def get_user_wallets(self, owner_id: str) -> List[dict]:
        """Get all wallets for a user."""
        query = "SELECT * FROM wallets WHERE owner_id = ? ORDER BY created_at"
        return self.fetch_all(query, (owner_id,))
    
    def update_balance(self, wallet_id: str, new_balance: float):
        """Update wallet balance."""
        query = "UPDATE wallets SET current_balance = ? WHERE id = ?"
        self.execute(query, (new_balance, wallet_id))
