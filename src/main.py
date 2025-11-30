"""
Main bot entry point.
"""
import asyncio
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from infrastructure.logging_config import setup_logging, get_logger

# Repositories
from infrastructure.repositories.user_repository import UserRepository
from infrastructure.repositories.wallet_repository import WalletRepository
from infrastructure.repositories.category_repository import CategoryRepository
from infrastructure.repositories.transaction_repository import TransactionRepository
from infrastructure.repositories.merchant_repository import MerchantRepository
from infrastructure.repositories.balance_snapshot_repository import BalanceSnapshotRepository
from infrastructure.repositories.audit_repository import AuditRepository
from infrastructure.database import Database
from infrastructure.unit_of_work import UnitOfWorkFactory
from infrastructure.security import get_encryption_service, get_audit_logger

# Services
from app.services.user_service import UserService
from app.services.wallet_service import WalletService
from app.services.transaction_service import TransactionService
from app.services.blockchain_service import BlockchainService
from app.services.deepseek_service import DeepSeekService
from app.services.sync_service import SyncService
from app.services.balance_detection.balance_monitor import BalanceMonitor
from app.services.balance_detection.pattern_detector import PatternDetector
from app.scheduler.wallet_sync_scheduler import WalletSyncScheduler

# Handlers
from app.bot.handlers import start, transaction, wallet_management, categories, labels, analytics, ai_finance, sync_command, pending_transactions

# Setup logging
setup_logging()
logger = get_logger(__name__)

# Load environment variables
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found in environment")


async def setup_bot_commands(bot: Bot):
    """Setup bot commands menu."""
    commands = [
        BotCommand(command="start", description="Start the bot"),
        BotCommand(command="help", description="Show help"),
        BotCommand(command="import", description="Import CSV file"),
        BotCommand(command="pending", description="Show pending transactions"),
        BotCommand(command="sync", description="Sync wallets now"),
    ]
    await bot.set_my_commands(commands)


async def main():
    """Main bot function."""
    logger.info("Starting Midas Financial Bot...")
    
    # Check for single instance
    from infrastructure.pid_manager import ensure_single_instance
    if not ensure_single_instance():
        logger.error("Another bot instance is already running. Exiting.")
        sys.exit(1)
    
    # Validate encryption key
    from infrastructure.security.encryption_key_validator import ensure_encryption_key_configured
    ensure_encryption_key_configured()
    
    # Initialize infrastructure
    logger.info("Initializing infrastructure...")
    
    # SQLite database
    logger.info("Using SQLite database")
    
    # Initialize database
    logger.info("Initializing database...")
    from pathlib import Path
    PROJECT_ROOT = Path(__file__).parent.parent
    DATA_DIR = PROJECT_ROOT / "data"
    DATA_DIR.mkdir(exist_ok=True)
    db_path = str(DATA_DIR / "bot.db")
    db = Database(db_path)
    
    # Run database migrations
    logger.info("Running database migrations...")
    from infrastructure.database_migrations import run_database_migrations
    if not run_database_migrations(db_path):
        logger.error("Database migrations failed. Exiting.")
        sys.exit(1)
    
    # Initialize repositories
    logger.info("Initializing repositories...")
    user_repo = UserRepository(db_path)
    wallet_repo = WalletRepository(db_path)
    category_repo = CategoryRepository(db_path)
    transaction_repo = TransactionRepository(db_path)
    merchant_repo = MerchantRepository(db)
    balance_snapshot_repo = BalanceSnapshotRepository(db_path)
    audit_repo = AuditRepository(db_path)
    
    # Initialize security services
    logger.info("Initializing security services...")
    encryption_service = get_encryption_service()
    audit_logger = get_audit_logger()
    
    # Initialize UnitOfWork factory
    uow_factory = UnitOfWorkFactory(db_path)
    
    # Initialize services
    logger.info("Initializing services...")
    user_service = UserService(user_repo)
    wallet_service = WalletService(wallet_repo)
    transaction_service = TransactionService(transaction_repo, wallet_service)
    blockchain_service = BlockchainService()
    deepseek_service = DeepSeekService()
    sync_service = SyncService(
        blockchain_service=blockchain_service,
        deepseek_service=deepseek_service,
        merchant_repo=merchant_repo,
        transaction_service=transaction_service,
        wallet_service=wallet_service
    )
    
    # Initialize Balance Detection services
    logger.info("Initializing Balance Detection services...")
    pattern_detector = PatternDetector(transaction_repo=transaction_repo)
    balance_monitor = BalanceMonitor(
        balance_repo=balance_snapshot_repo,
        wallet_repo=wallet_repo,
        blockchain_service=blockchain_service
    )
    
    # Initialize scheduler
    logger.info("Initializing scheduler...")
    scheduler = WalletSyncScheduler(sync_service, wallet_service)
    
    # Initialize bot and dispatcher
    logger.info("Initializing bot...")
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Drop pending updates to avoid conflicts with other instances
    logger.info("Dropping pending updates to avoid conflicts...")
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Pending updates dropped")
    
    # Register routers
    dp.include_router(start.router)
    dp.include_router(transaction.router)
    dp.include_router(wallet_management.router)
    dp.include_router(categories.router)
    dp.include_router(labels.router)
    dp.include_router(analytics.router)
    dp.include_router(ai_finance.router)
    dp.include_router(sync_command.router)
    dp.include_router(pending_transactions.router)
    logger.info("All handlers registered")
    
    # Dependency injection middleware
    @dp.update.outer_middleware()
    async def inject_dependencies(handler, event, data):
        """Inject dependencies into handlers."""
        data["user_service"] = user_service
        data["wallet_service"] = wallet_service
        data["transaction_service"] = transaction_service
        data["category_repo"] = category_repo
        data["transaction_repo"] = transaction_repo
        data["merchant_repo"] = merchant_repo
        data["blockchain_service"] = blockchain_service
        data["deepseek_service"] = deepseek_service
        data["sync_service"] = sync_service
        data["scheduler"] = scheduler
        data["balance_monitor"] = balance_monitor
        data["encryption_service"] = encryption_service
        data["audit_logger"] = audit_logger
        data["uow_factory"] = uow_factory
        return await handler(event, data)
    
    # Setup bot commands
    await setup_bot_commands(bot)
    
    # Start scheduler (disabled by default, can be enabled via /sync command)
    # scheduler.start(interval_hours=1)
    logger.info("Scheduler initialized (not started)")
    
    # Start polling
    logger.info("Bot started successfully! Polling...")
    try:
        # Use drop_pending_updates=True to handle conflicts automatically
        await dp.start_polling(
            bot, 
            allowed_updates=dp.resolve_used_update_types(),
            drop_pending_updates=True
        )
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot error: {e}", exc_info=True)
    finally:
        logger.info("Shutting down...")
        await bot.session.close()
        logger.info("Bot stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped")
