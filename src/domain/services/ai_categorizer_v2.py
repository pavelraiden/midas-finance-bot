"""
Enhanced AI Categorization Service with DeepSeek/Claude Integration
"""
import os
import json
from typing import Dict, Optional, List
from datetime import datetime
from anthropic import Anthropic
from src.domain.entities.transaction import Transaction
from src.infrastructure.logging.audit_logger import AuditLogger


class AICategorizer:
    """
    AI-powered transaction categorization with context-aware suggestions
    and self-learning capabilities.
    """
    
    CATEGORIES = {
        "food_dining": "Food & Dining",
        "transportation": "Transportation",
        "shopping": "Shopping",
        "entertainment": "Entertainment",
        "bills_utilities": "Bills & Utilities",
        "healthcare": "Healthcare",
        "income": "Income",
        "transfer": "Transfer",
        "savings": "Savings & Investments",
        "other": "Other"
    }
    
    DEEPSEEK_PROMPT_TEMPLATE = """You are an expert financial transaction categorization AI assistant.

Your task is to analyze transaction descriptions and categorize them accurately based on context, patterns, and financial domain knowledge.

**Available Categories:**
{categories}

**Transaction Details:**
- Description: {description}
- Amount: {amount} {currency}
- Date: {date}
- Account Type: {account_type}

**Historical Context:**
{context}

**Instructions:**
1. Analyze the transaction description carefully
2. Consider the amount and date context
3. Use historical patterns if available
4. Provide a category from the list above (exact match required)
5. Assign a confidence score (0-100)
6. Explain your reasoning briefly

**Output Format (JSON):**
{{
  "category": "exact_category_key",
  "category_name": "Human Readable Name",
  "confidence": 85,
  "reasoning": "Brief explanation of why this category was chosen",
  "alternative_category": "second_best_option",
  "tags": ["tag1", "tag2"]
}}

**Special Cases:**
- USDT→USDC swaps: "transfer"
- Card payments in EUR from USDC: "shopping" or specific category
- Salary deposits: "income"
- ATM withdrawals: "transfer"
- Recurring bills: "bills_utilities"

Analyze and respond:"""

    def __init__(self):
        self.client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        self.audit_logger = AuditLogger()
        self.cache = {}
    
    async def categorize(
        self,
        transaction: Transaction,
        context: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Categorize a transaction using AI with context awareness.
        
        Args:
            transaction: Transaction to categorize
            context: Historical transactions for context
            
        Returns:
            Dict with category, confidence, reasoning, and tags
        """
        cache_key = self._get_cache_key(transaction)
        if cache_key in self.cache:
            self.audit_logger.log_action(
                "ai_categorization",
                "cache_hit",
                {"transaction_id": transaction.id}
            )
            return self.cache[cache_key]
        
        context_str = self._format_context(context) if context else "No historical context available"
        
        categories_str = "\n".join([
            f"- {key}: {name}"
            for key, name in self.CATEGORIES.items()
        ])
        
        prompt = self.DEEPSEEK_PROMPT_TEMPLATE.format(
            categories=categories_str,
            description=transaction.description,
            amount=transaction.amount,
            currency=transaction.currency or "USD",
            date=transaction.created_at.strftime("%Y-%m-%d %H:%M") if transaction.created_at else "Unknown",
            account_type=transaction.account_type or "Unknown",
            context=context_str
        )
        
        try:
            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1024,
                temperature=0.2,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = message.content[0].text
            result = self._parse_response(response_text)
            
            self.cache[cache_key] = result
            
            self.audit_logger.log_action(
                "ai_categorization",
                "success",
                {
                    "transaction_id": transaction.id,
                    "category": result["category"],
                    "confidence": result["confidence"]
                }
            )
            
            return result
            
        except Exception as e:
            self.audit_logger.log_action(
                "ai_categorization",
                "error",
                {
                    "transaction_id": transaction.id,
                    "error": str(e)
                }
            )
            return self._fallback_categorization(transaction)
    
    def _get_cache_key(self, transaction: Transaction) -> str:
        """Generate cache key for semantic caching."""
        return f"{transaction.description.lower()}_{transaction.amount}"
    
    def _format_context(self, context: List[Dict]) -> str:
        """Format historical context for the prompt."""
        if not context:
            return "No previous transactions"
        
        context_lines = []
        for i, tx in enumerate(context[:5], 1):
            context_lines.append(
                f"{i}. {tx.get('description', 'N/A')} - "
                f"{tx.get('amount', 0)} {tx.get('currency', 'USD')} - "
                f"Category: {tx.get('category', 'Unknown')}"
            )
        
        return "\n".join(context_lines)
    
    def _parse_response(self, response_text: str) -> Dict:
        """Parse AI response and extract structured data."""
        try:
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                result = json.loads(json_str)
                
                if "category" not in result:
                    raise ValueError("Missing category in response")
                
                return {
                    "category": result.get("category", "other"),
                    "category_name": result.get("category_name", "Other"),
                    "confidence": result.get("confidence", 50),
                    "reasoning": result.get("reasoning", "AI analysis"),
                    "alternative_category": result.get("alternative_category"),
                    "tags": result.get("tags", [])
                }
            else:
                raise ValueError("No JSON found in response")
                
        except Exception as e:
            self.audit_logger.log_action(
                "ai_categorization",
                "parse_error",
                {"error": str(e), "response": response_text[:200]}
            )
            return {
                "category": "other",
                "category_name": "Other",
                "confidence": 30,
                "reasoning": "Failed to parse AI response",
                "alternative_category": None,
                "tags": []
            }
    
    def _fallback_categorization(self, transaction: Transaction) -> Dict:
        """Fallback rule-based categorization when AI fails."""
        description_lower = transaction.description.lower()
        
        rules = {
            "food_dining": ["restaurant", "cafe", "food", "pizza", "burger"],
            "transportation": ["uber", "taxi", "gas", "fuel", "parking"],
            "shopping": ["amazon", "shop", "store", "mall"],
            "entertainment": ["netflix", "spotify", "cinema", "movie"],
            "bills_utilities": ["electric", "water", "internet", "phone"],
            "healthcare": ["pharmacy", "doctor", "hospital", "medical"],
            "income": ["salary", "wage", "payment received"],
            "transfer": ["transfer", "usdt", "usdc", "swap"]
        }
        
        for category, keywords in rules.items():
            if any(keyword in description_lower for keyword in keywords):
                return {
                    "category": category,
                    "category_name": self.CATEGORIES[category],
                    "confidence": 60,
                    "reasoning": "Rule-based fallback categorization",
                    "alternative_category": None,
                    "tags": ["fallback"]
                }
        
        return {
            "category": "other",
            "category_name": "Other",
            "confidence": 40,
            "reasoning": "No matching rules found",
            "alternative_category": None,
            "tags": ["fallback", "uncategorized"]
        }
    
    async def learn_from_feedback(
        self,
        transaction_id: int,
        correct_category: str,
        ai_category: str,
        confidence: float
    ):
        """
        Learn from user corrections to improve future categorizations.
        
        Args:
            transaction_id: ID of the transaction
            correct_category: User-corrected category
            ai_category: AI-predicted category
            confidence: Original confidence score
        """
        self.audit_logger.log_action(
            "ai_learning",
            "feedback_received",
            {
                "transaction_id": transaction_id,
                "correct_category": correct_category,
                "ai_category": ai_category,
                "confidence": confidence,
                "was_correct": correct_category == ai_category
            }
        )
