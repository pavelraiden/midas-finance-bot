"""
Tests for Input Validator
"""
import pytest
from decimal import Decimal
from datetime import datetime
from pydantic import ValidationError as PydanticValidationError
from src.infrastructure.security.input_validator import (
    TransactionInput,
    AccountInput,
    CategoryInput,
    UserInput,
    BalanceSnapshotInput,
    validate_input,
    sanitize_string
)
from src.infrastructure.error_handling.exceptions import ValidationError


class TestTransactionInput:
    """Test TransactionInput validation."""
    
    def test_valid_transaction(self):
        """Test valid transaction input."""
        data = {
            "amount": "100.50",
            "description": "Test transaction",
            "account_id": 1,
            "currency": "USD"
        }
        result = TransactionInput(**data)
        assert result.amount == Decimal("100.50")
        assert result.description == "Test transaction"
        assert result.currency == "USD"
    
    def test_negative_amount_raises_error(self):
        """Test that negative amount raises error."""
        data = {
            "amount": "-50",
            "description": "Test",
            "account_id": 1
        }
        with pytest.raises(PydanticValidationError):
            TransactionInput(**data)
    
    def test_zero_amount_raises_error(self):
        """Test that zero amount raises error."""
        data = {
            "amount": "0",
            "description": "Test",
            "account_id": 1
        }
        with pytest.raises(PydanticValidationError):
            TransactionInput(**data)
    
    def test_empty_description_raises_error(self):
        """Test that empty description raises error."""
        data = {
            "amount": "100",
            "description": "   ",
            "account_id": 1
        }
        with pytest.raises(ValidationError):
            TransactionInput(**data)
    
    def test_dangerous_chars_in_description_raises_error(self):
        """Test that dangerous characters in description raise error."""
        data = {
            "amount": "100",
            "description": "Test <script>alert('xss')</script>",
            "account_id": 1
        }
        with pytest.raises(ValidationError):
            TransactionInput(**data)
    
    def test_invalid_currency_raises_error(self):
        """Test that invalid currency raises error."""
        data = {
            "amount": "100",
            "description": "Test",
            "account_id": 1,
            "currency": "XXX"
        }
        with pytest.raises(ValidationError):
            TransactionInput(**data)
    
    def test_amount_too_large_raises_error(self):
        """Test that amount exceeding maximum raises error."""
        data = {
            "amount": "10000000",
            "description": "Test",
            "account_id": 1
        }
        with pytest.raises(ValidationError):
            TransactionInput(**data)


class TestAccountInput:
    """Test AccountInput validation."""
    
    def test_valid_account(self):
        """Test valid account input."""
        data = {
            "name": "My Wallet",
            "account_type": "trustee_usdt",
            "currency": "USD"
        }
        result = AccountInput(**data)
        assert result.name == "My Wallet"
        assert result.account_type == "trustee_usdt"
    
    def test_short_name_raises_error(self):
        """Test that too short name raises error."""
        data = {
            "name": "A",
            "account_type": "bank"
        }
        with pytest.raises(ValidationError):
            AccountInput(**data)
    
    def test_invalid_account_type_raises_error(self):
        """Test that invalid account type raises error."""
        data = {
            "name": "My Account",
            "account_type": "invalid_type"
        }
        with pytest.raises(ValidationError):
            AccountInput(**data)


class TestCategoryInput:
    """Test CategoryInput validation."""
    
    def test_valid_category(self):
        """Test valid category input."""
        data = {
            "name": "Food & Dining",
            "category_type": "expense",
            "color": "#FF5733"
        }
        result = CategoryInput(**data)
        assert result.name == "Food & Dining"
        assert result.category_type == "expense"
        assert result.color == "#FF5733"
    
    def test_invalid_category_type_raises_error(self):
        """Test that invalid category type raises error."""
        data = {
            "name": "Test",
            "category_type": "invalid"
        }
        with pytest.raises(PydanticValidationError):
            CategoryInput(**data)
    
    def test_invalid_color_format_raises_error(self):
        """Test that invalid color format raises error."""
        data = {
            "name": "Test",
            "category_type": "expense",
            "color": "red"
        }
        with pytest.raises(PydanticValidationError):
            CategoryInput(**data)


class TestUserInput:
    """Test UserInput validation."""
    
    def test_valid_user(self):
        """Test valid user input."""
        data = {
            "telegram_id": 123456789,
            "username": "test_user",
            "language": "en"
        }
        result = UserInput(**data)
        assert result.telegram_id == 123456789
        assert result.username == "test_user"
    
    def test_invalid_telegram_id_raises_error(self):
        """Test that invalid telegram ID raises error."""
        data = {
            "telegram_id": -1,
            "username": "test"
        }
        with pytest.raises(PydanticValidationError):
            UserInput(**data)
    
    def test_invalid_username_raises_error(self):
        """Test that invalid username raises error."""
        data = {
            "telegram_id": 123456789,
            "username": "test@user!"
        }
        with pytest.raises(ValidationError):
            UserInput(**data)


class TestSanitizeString:
    """Test sanitize_string function."""
    
    def test_remove_dangerous_chars(self):
        """Test that dangerous characters are removed."""
        result = sanitize_string("test<script>alert('xss')</script>")
        assert "<" not in result
        assert ">" not in result
    
    def test_trim_whitespace(self):
        """Test that whitespace is trimmed."""
        result = sanitize_string("  test  ")
        assert result == "test"
    
    def test_max_length_truncation(self):
        """Test that string is truncated to max length."""
        long_string = "a" * 1000
        result = sanitize_string(long_string, max_length=100)
        assert len(result) == 100
