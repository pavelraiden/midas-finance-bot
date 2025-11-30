"""
Unit of Work Pattern Implementation.

Управляет database transactions и координирует работу repositories.
Обеспечивает ACID properties для complex operations.
"""

from typing import Optional
import logging
from contextlib import asynccontextmanager

from .repositories.user_repository import UserRepository
from .repositories.wallet_repository import WalletRepository
from .repositories.transaction_repository import TransactionRepository
from .repositories.category_repository import CategoryRepository
from .repositories.merchant_repository import MerchantRepository
from .repositories.audit_repository import AuditRepository

logger = logging.getLogger(__name__)


class UnitOfWork:
    """
    Unit of Work pattern для управления database transactions.
    
    Использование:
        async with UnitOfWork(db) as uow:
            user = await uow.users.get_by_telegram_id(telegram_id)
            wallet = await uow.wallets.create(wallet_data)
            await uow.commit()
    
    При ошибке автоматически вызывается rollback.
    """
    
    def __init__(self, db):
        """
        Инициализация Unit of Work.
        
        Args:
            db: Database connection instance
        """
        self.db = db
        self._transaction = None
        
        # Repositories
        self.users: Optional[UserRepository] = None
        self.wallets: Optional[WalletRepository] = None
        self.transactions: Optional[TransactionRepository] = None
        self.categories: Optional[CategoryRepository] = None
        self.merchants: Optional[MerchantRepository] = None
        self.audit: Optional[AuditRepository] = None
        
        logger.debug("UnitOfWork initialized")
    
    async def __aenter__(self):
        """Начинает database transaction."""
        # Начинаем transaction
        self._transaction = self.db.transaction()
        await self._transaction.start()
        
        # Инициализируем repositories
        self.users = UserRepository(self.db)
        self.wallets = WalletRepository(self.db)
        self.transactions = TransactionRepository(self.db)
        self.categories = CategoryRepository(self.db)
        self.merchants = MerchantRepository(self.db)
        self.audit = AuditRepository(self.db)
        
        logger.debug("Transaction started")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Завершает transaction.
        
        Если exception - rollback, иначе commit.
        """
        if exc_type is not None:
            # Exception occurred - rollback
            await self.rollback()
            logger.error(f"Transaction rolled back due to {exc_type.__name__}: {exc_val}")
            return False  # Re-raise exception
        else:
            # No exception - commit
            await self.commit()
            logger.debug("Transaction committed")
            return True
    
    async def commit(self):
        """Commits текущую transaction."""
        if self._transaction:
            try:
                await self._transaction.commit()
                logger.debug("Transaction committed successfully")
            except Exception as e:
                logger.error(f"Failed to commit transaction: {e}")
                await self.rollback()
                raise
    
    async def rollback(self):
        """Rollback текущей transaction."""
        if self._transaction:
            try:
                await self._transaction.rollback()
                logger.debug("Transaction rolled back successfully")
            except Exception as e:
                logger.error(f"Failed to rollback transaction: {e}")
                raise


@asynccontextmanager
async def unit_of_work(db):
    """
    Context manager для Unit of Work.
    
    Usage:
        async with unit_of_work(db) as uow:
            await uow.users.create(user_data)
            await uow.commit()
    
    Args:
        db: Database connection
        
    Yields:
        UnitOfWork instance
    """
    uow = UnitOfWork(db)
    async with uow:
        yield uow


class UnitOfWorkFactory:
    """
    Factory для создания Unit of Work instances.
    
    Полезно для dependency injection.
    """
    
    def __init__(self, db):
        """
        Инициализация factory.
        
        Args:
            db: Database connection
        """
        self.db = db
    
    def create(self) -> UnitOfWork:
        """
        Создает новый Unit of Work instance.
        
        Returns:
            UnitOfWork instance
        """
        return UnitOfWork(self.db)
    
    @asynccontextmanager
    async def __call__(self):
        """
        Позволяет использовать factory как context manager.
        
        Usage:
            factory = UnitOfWorkFactory(db)
            async with factory() as uow:
                ...
        """
        async with unit_of_work(self.db) as uow:
            yield uow


# Example usage in services:
"""
class TransactionService:
    def __init__(self, db):
        self.db = db
    
    async def create_transaction_with_balance_update(
        self,
        transaction_data: dict,
        wallet_id: int
    ):
        async with unit_of_work(self.db) as uow:
            # Create transaction
            transaction = await uow.transactions.create(transaction_data)
            
            # Update wallet balance
            wallet = await uow.wallets.get_by_id(wallet_id)
            new_balance = wallet['balance'] + transaction_data['amount']
            await uow.wallets.update(wallet_id, {'balance': new_balance})
            
            # Log audit
            await uow.audit.create({
                'action': 'transaction.create',
                'user_id': transaction_data['user_id'],
                'details': {'transaction_id': transaction['id']}
            })
            
            # Commit all changes atomically
            await uow.commit()
            
            return transaction
"""
