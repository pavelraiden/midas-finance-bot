"""
Prompt Library for AI Services
Centralized storage for high-quality, task-specific prompts
Based on AI Council recommendations (Claude 3.7)
"""
import json
from typing import Dict, Any, List
from infrastructure.logging_config import get_logger

logger = get_logger(__name__)


class PromptLibrary:
    """
    Centralized library for AI prompts.
    
    Features:
    - Task-specific prompts with placeholders
    - Context-aware prompt generation
    - JSON output formatting
    - Token-efficient templates
    """
    
    # ========== CATEGORIZATION PROMPT ==========
    # Based on AI Council Report (Claude 3.7)
    CATEGORIZATION_PROMPT = """# INSTRUCTION: Categorize the transaction based on the provided context.

# CONTEXT:
- User ID: {user_id}
- User Categories: {user_categories}
- Recent Transactions (last 7 days):
{recent_transactions}
- Known Merchant Mappings:
{merchant_mappings}

# TRANSACTION TO CATEGORIZE:
- Description: {description}
- Merchant: {merchant}
- Amount: {amount} {currency}

# OUTPUT FORMAT (JSON only):
{{
  "category": "<one of user categories>",
  "confidence": <float 0.0-1.0>,
  "reasoning": "<brief explanation>",
  "new_merchant_mapping": {{
    "merchant_name": "<normalized merchant name>",
    "suggested_category": "<suggested category>"
  }} // (optional - only if this is a new merchant)
}}

# RULES:
1. ONLY use categories from the user's category list
2. Confidence should be 0.0-1.0 (0.95+ for high confidence)
3. If merchant is in known mappings, use that category with high confidence
4. If similar merchant exists, use that category with medium confidence (0.7-0.85)
5. For new merchants, suggest a merchant mapping
6. Return ONLY valid JSON, no other text
"""
    
    # ========== ANALYZE SPENDING PROMPT ==========
    ANALYZE_SPENDING_PROMPT = """# INSTRUCTION: Analyze the user's spending patterns for the last 30 days.

# CONTEXT:
- User ID: {user_id}
- Total Spending: {total_spending} {currency}
- Spending by Category:
{spending_by_category}
- Spending by Day of Week:
{spending_by_day}
- Number of Transactions: {transaction_count}

# OUTPUT FORMAT (Markdown):
## 📊 Spending Analysis

**Top Categories**:
- [List top 3 categories with amounts and percentages]

**Spending Habits**:
- [Identify patterns: weekday vs weekend, specific days, etc.]

**Unusual Activity**:
- [Highlight any unusual spending patterns or spikes]

**Savings Opportunities**:
- [Suggest 2-3 concrete ways to reduce spending]

**Budget Recommendations**:
- [Suggest monthly budgets for top categories]

# RULES:
1. Be specific and actionable
2. Use actual numbers from the data
3. Keep it concise (max 200 words)
4. Focus on insights, not just data repetition
"""
    
    # ========== BUDGET RECOMMENDATION PROMPT ==========
    BUDGET_RECOMMENDATION_PROMPT = """# INSTRUCTION: Generate personalized budget recommendations.

# CONTEXT:
- User ID: {user_id}
- Monthly Income: {monthly_income} {currency} (if available)
- Average Monthly Spending: {avg_monthly_spending} {currency}
- Spending by Category (last 3 months):
{spending_by_category}
- Financial Goals: {financial_goals}

# OUTPUT FORMAT (JSON):
{{
  "recommended_budgets": {{
    "<category_name>": {{
      "current_avg": <float>,
      "recommended": <float>,
      "reasoning": "<why this amount>",
      "savings_potential": <float>
    }}
  }},
  "total_recommended_budget": <float>,
  "total_savings_potential": <float>,
  "priority_actions": [
    "<action 1>",
    "<action 2>",
    "<action 3>"
  ]
}}

# RULES:
1. Use 50/30/20 rule as baseline (50% needs, 30% wants, 20% savings)
2. Adjust based on user's actual spending patterns
3. Be realistic - don't suggest drastic cuts
4. Prioritize high-impact, easy-to-implement changes
5. Return ONLY valid JSON
"""
    
    # ========== FIND ANOMALIES PROMPT ==========
    FIND_ANOMALIES_PROMPT = """# INSTRUCTION: Detect unusual or suspicious transactions.

# CONTEXT:
- User ID: {user_id}
- Recent Transactions (last 30 days):
{recent_transactions}
- User's Typical Spending Patterns:
{typical_patterns}

# OUTPUT FORMAT (JSON):
{{
  "anomalies": [
    {{
      "transaction_id": "<id>",
      "type": "<duplicate|unusually_large|unusual_merchant|unusual_time>",
      "severity": "<low|medium|high>",
      "description": "<what's unusual>",
      "recommendation": "<what user should do>"
    }}
  ],
  "summary": "<overall assessment>"
}}

# RULES:
1. Only flag genuinely unusual transactions
2. Consider user's spending history
3. Severity: high = likely fraud, medium = worth checking, low = FYI
4. Return ONLY valid JSON
"""
    
    def get_categorization_prompt(self, context: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Generate categorization prompt with user context.
        
        Args:
            context: Dict with keys:
                - user_id: str
                - user_categories: List[str]
                - recent_transactions: List[Dict]
                - merchant_mappings: List[Dict]
                - description: str
                - merchant: str
                - amount: float
                - currency: str
        
        Returns:
            List of message dicts for DeepSeek API
        """
        # Format user categories
        categories_str = ", ".join(context.get("user_categories", ["Other"]))
        
        # Format recent transactions
        recent_txs = context.get("recent_transactions", [])
        if recent_txs:
            txs_str = "\n".join([
                f"  - {tx.get('date')}: {tx.get('merchant')} - {tx.get('amount')} ({tx.get('category')})"
                for tx in recent_txs[:10]  # Limit to 10 most recent
            ])
        else:
            txs_str = "  (No recent transactions)"
        
        # Format merchant mappings
        mappings = context.get("merchant_mappings", [])
        if mappings:
            mappings_str = "\n".join([
                f"  - {m.get('merchant_name')} → {m.get('category')}"
                for m in mappings[:20]  # Limit to 20 most common
            ])
        else:
            mappings_str = "  (No known merchant mappings)"
        
        # Fill in the template
        prompt = self.CATEGORIZATION_PROMPT.format(
            user_id=context.get("user_id", "unknown"),
            user_categories=categories_str,
            recent_transactions=txs_str,
            merchant_mappings=mappings_str,
            description=context.get("description", ""),
            merchant=context.get("merchant", "Unknown"),
            amount=context.get("amount", 0.0),
            currency=context.get("currency", "USD")
        )
        
        logger.debug(f"Generated categorization prompt ({len(prompt)} chars)")
        
        return [{"role": "user", "content": prompt}]
    
    def get_analyze_spending_prompt(self, context: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Generate spending analysis prompt with user context.
        
        Args:
            context: Dict with keys:
                - user_id: str
                - total_spending: float
                - spending_by_category: Dict[str, float]
                - spending_by_day: Dict[str, float]
                - transaction_count: int
                - currency: str
        
        Returns:
            List of message dicts for DeepSeek API
        """
        # Format spending by category
        spending_cat = context.get("spending_by_category", {})
        if spending_cat:
            cat_str = "\n".join([
                f"  - {cat}: {amount:.2f} {context.get('currency', 'USD')}"
                for cat, amount in sorted(spending_cat.items(), key=lambda x: x[1], reverse=True)
            ])
        else:
            cat_str = "  (No data)"
        
        # Format spending by day
        spending_day = context.get("spending_by_day", {})
        if spending_day:
            day_str = "\n".join([
                f"  - {day}: {amount:.2f} {context.get('currency', 'USD')}"
                for day, amount in spending_day.items()
            ])
        else:
            day_str = "  (No data)"
        
        # Fill in the template
        prompt = self.ANALYZE_SPENDING_PROMPT.format(
            user_id=context.get("user_id", "unknown"),
            total_spending=context.get("total_spending", 0.0),
            currency=context.get("currency", "USD"),
            spending_by_category=cat_str,
            spending_by_day=day_str,
            transaction_count=context.get("transaction_count", 0)
        )
        
        logger.debug(f"Generated analyze spending prompt ({len(prompt)} chars)")
        
        return [{"role": "user", "content": prompt}]
    
    def get_budget_recommendation_prompt(self, context: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Generate budget recommendation prompt with user context.
        
        Args:
            context: Dict with keys:
                - user_id: str
                - monthly_income: float (optional)
                - avg_monthly_spending: float
                - spending_by_category: Dict[str, float]
                - financial_goals: str (optional)
                - currency: str
        
        Returns:
            List of message dicts for DeepSeek API
        """
        # Format spending by category
        spending_cat = context.get("spending_by_category", {})
        if spending_cat:
            cat_str = "\n".join([
                f"  - {cat}: {amount:.2f} {context.get('currency', 'USD')}/month"
                for cat, amount in sorted(spending_cat.items(), key=lambda x: x[1], reverse=True)
            ])
        else:
            cat_str = "  (No data)"
        
        # Fill in the template
        prompt = self.BUDGET_RECOMMENDATION_PROMPT.format(
            user_id=context.get("user_id", "unknown"),
            monthly_income=context.get("monthly_income", "Not provided"),
            avg_monthly_spending=context.get("avg_monthly_spending", 0.0),
            currency=context.get("currency", "USD"),
            spending_by_category=cat_str,
            financial_goals=context.get("financial_goals", "Not specified")
        )
        
        logger.debug(f"Generated budget recommendation prompt ({len(prompt)} chars)")
        
        return [{"role": "user", "content": prompt}]
    
    def get_find_anomalies_prompt(self, context: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Generate anomaly detection prompt with user context.
        
        Args:
            context: Dict with keys:
                - user_id: str
                - recent_transactions: List[Dict]
                - typical_patterns: Dict
        
        Returns:
            List of message dicts for DeepSeek API
        """
        # Format recent transactions
        recent_txs = context.get("recent_transactions", [])
        if recent_txs:
            txs_str = "\n".join([
                f"  - ID: {tx.get('id')}, Date: {tx.get('date')}, Merchant: {tx.get('merchant')}, Amount: {tx.get('amount')}"
                for tx in recent_txs
            ])
        else:
            txs_str = "  (No recent transactions)"
        
        # Format typical patterns
        patterns = context.get("typical_patterns", {})
        patterns_str = json.dumps(patterns, indent=2) if patterns else "  (No pattern data)"
        
        # Fill in the template
        prompt = self.FIND_ANOMALIES_PROMPT.format(
            user_id=context.get("user_id", "unknown"),
            recent_transactions=txs_str,
            typical_patterns=patterns_str
        )
        
        logger.debug(f"Generated anomaly detection prompt ({len(prompt)} chars)")
        
        return [{"role": "user", "content": prompt}]
