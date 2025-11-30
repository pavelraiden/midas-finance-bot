"""
Telegram Handlers for Confirmation Flow
Handles user confirmation of AI categorizations
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from typing import List, Dict, Any
from infrastructure.logging_config import get_logger
from app.services.confirmation_service import ConfirmationService

logger = get_logger(__name__)

# Create router
router = Router()


def create_confirmation_keyboard(
    confirmation_id: str,
    suggested_category: str,
    categories: List[Dict[str, Any]]
) -> InlineKeyboardMarkup:
    """
    Create inline keyboard for category confirmation.
    
    Args:
        confirmation_id: Confirmation request ID
        suggested_category: AI-suggested category
        categories: List of user categories
    
    Returns:
        InlineKeyboardMarkup
    """
    buttons = []
    
    # Add suggested category as first button (highlighted)
    buttons.append([
        InlineKeyboardButton(
            text=f"✅ {suggested_category} (AI suggestion)",
            callback_data=f"confirm:{confirmation_id}:{suggested_category}"
        )
    ])
    
    # Add other categories (2 per row)
    other_categories = [c for c in categories if c["name"] != suggested_category]
    for i in range(0, len(other_categories), 2):
        row = []
        for cat in other_categories[i:i+2]:
            row.append(
                InlineKeyboardButton(
                    text=cat["name"],
                    callback_data=f"confirm:{confirmation_id}:{cat['name']}"
                )
            )
        buttons.append(row)
    
    # Add "Other" option
    buttons.append([
        InlineKeyboardButton(
            text="❓ Other (manual entry)",
            callback_data=f"confirm:{confirmation_id}:__other__"
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(Command("pending"))
async def show_pending_confirmations(message: Message, confirmation_service: ConfirmationService):
    """
    Show pending confirmation requests.
    
    Command: /pending
    """
    user_id = str(message.from_user.id)
    
    # Get pending count
    pending_count = await confirmation_service.get_pending_count(user_id)
    
    if pending_count == 0:
        await message.answer("✅ No pending confirmations!")
        return
    
    await message.answer(
        f"📋 You have **{pending_count}** pending confirmation(s).\n\n"
        f"Use /sync to process new transactions and receive confirmation requests."
    )


@router.callback_query(F.data.startswith("confirm:"))
async def handle_confirmation_callback(
    callback: CallbackQuery,
    confirmation_service: ConfirmationService
):
    """
    Handle category confirmation button click.
    
    Callback data format: confirm:{confirmation_id}:{category}
    """
    user_id = str(callback.from_user.id)
    
    # Parse callback data
    parts = callback.data.split(":", 2)
    if len(parts) != 3:
        await callback.answer("❌ Invalid callback data", show_alert=True)
        return
    
    _, confirmation_id, category = parts
    
    # Handle "Other" option
    if category == "__other__":
        await callback.message.answer(
            "Please type the category name manually:",
            reply_markup=None
        )
        # TODO: Store state for manual category entry
        await callback.answer()
        return
    
    # Process confirmation
    success = await confirmation_service.process_confirmation(
        confirmation_id=confirmation_id,
        confirmed_category=category,
        user_id=user_id
    )
    
    if success:
        # Update message to show confirmation
        await callback.message.edit_text(
            f"{callback.message.text}\n\n"
            f"✅ **Confirmed as: {category}**",
            reply_markup=None
        )
        await callback.answer(f"✅ Categorized as {category}", show_alert=False)
        
        logger.info(f"✅ User {user_id} confirmed: {category}")
    else:
        await callback.answer("❌ Failed to confirm. Please try again.", show_alert=True)
        logger.error(f"❌ Failed to process confirmation: {confirmation_id}")


async def send_confirmation_request(
    message: Message,
    confirmation_service: ConfirmationService,
    confirmation_id: str
):
    """
    Send confirmation request to user.
    
    Args:
        message: Telegram message object
        confirmation_service: ConfirmationService instance
        confirmation_id: Confirmation request ID
    """
    # Get confirmation message
    confirmation_msg = await confirmation_service.get_confirmation_message(confirmation_id)
    
    if not confirmation_msg:
        await message.answer("❌ Confirmation request not found or expired.")
        return
    
    # Create keyboard
    keyboard = create_confirmation_keyboard(
        confirmation_id=confirmation_id,
        suggested_category=confirmation_msg["suggested_category"],
        categories=confirmation_msg["categories"]
    )
    
    # Send message
    await message.answer(
        confirmation_msg["text"],
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    
    logger.info(f"📤 Sent confirmation request: {confirmation_id}")


# Export router
__all__ = ["router", "send_confirmation_request", "create_confirmation_keyboard"]
