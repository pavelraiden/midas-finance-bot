"""
Unit tests for CryptoCardDetector
"""
import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timedelta
from src.app.services.crypto_card_detector import CryptoCardDetector


class TestCryptoCardDetector:
    """Test suite for CryptoCardDetector"""
    
    @pytest.fixture
    def mock_transaction_repo(self):
        """Create mock transaction repository"""
        repo = Mock()
        repo.update = AsyncMock()
        return repo
    
    @pytest.fixture
    def detector(self, mock_transaction_repo):
        """Create CryptoCardDetector instance"""
        return CryptoCardDetector(transaction_repo=mock_transaction_repo)
    
    @pytest.fixture
    def base_time(self):
        """Base timestamp for tests"""
        return datetime(2025, 11, 30, 12, 0, 0)
    
    @pytest.mark.asyncio
    async def test_perfect_match(self, detector, base_time):
        """Test perfect USDT→USDC swap detection"""
        transactions = [
            {
                "id": "usdt_1",
                "currency": "USDT",
                "amount": -100.0,
                "timestamp": base_time,
                "wallet_id": "wallet_1"
            },
            {
                "id": "usdc_1",
                "currency": "USDC",
                "amount": 100.0,
                "timestamp": base_time + timedelta(seconds=30),
                "wallet_id": "wallet_1"
            }
        ]
        
        result = await detector.find_usdt_usdc_swaps("user_123", transactions)
        
        assert len(result) == 1
        assert result[0]["category"] == "Crypto Card Top-up"
        assert result[0]["amount"] == 100.0
        assert result[0]["currency"] == "USDC"
        assert result[0]["metadata"]["usdt_tx_id"] == "usdt_1"
        assert result[0]["metadata"]["usdc_tx_id"] == "usdc_1"
        assert result[0]["metadata"]["confidence"] > 0.9
    
    @pytest.mark.asyncio
    async def test_match_with_fees(self, detector, base_time):
        """Test swap detection with 2% fee"""
        transactions = [
            {
                "id": "usdt_1",
                "currency": "USDT",
                "amount": -100.0,
                "timestamp": base_time,
                "wallet_id": "wallet_1"
            },
            {
                "id": "usdc_1",
                "currency": "USDC",
                "amount": 98.0,  # 2% fee
                "timestamp": base_time + timedelta(seconds=45),
                "wallet_id": "wallet_1"
            }
        ]
        
        result = await detector.find_usdt_usdc_swaps("user_123", transactions)
        
        assert len(result) == 1
        assert result[0]["amount"] == 98.0
        assert result[0]["metadata"]["fee"] == pytest.approx(2.0, 0.01)
        assert result[0]["metadata"]["confidence"] > 0.3  # Lower confidence due to fee
    
    @pytest.mark.asyncio
    async def test_no_match_time_window(self, detector, base_time):
        """Test no match when outside time window"""
        transactions = [
            {
                "id": "usdt_1",
                "currency": "USDT",
                "amount": -100.0,
                "timestamp": base_time,
                "wallet_id": "wallet_1"
            },
            {
                "id": "usdc_1",
                "currency": "USDC",
                "amount": 100.0,
                "timestamp": base_time + timedelta(minutes=10),  # Outside 5-minute window
                "wallet_id": "wallet_1"
            }
        ]
        
        result = await detector.find_usdt_usdc_swaps("user_123", transactions)
        
        assert len(result) == 0
    
    @pytest.mark.asyncio
    async def test_no_match_amount_tolerance(self, detector, base_time):
        """Test no match when amount difference exceeds tolerance"""
        transactions = [
            {
                "id": "usdt_1",
                "currency": "USDT",
                "amount": -100.0,
                "timestamp": base_time,
                "wallet_id": "wallet_1"
            },
            {
                "id": "usdc_1",
                "currency": "USDC",
                "amount": 95.0,  # 5% difference, exceeds 2% tolerance
                "timestamp": base_time + timedelta(seconds=30),
                "wallet_id": "wallet_1"
            }
        ]
        
        result = await detector.find_usdt_usdc_swaps("user_123", transactions)
        
        assert len(result) == 0
    
    @pytest.mark.asyncio
    async def test_multiple_swaps(self, detector, base_time):
        """Test detection of multiple swaps"""
        transactions = [
            # First swap
            {
                "id": "usdt_1",
                "currency": "USDT",
                "amount": -100.0,
                "timestamp": base_time,
                "wallet_id": "wallet_1"
            },
            {
                "id": "usdc_1",
                "currency": "USDC",
                "amount": 100.0,
                "timestamp": base_time + timedelta(seconds=30),
                "wallet_id": "wallet_1"
            },
            # Second swap
            {
                "id": "usdt_2",
                "currency": "USDT",
                "amount": -50.0,
                "timestamp": base_time + timedelta(minutes=10),
                "wallet_id": "wallet_1"
            },
            {
                "id": "usdc_2",
                "currency": "USDC",
                "amount": 50.0,
                "timestamp": base_time + timedelta(minutes=10, seconds=45),
                "wallet_id": "wallet_1"
            }
        ]
        
        result = await detector.find_usdt_usdc_swaps("user_123", transactions)
        
        assert len(result) == 2
        assert result[0]["metadata"]["usdt_tx_id"] == "usdt_1"
        assert result[1]["metadata"]["usdt_tx_id"] == "usdt_2"
    
    @pytest.mark.asyncio
    async def test_no_usdt_transactions(self, detector, base_time):
        """Test with no USDT transactions"""
        transactions = [
            {
                "id": "usdc_1",
                "currency": "USDC",
                "amount": 100.0,
                "timestamp": base_time,
                "wallet_id": "wallet_1"
            }
        ]
        
        result = await detector.find_usdt_usdc_swaps("user_123", transactions)
        
        assert len(result) == 0
    
    @pytest.mark.asyncio
    async def test_no_usdc_transactions(self, detector, base_time):
        """Test with no USDC transactions"""
        transactions = [
            {
                "id": "usdt_1",
                "currency": "USDT",
                "amount": -100.0,
                "timestamp": base_time,
                "wallet_id": "wallet_1"
            }
        ]
        
        result = await detector.find_usdt_usdc_swaps("user_123", transactions)
        
        assert len(result) == 0
    
    @pytest.mark.asyncio
    async def test_empty_transactions(self, detector):
        """Test with empty transaction list"""
        result = await detector.find_usdt_usdc_swaps("user_123", [])
        
        assert len(result) == 0
    
    @pytest.mark.asyncio
    async def test_filter_transactions(self, detector, base_time):
        """Test _filter_transactions method"""
        transactions = [
            {"id": "1", "currency": "USDT", "amount": -100.0, "timestamp": base_time},
            {"id": "2", "currency": "USDC", "amount": 100.0, "timestamp": base_time},
            {"id": "3", "currency": "BTC", "amount": 0.5, "timestamp": base_time},
            {"id": "4", "currency": "USDT", "amount": 50.0, "timestamp": base_time},  # Positive USDT (not swap)
            {"id": "5", "currency": "USDC", "amount": -50.0, "timestamp": base_time},  # Negative USDC (not swap)
        ]
        
        usdt_out, usdc_in = detector._filter_transactions(transactions)
        
        assert len(usdt_out) == 1
        assert usdt_out[0]["id"] == "1"
        assert len(usdc_in) == 1
        assert usdc_in[0]["id"] == "2"
    
    @pytest.mark.asyncio
    async def test_best_match_selection(self, detector, base_time):
        """Test that best match is selected when multiple candidates exist"""
        transactions = [
            {
                "id": "usdt_1",
                "currency": "USDT",
                "amount": -100.0,
                "timestamp": base_time,
                "wallet_id": "wallet_1"
            },
            # Two potential matches - should pick the closer one
            {
                "id": "usdc_1",
                "currency": "USDC",
                "amount": 100.0,
                "timestamp": base_time + timedelta(minutes=2),  # Further away
                "wallet_id": "wallet_1"
            },
            {
                "id": "usdc_2",
                "currency": "USDC",
                "amount": 100.0,
                "timestamp": base_time + timedelta(seconds=30),  # Closer
                "wallet_id": "wallet_1"
            }
        ]
        
        result = await detector.find_usdt_usdc_swaps("user_123", transactions)
        
        assert len(result) == 1
        assert result[0]["metadata"]["usdc_tx_id"] == "usdc_2"  # Should pick closer match
    
    @pytest.mark.asyncio
    async def test_mark_as_internal_transfer(self, detector, mock_transaction_repo):
        """Test marking transactions as internal transfers"""
        tx_ids = ["tx_1", "tx_2", "tx_3"]
        
        count = await detector.mark_as_internal_transfer(tx_ids)
        
        assert count == 3
        assert mock_transaction_repo.update.call_count == 3
    
    @pytest.mark.asyncio
    async def test_mark_as_internal_transfer_empty(self, detector, mock_transaction_repo):
        """Test marking with empty list"""
        count = await detector.mark_as_internal_transfer([])
        
        assert count == 0
        assert mock_transaction_repo.update.call_count == 0
    
    @pytest.mark.asyncio
    async def test_confidence_scoring(self, detector, base_time):
        """Test confidence scoring for different match qualities"""
        # Perfect match (time + amount)
        perfect_match = [
            {
                "id": "usdt_1",
                "currency": "USDT",
                "amount": -100.0,
                "timestamp": base_time,
                "wallet_id": "wallet_1"
            },
            {
                "id": "usdc_1",
                "currency": "USDC",
                "amount": 100.0,
                "timestamp": base_time + timedelta(seconds=10),
                "wallet_id": "wallet_1"
            }
        ]
        
        result_perfect = await detector.find_usdt_usdc_swaps("user_123", perfect_match)
        
        # Good match (time ok, amount with fee)
        good_match = [
            {
                "id": "usdt_2",
                "currency": "USDT",
                "amount": -100.0,
                "timestamp": base_time,
                "wallet_id": "wallet_1"
            },
            {
                "id": "usdc_2",
                "currency": "USDC",
                "amount": 98.0,  # 2% fee
                "timestamp": base_time + timedelta(seconds=10),
                "wallet_id": "wallet_1"
            }
        ]
        
        result_good = await detector.find_usdt_usdc_swaps("user_123", good_match)
        
        # Verify perfect match has higher confidence
        assert result_perfect[0]["metadata"]["confidence"] > result_good[0]["metadata"]["confidence"]
        assert result_perfect[0]["metadata"]["confidence"] > 0.9
        assert result_good[0]["metadata"]["confidence"] > 0.3  # Lower confidence due to fee
