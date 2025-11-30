"""
Audit Repository для работы с audit logs.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from .base import BaseRepository

logger = logging.getLogger(__name__)


class AuditRepository(BaseRepository):
    """
    Repository для audit_log таблицы.
    """
    
    def __init__(self, db):
        """
        Инициализация repository.
        
        Args:
            db: Database connection instance
        """
        super().__init__(db)
        self.table_name = "audit_log"
    
    async def create(self, audit_entry: Dict[str, Any]) -> Optional[str]:
        """
        Создает audit log entry.
        
        Args:
            audit_entry: Dict с данными audit log
                - timestamp: datetime
                - action: str
                - user_id: int
                - details: dict
                - ip_address: str (optional)
                - user_agent: str (optional)
                - success: bool
                - error_message: str (optional)
        
        Returns:
            ID созданного audit log entry или None при ошибке
        """
        try:
            query = """
                INSERT INTO audit_log (
                    timestamp, action, user_id, details,
                    ip_address, user_agent, success, error_message
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id
            """
            
            result = await self.db.fetchrow(
                query,
                audit_entry.get("timestamp", datetime.utcnow()),
                audit_entry["action"],
                audit_entry.get("user_id"),
                audit_entry.get("details", {}),
                audit_entry.get("ip_address"),
                audit_entry.get("user_agent"),
                audit_entry.get("success", True),
                audit_entry.get("error_message")
            )
            
            if result:
                logger.debug(f"Created audit log entry: {result['id']}")
                return result["id"]
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to create audit log entry: {e}")
            return None
    
    async def get_by_user(
        self,
        user_id: int,
        limit: int = 100,
        offset: int = 0,
        action_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Получает audit logs для пользователя.
        
        Args:
            user_id: ID пользователя
            limit: Максимальное количество записей
            offset: Offset для пагинации
            action_filter: Фильтр по типу действия (optional)
        
        Returns:
            List of audit log entries
        """
        try:
            if action_filter:
                query = """
                    SELECT * FROM audit_log
                    WHERE user_id = $1 AND action = $2
                    ORDER BY timestamp DESC
                    LIMIT $3 OFFSET $4
                """
                results = await self.db.fetch(query, user_id, action_filter, limit, offset)
            else:
                query = """
                    SELECT * FROM audit_log
                    WHERE user_id = $1
                    ORDER BY timestamp DESC
                    LIMIT $2 OFFSET $3
                """
                results = await self.db.fetch(query, user_id, limit, offset)
            
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Failed to get audit logs for user {user_id}: {e}")
            return []
    
    async def get_failed_operations(
        self,
        user_id: Optional[int] = None,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Получает failed operations за последние N часов.
        
        Args:
            user_id: ID пользователя (optional, если None - все пользователи)
            hours: Количество часов назад
        
        Returns:
            List of failed audit log entries
        """
        try:
            since = datetime.utcnow() - timedelta(hours=hours)
            
            if user_id:
                query = """
                    SELECT * FROM audit_log
                    WHERE user_id = $1 AND success = FALSE AND timestamp >= $2
                    ORDER BY timestamp DESC
                """
                results = await self.db.fetch(query, user_id, since)
            else:
                query = """
                    SELECT * FROM audit_log
                    WHERE success = FALSE AND timestamp >= $1
                    ORDER BY timestamp DESC
                """
                results = await self.db.fetch(query, since)
            
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Failed to get failed operations: {e}")
            return []
    
    async def get_by_action(
        self,
        action: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Получает audit logs по типу действия.
        
        Args:
            action: Тип действия (e.g., 'transaction.create')
            limit: Максимальное количество записей
            offset: Offset для пагинации
        
        Returns:
            List of audit log entries
        """
        try:
            query = """
                SELECT * FROM audit_log
                WHERE action = $1
                ORDER BY timestamp DESC
                LIMIT $2 OFFSET $3
            """
            results = await self.db.fetch(query, action, limit, offset)
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Failed to get audit logs for action {action}: {e}")
            return []
    
    async def search_by_details(
        self,
        search_key: str,
        search_value: Any,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Поиск audit logs по содержимому details (JSONB).
        
        Args:
            search_key: Ключ в details JSON
            search_value: Значение для поиска
            limit: Максимальное количество записей
        
        Returns:
            List of audit log entries
        """
        try:
            query = """
                SELECT * FROM audit_log
                WHERE details->$1 = to_jsonb($2::text)
                ORDER BY timestamp DESC
                LIMIT $3
            """
            results = await self.db.fetch(query, search_key, str(search_value), limit)
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Failed to search audit logs by details: {e}")
            return []
    
    async def get_statistics(
        self,
        user_id: Optional[int] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Получает статистику audit logs.
        
        Args:
            user_id: ID пользователя (optional)
            days: Количество дней назад
        
        Returns:
            Dict со статистикой
        """
        try:
            since = datetime.utcnow() - timedelta(days=days)
            
            if user_id:
                query = """
                    SELECT 
                        COUNT(*) as total_operations,
                        COUNT(*) FILTER (WHERE success = TRUE) as successful,
                        COUNT(*) FILTER (WHERE success = FALSE) as failed,
                        COUNT(DISTINCT action) as unique_actions,
                        COUNT(DISTINCT DATE(timestamp)) as active_days
                    FROM audit_log
                    WHERE user_id = $1 AND timestamp >= $2
                """
                result = await self.db.fetchrow(query, user_id, since)
            else:
                query = """
                    SELECT 
                        COUNT(*) as total_operations,
                        COUNT(*) FILTER (WHERE success = TRUE) as successful,
                        COUNT(*) FILTER (WHERE success = FALSE) as failed,
                        COUNT(DISTINCT action) as unique_actions,
                        COUNT(DISTINCT user_id) as unique_users,
                        COUNT(DISTINCT DATE(timestamp)) as active_days
                    FROM audit_log
                    WHERE timestamp >= $1
                """
                result = await self.db.fetchrow(query, since)
            
            return dict(result) if result else {}
            
        except Exception as e:
            logger.error(f"Failed to get audit log statistics: {e}")
            return {}
    
    async def cleanup_old_logs(self, days: int = 730) -> int:
        """
        Удаляет старые audit logs (для retention policy).
        
        Args:
            days: Количество дней для хранения (default: 2 года)
        
        Returns:
            Количество удаленных записей
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            query = """
                DELETE FROM audit_log
                WHERE timestamp < $1
            """
            result = await self.db.execute(query, cutoff_date)
            
            # Extract count from result string "DELETE N"
            deleted_count = int(result.split()[-1]) if result else 0
            
            logger.info(f"Cleaned up {deleted_count} old audit log entries")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old audit logs: {e}")
            return 0
