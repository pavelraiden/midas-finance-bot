"""
Label domain entity
"""
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class Label:
    """Label entity"""
    id: str
    user_id: str
    name: str
    color: Optional[str] = None
    created_at: Optional[datetime] = None
