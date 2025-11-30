"""
Database Migration Manager
Automatically runs SQL migrations on startup
"""
import logging
import sqlite3
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)


class MigrationManager:
    """
    Manages database migrations.
    """
    
    def __init__(self, db_path: str):
        """
        Initialize migration manager.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self.migrations_dir = Path(__file__).parent.parent.parent / "migrations"
    
    def get_applied_migrations(self) -> List[str]:
        """
        Get list of applied migrations.
        
        Returns:
            List of migration filenames
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create migrations table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    migration_name TEXT UNIQUE NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            
            # Get applied migrations
            cursor.execute("SELECT migration_name FROM schema_migrations ORDER BY id")
            applied = [row[0] for row in cursor.fetchall()]
            
            conn.close()
            return applied
            
        except Exception as e:
            logger.error(f"Failed to get applied migrations: {e}")
            return []
    
    def apply_migration(self, migration_file: Path) -> bool:
        """
        Apply a single migration.
        
        Args:
            migration_file: Path to migration SQL file
        
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Read migration SQL
            with open(migration_file, 'r') as f:
                sql = f.read()
            
            # Execute migration
            cursor.executescript(sql)
            
            # Record migration
            cursor.execute(
                "INSERT INTO schema_migrations (migration_name) VALUES (?)",
                (migration_file.name,)
            )
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Applied migration: {migration_file.name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to apply migration {migration_file.name}: {e}")
            return False
    
    def run_migrations(self) -> bool:
        """
        Run all pending migrations.
        
        Returns:
            True if all migrations successful, False otherwise
        """
        try:
            # Create migrations directory if it doesn't exist
            self.migrations_dir.mkdir(exist_ok=True)
            
            # Get applied migrations
            applied = self.get_applied_migrations()
            logger.info(f"Applied migrations: {len(applied)}")
            
            # Get all migration files
            migration_files = sorted(self.migrations_dir.glob("*.sql"))
            
            if not migration_files:
                logger.info("No migration files found")
                return True
            
            # Apply pending migrations
            pending = [f for f in migration_files if f.name not in applied]
            
            if not pending:
                logger.info("All migrations already applied")
                return True
            
            logger.info(f"Applying {len(pending)} pending migrations...")
            
            for migration_file in pending:
                if not self.apply_migration(migration_file):
                    logger.error(f"Migration failed: {migration_file.name}")
                    return False
            
            logger.info(f"✅ All migrations applied successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to run migrations: {e}")
            return False


def run_database_migrations(db_path: str) -> bool:
    """
    Run all database migrations.
    
    Args:
        db_path: Path to SQLite database
    
    Returns:
        True if successful, False otherwise
    """
    manager = MigrationManager(db_path)
    return manager.run_migrations()
