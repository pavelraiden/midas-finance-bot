"""
Minimal working bot - restored from chat history
"""
import asyncio
import logging
import os
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import handlers
from app.bot.handlers import start, transaction, categories, labels, analytics, ai_finance, wallet_management

async def main():
    """Start bot"""
    token = os.getenv("BOT_TOKEN")
    if not token:
        logger.error("BOT_TOKEN not found in .env")
        return
    
    # Initialize bot and dispatcher
    bot = Bot(
        token=token,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
    )
    
    dp = Dispatcher(storage=MemoryStorage())
    
    # Initialize services
    from app.services.user_service import UserService
    from app.services.wallet_service import WalletService
    from app.services.transaction_service import TransactionService
    from infrastructure.repositories.category_repository import CategoryRepository
    from infrastructure.repositories.transaction_repository import TransactionRepository
    
    user_service = UserService()
    wallet_service = WalletService()
    transaction_service = TransactionService()
    category_repo = CategoryRepository()
    transaction_repo = TransactionRepository()
    
    # Inject services into dispatcher
    dp["user_service"] = user_service
    dp["wallet_service"] = wallet_service
    dp["transaction_service"] = transaction_service
    dp["category_repo"] = category_repo
    dp["transaction_repo"] = transaction_repo
    
    # Register routers
    dp.include_router(start.router)
    dp.include_router(transaction.router)
    dp.include_router(categories.router)
    dp.include_router(labels.router)
    dp.include_router(analytics.router)
    dp.include_router(ai_finance.router)
    dp.include_router(wallet_management.router)
    
    logger.info("✅ Bot starting...")
    
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
