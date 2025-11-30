"""
User service
"""
from typing import Optional
from infrastructure.logging_config import get_logger
from infrastructure.supabase_client import SupabaseClient

logger = get_logger(__name__)

class UserService:
    """User service for managing users"""
    
    def __init__(self, user_repository=None):
        self.user_repository = user_repository
        self.supabase = SupabaseClient()
    
    async def get_or_create_user(self, telegram_id: int, username: str = None, 
                                  first_name: str = None, last_name: str = None):
        """Get or create user from Supabase"""
        try:
            # Get or create user in Supabase
            user = self.supabase.get_or_create_user(telegram_id, username, first_name, last_name)
            
            if user:
                logger.info(f"User found/created in Supabase: {user['id']} for telegram_id {telegram_id}")
                return user
            else:
                logger.error(f"Failed to get/create user in Supabase for telegram_id {telegram_id}")
                # Fallback to local format
                return {
                    'id': f'user_{telegram_id}',
                    'telegram_id': telegram_id,
                    'username': username,
                    'first_name': first_name,
                    'last_name': last_name,
                    'default_currency': 'USD'
                }
        except Exception as e:
            logger.error(f"Error in get_or_create_user: {e}", exc_info=True)
            # Fallback
            return {
                'id': f'user_{telegram_id}',
                'telegram_id': telegram_id,
                'username': username,
                'first_name': first_name,
                'last_name': last_name,
                'default_currency': 'USD'
            }
    
    async def get_user_by_telegram_id(self, telegram_id: int):
        """Get user by telegram ID"""
        return await self.get_or_create_user(telegram_id)
    
    async def update_user_settings(self, user_id: str, settings: dict):
        """Update user settings"""
        logger.info(f"Updating settings for user {user_id}: {settings}")
        return True
