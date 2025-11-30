"""
Unit tests for PromptLibrary
"""
import pytest
from src.app.services.prompt_library import PromptLibrary


class TestPromptLibrary:
    """Test suite for PromptLibrary"""
    
    @pytest.fixture
    def prompt_library(self):
        """Create PromptLibrary instance"""
        return PromptLibrary()
    
    @pytest.fixture
    def categorization_context(self):
        """Sample context for categorization"""
        return {
            "user_id": "user_123",
            "user_categories": ["Food", "Transport", "Shopping", "Entertainment"],
            "recent_transactions": [
                {"date": "2025-11-29", "merchant": "Starbucks", "amount": 5.50, "category": "Food"},
                {"date": "2025-11-28", "merchant": "Uber", "amount": 12.00, "category": "Transport"}
            ],
            "merchant_mappings": [
                {"merchant_name": "Starbucks", "category": "Food"},
                {"merchant_name": "Uber", "category": "Transport"}
            ],
            "description": "Coffee purchase",
            "merchant": "Starbucks Downtown",
            "amount": 6.75,
            "currency": "USD"
        }
    
    @pytest.fixture
    def analyze_spending_context(self):
        """Sample context for spending analysis"""
        return {
            "user_id": "user_123",
            "total_spending": 1250.00,
            "spending_by_category": {
                "Food": 450.00,
                "Transport": 300.00,
                "Shopping": 350.00,
                "Entertainment": 150.00
            },
            "spending_by_day": {
                "Monday": 180.00,
                "Tuesday": 200.00,
                "Wednesday": 170.00,
                "Thursday": 220.00,
                "Friday": 250.00,
                "Saturday": 130.00,
                "Sunday": 100.00
            },
            "transaction_count": 45,
            "currency": "USD"
        }
    
    def test_get_categorization_prompt_returns_list(self, prompt_library, categorization_context):
        """Test that get_categorization_prompt returns a list"""
        result = prompt_library.get_categorization_prompt(categorization_context)
        assert isinstance(result, list)
        assert len(result) > 0
    
    def test_categorization_prompt_has_correct_structure(self, prompt_library, categorization_context):
        """Test that categorization prompt has correct message structure"""
        result = prompt_library.get_categorization_prompt(categorization_context)
        assert len(result) == 1
        assert "role" in result[0]
        assert "content" in result[0]
        assert result[0]["role"] == "user"
    
    def test_categorization_prompt_includes_context(self, prompt_library, categorization_context):
        """Test that categorization prompt includes all context elements"""
        result = prompt_library.get_categorization_prompt(categorization_context)
        content = result[0]["content"]
        
        # Check that key context elements are present
        assert "user_123" in content
        assert "Food" in content
        assert "Transport" in content
        assert "Starbucks" in content
        assert "6.75" in content
        assert "USD" in content
    
    def test_categorization_prompt_with_empty_transactions(self, prompt_library):
        """Test categorization prompt with no recent transactions"""
        context = {
            "user_id": "user_123",
            "user_categories": ["Food"],
            "recent_transactions": [],
            "merchant_mappings": [],
            "description": "Test",
            "merchant": "Test Merchant",
            "amount": 10.00,
            "currency": "USD"
        }
        result = prompt_library.get_categorization_prompt(context)
        content = result[0]["content"]
        
        assert "No recent transactions" in content
        assert "No known merchant mappings" in content
    
    def test_categorization_prompt_limits_transactions(self, prompt_library):
        """Test that categorization prompt limits recent transactions to 10"""
        context = {
            "user_id": "user_123",
            "user_categories": ["Food"],
            "recent_transactions": [
                {"date": f"2025-11-{i:02d}", "merchant": f"Merchant{i}", "amount": 10.00, "category": "Food"}
                for i in range(1, 21)  # 20 transactions
            ],
            "merchant_mappings": [],
            "description": "Test",
            "merchant": "Test",
            "amount": 10.00,
            "currency": "USD"
        }
        result = prompt_library.get_categorization_prompt(context)
        content = result[0]["content"]
        
        # Should only include first 10
        assert "Merchant1" in content
        assert "Merchant10" in content
        assert "Merchant11" not in content
    
    def test_get_analyze_spending_prompt_returns_list(self, prompt_library, analyze_spending_context):
        """Test that get_analyze_spending_prompt returns a list"""
        result = prompt_library.get_analyze_spending_prompt(analyze_spending_context)
        assert isinstance(result, list)
        assert len(result) > 0
    
    def test_analyze_spending_prompt_includes_context(self, prompt_library, analyze_spending_context):
        """Test that analyze spending prompt includes all context elements"""
        result = prompt_library.get_analyze_spending_prompt(analyze_spending_context)
        content = result[0]["content"]
        
        assert "user_123" in content
        assert "1250.00" in content or "1250.0" in content
        assert "Food" in content
        assert "450.00" in content or "450.0" in content
        assert "Monday" in content
    
    def test_get_budget_recommendation_prompt_returns_list(self, prompt_library):
        """Test that get_budget_recommendation_prompt returns a list"""
        context = {
            "user_id": "user_123",
            "monthly_income": 5000.00,
            "avg_monthly_spending": 3500.00,
            "spending_by_category": {"Food": 800.00, "Transport": 500.00},
            "financial_goals": "Save for vacation",
            "currency": "USD"
        }
        result = prompt_library.get_budget_recommendation_prompt(context)
        assert isinstance(result, list)
        assert len(result) > 0
    
    def test_budget_recommendation_prompt_includes_context(self, prompt_library):
        """Test that budget recommendation prompt includes all context elements"""
        context = {
            "user_id": "user_123",
            "monthly_income": 5000.00,
            "avg_monthly_spending": 3500.00,
            "spending_by_category": {"Food": 800.00},
            "financial_goals": "Save for vacation",
            "currency": "USD"
        }
        result = prompt_library.get_budget_recommendation_prompt(context)
        content = result[0]["content"]
        
        assert "user_123" in content
        assert "5000" in content
        assert "3500" in content
        assert "vacation" in content
    
    def test_get_find_anomalies_prompt_returns_list(self, prompt_library):
        """Test that get_find_anomalies_prompt returns a list"""
        context = {
            "user_id": "user_123",
            "recent_transactions": [
                {"id": "tx_1", "date": "2025-11-29", "merchant": "Test", "amount": 100.00}
            ],
            "typical_patterns": {"avg_transaction": 50.00}
        }
        result = prompt_library.get_find_anomalies_prompt(context)
        assert isinstance(result, list)
        assert len(result) > 0
    
    def test_find_anomalies_prompt_includes_context(self, prompt_library):
        """Test that anomaly detection prompt includes all context elements"""
        context = {
            "user_id": "user_123",
            "recent_transactions": [
                {"id": "tx_1", "date": "2025-11-29", "merchant": "Test", "amount": 100.00}
            ],
            "typical_patterns": {"avg_transaction": 50.00}
        }
        result = prompt_library.get_find_anomalies_prompt(context)
        content = result[0]["content"]
        
        assert "user_123" in content
        assert "tx_1" in content
        assert "Test" in content
    
    def test_all_prompts_are_non_empty(self, prompt_library):
        """Test that all prompt templates are non-empty strings"""
        assert len(prompt_library.CATEGORIZATION_PROMPT) > 0
        assert len(prompt_library.ANALYZE_SPENDING_PROMPT) > 0
        assert len(prompt_library.BUDGET_RECOMMENDATION_PROMPT) > 0
        assert len(prompt_library.FIND_ANOMALIES_PROMPT) > 0
    
    def test_categorization_prompt_mentions_json_output(self, prompt_library):
        """Test that categorization prompt specifies JSON output"""
        assert "JSON" in prompt_library.CATEGORIZATION_PROMPT
        assert "category" in prompt_library.CATEGORIZATION_PROMPT
        assert "confidence" in prompt_library.CATEGORIZATION_PROMPT
