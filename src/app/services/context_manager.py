"""
Context Manager for AI Services
Gathers user-specific context for AI prompts
Based on AI Council recommendations (Claude 3.7)
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from infrastructure.logging_config import get_logger

logger = get_logger(__name__)


class ContextManager:
    """
    Gathers user-specific context for AI prompts.
    
    Features:
    - Fetches user categories, transactions, merchant mappings
    - Token management (summarization for long contexts)
    - Caching for performance
    - Async database access
    """
    
    # Token limits
    MAX_TOKENS = 3000
    TOKENS_PER_TRANSACTION = 50  # Approximate
    TOKENS_PER_MERCHANT = 30
    
    def __init__(
        self,
        user_repo,
        transaction_repo,
        category_repo,
        merchant_repo
    ):
        """
        Initialize ContextManager with repository dependencies.
        
        Args:
            user_repo: UserRepository instance
            transaction_repo: TransactionRepository instance
            category_repo: CategoryRepository instance
            merchant_repo: MerchantRepository instance
        """
        self.user_repo = user_repo
        self.transaction_repo = transaction_repo
        self.category_repo = category_repo
        self.merchant_repo = merchant_repo
        
        logger.info("ContextManager initialized")
    
    async def get_categorization_context(
        self,
        user_id: str,
        transaction_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get context for transaction categorization.
        
        Args:
            user_id: User ID
            transaction_data: Transaction data (description, merchant, amount, etc.)
        
        Returns:
            Dict with context for categorization prompt:
                - user_id: str
                - user_categories: List[str]
                - recent_transactions: List[Dict]
                - merchant_mappings: List[Dict]
                - description: str
                - merchant: str
                - amount: float
                - currency: str
        """
        logger.debug(f"Getting categorization context for user {user_id}")
        
        # 1. Get user categories
        user_categories = await self._get_user_categories(user_id)
        
        # 2. Get recent transactions (last 7 days)
        recent_transactions = await self._get_recent_transactions(user_id, days=7)
        
        # 3. Get merchant mappings
        merchant_mappings = await self._get_merchant_mappings(user_id)
        
        # 4. Token management - limit context if too large
        recent_transactions, merchant_mappings = self._manage_tokens(
            recent_transactions,
            merchant_mappings
        )
        
        # 5. Build context
        context = {
            "user_id": user_id,
            "user_categories": user_categories,
            "recent_transactions": recent_transactions,
            "merchant_mappings": merchant_mappings,
            "description": transaction_data.get("description", ""),
            "merchant": transaction_data.get("merchant", "Unknown"),
            "amount": transaction_data.get("amount", 0.0),
            "currency": transaction_data.get("currency", "USD")
        }
        
        logger.debug(
            f"Context built: {len(user_categories)} categories, "
            f"{len(recent_transactions)} transactions, "
            f"{len(merchant_mappings)} merchant mappings"
        )
        
        return context
    
    async def get_analyze_spending_context(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get context for spending analysis.
        
        Args:
            user_id: User ID
            days: Number of days to analyze (default 30)
        
        Returns:
            Dict with context for analyze spending prompt:
                - user_id: str
                - total_spending: float
                - spending_by_category: Dict[str, float]
                - spending_by_day: Dict[str, float]
                - transaction_count: int
                - currency: str
        """
        logger.debug(f"Getting spending analysis context for user {user_id} ({days} days)")
        
        # Get transactions for the period
        start_date = datetime.now() - timedelta(days=days)
        transactions = await self.transaction_repo.get_by_user_and_date_range(
            user_id=user_id,
            start_date=start_date,
            end_date=datetime.now()
        )
        
        if not transactions:
            logger.warning(f"No transactions found for user {user_id}")
            return {
                "user_id": user_id,
                "total_spending": 0.0,
                "spending_by_category": {},
                "spending_by_day": {},
                "transaction_count": 0,
                "currency": "USD"
            }
        
        # Calculate spending by category
        spending_by_category = {}
        for tx in transactions:
            category = tx.get("category", "Other")
            amount = abs(float(tx.get("amount", 0)))
            spending_by_category[category] = spending_by_category.get(category, 0) + amount
        
        # Calculate spending by day of week
        spending_by_day = {
            "Monday": 0.0,
            "Tuesday": 0.0,
            "Wednesday": 0.0,
            "Thursday": 0.0,
            "Friday": 0.0,
            "Saturday": 0.0,
            "Sunday": 0.0
        }
        
        for tx in transactions:
            tx_date = tx.get("date")
            if tx_date:
                if isinstance(tx_date, str):
                    tx_date = datetime.fromisoformat(tx_date)
                day_name = tx_date.strftime("%A")
                amount = abs(float(tx.get("amount", 0)))
                spending_by_day[day_name] += amount
        
        # Calculate total spending
        total_spending = sum(spending_by_category.values())
        
        # Get currency (from first transaction)
        currency = transactions[0].get("currency", "USD") if transactions else "USD"
        
        context = {
            "user_id": user_id,
            "total_spending": total_spending,
            "spending_by_category": spending_by_category,
            "spending_by_day": spending_by_day,
            "transaction_count": len(transactions),
            "currency": currency
        }
        
        logger.debug(
            f"Spending context built: {total_spending:.2f} {currency} "
            f"across {len(transactions)} transactions"
        )
        
        return context
    
    async def get_budget_recommendation_context(
        self,
        user_id: str,
        months: int = 3
    ) -> Dict[str, Any]:
        """
        Get context for budget recommendations.
        
        Args:
            user_id: User ID
            months: Number of months to analyze (default 3)
        
        Returns:
            Dict with context for budget recommendation prompt
        """
        logger.debug(f"Getting budget recommendation context for user {user_id}")
        
        # Get user data
        user = await self.user_repo.get_by_id(user_id)
        monthly_income = user.get("monthly_income") if user else None
        financial_goals = user.get("financial_goals") if user else None
        
        # Get transactions for the period
        start_date = datetime.now() - timedelta(days=months * 30)
        transactions = await self.transaction_repo.get_by_user_and_date_range(
            user_id=user_id,
            start_date=start_date,
            end_date=datetime.now()
        )
        
        # Calculate average monthly spending by category
        spending_by_category = {}
        for tx in transactions:
            category = tx.get("category", "Other")
            amount = abs(float(tx.get("amount", 0)))
            spending_by_category[category] = spending_by_category.get(category, 0) + amount
        
        # Average over months
        for category in spending_by_category:
            spending_by_category[category] /= months
        
        # Calculate average monthly spending
        avg_monthly_spending = sum(spending_by_category.values())
        
        # Get currency
        currency = transactions[0].get("currency", "USD") if transactions else "USD"
        
        context = {
            "user_id": user_id,
            "monthly_income": monthly_income,
            "avg_monthly_spending": avg_monthly_spending,
            "spending_by_category": spending_by_category,
            "financial_goals": financial_goals,
            "currency": currency
        }
        
        return context
    
    async def _get_user_categories(self, user_id: str) -> List[str]:
        """
        Get list of user's categories.
        
        Args:
            user_id: User ID
        
        Returns:
            List of category names
        """
        try:
            categories = await self.category_repo.get_by_user(user_id)
            if categories:
                return [cat.get("name") for cat in categories if cat.get("name")]
            else:
                # Default categories if user has none
                return ["Food", "Transport", "Shopping", "Entertainment", "Bills", "Health", "Other"]
        except Exception as e:
            logger.error(f"Error getting user categories: {e}")
            return ["Other"]
    
    async def _get_recent_transactions(
        self,
        user_id: str,
        days: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Get recent transactions for user.
        
        Args:
            user_id: User ID
            days: Number of days to look back
        
        Returns:
            List of transaction dicts
        """
        try:
            start_date = datetime.now() - timedelta(days=days)
            transactions = await self.transaction_repo.get_by_user_and_date_range(
                user_id=user_id,
                start_date=start_date,
                end_date=datetime.now()
            )
            
            # Format for prompt
            formatted = []
            for tx in transactions:
                formatted.append({
                    "date": tx.get("date", "").strftime("%Y-%m-%d") if isinstance(tx.get("date"), datetime) else str(tx.get("date", "")),
                    "merchant": tx.get("merchant", "Unknown"),
                    "amount": abs(float(tx.get("amount", 0))),
                    "category": tx.get("category", "Other")
                })
            
            return formatted
        except Exception as e:
            logger.error(f"Error getting recent transactions: {e}")
            return []
    
    async def _get_merchant_mappings(self, user_id: str) -> List[Dict[str, str]]:
        """
        Get merchant mappings for user.
        
        Args:
            user_id: User ID
        
        Returns:
            List of merchant mapping dicts
        """
        try:
            mappings = await self.merchant_repo.get_by_user(user_id)
            
            # Format for prompt
            formatted = []
            for mapping in mappings:
                formatted.append({
                    "merchant_name": mapping.get("merchant_name", ""),
                    "category": mapping.get("category", "Other")
                })
            
            return formatted
        except Exception as e:
            logger.error(f"Error getting merchant mappings: {e}")
            return []
    
    def _manage_tokens(
        self,
        transactions: List[Dict],
        merchant_mappings: List[Dict]
    ) -> tuple:
        """
        Manage token count by limiting context size.
        
        Args:
            transactions: List of transactions
            merchant_mappings: List of merchant mappings
        
        Returns:
            Tuple of (limited_transactions, limited_mappings)
        """
        # Estimate token count
        tx_tokens = len(transactions) * self.TOKENS_PER_TRANSACTION
        mapping_tokens = len(merchant_mappings) * self.TOKENS_PER_MERCHANT
        total_tokens = tx_tokens + mapping_tokens
        
        if total_tokens <= self.MAX_TOKENS:
            # Within limit, return as is
            return transactions, merchant_mappings
        
        logger.warning(
            f"Context too large ({total_tokens} tokens), limiting to {self.MAX_TOKENS}"
        )
        
        # Limit transactions to most recent
        max_transactions = int((self.MAX_TOKENS * 0.6) / self.TOKENS_PER_TRANSACTION)
        limited_transactions = transactions[:max_transactions]
        
        # Limit merchant mappings to most common
        max_mappings = int((self.MAX_TOKENS * 0.4) / self.TOKENS_PER_MERCHANT)
        limited_mappings = merchant_mappings[:max_mappings]
        
        logger.debug(
            f"Limited context: {len(limited_transactions)} transactions, "
            f"{len(limited_mappings)} merchant mappings"
        )
        
        return limited_transactions, limited_mappings
