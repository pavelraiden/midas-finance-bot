"""
Transaction handlers with FSM.
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta

from app.bot.states.transaction_states import TransactionStates
from app.bot.keyboards.inline import (
    transaction_type_keyboard,
    categories_keyboard,
    currency_keyboard,
    date_selection_keyboard,
    skip_keyboard,
    confirmation_keyboard,
    back_keyboard
)
from app.services.transaction_service import TransactionService
from app.services.wallet_service import WalletService
from domain.transaction import TransactionType
from domain.category import CategoryType
from infrastructure.repositories.category_repository import CategoryRepository
from infrastructure.logging_config import get_logger
from app.utils.amount_parser import parse_amount_with_currency

logger = get_logger(__name__)

router = Router()


@router.callback_query(F.data == "add_transaction")
async def start_add_transaction(callback: CallbackQuery, state: FSMContext, wallet_service: WalletService):
    """Start adding a transaction."""
    logger.info(f"add_transaction callback received from user {callback.from_user.id}")
    try:
        # Get user_id from state (should already be set by /start)
        data = await state.get_data()
        user_id = data.get("user_id")
        logger.info(f"User ID from state: {user_id}")
        
        if not user_id:
            logger.warning("No user_id in state, using fallback")
            user_id = f"user_{callback.from_user.id}"
            await state.update_data(user_id=user_id)
        
        # Get or create default wallet
        wallet = wallet_service.get_or_create_default_wallet(user_id)
        logger.info(f"Using wallet: {wallet['id']}")
        
        # Store wallet_id in state
        await state.update_data(current_wallet_id=wallet['id'])
        
        await callback.message.edit_text(
            text="**Add Transaction**\n\nSelect transaction type:",
            reply_markup=transaction_type_keyboard()
        )
        await state.set_state(TransactionStates.selecting_type)
        await callback.answer()
        logger.info(f"Transaction flow started successfully for user {user_id}")
    except Exception as e:
        logger.error(f"Error in start_add_transaction: {e}", exc_info=True)
        await callback.answer("Error starting transaction. Please try again.", show_alert=True)


@router.callback_query(TransactionStates.selecting_type, F.data.startswith("type:"))
async def process_transaction_type(
    callback: CallbackQuery,
    state: FSMContext,
    category_repo: CategoryRepository
):
    """Process transaction type selection."""
    logger.info(f"process_transaction_type callback received: {callback.data}")
    try:
        # Extract type
        type_value = callback.data.split(":")[1]
        transaction_type = TransactionType(type_value)
        logger.info(f"Transaction type: {transaction_type}")
        
        # Store type
        await state.update_data(transaction_type=type_value)
        
        # Get user_id from state
        data = await state.get_data()
        user_id = data.get("user_id")
        logger.info(f"User ID from state: {user_id}")
        
        # Get categories for this type
        if transaction_type == TransactionType.INCOME:
            category_type = CategoryType.INCOME
        else:
            category_type = CategoryType.EXPENSE
        
        categories = category_repo.get_user_categories(user_id, category_type)
        logger.info(f"Found {len(categories)} categories for {category_type}")
        
        if not categories:
            await callback.message.edit_text(
                text="❌ No categories found. Please create categories first.",
                reply_markup=back_keyboard("main_menu")
            )
            await callback.answer()
            return
        
        # Show categories
        type_emoji = "💸" if transaction_type == TransactionType.EXPENSE else "💰"
        await callback.message.edit_text(
            text=f"**{type_emoji} {transaction_type.value.title()} Transaction**\n\nSelect category:",
            reply_markup=categories_keyboard(categories)
        )
        await state.set_state(TransactionStates.selecting_category)
        await callback.answer()
        logger.info("Category selection screen shown")
    except Exception as e:
        logger.error(f"Error in process_transaction_type: {e}", exc_info=True)
        await callback.answer("Error processing transaction type. Please try again.", show_alert=True)


@router.callback_query(TransactionStates.selecting_category, F.data.startswith("select_category:"))
async def process_category_selection(callback: CallbackQuery, state: FSMContext):
    """Process category selection."""
    # Extract category_id
    category_id = callback.data.split(":")[1]
    
    # Store category_id
    await state.update_data(category_id=category_id)
    
    # Ask for amount
    await callback.message.edit_text(
        text="**Enter Amount**\n\nPlease enter the transaction amount (e.g., 100.50):",
        reply_markup=back_keyboard("cancel")
    )
    await state.set_state(TransactionStates.entering_amount)
    await callback.answer()


@router.message(TransactionStates.entering_amount)
async def process_amount(message: Message, state: FSMContext):
    """Process amount input with smart parsing."""
    try:
        # Parse amount with flexible format support
        amount, currency = parse_amount_with_currency(message.text.strip())
        
        # Store amount and currency
        await state.update_data(
            amount=str(amount),
            currency=currency
        )
        
        # Ask for date
        await message.answer(
            text="**Select Date**\n\nWhen did this transaction occur?",
            reply_markup=date_selection_keyboard()
        )
        await state.set_state(TransactionStates.selecting_date)
        
    except ValueError as e:
        await message.answer(
            f"❌ Invalid amount format: {str(e)}\n\n"
            "Please enter amount in any of these formats:\n"
            "• 1021 eur\n"
            "• 100 usd\n"
            "• 50.5\n"
            "• €100\n"
            "• $50.50",
            reply_markup=back_keyboard("cancel")
        )


@router.callback_query(TransactionStates.selecting_date, F.data.startswith("date:"))
async def process_date_selection(callback: CallbackQuery, state: FSMContext):
    """Process date selection."""
    date_choice = callback.data.split(":")[1]
    
    if date_choice == "today":
        date = datetime.utcnow()
    elif date_choice == "yesterday":
        date = datetime.utcnow() - timedelta(days=1)
    elif date_choice == "skip":
        date = datetime.utcnow()
    else:
        # TODO: Implement custom date picker
        date = datetime.utcnow()
    
    # Store date
    await state.update_data(date=date.isoformat())
    
    # Ask for note
    await callback.message.edit_text(
        text="**Add Note (Optional)**\n\nEnter a description for this transaction or skip:",
        reply_markup=skip_keyboard()
    )
    await state.set_state(TransactionStates.entering_note)
    await callback.answer()


@router.callback_query(TransactionStates.entering_note, F.data == "skip_note")
async def skip_note(callback: CallbackQuery, state: FSMContext):
    """Skip note input."""
    await state.update_data(note=None)
    await show_confirmation(callback.message, state)
    await callback.answer()


@router.message(TransactionStates.entering_note)
async def process_note(message: Message, state: FSMContext):
    """Process note input."""
    note = message.text.strip()
    await state.update_data(note=note)
    await show_confirmation(message, state)


async def show_confirmation(message: Message, state: FSMContext):
    """Show transaction confirmation."""
    data = await state.get_data()
    
    # Format confirmation message
    transaction_type = TransactionType(data["transaction_type"])
    amount = Decimal(data["amount"])
    currency = data.get("currency", "USD")
    date = datetime.fromisoformat(data["date"])
    note = data.get("note")
    
    type_emoji = "💸" if transaction_type == TransactionType.EXPENSE else "💰"
    
    confirmation_text = f"""
