"""
Input Validation Layer using Pydantic v2
Validates all user inputs to prevent injection attacks and ensure data integrity
"""
from typing import Optional
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, field_validator, Field, ConfigDict
from src.infrastructure.error_handling.exceptions import ValidationError


class TransactionInput(BaseModel):
    """Validation model for transaction creation."""
    
    model_config = ConfigDict(
        json_encoders={
            Decimal: str,
            datetime: lambda v: v.isoformat()
        }
    )
    
    amount: Decimal = Field(..., gt=0, description="Transaction amount must be positive")
    description: str = Field(..., min_length=1, max_length=500)
    category_id: Optional[int] = Field(None, ge=1)
    account_id: int = Field(..., ge=1)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    transaction_date: Optional[datetime] = None
    
    @field_validator('description')
    @classmethod
    def description_must_not_be_empty(cls, v):
        v = v.strip()
        if not v:
            raise ValidationError("Description cannot be empty")
        
        dangerous_chars = ['<', '>', ';', '&', '|', '$', '`']
        if any(char in v for char in dangerous_chars):
            raise ValidationError("Description contains invalid characters")
        
        return v
    
    @field_validator('currency')
    @classmethod
    def currency_must_be_valid(cls, v):
        valid_currencies = ['USD', 'EUR', 'USDT', 'USDC', 'RUB']
        v = v.upper()
        if v not in valid_currencies:
            raise ValidationError(f"Invalid currency. Must be one of: {', '.join(valid_currencies)}")
        return v
    
    @field_validator('amount')
    @classmethod
    def amount_must_be_reasonable(cls, v):
        if v > Decimal('1000000'):
            raise ValidationError("Amount exceeds maximum allowed value")
        if v < Decimal('0.01'):
            raise ValidationError("Amount is too small")
        return v


class AccountInput(BaseModel):
    """Validation model for account creation."""
    
    name: str = Field(..., min_length=1, max_length=100)
    account_type: str = Field(..., min_length=1, max_length=50)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    initial_balance: Decimal = Field(default=Decimal('0'), ge=0)
    
    @field_validator('name')
    @classmethod
    def name_must_be_valid(cls, v):
        v = v.strip()
        if not v:
            raise ValidationError("Account name cannot be empty")
        
        if len(v) < 2:
            raise ValidationError("Account name too short")
        
        return v
    
    @field_validator('account_type')
    @classmethod
    def account_type_must_be_valid(cls, v):
        valid_types = ['trustee_usdt', 'trustee_usdc', 'trustee_eur', 'bank', 'cash', 'crypto']
        v = v.lower()
        if v not in valid_types:
            raise ValidationError(f"Invalid account type. Must be one of: {', '.join(valid_types)}")
        return v


class CategoryInput(BaseModel):
    """Validation model for category creation."""
    
    name: str = Field(..., min_length=1, max_length=100)
    category_type: str = Field(..., pattern='^(expense|income)$')
    icon: Optional[str] = Field(None, max_length=10)
    color: Optional[str] = Field(None, pattern='^#[0-9A-Fa-f]{6}$')
    
    @field_validator('name')
    @classmethod
    def name_must_be_valid(cls, v):
        v = v.strip()
        if not v:
            raise ValidationError("Category name cannot be empty")
        return v


class UserInput(BaseModel):
    """Validation model for user data."""
    
    telegram_id: int = Field(..., gt=0)
    username: Optional[str] = Field(None, max_length=100)
    language: str = Field(default="en", pattern='^(en|ru)$')
    timezone: str = Field(default="UTC", max_length=50)
    
    @field_validator('telegram_id')
    @classmethod
    def telegram_id_must_be_valid(cls, v):
        if v < 1:
            raise ValidationError("Invalid Telegram ID")
        if v > 9999999999:
            raise ValidationError("Telegram ID too large")
        return v
    
    @field_validator('username')
    @classmethod
    def username_must_be_valid(cls, v):
        if v is None:
            return v
        
        v = v.strip()
        if not v:
            return None
        
        if not v.replace('_', '').isalnum():
            raise ValidationError("Username can only contain letters, numbers, and underscores")
        
        return v


class BalanceSnapshotInput(BaseModel):
    """Validation model for balance snapshots."""
    
    account_id: int = Field(..., ge=1)
    balance: Decimal = Field(..., description="Account balance")
    currency: str = Field(default="USD", min_length=3, max_length=3)
    snapshot_time: Optional[datetime] = None
    
    @field_validator('balance')
    @classmethod
    def balance_can_be_negative(cls, v):
        if v < Decimal('-1000000'):
            raise ValidationError("Balance is unreasonably low")
        if v > Decimal('10000000'):
            raise ValidationError("Balance is unreasonably high")
        return v


def validate_input(model_class: type[BaseModel], data: dict) -> BaseModel:
    """
    Validate input data against a Pydantic model.
    
    Args:
        model_class: Pydantic model class to validate against
        data: Dictionary of input data
        
    Returns:
        Validated model instance
        
    Raises:
        ValidationError: If validation fails
    """
    try:
        return model_class(**data)
    except Exception as e:
        raise ValidationError(f"Input validation failed: {str(e)}")


def sanitize_string(value: str, max_length: int = 500) -> str:
    """
    Sanitize string input to prevent injection attacks.
    
    Args:
        value: String to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized string
    """
    if not isinstance(value, str):
        raise ValidationError("Value must be a string")
    
    value = value.strip()
    
    if len(value) > max_length:
        value = value[:max_length]
    
    dangerous_chars = ['<', '>', ';', '&', '|', '$', '`', '\x00']
    for char in dangerous_chars:
        value = value.replace(char, '')
    
    return value
