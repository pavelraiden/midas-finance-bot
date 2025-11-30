"""
AI Task Queue Service
Manages async AI processing tasks using Redis as backend
Based on AI Council recommendations (Claude 3.7)
"""
import json
import time
import uuid
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import redis.asyncio as redis

logger = logging.getLogger(__name__)


class TaskStatus:
    """Task status constants"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class AITaskQueue:
    """
    Redis-based task queue for async AI processing.
    
    Features:
    - Priority-based task ordering (sorted set)
    - Task result caching
    - Timeout handling
    - Task status tracking
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        """
        Initialize AI Task Queue.
        
        Args:
            redis_url: Redis connection URL
        """
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
        
        # Redis keys
        self.TASK_QUEUE_KEY = "ai:tasks:queue"
        self.TASK_DATA_PREFIX = "ai:tasks:data:"
        self.TASK_RESULT_PREFIX = "ai:tasks:result:"
        self.TASK_STATUS_PREFIX = "ai:tasks:status:"
        
        # Configuration
        self.TASK_TIMEOUT = 300  # 5 minutes
        self.RESULT_TTL = 3600  # 1 hour
    
    async def connect(self):
        """Connect to Redis"""
        if not self.redis_client:
            self.redis_client = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            logger.info(f"✅ Connected to Redis at {self.redis_url}")
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis connection closed")
    
    async def enqueue_task(
        self,
        task_type: str,
        data: Dict[str, Any],
        priority: int = 1,
        user_id: Optional[str] = None
    ) -> str:
        """
        Enqueue a new AI task.
        
        Args:
            task_type: Type of task (e.g., "categorize_transaction", "analyze_spending")
            data: Task data
            priority: Task priority (1=high, 2=medium, 3=low)
            user_id: Optional user ID for tracking
        
        Returns:
            task_id: Unique task ID
        """
        await self.connect()
        
        # Generate task ID
        task_id = f"{task_type}:{uuid.uuid4().hex[:12]}"
        
        # Prepare task data
        task_data = {
            "task_id": task_id,
            "task_type": task_type,
            "data": data,
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "priority": priority
        }
        
        # Store task data
        task_data_key = f"{self.TASK_DATA_PREFIX}{task_id}"
        await self.redis_client.setex(
            task_data_key,
            self.TASK_TIMEOUT,
            json.dumps(task_data)
        )
        
        # Add to priority queue (sorted set)
        # Score = priority * 1000000 + timestamp (lower score = higher priority)
        score = priority * 1000000 + int(time.time())
        await self.redis_client.zadd(self.TASK_QUEUE_KEY, {task_id: score})
        
        # Set initial status
        await self._set_task_status(task_id, TaskStatus.PENDING)
        
        logger.info(f"📥 Enqueued task: {task_id} (priority={priority})")
        return task_id
    
    async def dequeue_task(self) -> Optional[Dict[str, Any]]:
        """
        Dequeue the highest priority task.
        
        Returns:
            Task data or None if queue is empty
        """
        await self.connect()
        
        # Get highest priority task (lowest score)
        tasks = await self.redis_client.zrange(self.TASK_QUEUE_KEY, 0, 0)
        
        if not tasks:
            return None
        
        task_id = tasks[0]
        
        # Remove from queue
        await self.redis_client.zrem(self.TASK_QUEUE_KEY, task_id)
        
        # Get task data
        task_data_key = f"{self.TASK_DATA_PREFIX}{task_id}"
        task_data_json = await self.redis_client.get(task_data_key)
        
        if not task_data_json:
            logger.warning(f"Task data not found for {task_id}")
            return None
        
        task_data = json.loads(task_data_json)
        
        # Update status
        await self._set_task_status(task_id, TaskStatus.PROCESSING)
        
        logger.info(f"📤 Dequeued task: {task_id}")
        return task_data
    
    async def store_result(
        self,
        task_id: str,
        result: Any,
        status: str = TaskStatus.COMPLETED
    ):
        """
        Store task result.
        
        Args:
            task_id: Task ID
            result: Task result
            status: Task status
        """
        await self.connect()
        
        # Store result
        result_key = f"{self.TASK_RESULT_PREFIX}{task_id}"
        result_data = {
            "task_id": task_id,
            "result": result,
            "status": status,
            "completed_at": datetime.utcnow().isoformat()
        }
        
        await self.redis_client.setex(
            result_key,
            self.RESULT_TTL,
            json.dumps(result_data)
        )
        
        # Update status
        await self._set_task_status(task_id, status)
        
        logger.info(f"✅ Stored result for task: {task_id} (status={status})")
    
    async def get_result(self, task_id: str, timeout: int = 30) -> Optional[Dict[str, Any]]:
        """
        Get task result (blocking with timeout).
        
        Args:
            task_id: Task ID
            timeout: Max wait time in seconds
        
        Returns:
            Result data or None if timeout
        """
        await self.connect()
        
        start_time = time.time()
        result_key = f"{self.TASK_RESULT_PREFIX}{task_id}"
        
        while time.time() - start_time < timeout:
            # Check if result exists
            result_json = await self.redis_client.get(result_key)
            
            if result_json:
                result_data = json.loads(result_json)
                logger.info(f"📨 Retrieved result for task: {task_id}")
                return result_data
            
            # Wait a bit before checking again
            await asyncio.sleep(0.5)
        
        # Timeout
        logger.warning(f"⏱️ Timeout waiting for result: {task_id}")
        await self._set_task_status(task_id, TaskStatus.TIMEOUT)
        return None
    
    async def get_task_status(self, task_id: str) -> Optional[str]:
        """
        Get task status.
        
        Args:
            task_id: Task ID
        
        Returns:
            Task status or None
        """
        await self.connect()
        
        status_key = f"{self.TASK_STATUS_PREFIX}{task_id}"
        status = await self.redis_client.get(status_key)
        return status
    
    async def _set_task_status(self, task_id: str, status: str):
        """Set task status"""
        status_key = f"{self.TASK_STATUS_PREFIX}{task_id}"
        await self.redis_client.setex(status_key, self.TASK_TIMEOUT, status)
    
    async def get_queue_size(self) -> int:
        """Get number of pending tasks in queue"""
        await self.connect()
        return await self.redis_client.zcard(self.TASK_QUEUE_KEY)
    
    async def clear_queue(self):
        """Clear all tasks from queue (for testing)"""
        await self.connect()
        await self.redis_client.delete(self.TASK_QUEUE_KEY)
        logger.info("🗑️ Cleared task queue")


# Import asyncio at the end to avoid circular import
import asyncio