**{type_emoji} Confirm Transaction**

**Type:** {transaction_type.value.title()}
**Amount:** {amount} {currency}
**Date:** {date.strftime("%Y-%m-%d %H:%M")}
**Note:** {note or "—"}

Is this correct?
"""
    
    await message.answer(
        text=confirmation_text,
        reply_markup=confirmation_keyboard()
    )
    await state.set_state(TransactionStates.confirming)


@router.callback_query(TransactionStates.confirming, F.data == "confirm_transaction:yes")
async def confirm_transaction(
    callback: CallbackQuery,
    state: FSMContext,
    transaction_service: TransactionService
):
    """Confirm and create transaction."""
    data = await state.get_data()
    
    # Get current_wallet_id safely
    current_wallet_id = data.get("current_wallet_id")
    if not current_wallet_id:
        await callback.message.edit_text(
            text="❌ Wallet not found. Please /start again.",
            reply_markup=back_keyboard("main_menu")
        )
        await callback.answer()
        return
    
    try:
        # Create transaction
        transaction = await transaction_service.create_transaction(
            wallet_id=current_wallet_id,
            user_id=data["user_id"],
            category_id=data["category_id"],
            transaction_type=data["transaction_type"],
            amount=Decimal(data["amount"]),
            currency=data.get("currency", "USD"),
            transaction_date=datetime.fromisoformat(data["date"]),
            note=data.get("note")
        )
        
        # Success message
        type_emoji = "💸" if transaction['type'] == 'expense' else "💰"
        await callback.message.edit_text(
            text=f"✅ Transaction Created!\n\n{type_emoji} {transaction['amount']} {transaction['currency']}",
            reply_markup=back_keyboard("main_menu")
        )
        
        # Clear state
        await state.clear()
        # Restore user_id and wallet_id
        await state.update_data(
            user_id=data["user_id"],
            current_wallet_id=data["current_wallet_id"]
        )
        
        logger.info(f"Transaction created: {transaction['id']}")
        
    except Exception as e:
        logger.error(f"Failed to create transaction: {e}")
        await callback.message.edit_text(
            text="❌ Failed to create transaction. Please try again.",
            reply_markup=back_keyboard("main_menu")
        )
        # Restore state even on error
        user_id = data.get("user_id")
        wallet_id = data.get("current_wallet_id")
        await state.clear()
        if user_id:
            await state.update_data(
                user_id=user_id,
                current_wallet_id=wallet_id
            )
    
    await callback.answer()


@router.callback_query(TransactionStates.confirming, F.data == "confirm_transaction:no")
async def cancel_transaction(callback: CallbackQuery, state: FSMContext):
    """Cancel transaction creation."""
    await callback.message.edit_text(
        text="❌ Transaction cancelled.",
        reply_markup=back_keyboard("main_menu")
    )
    # Restore state
    data = await state.get_data()
    user_id = data.get("user_id")
    wallet_id = data.get("current_wallet_id")
    await state.clear()
    if user_id:
        await state.update_data(
            user_id=user_id,
            current_wallet_id=wallet_id
        )
    await callback.answer()


@router.callback_query(F.data == "cancel")
async def cancel_operation(callback: CallbackQuery, state: FSMContext):
    """Cancel current operation."""
    await callback.message.edit_text(
        text="❌ Operation cancelled.",
        reply_markup=back_keyboard()
    )
    # Restore state
    data = await state.get_data()
    user_id = data.get("user_id")
    wallet_id = data.get("current_wallet_id")
    await state.clear()
    if user_id:
        await state.update_data(
            user_id=user_id,
            current_wallet_id=wallet_id
        )
    await callback.answer()
