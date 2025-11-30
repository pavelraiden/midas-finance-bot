"""
Wallet service with Supabase integration
"""
from typing import List, Optional
from decimal import Decimal
from infrastructure.logging_config import get_logger
from infrastructure.supabase_client import SupabaseClient

logger = get_logger(__name__)

class WalletService:
    """Wallet service for managing wallets"""
    
    def __init__(self, wallet_repository=None):
        self.wallet_repository = wallet_repository
        self.supabase = SupabaseClient()
    
    def get_user_wallets(self, user_id: str) -> List[dict]:
        """Get all wallets for user from Supabase"""
        try:
            wallets = self.supabase.get_user_wallets(user_id)
            logger.info(f"Found {len(wallets)} wallets for user {user_id}")
            
            # Convert to expected format
            result = []
            for wallet in wallets:
                result.append({
                    'id': wallet['id'],
                    'name': wallet['name'],
                    'owner_id': wallet['user_id'],
                    'currency': wallet['currency'],
                    'current_balance': Decimal(wallet['balance']),
                    'is_active': wallet.get('is_active', True),
                    'wallet_type': wallet.get('wallet_type', 'manual'),
                    'icon': wallet.get('icon', '💰'),
                    'metadata': wallet.get('metadata', {})
                })
            
            return result
        except Exception as e:
            logger.error(f"Error fetching wallets: {e}", exc_info=True)
            return []
    
    def get_wallet_by_id(self, wallet_id: str) -> Optional[dict]:
        """Get wallet by ID from Supabase"""
        try:
            wallet = self.supabase.get_wallet_by_id(wallet_id)
            if wallet:
                return {
                    'id': wallet['id'],
                    'name': wallet['name'],
                    'owner_id': wallet['user_id'],
                    'currency': wallet['currency'],
                    'current_balance': Decimal(wallet['balance']),
                    'is_active': wallet.get('is_active', True),
                    'wallet_type': wallet.get('wallet_type', 'manual'),
                    'icon': wallet.get('icon', '💰'),
                    'metadata': wallet.get('metadata', {})
                }
            return None
        except Exception as e:
            logger.error(f"Error fetching wallet {wallet_id}: {e}", exc_info=True)
            return None
    
    def get_or_create_default_wallet(self, user_id: str) -> dict:
        """Get or create default wallet for user"""
        try:
            wallets = self.get_user_wallets(user_id)
            if wallets:
                return wallets[0]
            
            # Create default wallet
            logger.info(f"Creating default wallet for user {user_id}")
            wallet = self.supabase.create_wallet(
                user_id=user_id,
                name="Main Wallet",
                currency="USD",
                balance=0.0,
                wallet_type="manual"
            )
            
            if wallet:
                return {
                    'id': wallet['id'],
                    'name': wallet['name'],
                    'owner_id': wallet['user_id'],
                    'currency': wallet['currency'],
                    'current_balance': Decimal(wallet['balance']),
                    'is_active': True,
                    'wallet_type': 'manual',
                    'icon': '💰'
                }
            
            # Fallback
            return {
                'id': f'wallet_{user_id}_default',
                'name': 'Main Wallet',
                'owner_id': user_id,
                'currency': 'USD',
                'current_balance': Decimal('0.00'),
                'is_active': True,
                'wallet_type': 'manual',
                'icon': '💰'
            }
        except Exception as e:
            logger.error(f"Error in get_or_create_default_wallet: {e}", exc_info=True)
            # Fallback
            return {
                'id': f'wallet_{user_id}_default',
                'name': 'Main Wallet',
                'owner_id': user_id,
                'currency': 'USD',
                'current_balance': Decimal('0.00'),
                'is_active': True,
                'wallet_type': 'manual',
                'icon': '💰'
            }
    
    async def create_wallet(self, user_id: str, name: str, currency: str = 'USD', 
                           initial_balance: Decimal = Decimal('0.00'), 
                           icon: str = '💰', wallet_type: str = 'manual',
                           metadata: dict = None) -> dict:
        """Create new wallet in Supabase"""
        try:
            wallet = self.supabase.create_wallet(
                user_id=user_id,
                name=name,
                currency=currency,
                balance=float(initial_balance),
                wallet_type=wallet_type,
                metadata=metadata or {}
            )
            
            if wallet:
                logger.info(f"Wallet created: {wallet['id']}")
                return {
                    'id': wallet['id'],
                    'name': wallet['name'],
                    'owner_id': wallet['user_id'],
                    'currency': wallet['currency'],
                    'current_balance': Decimal(wallet['balance']),
                    'is_active': True,
                    'wallet_type': wallet_type,
                    'icon': icon
                }
            return None
        except Exception as e:
            logger.error(f"Error creating wallet: {e}", exc_info=True)
            raise
    
    async def update_wallet_balance(self, wallet_id: str, amount: Decimal):
        """Update wallet balance"""
        try:
            wallet = self.supabase.get_wallet_by_id(wallet_id)
            if wallet:
                new_balance = Decimal(wallet['balance']) + amount
                self.supabase.update_wallet(wallet_id, {'balance': str(new_balance)})
                logger.info(f"Updated wallet {wallet_id} balance to {new_balance}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating wallet balance: {e}", exc_info=True)
            return False
    
    async def delete_wallet(self, wallet_id: str):
        """Delete wallet"""
        try:
            return self.supabase.delete_wallet(wallet_id)
        except Exception as e:
            logger.error(f"Error deleting wallet: {e}", exc_info=True)
            return False
