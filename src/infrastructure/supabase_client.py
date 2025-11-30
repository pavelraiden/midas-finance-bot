"""
Supabase client for database operations
"""
import os
from typing import Optional, List, Dict, Any
import requests
from infrastructure.logging_config import get_logger

logger = get_logger(__name__)


class SupabaseClient:
    """Supabase client for REST API operations"""
    
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        self.headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
    
    def _request(self, method: str, table: str, params: dict = None, json_data: dict = None) -> Any:
        """Make request to Supabase REST API"""
        url = f"{self.url}/rest/v1/{table}"
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                params=params,
                json=json_data,
                timeout=10
            )
            response.raise_for_status()
            return response.json() if response.text else None
        except Exception as e:
            logger.error(f"Supabase request error: {e}")
            return None
    
    def select(self, table: str, columns: str = "*", filters: dict = None) -> List[Dict]:
        """Select data from table"""
        params = {"select": columns}
        if filters:
            for key, value in filters.items():
                params[key] = f"eq.{value}"
        
        result = self._request("GET", table, params=params)
        return result if result else []
    
    def insert(self, table: str, data: dict) -> Optional[Dict]:
        """Insert data into table"""
        result = self._request("POST", table, json_data=data)
        return result[0] if result and isinstance(result, list) else result
    
    def update(self, table: str, data: dict, filters: dict) -> Optional[Dict]:
        """Update data in table"""
        params = {}
        for key, value in filters.items():
            params[key] = f"eq.{value}"
        
        result = self._request("PATCH", table, params=params, json_data=data)
        return result[0] if result and isinstance(result, list) else result
    
    def delete(self, table: str, filters: dict) -> bool:
        """Delete data from table"""
        params = {}
        for key, value in filters.items():
            params[key] = f"eq.{value}"
        
        result = self._request("DELETE", table, params=params)
        return result is not None
    
    # User operations
    def get_user_by_telegram_id(self, telegram_id: int) -> Optional[Dict]:
        """Get user by Telegram ID"""
        users = self.select("users", filters={"telegram_id": telegram_id})
        return users[0] if users else None
    
    def create_user(self, telegram_id: int, username: str = None, 
                   first_name: str = None, last_name: str = None) -> Optional[Dict]:
        """Create user in Supabase"""
        import uuid
        data = {
            "id": str(uuid.uuid4()),
            "telegram_id": telegram_id,
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "default_currency": "USD"
        }
        return self.insert("users", data)
    
    def get_or_create_user(self, telegram_id: int, username: str = None,
                          first_name: str = None, last_name: str = None) -> Dict:
        """Get or create user"""
        user = self.get_user_by_telegram_id(telegram_id)
        if not user:
            user = self.create_user(telegram_id, username, first_name, last_name)
        return user
    
    # Category operations
    def get_user_categories(self, user_id: str) -> List[Dict]:
        """Get user categories"""
        return self.select("categories", filters={"user_id": user_id})
    
    def get_category_by_id(self, category_id: str) -> Optional[Dict]:
        """Get category by ID"""
        categories = self.select("categories", filters={"id": category_id})
        return categories[0] if categories else None
    
    def create_category(self, user_id: str, name: str, icon: str, 
                       category_type: str) -> Optional[Dict]:
        """Create category"""
        import uuid
        data = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": name,
            "icon": icon,
            "type": category_type
        }
        return self.insert("categories", data)
    
    def update_category(self, category_id: str, data: dict) -> Optional[Dict]:
        """Update category"""
        return self.update("categories", data, filters={"id": category_id})
    
    def delete_category(self, category_id: str) -> bool:
        """Delete category"""
        return self.delete("categories", filters={"id": category_id})
    
    # Wallet operations
    def get_user_wallets(self, user_id: str) -> List[Dict]:
        """Get user wallets"""
        return self.select("wallets", filters={"user_id": user_id})
    
    def get_wallet_by_id(self, wallet_id: str) -> Optional[Dict]:
        """Get wallet by ID"""
        wallets = self.select("wallets", filters={"id": wallet_id})
        return wallets[0] if wallets else None
    
    def create_wallet(self, user_id: str, name: str, currency: str = "USD",
                     balance: float = 0.0, wallet_type: str = "manual",
                     metadata: dict = None) -> Optional[Dict]:
        """Create wallet"""
        import uuid
        data = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": name,
            "currency": currency,
            "balance": str(balance),
            "wallet_type": wallet_type,
            "is_active": True,
            "metadata": metadata or {}
        }
        return self.insert("wallets", data)
    
    def update_wallet(self, wallet_id: str, data: dict) -> Optional[Dict]:
        """Update wallet"""
        return self.update("wallets", data, filters={"id": wallet_id})
    
    def delete_wallet(self, wallet_id: str) -> bool:
        """Delete wallet"""
        return self.delete("wallets", filters={"id": wallet_id})
