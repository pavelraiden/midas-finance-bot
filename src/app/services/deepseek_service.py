"""
DeepSeek AI service for financial analysis with persistent chat.
"""
import os
import json
import requests
from typing import List, Dict, Optional
from datetime import datetime
from infrastructure.logging_config import get_logger

logger = get_logger(__name__)


class DeepSeekService:
    """Service for AI-powered financial analysis using DeepSeek"""
    
    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.base_url = "https://api.deepseek.com/v1"
        
        if not self.api_key:
            logger.warning("DEEPSEEK_API_KEY not set - AI features will not work")
        
        # Persistent chat history per user
        self.chat_histories = {}
    
    def _make_request(self, messages: List[Dict], model: str = "deepseek-chat") -> Optional[str]:
        """Make request to DeepSeek API"""
        if not self.api_key:
            logger.error("DeepSeek API key not configured")
            return None
        
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 4000
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"DeepSeek API request failed: {e}")
            return None
    
    def _get_chat_history(self, user_id: str) -> List[Dict]:
        """Get persistent chat history for user"""
        if user_id not in self.chat_histories:
            self.chat_histories[user_id] = []
        return self.chat_histories[user_id]
    
    def _add_to_history(self, user_id: str, role: str, content: str):
        """Add message to chat history"""
        history = self._get_chat_history(user_id)
        history.append({"role": role, "content": content})
        
        # Limit history to prevent token overflow (keep last 20 messages)
        if len(history) > 20:
            # Keep system message and last 19 messages
            system_msg = next((msg for msg in history if msg["role"] == "system"), None)
            history = history[-19:]
            if system_msg and history[0]["role"] != "system":
                history.insert(0, system_msg)
            self.chat_histories[user_id] = history
    
    def _get_system_prompt(self) -> str:
        """Get comprehensive system prompt for financial analysis"""
        return """You are an expert financial analyst AI assistant specializing in personal finance management. Your role is to:

1. **Analyze spending patterns** - Identify trends, anomalies, and patterns in transaction data
2. **Provide insights** - Offer actionable recommendations to improve financial health
3. **Categorize transactions** - Accurately categorize transactions based on merchant names and descriptions
4. **Detect transfers** - Identify transfers between user's own wallets vs actual expenses
5. **Budget recommendations** - Suggest realistic budgets based on historical data
6. **Forecast trends** - Predict future spending patterns based on past behavior
7. **Learn from feedback** - Remember user corrections and preferences for future analysis

**Key Capabilities:**
- Multi-currency support (USD, EUR, UAH, etc.)
- Crypto and fiat transaction analysis
- Period comparison (daily, weekly, monthly, yearly)
- Category-wise breakdown
- Merchant learning and recognition
- Anomaly detection (unusual spending)

**Analysis Quality Standards:**
- Be specific with numbers and percentages
- Provide actionable recommendations
- Highlight both positive trends and areas for improvement
- Use clear, friendly language
- Format reports with sections and bullet points
- Always cite specific data points

**Important Rules:**
- If uncertain about transaction categorization (< 95% confidence), ask the user
- Remember merchant mappings the user confirms
- Never make assumptions about personal financial goals
- Be encouraging and supportive, not judgmental
- Respect privacy - never store sensitive data externally

You maintain context across conversations to provide increasingly better analysis over time."""
    
    def initialize_user_chat(self, user_id: str):
        """Initialize chat history for new user"""
        if user_id not in self.chat_histories:
            self.chat_histories[user_id] = [
                {"role": "system", "content": self._get_system_prompt()}
            ]
            logger.info(f"Initialized chat history for user {user_id}")
    
    def analyze_transactions(
        self,
        user_id: str,
        transactions: List[Dict],
        period_days: int,
        categories: Dict[str, str] = None
    ) -> Optional[str]:
        """Analyze transactions and generate comprehensive report"""
        self.initialize_user_chat(user_id)
        
        # Prepare transaction data for analysis
        tx_summary = self._prepare_transaction_summary(transactions, categories)
        
        # Create analysis prompt
        prompt = f"""Please analyze the following financial data for the last {period_days} days:

**Transaction Summary:**
{tx_summary}

**Analysis Required:**
1. Overall spending patterns and trends
2. Top spending categories with percentages
3. Income vs Expenses comparison
4. Daily/Weekly average spending
5. Unusual or anomalous transactions (if any)
6. Budget recommendations for each category
7. Actionable insights to improve financial health
8. Comparison with previous period (if data available)

Please provide a detailed, well-structured report with specific numbers and actionable recommendations."""
        
        # Add to history and get response
        self._add_to_history(user_id, "user", prompt)
        
        # Get all messages for context
        messages = self._get_chat_history(user_id)
        
        # Make API request
        response = self._make_request(messages, model="deepseek-chat")
        
        if response:
            self._add_to_history(user_id, "assistant", response)
            logger.info(f"Generated financial analysis for user {user_id}")
        
        return response
    
    def _prepare_transaction_summary(
        self,
        transactions: List[Dict],
        categories: Dict[str, str] = None
    ) -> str:
        """Prepare transaction data summary for AI analysis"""
        if not transactions:
            return "No transactions in this period."
        
        # Group by category
        category_totals = {}
        income_total = 0
        expense_total = 0
        
        for tx in transactions:
            tx_type = tx.get("type", "expense")
            amount = float(tx.get("amount", 0))
            category_id = tx.get("category_id")
            category_name = categories.get(category_id, "Uncategorized") if categories else "Uncategorized"
            
            if tx_type == "income":
                income_total += amount
            elif tx_type == "expense":
                expense_total += amount
                
                if category_name not in category_totals:
                    category_totals[category_name] = 0
                category_totals[category_name] += amount
        
        # Build summary
        summary = f"""
Total Transactions: {len(transactions)}
Total Income: ${income_total:.2f}
Total Expenses: ${expense_total:.2f}
Net: ${income_total - expense_total:.2f}

Spending by Category:
"""
        
        for category, total in sorted(category_totals.items(), key=lambda x: x[1], reverse=True):
            percentage = (total / expense_total * 100) if expense_total > 0 else 0
            summary += f"- {category}: ${total:.2f} ({percentage:.1f}%)\n"
        
        return summary
    
    def categorize_transaction(
        self,
        user_id: str,
        merchant_name: str,
        amount: float,
        description: str = None
    ) -> Dict:
        """Use AI to categorize a transaction"""
        self.initialize_user_chat(user_id)
        
        prompt = f"""Categorize this transaction:

Merchant: {merchant_name}
Amount: ${amount:.2f}
Description: {description or 'N/A'}

Based on the merchant name and description, suggest:
1. Category (e.g., Food & Dining, Shopping, Transport, etc.)
2. Confidence level (0-100%)
3. Brief reasoning

Respond in JSON format:
{{
    "category": "category name",
    "confidence": 95,
    "reasoning": "brief explanation"
}}"""
        
        self._add_to_history(user_id, "user", prompt)
        messages = self._get_chat_history(user_id)
        
        response = self._make_request(messages, model="deepseek-chat")
        
        if response:
            self._add_to_history(user_id, "assistant", response)
            
            # Parse JSON response
            try:
                # Extract JSON from response (handle markdown code blocks)
                json_str = response
                if "```json" in response:
                    json_str = response.split("```json")[1].split("```")[0].strip()
                elif "```" in response:
                    json_str = response.split("```")[1].split("```")[0].strip()
                
                result = json.loads(json_str)
                return result
            except Exception as e:
                logger.error(f"Failed to parse AI categorization response: {e}")
                return {
                    "category": "Uncategorized",
                    "confidence": 0,
                    "reasoning": "Failed to parse AI response"
                }
        
        return {
            "category": "Uncategorized",
            "confidence": 0,
            "reasoning": "AI request failed"
        }
    
    def learn_merchant(self, user_id: str, merchant_name: str, category: str):
        """Teach AI about merchant-category mapping"""
        self.initialize_user_chat(user_id)
        
        prompt = f"""Learn this merchant mapping:
Merchant: {merchant_name}
Category: {category}

Remember this for future categorization of similar transactions."""
        
        self._add_to_history(user_id, "user", prompt)
        messages = self._get_chat_history(user_id)
        
        response = self._make_request(messages, model="deepseek-chat")
        
        if response:
            self._add_to_history(user_id, "assistant", response)
            logger.info(f"AI learned merchant mapping: {merchant_name} -> {category}")
    
    def clear_history(self, user_id: str):
        """Clear chat history for user (start fresh)"""
        if user_id in self.chat_histories:
            del self.chat_histories[user_id]
            logger.info(f"Cleared chat history for user {user_id}")
    
    def get_history_size(self, user_id: str) -> int:
        """Get number of messages in chat history"""
        return len(self._get_chat_history(user_id))
