"""
AI Finance Analysis handler with DeepSeek integration.
"""
import os
import json
from datetime import datetime, timedelta
from decimal import Decimal
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from infrastructure.repositories.transaction_repository import TransactionRepository
from infrastructure.repositories.category_repository import CategoryRepository
from infrastructure.logging_config import get_logger
from app.services.deepseek_service import DeepSeekService

logger = get_logger(__name__)

# Initialize DeepSeek service
deepseek_service = DeepSeekService()

router = Router()


async def call_deepseek_api(prompt: str) -> str:
    """Call DeepSeek API for financial analysis"""
    import httpx
    
    api_key = os.getenv("Manus_DeepSeek_Key")
    if not api_key:
        return "❌ DeepSeek API key not configured"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a professional financial advisor. Provide clear, actionable insights about spending patterns, budgeting, and financial health. Use emojis for better readability."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.7,
                    "max_tokens": 1000
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"]
            else:
                logger.error(f"DeepSeek API error: {response.status_code} - {response.text}")
                return f"❌ API Error: {response.status_code}"
                
    except Exception as e:
        logger.error(f"Failed to call DeepSeek API: {e}")
        return f"❌ Error: {str(e)}"


def prepare_financial_data(transactions: list, categories: list) -> dict:
    """Prepare financial data for AI analysis"""
    # Calculate totals
    total_income = Decimal("0")
    total_expenses = Decimal("0")
    category_spending = {}
    
    for tx in transactions:
        if tx.type.value == "income":
            total_income += tx.amount
        else:
            total_expenses += tx.amount
            
            # Group by category
            if tx.category_id:
                category_name = next((c.name for c in categories if c.id == tx.category_id), "Uncategorized")
                if category_name not in category_spending:
                    category_spending[category_name] = Decimal("0")
                category_spending[category_name] += tx.amount
    
    # Sort categories by spending
    top_categories = sorted(
        category_spending.items(),
        key=lambda x: x[1],
        reverse=True
    )[:5]
    
    return {
        "total_income": float(total_income),
        "total_expenses": float(total_expenses),
        "net_balance": float(total_income - total_expenses),
        "transaction_count": len(transactions),
        "top_categories": [(name, float(amount)) for name, amount in top_categories],
        "avg_transaction": float(total_expenses / len(transactions)) if transactions else 0
    }


@router.callback_query(F.data == "ai_finance")
async def show_ai_finance_menu(callback: CallbackQuery):
    """Show AI Finance Analysis menu"""
    logger.info(f"AI Finance button clicked by user {callback.from_user.id}")
    
    try:
        await callback.message.edit_text(
            text="🤖 **AI Finance Analysis**\n\n"
            "Get AI-powered insights about your finances:\n\n"
            "• **Smart Insights** - Overall financial health\n"
            "• **Spending Patterns** - Where your money goes\n"
            "• **Budget Recommendations** - Personalized advice\n"
            "• **Savings Tips** - How to save more",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="💡 Smart Insights", callback_data="ai_insights"),
                    InlineKeyboardButton(text="📊 Spending Patterns", callback_data="ai_patterns")
                ],
                [
                    InlineKeyboardButton(text="💰 Budget Tips", callback_data="ai_budget"),
                    InlineKeyboardButton(text="🎯 Savings Goals", callback_data="ai_savings")
                ],
                [InlineKeyboardButton(text="◀️ Back", callback_data="main_menu")]
            ])
        )
        await callback.answer()
        logger.info("AI Finance menu displayed successfully")
    except Exception as e:
        logger.error(f"Error in show_ai_finance_menu: {e}", exc_info=True)
        await callback.answer("❌ Error loading AI Finance. Please try again.", show_alert=True)


