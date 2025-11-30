"""
Merchant mappings repository for learning transaction categorization.
"""
from typing import Optional, List
from infrastructure.database import Database
from infrastructure.logging_config import get_logger
import uuid
from datetime import datetime

logger = get_logger(__name__)


class MerchantRepository:
    """Repository for merchant-category mappings"""
    
    def __init__(self, db: Database):
        self.db = db
        self._create_table()
    
    def _create_table(self):
        """Create merchant_mappings table if not exists"""
        query = """
        CREATE TABLE IF NOT EXISTS merchant_mappings (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            merchant_name TEXT NOT NULL,
            normalized_name TEXT NOT NULL,
            category_id TEXT NOT NULL,
            confidence INTEGER DEFAULT 100,
            usage_count INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, normalized_name)
        )
        """
        self.db.execute(query)
        
        # Create index for faster lookups
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_merchant_user_normalized 
            ON merchant_mappings(user_id, normalized_name)
        """)
        
        logger.info("Merchant mappings table initialized")
    
    def _normalize_merchant_name(self, name: str) -> str:
        """Normalize merchant name for matching"""
        # Remove special characters, convert to lowercase, strip whitespace
        import re
        normalized = re.sub(r'[^a-z0-9\s]', '', name.lower())
        normalized = ' '.join(normalized.split())  # Remove extra spaces
        return normalized
    
    def find_mapping(self, user_id: str, merchant_name: str) -> Optional[dict]:
        """Find existing merchant mapping"""
        normalized = self._normalize_merchant_name(merchant_name)
        
        query = """
        SELECT * FROM merchant_mappings 
        WHERE user_id = ? AND normalized_name = ?
        """
        
        result = self.db.fetch_one(query, (user_id, normalized))
        return dict(result) if result else None
    
    def find_similar_mappings(self, user_id: str, merchant_name: str, limit: int = 5) -> List[dict]:
        """Find similar merchant mappings using fuzzy matching"""
        normalized = self._normalize_merchant_name(merchant_name)
        words = normalized.split()
        
        if not words:
            return []
        
        # Build LIKE query for each word
        like_conditions = ' OR '.join(['normalized_name LIKE ?' for _ in words])
        query = f"""
        SELECT * FROM merchant_mappings 
        WHERE user_id = ? AND ({like_conditions})
        ORDER BY usage_count DESC, updated_at DESC
        LIMIT ?
        """
        
        params = [user_id] + [f'%{word}%' for word in words] + [limit]
        results = self.db.fetch_all(query, tuple(params))
        
        return [dict(row) for row in results]
    
    def create_mapping(
        self,
        user_id: str,
        merchant_name: str,
        category_id: str,
        confidence: int = 100
    ) -> dict:
        """Create new merchant mapping"""
        normalized = self._normalize_merchant_name(merchant_name)
        
        # Check if mapping already exists
        existing = self.find_mapping(user_id, merchant_name)
        if existing:
            # Update existing mapping
            return self.update_mapping(existing['id'], category_id, confidence)
        
        mapping_id = str(uuid.uuid4())
        
        query = """
        INSERT INTO merchant_mappings 
        (id, user_id, merchant_name, normalized_name, category_id, confidence, usage_count)
        VALUES (?, ?, ?, ?, ?, ?, 1)
        """
        
        self.db.execute(query, (
            mapping_id,
            user_id,
            merchant_name,
            normalized,
            category_id,
            confidence
        ))
        
        logger.info(f"Created merchant mapping: {merchant_name} -> {category_id}")
        
        return {
            'id': mapping_id,
            'user_id': user_id,
            'merchant_name': merchant_name,
            'normalized_name': normalized,
            'category_id': category_id,
            'confidence': confidence,
            'usage_count': 1
        }
    
    def update_mapping(
        self,
        mapping_id: str,
        category_id: str = None,
        confidence: int = None
    ) -> dict:
        """Update existing merchant mapping"""
        updates = []
        params = []
        
        if category_id:
            updates.append("category_id = ?")
            params.append(category_id)
        
        if confidence is not None:
            updates.append("confidence = ?")
            params.append(confidence)
        
        updates.append("usage_count = usage_count + 1")
        updates.append("updated_at = CURRENT_TIMESTAMP")
        
        params.append(mapping_id)
        
        query = f"""
        UPDATE merchant_mappings 
        SET {', '.join(updates)}
        WHERE id = ?
        """
        
        self.db.execute(query, tuple(params))
        
        # Fetch updated mapping
        result = self.db.fetch_one("SELECT * FROM merchant_mappings WHERE id = ?", (mapping_id,))
        return dict(result) if result else None
    
    def increment_usage(self, mapping_id: str):
        """Increment usage count for mapping"""
        query = """
        UPDATE merchant_mappings 
        SET usage_count = usage_count + 1, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """
        self.db.execute(query, (mapping_id,))
    
    def get_user_mappings(self, user_id: str, limit: int = 100) -> List[dict]:
        """Get all merchant mappings for user"""
        query = """
        SELECT * FROM merchant_mappings 
        WHERE user_id = ?
        ORDER BY usage_count DESC, updated_at DESC
        LIMIT ?
        """
        
        results = self.db.fetch_all(query, (user_id, limit))
        return [dict(row) for row in results]
    
    def get_top_merchants(self, user_id: str, limit: int = 10) -> List[dict]:
        """Get top merchants by usage count"""
        query = """
        SELECT merchant_name, category_id, usage_count 
        FROM merchant_mappings 
        WHERE user_id = ?
        ORDER BY usage_count DESC
        LIMIT ?
        """
        
        results = self.db.fetch_all(query, (user_id, limit))
        return [dict(row) for row in results]
    
    def delete_mapping(self, mapping_id: str) -> bool:
        """Delete merchant mapping"""
        query = "DELETE FROM merchant_mappings WHERE id = ?"
        self.db.execute(query, (mapping_id,))
        logger.info(f"Deleted merchant mapping: {mapping_id}")
        return True
