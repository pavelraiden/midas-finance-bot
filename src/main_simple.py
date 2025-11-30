#!/usr/bin/env python3
"""
Midas Financial Bot - Simplified Version
Focuses on fixing immediate bugs without full infrastructure
"""
import os
import logging
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import asyncio
import sqlite3
from datetime import datetime

# Load environment
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize bot
bot = Bot(token=os.getenv('TELEGRAM_BOT_TOKEN'))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Initialize SQLite database
DB_PATH = '/home/ubuntu/spendee_bot/spendee_bot.db'

def init_db():
    """Initialize SQLite database with minimal schema"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Wallets table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS wallets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            balance REAL DEFAULT 0,
            currency TEXT DEFAULT 'USD',
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # Transactions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            wallet_id INTEGER,
            amount REAL NOT NULL,
            currency TEXT NOT NULL,
            category TEXT,
            note TEXT,
            label_ids TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (wallet_id) REFERENCES wallets(id)
        )
    ''')
    
    # Categories table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            icon TEXT,
            type TEXT DEFAULT 'expense',
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # Labels table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS labels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # AI Analyses table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ai_analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            analysis_type TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("✅ Database initialized")

# Helper functions
def get_or_create_user(telegram_id: int, username: str = None):
    """Get or create user in database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (telegram_id,))
    result = cursor.fetchone()
    
    if result:
        user_id = result[0]
    else:
        cursor.execute('INSERT INTO users (telegram_id, username) VALUES (?, ?)', 
                      (telegram_id, username))
        user_id = cursor.lastrowid
        
        # Create default wallet
        cursor.execute('INSERT INTO wallets (user_id, name, currency) VALUES (?, ?, ?)',
                      (user_id, 'Main Wallet', 'USD'))
        conn.commit()
    
    conn.close()
    return user_id

def get_user_wallet(user_id: int):
    """Get user's first wallet"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM wallets WHERE user_id = ? LIMIT 1', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

# Handlers
@dp.message(Command('start'))
async def cmd_start(message: types.Message):
    """Start command handler"""
    user_id = get_or_create_user(message.from_user.id, message.from_user.username)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Add Transaction", callback_data="add_transaction")],
        [InlineKeyboardButton(text="📁 Categories", callback_data="categories")],
        [InlineKeyboardButton(text="🏷️ Labels", callback_data="labels")],
        [InlineKeyboardButton(text="📊 Analytics", callback_data="analytics")],
        [InlineKeyboardButton(text="🤖 AI Finance Analysis", callback_data="ai_finance")],
        [InlineKeyboardButton(text="💳 Wallets", callback_data="wallets")]
    ])
    
    await message.answer(
        "🎯 **Midas Financial Bot**\n\n"
        "Welcome! Choose an option:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "ai_finance")
async def ai_finance_menu(callback: types.CallbackQuery):
    """AI Finance Analysis menu"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💡 Smart Insights", callback_data="ai_insights")],
        [InlineKeyboardButton(text="📊 Spending Patterns", callback_data="ai_patterns")],
        [InlineKeyboardButton(text="💰 Budget Tips", callback_data="ai_budget")],
        [InlineKeyboardButton(text="🎯 Savings Goals", callback_data="ai_savings")],
        [InlineKeyboardButton(text="📜 View History", callback_data="ai_history")],
        [InlineKeyboardButton(text="◀️ Back", callback_data="back_main")]
    ])
    
    await callback.message.edit_text(
        "🤖 **AI Finance Analysis**\n\n"
        "Choose analysis type:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data == "back_main")
async def back_to_main(callback: types.CallbackQuery):
    """Back to main menu"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Add Transaction", callback_data="add_transaction")],
        [InlineKeyboardButton(text="📁 Categories", callback_data="categories")],
        [InlineKeyboardButton(text="🏷️ Labels", callback_data="labels")],
        [InlineKeyboardButton(text="📊 Analytics", callback_data="analytics")],
        [InlineKeyboardButton(text="🤖 AI Finance Analysis", callback_data="ai_finance")],
        [InlineKeyboardButton(text="💳 Wallets", callback_data="wallets")]
    ])
    
    await callback.message.edit_text(
        "🎯 **Midas Financial Bot**\n\n"
        "Welcome! Choose an option:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("ai_"))
async def ai_analysis_handler(callback: types.CallbackQuery):
    """Handle AI analysis requests"""
    analysis_type = callback.data.replace("ai_", "")
    
    if analysis_type == "history":
        # Show history
        user_id = get_or_create_user(callback.from_user.id)
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT analysis_type, created_at 
            FROM ai_analyses 
            WHERE user_id = ? 
            ORDER BY created_at DESC 
            LIMIT 10
        ''', (user_id,))
        analyses = cursor.fetchall()
        conn.close()
        
        if not analyses:
            text = "📜 **Analysis History**\n\nNo analyses yet."
        else:
            text = "📜 **Analysis History**\n\n"
            for i, (atype, created_at) in enumerate(analyses, 1):
                text += f"{i}. {atype.title()} - {created_at}\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Back", callback_data="ai_finance")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
        await callback.answer()
        return
    
    # Simulate AI analysis
    await callback.message.edit_text("🤖 Analyzing your finances...", parse_mode="Markdown")
    await asyncio.sleep(2)
    
    # Mock AI response
    analysis_text = f"🤖 **{analysis_type.title()} Analysis**\n\n"
    analysis_text += "Based on your transaction history:\n\n"
    analysis_text += "• Total spending: $0.00\n"
    analysis_text += "• No transactions found\n\n"
    analysis_text += "💡 **Recommendation:**\n"
    analysis_text += "Start adding transactions to get personalized insights!"
    
    # Save to database
    user_id = get_or_create_user(callback.from_user.id)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO ai_analyses (user_id, analysis_type, content) 
        VALUES (?, ?, ?)
    ''', (user_id, analysis_type, analysis_text))
    conn.commit()
    conn.close()
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Refresh", callback_data=f"ai_{analysis_type}")],
        [InlineKeyboardButton(text="◀️ Back", callback_data="ai_finance")]
    ])
    
    await callback.message.edit_text(analysis_text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

# Placeholder handlers for other features
@dp.callback_query(F.data.in_({"categories", "labels", "analytics", "wallets", "add_transaction"}))
async def placeholder_handler(callback: types.CallbackQuery):
    """Placeholder for other features"""
    await callback.answer(f"✅ {callback.data.replace('_', ' ').title()} - Coming soon!", show_alert=True)

async def main():
    """Main entry point"""
    logger.info("🚀 Starting Midas Financial Bot (Simplified)")
    
    # Initialize database
    init_db()
    
    # Drop pending updates to avoid conflicts
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Start polling
    logger.info("✅ Bot is running!")
    await dp.start_polling(bot, drop_pending_updates=True)

if __name__ == '__main__':
    asyncio.run(main())
