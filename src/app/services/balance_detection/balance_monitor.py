"""
Balance Monitoring Service.

Автоматически отслеживает балансы кошельков и детектирует транзакции
по изменению баланса (balance-based detection).

Твоя гениальная идея:
"бот проверил было 612 баланса ЮСДС, через час уже 505, 
значит за час было потрачено 107 ЮСДС"
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal

from ....domain.balance.balance_snapshot import BalanceSnapshot, BalanceDelta
from ....infrastructure.repositories.balance_snapshot_repository import BalanceSnapshotRepository
from ....infrastructure.repositories.wallet_repository import WalletRepository
from ....infrastructure.error_handling import with_retry, AGGRESSIVE_RETRY_CONFIG

logger = logging.getLogger(__name__)


class BalanceMonitor:
    """
    Service для мониторинга балансов и детекции транзакций.
    
    Основные функции:
    - Hourly balance snapshots
    - Delta calculation
    - Transaction detection
    - Pattern matching
    """
    
    def __init__(
        self,
        balance_repo: BalanceSnapshotRepository,
        wallet_repo: WalletRepository,
        blockchain_service: Any  # BlockchainService
    ):
        """
        Инициализация balance monitor.
        
        Args:
            balance_repo: BalanceSnapshotRepository
            wallet_repo: WalletRepository
            blockchain_service: Service для получения балансов из blockchain
        """
        self.balance_repo = balance_repo
        self.wallet_repo = wallet_repo
        self.blockchain_service = blockchain_service
        
        # Configuration
        self.min_change_threshold = Decimal("0.01")  # Минимальное изменение для детекции
        self.snapshot_interval = 3600  # 1 hour in seconds
        
        logger.info("BalanceMonitor initialized")
    
    @with_retry(config=AGGRESSIVE_RETRY_CONFIG)
    async def capture_snapshot(
        self,
        wallet_id: str,
        currency: str
    ) -> Optional[BalanceSnapshot]:
        """
        Создает snapshot текущего баланса кошелька.
        
        Args:
            wallet_id: ID кошелька
            currency: Валюта
        
        Returns:
            BalanceSnapshot или None
        """
        try:
            # Get current balance from blockchain
            balance = await self.blockchain_service.get_balance(wallet_id, currency)
            
            if balance is None:
                logger.warning(f"Failed to get balance for wallet {wallet_id}, currency {currency}")
                return None
            
            # Create snapshot
            snapshot = BalanceSnapshot(
                id=None,
                wallet_id=wallet_id,
                currency=currency,
                balance=Decimal(str(balance)),
                timestamp=datetime.utcnow(),
                source="blockchain"
            )
            
            # Save to database
            snapshot_id = await self.balance_repo.create(snapshot)
            snapshot.id = snapshot_id
            
            logger.info(
                f"Captured balance snapshot: wallet={wallet_id}, "
                f"currency={currency}, balance={balance}"
            )
            
            return snapshot
            
        except Exception as e:
            logger.error(f"Failed to capture snapshot: {e}")
            return None
    
    async def capture_all_snapshots(self) -> Dict[str, int]:
        """
        Создает snapshots для всех активных кошельков.
        
        Returns:
            Dict со статистикой: {"success": N, "failed": M}
        """
        stats = {"success": 0, "failed": 0}
        
        try:
            # Get all active wallets
            wallets = await self.wallet_repo.get_all_active()
            
            logger.info(f"Capturing snapshots for {len(wallets)} wallets")
            
            # Capture snapshots for each wallet
            tasks = []
            for wallet in wallets:
                # Get currencies for wallet
                currencies = await self._get_wallet_currencies(wallet["id"])
                
                for currency in currencies:
                    task = self.capture_snapshot(wallet["id"], currency)
                    tasks.append(task)
            
            # Execute all tasks concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Count successes and failures
            for result in results:
                if isinstance(result, Exception):
                    stats["failed"] += 1
                elif result is not None:
                    stats["success"] += 1
                else:
                    stats["failed"] += 1
            
            logger.info(
                f"Snapshot capture completed: "
                f"{stats['success']} success, {stats['failed']} failed"
            )
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to capture all snapshots: {e}")
            return stats
    
    async def detect_changes(
        self,
        wallet_id: str,
        currency: str,
        hours: int = 1
    ) -> List[BalanceDelta]:
        """
        Детектирует изменения баланса за последние N часов.
        
        Args:
            wallet_id: ID кошелька
            currency: Валюта
            hours: Количество часов назад
        
        Returns:
            List of BalanceDelta
        """
        try:
            # Get snapshots for timerange
            to_time = datetime.utcnow()
            from_time = to_time - timedelta(hours=hours)
            
            snapshots = await self.balance_repo.get_by_timerange(
                wallet_id, currency, from_time, to_time
            )
            
            if len(snapshots) < 2:
                logger.debug(f"Not enough snapshots for change detection: {len(snapshots)}")
                return []
            
            # Calculate deltas between consecutive snapshots
            deltas = []
            for i in range(len(snapshots) - 1):
                from_snapshot = snapshots[i]
                to_snapshot = snapshots[i + 1]
                
                delta = BalanceDelta(
                    wallet_id=wallet_id,
                    currency=currency,
                    from_snapshot=from_snapshot,
                    to_snapshot=to_snapshot,
                    amount=Decimal(0),  # Calculated in __post_init__
                    time_diff=0.0,  # Calculated in __post_init__
                    confidence=0.0  # Calculated in __post_init__
                )
                
                # Only include significant changes
                if abs(delta.amount) >= self.min_change_threshold:
                    deltas.append(delta)
            
            logger.info(
                f"Detected {len(deltas)} balance changes for wallet {wallet_id}, "
                f"currency {currency}"
            )
            
            return deltas
            
        except Exception as e:
            logger.error(f"Failed to detect changes: {e}")
            return []
    
    async def detect_all_changes(self, hours: int = 1) -> List[BalanceDelta]:
        """
        Детектирует изменения балансов для всех кошельков.
        
        Args:
            hours: Количество часов назад
        
        Returns:
            List of all BalanceDelta
        """
        all_deltas = []
        
        try:
            # Get all active wallets
            wallets = await self.wallet_repo.get_all_active()
            
            logger.info(f"Detecting changes for {len(wallets)} wallets")
            
            # Detect changes for each wallet
            for wallet in wallets:
                currencies = await self._get_wallet_currencies(wallet["id"])
                
                for currency in currencies:
                    deltas = await self.detect_changes(wallet["id"], currency, hours)
                    all_deltas.extend(deltas)
            
            logger.info(f"Total balance changes detected: {len(all_deltas)}")
            
            return all_deltas
            
        except Exception as e:
            logger.error(f"Failed to detect all changes: {e}")
            return all_deltas
    
    async def get_balance_history(
        self,
        wallet_id: str,
        currency: str,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Получает balance history для кошелька.
        
        Args:
            wallet_id: ID кошелька
            currency: Валюта
            days: Количество дней истории
        
        Returns:
            List of balance history entries
        """
        try:
            history = await self.balance_repo.get_history(
                wallet_id, currency, limit=days * 24  # hourly snapshots
            )
            
            return history
            
        except Exception as e:
            logger.error(f"Failed to get balance history: {e}")
            return []
    
    async def _get_wallet_currencies(self, wallet_id: str) -> List[str]:
        """
        Получает список валют для кошелька.
        
        Args:
            wallet_id: ID кошелька
        
        Returns:
            List of currency codes
        """
        try:
            # Get wallet info
            wallet = await self.wallet_repo.get_by_id(wallet_id)
            
            if not wallet:
                return []
            
            # For now, return wallet's default currency
            # TODO: Get all currencies from transactions or wallet config
            return [wallet.get("currency", "USD")]
            
        except Exception as e:
            logger.error(f"Failed to get wallet currencies: {e}")
            return []
    
    async def start_monitoring(self):
        """
        Запускает continuous monitoring (hourly snapshots).
        
        Должен вызываться через scheduler (APScheduler, Celery, etc.)
        """
        logger.info("Starting balance monitoring...")
        
        while True:
            try:
                # Capture snapshots
                stats = await self.capture_all_snapshots()
                
                # Detect changes
                deltas = await self.detect_all_changes(hours=1)
                
                logger.info(
                    f"Monitoring cycle completed: "
                    f"{stats['success']} snapshots, {len(deltas)} changes detected"
                )
                
                # Wait for next cycle (1 hour)
                await asyncio.sleep(self.snapshot_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring cycle: {e}")
                # Wait a bit before retry
                await asyncio.sleep(60)


# Example usage:
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

async def monitor_balances():
    monitor = BalanceMonitor(balance_repo, wallet_repo, blockchain_service)
    await monitor.capture_all_snapshots()
    await monitor.detect_all_changes(hours=1)

# Schedule hourly
scheduler.add_job(monitor_balances, 'interval', hours=1)
scheduler.start()
"""
