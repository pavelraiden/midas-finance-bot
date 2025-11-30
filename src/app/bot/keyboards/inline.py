"""
Inline keyboards for bot
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Optional

def transaction_type_keyboard() -> InlineKeyboardMarkup:
    """Transaction type selection keyboard"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💰 Income", callback_data="type:income"),
            InlineKeyboardButton(text="💸 Expense", callback_data="type:expense")
        ],
        [InlineKeyboardButton(text="🔄 Transfer", callback_data="type:transfer")],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel")]
    ])

def categories_keyboard(categories: List, transaction_type: str = "expense") -> InlineKeyboardMarkup:
    """Categories selection keyboard"""
    buttons = []
    for category in categories:
        # Handle both dict and Category object
        if hasattr(category, 'icon'):
            icon = category.icon or '📁'
            name = category.name
            cat_id = category.id
        else:
            icon = category.get('icon', '📁')
            name = category['name']
            cat_id = category['id']
        buttons.append([InlineKeyboardButton(
            text=f"{icon} {name}", 
            callback_data=f"select_category:{cat_id}"
        )])
    
    buttons.append([InlineKeyboardButton(text="➕ Create New Category", callback_data="create_category")])
    buttons.append([InlineKeyboardButton(text="⬅️ Back", callback_data="back")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def currency_keyboard() -> InlineKeyboardMarkup:
    """Currency selection keyboard"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="USD $", callback_data="currency_USD"),
            InlineKeyboardButton(text="EUR €", callback_data="currency_EUR")
        ],
        [
            InlineKeyboardButton(text="GBP £", callback_data="currency_GBP"),
            InlineKeyboardButton(text="UAH ₴", callback_data="currency_UAH")
        ],
        [InlineKeyboardButton(text="⬅️ Back", callback_data="back")]
    ])

def date_selection_keyboard() -> InlineKeyboardMarkup:
    """Date selection keyboard"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Today", callback_data="date:today")],
        [InlineKeyboardButton(text="📅 Yesterday", callback_data="date:yesterday")],
        [InlineKeyboardButton(text="📅 Custom Date", callback_data="date:custom")],
        [InlineKeyboardButton(text="⬅️ Back", callback_data="back")]
    ])

def skip_keyboard() -> InlineKeyboardMarkup:
    """Skip button keyboard"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭️ Skip", callback_data="skip_note")],
        [InlineKeyboardButton(text="⬅️ Back", callback_data="back")]
    ])

def confirmation_keyboard() -> InlineKeyboardMarkup:
    """Confirmation keyboard"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Confirm", callback_data="confirm_transaction:yes"),
            InlineKeyboardButton(text="✏️ Edit", callback_data="confirm_transaction:edit")
        ],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="confirm_transaction:no")]
    ])

def back_keyboard(callback_data: str = "back_main") -> InlineKeyboardMarkup:
    """Back button keyboard"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Back", callback_data=callback_data)]
    ])

def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Main menu keyboard"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Add Transaction", callback_data="add_transaction"),
            InlineKeyboardButton(text="💳 Wallets", callback_data="wallets")
        ],
        [
            InlineKeyboardButton(text="📁 Categories", callback_data="categories"),
            InlineKeyboardButton(text="🏷️ Labels", callback_data="labels")
        ],
        [
            InlineKeyboardButton(text="📊 Analytics", callback_data="analytics"),
            InlineKeyboardButton(text="🤖 AI Finance", callback_data="ai_finance")
        ]
    ])

def labels_keyboard(labels: List[dict], selected: List[str] = None) -> InlineKeyboardMarkup:
    """Labels selection keyboard"""
    selected = selected or []
    buttons = []
    
    for label in labels:
        name = label['name']
        label_id = label['id']
        prefix = "✅ " if label_id in selected else ""
        buttons.append([InlineKeyboardButton(
            text=f"{prefix}{name}", 
            callback_data=f"label_{label_id}"
        )])
    
    buttons.append([InlineKeyboardButton(text="➕ Create New Label", callback_data="create_label")])
    buttons.append([InlineKeyboardButton(text="✅ Done", callback_data="labels_done")])
    buttons.append([InlineKeyboardButton(text="⬅️ Back", callback_data="back")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)
