"""
Sync command handler for manual wallet synchronization.
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from infrastructure.logging_config import get_logger

logger = get_logger(__name__)

router = Router()


@router.message(Command("sync"))
async def sync_command(message: Message, state: FSMContext, sync_service, scheduler):
    """Manual sync command"""
    logger.info(f"/sync command from user {message.from_user.id}")
    
    try:
        # Get user_id from state
        data = await state.get_data()
        user_id = data.get("user_id")
        
        if not user_id:
            await message.answer("❌ Please /start the bot first")
            return
        
        # Show sync menu
        await message.answer(
            text="🔄 **Wallet Synchronization**\n\n"
            "Choose an action:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Sync Now", callback_data="sync_now")],
                [InlineKeyboardButton(text="⏰ Enable Auto-Sync", callback_data="sync_enable")],
                [InlineKeyboardButton(text="⏸️ Disable Auto-Sync", callback_data="sync_disable")],
                [InlineKeyboardButton(text="📊 Sync Status", callback_data="sync_status")]
            ])
        )
        
    except Exception as e:
        logger.error(f"Error in sync command: {e}", exc_info=True)
        await message.answer("❌ Error loading sync menu")


@router.callback_query(F.data == "sync_now")
async def sync_now(callback: CallbackQuery, state: FSMContext, sync_service):
    """Trigger manual sync"""
    await callback.answer("🔄 Starting sync...", show_alert=False)
    
    try:
        data = await state.get_data()
        user_id = data.get("user_id")
        
        # Start sync
        await callback.message.edit_text("🔄 Syncing wallets...\n\nThis may take a moment...")
        
        result = await sync_service.sync_all_user_wallets(user_id)
        
        # Show results
        response = f"""✅ **Sync Complete!**

📊 **Results:**
• Wallets synced: {result['synced']}/{result['total_wallets']}
• New transactions: {result['new_transactions']}
• Auto-categorized: {result['categorized']}
• Need review: {result['uncategorized']}
"""
        
        if result['failed'] > 0:
            response += f"\n⚠️ Failed wallets: {result['failed']}"
        
        await callback.message.edit_text(
            text=response,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Sync Again", callback_data="sync_now")],
                [InlineKeyboardButton(text="◀️ Back", callback_data="sync_menu")]
            ])
        )
        
    except Exception as e:
        logger.error(f"Sync failed: {e}", exc_info=True)
        await callback.message.edit_text(
            text=f"❌ Sync failed: {str(e)}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Back", callback_data="sync_menu")]
            ])
        )


@router.callback_query(F.data == "sync_enable")
async def enable_auto_sync(callback: CallbackQuery, scheduler):
    """Enable auto-sync scheduler"""
    try:
        if scheduler.is_running():
            await callback.answer("✅ Auto-sync is already enabled", show_alert=True)
        else:
            scheduler.start(interval_hours=1)
            await callback.answer("✅ Auto-sync enabled (every hour)", show_alert=True)
            
            next_run = scheduler.get_next_run_time()
            await callback.message.edit_text(
                text=f"✅ **Auto-Sync Enabled**\n\n"
                f"Wallets will sync automatically every hour.\n"
                f"Next sync: {next_run.strftime('%Y-%m-%d %H:%M') if next_run else 'Unknown'}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Back", callback_data="sync_menu")]
                ])
            )
    except Exception as e:
        logger.error(f"Failed to enable auto-sync: {e}")
        await callback.answer("❌ Failed to enable auto-sync", show_alert=True)


@router.callback_query(F.data == "sync_disable")
async def disable_auto_sync(callback: CallbackQuery, scheduler):
    """Disable auto-sync scheduler"""
    try:
        if not scheduler.is_running():
            await callback.answer("⚠️ Auto-sync is already disabled", show_alert=True)
        else:
            scheduler.stop()
            await callback.answer("✅ Auto-sync disabled", show_alert=True)
            
            await callback.message.edit_text(
                text="⏸️ **Auto-Sync Disabled**\n\n"
                "Automatic wallet synchronization has been stopped.\n"
                "You can still sync manually using the 'Sync Now' button.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Back", callback_data="sync_menu")]
                ])
            )
    except Exception as e:
        logger.error(f"Failed to disable auto-sync: {e}")
        await callback.answer("❌ Failed to disable auto-sync", show_alert=True)


@router.callback_query(F.data == "sync_status")
async def show_sync_status(callback: CallbackQuery, scheduler):
    """Show sync status"""
    try:
        is_running = scheduler.is_running()
        next_run = scheduler.get_next_run_time()
        
        status_text = "🟢 **Enabled**" if is_running else "🔴 **Disabled**"
        next_run_text = next_run.strftime('%Y-%m-%d %H:%M') if next_run else "N/A"
        
        await callback.message.edit_text(
            text=f"📊 **Auto-Sync Status**\n\n"
            f"Status: {status_text}\n"
            f"Interval: Every 1 hour\n"
            f"Next run: {next_run_text}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Refresh", callback_data="sync_status")],
                [InlineKeyboardButton(text="◀️ Back", callback_data="sync_menu")]
            ])
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Failed to get sync status: {e}")
        await callback.answer("❌ Failed to get status", show_alert=True)


@router.callback_query(F.data == "sync_menu")
async def show_sync_menu(callback: CallbackQuery):
    """Show sync menu"""
    await callback.message.edit_text(
        text="🔄 **Wallet Synchronization**\n\n"
        "Choose an action:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Sync Now", callback_data="sync_now")],
            [InlineKeyboardButton(text="⏰ Enable Auto-Sync", callback_data="sync_enable")],
            [InlineKeyboardButton(text="⏸️ Disable Auto-Sync", callback_data="sync_disable")],
            [InlineKeyboardButton(text="📊 Sync Status", callback_data="sync_status")]
        ])
    )
    await callback.answer()
