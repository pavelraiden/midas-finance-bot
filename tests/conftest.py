"""
Pytest configuration and fixtures.
"""

import pytest
import asyncio
import sys
from pathlib import Path
from datetime import datetime
from decimal import Decimal

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_wallet_id():
    """Sample wallet ID for tests."""
    return "test-wallet-123"


@pytest.fixture
def sample_user_id():
    """Sample user ID for tests."""
    return "test-user-456"


@pytest.fixture
def sample_balance():
    """Sample balance for tests."""
    return Decimal("612.50")


@pytest.fixture
def sample_timestamp():
    """Sample timestamp for tests."""
    return datetime(2025, 11, 30, 12, 0, 0)


@pytest.fixture
def sample_encryption_key():
    """Sample encryption key for tests."""
    from cryptography.fernet import Fernet
    return Fernet.generate_key()
