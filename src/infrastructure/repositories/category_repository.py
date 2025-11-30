"""
Category repository with Supabase integration
"""
from typing import List, Optional
from datetime import datetime

from .base import BaseRepository
from domain.category import Category, CategoryType
from infrastructure.supabase_client import SupabaseClient
from infrastructure.logging_config import get_logger

logger = get_logger(__name__)


class CategoryRepository(BaseRepository):
    """Category repository with Supabase backend"""
    
    def __init__(self, db_path: str = None):
        super().__init__(db_path)
        self.supabase = SupabaseClient()
    
    def get_user_categories(self, user_id: str, type: Optional[CategoryType] = None) -> List[Category]:
        """Get all categories for a user from Supabase"""
        try:
            logger.info(f"Fetching categories from Supabase for user {user_id}")
            categories_data = self.supabase.get_user_categories(user_id)
            logger.info(f"Found {len(categories_data)} categories in Supabase")
            
            categories = []
            for data in categories_data:
                # Filter by type if specified
                if type and data['type'] != type.value:
                    continue
                    
                category = Category(
                    id=data['id'],
                    user_id=data['user_id'],
                    name=data['name'],
                    icon=data.get('icon', '📁'),
                    type=CategoryType(data['type']),
                    color=data.get('color'),
                    created_at=datetime.fromisoformat(data['created_at']) if 'created_at' in data else datetime.utcnow(),
                    updated_at=datetime.fromisoformat(data['updated_at']) if 'updated_at' in data else datetime.utcnow()
                )
                categories.append(category)
            
            return categories
        except Exception as e:
            logger.error(f"Error fetching categories from Supabase: {e}", exc_info=True)
            return []
    
    def get_category_by_id(self, category_id: str) -> Optional[Category]:
        """Get category by ID from Supabase"""
        try:
            data = self.supabase.get_category_by_id(category_id)
            if data:
                return Category(
                    id=data['id'],
                    user_id=data['user_id'],
                    name=data['name'],
                    icon=data.get('icon', '📁'),
                    type=CategoryType(data['type']),
                    color=data.get('color'),
                    created_at=datetime.fromisoformat(data['created_at']) if 'created_at' in data else datetime.utcnow(),
                    updated_at=datetime.fromisoformat(data['updated_at']) if 'updated_at' in data else datetime.utcnow()
                )
            return None
        except Exception as e:
            logger.error(f"Error fetching category {category_id}: {e}", exc_info=True)
            return None
    
    def create_category(self, user_id: str, name: str, type: CategoryType, 
                       icon: Optional[str] = None, color: Optional[str] = None) -> Category:
        """Create a new category in Supabase"""
        try:
            data = self.supabase.create_category(user_id, name, icon or '📁', type.value)
            if data:
                logger.info(f"Category created in Supabase: {data['id']}")
                return Category(
                    id=data['id'],
                    user_id=data['user_id'],
                    name=data['name'],
                    icon=data.get('icon', '📁'),
                    type=CategoryType(data['type']),
                    color=data.get('color'),
                    created_at=datetime.fromisoformat(data['created_at']) if 'created_at' in data else datetime.utcnow(),
                    updated_at=datetime.fromisoformat(data['updated_at']) if 'updated_at' in data else datetime.utcnow()
                )
            return None
        except Exception as e:
            logger.error(f"Error creating category: {e}", exc_info=True)
            raise
    
    def update_category(self, category_id: str, name: str = None, icon: str = None) -> bool:
        """Update category in Supabase"""
        try:
            data = {}
            if name:
                data['name'] = name
            if icon:
                data['icon'] = icon
            
            result = self.supabase.update_category(category_id, data)
            return result is not None
        except Exception as e:
            logger.error(f"Error updating category {category_id}: {e}", exc_info=True)
            return False
    
    def delete(self, category_id: str) -> bool:
        """Delete category from Supabase"""
        try:
            return self.supabase.delete_category(category_id)
        except Exception as e:
            logger.error(f"Error deleting category {category_id}: {e}", exc_info=True)
            return False
