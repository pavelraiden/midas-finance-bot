"""
Encryption Key Validator
Ensures ENCRYPTION_KEY is properly configured
"""
import os
import sys
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def validate_encryption_key() -> bool:
    """
    Validate that ENCRYPTION_KEY is properly configured.
    
    Returns:
        True if key is valid, False otherwise
    """
    encryption_key = os.getenv("ENCRYPTION_KEY")
    
    if not encryption_key:
        logger.error("=" * 80)
        logger.error("CRITICAL: ENCRYPTION_KEY not set in environment variables!")
        logger.error("")
        logger.error("The encryption key is required to protect sensitive data.")
        logger.error("Without it, the bot cannot securely store API keys and credentials.")
        logger.error("")
        logger.error("To fix this:")
        logger.error("1. Generate a new key:")
        logger.error("   python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'")
        logger.error("")
        logger.error("2. Add it to your .env file:")
        logger.error("   ENCRYPTION_KEY=your_generated_key_here")
        logger.error("")
        logger.error("3. Restart the bot")
        logger.error("=" * 80)
        return False
    
    # Validate key format (Fernet keys are 44 characters base64)
    if len(encryption_key) != 44:
        logger.error("=" * 80)
        logger.error("CRITICAL: ENCRYPTION_KEY has invalid format!")
        logger.error("")
        logger.error(f"Expected length: 44 characters")
        logger.error(f"Actual length: {len(encryption_key)} characters")
        logger.error("")
        logger.error("Please generate a new valid key:")
        logger.error("python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'")
        logger.error("=" * 80)
        return False
    
    logger.info("✅ ENCRYPTION_KEY validated successfully")
    return True


def ensure_encryption_key_configured():
    """
    Ensure encryption key is configured, exit if not.
    """
    if not validate_encryption_key():
        logger.error("Bot cannot start without proper ENCRYPTION_KEY configuration")
        sys.exit(1)
