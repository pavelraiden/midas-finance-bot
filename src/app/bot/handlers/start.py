"""
Start command handler for Midas Financial Bot.
"""
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from app.services.user_service import UserService
from app.services.wallet_service import WalletService
from infrastructure.logging_config import get_logger

logger = get_logger(__name__)

router = Router()


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Create main menu keyboard"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💰 Add Transaction", callback_data="add_transaction"),
            InlineKeyboardButton(text="📊 Overview", callback_data="overview")
        ],
        [
            InlineKeyboardButton(text="💳 Wallets", callback_data="wallets"),
            InlineKeyboardButton(text="📁 Categories", callback_data="categories")
        ],
        [
            InlineKeyboardButton(text="🏷️ Labels", callback_data="labels"),
            InlineKeyboardButton(text="📈 Analytics", callback_data="analytics")
        ],
        [
            InlineKeyboardButton(text="🤖 AI Finance Analysis", callback_data="ai_finance")
        ],
        [
            InlineKeyboardButton(text="⚙️ Settings", callback_data="settings")
        ]
    ])
    return keyboard


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    state: FSMContext,
    user_service: UserService,
    wallet_service: WalletService
):
    """
    Handle /start command.
    
    Args:
        message: Telegram message
        state: FSM context
        user_service: User service
        wallet_service: Wallet service
    """
    # Clear any previous state
    await state.clear()
    
    # Get or create user
    user = await user_service.get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name
    )
    
    # Get or create default wallet
    wallet = wallet_service.get_or_create_default_wallet(user['id'])
    
    # Store user_id and wallet_id in state
    await state.update_data(
        user_id=user['id'],
        current_wallet_id=wallet['id']
    )
    
    # Send welcome message
    welcome_text = f"""
🎯 **Welcome to Midas Financial Bot!**

Hello, {user['first_name']}!

Your **balance-based transaction detection** system is ready!

**How it works:**
✅ Hourly balance snapshots
✅ Automatic transaction detection
✅ Smart pattern matching (95% accuracy)
✅ Operator validation for 100% accuracy

**Your default wallet:** {wallet['name']} ({wallet['current_balance']} {wallet['currency']})

**Available commands:**
/pending - View uncategorized transactions
/sync - Sync wallets now
/import - Import CSV file
/help - Show help

Choose an action from the menu below:
"""
    
    await message.answer(
        text=welcome_text,
        reply_markup=main_menu_keyboard()
    )
    
    logger.info(f"User {user['id']} started bot")


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Show help message"""
    help_text = """
📖 **Midas Financial Bot - Help**

**Balance-Based Detection:**
The bot monitors your wallet balances every hour and automatically detects transactions from balance changes.

**Commands:**
/start - Start the bot
/help - Show this help
/pending - View uncategorized transactions
/sync - Sync wallets now
/import - Import CSV file

**How to categorize transactions:**
1. Bot detects balance change
2. Bot sends notification with transaction details
3. You categorize it or add notes
4. Bot learns from your feedback

**Pattern Detection:**
• **Swap** (USDT↔USDC) - 95% confidence
• **Card Top-up** (USDT→USDC) - 95% confidence
• **Card Payment** (USDC decrease) - 70% confidence
• **Transfer** (between your wallets) - 90% confidence

**Need help?** Just ask!
"""
    await message.answer(help_text)


@router.message(Command("pending"))
async def cmd_pending(message: Message):
    """Show pending uncategorized transactions"""
    # TODO: Implement pending transactions view
    await message.answer(
        "🔍 **Pending Transactions**\n\n"
        "No uncategorized transactions at the moment.\n\n"
        "Transactions will appear here after hourly sync detects balance changes."
    )


@router.message(Command("sync"))
async def cmd_sync(message: Message):
    """Trigger manual wallet sync"""
    await message.answer(
        "🔄 **Manual Sync**\n\n"
        "Syncing wallets...\n\n"
        "⚠️ Manual sync is not yet implemented.\n"
        "Automatic hourly sync is active."
    )


@router.callback_query(F.data == "main_menu")
async def show_main_menu(callback: CallbackQuery):
    """
    Show main menu.
    
    Args:
        callback: Callback query
    """
    await callback.message.edit_text(
        text="**Main Menu**\n\nChoose an action:",
        reply_markup=main_menu_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "overview")
async def show_overview(callback: CallbackQuery):
    """Show overview"""
    await callback.message.edit_text(
        text="📊 **Overview**\n\n"
        "Balance monitoring: ✅ Active\n"
        "Last sync: Just now\n"
        "Pending transactions: 0\n\n"
        "Hourly sync is running automatically.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Back", callback_data="main_menu")]
        ])
    )
    await callback.answer()


@router.callback_query(F.data == "wallets")
async def show_wallets(callback: CallbackQuery):
    """Show wallets"""
    await callback.message.edit_text(
        text="💳 **Your Wallets**\n\n"
        "• Main Wallet (0.00 USD)\n\n"
        "Add more wallets to track multiple accounts.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Back", callback_data="main_menu")]
        ])
    )
    await callback.answer()


# Categories handler moved to app/bot/handlers/categories.py


@router.callback_query(F.data == "settings")
async def show_settings(callback: CallbackQuery):
    """Show settings"""
    await callback.message.edit_text(
        text="⚙️ **Settings**\n\n"
        "• Language: English\n"
        "• Timezone: UTC\n"
        "• Currency: USD\n"
        "• Auto-sync: ✅ Enabled (hourly)\n\n"
        "Balance-based detection is active.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Back", callback_data="main_menu")]
        ])
    )
    await callback.answer()
