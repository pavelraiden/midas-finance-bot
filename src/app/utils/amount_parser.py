"""
Smart amount parser with flexible format support.
Handles: "1021 eur", "100 usd", "50.5", "1,000.50 USD", etc.
"""
import re
from decimal import Decimal, InvalidOperation
from typing import Tuple, Optional


def parse_amount_with_currency(
    amount_str: str,
    default_currency: str = "USD"
) -> Tuple[Decimal, str]:
    """
    Parse amount string with optional currency.
    
    Examples:
        - "1021 eur" -> (Decimal('1021'), "EUR")
        - "100 usd" -> (Decimal('100'), "USD")
        - "50.5" -> (Decimal('50.5'), "USD")
        - "1,000.50 USD" -> (Decimal('1000.50'), "USD")
        - "€50" -> (Decimal('50'), "EUR")
        - "$100.50" -> (Decimal('100.50'), "USD")
    
    Args:
        amount_str: Input string containing amount and optional currency
        default_currency: Default currency if not specified
    
    Returns:
        Tuple of (amount, currency)
    
    Raises:
        ValueError: If amount cannot be parsed
    """
    if not amount_str or not isinstance(amount_str, str):
        raise ValueError("Amount string is required")
    
    # Clean the input
    amount_str = amount_str.strip()
    
    # Currency symbols mapping
    currency_symbols = {
        '$': 'USD',
        '€': 'EUR',
        '£': 'GBP',
        '¥': 'JPY',
        '₽': 'RUB',
        '₴': 'UAH'
    }
    
    # Check for currency symbol
    detected_currency = None
    for symbol, code in currency_symbols.items():
        if symbol in amount_str:
            detected_currency = code
            amount_str = amount_str.replace(symbol, '')
            break
    
    # Ukrainian currency keywords
    ukrainian_currency_keywords = {
        'грн': 'UAH',
        'гривен': 'UAH',
        'гривень': 'UAH',
        'гривны': 'UAH',
        'гривні': 'UAH',
        'гривна': 'UAH',
        'uah': 'UAH'
    }
    
    # Check for Ukrainian currency keywords (case insensitive)
    amount_lower = amount_str.lower()
    for keyword, code in ukrainian_currency_keywords.items():
        if keyword in amount_lower:
            detected_currency = code
            # Remove the keyword from amount string
            amount_str = re.sub(keyword, '', amount_str, flags=re.IGNORECASE)
            break
    
    # Extract currency code if present (e.g., "EUR", "USD")
    if not detected_currency:
        currency_match = re.search(r'\b([A-Za-z]{3})\b', amount_str)
        if currency_match:
            detected_currency = currency_match.group(1).upper()
    
    currency = detected_currency or default_currency
    
    # Remove currency code and any non-numeric chars except . and ,
    amount_numeric = re.sub(r'[A-Za-z\s]', '', amount_str)
    
    # Handle commas and periods correctly
    if ',' in amount_numeric and '.' in amount_numeric:
        # Check which comes last to determine format
        last_comma = amount_numeric.rfind(',')
        last_period = amount_numeric.rfind('.')
        
        if last_comma > last_period:
            # European format: 1.234,56 (period = thousands, comma = decimal)
            amount_numeric = amount_numeric.replace('.', '').replace(',', '.')
        else:
            # US format: 1,234.56 (comma = thousands, period = decimal)
            amount_numeric = amount_numeric.replace(',', '')
    elif ',' in amount_numeric:
        # Check if comma is used as decimal separator (European format)
        # If there's only one comma and it's followed by 1-2 digits, it's decimal
        if amount_numeric.count(',') == 1:
            parts = amount_numeric.split(',')
            if len(parts) == 2 and len(parts[1]) <= 2:
                # Decimal separator
                amount_numeric = amount_numeric.replace(',', '.')
            else:
                # Thousands separator
                amount_numeric = amount_numeric.replace(',', '')
        else:
            # Multiple commas = thousands separators
            amount_numeric = amount_numeric.replace(',', '')
    
    # Remove any remaining non-numeric characters except decimal point
    amount_numeric = re.sub(r'[^\d.]', '', amount_numeric)
    
    if not amount_numeric:
        raise ValueError(f"Could not extract numeric value from '{amount_str}'")
    
    try:
        amount = Decimal(amount_numeric)
        if amount <= 0:
            raise ValueError("Amount must be positive")
        return amount, currency
    except (InvalidOperation, ValueError) as e:
        raise ValueError(f"Could not parse amount from '{amount_str}': {str(e)}")


def format_amount(amount: Decimal, currency: str) -> str:
    """
    Format amount with currency for display.
    
    Args:
        amount: Decimal amount
        currency: Currency code
    
    Returns:
        Formatted string (e.g., "100.50 USD")
    """
    return f"{amount:.2f} {currency}"


# Test cases
if __name__ == "__main__":
    test_cases = [
        "1021 eur",
        "100 usd",
        "50.5",
        "1,000.50 USD",
        "€50",
        "$100.50",
        "1000",
        "1,234.56",
        "1.234,56 EUR",  # European format
        "50 грн",
        "100.5 uah"
    ]
    
    print("Testing amount parser:")
    print("=" * 50)
    for test in test_cases:
        try:
            amount, currency = parse_amount_with_currency(test)
            print(f"✅ '{test}' -> {amount} {currency}")
        except ValueError as e:
            print(f"❌ '{test}' -> ERROR: {e}")
