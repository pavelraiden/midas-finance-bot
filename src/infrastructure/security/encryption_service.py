"""
Improved Fernet Encryption Service для безопасного хранения credentials.

Production-ready encryption для 50 users без over-engineering.
"""

import os
import base64
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import logging

logger = logging.getLogger(__name__)


class EncryptionService:
    """
    Production-ready encryption service на основе Fernet.
    
    Преимущества:
    - Symmetric encryption (AES-128)
    - Built-in authentication (HMAC)
    - Timestamp support для key rotation
    - Simple API
    - No external dependencies (AWS, etc.)
    
    Подходит для 50 users, но с enterprise-grade security.
    """
    
    def __init__(self, key: Optional[bytes] = None, salt: Optional[bytes] = None):
        """
        Инициализация encryption service.
        
        Args:
            key: Fernet key (если None, генерируется из env)
            salt: Salt для key derivation (если None, берется из env)
        """
        if key is None:
            key = self._get_or_generate_key(salt)
        
        self.fernet = Fernet(key)
        self._key = key
        
        logger.info("EncryptionService initialized")
    
    def _get_or_generate_key(self, salt: Optional[bytes] = None) -> bytes:
        """
        Получает или генерирует Fernet key.
        
        Args:
            salt: Salt для key derivation
            
        Returns:
            Fernet key (32 bytes, base64-encoded)
        """
        # Проверяем env variable
        key_str = os.getenv("ENCRYPTION_KEY")
        if key_str:
            logger.info("Using ENCRYPTION_KEY from environment")
            return key_str.encode()
        
        # Генерируем из passphrase + salt (более безопасно чем просто random key)
        passphrase = os.getenv("ENCRYPTION_PASSPHRASE")
        if not passphrase:
            # Fallback: генерируем random key
            key = Fernet.generate_key()
            logger.warning("Generated new random Fernet key")
            logger.warning(f"Add to .env: ENCRYPTION_KEY={key.decode()}")
            return key
        
        # Derive key from passphrase
        if salt is None:
            salt_str = os.getenv("ENCRYPTION_SALT")
            if salt_str:
                salt = base64.b64decode(salt_str.encode())
            else:
                salt = os.urandom(16)
                logger.warning(f"Generated new salt: {base64.b64encode(salt).decode()}")
                logger.warning(f"Add to .env: ENCRYPTION_SALT={base64.b64encode(salt).decode()}")
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,  # OWASP recommendation 2023
        )
        key = base64.urlsafe_b64encode(kdf.derive(passphrase.encode()))
        
        logger.info("Derived encryption key from passphrase")
        return key
    
    def encrypt(self, plaintext: str) -> str:
        """
        Шифрует plaintext.
        
        Args:
            plaintext: Текст для шифрования
            
        Returns:
            Base64-encoded ciphertext
            
        Raises:
            EncryptionError: При ошибке шифрования
        """
        try:
            if plaintext is None:
                return None
            
            if plaintext == "":
                # Allow empty strings, encrypt them
                pass
            
            token = self.fernet.encrypt(plaintext.encode('utf-8'))
            ciphertext = token.decode('utf-8')
            
            logger.debug(f"Successfully encrypted {len(plaintext)} bytes")
            return ciphertext
            
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise EncryptionError(f"Failed to encrypt: {e}") from e
    
    def decrypt(self, ciphertext: str) -> str:
        """
        Дешифрует ciphertext.
        
        Args:
            ciphertext: Base64-encoded ciphertext
            
        Returns:
            Decrypted plaintext
            
        Raises:
            DecryptionError: При ошибке дешифрования
        """
        try:
            if ciphertext is None:
                return None
            
            if not ciphertext:
                raise ValueError("Ciphertext cannot be empty")
            
            token = ciphertext.encode('utf-8')
            plaintext = self.fernet.decrypt(token).decode('utf-8')
            
            logger.debug(f"Successfully decrypted {len(plaintext)} bytes")
            return plaintext
            
        except InvalidToken as e:
            logger.error("Invalid token or corrupted ciphertext")
            raise DecryptionError("Invalid token or corrupted ciphertext") from e
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise DecryptionError(f"Failed to decrypt: {e}") from e
    
    def rotate_key(self, new_key: bytes) -> 'EncryptionService':
        """
        Создает новый EncryptionService с новым ключом для key rotation.
        
        Args:
            new_key: Новый Fernet key
            
        Returns:
            Новый EncryptionService instance
        """
        logger.info("Creating new EncryptionService for key rotation")
        return EncryptionService(key=new_key)
    
    def re_encrypt(self, ciphertext: str, new_service: 'EncryptionService') -> str:
        """
        Перешифровывает данные с новым ключом (для key rotation).
        
        Args:
            ciphertext: Старый ciphertext
            new_service: Новый EncryptionService с новым ключом
            
        Returns:
            Новый ciphertext
        """
        plaintext = self.decrypt(ciphertext)
        return new_service.encrypt(plaintext)


class EncryptionError(Exception):
    """Ошибка при шифровании."""
    pass


class DecryptionError(Exception):
    """Ошибка при дешифровании."""
    pass


# Singleton instance
_encryption_service: Optional[EncryptionService] = None


def get_encryption_service() -> EncryptionService:
    """
    Получает singleton instance EncryptionService.
    
    Returns:
        EncryptionService instance
    """
    global _encryption_service
    
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    
    return _encryption_service


def encrypt_credential(plaintext: str) -> str:
    """
    Helper function для шифрования credentials.
    
    Args:
        plaintext: Credential для шифрования
        
    Returns:
        Encrypted credential
    """
    service = get_encryption_service()
    return service.encrypt(plaintext)


def decrypt_credential(ciphertext: str) -> str:
    """
    Helper function для дешифрования credentials.
    
    Args:
        ciphertext: Encrypted credential
        
    Returns:
        Decrypted credential
    """
    service = get_encryption_service()
    return service.decrypt(ciphertext)
