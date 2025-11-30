"""Transaction repository."""
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
import uuid
import json

from .base import BaseRepository
from domain.transaction import Transaction, TransactionType


class TransactionRepository(BaseRepository):
    """Transaction repository."""
    
    def create_transaction(
        self,
        wallet_id: str,
        user_id: str,
        category_id: str,
        type: TransactionType,
        amount: Decimal,
        currency: str,
        date: datetime,
        note: Optional[str] = None,
        label_ids: Optional[List[str]] = None
    ) -> Transaction:
        """Create a new transaction."""
        transaction_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        query = """
            INSERT INTO transactions (
                id, wallet_id, user_id, category_id, type,
                amount, currency, date, note, label_ids,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        self.execute(query, (
            transaction_id, wallet_id, user_id, category_id, type.value,
            str(amount), currency, date.isoformat(), note,
            json.dumps(label_ids or []),
            now.isoformat(), now.isoformat()
        ))
        
        return Transaction(
            id=transaction_id,
            wallet_id=wallet_id,
            user_id=user_id,
            category_id=category_id,
            type=type,
            amount=amount,
            currency=currency,
            date=date,
            note=note,
            label_ids=label_ids or [],
            created_at=now,
            updated_at=now
        )
    
    def get_transaction_by_id(self, transaction_id: str) -> Optional[Transaction]:
        """Get transaction by ID."""
        query = "SELECT * FROM transactions WHERE id = ?"
        row = self.fetch_one(query, (transaction_id,))
        
        if not row:
            return None
        
        return Transaction(
            id=row["id"],
            wallet_id=row["wallet_id"],
            user_id=row["user_id"],
            category_id=row["category_id"],
            type=TransactionType(row["type"]),
            amount=Decimal(row["amount"]),
            currency=row["currency"],
            date=datetime.fromisoformat(row["date"]),
            note=row["note"],
            label_ids=json.loads(row["label_ids"]) if row["label_ids"] else [],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"])
        )
    
    def get_wallet_transactions(self, wallet_id: str, limit: int = 100) -> List[Transaction]:
        """Get all transactions for a wallet."""
        query = """
            SELECT * FROM transactions 
            WHERE wallet_id = ? 
            ORDER BY date DESC, created_at DESC 
            LIMIT ?
        """
        rows = self.fetch_all(query, (wallet_id, limit))
        
        return [
            Transaction(
                id=row["id"],
                wallet_id=row["wallet_id"],
                user_id=row["user_id"],
                category_id=row["category_id"],
                type=TransactionType(row["type"]),
                amount=Decimal(row["amount"]),
                currency=row["currency"],
                date=datetime.fromisoformat(row["date"]),
                note=row["note"],
                label_ids=json.loads(row["label_ids"]) if row["label_ids"] else [],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"])
            )
            for row in rows
        ]
    
    def delete_transaction(self, transaction_id: str) -> None:
        """Delete a transaction."""
        query = "DELETE FROM transactions WHERE id = ?"
        self.execute(query, (transaction_id,))

    def count_by_category(self, category_id: str) -> int:
        """Count transactions by category."""
        query = "SELECT COUNT(*) as count FROM transactions WHERE category_id = ?"
        row = self.fetch_one(query, (category_id,))
        return row["count"] if row else 0
    
    def sum_by_category(self, category_id: str) -> Decimal:
        """Sum transaction amounts by category."""
        query = "SELECT SUM(CAST(amount AS REAL)) as total FROM transactions WHERE category_id = ?"
        row = self.fetch_one(query, (category_id,))
        return Decimal(str(row["total"])) if row and row["total"] else Decimal("0")

    def get_user_transactions(self, user_id: str, limit: int = 1000) -> List[Transaction]:
        """Get all transactions for a user."""
        query = """
            SELECT * FROM transactions 
            WHERE user_id = ? 
            ORDER BY date DESC, created_at DESC 
            LIMIT ?
        """
        rows = self.fetch_all(query, (user_id, limit))
        
        return [
            Transaction(
                id=row["id"],
                wallet_id=row["wallet_id"],
                user_id=row["user_id"],
                category_id=row["category_id"],
                type=TransactionType(row["type"]),
                amount=Decimal(row["amount"]),
                currency=row["currency"],
                date=datetime.fromisoformat(row["date"]),
                note=row["note"],
                label_ids=json.loads(row["label_ids"]) if row["label_ids"] else [],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"])
            )
            for row in rows
        ]
