"""
Unit tests for BalanceSnapshot domain entity.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from domain.balance.balance_snapshot import BalanceSnapshot, BalanceDelta


@pytest.mark.unit
@pytest.mark.balance_detection
class TestBalanceSnapshot:
    """Tests for BalanceSnapshot."""
    
    def test_create_balance_snapshot(self, sample_wallet_id, sample_balance, sample_timestamp):
        """Test creating a balance snapshot."""
        snapshot = BalanceSnapshot(
            id="snap-123",
            wallet_id=sample_wallet_id,
            currency="USDC",
            balance=sample_balance,
            timestamp=sample_timestamp,
            source="blockchain"
        )
        
        assert snapshot.id == "snap-123"
        assert snapshot.wallet_id == sample_wallet_id
        assert snapshot.currency == "USDC"
        assert snapshot.balance == sample_balance
        assert snapshot.timestamp == sample_timestamp
        assert snapshot.source == "blockchain"
    
    def test_balance_snapshot_with_delta(self, sample_wallet_id, sample_timestamp):
        """Test balance snapshot with previous balance and delta."""
        snapshot = BalanceSnapshot(
            id="snap-123",
            wallet_id=sample_wallet_id,
            currency="USDC",
            balance=Decimal("505.00"),
            timestamp=sample_timestamp,
            source="blockchain",
            previous_balance=Decimal("612.00")
        )
        
        assert snapshot.delta == Decimal("-107.00")
    
    def test_has_changed_true(self, sample_wallet_id, sample_timestamp):
        """Test has_changed returns True for significant change."""
        snapshot = BalanceSnapshot(
            id="snap-123",
            wallet_id=sample_wallet_id,
            currency="USDC",
            balance=Decimal("505.00"),
            timestamp=sample_timestamp,
            source="blockchain",
            previous_balance=Decimal("612.00")
        )
        
        assert snapshot.has_changed(threshold=Decimal("1.00")) is True
    
    def test_has_changed_false(self, sample_wallet_id, sample_timestamp):
        """Test has_changed returns False for insignificant change."""
        snapshot = BalanceSnapshot(
            id="snap-123",
            wallet_id=sample_wallet_id,
            currency="USDC",
            balance=Decimal("612.00"),
            timestamp=sample_timestamp,
            source="blockchain",
            previous_balance=Decimal("612.005")
        )
        
        assert snapshot.has_changed(threshold=Decimal("0.01")) is False
    
    def test_is_decrease(self, sample_wallet_id, sample_timestamp):
        """Test is_decrease returns True for balance decrease."""
        snapshot = BalanceSnapshot(
            id="snap-123",
            wallet_id=sample_wallet_id,
            currency="USDC",
            balance=Decimal("505.00"),
            timestamp=sample_timestamp,
            source="blockchain",
            previous_balance=Decimal("612.00")
        )
        
        assert snapshot.is_decrease() is True
        assert snapshot.is_increase() is False
    
    def test_is_increase(self, sample_wallet_id, sample_timestamp):
        """Test is_increase returns True for balance increase."""
        snapshot = BalanceSnapshot(
            id="snap-123",
            wallet_id=sample_wallet_id,
            currency="USDC",
            balance=Decimal("700.00"),
            timestamp=sample_timestamp,
            source="blockchain",
            previous_balance=Decimal("612.00")
        )
        
        assert snapshot.is_increase() is True
        assert snapshot.is_decrease() is False
    
    def test_to_dict(self, sample_wallet_id, sample_timestamp):
        """Test converting snapshot to dict."""
        snapshot = BalanceSnapshot(
            id="snap-123",
            wallet_id=sample_wallet_id,
            currency="USDC",
            balance=Decimal("612.50"),
            timestamp=sample_timestamp,
            source="blockchain",
            previous_balance=Decimal("600.00")
        )
        
        data = snapshot.to_dict()
        
        assert data["id"] == "snap-123"
        assert data["wallet_id"] == sample_wallet_id
        assert data["currency"] == "USDC"
        assert data["balance"] == 612.50
        assert data["previous_balance"] == 600.00
        assert data["delta"] == 12.50
    
    def test_from_dict(self, sample_wallet_id, sample_timestamp):
        """Test creating snapshot from dict."""
        data = {
            "id": "snap-123",
            "wallet_id": sample_wallet_id,
            "currency": "USDC",
            "balance": 612.50,
            "timestamp": sample_timestamp.isoformat(),
            "source": "blockchain",
            "previous_balance": 600.00,
            "delta": 12.50
        }
        
        snapshot = BalanceSnapshot.from_dict(data)
        
        assert snapshot.id == "snap-123"
        assert snapshot.wallet_id == sample_wallet_id
        assert snapshot.balance == Decimal("612.50")
    
    def test_negative_balance_raises_error(self, sample_wallet_id, sample_timestamp):
        """Test that negative balance raises ValueError."""
        with pytest.raises(ValueError, match="Balance cannot be negative"):
            BalanceSnapshot(
                id="snap-123",
                wallet_id=sample_wallet_id,
                currency="USDC",
                balance=Decimal("-100.00"),
                timestamp=sample_timestamp,
                source="blockchain"
            )


@pytest.mark.unit
@pytest.mark.balance_detection
class TestBalanceDelta:
    """Tests for BalanceDelta."""
    
    def test_create_balance_delta(self, sample_wallet_id):
        """Test creating a balance delta."""
        from_snapshot = BalanceSnapshot(
            id="snap-1",
            wallet_id=sample_wallet_id,
            currency="USDC",
            balance=Decimal("612.00"),
            timestamp=datetime(2025, 11, 30, 12, 0, 0),
            source="blockchain"
        )
        
        to_snapshot = BalanceSnapshot(
            id="snap-2",
            wallet_id=sample_wallet_id,
            currency="USDC",
            balance=Decimal("505.00"),
            timestamp=datetime(2025, 11, 30, 13, 0, 0),
            source="blockchain"
        )
        
        delta = BalanceDelta(
            wallet_id=sample_wallet_id,
            currency="USDC",
            from_snapshot=from_snapshot,
            to_snapshot=to_snapshot,
            amount=Decimal(0),  # Calculated in __post_init__
            time_diff=0.0,  # Calculated in __post_init__
            confidence=0.0  # Calculated in __post_init__
        )
        
        assert delta.amount == Decimal("-107.00")
        assert delta.time_diff == 3600.0  # 1 hour
        assert delta.confidence == 0.9  # High confidence for 1-hour window
    
    def test_is_expense(self, sample_wallet_id):
        """Test is_expense returns True for balance decrease."""
        from_snapshot = BalanceSnapshot(
            id="snap-1",
            wallet_id=sample_wallet_id,
            currency="USDC",
            balance=Decimal("612.00"),
            timestamp=datetime(2025, 11, 30, 12, 0, 0),
            source="blockchain"
        )
        
        to_snapshot = BalanceSnapshot(
            id="snap-2",
            wallet_id=sample_wallet_id,
            currency="USDC",
            balance=Decimal("505.00"),
            timestamp=datetime(2025, 11, 30, 13, 0, 0),
            source="blockchain"
        )
        
        delta = BalanceDelta(
            wallet_id=sample_wallet_id,
            currency="USDC",
            from_snapshot=from_snapshot,
            to_snapshot=to_snapshot,
            amount=Decimal(0),
            time_diff=0.0,
            confidence=0.0
        )
        
        assert delta.is_expense() is True
        assert delta.is_income() is False
    
    def test_is_income(self, sample_wallet_id):
        """Test is_income returns True for balance increase."""
        from_snapshot = BalanceSnapshot(
            id="snap-1",
            wallet_id=sample_wallet_id,
            currency="USDC",
            balance=Decimal("505.00"),
            timestamp=datetime(2025, 11, 30, 12, 0, 0),
            source="blockchain"
        )
        
        to_snapshot = BalanceSnapshot(
            id="snap-2",
            wallet_id=sample_wallet_id,
            currency="USDC",
            balance=Decimal("612.00"),
            timestamp=datetime(2025, 11, 30, 13, 0, 0),
            source="blockchain"
        )
        
        delta = BalanceDelta(
            wallet_id=sample_wallet_id,
            currency="USDC",
            from_snapshot=from_snapshot,
            to_snapshot=to_snapshot,
            amount=Decimal(0),
            time_diff=0.0,
            confidence=0.0
        )
        
        assert delta.is_income() is True
        assert delta.is_expense() is False
    
    def test_abs_amount(self, sample_wallet_id):
        """Test abs_amount returns absolute value."""
        from_snapshot = BalanceSnapshot(
            id="snap-1",
            wallet_id=sample_wallet_id,
            currency="USDC",
            balance=Decimal("612.00"),
            timestamp=datetime(2025, 11, 30, 12, 0, 0),
            source="blockchain"
        )
        
        to_snapshot = BalanceSnapshot(
            id="snap-2",
            wallet_id=sample_wallet_id,
            currency="USDC",
            balance=Decimal("505.00"),
            timestamp=datetime(2025, 11, 30, 13, 0, 0),
            source="blockchain"
        )
        
        delta = BalanceDelta(
            wallet_id=sample_wallet_id,
            currency="USDC",
            from_snapshot=from_snapshot,
            to_snapshot=to_snapshot,
            amount=Decimal(0),
            time_diff=0.0,
            confidence=0.0
        )
        
        assert delta.abs_amount() == Decimal("107.00")
    
    def test_confidence_calculation(self, sample_wallet_id):
        """Test confidence calculation based on time diff."""
        # Test 1 hour window (high confidence)
        from_snapshot_1h = BalanceSnapshot(
            id="snap-1",
            wallet_id=sample_wallet_id,
            currency="USDC",
            balance=Decimal("612.00"),
            timestamp=datetime(2025, 11, 30, 12, 0, 0),
            source="blockchain"
        )
        
        to_snapshot_1h = BalanceSnapshot(
            id="snap-2",
            wallet_id=sample_wallet_id,
            currency="USDC",
            balance=Decimal("505.00"),
            timestamp=datetime(2025, 11, 30, 13, 0, 0),
            source="blockchain"
        )
        
        delta_1h = BalanceDelta(
            wallet_id=sample_wallet_id,
            currency="USDC",
            from_snapshot=from_snapshot_1h,
            to_snapshot=to_snapshot_1h,
            amount=Decimal(0),
            time_diff=0.0,
            confidence=0.0
        )
        
        assert delta_1h.confidence == 0.9
        
        # Test 5 hour window (lower confidence)
        to_snapshot_5h = BalanceSnapshot(
            id="snap-3",
            wallet_id=sample_wallet_id,
            currency="USDC",
            balance=Decimal("505.00"),
            timestamp=datetime(2025, 11, 30, 17, 0, 0),
            source="blockchain"
        )
        
        delta_5h = BalanceDelta(
            wallet_id=sample_wallet_id,
            currency="USDC",
            from_snapshot=from_snapshot_1h,
            to_snapshot=to_snapshot_5h,
            amount=Decimal(0),
            time_diff=0.0,
            confidence=0.0
        )
        
        assert delta_5h.confidence == 0.6
