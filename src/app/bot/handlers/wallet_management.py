"""
Wallet management handler with add/remove/monitor functionality.
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.services.wallet_service import WalletService
from infrastructure.logging_config import get_logger

logger = get_logger(__name__)

router = Router()


class WalletStates(StatesGroup):
    """FSM states for wallet management"""
    waiting_for_name = State()
    waiting_for_address = State()
    waiting_for_blockchain = State()
    waiting_for_initial_balance = State()


@router.callback_query(F.data == "wallets")
async def show_wallets(
    callback: CallbackQuery,
    state: FSMContext,
    wallet_service: WalletService
):
    """Show user's wallets with management options"""
    logger.info(f"Wallets button clicked by user {callback.from_user.id}")
    
    try:
        data = await state.get_data()
        user_id = data.get("user_id")
        logger.info(f"User ID from state: {user_id}")
        
        if not user_id:
            logger.warning("No user_id in state!")
            await callback.answer("❌ User not found. Please /start again.", show_alert=True)
            return
        
        # Get all user wallets
        wallets = wallet_service.get_user_wallets(user_id)
        logger.info(f"Found {len(wallets) if wallets else 0} wallets")
        
        # Build keyboard
        keyboard = []
        
        if wallets:
            for wallet in wallets:
                # Show balance and monitoring status
                monitor_emoji = "🟢" if wallet.is_active else "🔴"
                button_text = f"{monitor_emoji} {wallet.name} ({wallet.current_balance} {wallet.currency})"
                keyboard.append([
                    InlineKeyboardButton(
                        text=button_text,
                        callback_data=f"wallet_view:{wallet.id}"
                    )
                ])
        
        # Add management buttons
        keyboard.append([
            InlineKeyboardButton(text="➕ Add Wallet", callback_data="wallet_add"),
            InlineKeyboardButton(text="📊 Statistics", callback_data="wallet_stats")
        ])
        keyboard.append([
            InlineKeyboardButton(text="◀️ Back", callback_data="main_menu")
        ])
        
        text = "💳 **Your Wallets**\n\n"
        if wallets:
            text += "Select a wallet to view details or manage:\n\n"
            text += "🟢 = Auto-monitoring ON\n"
            text += "🔴 = Auto-monitoring OFF"
        else:
            text += "You don't have any wallets yet.\n"
            text += "Add your first wallet to start tracking!"
        
        await callback.message.edit_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await callback.answer()
        logger.info("Wallets displayed successfully")
        
    except Exception as e:
        logger.error(f"Error in show_wallets: {e}", exc_info=True)
        await callback.answer("❌ Error loading wallets. Please try again.", show_alert=True)


@router.callback_query(F.data == "wallet_add")
async def start_add_wallet(callback: CallbackQuery, state: FSMContext):
    """Start adding a new wallet"""
    await callback.message.edit_text(
        text="**Add New Wallet**\n\n"
        "Please enter the wallet name:\n"
        "Examples: Main Wallet, Savings, Trading",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancel", callback_data="wallets")]
        ])
    )
    await state.set_state(WalletStates.waiting_for_name)
    await callback.answer()


@router.message(WalletStates.waiting_for_name)
async def process_wallet_name(message: Message, state: FSMContext):
    """Process wallet name input"""
    name = message.text.strip()
    
    if not name or len(name) > 50:
        await message.answer(
            "❌ Invalid name. Please enter a name (1-50 characters):",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Cancel", callback_data="wallets")]
            ])
        )
        return
    
    # Store name
    await state.update_data(new_wallet_name=name)
    
    # Ask for blockchain
    await message.answer(
        text=f"**Wallet Name:** {name}\n\n"
        "Select blockchain:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🔷 Ethereum", callback_data="wallet_blockchain:ethereum"),
                InlineKeyboardButton(text="🔺 TRON", callback_data="wallet_blockchain:tron")
            ],
            [
                InlineKeyboardButton(text="🟡 Binance Smart Chain", callback_data="wallet_blockchain:bsc"),
                InlineKeyboardButton(text="🔵 Polygon", callback_data="wallet_blockchain:polygon")
            ],
            [InlineKeyboardButton(text="❌ Cancel", callback_data="wallets")]
        ])
    )
    await state.set_state(WalletStates.waiting_for_blockchain)


