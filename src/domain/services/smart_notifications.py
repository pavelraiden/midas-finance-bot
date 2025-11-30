"""
Smart Notifications System
Sends intelligent notifications about unusual spending, budget alerts, and insights
"""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from decimal import Decimal
from src.domain.entities.transaction import Transaction
from src.infrastructure.logging.audit_logger import AuditLogger


class SmartNotificationService:
    """
    Analyzes spending patterns and sends smart notifications.
    """
    
    def __init__(self):
        self.audit_logger = AuditLogger()
    
    async def check_unusual_spending(
        self,
        user_id: int,
        transaction: Transaction,
        historical_transactions: List[Transaction]
    ) -> Optional[Dict]:
        """
        Check if a transaction is unusually large compared to history.
        
        Args:
            user_id: User ID
            transaction: Current transaction
            historical_transactions: Historical transactions for comparison
            
        Returns:
            Notification dict if unusual, None otherwise
        """
        if not historical_transactions:
            return None
        
        same_category = [
            t for t in historical_transactions
            if t.category_id == transaction.category_id
        ]
        
        if not same_category:
            return None
        
        avg_amount = sum(t.amount for t in same_category) / len(same_category)
        
        if transaction.amount > avg_amount * Decimal('2.5'):
            return {
                "type": "unusual_spending",
                "severity": "warning",
                "title": "⚠️ Unusual Spending Detected",
                "message": (
                    f"Your transaction of {transaction.amount} {transaction.currency} "
                    f"is {float(transaction.amount / avg_amount):.1f}x higher than your "
                    f"average for this category ({avg_amount:.2f} {transaction.currency})."
                ),
                "transaction_id": transaction.id,
                "category": transaction.category_name
            }
        
        return None
    
    async def check_budget_alerts(
        self,
        user_id: int,
        category_id: int,
        spent_this_month: Decimal,
        budget_limit: Decimal
    ) -> Optional[Dict]:
        """
        Check if spending is approaching or exceeding budget.
        
        Args:
            user_id: User ID
            category_id: Category ID
            spent_this_month: Amount spent this month
            budget_limit: Budget limit for the category
            
        Returns:
            Notification dict if alert needed, None otherwise
        """
        if spent_this_month <= 0 or budget_limit <= 0:
            return None
        
        percentage = float(spent_this_month / budget_limit * 100)
        
        if percentage >= 100:
            return {
                "type": "budget_exceeded",
                "severity": "critical",
                "title": "🚨 Budget Exceeded!",
                "message": (
                    f"You've exceeded your budget by "
                    f"{spent_this_month - budget_limit:.2f}! "
                    f"Spent: {spent_this_month:.2f} / {budget_limit:.2f}"
                ),
                "category_id": category_id,
                "percentage": percentage
            }
        elif percentage >= 90:
            return {
                "type": "budget_warning",
                "severity": "warning",
                "title": "⚠️ Budget Alert",
                "message": (
                    f"You've used {percentage:.0f}% of your budget. "
                    f"Spent: {spent_this_month:.2f} / {budget_limit:.2f}"
                ),
                "category_id": category_id,
                "percentage": percentage
            }
        elif percentage >= 75:
            return {
                "type": "budget_info",
                "severity": "info",
                "title": "ℹ️ Budget Update",
                "message": (
                    f"You've used {percentage:.0f}% of your budget. "
                    f"Remaining: {budget_limit - spent_this_month:.2f}"
                ),
                "category_id": category_id,
                "percentage": percentage
            }
        
        return None
    
    async def check_recurring_patterns(
        self,
        user_id: int,
        transactions: List[Transaction]
    ) -> List[Dict]:
        """
        Detect recurring payment patterns.
        
        Args:
            user_id: User ID
            transactions: List of transactions to analyze
            
        Returns:
            List of detected patterns
        """
        patterns = []
        
        grouped_by_description = {}
        for tx in transactions:
            desc_lower = tx.description.lower()
            if desc_lower not in grouped_by_description:
                grouped_by_description[desc_lower] = []
            grouped_by_description[desc_lower].append(tx)
        
        for description, txs in grouped_by_description.items():
            if len(txs) >= 3:
                amounts = [t.amount for t in txs]
                avg_amount = sum(amounts) / len(amounts)
                
                amount_variance = sum(abs(a - avg_amount) for a in amounts) / len(amounts)
                
                if amount_variance < avg_amount * Decimal('0.1'):
                    dates = [t.created_at for t in txs if t.created_at]
                    if len(dates) >= 2:
                        intervals = [
                            (dates[i+1] - dates[i]).days
                            for i in range(len(dates) - 1)
                        ]
                        avg_interval = sum(intervals) / len(intervals)
                        
                        if 25 <= avg_interval <= 35:
                            patterns.append({
                                "type": "recurring_monthly",
                                "description": description,
                                "average_amount": float(avg_amount),
                                "frequency": "monthly",
                                "occurrences": len(txs)
                            })
        
        return patterns
    
    async def generate_spending_insights(
        self,
        user_id: int,
        transactions: List[Transaction],
        period_days: int = 30
    ) -> Dict:
        """
        Generate spending insights for a user.
        
        Args:
            user_id: User ID
            transactions: List of transactions
            period_days: Period in days to analyze
            
        Returns:
            Dict with insights
        """
        if not transactions:
            return {
                "total_spent": 0,
                "total_income": 0,
                "net_change": 0,
                "top_categories": [],
                "insights": []
            }
        
        cutoff_date = datetime.now() - timedelta(days=period_days)
        recent_txs = [
            t for t in transactions
            if t.created_at and t.created_at >= cutoff_date
        ]
        
        total_spent = sum(
            t.amount for t in recent_txs
            if t.transaction_type == "expense"
        )
        
        total_income = sum(
            t.amount for t in recent_txs
            if t.transaction_type == "income"
        )
        
        category_spending = {}
        for tx in recent_txs:
            if tx.transaction_type == "expense":
                if tx.category_name not in category_spending:
                    category_spending[tx.category_name] = Decimal('0')
                category_spending[tx.category_name] += tx.amount
        
        top_categories = sorted(
            category_spending.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        insights = []
        
        if total_spent > total_income:
            insights.append({
                "type": "warning",
                "message": f"You spent {float(total_spent - total_income):.2f} more than you earned this period."
            })
        elif total_income > total_spent:
            insights.append({
                "type": "positive",
                "message": f"Great job! You saved {float(total_income - total_spent):.2f} this period."
            })
        
        if top_categories:
            top_cat_name, top_cat_amount = top_categories[0]
            percentage = float(top_cat_amount / total_spent * 100) if total_spent > 0 else 0
            insights.append({
                "type": "info",
                "message": f"Your biggest expense category is {top_cat_name} ({percentage:.0f}% of total spending)."
            })
        
        return {
            "total_spent": float(total_spent),
            "total_income": float(total_income),
            "net_change": float(total_income - total_spent),
            "top_categories": [
                {"category": cat, "amount": float(amt)}
                for cat, amt in top_categories
            ],
            "insights": insights
        }