@router.callback_query(F.data == "ai_insights")
async def show_ai_insights(
    callback: CallbackQuery,
    transaction_repo: TransactionRepository,
    category_repo: CategoryRepository,
    state: FSMContext
):
    """Generate AI-powered financial insights"""
    await callback.answer("🤖 Analyzing your finances...", show_alert=False)
    
    # Get user data
    data = await state.get_data()
    user_id = data.get("user_id")
    
    # Get last 30 days transactions
    transactions = transaction_repo.get_user_transactions(user_id, limit=1000)
    thirty_days_ago = datetime.now() - timedelta(days=30)
    recent_transactions = [tx for tx in transactions if tx.date >= thirty_days_ago]
    
    if not recent_transactions:
        await callback.message.edit_text(
            text="❌ No transactions found in the last 30 days.\n"
            "Add some transactions to get AI insights!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Back", callback_data="ai_finance")]
            ])
        )
        return
    
    # Get categories
    categories = category_repo.get_user_categories(user_id)
    
    # Prepare data
    financial_data = prepare_financial_data(recent_transactions, categories)
    
    # Build prompt
    prompt = f"""
Analyze this user's financial data for the last 30 days:

Total Income: ${financial_data['total_income']:.2f}
Total Expenses: ${financial_data['total_expenses']:.2f}
Net Balance: ${financial_data['net_balance']:.2f}
Number of Transactions: {financial_data['transaction_count']}
Average Transaction: ${financial_data['avg_transaction']:.2f}

Top 5 Spending Categories:
"""
    
    for i, (category, amount) in enumerate(financial_data['top_categories'], 1):
        prompt += f"{i}. {category}: ${amount:.2f}\n"
    
    prompt += """
Provide:
1. Overall financial health assessment (1-2 sentences)
2. Key observations about spending patterns (2-3 bullet points)
3. One actionable recommendation to improve finances

Keep it concise and use emojis for better readability.
"""
    
    # Call DeepSeek service with persistent chat
    analysis = deepseek_service.analyze_transactions(
        user_id=user_id,
        transactions=[{
            'type': tx.type.value,
            'amount': float(tx.amount),
            'category_id': tx.category_id,
            'date': tx.date
        } for tx in recent_transactions],
        period_days=30,
        categories={cat.id: cat.name for cat in categories}
    )
    
    # Format response
    response_text = "🤖 **AI Financial Insights**\n\n"
    response_text += f"📊 **Last 30 Days Summary:**\n"
    response_text += f"• Income: ${financial_data['total_income']:.2f}\n"
    response_text += f"• Expenses: ${financial_data['total_expenses']:.2f}\n"
    response_text += f"• Net: ${financial_data['net_balance']:.2f}\n\n"
    response_text += f"**AI Analysis:**\n\n{analysis}"
    
    await callback.message.edit_text(
        text=response_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Refresh Analysis", callback_data="ai_insights")],
            [InlineKeyboardButton(text="◀️ Back", callback_data="ai_finance")]
        ])
    )


@router.callback_query(F.data == "ai_patterns")
async def show_spending_patterns(
    callback: CallbackQuery,
    transaction_repo: TransactionRepository,
    category_repo: CategoryRepository,
    state: FSMContext
):
    """Analyze spending patterns with AI"""
    await callback.answer("🤖 Analyzing patterns...", show_alert=False)
    
    data = await state.get_data()
    user_id = data.get("user_id")
    
    transactions = transaction_repo.get_user_transactions(user_id, limit=1000)
    thirty_days_ago = datetime.now() - timedelta(days=30)
    recent_transactions = [tx for tx in transactions if tx.date >= thirty_days_ago]
    
    if not recent_transactions:
        await callback.message.edit_text(
            text="❌ No transactions to analyze",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Back", callback_data="ai_finance")]
            ])
        )
        return
    
    categories = category_repo.get_user_categories(user_id)
    financial_data = prepare_financial_data(recent_transactions, categories)
    
    prompt = f"""
Analyze spending patterns for this user (last 30 days):

Top Spending Categories:
"""
    for i, (category, amount) in enumerate(financial_data['top_categories'], 1):
        percentage = (amount / financial_data['total_expenses'] * 100) if financial_data['total_expenses'] > 0 else 0
        prompt += f"{i}. {category}: ${amount:.2f} ({percentage:.1f}%)\n"
    
    prompt += f"""
Total Transactions: {financial_data['transaction_count']}
Average per Transaction: ${financial_data['avg_transaction']:.2f}

Identify:
1. Main spending patterns (what dominates spending?)
2. Potential areas of overspending
3. Recommendations to optimize spending

Be specific and actionable. Use emojis.
"""
    
    analysis = await call_deepseek_api(prompt)
    
    response_text = "📊 **Spending Patterns Analysis**\n\n"
    response_text += f"**Your Top Categories:**\n"
    for i, (category, amount) in enumerate(financial_data['top_categories'], 1):
        percentage = (amount / financial_data['total_expenses'] * 100) if financial_data['total_expenses'] > 0 else 0
        response_text += f"{i}. {category}: ${amount:.2f} ({percentage:.1f}%)\n"
    response_text += f"\n**AI Analysis:**\n\n{analysis}"
    
    await callback.message.edit_text(
        text=response_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Refresh", callback_data="ai_patterns")],
            [InlineKeyboardButton(text="◀️ Back", callback_data="ai_finance")]
        ])
    )


