"""
Global Exception Handler for Telegram Bot
Catches all unhandled exceptions and provides user-friendly error messages
"""
import traceback
from typing import Optional
from aiogram import types
from aiogram.dispatcher.middlewares import BaseMiddleware
from src.infrastructure.error_handling.exceptions import (
    MidasException,
    DatabaseError,
    ValidationError,
    ExternalAPIError,
    AuthenticationError
)
from src.infrastructure.logging.audit_logger import AuditLogger


class GlobalExceptionHandler(BaseMiddleware):
    """
    Middleware to catch and handle all unhandled exceptions in bot handlers.
    """
    
    def __init__(self):
        super().__init__()
        self.audit_logger = AuditLogger()
    
    async def on_pre_process_message(self, message: types.Message, data: dict):
        """Called before processing a message."""
        pass
    
    async def on_process_message(self, message: types.Message, data: dict):
        """Called during message processing."""
        pass
    
    async def on_post_process_message(self, message: types.Message, data: dict, exception: Optional[Exception] = None):
        """
        Called after message processing, handles exceptions.
        
        Args:
            message: Telegram message object
            data: Handler data
            exception: Exception that occurred, if any
        """
        if exception:
            await self.handle_exception(message, exception)
    
    async def handle_exception(self, message: types.Message, exception: Exception):
        """
        Handle exception and send user-friendly error message.
        
        Args:
            message: Telegram message object
            exception: Exception that occurred
        """
        user_id = message.from_user.id if message.from_user else None
        
        error_context = {
            "user_id": user_id,
            "message_text": message.text[:100] if message.text else None,
            "exception_type": type(exception).__name__,
            "exception_message": str(exception),
            "traceback": traceback.format_exc()
        }
        
        self.audit_logger.log_action(
            "error_handling",
            "exception_caught",
            error_context
        )
        
        if isinstance(exception, MidasException):
            user_message = exception.get_user_friendly_message()
        elif isinstance(exception, ValidationError):
            user_message = f"❌ Validation error: {str(exception)}"
        elif isinstance(exception, DatabaseError):
            user_message = "❌ Database error occurred. Please try again later."
        elif isinstance(exception, ExternalAPIError):
            user_message = "❌ External service error. Please try again later."
        elif isinstance(exception, AuthenticationError):
            user_message = "❌ Authentication failed. Please try again."
        else:
            user_message = (
                "❌ An unexpected error occurred. "
                "Our team has been notified and will fix it soon."
            )
        
        try:
            await message.reply(user_message)
        except Exception as e:
            self.audit_logger.log_action(
                "error_handling",
                "failed_to_send_error_message",
                {
                    "user_id": user_id,
                    "original_exception": str(exception),
                    "send_error": str(e)
                }
            )


class ErrorNotifier:
    """
    Notifies administrators about critical errors.
    """
    
    def __init__(self, admin_chat_ids: list[int]):
        """
        Initialize error notifier.
        
        Args:
            admin_chat_ids: List of admin Telegram chat IDs
        """
        self.admin_chat_ids = admin_chat_ids
        self.audit_logger = AuditLogger()
    
    async def notify_critical_error(
        self,
        bot,
        error_type: str,
        error_message: str,
        context: dict
    ):
        """
        Notify admins about a critical error.
        
        Args:
            bot: Telegram bot instance
            error_type: Type of error
            error_message: Error message
            context: Additional context
        """
        notification = (
            f"🚨 CRITICAL ERROR\n\n"
            f"Type: {error_type}\n"
            f"Message: {error_message}\n\n"
            f"Context:\n"
        )
        
        for key, value in context.items():
            notification += f"- {key}: {value}\n"
        
        for admin_id in self.admin_chat_ids:
            try:
                await bot.send_message(admin_id, notification)
            except Exception as e:
                self.audit_logger.log_action(
                    "error_notification",
                    "failed_to_notify_admin",
                    {
                        "admin_id": admin_id,
                        "error": str(e)
                    }
                )


def setup_error_handling(dp, admin_chat_ids: list[int]):
    """
    Setup global error handling for the bot.
    
    Args:
        dp: Dispatcher instance
        admin_chat_ids: List of admin chat IDs for notifications
    """
    dp.middleware.setup(GlobalExceptionHandler())
    
    error_notifier = ErrorNotifier(admin_chat_ids)
    
    return error_notifier
