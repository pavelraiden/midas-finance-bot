"""
Transaction domain entity
"""
from enum import Enum
from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime, date, time
from decimal import Decimal

class TransactionType(str, Enum):
    """Transaction type enum"""
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"

@dataclass
class Transaction:
    """Transaction entity"""
    id: str
    wallet_id: str
    user_id: str
    category_id: Optional[str]
    type: TransactionType
    amount: Decimal
    currency: str
    date: date
    time: Optional[time] = None
    note: Optional[str] = None
    to_wallet_id: Optional[str] = None
    source_type: Optional[str] = None
    source_id: Optional[str] = None
    merchant_name: Optional[str] = None
    attachment_urls: Optional[List[str]] = None
    is_recurring: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
