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
from app.services.prompt_library import PromptLibrary
from app.services.context_manager import ContextManager
from infrastructure.repositories.user_repository import UserRepository
from infrastructure.repositories.transaction_repository import TransactionRepository
from infrastructure.repositories.category_repository import CategoryRepository
from infrastructure.repositories.merchant_repository import MerchantRepository
from infrastructure.database import Database

# Setup logging
setup_logging()
logger = get_logger(__name__)


class DeepSeekWorker:
    """
    Worker process for handling AI tasks from Redis queue.
    
    Features:
    - Async task processing
    - Confidence-based auto-confirmation
    - Error handling and retry
    - Task result caching
    - Graceful shutdown
    """
    
    # Confidence thresholds (from AI Council recommendations)
    HIGH_CONFIDENCE_THRESHOLD = 0.95  # Auto-confirm if >= 95%
    MEDIUM_CONFIDENCE_THRESHOLD = 0.70  # Request confirmation if >= 70%
    LOW_CONFIDENCE_THRESHOLD = 0.50  # Suggest manual review if < 50%
    
    def __init__(self, redis_url: Optional[str] = None, db_path: Optional[str] = None):
        """
        Initialize DeepSeek Worker.
        
        Args:
            redis_url: Redis connection URL (defaults to env var or localhost)
            db_path: Database path (defaults to env var or ./data/midas.db)
        """
        if redis_url is None:
            redis_host = os.getenv("REDIS_HOST", "localhost")
            redis_port = os.getenv("REDIS_PORT", "6379")
            redis_url = f"redis://{redis_host}:{redis_port}"
        
        if db_path is None:
            db_path = os.getenv("DB_PATH", "./data/midas.db")
        
        # Initialize services
        self.task_queue = AITaskQueue(redis_url)
        self.deepseek_service = DeepSeekService()
        self.prompt_library = PromptLibrary()
        
        # Initialize database and repositories
        self.database = Database(db_path)
        self.user_repo = UserRepository(db_path)
        self.transaction_repo = TransactionRepository(db_path)
        self.category_repo = CategoryRepository(db_path)
        self.merchant_repo = MerchantRepository(db_path)
        
        # Initialize context manager
        self.context_manager = ContextManager(
            user_repo=self.user_repo,
            transaction_repo=self.transaction_repo,
            category_repo=self.category_repo,
            merchant_repo=self.merchant_repo
        )
        
        self.running = False
        
        logger.info(f"🤖 DeepSeekWorker initialized (Redis: {redis_url}, DB: {db_path})")
    
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
        Categorize a transaction using DeepSeek AI with context.
        
        Args:
            data: Transaction data (must include user_id)
        
        Returns:
            Category and confidence
        """
        user_id = data.get("user_id")
        if not user_id:
            logger.error("Missing user_id in transaction data")
            return {
                "category": "Other",
                "confidence": 0.0,
                "reasoning": "Missing user_id"
            }
        
        # 1. Get context from ContextManager
        context = await self.context_manager.get_categorization_context(
            user_id=user_id,
            transaction_data=data
        )
        
        # 2. Get prompt from PromptLibrary
        prompt_messages = self.prompt_library.get_categorization_prompt(context)
        
        # 3. Call DeepSeek (sync, will be run in executor)
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            self.deepseek_service._make_request,
            prompt_messages
        )
        
        if not response:
            return {
                "category": "Other",
                "confidence": 0.0,
                "reasoning": "AI service unavailable"
            }
        
        # 4. Parse response
        try:
            import json
            result = json.loads(response)
            
            # 5. Determine confidence level and action
            confidence = result.get("confidence", 0.0)
            
            if confidence >= self.HIGH_CONFIDENCE_THRESHOLD:
                # High confidence - auto-confirm
                result["auto_confirmed"] = True
                result["requires_confirmation"] = False
                logger.info(f"✅ High confidence ({confidence:.2%}) - auto-confirmed: {result.get('category')}")
                
                # Handle merchant mapping if suggested
                if "new_merchant_mapping" in result and result["new_merchant_mapping"]:
                    mapping = result["new_merchant_mapping"]
                    try:
                        await self.merchant_repo.create({
                            "user_id": user_id,
                            "merchant_name": mapping.get("merchant_name"),
                            "category": mapping.get("suggested_category")
                        })
                        logger.info(f"✅ Saved new merchant mapping: {mapping.get('merchant_name')} → {mapping.get('suggested_category')}")
                    except Exception as e:
                        logger.error(f"Failed to save merchant mapping: {e}")
            
            elif confidence >= self.MEDIUM_CONFIDENCE_THRESHOLD:
                # Medium confidence - request confirmation
                result["auto_confirmed"] = False
                result["requires_confirmation"] = True
                logger.info(f"⚠️ Medium confidence ({confidence:.2%}) - requesting user confirmation")
            
            else:
                # Low confidence - suggest manual review
                result["auto_confirmed"] = False
                result["requires_confirmation"] = True
                result["suggest_manual_review"] = True
                logger.warning(f"❌ Low confidence ({confidence:.2%}) - suggesting manual review")
            
            return result
        except json.JSONDecodeError:
            # Fallback if response is not JSON
            logger.warning(f"Non-JSON response from AI: {response[:100]}")
            return {
                "category": "Other",
                "confidence": 0.5,
                "reasoning": response[:200]
            }
    
    async def _analyze_spending(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze spending patterns with context.
        
        Args:
            data: User spending data (must include user_id)
        
        Returns:
            Analysis results
        """
        user_id = data.get("user_id")
        if not user_id:
            return {"error": "Missing user_id"}
        
        # 1. Get context from ContextManager
        days = data.get("days", 30)
        context = await self.context_manager.get_analyze_spending_context(
            user_id=user_id,
            days=days
        )
        
        # 2. Get prompt from PromptLibrary
        prompt_messages = self.prompt_library.get_analyze_spending_prompt(context)
        
        # 3. Call DeepSeek
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            self.deepseek_service._make_request,
            prompt_messages
        )
        
        return {
            "analysis": response or "Analysis unavailable",
            "timestamp": asyncio.get_event_loop().time()
        }
    
    async def _budget_recommendation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate budget recommendations with context.
        
        Args:
            data: User financial data (must include user_id)
        
        Returns:
            Budget recommendations
        """
        user_id = data.get("user_id")
        if not user_id:
            return {"error": "Missing user_id"}
        
        # 1. Get context from ContextManager
        months = data.get("months", 3)
        context = await self.context_manager.get_budget_recommendation_context(
            user_id=user_id,
            months=months
        )
        
        # 2. Get prompt from PromptLibrary
        prompt_messages = self.prompt_library.get_budget_recommendation_prompt(context)
        
        # 3. Call DeepSeek
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            self.deepseek_service._make_request,
            prompt_messages
        )
        
        # 4. Parse response
        try:
            import json
            result = json.loads(response)
            return result
        except json.JSONDecodeError:
            return {
                "recommendations": response or "Recommendations unavailable",
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
