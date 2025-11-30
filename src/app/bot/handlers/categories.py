"""
Categories management handler with full CRUD operations.
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from infrastructure.repositories.category_repository import CategoryRepository
from infrastructure.repositories.transaction_repository import TransactionRepository
from domain.category import CategoryType
from infrastructure.logging_config import get_logger

logger = get_logger(__name__)

router = Router()


class CategoryStates(StatesGroup):
    """FSM states for category management"""
    waiting_for_name = State()
    waiting_for_icon = State()
    waiting_for_type = State()
    editing_name = State()
    editing_icon = State()


def get_categories_keyboard(categories: list, user_id: int, transaction_repo: TransactionRepository) -> InlineKeyboardMarkup:
    """Generate categories management keyboard with stats"""
    keyboard = []
    
    # Add each category with stats
    for cat in categories:
        # Get transaction count and total for this category
        count = transaction_repo.count_by_category(cat.id)
        total = transaction_repo.sum_by_category(cat.id)
        
        button_text = f"{cat.icon} {cat.name} ({count}) - ${total:.2f}"
        keyboard.append([
            InlineKeyboardButton(
                text=button_text,
                callback_data=f"category_view:{cat.id}"
            )
        ])
    
    # Add management buttons
    keyboard.append([
        InlineKeyboardButton(text="➕ Add Category", callback_data="category_add"),
        InlineKeyboardButton(text="📊 Statistics", callback_data="category_stats")
    ])
    keyboard.append([
        InlineKeyboardButton(text="◀️ Back", callback_data="main_menu")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


@router.callback_query(F.data == "categories")
async def show_categories(
    callback: CallbackQuery,
    category_repo: CategoryRepository,
    transaction_repo: TransactionRepository,
    state: FSMContext
):
    """Show categories management"""
    logger.info(f"Categories button clicked by user {callback.from_user.id}")
    
    try:
        data = await state.get_data()
        user_id = data.get("user_id")
        logger.info(f"User ID from state: {user_id}")
        
        if not user_id:
            logger.warning("No user_id in state!")
            await callback.answer("❌ User not found. Please /start again.", show_alert=True)
            return
        
        # Get all user categories
        logger.info(f"Fetching categories for user {user_id}")
        categories = category_repo.get_user_categories(user_id)
        logger.info(f"Found {len(categories) if categories else 0} categories")
        
        if not categories:
            await callback.message.edit_text(
                text="📁 **Categories Management**\n\n"
                "You don't have any categories yet.\n"
                "Create your first category to start organizing transactions!",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="➕ Add Category", callback_data="category_add")],
                    [InlineKeyboardButton(text="◀️ Back", callback_data="main_menu")]
                ])
            )
        else:
            keyboard = get_categories_keyboard(categories, user_id, transaction_repo)
            await callback.message.edit_text(
                text="📁 **Categories Management**\n\n"
                "Select a category to view details or manage:",
                reply_markup=keyboard
            )
        
        await callback.answer()
        logger.info("Categories displayed successfully")
        
    except Exception as e:
        logger.error(f"Error in show_categories: {e}", exc_info=True)
        await callback.answer("❌ Error loading categories. Please try again.", show_alert=True)


@router.callback_query(F.data == "category_add")
async def start_add_category(callback: CallbackQuery, state: FSMContext):
    """Start adding a new category"""
    await callback.message.edit_text(
        text="**Add New Category**\n\n"
        "Please enter the category name:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancel", callback_data="categories")]
        ])
    )
    await state.set_state(CategoryStates.waiting_for_name)
    await callback.answer()


@router.message(CategoryStates.waiting_for_name)
async def process_category_name(message: Message, state: FSMContext):
    """Process category name input"""
    name = message.text.strip()
    
    if not name or len(name) > 50:
        await message.answer(
            "❌ Invalid name. Please enter a name (1-50 characters):",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Cancel", callback_data="categories")]
            ])
        )
        return
    
    # Store name
    await state.update_data(new_category_name=name)
    
    # Ask for icon
    await message.answer(
        text=f"**Category Name:** {name}\n\n"
        "Now enter an emoji icon for this category:\n"
        "Examples: 🍔 🛒 🚗 🎮 💊 🏠",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancel", callback_data="categories")]
        ])
    )
    await state.set_state(CategoryStates.waiting_for_icon)


@router.message(CategoryStates.waiting_for_icon)
async def process_category_icon(message: Message, state: FSMContext):
    """Process category icon input"""
    icon = message.text.strip()
    
    if not icon or len(icon) > 10:
        await message.answer(
            "❌ Invalid icon. Please enter an emoji:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Cancel", callback_data="categories")]
            ])
        )
        return
    
    # Store icon
    await state.update_data(new_category_icon=icon)
    
    # Ask for type
    await message.answer(
        text="**Select Category Type:**",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="💸 Expense", callback_data="category_type:expense"),
                InlineKeyboardButton(text="💰 Income", callback_data="category_type:income")
            ],
            [InlineKeyboardButton(text="❌ Cancel", callback_data="categories")]
        ])
    )
    await state.set_state(CategoryStates.waiting_for_type)


@router.callback_query(CategoryStates.waiting_for_type, F.data.startswith("category_type:"))
async def process_category_type(
    callback: CallbackQuery,
    state: FSMContext,
    category_repo: CategoryRepository
):
    """Process category type selection and create category"""
    type_value = callback.data.split(":")[1]
    category_type = CategoryType.EXPENSE if type_value == "expense" else CategoryType.INCOME
    
    # Get stored data
    data = await state.get_data()
    user_id = data.get("user_id")
    name = data.get("new_category_name")
    icon = data.get("new_category_icon")
    
    try:
        # Create category
        category = category_repo.create_category(
            user_id=user_id,
            name=name,
            icon=icon,
            type=category_type
        )
        
        await callback.message.edit_text(
            text=f"✅ **Category Created!**\n\n"
            f"{icon} {name}\n"
            f"Type: {category_type.value.title()}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Back to Categories", callback_data="categories")]
            ])
        )
        
        # Clear category creation state but keep user_id and current_wallet_id
        current_wallet_id = data.get("current_wallet_id")
        await state.clear()
        await state.update_data(
            user_id=user_id,
            current_wallet_id=current_wallet_id
        )
        
        logger.info(f"Category created: {category.id} by user {user_id}")
        
    except Exception as e:
        logger.error(f"Failed to create category: {e}")
        await callback.message.edit_text(
            text=f"❌ Failed to create category: {str(e)}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Back", callback_data="categories")]
            ])
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("category_view:"))
async def view_category(
    callback: CallbackQuery,
    category_repo: CategoryRepository,
    transaction_repo: TransactionRepository
):
    """View category details"""
    category_id = callback.data.split(":")[1]
    
    try:
        category = category_repo.get_category_by_id(category_id)
        
        if not category:
            await callback.answer("❌ Category not found", show_alert=True)
            return
        
        # Get stats
        count = transaction_repo.count_by_category(category_id)
        total = transaction_repo.sum_by_category(category_id)
        
        await callback.message.edit_text(
            text=f"**Category Details**\n\n"
            f"{category.icon} **{category.name}**\n"
            f"Type: {category.type.value.title()}\n\n"
            f"📊 **Statistics:**\n"
            f"Transactions: {count}\n"
            f"Total: ${total:.2f}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✏️ Edit", callback_data=f"category_edit:{category_id}"),
                    InlineKeyboardButton(text="🗑️ Delete", callback_data=f"category_delete:{category_id}")
                ],
                [InlineKeyboardButton(text="◀️ Back", callback_data="categories")]
            ])
        )
        
    except Exception as e:
        logger.error(f"Failed to view category: {e}")
        await callback.answer("❌ Error loading category", show_alert=True)
    
    await callback.answer()


@router.callback_query(F.data.startswith("category_edit:"))
async def edit_category(callback: CallbackQuery, state: FSMContext):
    """Edit category"""
    category_id = callback.data.split(":")[1]
    
    await state.update_data(editing_category_id=category_id)
    
    await callback.message.edit_text(
        text="**Edit Category**\n\n"
        "What would you like to edit?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Name", callback_data=f"category_edit_name:{category_id}")],
            [InlineKeyboardButton(text="🎨 Icon", callback_data=f"category_edit_icon:{category_id}")],
            [InlineKeyboardButton(text="◀️ Back", callback_data=f"category_view:{category_id}")]
        ])
    )
    await callback.answer()


@router.callback_query(F.data.startswith("category_delete:"))
async def delete_category(
    callback: CallbackQuery,
    category_repo: CategoryRepository,
    transaction_repo: TransactionRepository
):
    """Delete category with confirmation"""
    category_id = callback.data.split(":")[1]
    
    try:
        category = category_repo.get_category_by_id(category_id)
        count = transaction_repo.count_by_category(category_id)
        
        if count > 0:
            await callback.message.edit_text(
                text=f"⚠️ **Warning**\n\n"
                f"Category **{category.icon} {category.name}** has {count} transactions.\n\n"
                f"Are you sure you want to delete it?\n"
                f"Transactions will be uncategorized.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(text="✅ Yes, Delete", callback_data=f"category_delete_confirm:{category_id}"),
                        InlineKeyboardButton(text="❌ Cancel", callback_data=f"category_view:{category_id}")
                    ]
                ])
            )
        else:
            # Delete immediately if no transactions
            category_repo.delete(category_id)
            await callback.message.edit_text(
                text=f"✅ Category **{category.icon} {category.name}** deleted!",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Back to Categories", callback_data="categories")]
                ])
            )
            logger.info(f"Category deleted: {category_id}")
        
    except Exception as e:
        logger.error(f"Failed to delete category: {e}")
        await callback.answer("❌ Error deleting category", show_alert=True)
    
    await callback.answer()


@router.callback_query(F.data.startswith("category_delete_confirm:"))
async def confirm_delete_category(
    callback: CallbackQuery,
    category_repo: CategoryRepository
):
    """Confirm category deletion"""
    category_id = callback.data.split(":")[1]
    
    try:
        category = category_repo.get_category_by_id(category_id)
        category_repo.delete(category_id)
        
        await callback.message.edit_text(
            text=f"✅ Category **{category.icon} {category.name}** deleted!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Back to Categories", callback_data="categories")]
            ])
        )
        logger.info(f"Category deleted: {category_id}")
        
    except Exception as e:
        logger.error(f"Failed to delete category: {e}")
        await callback.answer("❌ Error deleting category", show_alert=True)
    
    await callback.answer()


@router.callback_query(F.data == "category_stats")
async def show_category_stats(
    callback: CallbackQuery,
    category_repo: CategoryRepository,
    transaction_repo: TransactionRepository,
    state: FSMContext
):
    """Show category statistics"""
    data = await state.get_data()
    user_id = data.get("user_id")
    
    categories = category_repo.get_user_categories(user_id)
    
    if not categories:
        await callback.answer("No categories to show stats", show_alert=True)
        return
    
    # Build stats text
    stats_text = "📊 **Category Statistics**\n\n"
    
    total_expenses = 0
    total_income = 0
    
    for cat in categories:
        count = transaction_repo.count_by_category(cat.id)
        total = transaction_repo.sum_by_category(cat.id)
        
        if cat.type == CategoryType.EXPENSE:
            total_expenses += total
        else:
            total_income += total
        
        stats_text += f"{cat.icon} **{cat.name}**\n"
        stats_text += f"   {count} transactions | ${total:.2f}\n\n"
    
    stats_text += f"**Total Expenses:** ${total_expenses:.2f}\n"
    stats_text += f"**Total Income:** ${total_income:.2f}\n"
    stats_text += f"**Net:** ${total_income - total_expenses:.2f}"
    
    await callback.message.edit_text(
        text=stats_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Back to Categories", callback_data="categories")]
        ])
    )
    await callback.answer()
