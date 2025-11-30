"""
Unit tests for Redis-based ConfirmationService
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
import json
from src.app.services.confirmation_service import ConfirmationService


@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    redis_mock = AsyncMock()
    redis_mock.setex = AsyncMock()
    redis_mock.get = AsyncMock()
    redis_mock.delete = AsyncMock()
    redis_mock.sadd = AsyncMock()
    redis_mock.srem = AsyncMock()
    redis_mock.scard = AsyncMock()
    redis_mock.expire = AsyncMock()
    redis_mock.scan = AsyncMock()
    redis_mock.ttl = AsyncMock()
    return redis_mock


@pytest.fixture
def mock_repos():
    """Mock repositories"""
    return {
        "transaction_repo": AsyncMock(),
        "category_repo": AsyncMock(),
        "merchant_repo": AsyncMock()
    }


@pytest.fixture
def confirmation_service(mock_redis, mock_repos):
    """Create ConfirmationService with mocked dependencies"""
    return ConfirmationService(
        transaction_repo=mock_repos["transaction_repo"],
        category_repo=mock_repos["category_repo"],
        merchant_repo=mock_repos["merchant_repo"],
        redis_client=mock_redis
    )


@pytest.mark.asyncio
async def test_create_confirmation_request(confirmation_service, mock_redis):
    """Test creating confirmation request in Redis"""
    user_id = "123"
    transaction_data = {
        "id": "tx_1",
        "amount": 100.0,
        "merchant": "Starbucks"
    }
    ai_suggestion = {
        "category": "Food & Drinks",
        "confidence": 0.75
    }
    
    # Create confirmation
    confirmation_id = await confirmation_service.create_confirmation_request(
        user_id=user_id,
        transaction_data=transaction_data,
        ai_suggestion=ai_suggestion
    )
    
    # Verify confirmation ID format
    assert confirmation_id.startswith(f"conf_{user_id}_")
    
    # Verify Redis calls
    assert mock_redis.setex.called
    assert mock_redis.sadd.called
    assert mock_redis.expire.called


@pytest.mark.asyncio
async def test_get_confirmation_message(confirmation_service, mock_redis, mock_repos):
    """Test getting confirmation message from Redis"""
    confirmation_id = "conf_123_1234567890"
    
    # Mock Redis response
    confirmation_data = {
        "user_id": "123",
        "transaction_data": {
            "id": "tx_1",
            "amount": 100.0,
            "merchant": "Starbucks",
            "currency": "USD",
            "timestamp": "2025-11-30"
        },
        "ai_suggestion": {
            "category": "Food & Drinks",
            "confidence": 0.75,
            "reasoning": "Coffee shop"
        },
        "created_at": datetime.now().isoformat(),
        "expires_at": (datetime.now() + timedelta(hours=24)).isoformat()
    }
    mock_redis.get.return_value = json.dumps(confirmation_data)
    
    # Mock categories
    mock_repos["category_repo"].get_by_user.return_value = [
        {"name": "Food & Drinks"},
        {"name": "Transport"},
        {"name": "Shopping"}
    ]
    
    # Get message
    message = await confirmation_service.get_confirmation_message(confirmation_id)
    
    # Verify message structure
    assert message is not None
    assert "text" in message
    assert "confirmation_id" in message
    assert "suggested_category" in message
    assert "categories" in message
    assert message["suggested_category"] == "Food & Drinks"


@pytest.mark.asyncio
async def test_get_confirmation_message_expired(confirmation_service, mock_redis):
    """Test getting expired confirmation returns None"""
    confirmation_id = "conf_123_1234567890"
    
    # Mock expired confirmation
    confirmation_data = {
        "user_id": "123",
        "transaction_data": {},
        "ai_suggestion": {},
        "created_at": (datetime.now() - timedelta(days=2)).isoformat(),
        "expires_at": (datetime.now() - timedelta(days=1)).isoformat()
    }
    mock_redis.get.return_value = json.dumps(confirmation_data)
    
    # Get message
    message = await confirmation_service.get_confirmation_message(confirmation_id)
    
    # Verify returns None and deletes from Redis
    assert message is None
    assert mock_redis.delete.called


@pytest.mark.asyncio
async def test_process_confirmation_success(confirmation_service, mock_redis, mock_repos):
    """Test successful confirmation processing"""
    confirmation_id = "conf_123_1234567890"
    user_id = "123"
    confirmed_category = "Food & Drinks"
    
    # Mock Redis response
    confirmation_data = {
        "user_id": user_id,
        "transaction_data": {
            "id": "tx_1",
            "merchant": "Starbucks"
        },
        "ai_suggestion": {
            "category": "Food & Drinks",
            "confidence": 0.75
        }
    }
    mock_redis.get.return_value = json.dumps(confirmation_data)
    
    # Mock successful transaction update
    mock_repos["transaction_repo"].update = AsyncMock()
    
    # Process confirmation
    success = await confirmation_service.process_confirmation(
        confirmation_id=confirmation_id,
        confirmed_category=confirmed_category,
        user_id=user_id
    )
    
    # Verify success
    assert success is True
    assert mock_repos["transaction_repo"].update.called
    assert mock_redis.delete.called
    assert mock_redis.srem.called


@pytest.mark.asyncio
async def test_process_confirmation_wrong_user(confirmation_service, mock_redis):
    """Test confirmation processing with wrong user"""
    confirmation_id = "conf_123_1234567890"
    
    # Mock Redis response with different user
    confirmation_data = {
        "user_id": "123",
        "transaction_data": {},
        "ai_suggestion": {}
    }
    mock_redis.get.return_value = json.dumps(confirmation_data)
    
    # Try to process with wrong user
    success = await confirmation_service.process_confirmation(
        confirmation_id=confirmation_id,
        confirmed_category="Food",
        user_id="456"  # Different user
    )
    
    # Verify failure
    assert success is False


@pytest.mark.asyncio
async def test_learn_from_correction(confirmation_service, mock_redis, mock_repos):
    """Test learning from user correction"""
    confirmation_id = "conf_123_1234567890"
    user_id = "123"
    
    # Mock Redis response with different category
    confirmation_data = {
        "user_id": user_id,
        "transaction_data": {
            "id": "tx_1",
            "merchant": "Starbucks"
        },
        "ai_suggestion": {
            "category": "Shopping",  # AI suggested wrong category
            "confidence": 0.75
        }
    }
    mock_redis.get.return_value = json.dumps(confirmation_data)
    
    # Mock merchant repo
    mock_repos["merchant_repo"].get_by_merchant.return_value = None
    mock_repos["merchant_repo"].create = AsyncMock()
    mock_repos["transaction_repo"].update = AsyncMock()
    
    # Process confirmation with correction
    success = await confirmation_service.process_confirmation(
        confirmation_id=confirmation_id,
        confirmed_category="Food & Drinks",  # User corrects
        user_id=user_id
    )
    
    # Verify learning occurred
    assert success is True
    assert mock_repos["merchant_repo"].create.called


@pytest.mark.asyncio
async def test_get_pending_count(confirmation_service, mock_redis):
    """Test getting pending count from Redis"""
    user_id = "123"
    
    # Mock Redis response
    mock_redis.scard.return_value = 5
    
    # Get count
    count = await confirmation_service.get_pending_count(user_id)
    
    # Verify count
    assert count == 5
    assert mock_redis.scard.called


@pytest.mark.asyncio
async def test_cleanup_expired(confirmation_service, mock_redis):
    """Test cleanup of expired confirmations"""
    # Mock Redis scan response
    mock_redis.scan.return_value = (0, [
        b"confirmation:conf_123_1",
        b"confirmation:conf_123_2"
    ])
    mock_redis.ttl.return_value = -2  # Key doesn't exist
    
    # Run cleanup
    await confirmation_service.cleanup_expired()
    
    # Verify scan was called
    assert mock_redis.scan.called
