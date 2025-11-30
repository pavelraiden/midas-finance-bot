"""
Unit tests for EncryptionService.
"""

import pytest
from decimal import Decimal

from infrastructure.security.encryption_service import EncryptionService


@pytest.mark.unit
@pytest.mark.security
class TestEncryptionService:
    """Tests for EncryptionService."""
    
    def test_encrypt_decrypt_string(self):
        """Test encrypting and decrypting a string."""
        service = EncryptionService()
        
        plaintext = "Hello, World!"
        encrypted = service.encrypt(plaintext)
        decrypted = service.decrypt(encrypted)
        
        assert decrypted == plaintext
        assert encrypted != plaintext
    
    def test_encrypt_decrypt_number(self):
        """Test encrypting and decrypting a number."""
        service = EncryptionService()
        
        plaintext = "123.456"
        encrypted = service.encrypt(plaintext)
        decrypted = service.decrypt(encrypted)
        
        assert decrypted == plaintext
    
    def test_encrypt_empty_string(self):
        """Test encrypting an empty string."""
        service = EncryptionService()
        
        plaintext = ""
        encrypted = service.encrypt(plaintext)
        decrypted = service.decrypt(encrypted)
        
        assert decrypted == plaintext
    
    def test_decrypt_invalid_token(self):
        """Test decrypting an invalid token."""
        from infrastructure.security.encryption_service import DecryptionError
        
        service = EncryptionService()
        
        invalid_token = "invalid_token_12345"
        
        with pytest.raises(DecryptionError):
            service.decrypt(invalid_token)
    
    def test_encrypt_decrypt_unicode(self):
        """Test encrypting and decrypting unicode characters."""
        service = EncryptionService()
        
        plaintext = "Привет, мир! 🚀"
        encrypted = service.encrypt(plaintext)
        decrypted = service.decrypt(encrypted)
        
        assert decrypted == plaintext
    
    def test_encrypt_decrypt_long_string(self):
        """Test encrypting and decrypting a long string."""
        service = EncryptionService()
        
        plaintext = "A" * 10000
        encrypted = service.encrypt(plaintext)
        decrypted = service.decrypt(encrypted)
        
        assert decrypted == plaintext
    
    def test_encrypt_none(self):
        """Test encrypting None returns None."""
        service = EncryptionService()
        
        encrypted = service.encrypt(None)
        
        assert encrypted is None
    
    def test_decrypt_none(self):
        """Test decrypting None."""
        service = EncryptionService()
        
        decrypted = service.decrypt(None)
        
        assert decrypted is None
    
    def test_key_persistence(self):
        """Test that key is persisted in instance."""
        service = EncryptionService()
        
        plaintext = "Test message"
        encrypted = service.encrypt(plaintext)
        decrypted = service.decrypt(encrypted)
        
        assert decrypted == plaintext
        assert service._key is not None
