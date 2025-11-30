"""
Wallet synchronization service for automatic transaction import.
"""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from decimal import Decimal
from infrastructure.logging_config import get_logger
from app.services.blockchain_service import BlockchainService
from app.services.deepseek_service import DeepSeekService
from infrastructure.repositories.merchant_repository import MerchantRepository

logger = get_logger(__name__)


class SyncService:
    """Service for syncing wallet transactions"""
    
    def __init__(
        self,
        blockchain_service: BlockchainService,
        deepseek_service: DeepSeekService,
        merchant_repo: MerchantRepository,
        transaction_service,
        wallet_service
    ):
        self.blockchain = blockchain_service
        self.ai = deepseek_service
        self.merchant_repo = merchant_repo
        self.transaction_service = transaction_service
        self.wallet_service = wallet_service
    
    async def sync_wallet(
        self,
        user_id: str,
        wallet_id: str,
        wallet_address: str,
        last_sync_timestamp: Optional[int] = None
    ) -> Dict:
        """Sync transactions from a crypto wallet"""
        logger.info(f"Starting wallet sync: {wallet_id} ({wallet_address})")
        
        # Get transactions from blockchain
        transactions = self.blockchain.get_wallet_transactions(
            address=wallet_address,
            from_timestamp=last_sync_timestamp
        )
        
        if not transactions:
            logger.info(f"No new transactions for wallet {wallet_id}")
            return {
                'wallet_id': wallet_id,
                'new_transactions': 0,
                'categorized': 0,
                'uncategorized': 0
            }
        
        logger.info(f"Found {len(transactions)} new transactions")
        
        # Process each transaction
        categorized_count = 0
        uncategorized_count = 0
        
        for tx in transactions:
            # Check if transaction already exists (by hash)
            existing_tx = await self.transaction_repo.get_by_hash(tx.hash)
            if existing_tx:
                logger.debug(f"Skipping duplicate transaction: {tx.hash}")
                continue
            
            # Detect if this is a transfer between user's wallets
            is_transfer = await self._detect_transfer(user_id, tx)
            
            if is_transfer:
                # Create transfer transaction
                await self._create_transfer_transaction(user_id, wallet_id, tx)
                categorized_count += 1
                continue
            
            # Try to categorize transaction
            category_id, confidence = await self._categorize_transaction(
                user_id=user_id,
                merchant_name=tx.get('to', 'Unknown'),
                amount=tx['value'],
                description=tx.get('hash', '')
            )
            
            if confidence >= 95:
                # High confidence - auto-categorize
                await self._create_transaction(
                    user_id=user_id,
                    wallet_id=wallet_id,
                    tx=tx,
                    category_id=category_id
                )
                categorized_count += 1
            else:
                # Low confidence - add to uncategorized queue
                await self._add_to_uncategorized_queue(
                    user_id=user_id,
                    wallet_id=wallet_id,
                    tx=tx,
                    suggested_category_id=category_id,
                    confidence=confidence
                )
                uncategorized_count += 1
        
        # Update last sync timestamp
        await self.wallet_service.update_last_sync(
            wallet_id=wallet_id,
            timestamp=int(datetime.now().timestamp())
        )
        
        logger.info(f"Wallet sync complete: {categorized_count} categorized, {uncategorized_count} need review")
        
        return {
            'wallet_id': wallet_id,
            'new_transactions': len(transactions),
            'categorized': categorized_count,
            'uncategorized': uncategorized_count
        }
    
    async def _detect_transfer(self, user_id: str, tx: Dict) -> bool:
        """Detect if transaction is a transfer between user's wallets"""
        # Get all user's wallet addresses
        user_wallets = await self.wallet_service.get_user_wallet_addresses(user_id)
        
        # Check if 'to' address belongs to user
        to_address = tx.get('to', '').lower()
        from_address = tx.get('from', '').lower()
        
        # If both addresses belong to user, it's a transfer
        if to_address in user_wallets and from_address in user_wallets:
            return True
        
        return False
    
    async def _categorize_transaction(
        self,
        user_id: str,
        merchant_name: str,
        amount: float,
        description: str
    ) -> tuple:
        """Categorize transaction using merchant learning + AI"""
        
        # 1. Check merchant mappings first
        mapping = self.merchant_repo.find_mapping(user_id, merchant_name)
        if mapping:
            # Increment usage count
            self.merchant_repo.increment_usage(mapping['id'])
            logger.info(f"Found merchant mapping: {merchant_name} -> {mapping['category_id']}")
            return mapping['category_id'], mapping['confidence']
        
        # 2. Check similar merchants
        similar = self.merchant_repo.find_similar_mappings(user_id, merchant_name, limit=3)
        if similar:
            # Use most common category from similar merchants
            best_match = similar[0]
            logger.info(f"Found similar merchant: {best_match['merchant_name']} -> {best_match['category_id']}")
            return best_match['category_id'], 85  # Lower confidence for similar match
        
        # 3. Use AI to categorize
        ai_result = self.ai.categorize_transaction(
            user_id=user_id,
            merchant_name=merchant_name,
            amount=amount,
            description=description
        )
        
        category_name = ai_result.get('category', 'Uncategorized')
        confidence = ai_result.get('confidence', 0)
        
        # Map category name to category_id
        category = await self.category_repo.get_by_name(user_id, category_name)
        category_id = category.id if category else None
        
        if not category_id:
            logger.warning(f"Category not found: {category_name}. Creating new category.")
            # Create new category if not exists
            from src.domain.category import Category
            new_category = Category(
                user_id=user_id,
                name=category_name,
                type='expense',  # Default to expense
                icon='❓',  # Default icon
                color='#808080'  # Default gray color
            )
            category_id = await self.category_repo.create(new_category)
        
        logger.info(f"AI categorization: {merchant_name} -> {category_name} ({confidence}%)")
        
        return category_id, confidence
    
    async def _create_transaction(
        self,
        user_id: str,
        wallet_id: str,
        tx: Dict,
        category_id: str
    ):
        """Create transaction in database"""
        await self.transaction_service.create_transaction(
            wallet_id=wallet_id,
            user_id=user_id,
            category_id=category_id,
            transaction_type='expense',  # Most blockchain txs are expenses
            amount=Decimal(str(tx['value'])),
            currency=tx['currency'],
            transaction_date=tx['timestamp'],
            note=f"Hash: {tx['hash']}"
        )
    
    async def _create_transfer_transaction(
        self,
        user_id: str,
        wallet_id: str,
        tx: Dict
    ):
        """Create transfer transaction"""
        # Find destination wallet
        to_wallet = await self.wallet_service.get_wallet_by_address(tx['to'])
        
        await self.transaction_service.create_transaction(
            wallet_id=wallet_id,
            user_id=user_id,
            category_id=None,
            transaction_type='transfer',
            amount=Decimal(str(tx['value'])),
            currency=tx['currency'],
            transaction_date=tx['timestamp'],
            note=f"Transfer to {tx['to'][:10]}...",
            to_wallet_id=to_wallet['id'] if to_wallet else None
        )
    
    async def _add_to_uncategorized_queue(
        self,
        tx: Dict,
        suggested_category_id: Optional[str],
        confidence: int
    ):
        """Add transaction to uncategorized queue for user review"""
        logger.info(f"Adding to uncategorized queue: {tx['hash']} (confidence: {confidence}%)")
        
        # Create transaction with 'uncategorized' status
        transaction_data = {
            'hash': tx['hash'],
            'amount': float(tx['value']),
            'currency': tx['currency'],
            'date': tx['block_timestamp'],
            'type': tx['type'],
            'wallet_id': tx['wallet_id'],
            'category_id': suggested_category_id,  # Suggested category
            'status': 'uncategorized',  # Mark as needing review
            'confidence': confidence,
            'note': f"Auto-detected transaction (confidence: {confidence}%). Please review and confirm category."
        }
        
        # Save to database with uncategorized status
        await self.transaction_service.create_transaction(transaction_data)
        logger.info(f"Transaction {tx['hash']} added to uncategorized queue")
    
    async def sync_all_user_wallets(self, user_id: str) -> Dict:
        """Sync all wallets for a user"""
        logger.info(f"Starting full wallet sync for user {user_id}")
        
        # Get all user's crypto wallets with auto-sync enabled
        wallets = await self.wallet_service.get_auto_sync_wallets(user_id)
        
        if not wallets:
            logger.info(f"No auto-sync wallets found for user {user_id}")
            return {
                'total_wallets': 0,
                'synced': 0,
                'failed': 0,
                'new_transactions': 0
            }
        
        results = {
            'total_wallets': len(wallets),
            'synced': 0,
            'failed': 0,
            'new_transactions': 0,
            'categorized': 0,
            'uncategorized': 0
        }
        
        for wallet in wallets:
            try:
                sync_result = await self.sync_wallet(
                    user_id=user_id,
                    wallet_id=wallet['id'],
                    wallet_address=wallet['address'],
                    last_sync_timestamp=wallet.get('last_sync_timestamp')
                )
                
                results['synced'] += 1
                results['new_transactions'] += sync_result['new_transactions']
                results['categorized'] += sync_result['categorized']
                results['uncategorized'] += sync_result['uncategorized']
                
            except Exception as e:
                logger.error(f"Failed to sync wallet {wallet['id']}: {e}")
                results['failed'] += 1
        
        logger.info(f"Full sync complete for user {user_id}: {results}")
        return results
    
    def detect_card_payments(
        self,
        transactions: List[Dict],
        usdt_balance_before: Decimal,
        usdc_balance_before: Decimal
    ) -> List[Dict]:
        """Detect card payments from USDT→USDC swaps"""
        card_payments = []
        
        # Look for USDT → USDC swaps
        for i, tx in enumerate(transactions):
            if tx['currency'] == 'USDC' and tx.get('from_currency') == 'USDT':
                # This is a swap, likely for card payment
                card_payments.append({
                    'type': 'card_payment_prep',
                    'amount': tx['value'],
                    'timestamp': tx['timestamp'],
                    'tx': tx
                })
        
        # Look for USDC decreases (actual card payments)
        usdc_txs = [tx for tx in transactions if tx['currency'] == 'USDC']
        for tx in usdc_txs:
            if tx['value'] < 0:  # Outgoing
                card_payments.append({
                    'type': 'card_payment',
                    'amount': abs(tx['value']),
                    'timestamp': tx['timestamp'],
                    'tx': tx
                })
        
        return card_payments
