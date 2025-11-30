"""
Pending transactions handler for reviewing uncategorized transactions.
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from infrastructure.logging_config import get_logger

router = Router()
logger = get_logger(__name__)


@router.message(Command("pending"))
async def show_pending_transactions(
    message: Message,
    transaction_service,
    category_repo
):
    """Show all pending/uncategorized transactions for user review"""
    user_id = str(message.from_user.id)
    logger.info(f"User {user_id} requested pending transactions")
    
    try:
        # Get all uncategorized transactions
        uncategorized_txs = await transaction_service.get_uncategorized_transactions(user_id)
        
        if not uncategorized_txs:
            await message.answer(
                "✅ No pending transactions!\n\n"
                "All your transactions have been categorized."
            )
            return
        
        # Show summary
        await message.answer(
            f"📋 **Pending Transactions: {len(uncategorized_txs)}**\n\n"
            f"These transactions need your review to confirm their category.\n"
            f"I'll show them one by one."
        )
        
        # Show first transaction for review
        await _show_transaction_for_review(
            message, 
            uncategorized_txs[0], 
            1, 
            len(uncategorized_txs),
            category_repo
        )
        
    except Exception as e:
        logger.error(f"Error showing pending transactions: {e}")
        await message.answer(
            "❌ Error loading pending transactions. Please try again later."
        )


async def _show_transaction_for_review(
    message: Message,
    tx: dict,
    current: int,
    total: int,
    category_repo
):
    """Show single transaction for user review"""
    # Get suggested category name
    category_name = "Unknown"
    if tx.get('category_id'):
        category = await category_repo.get_by_id(tx['category_id'])
        if category:
            category_name = category['name']
    
    # Format transaction details
    text = (
        f"**Transaction {current}/{total}**\n\n"
        f"💰 Amount: {tx['amount']} {tx['currency']}\n"
        f"📅 Date: {tx['date']}\n"
        f"🔗 Hash: `{tx['hash'][:16]}...`\n\n"
        f"🤖 Suggested Category: **{category_name}**\n"
        f"📊 Confidence: {tx.get('confidence', 0)}%\n\n"
        f"📝 Note: {tx.get('note', 'No note')}\n\n"
        f"Is this category correct?"
    )
    
    # TODO: Add inline keyboard with Confirm/Change/Skip buttons
    await message.answer(text)


@router.callback_query(F.data.startswith("pending_confirm:"))
async def confirm_pending_transaction(
    callback: CallbackQuery,
    transaction_service
):
    """Confirm suggested category for pending transaction"""
    tx_id = callback.data.split(":")[1]
    
    try:
        # Update transaction status to 'confirmed'
        await transaction_service.confirm_transaction(tx_id)
        
        await callback.message.edit_text(
            "✅ Transaction confirmed!\n\n"
            "Category has been applied."
        )
        
        # TODO: Show next pending transaction
        
    except Exception as e:
        logger.error(f"Error confirming transaction: {e}")
        await callback.answer("Error confirming transaction", show_alert=True)