@router.callback_query(WalletStates.waiting_for_blockchain, F.data.startswith("wallet_blockchain:"))
async def process_wallet_blockchain(callback: CallbackQuery, state: FSMContext):
    """Process blockchain selection"""
    blockchain = callback.data.split(":")[1]
    
    # Store blockchain
    await state.update_data(new_wallet_blockchain=blockchain)
    
    # Ask for address
    blockchain_names = {
        "ethereum": "Ethereum",
        "tron": "TRON",
        "bsc": "Binance Smart Chain",
        "polygon": "Polygon"
    }
    
    await callback.message.edit_text(
        text=f"**Blockchain:** {blockchain_names.get(blockchain, blockchain)}\n\n"
        "Please enter the wallet address:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancel", callback_data="wallets")]
        ])
    )
    await state.set_state(WalletStates.waiting_for_address)
    await callback.answer()


@router.message(WalletStates.waiting_for_address)
async def process_wallet_address(message: Message, state: FSMContext, wallet_service: WalletService):
    """Process wallet address input and create wallet"""
    address = message.text.strip()
    
    # Basic validation
    if not address or len(address) < 20:
        await message.answer(
            "❌ Invalid address. Please enter a valid blockchain address:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Cancel", callback_data="wallets")]
            ])
        )
        return
    
    # Get stored data
    data = await state.get_data()
    user_id = data.get("user_id")
    name = data.get("new_wallet_name")
    blockchain = data.get("new_wallet_blockchain")
    
    try:
        # Create wallet
        wallet = wallet_service.create_wallet(
            user_id=user_id,
            name=name,
            address=address,
            blockchain=blockchain,
            currency="USD",
            initial_balance=0.0
        )
        
        await message.answer(
            text=f"✅ **Wallet Created!**\n\n"
            f"💳 {name}\n"
            f"🔗 {blockchain.upper()}\n"
            f"📍 {address[:10]}...{address[-8:]}\n\n"
            f"Auto-monitoring: 🟢 Enabled\n"
            f"Balance will be synced hourly!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Back to Wallets", callback_data="wallets")]
            ])
        )
        
        # Clear wallet creation state but keep user_id and current_wallet_id
        current_wallet_id = data.get("current_wallet_id")
        await state.clear()
        await state.update_data(
            user_id=user_id,
            current_wallet_id=current_wallet_id
        )
        
        logger.info(f"Wallet created: {wallet.id} by user {user_id}")
        
    except Exception as e:
        logger.error(f"Failed to create wallet: {e}")
        await message.answer(
            text=f"❌ Failed to create wallet: {str(e)}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Back", callback_data="wallets")]
            ])
        )


@router.callback_query(F.data.startswith("wallet_view:"))
async def view_wallet(
    callback: CallbackQuery,
    wallet_service: WalletService
):
    """View wallet details"""
    wallet_id = callback.data.split(":")[1]
    
    try:
        wallet = wallet_service.get_wallet_by_id(wallet_id)
        
        if not wallet:
            await callback.answer("❌ Wallet not found", show_alert=True)
            return
        
        monitor_status = "🟢 Enabled" if wallet.is_active else "🔴 Disabled"
        
        await callback.message.edit_text(
            text=f"**Wallet Details**\n\n"
            f"💳 **{wallet.name}**\n"
            f"🔗 Blockchain: {wallet.blockchain.upper() if hasattr(wallet, 'blockchain') else 'Unknown'}\n"
            f"💰 Balance: {wallet.current_balance} {wallet.currency}\n"
            f"📊 Auto-monitoring: {monitor_status}\n"
            f"📅 Created: {wallet.created_at.strftime('%Y-%m-%d')}\n",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="🔄 Toggle Monitor", callback_data=f"wallet_toggle:{wallet_id}"),
                    InlineKeyboardButton(text="📊 View Transactions", callback_data=f"wallet_transactions:{wallet_id}")
                ],
                [
                    InlineKeyboardButton(text="🗑️ Delete", callback_data=f"wallet_delete:{wallet_id}")
                ],
                [InlineKeyboardButton(text="◀️ Back", callback_data="wallets")]
            ])
        )
        
    except Exception as e:
        logger.error(f"Failed to view wallet: {e}")
        await callback.answer("❌ Error loading wallet", show_alert=True)
    
    await callback.answer()


