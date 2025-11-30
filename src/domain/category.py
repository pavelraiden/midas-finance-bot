"""
Category domain entity
"""
from enum import Enum
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

class CategoryType(str, Enum):
    """Category type enum"""
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"

@dataclass
class Category:
    """Category entity"""
    id: str
    user_id: Optional[str]
    name: str
    type: CategoryType
    icon: Optional[str] = None
    color: Optional[str] = None
    parent_id: Optional[str] = None
    is_system: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
