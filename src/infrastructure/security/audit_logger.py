"""
Comprehensive Audit Logging для отслеживания всех критических операций.

Логирует:
- Создание/изменение/удаление транзакций
- Создание/изменение/удаление кошельков
- Изменение категорий
- AI-категоризация
- CSV импорт
- Все критические операции
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum
import json

logger = logging.getLogger(__name__)


class AuditAction(Enum):
    """Типы audit actions."""
    
    # Transaction actions
    TRANSACTION_CREATE = "transaction.create"
    TRANSACTION_UPDATE = "transaction.update"
    TRANSACTION_DELETE = "transaction.delete"
    TRANSACTION_CATEGORIZE = "transaction.categorize"
    
    # Wallet actions
    WALLET_CREATE = "wallet.create"
    WALLET_UPDATE = "wallet.update"
    WALLET_DELETE = "wallet.delete"
    WALLET_SYNC = "wallet.sync"
    
    # Category actions
    CATEGORY_CREATE = "category.create"
    CATEGORY_UPDATE = "category.update"
    CATEGORY_DELETE = "category.delete"
    
    # Label actions
    LABEL_CREATE = "label.create"
    LABEL_UPDATE = "label.update"
    LABEL_DELETE = "label.delete"
    
    # Import actions
    CSV_IMPORT = "csv.import"
    TRUSTEE_IMPORT = "trustee.import"
    
    # AI actions
    AI_CATEGORIZE = "ai.categorize"
    AI_ANALYZE = "ai.analyze"
    
    # Security actions
    AUTH_LOGIN = "auth.login"
    AUTH_LOGOUT = "auth.logout"
    AUTH_FAILED = "auth.failed"
    
    # System actions
    SYSTEM_ERROR = "system.error"
    SYSTEM_WARNING = "system.warning"


class AuditLogger:
    """
    Service для audit logging.
    
    Логирует все критические операции в БД и файл.
    """
    
    def __init__(self, repository=None):
        """
        Инициализация audit logger.
        
        Args:
            repository: AuditRepository для сохранения в БД
        """
        self.repository = repository
        logger.info("AuditLogger initialized")
    
    def log(
        self,
        action: AuditAction,
        user_id: int,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> None:
        """
        Логирует audit event.
        
        Args:
            action: Тип действия
            user_id: ID пользователя
            details: Дополнительные детали (JSON-serializable)
            ip_address: IP адрес пользователя
            user_agent: User agent
            success: Успешность операции
            error_message: Сообщение об ошибке (если есть)
        """
        timestamp = datetime.utcnow()
        
        audit_entry = {
            "timestamp": timestamp.isoformat(),
            "action": action.value,
            "user_id": user_id,
            "details": details or {},
            "ip_address": ip_address,
            "user_agent": user_agent,
            "success": success,
            "error_message": error_message
        }
        
        # Логируем в файл
        log_level = logging.INFO if success else logging.ERROR
        logger.log(
            log_level,
            f"AUDIT: {action.value} by user {user_id} - "
            f"{'SUCCESS' if success else 'FAILED'} - {json.dumps(details or {})}"
        )
        
        # Сохраняем в БД (если repository доступен)
        if self.repository:
            try:
                self.repository.create(audit_entry)
            except Exception as e:
                logger.error(f"Failed to save audit log to database: {e}")
    
    # Convenience methods для частых операций
    
    def log_transaction_create(
        self,
        user_id: int,
        transaction_id: int,
        amount: float,
        currency: str,
        category_id: Optional[int] = None
    ) -> None:
        """Логирует создание транзакции."""
        self.log(
            action=AuditAction.TRANSACTION_CREATE,
            user_id=user_id,
            details={
                "transaction_id": transaction_id,
                "amount": amount,
                "currency": currency,
                "category_id": category_id
            }
        )
    
    def log_transaction_update(
        self,
        user_id: int,
        transaction_id: int,
        changes: Dict[str, Any]
    ) -> None:
        """Логирует изменение транзакции."""
        self.log(
            action=AuditAction.TRANSACTION_UPDATE,
            user_id=user_id,
            details={
                "transaction_id": transaction_id,
                "changes": changes
            }
        )
    
    def log_transaction_delete(
        self,
        user_id: int,
        transaction_id: int
    ) -> None:
        """Логирует удаление транзакции."""
        self.log(
            action=AuditAction.TRANSACTION_DELETE,
            user_id=user_id,
            details={"transaction_id": transaction_id}
        )
    
    def log_wallet_create(
        self,
        user_id: int,
        wallet_id: int,
        wallet_type: str,
        name: str
    ) -> None:
        """Логирует создание кошелька."""
        self.log(
            action=AuditAction.WALLET_CREATE,
            user_id=user_id,
            details={
                "wallet_id": wallet_id,
                "wallet_type": wallet_type,
                "name": name
            }
        )
    
    def log_wallet_delete(
        self,
        user_id: int,
        wallet_id: int
    ) -> None:
        """Логирует удаление кошелька."""
        self.log(
            action=AuditAction.WALLET_DELETE,
            user_id=user_id,
            details={"wallet_id": wallet_id}
        )
    
    def log_csv_import(
        self,
        user_id: int,
        filename: str,
        transactions_count: int,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> None:
        """Логирует CSV импорт."""
        self.log(
            action=AuditAction.CSV_IMPORT,
            user_id=user_id,
            details={
                "filename": filename,
                "transactions_count": transactions_count
            },
            success=success,
            error_message=error_message
        )
    
    def log_ai_categorize(
        self,
        user_id: int,
        transaction_id: int,
        category_id: int,
        confidence: float,
        model: str = "deepseek"
    ) -> None:
        """Логирует AI-категоризацию."""
        self.log(
            action=AuditAction.AI_CATEGORIZE,
            user_id=user_id,
            details={
                "transaction_id": transaction_id,
                "category_id": category_id,
                "confidence": confidence,
                "model": model
            }
        )
    
    def log_error(
        self,
        user_id: int,
        error_type: str,
        error_message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Логирует системную ошибку."""
        self.log(
            action=AuditAction.SYSTEM_ERROR,
            user_id=user_id,
            details={
                "error_type": error_type,
                **(details or {})
            },
            success=False,
            error_message=error_message
        )


# Singleton instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """
    Получает singleton instance AuditLogger.
    
    Returns:
        AuditLogger instance
    """
    global _audit_logger
    
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    
    return _audit_logger


def init_audit_logger(repository) -> AuditLogger:
    """
    Инициализирует AuditLogger с repository.
    
    Args:
        repository: AuditRepository instance
        
    Returns:
        AuditLogger instance
    """
    global _audit_logger
    _audit_logger = AuditLogger(repository=repository)
    return _audit_logger
