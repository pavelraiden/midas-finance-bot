"""
Unit tests for DeepSeekWorker confidence-based flows
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime


class TestDeepSeekWorkerConfidence:
    """Test confidence-based auto-confirmation logic"""
    
    @pytest.fixture
    def worker(self):
        """Create DeepSeekWorker instance with mocked dependencies"""
        with patch('src.worker.AITaskQueue'), \
             patch('src.worker.DeepSeekService'), \
             patch('src.worker.Database'), \
             patch('src.worker.UserRepository'), \
             patch('src.worker.TransactionRepository'), \
             patch('src.worker.CategoryRepository'), \
             patch('src.worker.MerchantRepository'), \
             patch('src.worker.ContextManager'), \
             patch('src.worker.PromptLibrary'):
            
            from src.worker import DeepSeekWorker
            worker = DeepSeekWorker()
            
            # Mock repositories
            worker.merchant_repo = AsyncMock()
            worker.context_manager = AsyncMock()
            worker.prompt_library = Mock()
            worker.deepseek_service = Mock()
            
            return worker
    
    @pytest.mark.asyncio
    async def test_high_confidence_auto_confirm(self, worker):
        """Test high confidence (>=95%) auto-confirms"""
        # Mock context and prompt
        worker.context_manager.get_categorization_context.return_value = {
            "user_categories": ["Food", "Transport"],
            "recent_transactions": []
        }
        worker.prompt_library.get_categorization_prompt.return_value = []
        
        # Mock AI response with high confidence
        ai_response = {
            "category": "Food",
            "confidence": 0.97,
            "reasoning": "Clear food purchase"
        }
        worker.deepseek_service._make_request.return_value = str(ai_response).replace("'", '"')
        
        # Execute
        result = await worker._categorize_transaction({
            "user_id": "user_123",
            "merchant": "Starbucks",
            "amount": 5.50
        })
        
        # Verify auto-confirmation
        assert result["auto_confirmed"] is True
        assert result["requires_confirmation"] is False
        assert "suggest_manual_review" not in result
        assert result["confidence"] == 0.97
    
    @pytest.mark.asyncio
    async def test_high_confidence_saves_merchant_mapping(self, worker):
        """Test high confidence saves new merchant mappings"""
        # Mock context and prompt
        worker.context_manager.get_categorization_context.return_value = {}
        worker.prompt_library.get_categorization_prompt.return_value = []
        
        # Mock AI response with merchant mapping
        ai_response = {
            "category": "Food",
            "confidence": 0.98,
            "reasoning": "Coffee shop",
            "new_merchant_mapping": {
                "merchant_name": "Starbucks",
                "suggested_category": "Food"
            }
        }
        worker.deepseek_service._make_request.return_value = str(ai_response).replace("'", '"')
        
        # Execute
        result = await worker._categorize_transaction({
            "user_id": "user_123",
            "merchant": "Starbucks",
            "amount": 5.50
        })
        
        # Verify merchant mapping was saved
        worker.merchant_repo.create.assert_called_once_with({
            "user_id": "user_123",
            "merchant_name": "Starbucks",
            "category": "Food"
        })
        assert result["auto_confirmed"] is True
    
    @pytest.mark.asyncio
    async def test_medium_confidence_requests_confirmation(self, worker):
        """Test medium confidence (70-95%) requests confirmation"""
        # Mock context and prompt
        worker.context_manager.get_categorization_context.return_value = {}
        worker.prompt_library.get_categorization_prompt.return_value = []
        
        # Mock AI response with medium confidence
        ai_response = {
            "category": "Shopping",
            "confidence": 0.85,
            "reasoning": "Unclear merchant category"
        }
        worker.deepseek_service._make_request.return_value = str(ai_response).replace("'", '"')
        
        # Execute
        result = await worker._categorize_transaction({
            "user_id": "user_123",
            "merchant": "Unknown Store",
            "amount": 25.00
        })
        
        # Verify confirmation request
        assert result["auto_confirmed"] is False
        assert result["requires_confirmation"] is True
        assert "suggest_manual_review" not in result
        assert result["confidence"] == 0.85
    
    @pytest.mark.asyncio
    async def test_low_confidence_suggests_manual_review(self, worker):
        """Test low confidence (<70%) suggests manual review"""
        # Mock context and prompt
        worker.context_manager.get_categorization_context.return_value = {}
        worker.prompt_library.get_categorization_prompt.return_value = []
        
        # Mock AI response with low confidence
        ai_response = {
            "category": "Other",
            "confidence": 0.45,
            "reasoning": "Insufficient information"
        }
        worker.deepseek_service._make_request.return_value = str(ai_response).replace("'", '"')
        
        # Execute
        result = await worker._categorize_transaction({
            "user_id": "user_123",
            "merchant": "???",
            "amount": 100.00
        })
        
        # Verify manual review suggestion
        assert result["auto_confirmed"] is False
        assert result["requires_confirmation"] is True
        assert result["suggest_manual_review"] is True
        assert result["confidence"] == 0.45
    
    @pytest.mark.asyncio
    async def test_threshold_boundary_95_percent(self, worker):
        """Test exact 95% threshold is auto-confirmed"""
        # Mock context and prompt
        worker.context_manager.get_categorization_context.return_value = {}
        worker.prompt_library.get_categorization_prompt.return_value = []
        
        # Mock AI response with exactly 95% confidence
        ai_response = {
            "category": "Transport",
            "confidence": 0.95,
            "reasoning": "Uber ride"
        }
        worker.deepseek_service._make_request.return_value = str(ai_response).replace("'", '"')
        
        # Execute
        result = await worker._categorize_transaction({
            "user_id": "user_123",
            "merchant": "Uber",
            "amount": 15.00
        })
        
        # Verify auto-confirmation (>= threshold)
        assert result["auto_confirmed"] is True
        assert result["requires_confirmation"] is False
    
    @pytest.mark.asyncio
    async def test_threshold_boundary_70_percent(self, worker):
        """Test exact 70% threshold requests confirmation"""
        # Mock context and prompt
        worker.context_manager.get_categorization_context.return_value = {}
        worker.prompt_library.get_categorization_prompt.return_value = []
        
        # Mock AI response with exactly 70% confidence
        ai_response = {
            "category": "Entertainment",
            "confidence": 0.70,
            "reasoning": "Possibly cinema"
        }
        worker.deepseek_service._make_request.return_value = str(ai_response).replace("'", '"')
        
        # Execute
        result = await worker._categorize_transaction({
            "user_id": "user_123",
            "merchant": "AMC",
            "amount": 20.00
        })
        
        # Verify confirmation request (>= medium threshold)
        assert result["auto_confirmed"] is False
        assert result["requires_confirmation"] is True
        assert "suggest_manual_review" not in result
    
    @pytest.mark.asyncio
    async def test_merchant_mapping_error_handling(self, worker):
        """Test graceful handling of merchant mapping errors"""
        # Mock context and prompt
        worker.context_manager.get_categorization_context.return_value = {}
        worker.prompt_library.get_categorization_prompt.return_value = []
        
        # Mock merchant repo to raise error
        worker.merchant_repo.create.side_effect = Exception("Database error")
        
        # Mock AI response with merchant mapping
        ai_response = {
            "category": "Food",
            "confidence": 0.98,
            "new_merchant_mapping": {
                "merchant_name": "Starbucks",
                "suggested_category": "Food"
            }
        }
        worker.deepseek_service._make_request.return_value = str(ai_response).replace("'", '"')
        
        # Execute - should not crash
        result = await worker._categorize_transaction({
            "user_id": "user_123",
            "merchant": "Starbucks",
            "amount": 5.50
        })
        
        # Verify still auto-confirmed despite mapping error
        assert result["auto_confirmed"] is True
        assert result["confidence"] == 0.98
