"""
Unit tests for custom exceptions.
"""

import pytest

from infrastructure.error_handling.exceptions import (
    MidasException,
    DatabaseError,
    ValidationError,
    ExternalAPIError,
    get_user_friendly_message
)


@pytest.mark.unit
@pytest.mark.error_handling
class TestExceptions:
    """Tests for custom exceptions."""
    
    def test_midas_exception(self):
        """Test MidasException base class."""
        exc = MidasException("Test error")
        
        assert str(exc) == "Test error"
        assert exc.message == "Test error"
    
    def test_database_error(self):
        """Test DatabaseError."""
        exc = DatabaseError("Connection failed")
        
        assert isinstance(exc, MidasException)
        assert str(exc) == "Connection failed"
    
    def test_validation_error(self):
        """Test ValidationError."""
        exc = ValidationError("Invalid amount")
        
        assert isinstance(exc, MidasException)
        assert str(exc) == "Invalid amount"
    
    def test_external_api_error(self):
        """Test ExternalAPIError."""
        exc = ExternalAPIError("API timeout")
        
        assert isinstance(exc, MidasException)
        assert str(exc) == "API timeout"
    
    def test_get_user_friendly_message_database(self):
        """Test user-friendly message for database error."""
        exc = DatabaseError("Connection failed", code="DB_CONNECTION_ERROR")
        message = get_user_friendly_message(exc, language="en")
        
        assert "database" in message.lower()
    
    def test_get_user_friendly_message_validation(self):
        """Test user-friendly message for validation error."""
        exc = ValidationError("Invalid amount", code="INVALID_AMOUNT")
        message = get_user_friendly_message(exc, language="en")
        
        assert "invalid" in message.lower()
    
    def test_get_user_friendly_message_api(self):
        """Test user-friendly message for API error."""
        exc = ExternalAPIError("API timeout", code="BLOCKCHAIN_API_ERROR")
        message = get_user_friendly_message(exc, language="en")
        
        assert "blockchain" in message.lower() or "api" in message.lower()
    
    def test_get_user_friendly_message_russian(self):
        """Test user-friendly message in Russian."""
        exc = DatabaseError("Connection failed", code="DB_CONNECTION_ERROR")
        message = get_user_friendly_message(exc, language="ru")
        
        assert "базе данных" in message.lower()
    
    def test_get_user_friendly_message_unknown(self):
        """Test user-friendly message for unknown error."""
        exc = Exception("Unknown error")
        message = get_user_friendly_message(exc, language="en")
        
        assert "error" in message.lower()