@router.callback_query(F.data == "ai_budget")
async def show_budget_recommendations(
    callback: CallbackQuery,
    transaction_repo: TransactionRepository,
    state: FSMContext
):
    """Get AI budget recommendations"""
    await callback.answer("🤖 Generating budget tips...", show_alert=False)
    
    data = await state.get_data()
    user_id = data.get("user_id")
    
    transactions = transaction_repo.get_user_transactions(user_id, limit=1000)
    thirty_days_ago = datetime.now() - timedelta(days=30)
    recent_transactions = [tx for tx in transactions if tx.date >= thirty_days_ago]
    
    if not recent_transactions:
        await callback.message.edit_text(
            text="❌ No data for budget recommendations",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Back", callback_data="ai_finance")]
            ])
        )
        return
    
    # Calculate income/expenses
    total_income = sum(tx.amount for tx in recent_transactions if tx.type.value == "income")
    total_expenses = sum(tx.amount for tx in recent_transactions if tx.type.value == "expense")
    
    prompt = f"""
Create a personalized budget plan for this user:

Monthly Income: ${float(total_income):.2f}
Monthly Expenses: ${float(total_expenses):.2f}
Savings Rate: {((total_income - total_expenses) / total_income * 100) if total_income > 0 else 0:.1f}%

Provide:
1. Budget allocation recommendations (50/30/20 rule or custom)
2. Specific spending limits for top categories
3. Savings goals (realistic monthly target)

Be practical and encouraging. Use emojis.
"""
    
    analysis = await call_deepseek_api(prompt)
    
    response_text = "💰 **Budget Recommendations**\n\n"
    response_text += f"📊 **Current Status:**\n"
    response_text += f"• Income: ${float(total_income):.2f}/month\n"
    response_text += f"• Expenses: ${float(total_expenses):.2f}/month\n"
    response_text += f"• Savings: ${float(total_income - total_expenses):.2f}/month\n\n"
    response_text += f"**AI Recommendations:**\n\n{analysis}"
    
    await callback.message.edit_text(
        text=response_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Refresh", callback_data="ai_budget")],
            [InlineKeyboardButton(text="◀️ Back", callback_data="ai_finance")]
        ])
    )


@router.callback_query(F.data == "ai_savings")
async def show_savings_tips(callback: CallbackQuery):
    """Get AI savings tips"""
    await callback.answer("🤖 Generating savings tips...", show_alert=False)
    
    prompt = """
Provide 5 practical savings tips for someone tracking their finances:

1. Short-term tips (immediate actions)
2. Medium-term strategies (1-3 months)
3. Long-term habits (lifestyle changes)

Be specific, actionable, and motivating. Use emojis.
"""
    
    analysis = await call_deepseek_api(prompt)
    
    response_text = "🎯 **Savings Tips**\n\n"
    response_text += f"{analysis}\n\n"
    response_text += "💡 **Pro Tip:** Review your spending weekly to stay on track!"
    
    await callback.message.edit_text(
        text=response_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Get More Tips", callback_data="ai_savings")],
            [InlineKeyboardButton(text="◀️ Back", callback_data="ai_finance")]
        ])
    )
