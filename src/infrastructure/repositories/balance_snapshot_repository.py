"""
Balance Snapshot Repository.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal
import logging

from .base import BaseRepository
from src.domain.balance.balance_snapshot import BalanceSnapshot, BalanceDelta

logger = logging.getLogger(__name__)


class BalanceSnapshotRepository(BaseRepository):
    """
    Repository для balance_snapshots таблицы.
    """
    
    def __init__(self, db):
        super().__init__(db)
        self.table_name = "balance_snapshots"
    
    async def create(self, snapshot: BalanceSnapshot) -> Optional[str]:
        """
        Создает balance snapshot.
        
        Args:
            snapshot: BalanceSnapshot instance
        
        Returns:
            ID созданного snapshot
        """
        try:
            query = """
                INSERT INTO balance_snapshots (
                    wallet_id, user_id, currency, balance,
                    timestamp, source, block_number, chain_id
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id
            """
            
            result = await self.db.fetchrow(
                query,
                snapshot.wallet_id,
                None,  # user_id будет получен через JOIN с wallets
                snapshot.currency,
                snapshot.balance,
                snapshot.timestamp,
                snapshot.source,
                snapshot.block_number,
                snapshot.chain_id
            )
            
            if result:
                logger.debug(f"Created balance snapshot: {result['id']}")
                return result["id"]
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to create balance snapshot: {e}")
            return None
    
    async def get_latest(
        self,
        wallet_id: str,
        currency: str
    ) -> Optional[BalanceSnapshot]:
        """
        Получает latest balance snapshot для кошелька.
        
        Args:
            wallet_id: ID кошелька
            currency: Валюта
        
        Returns:
            BalanceSnapshot или None
        """
        try:
            query = """
                SELECT * FROM balance_snapshots
                WHERE wallet_id = $1 AND currency = $2
                ORDER BY timestamp DESC
                LIMIT 1
            """
            
            result = await self.db.fetchrow(query, wallet_id, currency)
            
            if result:
                return self._row_to_snapshot(result)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get latest snapshot: {e}")
            return None
    
    async def get_by_timerange(
        self,
        wallet_id: str,
        currency: str,
        from_time: datetime,
        to_time: datetime
    ) -> List[BalanceSnapshot]:
        """
        Получает snapshots в заданном временном диапазоне.
        
        Args:
            wallet_id: ID кошелька
            currency: Валюта
            from_time: Начало диапазона
            to_time: Конец диапазона
        
        Returns:
            List of BalanceSnapshot
        """
        try:
            query = """
                SELECT * FROM balance_snapshots
                WHERE wallet_id = $1 AND currency = $2
                  AND timestamp BETWEEN $3 AND $4
                ORDER BY timestamp ASC
            """
            
            results = await self.db.fetch(query, wallet_id, currency, from_time, to_time)
            
            return [self._row_to_snapshot(row) for row in results]
            
        except Exception as e:
            logger.error(f"Failed to get snapshots by timerange: {e}")
            return []
    
    async def get_delta(
        self,
        wallet_id: str,
        currency: str,
        from_time: datetime,
        to_time: datetime
    ) -> Optional[BalanceDelta]:
        """
        Вычисляет balance delta между двумя timestamps.
        
        Args:
            wallet_id: ID кошелька
            currency: Валюта
            from_time: Начало периода
            to_time: Конец периода
        
        Returns:
            BalanceDelta или None
        """
        try:
            # Get snapshots closest to from_time and to_time
            from_snapshot = await self._get_closest_snapshot(wallet_id, currency, from_time)
            to_snapshot = await self._get_closest_snapshot(wallet_id, currency, to_time)
            
            if not from_snapshot or not to_snapshot:
                return None
            
            return BalanceDelta(
                wallet_id=wallet_id,
                currency=currency,
                from_snapshot=from_snapshot,
                to_snapshot=to_snapshot,
                amount=Decimal(0),  # Will be calculated in __post_init__
                time_diff=0.0,  # Will be calculated in __post_init__
                confidence=0.0  # Will be calculated in __post_init__
            )
            
        except Exception as e:
            logger.error(f"Failed to calculate balance delta: {e}")
            return None
    
    async def _get_closest_snapshot(
        self,
        wallet_id: str,
        currency: str,
        target_time: datetime
    ) -> Optional[BalanceSnapshot]:
        """
        Получает snapshot, ближайший к target_time.
        
        Args:
            wallet_id: ID кошелька
            currency: Валюта
            target_time: Целевое время
        
        Returns:
            BalanceSnapshot или None
        """
        try:
            query = """
                SELECT * FROM balance_snapshots
                WHERE wallet_id = $1 AND currency = $2
                  AND timestamp <= $3
                ORDER BY timestamp DESC
                LIMIT 1
            """
            
            result = await self.db.fetchrow(query, wallet_id, currency, target_time)
            
            if result:
                return self._row_to_snapshot(result)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get closest snapshot: {e}")
            return None
    
    async def get_history(
        self,
        wallet_id: str,
        currency: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Получает balance history с вычисленными deltas.
        
        Args:
            wallet_id: ID кошелька
            currency: Валюта
            limit: Максимальное количество записей
        
        Returns:
            List of dicts with balance history
        """
        try:
            query = """
                SELECT * FROM v_balance_history
                WHERE wallet_id = $1 AND currency = $2
                ORDER BY timestamp DESC
                LIMIT $3
            """
            
            results = await self.db.fetch(query, wallet_id, currency, limit)
            
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Failed to get balance history: {e}")
            return []
    
    async def detect_significant_changes(
        self,
        wallet_id: str,
        currency: str,
        threshold: Decimal,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Детектирует significant balance changes за последние N часов.
        
        Args:
            wallet_id: ID кошелька
            currency: Валюта
            threshold: Минимальное изменение для детекции
            hours: Количество часов назад
        
        Returns:
            List of significant changes
        """
        try:
            since = datetime.utcnow() - timedelta(hours=hours)
            
            query = """
                SELECT * FROM v_balance_history
                WHERE wallet_id = $1 AND currency = $2
                  AND timestamp >= $3
                  AND ABS(delta) >= $4
                ORDER BY timestamp DESC
            """
            
            results = await self.db.fetch(query, wallet_id, currency, since, threshold)
            
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Failed to detect significant changes: {e}")
            return []
    
    async def cleanup_old_snapshots(self, days: int = 90) -> int:
        """
        Удаляет старые snapshots (для экономии места).
        
        Args:
            days: Количество дней для хранения
        
        Returns:
            Количество удаленных записей
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            query = """
                DELETE FROM balance_snapshots
                WHERE timestamp < $1
            """
            result = await self.db.execute(query, cutoff_date)
            
            deleted_count = int(result.split()[-1]) if result else 0
            
            logger.info(f"Cleaned up {deleted_count} old balance snapshots")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old snapshots: {e}")
            return 0
    
    def _row_to_snapshot(self, row) -> BalanceSnapshot:
        """Converts database row to BalanceSnapshot."""
        return BalanceSnapshot(
            id=row["id"],
            wallet_id=row["wallet_id"],
            currency=row["currency"],
            balance=Decimal(str(row["balance"])),
            timestamp=row["timestamp"],
            source=row["source"],
            block_number=row.get("block_number"),
            chain_id=row.get("chain_id")
        )
