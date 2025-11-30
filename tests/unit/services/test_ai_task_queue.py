"""
Tests for AI Task Queue Service
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from src.app.services.ai_task_queue import AITaskQueue, TaskStatus


@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    redis_mock = AsyncMock()
    redis_mock.setex = AsyncMock()
    redis_mock.zadd = AsyncMock()
    redis_mock.zrange = AsyncMock()
    redis_mock.zrem = AsyncMock()
    redis_mock.get = AsyncMock()
    redis_mock.zcard = AsyncMock()
    redis_mock.delete = AsyncMock()
    redis_mock.close = AsyncMock()
    return redis_mock


@pytest.fixture
async def task_queue(mock_redis):
    """Create AITaskQueue instance with mocked Redis"""
    queue = AITaskQueue("redis://localhost:6379")
    
    # Mock from_url to return our mock_redis
    async def mock_from_url(*args, **kwargs):
        return mock_redis
    
    with patch('redis.asyncio.from_url', side_effect=mock_from_url):
        await queue.connect()
        yield queue
        await queue.disconnect()


class TestAITaskQueue:
    """Test AITaskQueue functionality"""
    
    @pytest.mark.asyncio
    async def test_enqueue_task(self, task_queue, mock_redis):
        """Test enqueueing a task"""
        task_data = {"transaction_id": "tx123", "amount": 100}
        
        task_id = await task_queue.enqueue_task(
            task_type="categorize_transaction",
            data=task_data,
            priority=1,
            user_id="user123"
        )
        
        # Verify task ID format
        assert task_id.startswith("categorize_transaction:")
        
        # Verify Redis calls
        assert mock_redis.setex.called
        assert mock_redis.zadd.called
    
    @pytest.mark.asyncio
    async def test_dequeue_task(self, task_queue, mock_redis):
        """Test dequeueing a task"""
        task_id = "categorize_transaction:abc123"
        task_data = {
            "task_id": task_id,
            "task_type": "categorize_transaction",
            "data": {"amount": 100},
            "priority": 1
        }
        
        # Mock Redis responses
        mock_redis.zrange.return_value = [task_id]
        mock_redis.get.return_value = '{"task_id": "' + task_id + '", "task_type": "categorize_transaction", "data": {"amount": 100}, "priority": 1}'
        
        result = await task_queue.dequeue_task()
        
        assert result is not None
        assert result["task_id"] == task_id
        assert result["task_type"] == "categorize_transaction"
        
        # Verify Redis calls
        assert mock_redis.zrange.called
        assert mock_redis.zrem.called
        assert mock_redis.get.called
    
    @pytest.mark.asyncio
    async def test_dequeue_empty_queue(self, task_queue, mock_redis):
        """Test dequeueing from empty queue"""
        mock_redis.zrange.return_value = []
        
        result = await task_queue.dequeue_task()
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_store_result(self, task_queue, mock_redis):
        """Test storing task result"""
        task_id = "categorize_transaction:abc123"
        result = {"category": "Food", "confidence": 0.95}
        
        await task_queue.store_result(task_id, result, TaskStatus.COMPLETED)
        
        # Verify Redis calls
        assert mock_redis.setex.called
        
        # Check that result was stored with correct TTL
        call_args = mock_redis.setex.call_args_list
        assert any(str(task_queue.RESULT_TTL) in str(args) for args in call_args)
    
    @pytest.mark.asyncio
    async def test_get_task_status(self, task_queue, mock_redis):
        """Test getting task status"""
        task_id = "categorize_transaction:abc123"
        mock_redis.get.return_value = TaskStatus.PROCESSING
        
        status = await task_queue.get_task_status(task_id)
        
        assert status == TaskStatus.PROCESSING
        assert mock_redis.get.called
    
    @pytest.mark.asyncio
    async def test_get_queue_size(self, task_queue, mock_redis):
        """Test getting queue size"""
        mock_redis.zcard.return_value = 5
        
        size = await task_queue.get_queue_size()
        
        assert size == 5
        assert mock_redis.zcard.called
    
    @pytest.mark.asyncio
    async def test_clear_queue(self, task_queue, mock_redis):
        """Test clearing queue"""
        await task_queue.clear_queue()
        
        assert mock_redis.delete.called
    
    @pytest.mark.asyncio
    async def test_priority_ordering(self, task_queue, mock_redis):
        """Test that tasks are ordered by priority"""
        # Enqueue high priority task
        await task_queue.enqueue_task(
            task_type="test",
            data={},
            priority=1
        )
        
        # Enqueue low priority task
        await task_queue.enqueue_task(
            task_type="test",
            data={},
            priority=3
        )
        
        # Verify that zadd was called with correct scores
        # High priority (1) should have lower score than low priority (3)
        zadd_calls = mock_redis.zadd.call_args_list
        assert len(zadd_calls) == 2
        
        # Extract scores from calls
        scores = []
        for call in zadd_calls:
            # call[0] is positional args, call[1] is kwargs
            if len(call[0]) > 1:
                task_dict = call[0][1]
                scores.extend(task_dict.values())
        
        # Verify high priority has lower score
        assert len(scores) == 2
        assert scores[0] < scores[1]  # priority 1 < priority 3


class TestTaskStatus:
    """Test TaskStatus constants"""
    
    def test_status_constants(self):
        """Test that all status constants are defined"""
        assert TaskStatus.PENDING == "pending"
        assert TaskStatus.PROCESSING == "processing"
        assert TaskStatus.COMPLETED == "completed"
        assert TaskStatus.FAILED == "failed"
        assert TaskStatus.TIMEOUT == "timeout"
