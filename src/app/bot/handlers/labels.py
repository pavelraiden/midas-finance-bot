"""
Labels management handler with CRUD operations.
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from infrastructure.repositories.transaction_repository import TransactionRepository
from infrastructure.logging_config import get_logger
from domain.label import Label
import uuid
from datetime import datetime

logger = get_logger(__name__)

router = Router()


class LabelStates(StatesGroup):
    """FSM states for label management"""
    waiting_for_name = State()
    editing_name = State()


# Temporary in-memory storage for labels (replace with database later)
_labels_storage = {}


def get_user_labels(user_id: str) -> list:
    """Get user labels from storage"""
    return _labels_storage.get(user_id, [])


def create_label(user_id: str, name: str, color: str = "#3498db") -> Label:
    """Create a new label"""
    label = Label(
        id=str(uuid.uuid4()),
        user_id=user_id,
        name=name,
        color=color,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    if user_id not in _labels_storage:
        _labels_storage[user_id] = []
    
    _labels_storage[user_id].append(label)
    return label


def delete_label(user_id: str, label_id: str):
    """Delete a label"""
    if user_id in _labels_storage:
        _labels_storage[user_id] = [
            label for label in _labels_storage[user_id]
            if label.id != label_id
        ]


def count_label_usage(label_id: str, transaction_repo: TransactionRepository) -> int:
    """Count how many transactions use this label"""
    # TODO: Implement proper query when label_ids are properly stored
    return 0


def get_labels_keyboard(labels: list, user_id: str, transaction_repo: TransactionRepository) -> InlineKeyboardMarkup:
    """Generate labels management keyboard"""
    keyboard = []
    
    # Add labels in grid (2 per row)
    row = []
    for label in labels:
        count = count_label_usage(label.id, transaction_repo)
        button_text = f"#{label.name} ({count})"
        row.append(InlineKeyboardButton(
            text=button_text,
            callback_data=f"label_view:{label.id}"
        ))
        
        if len(row) == 2:
            keyboard.append(row)
            row = []
    
    # Add remaining button if odd number
    if row:
        keyboard.append(row)
    
    # Add management buttons
    keyboard.append([
        InlineKeyboardButton(text="➕ Add Label", callback_data="label_add")
    ])
    keyboard.append([
        InlineKeyboardButton(text="◀️ Back", callback_data="main_menu")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


@router.callback_query(F.data == "labels")
async def show_labels(
    callback: CallbackQuery,
    transaction_repo: TransactionRepository,
    state: FSMContext
):
    """Show labels management"""
    logger.info(f"Labels button clicked by user {callback.from_user.id}")
    
    try:
        data = await state.get_data()
        user_id = data.get("user_id")
        logger.info(f"User ID from state: {user_id}")
        
        if not user_id:
            logger.warning("No user_id in state!")
            await callback.answer("❌ User not found. Please /start again.", show_alert=True)
            return
        
        # Get user labels
        labels = get_user_labels(str(user_id))
        logger.info(f"Found {len(labels)} labels")
        
        if not labels:
            await callback.message.edit_text(
                text="🏷️ **Labels Management**\n\n"
                "You don't have any labels yet.\n"
                "Labels help you tag and organize transactions!\n\n"
                "Examples: #work, #personal, #business, #vacation",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="➕ Add Label", callback_data="label_add")],
                    [InlineKeyboardButton(text="◀️ Back", callback_data="main_menu")]
                ])
            )
        else:
            keyboard = get_labels_keyboard(labels, str(user_id), transaction_repo)
            await callback.message.edit_text(
                text="🏷️ **Labels Management**\n\n"
                "Select a label to view details or manage:",
                reply_markup=keyboard
            )
        
        await callback.answer()
        logger.info("Labels displayed successfully")
        
    except Exception as e:
        logger.error(f"Error in show_labels: {e}", exc_info=True)
        await callback.answer("❌ Error loading labels. Please try again.", show_alert=True)


@router.callback_query(F.data == "label_add")
async def start_add_label(callback: CallbackQuery, state: FSMContext):
    """Start adding a new label"""
    await callback.message.edit_text(
        text="**Add New Label**\n\n"
        "Please enter the label name (without #):\n"
        "Examples: work, personal, business, vacation",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancel", callback_data="labels")]
        ])
    )
    await state.set_state(LabelStates.waiting_for_name)
    await callback.answer()


@router.message(LabelStates.waiting_for_name)
async def process_label_name(
    message: Message,
    state: FSMContext,
    transaction_repo: TransactionRepository
):
    """Process label name input"""
    name = message.text.strip().replace("#", "").lower()
    
    if not name or len(name) > 30:
        await message.answer(
            "❌ Invalid name. Please enter a name (1-30 characters):",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Cancel", callback_data="labels")]
            ])
        )
        return
    
    # Get user_id
    data = await state.get_data()
    user_id = str(data.get("user_id"))
    
    # Check if label already exists
    existing_labels = get_user_labels(user_id)
    if any(label.name.lower() == name for label in existing_labels):
        await message.answer(
            f"❌ Label **#{name}** already exists!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Back to Labels", callback_data="labels")]
            ])
        )
        return
    
    try:
        # Create label
        label = create_label(user_id, name)
        
        await message.answer(
            text=f"✅ **Label Created!**\n\n"
            f"🏷️ #{label.name}\n\n"
            f"You can now use this label to tag transactions!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Back to Labels", callback_data="labels")]
            ])
        )
        
        # Clear state but keep user_id and current_wallet_id
        current_wallet_id = data.get("current_wallet_id")
        await state.clear()
        await state.update_data(
            user_id=data.get("user_id"),
            current_wallet_id=current_wallet_id
        )
        
        logger.info(f"Label created: {label.id} by user {user_id}")
        
    except Exception as e:
        logger.error(f"Failed to create label: {e}")
        await message.answer(
            text=f"❌ Failed to create label: {str(e)}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Back", callback_data="labels")]
            ])
        )


@router.callback_query(F.data.startswith("label_view:"))
async def view_label(
    callback: CallbackQuery,
    transaction_repo: TransactionRepository,
    state: FSMContext
):
    """View label details"""
    label_id = callback.data.split(":")[1]
    
    data = await state.get_data()
    user_id = str(data.get("user_id"))
    
    # Find label
    labels = get_user_labels(user_id)
    label = next((l for l in labels if l.id == label_id), None)
    
    if not label:
        await callback.answer("❌ Label not found", show_alert=True)
        return
    
    # Get usage count
    count = count_label_usage(label_id, transaction_repo)
    
    await callback.message.edit_text(
        text=f"**Label Details**\n\n"
        f"🏷️ **#{label.name}**\n\n"
        f"📊 **Statistics:**\n"
        f"Used in {count} transactions",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🗑️ Delete", callback_data=f"label_delete:{label_id}")],
            [InlineKeyboardButton(text="◀️ Back", callback_data="labels")]
        ])
    )
    await callback.answer()


@router.callback_query(F.data.startswith("label_delete:"))
async def delete_label_handler(
    callback: CallbackQuery,
    transaction_repo: TransactionRepository,
    state: FSMContext
):
    """Delete label"""
    label_id = callback.data.split(":")[1]
    
    data = await state.get_data()
    user_id = str(data.get("user_id"))
    
    # Find label
    labels = get_user_labels(user_id)
    label = next((l for l in labels if l.id == label_id), None)
    
    if not label:
        await callback.answer("❌ Label not found", show_alert=True)
        return
    
    try:
        # Delete label
        delete_label(user_id, label_id)
        
        await callback.message.edit_text(
            text=f"✅ Label **#{label.name}** deleted!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Back to Labels", callback_data="labels")]
            ])
        )
        logger.info(f"Label deleted: {label_id}")
        
    except Exception as e:
        logger.error(f"Failed to delete label: {e}")
        await callback.answer("❌ Error deleting label", show_alert=True)
    
    await callback.answer()
