"""
Balance Snapshot Domain Entity.

Представляет snapshot баланса кошелька в конкретный момент времени.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from decimal import Decimal


@dataclass
class BalanceSnapshot:
    """
    Snapshot баланса кошелька.
    
    Используется для balance-based transaction detection:
    - Сохраняем balance каждый час
    - Вычисляем delta между snapshots
    - Детектируем transactions по изменению баланса
    """
    
    id: Optional[str]
    wallet_id: str
    currency: str
    balance: Decimal
    timestamp: datetime
    source: str  # 'blockchain', 'api', 'manual'
    
    # Metadata
    block_number: Optional[int] = None
    chain_id: Optional[str] = None
    
    # Calculated fields
    previous_balance: Optional[Decimal] = None
    delta: Optional[Decimal] = None
    
    def __post_init__(self):
        """Validate and calculate fields."""
        if self.balance < 0:
            raise ValueError(f"Balance cannot be negative: {self.balance}")
        
        # Calculate delta if previous_balance is set
        if self.previous_balance is not None:
            self.delta = self.balance - self.previous_balance
    
    def has_changed(self, threshold: Decimal = Decimal("0.01")) -> bool:
        """
        Проверяет, изменился ли баланс значительно.
        
        Args:
            threshold: Минимальное изменение для детекции
        
        Returns:
            True if balance changed significantly
        """
        if self.delta is None:
            return False
        
        return abs(self.delta) >= threshold
    
    def is_decrease(self) -> bool:
        """Проверяет, уменьшился ли баланс (expense)."""
        return self.delta is not None and self.delta < 0
    
    def is_increase(self) -> bool:
        """Проверяет, увеличился ли баланс (income)."""
        return self.delta is not None and self.delta > 0
    
    def to_dict(self) -> dict:
        """Converts to dict."""
        return {
            "id": self.id,
            "wallet_id": self.wallet_id,
            "currency": self.currency,
            "balance": float(self.balance),
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "block_number": self.block_number,
            "chain_id": self.chain_id,
            "previous_balance": float(self.previous_balance) if self.previous_balance else None,
            "delta": float(self.delta) if self.delta else None,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'BalanceSnapshot':
        """Creates from dict."""
        return cls(
            id=data.get("id"),
            wallet_id=data["wallet_id"],
            currency=data["currency"],
            balance=Decimal(str(data["balance"])),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            source=data["source"],
            block_number=data.get("block_number"),
            chain_id=data.get("chain_id"),
            previous_balance=Decimal(str(data["previous_balance"])) if data.get("previous_balance") else None,
            delta=Decimal(str(data["delta"])) if data.get("delta") else None,
        )


@dataclass
class BalanceDelta:
    """
    Представляет изменение баланса между двумя snapshots.
    
    Используется для детекции transactions.
    """
    
    wallet_id: str
    currency: str
    
    # Snapshots
    from_snapshot: BalanceSnapshot
    to_snapshot: BalanceSnapshot
    
    # Delta
    amount: Decimal
    time_diff: float  # seconds
    
    # Confidence
    confidence: float  # 0.0 - 1.0
    
    def __post_init__(self):
        """Calculate delta and confidence."""
        self.amount = self.to_snapshot.balance - self.from_snapshot.balance
        
        # Calculate time difference
        time_delta = self.to_snapshot.timestamp - self.from_snapshot.timestamp
        self.time_diff = time_delta.total_seconds()
        
        # Calculate confidence based on time diff
        # Shorter time = higher confidence
        if self.time_diff <= 3600:  # 1 hour
            self.confidence = 0.9
        elif self.time_diff <= 7200:  # 2 hours
            self.confidence = 0.8
        elif self.time_diff <= 14400:  # 4 hours
            self.confidence = 0.7
        else:
            self.confidence = 0.6
    
    def is_expense(self) -> bool:
        """Проверяет, это expense (баланс уменьшился)."""
        return self.amount < 0
    
    def is_income(self) -> bool:
        """Проверяет, это income (баланс увеличился)."""
        return self.amount > 0
    
    def abs_amount(self) -> Decimal:
        """Возвращает абсолютное значение amount."""
        return abs(self.amount)
    
    def to_dict(self) -> dict:
        """Converts to dict."""
        return {
            "wallet_id": self.wallet_id,
            "currency": self.currency,
            "from_snapshot": self.from_snapshot.to_dict(),
            "to_snapshot": self.to_snapshot.to_dict(),
            "amount": float(self.amount),
            "time_diff": self.time_diff,
            "confidence": self.confidence,
        }
