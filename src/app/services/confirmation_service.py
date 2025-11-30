"""
Confirmation Service
Handles user confirmation requests for low-confidence AI categorizations
Now with Redis persistence for reliability and horizontal scaling
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import json
import redis.asyncio as redis
from infrastructure.logging_config import get_logger
from infrastructure.repositories.transaction_repository import TransactionRepository
from infrastructure.repositories.category_repository import CategoryRepository
from infrastructure.repositories.merchant_repository import MerchantRepository

logger = get_logger(__name__)


class ConfirmationService:
    """
    Service for managing user confirmation requests with Redis persistence.
    
    Features:
    - Store pending confirmations in Redis with TTL
    - Generate confirmation messages
    - Process user responses
    - Learn from corrections (update merchant mappings)
    - Horizontal scaling support
    """
    
    def __init__(
        self,
        transaction_repo: TransactionRepository,
        category_repo: CategoryRepository,
        merchant_repo: MerchantRepository,
        redis_client: redis.Redis
    ):
        self.transaction_repo = transaction_repo
        self.category_repo = category_repo
        self.merchant_repo = merchant_repo
        self.redis = redis_client
        
        # Redis key prefix for confirmations
        self.CONFIRMATION_PREFIX = "confirmation:"
        self.USER_PENDING_PREFIX = "user_pending:"
        self.CONFIRMATION_TTL = 86400  # 24 hours
    
    async def create_confirmation_request(
        self,
        user_id: str,
        transaction_data: Dict[str, Any],
        ai_suggestion: Dict[str, Any]
    ) -> str:
        """
        Create a new confirmation request in Redis.
        
        Args:
            user_id: User ID
            transaction_data: Transaction data
            ai_suggestion: AI categorization suggestion
        
        Returns:
            Confirmation request ID
        """
        # Generate unique confirmation ID
        confirmation_id = f"conf_{user_id}_{int(datetime.now().timestamp())}"
        
        # Prepare confirmation data
        confirmation_data = {
            "user_id": user_id,
            "transaction_data": transaction_data,
            "ai_suggestion": ai_suggestion,
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(hours=24)).isoformat()
        }
        
        # Store in Redis with TTL
        redis_key = f"{self.CONFIRMATION_PREFIX}{confirmation_id}"
        await self.redis.setex(
            redis_key,
            self.CONFIRMATION_TTL,
            json.dumps(confirmation_data)
        )
        
        # Add to user's pending set
        user_pending_key = f"{self.USER_PENDING_PREFIX}{user_id}"
        await self.redis.sadd(user_pending_key, confirmation_id)
        await self.redis.expire(user_pending_key, self.CONFIRMATION_TTL)
        
        logger.info(f"📝 Created confirmation request in Redis: {confirmation_id}")
        return confirmation_id
    
    async def get_confirmation_message(
        self,
        confirmation_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get formatted confirmation message for Telegram.
        
        Args:
            confirmation_id: Confirmation request ID
        
        Returns:
            Message data with text and buttons
        """
        # Get confirmation from Redis
        redis_key = f"{self.CONFIRMATION_PREFIX}{confirmation_id}"
        confirmation_json = await self.redis.get(redis_key)
        
        if not confirmation_json:
            logger.warning(f"Confirmation not found in Redis: {confirmation_id}")
            return None
        
        try:
            confirmation = json.loads(confirmation_json)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse confirmation JSON: {e}")
            return None
        
        # Check if expired
        expires_at = datetime.fromisoformat(confirmation["expires_at"])
        if datetime.now() > expires_at:
            logger.warning(f"Confirmation expired: {confirmation_id}")
            await self.redis.delete(redis_key)
            return None
        
        tx = confirmation["transaction_data"]
        suggestion = confirmation["ai_suggestion"]
        
        # Format message
        message_text = (
            f"🤔 **Please confirm categorization:**\n\n"
            f"💰 Amount: {tx.get('amount', 0)} {tx.get('currency', 'USD')}\n"
            f"🏪 Merchant: {tx.get('merchant', 'Unknown')}\n"
            f"📅 Date: {tx.get('timestamp', 'Unknown')}\n\n"
            f"🤖 AI suggests: **{suggestion.get('category', 'Other')}**\n"
            f"📊 Confidence: {suggestion.get('confidence', 0):.0%}\n"
            f"💡 Reasoning: {suggestion.get('reasoning', 'N/A')}\n\n"
        )
        
        if suggestion.get("suggest_manual_review"):
            message_text += "⚠️ **Low confidence** - please review carefully"
        
        # Get user categories for buttons
        user_id = confirmation["user_id"]
        categories = await self.category_repo.get_by_user(user_id)
        
        return {
            "text": message_text,
            "confirmation_id": confirmation_id,
            "suggested_category": suggestion.get("category"),
            "categories": categories[:8]  # Limit to 8 for Telegram inline keyboard
        }
    
    async def process_confirmation(
        self,
        confirmation_id: str,
        confirmed_category: str,
        user_id: str
    ) -> bool:
        """
        Process user confirmation response.
        
        Args:
            confirmation_id: Confirmation request ID
            confirmed_category: User-confirmed category
            user_id: User ID
        
        Returns:
            True if successful, False otherwise
        """
        # Get confirmation from Redis
        redis_key = f"{self.CONFIRMATION_PREFIX}{confirmation_id}"
        confirmation_json = await self.redis.get(redis_key)
        
        if not confirmation_json:
            logger.warning(f"Confirmation not found in Redis: {confirmation_id}")
            return False
        
        try:
            confirmation = json.loads(confirmation_json)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse confirmation JSON: {e}")
            return False
        
        # Verify user owns this confirmation
        if confirmation["user_id"] != user_id:
            logger.error(f"User {user_id} tried to confirm request for {confirmation['user_id']}")
            return False
        
        tx = confirmation["transaction_data"]
        suggestion = confirmation["ai_suggestion"]
        
        # Update transaction with confirmed category
        try:
            await self.transaction_repo.update(
                transaction_id=tx.get("id"),
                category=confirmed_category,
                confirmed=True,
                confirmed_at=datetime.now()
            )
            
            logger.info(f"✅ Transaction {tx.get('id')} confirmed: {confirmed_category}")
        except Exception as e:
            logger.error(f"Failed to update transaction: {e}")
            return False
        
        # Learn from correction if user changed category
        if confirmed_category != suggestion.get("category"):
            await self._learn_from_correction(
                user_id=user_id,
                merchant=tx.get("merchant"),
                correct_category=confirmed_category,
                ai_category=suggestion.get("category")
            )
        
        # Remove from Redis
        await self.redis.delete(redis_key)
        
        # Remove from user's pending set
        user_pending_key = f"{self.USER_PENDING_PREFIX}{user_id}"
        await self.redis.srem(user_pending_key, confirmation_id)
        
        logger.info(f"🗑️ Removed confirmation from Redis: {confirmation_id}")
        
        return True
    
    async def _learn_from_correction(
        self,
        user_id: str,
        merchant: str,
        correct_category: str,
        ai_category: str
    ):
        """
        Learn from user correction by updating merchant mapping.
        
        Args:
            user_id: User ID
            merchant: Merchant name
            correct_category: User-corrected category
            ai_category: AI-suggested category
        """
        try:
            # Check if mapping exists
            existing = await self.merchant_repo.get_by_merchant(user_id, merchant)
            
            if existing:
                # Update existing mapping
                await self.merchant_repo.update(
                    mapping_id=existing["id"],
                    category=correct_category
                )
                logger.info(f"📚 Updated merchant mapping: {merchant} → {correct_category}")
            else:
                # Create new mapping
                await self.merchant_repo.create({
                    "user_id": user_id,
                    "merchant_name": merchant,
                    "category": correct_category
                })
                logger.info(f"📚 Learned new merchant mapping: {merchant} → {correct_category}")
            
            # Log correction for analytics
            logger.info(
                f"🔄 AI correction: {merchant} | "
                f"AI said: {ai_category} | "
                f"User corrected: {correct_category}"
            )
        
        except Exception as e:
            logger.error(f"Failed to learn from correction: {e}")
    
    async def get_pending_count(self, user_id: str) -> int:
        """
        Get count of pending confirmations for a user from Redis.
        
        Args:
            user_id: User ID
        
        Returns:
            Count of pending confirmations
        """
        user_pending_key = f"{self.USER_PENDING_PREFIX}{user_id}"
        count = await self.redis.scard(user_pending_key)
        return count
    
    async def cleanup_expired(self):
        """
        Remove expired confirmation requests from Redis.
        Note: Redis TTL handles most cleanup automatically.
        This method is for manual cleanup if needed.
        """
        # Get all confirmation keys
        pattern = f"{self.CONFIRMATION_PREFIX}*"
        cursor = 0
        expired_count = 0
        
        while True:
            cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)
            
            for key in keys:
                # Check TTL
                ttl = await self.redis.ttl(key)
                if ttl == -2:  # Key doesn't exist
                    expired_count += 1
                elif ttl == -1:  # Key has no expiry (shouldn't happen)
                    await self.redis.expire(key, self.CONFIRMATION_TTL)
                    logger.warning(f"Fixed missing TTL for key: {key}")
            
            if cursor == 0:
                break
        
        if expired_count > 0:
            logger.info(f"🗑️ Cleaned up {expired_count} expired confirmations from Redis")
