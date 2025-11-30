"""
Unit tests for ContextManager
"""
import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timedelta
from src.app.services.context_manager import ContextManager


class TestContextManager:
    """Test suite for ContextManager"""
    
    @pytest.fixture
    def mock_repos(self):
        """Create mock repositories"""
        user_repo = Mock()
        transaction_repo = Mock()
        category_repo = Mock()
        merchant_repo = Mock()
        
        return {
            "user_repo": user_repo,
            "transaction_repo": transaction_repo,
            "category_repo": category_repo,
            "merchant_repo": merchant_repo
        }
    
    @pytest.fixture
    def context_manager(self, mock_repos):
        """Create ContextManager instance with mocks"""
        return ContextManager(
            user_repo=mock_repos["user_repo"],
            transaction_repo=mock_repos["transaction_repo"],
            category_repo=mock_repos["category_repo"],
            merchant_repo=mock_repos["merchant_repo"]
        )
    
    @pytest.mark.asyncio
    async def test_get_categorization_context_returns_dict(self, context_manager, mock_repos):
        """Test that get_categorization_context returns a dict"""
        # Setup mocks
        mock_repos["category_repo"].get_by_user = AsyncMock(return_value=[
            {"name": "Food"},
            {"name": "Transport"}
        ])
        mock_repos["transaction_repo"].get_by_user_and_date_range = AsyncMock(return_value=[])
        mock_repos["merchant_repo"].get_by_user = AsyncMock(return_value=[])
        
        # Test
        result = await context_manager.get_categorization_context(
            user_id="user_123",
            transaction_data={"description": "Test", "merchant": "Test", "amount": 10.0}
        )
        
        assert isinstance(result, dict)
        assert "user_id" in result
        assert "user_categories" in result
        assert "recent_transactions" in result
        assert "merchant_mappings" in result
    
    @pytest.mark.asyncio
    async def test_categorization_context_includes_user_data(self, context_manager, mock_repos):
        """Test that categorization context includes user data"""
        # Setup mocks
        mock_repos["category_repo"].get_by_user = AsyncMock(return_value=[
            {"name": "Food"},
            {"name": "Transport"}
        ])
        mock_repos["transaction_repo"].get_by_user_and_date_range = AsyncMock(return_value=[
            {
                "date": datetime.now(),
                "merchant": "Starbucks",
                "amount": -5.50,
                "category": "Food"
            }
        ])
        mock_repos["merchant_repo"].get_by_user = AsyncMock(return_value=[
            {"merchant_name": "Starbucks", "category": "Food"}
        ])
        
        # Test
        result = await context_manager.get_categorization_context(
            user_id="user_123",
            transaction_data={
                "description": "Coffee",
                "merchant": "Starbucks",
                "amount": 6.75,
                "currency": "USD"
            }
        )
        
        assert result["user_id"] == "user_123"
        assert "Food" in result["user_categories"]
        assert "Transport" in result["user_categories"]
        assert len(result["recent_transactions"]) == 1
        assert len(result["merchant_mappings"]) == 1
        assert result["merchant"] == "Starbucks"
        assert result["amount"] == 6.75
    
    @pytest.mark.asyncio
    async def test_get_analyze_spending_context_returns_dict(self, context_manager, mock_repos):
        """Test that get_analyze_spending_context returns a dict"""
        # Setup mocks
        mock_repos["transaction_repo"].get_by_user_and_date_range = AsyncMock(return_value=[
            {
                "date": datetime.now(),
                "merchant": "Starbucks",
                "amount": -5.50,
                "category": "Food",
                "currency": "USD"
            }
        ])
        
        # Test
        result = await context_manager.get_analyze_spending_context(user_id="user_123")
        
        assert isinstance(result, dict)
        assert "user_id" in result
        assert "total_spending" in result
        assert "spending_by_category" in result
        assert "spending_by_day" in result
        assert "transaction_count" in result
    
    @pytest.mark.asyncio
    async def test_analyze_spending_calculates_totals(self, context_manager, mock_repos):
        """Test that analyze spending calculates totals correctly"""
        # Setup mocks with multiple transactions
        mock_repos["transaction_repo"].get_by_user_and_date_range = AsyncMock(return_value=[
            {"date": datetime.now(), "merchant": "Starbucks", "amount": -5.50, "category": "Food", "currency": "USD"},
            {"date": datetime.now(), "merchant": "Uber", "amount": -12.00, "category": "Transport", "currency": "USD"},
            {"date": datetime.now(), "merchant": "Starbucks", "amount": -6.00, "category": "Food", "currency": "USD"}
        ])
        
        # Test
        result = await context_manager.get_analyze_spending_context(user_id="user_123")
        
        assert result["total_spending"] == pytest.approx(23.50, 0.01)
        assert result["spending_by_category"]["Food"] == pytest.approx(11.50, 0.01)
        assert result["spending_by_category"]["Transport"] == pytest.approx(12.00, 0.01)
        assert result["transaction_count"] == 3
    
    @pytest.mark.asyncio
    async def test_analyze_spending_with_no_transactions(self, context_manager, mock_repos):
        """Test analyze spending with no transactions"""
        # Setup mocks
        mock_repos["transaction_repo"].get_by_user_and_date_range = AsyncMock(return_value=[])
        
        # Test
        result = await context_manager.get_analyze_spending_context(user_id="user_123")
        
        assert result["total_spending"] == 0.0
        assert result["spending_by_category"] == {}
        assert result["transaction_count"] == 0
    
    @pytest.mark.asyncio
    async def test_get_budget_recommendation_context_returns_dict(self, context_manager, mock_repos):
        """Test that get_budget_recommendation_context returns a dict"""
        # Setup mocks
        mock_repos["user_repo"].get_by_id = AsyncMock(return_value={
            "monthly_income": 5000.00,
            "financial_goals": "Save for vacation"
        })
        mock_repos["transaction_repo"].get_by_user_and_date_range = AsyncMock(return_value=[
            {"date": datetime.now(), "amount": -100.00, "category": "Food", "currency": "USD"}
        ])
        
        # Test
        result = await context_manager.get_budget_recommendation_context(user_id="user_123")
        
        assert isinstance(result, dict)
        assert "user_id" in result
        assert "monthly_income" in result
        assert "avg_monthly_spending" in result
        assert "spending_by_category" in result
    
    @pytest.mark.asyncio
    async def test_get_user_categories_returns_defaults_on_empty(self, context_manager, mock_repos):
        """Test that _get_user_categories returns defaults when user has no categories"""
        # Setup mocks
        mock_repos["category_repo"].get_by_user = AsyncMock(return_value=[])
        
        # Test
        result = await context_manager._get_user_categories("user_123")
        
        assert isinstance(result, list)
        assert len(result) > 0
        assert "Food" in result
        assert "Other" in result
    
    @pytest.mark.asyncio
    async def test_get_user_categories_handles_error(self, context_manager, mock_repos):
        """Test that _get_user_categories handles errors gracefully"""
        # Setup mocks to raise error
        mock_repos["category_repo"].get_by_user = AsyncMock(side_effect=Exception("DB error"))
        
        # Test
        result = await context_manager._get_user_categories("user_123")
        
        assert isinstance(result, list)
        assert result == ["Other"]
    
    @pytest.mark.asyncio
    async def test_get_recent_transactions_formats_correctly(self, context_manager, mock_repos):
        """Test that _get_recent_transactions formats data correctly"""
        # Setup mocks
        mock_repos["transaction_repo"].get_by_user_and_date_range = AsyncMock(return_value=[
            {
                "date": datetime(2025, 11, 29),
                "merchant": "Starbucks",
                "amount": -5.50,
                "category": "Food"
            }
        ])
        
        # Test
        result = await context_manager._get_recent_transactions("user_123")
        
        assert len(result) == 1
        assert result[0]["merchant"] == "Starbucks"
        assert result[0]["amount"] == 5.50  # Absolute value
        assert result[0]["category"] == "Food"
    
    @pytest.mark.asyncio
    async def test_get_merchant_mappings_formats_correctly(self, context_manager, mock_repos):
        """Test that _get_merchant_mappings formats data correctly"""
        # Setup mocks
        mock_repos["merchant_repo"].get_by_user = AsyncMock(return_value=[
            {"merchant_name": "Starbucks", "category": "Food"},
            {"merchant_name": "Uber", "category": "Transport"}
        ])
        
        # Test
        result = await context_manager._get_merchant_mappings("user_123")
        
        assert len(result) == 2
        assert result[0]["merchant_name"] == "Starbucks"
        assert result[0]["category"] == "Food"
    
    def test_manage_tokens_within_limit(self, context_manager):
        """Test that _manage_tokens doesn't limit when within MAX_TOKENS"""
        transactions = [{"date": "2025-11-29", "merchant": "Test", "amount": 10.0}] * 5
        mappings = [{"merchant_name": "Test", "category": "Food"}] * 5
        
        limited_txs, limited_mappings = context_manager._manage_tokens(transactions, mappings)
        
        assert len(limited_txs) == 5
        assert len(limited_mappings) == 5
    
    def test_manage_tokens_limits_when_over(self, context_manager):
        """Test that _manage_tokens limits context when over MAX_TOKENS"""
        # Create large context
        transactions = [{"date": "2025-11-29", "merchant": "Test", "amount": 10.0}] * 100
        mappings = [{"merchant_name": "Test", "category": "Food"}] * 100
        
        limited_txs, limited_mappings = context_manager._manage_tokens(transactions, mappings)
        
        # Should be limited
        assert len(limited_txs) < 100
        assert len(limited_mappings) < 100
        
        # Estimate tokens should be under limit
        estimated_tokens = (
            len(limited_txs) * context_manager.TOKENS_PER_TRANSACTION +
            len(limited_mappings) * context_manager.TOKENS_PER_MERCHANT
        )
        assert estimated_tokens <= context_manager.MAX_TOKENS
