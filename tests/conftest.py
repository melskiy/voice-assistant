"""
Pytest configuration and shared fixtures for voice assistant tests.
"""
import asyncio
import logging
import os
import sys
from pathlib import Path

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# Configure logging for tests
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "live: mark test as live integration test requiring running services"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--live",
        action="store_true",
        default=False,
        help="Run live integration tests against real services"
    )
    parser.addoption(
        "--integration",
        action="store_true",
        default=False,
        help="Run integration tests"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection based on options."""
    skip_live = pytest.mark.skip(reason="Need --live option to run")
    skip_integration = pytest.mark.skip(reason="Need --integration option to run")
    
    for item in items:
        if "test_live_integration.py" in item.nodeid and not config.getoption("--live"):
            item.add_marker(skip_live)
        if "integration" in item.keywords and not config.getoption("--integration"):
            item.add_marker(skip_integration)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def async_client():
    """Async HTTP client fixture."""
    import aiohttp
    async with aiohttp.ClientSession() as session:
        yield session


@pytest.fixture
def mock_grpc_channel():
    """Mock gRPC channel fixture."""
    from unittest.mock import AsyncMock, MagicMock
    
    channel = AsyncMock()
    channel.channel_ready = AsyncMock()
    channel.close = AsyncMock()
    return channel


@pytest.fixture
def test_config():
    """Test configuration fixture."""
    from voice_assistant.interfaces.container import Config
    
    config = Config()
    # Override with test values
    config.asr_service_url = "localhost:50051"
    config.nlu_service_url = "localhost:50052"
    config.dialog_service_url = "localhost:50053"
    config.tts_service_url = "localhost:50054"
    config.redis_url = "redis://localhost:6379/1"  # Use DB 1 for tests
    config.database_url = "postgresql://test:test@localhost:5432/test"
    return config


@pytest.fixture
def sample_audio_chunk():
    """Sample audio chunk data for testing."""
    return {
        'data': b'\x00\x01' * 1600,  # 100ms of 8kHz 16-bit audio
        'sample_rate': 8000,
        'channels': 1,
        'duration_ms': 100
    }


@pytest.fixture
def sample_intent():
    """Sample intent for testing."""
    return {
        'name': 'ADD_SHOPPING_ITEM',
        'confidence': 0.88,
        'entities': {'item': 'молоко', 'quantity': '1'},
        'raw_text': 'добавь молоко в список покупок'
    }


@pytest.fixture
def sample_session():
    """Sample session data for testing."""
    import uuid
    from datetime import datetime
    
    return {
        'session_id': str(uuid.uuid4()),
        'caller_id': '+79123456789',
        'start_time': datetime.now().isoformat(),
        'language': 'ru',
        'status': 'active'
    }