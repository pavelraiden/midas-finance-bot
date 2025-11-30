"""
Health Check System
Provides health status of all system components
"""
import asyncio
from typing import Dict, Optional
from datetime import datetime
from enum import Enum


class HealthStatus(Enum):
    """Health status enum."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class HealthChecker:
    """
    System health checker that monitors all critical components.
    """
    
    def __init__(self):
        self.last_check_time: Optional[datetime] = None
        self.last_check_result: Optional[Dict] = None
    
    async def check_database(self) -> Dict:
        """
        Check database connectivity and performance.
        
        Returns:
            Dict with status and details
        """
        try:
            from src.infrastructure.database.supabase_client import get_supabase_client
            
            client = get_supabase_client()
            
            start_time = datetime.now()
            response = client.table('users').select('id').limit(1).execute()
            end_time = datetime.now()
            
            response_time = (end_time - start_time).total_seconds() * 1000
            
            if response_time > 1000:
                return {
                    "status": HealthStatus.DEGRADED.value,
                    "response_time_ms": response_time,
                    "message": "Database response time is slow"
                }
            
            return {
                "status": HealthStatus.HEALTHY.value,
                "response_time_ms": response_time,
                "message": "Database is healthy"
            }
            
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY.value,
                "error": str(e),
                "message": "Database connection failed"
            }
    
    async def check_telegram(self) -> Dict:
        """
        Check Telegram Bot API connectivity.
        
        Returns:
            Dict with status and details
        """
        try:
            import os
            from aiogram import Bot
            
            token = os.environ.get("TELEGRAM_BOT_TOKEN")
            if not token:
                return {
                    "status": HealthStatus.UNHEALTHY.value,
                    "message": "Telegram token not configured"
                }
            
            bot = Bot(token=token)
            
            start_time = datetime.now()
            me = await bot.get_me()
            end_time = datetime.now()
            
            response_time = (end_time - start_time).total_seconds() * 1000
            
            await bot.session.close()
            
            return {
                "status": HealthStatus.HEALTHY.value,
                "response_time_ms": response_time,
                "bot_username": me.username,
                "message": "Telegram API is healthy"
            }
            
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY.value,
                "error": str(e),
                "message": "Telegram API connection failed"
            }
    
    async def check_claude(self) -> Dict:
        """
        Check Claude AI API connectivity.
        
        Returns:
            Dict with status and details
        """
        try:
            import os
            from anthropic import Anthropic
            
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                return {
                    "status": HealthStatus.UNHEALTHY.value,
                    "message": "Claude API key not configured"
                }
            
            client = Anthropic(api_key=api_key)
            
            start_time = datetime.now()
            message = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=10,
                messages=[{"role": "user", "content": "test"}]
            )
            end_time = datetime.now()
            
            response_time = (end_time - start_time).total_seconds() * 1000
            
            return {
                "status": HealthStatus.HEALTHY.value,
                "response_time_ms": response_time,
                "model": message.model,
                "message": "Claude API is healthy"
            }
            
        except Exception as e:
            return {
                "status": HealthStatus.DEGRADED.value,
                "error": str(e),
                "message": "Claude API check failed (non-critical)"
            }
    
    async def check_all(self) -> Dict:
        """
        Check health of all system components.
        
        Returns:
            Dict with overall status and component details
        """
        self.last_check_time = datetime.now()
        
        database_health, telegram_health, claude_health = await asyncio.gather(
            self.check_database(),
            self.check_telegram(),
            self.check_claude(),
            return_exceptions=True
        )
        
        if isinstance(database_health, Exception):
            database_health = {
                "status": HealthStatus.UNHEALTHY.value,
                "error": str(database_health)
            }
        
        if isinstance(telegram_health, Exception):
            telegram_health = {
                "status": HealthStatus.UNHEALTHY.value,
                "error": str(telegram_health)
            }
        
        if isinstance(claude_health, Exception):
            claude_health = {
                "status": HealthStatus.DEGRADED.value,
                "error": str(claude_health)
            }
        
        critical_unhealthy = (
            database_health["status"] == HealthStatus.UNHEALTHY.value or
            telegram_health["status"] == HealthStatus.UNHEALTHY.value
        )
        
        any_degraded = (
            database_health["status"] == HealthStatus.DEGRADED.value or
            telegram_health["status"] == HealthStatus.DEGRADED.value or
            claude_health["status"] == HealthStatus.DEGRADED.value
        )
        
        if critical_unhealthy:
            overall_status = HealthStatus.UNHEALTHY.value
        elif any_degraded:
            overall_status = HealthStatus.DEGRADED.value
        else:
            overall_status = HealthStatus.HEALTHY.value
        
        self.last_check_result = {
            "status": overall_status,
            "timestamp": self.last_check_time.isoformat(),
            "components": {
                "database": database_health,
                "telegram": telegram_health,
                "claude": claude_health
            }
        }
        
        return self.last_check_result
    
    def get_last_check(self) -> Optional[Dict]:
        """
        Get result of last health check without running a new check.
        
        Returns:
            Last check result or None if no check has been run
        """
        return self.last_check_result


health_checker = HealthChecker()


async def get_health_status() -> Dict:
    """
    Get current system health status.
    
    Returns:
        Dict with health status
    """
    return await health_checker.check_all()
