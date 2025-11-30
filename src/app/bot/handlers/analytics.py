"""
Analytics dashboard handler with charts and statistics.
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta
from decimal import Decimal
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import io
from collections import defaultdict

from infrastructure.repositories.transaction_repository import TransactionRepository
from infrastructure.repositories.category_repository import CategoryRepository
from domain.transaction import TransactionType
from infrastructure.logging_config import get_logger

logger = get_logger(__name__)

router = Router()


def generate_monthly_spending_chart(transactions: list) -> io.BytesIO:
    """Generate monthly spending bar chart"""
    if not transactions:
        # Create empty chart
        plt.figure(figsize=(10, 6))
        plt.text(0.5, 0.5, 'No data available', 
                ha='center', va='center', fontsize=16)
        plt.axis('off')
    else:
        # Group by date
        daily_spending = defaultdict(Decimal)
        for tx in transactions:
            if tx.type == TransactionType.EXPENSE:
                date_key = tx.date.date()
                daily_spending[date_key] += tx.amount
        
        # Sort by date
        dates = sorted(daily_spending.keys())
        amounts = [float(daily_spending[d]) for d in dates]
        
        # Create chart
        plt.figure(figsize=(12, 6))
        plt.bar(range(len(dates)), amounts, color='#e74c3c', alpha=0.7)
        plt.title('Daily Spending (Last 30 Days)', fontsize=16, fontweight='bold')
        plt.xlabel('Date', fontsize=12)
        plt.ylabel('Amount ($)', fontsize=12)
        plt.xticks(range(len(dates)), [d.strftime('%m/%d') for d in dates], rotation=45)
        plt.grid(axis='y', alpha=0.3)
        plt.tight_layout()
    
    # Save to buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    plt.close()
    
    return buf


def generate_category_pie_chart(transactions: list, categories: dict) -> io.BytesIO:
    """Generate category distribution pie chart"""
    if not transactions:
        # Create empty chart
        plt.figure(figsize=(10, 8))
        plt.text(0.5, 0.5, 'No data available', 
                ha='center', va='center', fontsize=16)
        plt.axis('off')
    else:
        # Group by category
        category_spending = defaultdict(Decimal)
        for tx in transactions:
            if tx.type == TransactionType.EXPENSE:
                category_spending[tx.category_id] += tx.amount
        
        # Prepare data
        labels = []
        sizes = []
        colors = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6', 
                 '#1abc9c', '#34495e', '#e67e22', '#95a5a6', '#d35400']
        
        for cat_id, amount in category_spending.items():
            category = categories.get(cat_id)
            if category:
                labels.append(f"{category.icon} {category.name}")
            else:
                labels.append("Unknown")
            sizes.append(float(amount))
        
        # Create pie chart
        plt.figure(figsize=(10, 8))
        plt.pie(sizes, labels=labels, colors=colors[:len(labels)], 
               autopct='%1.1f%%', startangle=90)
        plt.title('Spending by Category', fontsize=16, fontweight='bold')
        plt.axis('equal')
        plt.tight_layout()
    
    # Save to buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    plt.close()
    
    return buf


def generate_income_vs_expenses_chart(transactions: list) -> io.BytesIO:
    """Generate income vs expenses comparison chart"""
    if not transactions:
        # Create empty chart
        plt.figure(figsize=(10, 6))
        plt.text(0.5, 0.5, 'No data available', 
                ha='center', va='center', fontsize=16)
        plt.axis('off')
    else:
        # Calculate totals
        total_income = sum(float(tx.amount) for tx in transactions 
                          if tx.type == TransactionType.INCOME)
        total_expenses = sum(float(tx.amount) for tx in transactions 
                            if tx.type == TransactionType.EXPENSE)
        net = total_income - total_expenses
        
        # Create bar chart
        plt.figure(figsize=(10, 6))
        categories = ['Income', 'Expenses', 'Net']
        values = [total_income, total_expenses, net]
        colors = ['#2ecc71', '#e74c3c', '#3498db' if net >= 0 else '#e74c3c']
        
        bars = plt.bar(categories, values, color=colors, alpha=0.7)
        plt.title('Income vs Expenses', fontsize=16, fontweight='bold')
        plt.ylabel('Amount ($)', fontsize=12)
        plt.grid(axis='y', alpha=0.3)
        
        # Add value labels on bars
        for bar, value in zip(bars, values):
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height,
                    f'${value:.2f}',
                    ha='center', va='bottom', fontsize=11, fontweight='bold')
        
        plt.tight_layout()
    
    # Save to buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    plt.close()
    
    return buf


@router.callback_query(F.data == "analytics")
async def show_analytics_menu(callback: CallbackQuery):
    """Show analytics menu"""
    logger.info(f"Analytics button clicked by user {callback.from_user.id}")
    
    try:
        await callback.message.edit_text(
            text="📊 **Analytics Dashboard**\n\n"
            "Select the type of analytics you want to view:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="📊 Monthly Spending", callback_data="analytics_monthly"),
                    InlineKeyboardButton(text="🥧 Categories", callback_data="analytics_categories")
                ],
                [
                    InlineKeyboardButton(text="💰 Income vs Expenses", callback_data="analytics_income_expenses"),
                    InlineKeyboardButton(text="📈 Top Expenses", callback_data="analytics_top")
                ],
                [InlineKeyboardButton(text="◀️ Back", callback_data="main_menu")]
            ])
        )
        await callback.answer()
        logger.info("Analytics menu displayed successfully")
    except Exception as e:
        logger.error(f"Error in show_analytics_menu: {e}", exc_info=True)
        await callback.answer("❌ Error loading analytics. Please try again.", show_alert=True)


@router.callback_query(F.data == "analytics_monthly")
async def show_monthly_analytics(
    callback: CallbackQuery,
    transaction_repo: TransactionRepository,
    state: FSMContext
):
    """Show monthly spending chart"""
    await callback.answer("Generating chart...")
    
    data = await state.get_data()
    user_id = data.get("user_id")
    
    if not user_id:
        await callback.answer("❌ User not found", show_alert=True)
        return
    
    try:
        # Get transactions from last 30 days
        start_date = datetime.utcnow() - timedelta(days=30)
        transactions = transaction_repo.get_user_transactions(user_id)
        
        # Filter by date
        recent_transactions = [
            tx for tx in transactions 
            if tx.date >= start_date
        ]
        
        # Generate chart
        chart_buf = generate_monthly_spending_chart(recent_transactions)
        
        # Save to temp file
        chart_path = f"/tmp/monthly_spending_{user_id}.png"
        with open(chart_path, 'wb') as f:
            f.write(chart_buf.getvalue())
        
        # Send as photo
        await callback.message.delete()
        await callback.message.answer_photo(
            photo=FSInputFile(chart_path),
            caption="📊 **Monthly Spending Chart**\n\nLast 30 days",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton("◀️ Back to Analytics", callback_data="analytics")]
            ])
        )
        
        logger.info(f"Monthly analytics generated for user {user_id}")
        
    except Exception as e:
        logger.error(f"Failed to generate monthly analytics: {e}", exc_info=True)
        await callback.message.edit_text(
            text=f"❌ Failed to generate chart: {str(e)}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton("◀️ Back", callback_data="analytics")]
            ])
        )


@router.callback_query(F.data == "analytics_categories")
async def show_category_analytics(
    callback: CallbackQuery,
    transaction_repo: TransactionRepository,
    category_repo: CategoryRepository,
    state: FSMContext
):
    """Show category distribution chart"""
    await callback.answer("Generating chart...")
    
    data = await state.get_data()
    user_id = data.get("user_id")
    
    if not user_id:
        await callback.answer("❌ User not found", show_alert=True)
        return
    
    try:
        # Get transactions from last 30 days
        start_date = datetime.utcnow() - timedelta(days=30)
        transactions = transaction_repo.get_user_transactions(user_id)
        
        # Filter by date
        recent_transactions = [
            tx for tx in transactions 
            if tx.date >= start_date
        ]
        
        # Get categories
        categories = category_repo.get_user_categories(user_id)
        categories_dict = {cat.id: cat for cat in categories}
        
        # Generate chart
        chart_buf = generate_category_pie_chart(recent_transactions, categories_dict)
        
        # Save to temp file
        chart_path = f"/tmp/category_pie_{user_id}.png"
        with open(chart_path, 'wb') as f:
            f.write(chart_buf.getvalue())
        
        # Send as photo
        await callback.message.delete()
        await callback.message.answer_photo(
            photo=FSInputFile(chart_path),
            caption="🥧 **Spending by Category**\n\nLast 30 days",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton("◀️ Back to Analytics", callback_data="analytics")]
            ])
        )
        
        logger.info(f"Category analytics generated for user {user_id}")
        
    except Exception as e:
        logger.error(f"Failed to generate category analytics: {e}", exc_info=True)
        await callback.message.edit_text(
            text=f"❌ Failed to generate chart: {str(e)}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton("◀️ Back", callback_data="analytics")]
            ])
        )


@router.callback_query(F.data == "analytics_income_expenses")
async def show_income_expenses_analytics(
    callback: CallbackQuery,
    transaction_repo: TransactionRepository,
    state: FSMContext
):
    """Show income vs expenses chart"""
    await callback.answer("Generating chart...")
    
    data = await state.get_data()
    user_id = data.get("user_id")
    
    if not user_id:
        await callback.answer("❌ User not found", show_alert=True)
        return
    
    try:
        # Get transactions from last 30 days
        start_date = datetime.utcnow() - timedelta(days=30)
        transactions = transaction_repo.get_user_transactions(user_id)
        
        # Filter by date
        recent_transactions = [
            tx for tx in transactions 
            if tx.date >= start_date
        ]
        
        # Generate chart
        chart_buf = generate_income_vs_expenses_chart(recent_transactions)
        
        # Save to temp file
        chart_path = f"/tmp/income_expenses_{user_id}.png"
        with open(chart_path, 'wb') as f:
            f.write(chart_buf.getvalue())
        
        # Send as photo
        await callback.message.delete()
        await callback.message.answer_photo(
            photo=FSInputFile(chart_path),
            caption="💰 **Income vs Expenses**\n\nLast 30 days",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton("◀️ Back to Analytics", callback_data="analytics")]
            ])
        )
        
        logger.info(f"Income/Expenses analytics generated for user {user_id}")
        
    except Exception as e:
        logger.error(f"Failed to generate income/expenses analytics: {e}", exc_info=True)
        await callback.message.edit_text(
            text=f"❌ Failed to generate chart: {str(e)}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton("◀️ Back", callback_data="analytics")]
            ])
        )


@router.callback_query(F.data == "analytics_top")
async def show_top_expenses(
    callback: CallbackQuery,
    transaction_repo: TransactionRepository,
    category_repo: CategoryRepository,
    state: FSMContext
):
    """Show top expenses list"""
    data = await state.get_data()
    user_id = data.get("user_id")
    
    if not user_id:
        await callback.answer("❌ User not found", show_alert=True)
        return
    
    try:
        # Get transactions from last 30 days
        start_date = datetime.utcnow() - timedelta(days=30)
        transactions = transaction_repo.get_user_transactions(user_id)
        
        # Filter expenses only
        expenses = [
            tx for tx in transactions 
            if tx.type == TransactionType.EXPENSE and tx.date >= start_date
        ]
        
        # Sort by amount
        expenses.sort(key=lambda x: x.amount, reverse=True)
        
        # Get categories
        categories = category_repo.get_user_categories(user_id)
        categories_dict = {cat.id: cat for cat in categories}
        
        # Build text
        if not expenses:
            text = "📈 **Top Expenses**\n\nNo expenses in the last 30 days."
        else:
            text = "📈 **Top Expenses (Last 30 Days)**\n\n"
            for i, tx in enumerate(expenses[:10], 1):
                category = categories_dict.get(tx.category_id)
                cat_name = f"{category.icon} {category.name}" if category else "Unknown"
                date_str = tx.date.strftime("%m/%d")
                text += f"{i}. **${tx.amount:.2f}** - {cat_name}\n"
                text += f"   {date_str}"
                if tx.note:
                    text += f" | {tx.note}"
                text += "\n\n"
        
        await callback.message.edit_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton("◀️ Back to Analytics", callback_data="analytics")]
            ])
        )
        
    except Exception as e:
        logger.error(f"Failed to show top expenses: {e}", exc_info=True)
        await callback.answer("❌ Error loading top expenses", show_alert=True)
    
    await callback.answer()
