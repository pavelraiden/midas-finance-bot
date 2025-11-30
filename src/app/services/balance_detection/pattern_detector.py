"""
Pattern Detector для специфичных transaction patterns.

Детектирует:
- USDT→USDC swaps (Trustee Card top-up)
- USDC→EUR card payments
- Inter-wallet transfers
"""

import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal

from src.domain.balance.balance_snapshot import BalanceDelta
from src.infrastructure.repositories.transaction_repository import TransactionRepository

logger = logging.getLogger(__name__)


class PatternDetector:
    """
    Service для детекции transaction patterns.
    
    Patterns:
    1. USDT→USDC Swap (Trustee Card top-up)
       - USDT balance decrease
       - USDC balance increase
       - Time window: 1-30 minutes
       - Amount matching (with fees)
    
    2. USDC→EUR Card Payment
       - USDC balance decrease
       - No corresponding blockchain transaction
       - Pattern: internal Trustee operation
    
    3. Inter-wallet Transfer
       - Balance decrease in wallet A
       - Balance increase in wallet B
       - Same user
       - Time window: 1-30 minutes
    """
    
    def __init__(
        self,
        transaction_repo: TransactionRepository
    ):
        """
        Инициализация pattern detector.
        
        Args:
            transaction_repo: TransactionRepository
        """
        self.transaction_repo = transaction_repo
        
        # Configuration
        self.swap_time_window = 30 * 60  # 30 minutes in seconds
        self.transfer_time_window = 30 * 60  # 30 minutes
        self.amount_tolerance = Decimal("0.05")  # 5% tolerance for fees
        
        logger.info("PatternDetector initialized")
    
    async def detect_swap_pattern(
        self,
        usdt_delta: BalanceDelta,
        usdc_delta: BalanceDelta
    ) -> Optional[Dict[str, Any]]:
        """
        Детектирует USDT→USDC swap pattern.
        
        Args:
            usdt_delta: USDT balance change
            usdc_delta: USDC balance change
        
        Returns:
            Dict с деталями swap или None
        """
        try:
            # Check if USDT decreased and USDC increased
            if not usdt_delta.is_expense() or not usdc_delta.is_income():
                return None
            
            # Check time window
            time_diff = abs(
                (usdc_delta.to_snapshot.timestamp - usdt_delta.to_snapshot.timestamp).total_seconds()
            )
            
            if time_diff > self.swap_time_window:
                logger.debug(f"Time window too large for swap: {time_diff}s")
                return None
            
            # Check amount matching (with tolerance for fees)
            usdt_amount = usdt_delta.abs_amount()
            usdc_amount = usdc_delta.abs_amount()
            
            # USDT ≈ USDC (both stablecoins)
            amount_diff = abs(usdt_amount - usdc_amount)
            amount_diff_pct = amount_diff / usdt_amount if usdt_amount > 0 else Decimal(1)
            
            if amount_diff_pct > self.amount_tolerance:
                logger.debug(
                    f"Amount mismatch for swap: USDT={usdt_amount}, "
                    f"USDC={usdc_amount}, diff={amount_diff_pct:.2%}"
                )
                return None
            
            # Swap detected!
            confidence = 1.0 - float(amount_diff_pct)  # Higher confidence if amounts match better
            
            swap_info = {
                "pattern": "usdt_usdc_swap",
                "from_currency": "USDT",
                "to_currency": "USDC",
                "from_amount": float(usdt_amount),
                "to_amount": float(usdc_amount),
                "fee": float(amount_diff),
                "time_diff_seconds": time_diff,
                "confidence": confidence,
                "usdt_delta": usdt_delta.to_dict(),
                "usdc_delta": usdc_delta.to_dict(),
            }
            
            logger.info(
                f"USDT→USDC swap detected: {usdt_amount} USDT → {usdc_amount} USDC, "
                f"confidence={confidence:.2f}"
            )
            
            return swap_info
            
        except Exception as e:
            logger.error(f"Failed to detect swap pattern: {e}")
            return None
    
    async def detect_card_payment_pattern(
        self,
        usdc_delta: BalanceDelta
    ) -> Optional[Dict[str, Any]]:
        """
        Детектирует USDC→EUR card payment pattern.
        
        Args:
            usdc_delta: USDC balance change (decrease)
        
        Returns:
            Dict с деталями payment или None
        """
        try:
            # Check if USDC decreased
            if not usdc_delta.is_expense():
                return None
            
            # Check if there's no corresponding blockchain transaction
            # (card payments are internal Trustee operations)
            has_blockchain_tx = await self._has_blockchain_transaction(
                usdc_delta.wallet_id,
                usdc_delta.abs_amount(),
                usdc_delta.to_snapshot.timestamp
            )
            
            if has_blockchain_tx:
                logger.debug("Blockchain transaction found, not a card payment")
                return None
            
            # Card payment detected!
            payment_info = {
                "pattern": "usdc_card_payment",
                "currency": "USDC",
                "amount": float(usdc_delta.abs_amount()),
                "confidence": usdc_delta.confidence,
                "usdc_delta": usdc_delta.to_dict(),
                "note": "Trustee Card payment (USDC→EUR)",
            }
            
            logger.info(
                f"USDC card payment detected: {usdc_delta.abs_amount()} USDC, "
                f"confidence={usdc_delta.confidence:.2f}"
            )
            
            return payment_info
            
        except Exception as e:
            logger.error(f"Failed to detect card payment pattern: {e}")
            return None
    
    async def detect_transfer_pattern(
        self,
        delta_a: BalanceDelta,
        delta_b: BalanceDelta,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Детектирует inter-wallet transfer pattern.
        
        Args:
            delta_a: Balance change в wallet A (decrease)
            delta_b: Balance change в wallet B (increase)
            user_id: ID пользователя
        
        Returns:
            Dict с деталями transfer или None
        """
        try:
            # Check if one decreased and other increased
            if not (delta_a.is_expense() and delta_b.is_income()):
                return None
            
            # Check if same currency
            if delta_a.currency != delta_b.currency:
                return None
            
            # Check time window
            time_diff = abs(
                (delta_b.to_snapshot.timestamp - delta_a.to_snapshot.timestamp).total_seconds()
            )
            
            if time_diff > self.transfer_time_window:
                logger.debug(f"Time window too large for transfer: {time_diff}s")
                return None
            
            # Check amount matching (with tolerance for fees)
            amount_a = delta_a.abs_amount()
            amount_b = delta_b.abs_amount()
            
            amount_diff = abs(amount_a - amount_b)
            amount_diff_pct = amount_diff / amount_a if amount_a > 0 else Decimal(1)
            
            if amount_diff_pct > self.amount_tolerance:
                logger.debug(
                    f"Amount mismatch for transfer: A={amount_a}, B={amount_b}, "
                    f"diff={amount_diff_pct:.2%}"
                )
                return None
            
            # Transfer detected!
            confidence = 1.0 - float(amount_diff_pct)
            
            transfer_info = {
                "pattern": "inter_wallet_transfer",
                "from_wallet_id": delta_a.wallet_id,
                "to_wallet_id": delta_b.wallet_id,
                "currency": delta_a.currency,
                "amount": float(amount_a),
                "fee": float(amount_diff),
                "time_diff_seconds": time_diff,
                "confidence": confidence,
                "delta_a": delta_a.to_dict(),
                "delta_b": delta_b.to_dict(),
            }
            
            logger.info(
                f"Inter-wallet transfer detected: {amount_a} {delta_a.currency}, "
                f"confidence={confidence:.2f}"
            )
            
            return transfer_info
            
        except Exception as e:
            logger.error(f"Failed to detect transfer pattern: {e}")
            return None
    
    async def detect_all_patterns(
        self,
        deltas: List[BalanceDelta],
        user_id: str
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Детектирует все patterns в списке deltas.
        
        Args:
            deltas: List of BalanceDelta
            user_id: ID пользователя
        
        Returns:
            Dict с detected patterns по типам
        """
        patterns = {
            "swaps": [],
            "card_payments": [],
            "transfers": [],
        }
        
        try:
            # Group deltas by wallet and currency
            deltas_by_wallet = {}
            for delta in deltas:
                key = (delta.wallet_id, delta.currency)
                if key not in deltas_by_wallet:
                    deltas_by_wallet[key] = []
                deltas_by_wallet[key].append(delta)
            
            # Detect swaps (USDT→USDC)
            usdt_deltas = deltas_by_wallet.get((delta.wallet_id, "USDT"), [])
            usdc_deltas = deltas_by_wallet.get((delta.wallet_id, "USDC"), [])
            
            for usdt_delta in usdt_deltas:
                for usdc_delta in usdc_deltas:
                    swap = await self.detect_swap_pattern(usdt_delta, usdc_delta)
                    if swap:
                        patterns["swaps"].append(swap)
            
            # Detect card payments (USDC→EUR)
            for usdc_delta in usdc_deltas:
                if usdc_delta.is_expense():
                    payment = await self.detect_card_payment_pattern(usdc_delta)
                    if payment:
                        patterns["card_payments"].append(payment)
            
            # Detect transfers (between wallets)
            all_deltas = [d for deltas_list in deltas_by_wallet.values() for d in deltas_list]
            
            for i, delta_a in enumerate(all_deltas):
                for delta_b in all_deltas[i+1:]:
                    if delta_a.wallet_id != delta_b.wallet_id:
                        transfer = await self.detect_transfer_pattern(delta_a, delta_b, user_id)
                        if transfer:
                            patterns["transfers"].append(transfer)
            
            logger.info(
                f"Pattern detection completed: "
                f"{len(patterns['swaps'])} swaps, "
                f"{len(patterns['card_payments'])} card payments, "
                f"{len(patterns['transfers'])} transfers"
            )
            
            return patterns
            
        except Exception as e:
            logger.error(f"Failed to detect all patterns: {e}")
            return patterns
    
    async def _has_blockchain_transaction(
        self,
        wallet_id: str,
        amount: Decimal,
        timestamp: datetime
    ) -> bool:
        """
        Проверяет, есть ли blockchain transaction для данного изменения баланса.
        
        Args:
            wallet_id: ID кошелька
            amount: Amount
            timestamp: Timestamp
        
        Returns:
            True if blockchain transaction exists
        """
        try:
            # Search for transaction in ±5 minutes window
            from_time = timestamp - timedelta(minutes=5)
            to_time = timestamp + timedelta(minutes=5)
            
            transactions = await self.transaction_repo.get_by_timerange(
                wallet_id, from_time, to_time
            )
            
            # Check if any transaction matches amount
            for tx in transactions:
                tx_amount = Decimal(str(tx.get("amount", 0)))
                amount_diff = abs(tx_amount - amount)
                amount_diff_pct = amount_diff / amount if amount > 0 else Decimal(1)
                
                if amount_diff_pct <= self.amount_tolerance:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to check blockchain transaction: {e}")
            return False
