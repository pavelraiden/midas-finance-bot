"""
Transaction service
"""
from typing import List, Optional
from decimal import Decimal
from datetime import date, datetime
from infrastructure.logging_config import get_logger
from infrastructure.supabase_client import SupabaseClient
import uuid

logger = get_logger(__name__)

class TransactionService:
    """Transaction service for managing transactions"""
    
    def __init__(self, transaction_repository=None, wallet_service=None):
        self.transaction_repository = transaction_repository
        self.wallet_service = wallet_service
        self.supabase = SupabaseClient()
    
    async def create_transaction(self, wallet_id: str, user_id: str, 
                                category_id: Optional[str], transaction_type: str,
                                amount: Decimal, currency: str, transaction_date: date,
                                note: Optional[str] = None, 
                                to_wallet_id: Optional[str] = None) -> dict:
        """Create new transaction"""
        transaction_id = f'tx_{user_id}_{datetime.now().timestamp()}'
        
        logger.info(f"Creating transaction {transaction_id}: {amount} {currency}")
        
        transaction = {
            'id': transaction_id,
            'wallet_id': wallet_id,
            'user_id': user_id,
            'category_id': category_id,
            'type': transaction_type,
            'amount': amount,
            'currency': currency,
            'date': transaction_date,
            'note': note,
            'to_wallet_id': to_wallet_id,
            'created_at': datetime.now()
        }
        
        # Save to Supabase
        try:
            supabase_transaction = {
                'id': str(uuid.uuid4()),
                'user_id': user_id,
                'wallet_id': wallet_id,
                'category_id': category_id,
                'amount': str(amount),
                'currency': currency,
                'type': transaction_type,
                'note': note,
                'transaction_date': transaction_date.isoformat() if isinstance(transaction_date, datetime) else transaction_date,
                'is_transfer': transaction_type == 'transfer',
                'transfer_wallet_id': to_wallet_id
            }
            
            result = self.supabase.insert('transactions', supabase_transaction)
            logger.info(f"Transaction saved to Supabase: {result}")
            
            # Update transaction dict with Supabase ID
            transaction['id'] = supabase_transaction['id']
            
        except Exception as e:
            logger.error(f"Failed to save transaction to Supabase: {e}")
            raise
        
        # Update wallet balance if wallet_service available
        if self.wallet_service:
            if transaction_type == 'income':
                await self.wallet_service.update_wallet_balance(wallet_id, amount)
            elif transaction_type == 'expense':
                await self.wallet_service.update_wallet_balance(wallet_id, -amount)
            elif transaction_type == 'transfer' and to_wallet_id:
                await self.wallet_service.update_wallet_balance(wallet_id, -amount)
                await self.wallet_service.update_wallet_balance(to_wallet_id, amount)
        
        return transaction
    
    async def get_user_transactions(self, user_id: str, limit: int = 100) -> List[dict]:
        """Get user transactions"""
        # Return empty list for now
        return []
    
    async def get_transaction_by_id(self, transaction_id: str) -> Optional[dict]:
        """Get transaction by ID"""
        return None
    
    async def update_transaction(self, transaction_id: str, **kwargs) -> dict:
        """Update transaction"""
        logger.info(f"Updating transaction {transaction_id}")
        return {'id': transaction_id, **kwargs}
    
    async def delete_transaction(self, transaction_id: str):
        """Delete transaction"""
        logger.info(f"Deleting transaction {transaction_id}")
        return True
    
    async def get_transactions_by_category(self, user_id: str, category_id: str) -> List[dict]:
        """Get transactions by category"""
        return []
    
    async def get_transactions_by_date_range(self, user_id: str, 
                                            start_date: date, 
                                            end_date: date) -> List[dict]:
        """Get transactions by date range"""
        return []
