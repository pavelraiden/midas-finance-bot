"""
AI Worker Process
Processes AI tasks from Redis queue asynchronously
Based on AI Council recommendations (Claude 3.7)
"""
import asyncio
import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any, Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from infrastructure.logging_config import setup_logging, get_logger
from app.services.ai_task_queue import AITaskQueue, TaskStatus
from app.services.deepseek_service import DeepSeekService

# Setup logging
setup_logging()
logger = get_logger(__name__)


class DeepSeekWorker:
    """
    Worker process for handling AI tasks from Redis queue.
    
    Features:
    - Async task processing
    - Error handling and retry
    - Task result caching
    - Graceful shutdown
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize DeepSeek Worker.
        
        Args:
            redis_url: Redis connection URL (defaults to env var or localhost)
        """
        if redis_url is None:
            redis_host = os.getenv("REDIS_HOST", "localhost")
            redis_port = os.getenv("REDIS_PORT", "6379")
            redis_url = f"redis://{redis_host}:{redis_port}"
        
        self.task_queue = AITaskQueue(redis_url)
        self.deepseek_service = DeepSeekService()
        self.running = False
        
        logger.info(f"🤖 DeepSeekWorker initialized (Redis: {redis_url})")
    
    async def process_task(self, task_data: Dict[str, Any]) -> Optional[Any]:
        """
        Process a single AI task.
        
        Args:
            task_data: Task data from queue
        
        Returns:
            Task result or None on error
        """
        task_id = task_data.get("task_id")
        task_type = task_data.get("task_type")
        data = task_data.get("data", {})
        
        logger.info(f"🔄 Processing task: {task_id} (type={task_type})")
        
        try:
            # Route to appropriate handler based on task type
            if task_type == "categorize_transaction":
                result = await self._categorize_transaction(data)
            elif task_type == "analyze_spending":
                result = await self._analyze_spending(data)
            elif task_type == "budget_recommendation":
                result = await self._budget_recommendation(data)
            elif task_type == "find_anomalies":
                result = await self._find_anomalies(data)
            else:
                logger.error(f"Unknown task type: {task_type}")
                return None
            
            logger.info(f"✅ Task completed: {task_id}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Task failed: {task_id} - {e}")
            return None
    
    async def _categorize_transaction(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Categorize a transaction using DeepSeek AI.
        
        Args:
            data: Transaction data
        
        Returns:
            Category and confidence
        """
        # Extract transaction details
        amount = data.get("amount")
        description = data.get("description", "")
        merchant = data.get("merchant", "")
        
        # Build prompt
        prompt = f"""
Categorize this transaction:
Amount: {amount}
Description: {description}
Merchant: {merchant}

Return JSON with:
- category: One of [Food, Transport, Shopping, Entertainment, Bills, Health, Other]
- confidence: Float between 0 and 1
- reasoning: Brief explanation
"""
        
        # Call DeepSeek (sync, will be run in executor)
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            self.deepseek_service._make_request,
            [{"role": "user", "content": prompt}]
        )
        
        if not response:
            return {
                "category": "Other",
                "confidence": 0.0,
                "reasoning": "AI service unavailable"
            }
        
        # Parse response (simplified - in production use proper JSON parsing)
        try:
            import json
            result = json.loads(response)
            return result
        except:
            # Fallback if response is not JSON
            return {
                "category": "Other",
                "confidence": 0.5,
                "reasoning": response[:200]
            }
    
    async def _analyze_spending(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze spending patterns.
        
        Args:
            data: User spending data
        
        Returns:
            Analysis results
        """
        user_id = data.get("user_id")
        transactions = data.get("transactions", [])
        
        prompt = f"""
Analyze spending for user {user_id}:
Total transactions: {len(transactions)}

Provide insights on:
1. Top spending categories
2. Unusual patterns
3. Savings opportunities

Return structured analysis.
"""
        
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            self.deepseek_service._make_request,
            [{"role": "user", "content": prompt}]
        )
        
        return {
            "analysis": response or "Analysis unavailable",
            "timestamp": asyncio.get_event_loop().time()
        }
    
    async def _budget_recommendation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate budget recommendations.
        
        Args:
            data: User financial data
        
        Returns:
            Budget recommendations
        """
        # Placeholder - implement full logic later
        return {
            "recommendations": "Budget recommendations coming soon",
            "categories": {}
        }
    
    async def _find_anomalies(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Find anomalies in transactions.
        
        Args:
            data: Transaction data
        
        Returns:
            Detected anomalies
        """
        # Placeholder - implement full logic later
        return {
            "anomalies": [],
            "count": 0
        }
    
    async def process_tasks(self):
        """
        Main worker loop - continuously process tasks from queue.
        """
        self.running = True
        logger.info("🚀 Worker started - waiting for tasks...")
        
        try:
            while self.running:
                # Dequeue task
                task_data = await self.task_queue.dequeue_task()
                
                if task_data is None:
                    # No tasks available, wait a bit
                    await asyncio.sleep(1)
                    continue
                
                task_id = task_data.get("task_id")
                
                try:
                    # Process task
                    result = await self.process_task(task_data)
                    
                    # Store result
                    if result is not None:
                        await self.task_queue.store_result(
                            task_id,
                            result,
                            TaskStatus.COMPLETED
                        )
                    else:
                        await self.task_queue.store_result(
                            task_id,
                            {"error": "Task processing failed"},
                            TaskStatus.FAILED
                        )
                
                except Exception as e:
                    logger.error(f"Error processing task {task_id}: {e}")
                    await self.task_queue.store_result(
                        task_id,
                        {"error": str(e)},
                        TaskStatus.FAILED
                    )
        
        except KeyboardInterrupt:
            logger.info("⚠️ Worker interrupted by user")
        except Exception as e:
            logger.error(f"❌ Worker error: {e}")
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("🛑 Shutting down worker...")
        self.running = False
        await self.task_queue.disconnect()
        logger.info("✅ Worker shutdown complete")


async def main():
    """Main entry point for worker process"""
    logger.info("=" * 80)
    logger.info("🤖 Midas Finance Bot - AI Worker Process")
    logger.info("=" * 80)
    
    # Create worker
    worker = DeepSeekWorker()
    
    # Start processing
    await worker.process_tasks()


if __name__ == "__main__":
    asyncio.run(main())
