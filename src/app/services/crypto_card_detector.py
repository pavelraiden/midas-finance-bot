"""
Crypto Card Detector Service
Detects crypto card payments by analyzing USDT→USDC swaps
Based on AI Council recommendations (DeepSeek Reasoner)
"""
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from infrastructure.logging_config import get_logger

logger = get_logger(__name__)


class CryptoCardDetector:
    """
    Detects crypto card payments by analyzing USDT→USDC swaps.
    
    Features:
    - State machine for swap detection
    - Time window matching (5 minutes)
    - Amount tolerance for fees (2%)
    - Automatic transaction linking
    - Internal transfer marking
    """
    
    # Configuration
    TIME_WINDOW = timedelta(minutes=5)  # Max time between USDT out and USDC in
    AMOUNT_TOLERANCE = 0.02  # 2% tolerance for fees
    
    # Transaction types
    USDT_OUT = "USDT_OUT"
    USDC_IN = "USDC_IN"
    
    def __init__(self, transaction_repo):
        """
        Initialize CryptoCardDetector.
        
        Args:
            transaction_repo: TransactionRepository instance
        """
        self.transaction_repo = transaction_repo
        logger.info("CryptoCardDetector initialized")
    
    async def find_usdt_usdc_swaps(
        self,
        user_id: str,
        new_transactions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Find USDT→USDC swaps in new transactions.
        
        Args:
            user_id: User ID
            new_transactions: List of new transactions to analyze
        
        Returns:
            List of detected crypto card top-up transactions
        """
        logger.debug(f"Analyzing {len(new_transactions)} transactions for crypto card swaps")
        
        # 1. Filter transactions into USDT out and USDC in
        usdt_out, usdc_in = self._filter_transactions(new_transactions)
        
        logger.debug(f"Found {len(usdt_out)} USDT out, {len(usdc_in)} USDC in")
        
        if not usdt_out or not usdc_in:
            logger.debug("No potential swaps found")
            return []
        
        # 2. Find matching swaps
        swaps = []
        matched_usdc_ids = set()  # Track matched USDC to avoid duplicates
        
        for usdt_tx in usdt_out:
            # Find matching USDC transaction
            match = self._find_matching_usdc(usdt_tx, usdc_in, matched_usdc_ids)
            
            if match:
                usdc_tx, confidence = match
                
                # Create crypto card top-up transaction
                topup_tx = self._create_topup_transaction(
                    user_id=user_id,
                    usdt_tx=usdt_tx,
                    usdc_tx=usdc_tx,
                    confidence=confidence
                )
                
                swaps.append(topup_tx)
                matched_usdc_ids.add(usdc_tx["id"])
                
                logger.info(
                    f"✅ Detected crypto card swap: "
                    f"{usdt_tx['amount']} USDT → {usdc_tx['amount']} USDC "
                    f"(confidence: {confidence:.2%})"
                )
        
        logger.info(f"Detected {len(swaps)} crypto card top-ups")
        return swaps
    
    def _filter_transactions(
        self,
        transactions: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Filter transactions into USDT out and USDC in.
        
        Args:
            transactions: List of transactions
        
        Returns:
            Tuple of (usdt_out, usdc_in) lists
        """
        usdt_out = []
        usdc_in = []
        
        for tx in transactions:
            currency = tx.get("currency", "").upper()
            amount = float(tx.get("amount", 0))
            
            # USDT outgoing (negative amount)
            if currency == "USDT" and amount < 0:
                usdt_out.append(tx)
            
            # USDC incoming (positive amount)
            elif currency == "USDC" and amount > 0:
                usdc_in.append(tx)
        
        # Sort by timestamp for efficient matching
        usdt_out.sort(key=lambda x: x.get("timestamp", datetime.min))
        usdc_in.sort(key=lambda x: x.get("timestamp", datetime.min))
        
        return usdt_out, usdc_in
    
    def _find_matching_usdc(
        self,
        usdt_tx: Dict[str, Any],
        usdc_candidates: List[Dict[str, Any]],
        matched_ids: set
    ) -> Optional[Tuple[Dict[str, Any], float]]:
        """
        Find matching USDC transaction for a USDT transaction.
        
        Args:
            usdt_tx: USDT outgoing transaction
            usdc_candidates: List of USDC incoming transactions
            matched_ids: Set of already matched USDC transaction IDs
        
        Returns:
            Tuple of (usdc_tx, confidence) or None if no match
        """
        usdt_amount = abs(float(usdt_tx.get("amount", 0)))
        usdt_time = usdt_tx.get("timestamp")
        
        if not usdt_time:
            logger.warning(f"USDT transaction {usdt_tx.get('id')} has no timestamp")
            return None
        
        # Convert string timestamp to datetime if needed
        if isinstance(usdt_time, str):
            usdt_time = datetime.fromisoformat(usdt_time)
        
        best_match = None
        best_confidence = 0.0
        
        for usdc_tx in usdc_candidates:
            # Skip already matched
            if usdc_tx["id"] in matched_ids:
                continue
            
            usdc_amount = float(usdc_tx.get("amount", 0))
            usdc_time = usdc_tx.get("timestamp")
            
            if not usdc_time:
                continue
            
            # Convert string timestamp to datetime if needed
            if isinstance(usdc_time, str):
                usdc_time = datetime.fromisoformat(usdc_time)
            
            # Check time window
            time_diff = abs(usdc_time - usdt_time)
            if time_diff > self.TIME_WINDOW:
                continue
            
            # Check amount tolerance
            amount_diff = abs(usdc_amount - usdt_amount)
            amount_ratio = amount_diff / usdt_amount if usdt_amount > 0 else 1.0
            
            if amount_ratio > self.AMOUNT_TOLERANCE:
                continue
            
            # Calculate confidence score
            # Higher confidence for:
            # - Closer time match
            # - Closer amount match
            time_score = 1.0 - (time_diff.total_seconds() / self.TIME_WINDOW.total_seconds())
            amount_score = 1.0 - (amount_ratio / self.AMOUNT_TOLERANCE)
            confidence = (time_score * 0.4 + amount_score * 0.6)
            
            # Keep best match
            if confidence > best_confidence:
                best_match = usdc_tx
                best_confidence = confidence
        
        if best_match:
            return (best_match, best_confidence)
        
        return None
    
    def _create_topup_transaction(
        self,
        user_id: str,
        usdt_tx: Dict[str, Any],
        usdc_tx: Dict[str, Any],
        confidence: float
    ) -> Dict[str, Any]:
        """
        Create a crypto card top-up transaction.
        
        Args:
            user_id: User ID
            usdt_tx: USDT outgoing transaction
            usdc_tx: USDC incoming transaction
            confidence: Match confidence score
        
        Returns:
            New transaction dict
        """
        # Use USDC amount (what actually arrived on card)
        amount = float(usdc_tx.get("amount", 0))
        
        # Use USDC timestamp (when card was topped up)
        timestamp = usdc_tx.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        
        # Calculate fee
        usdt_amount = abs(float(usdt_tx.get("amount", 0)))
        fee = usdt_amount - amount
        
        return {
            "user_id": user_id,
            "wallet_id": usdc_tx.get("wallet_id"),
            "amount": amount,
            "currency": "USDC",
            "timestamp": timestamp,
            "category": "Crypto Card Top-up",
            "description": f"Crypto card top-up via USDT→USDC swap (fee: {fee:.2f} USDT)",
            "merchant": "Crypto Card",
            "type": "crypto_card_topup",
            "metadata": {
                "usdt_tx_id": usdt_tx.get("id"),
                "usdc_tx_id": usdc_tx.get("id"),
                "confidence": confidence,
                "fee": fee,
                "swap_detected": True
            }
        }
    
    async def mark_as_internal_transfer(
        self,
        transaction_ids: List[str]
    ) -> int:
        """
        Mark transactions as internal transfers (hide from main view).
        
        Args:
            transaction_ids: List of transaction IDs to mark
        
        Returns:
            Number of transactions marked
        """
        if not transaction_ids:
            return 0
        
        try:
            count = 0
            for tx_id in transaction_ids:
                await self.transaction_repo.update(
                    tx_id,
                    {"internal_transfer": True}
                )
                count += 1
            
            logger.info(f"Marked {count} transactions as internal transfers")
            return count
            
        except Exception as e:
            logger.error(f"Error marking transactions as internal: {e}")
            return 0
