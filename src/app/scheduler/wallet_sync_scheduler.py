"""
Wallet synchronization scheduler using APScheduler.
"""
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from infrastructure.logging_config import get_logger

logger = get_logger(__name__)


class WalletSyncScheduler:
    """Scheduler for automatic wallet synchronization"""
    
    def __init__(self, sync_service, wallet_service):
        self.sync_service = sync_service
        self.wallet_service = wallet_service
        self.scheduler = AsyncIOScheduler()
        self.enabled = False
    
    async def sync_all_users(self):
        """Sync all users' wallets"""
        logger.info("Starting scheduled wallet sync for all users")
        
        try:
            # Get all users with auto-sync enabled
            users = await self.wallet_service.get_users_with_auto_sync()
            
            if not users:
                logger.info("No users with auto-sync enabled")
                return
            
            logger.info(f"Syncing wallets for {len(users)} users")
            
            for user_id in users:
                try:
                    result = await self.sync_service.sync_all_user_wallets(user_id)
                    logger.info(f"Synced user {user_id}: {result}")
                except Exception as e:
                    logger.error(f"Failed to sync user {user_id}: {e}", exc_info=True)
            
            logger.info("Scheduled wallet sync complete")
            
        except Exception as e:
            logger.error(f"Error in scheduled sync: {e}", exc_info=True)
    
    def start(self, interval_hours: int = 1):
        """Start the scheduler"""
        if self.enabled:
            logger.warning("Scheduler already running")
            return
        
        # Add hourly sync job
        self.scheduler.add_job(
            self.sync_all_users,
            trigger=CronTrigger(hour=f'*/{interval_hours}'),
            id='wallet_sync',
            name='Wallet Synchronization',
            replace_existing=True
        )
        
        self.scheduler.start()
        self.enabled = True
        
        logger.info(f"Wallet sync scheduler started (every {interval_hours} hour(s))")
    
    def stop(self):
        """Stop the scheduler"""
        if not self.enabled:
            logger.warning("Scheduler not running")
            return
        
        self.scheduler.shutdown()
        self.enabled = False
        
        logger.info("Wallet sync scheduler stopped")
    
    def is_running(self) -> bool:
        """Check if scheduler is running"""
        return self.enabled and self.scheduler.running
    
    def get_next_run_time(self) -> datetime:
        """Get next scheduled run time"""
        if not self.enabled:
            return None
        
        job = self.scheduler.get_job('wallet_sync')
        return job.next_run_time if job else None
    
    async def trigger_manual_sync(self, user_id: str = None):
        """Manually trigger sync for specific user or all users"""
        if user_id:
            logger.info(f"Manual sync triggered for user {user_id}")
            return await self.sync_service.sync_all_user_wallets(user_id)
        else:
            logger.info("Manual sync triggered for all users")
            await self.sync_all_users()