@router.callback_query(F.data.startswith("wallet_toggle:"))
async def toggle_wallet_monitoring(
    callback: CallbackQuery,
    wallet_service: WalletService
):
    """Toggle wallet auto-monitoring"""
    wallet_id = callback.data.split(":")[1]
    
    try:
        wallet = wallet_service.get_wallet_by_id(wallet_id)
        
        # Toggle is_active
        new_status = not wallet.is_active
        wallet_service.update_wallet_status(wallet_id, new_status)
        
        status_text = "enabled" if new_status else "disabled"
        status_emoji = "🟢" if new_status else "🔴"
        
        await callback.answer(f"{status_emoji} Auto-monitoring {status_text}!", show_alert=True)
        
        # Refresh view
        await view_wallet(callback, wallet_service)
        
    except Exception as e:
        logger.error(f"Failed to toggle monitoring: {e}")
        await callback.answer("❌ Error toggling monitoring", show_alert=True)


@router.callback_query(F.data.startswith("wallet_delete:"))
async def delete_wallet(
    callback: CallbackQuery,
    wallet_service: WalletService
):
    """Delete wallet with confirmation"""
    wallet_id = callback.data.split(":")[1]
    
    try:
        wallet = wallet_service.get_wallet_by_id(wallet_id)
        
        await callback.message.edit_text(
            text=f"⚠️ **Warning**\n\n"
            f"Are you sure you want to delete wallet **{wallet.name}**?\n\n"
            f"This action cannot be undone!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Yes, Delete", callback_data=f"wallet_delete_confirm:{wallet_id}"),
                    InlineKeyboardButton(text="❌ Cancel", callback_data=f"wallet_view:{wallet_id}")
                ]
            ])
        )
        
    except Exception as e:
        logger.error(f"Failed to delete wallet: {e}")
        await callback.answer("❌ Error deleting wallet", show_alert=True)
    
    await callback.answer()


@router.callback_query(F.data.startswith("wallet_delete_confirm:"))
async def confirm_delete_wallet(
    callback: CallbackQuery,
    wallet_service: WalletService
):
    """Confirm wallet deletion"""
    wallet_id = callback.data.split(":")[1]
    
    try:
        wallet = wallet_service.get_wallet_by_id(wallet_id)
        wallet_service.delete_wallet(wallet_id)
        
        await callback.message.edit_text(
            text=f"✅ Wallet **{wallet.name}** deleted!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Back to Wallets", callback_data="wallets")]
            ])
        )
        logger.info(f"Wallet deleted: {wallet_id}")
        
    except Exception as e:
        logger.error(f"Failed to delete wallet: {e}")
        await callback.answer("❌ Error deleting wallet", show_alert=True)
    
    await callback.answer()


@router.callback_query(F.data == "wallet_stats")
async def show_wallet_stats(
    callback: CallbackQuery,
    wallet_service: WalletService,
    state: FSMContext
):
    """Show wallet statistics"""
    data = await state.get_data()
    user_id = data.get("user_id")
    
    wallets = wallet_service.get_user_wallets(user_id)
    
    if not wallets:
        await callback.answer("No wallets to show stats", show_alert=True)
        return
    
    # Build stats text
    stats_text = "📊 **Wallet Statistics**\n\n"
    
    total_balance = 0
    active_count = 0
    
    for wallet in wallets:
        total_balance += float(wallet.current_balance)
        if wallet.is_active:
            active_count += 1
        
        monitor_emoji = "🟢" if wallet.is_active else "🔴"
        stats_text += f"{monitor_emoji} **{wallet.name}**\n"
        stats_text += f"   {wallet.current_balance} {wallet.currency}\n\n"
    
    stats_text += f"**Total Wallets:** {len(wallets)}\n"
    stats_text += f"**Active Monitoring:** {active_count}/{len(wallets)}\n"
    stats_text += f"**Total Balance:** ${total_balance:.2f}"
    
    await callback.message.edit_text(
        text=stats_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Back to Wallets", callback_data="wallets")]
        ])
    )
    await callback.answer()
