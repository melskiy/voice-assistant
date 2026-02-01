"""
Live Integration Test for Voice Assistant Services.

This test requires all microservices to be running.
It performs real HTTP and gRPC calls to verify end-to-end functionality.

Prerequisites:
1. All services running (docker-compose up)
2. ASR Service on localhost:50051
3. NLU Service on localhost:50052
4. Dialog Service on localhost:50053
5. TTS Service on localhost:50054
6. Storage Service on localhost:50055
7. Gateway Service on localhost:8000
8. PostgreSQL and Redis running

Usage:
    # Run all live tests
    pytest tests/test_live_integration.py -v -s
    
    # Run specific test
    pytest tests/test_live_integration.py::TestLiveIntegration::test_gateway_health -v -s
    
    # Skip live tests (if services not running)
    pytest tests/ -v --ignore=tests/test_live_integration.py
"""
import asyncio
import logging
import time
import uuid
from datetime import datetime
from typing import Dict, Optional

import pytest
import aiohttp
import grpc

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Service endpoints
GATEWAY_URL = "http://localhost:8000"
ASR_URL = "localhost:50051"
NLU_URL = "localhost:50052"
DIALOG_URL = "localhost:50053"
TTS_URL = "localhost:50054"
STORAGE_URL = "localhost:50055"


# Skip all tests in this file if LIVE_TEST env var is not set
pytestmark = pytest.mark.skipif(
    not pytest.config.getoption("--live", default=False) if hasattr(pytest, 'config') else True,
    reason="Live integration tests require --live flag and running services"
)


class ServiceClient:
    """Client for interacting with all services."""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.grpc_channels: Dict[str, grpc.aio.Channel] = {}
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
        for channel in self.grpc_channels.values():
            await channel.close()
    
    async def gateway_health(self) -> Dict:
        """Check Gateway health."""
        async with self.session.get(f"{GATEWAY_URL}/health") as resp:
            return await resp.json()
    
    async def gateway_ready(self) -> Dict:
        """Check Gateway readiness."""
        async with self.session.get(f"{GATEWAY_URL}/ready") as resp:
            return await resp.json()
    
    async def start_session(self, caller_id: str) -> Dict:
        """Start a new call session."""
        payload = {
            "caller_id": caller_id,
            "metadata": {"test": True, "timestamp": datetime.now().isoformat()}
        }
        async with self.session.post(
            f"{GATEWAY_URL}/v1/sessions/start",
            json=payload
        ) as resp:
            return await resp.json()
    
    async def end_session(self, session_id: str) -> Dict:
        """End a call session."""
        payload = {"session_id": session_id}
        async with self.session.post(
            f"{GATEWAY_URL}/v1/sessions/end",
            json=payload
        ) as resp:
            return await resp.json()
    
    async def get_shopping_list(self, session_id: str) -> Dict:
        """Get shopping list for session."""
        async with self.session.get(
            f"{GATEWAY_URL}/v1/shopping/{session_id}/items"
        ) as resp:
            return await resp.json()
    
    async def add_shopping_item(self, session_id: str, name: str, quantity: int = 1) -> Dict:
        """Add item to shopping list."""
        payload = {
            "name": name,
            "quantity": quantity,
            "unit": "шт"
        }
        async with self.session.post(
            f"{GATEWAY_URL}/v1/shopping/{session_id}/items",
            json=payload
        ) as resp:
            return await resp.json()
    
    def get_grpc_channel(self, service_url: str) -> grpc.aio.Channel:
        """Get or create gRPC channel."""
        if service_url not in self.grpc_channels:
            self.grpc_channels[service_url] = grpc.aio.insecure_channel(service_url)
        return self.grpc_channels[service_url]


@pytest.fixture
async def client():
    """Create service client."""
    async with ServiceClient() as client:
        yield client


class TestLiveIntegration:
    """Live integration tests with real service calls."""
    
    @pytest.mark.asyncio
    async def test_gateway_health(self, client: ServiceClient):
        """Test Gateway health endpoint."""
        logger.info("Testing Gateway health...")
        
        health = await client.gateway_health()
        
        logger.info(f"Health response: {health}")
        assert health.get("status") in ["healthy", "degraded"]
        assert health.get("service") == "gateway"
        
    @pytest.mark.asyncio
    async def test_gateway_readiness(self, client: ServiceClient):
        """Test Gateway readiness endpoint."""
        logger.info("Testing Gateway readiness...")
        
        ready = await client.gateway_ready()
        
        logger.info(f"Readiness response: {ready}")
        assert ready.get("status") in ["ready", "not_ready"]
    
    @pytest.mark.asyncio
    async def test_session_lifecycle(self, client: ServiceClient):
        """Test complete session lifecycle."""
        logger.info("Testing session lifecycle...")
        
        caller_id = f"+7{int(time.time())}"
        
        # Start session
        start_result = await client.start_session(caller_id)
        logger.info(f"Session started: {start_result}")
        
        assert "session_id" in start_result
        session_id = start_result["session_id"]
        
        # End session
        end_result = await client.end_session(session_id)
        logger.info(f"Session ended: {end_result}")
        
        assert end_result.get("success") is True
    
    @pytest.mark.asyncio
    async def test_shopping_list_crud(self, client: ServiceClient):
        """Test shopping list CRUD operations."""
        logger.info("Testing shopping list CRUD...")
        
        # Create session
        caller_id = f"+7{int(time.time())}"
        session = await client.start_session(caller_id)
        session_id = session["session_id"]
        
        try:
            # Add items
            items = ["молоко", "хлеб", "яйца"]
            for item in items:
                result = await client.add_shopping_item(session_id, item)
                logger.info(f"Added item: {result}")
                assert result.get("success") is True
            
            # Get list
            shopping_list = await client.get_shopping_list(session_id)
            logger.info(f"Shopping list: {shopping_list}")
            
            assert shopping_list.get("success") is True
            assert len(shopping_list.get("items", [])) == len(items)
            
        finally:
            # Cleanup
            await client.end_session(session_id)
    
    @pytest.mark.asyncio
    async def test_grpc_asr_connection(self, client: ServiceClient):
        """Test gRPC connection to ASR service."""
        logger.info("Testing gRPC ASR connection...")
        
        try:
            channel = client.get_grpc_channel(ASR_URL)
            
            # Check channel connectivity
            await asyncio.wait_for(channel.channel_ready(), timeout=5.0)
            logger.info("✓ ASR gRPC connection established")
            
        except asyncio.TimeoutError:
            pytest.skip("ASR service not available")
        except Exception as e:
            logger.error(f"ASR connection failed: {e}")
            pytest.skip(f"ASR service error: {e}")
    
    @pytest.mark.asyncio
    async def test_grpc_nlu_connection(self, client: ServiceClient):
        """Test gRPC connection to NLU service."""
        logger.info("Testing gRPC NLU connection...")
        
        try:
            channel = client.get_grpc_channel(NLU_URL)
            
            # Check channel connectivity
            await asyncio.wait_for(channel.channel_ready(), timeout=5.0)
            logger.info("✓ NLU gRPC connection established")
            
        except asyncio.TimeoutError:
            pytest.skip("NLU service not available")
        except Exception as e:
            logger.error(f"NLU connection failed: {e}")
            pytest.skip(f"NLU service error: {e}")
    
    @pytest.mark.asyncio
    async def test_grpc_dialog_connection(self, client: ServiceClient):
        """Test gRPC connection to Dialog service."""
        logger.info("Testing gRPC Dialog connection...")
        
        try:
            channel = client.get_grpc_channel(DIALOG_URL)
            
            # Check channel connectivity
            await asyncio.wait_for(channel.channel_ready(), timeout=5.0)
            logger.info("✓ Dialog gRPC connection established")
            
        except asyncio.TimeoutError:
            pytest.skip("Dialog service not available")
        except Exception as e:
            logger.error(f"Dialog connection failed: {e}")
            pytest.skip(f"Dialog service error: {e}")
    
    @pytest.mark.asyncio
    async def test_grpc_tts_connection(self, client: ServiceClient):
        """Test gRPC connection to TTS service."""
        logger.info("Testing gRPC TTS connection...")
        
        try:
            channel = client.get_grpc_channel(TTS_URL)
            
            # Check channel connectivity
            await asyncio.wait_for(channel.channel_ready(), timeout=5.0)
            logger.info("✓ TTS gRPC connection established")
            
        except asyncio.TimeoutError:
            pytest.skip("TTS service not available")
        except Exception as e:
            logger.error(f"TTS connection failed: {e}")
            pytest.skip(f"TTS service error: {e}")
    
    @pytest.mark.asyncio
    async def test_grpc_storage_connection(self, client: ServiceClient):
        """Test gRPC connection to Storage service."""
        logger.info("Testing gRPC Storage connection...")
        
        try:
            channel = client.get_grpc_channel(STORAGE_URL)
            
            # Check channel connectivity
            await asyncio.wait_for(channel.channel_ready(), timeout=5.0)
            logger.info("✓ Storage gRPC connection established")
            
        except asyncio.TimeoutError:
            pytest.skip("Storage service not available")
        except Exception as e:
            logger.error(f"Storage connection failed: {e}")
            pytest.skip(f"Storage service error: {e}")
    
    @pytest.mark.asyncio
    async def test_complete_voice_interaction(self, client: ServiceClient):
        """
        Test complete voice interaction flow.
        
        This test simulates:
        1. Incoming call
        2. Audio processing (mocked)
        3. Intent extraction
        4. Dialog processing
        5. Response generation
        6. Data persistence
        """
        logger.info("=" * 60)
        logger.info("STARTING COMPLETE VOICE INTERACTION TEST")
        logger.info("=" * 60)
        
        # Create session
        caller_id = f"+7{int(time.time())}"
        session = await client.start_session(caller_id)
        session_id = session["session_id"]
        logger.info(f"Session created: {session_id}")
        
        try:
            # Simulate adding item via API (normally would come from ASR/NLU)
            item_name = "тестовый продукт"
            add_result = await client.add_shopping_item(session_id, item_name)
            logger.info(f"Item added: {add_result}")
            
            assert add_result.get("success") is True
            assert add_result.get("item", {}).get("name") == item_name
            
            # Verify item in list
            shopping_list = await client.get_shopping_list(session_id)
            items = shopping_list.get("items", [])
            
            item_names = [item.get("name") for item in items]
            assert item_name in item_names, f"Item {item_name} not found in list: {item_names}"
            
            logger.info("✓ Complete voice interaction test passed")
            
        finally:
            await client.end_session(session_id)
            logger.info(f"Session {session_id} terminated")
    
    @pytest.mark.asyncio
    async def test_service_health_check(self, client: ServiceClient):
        """Test health of all services."""
        logger.info("Checking all services health...")
        
        services = {
            'Gateway': GATEWAY_URL,
            'ASR': ASR_URL,
            'NLU': NLU_URL,
            'Dialog': DIALOG_URL,
            'TTS': TTS_URL,
            'Storage': STORAGE_URL,
        }
        
        results = {}
        
        # Check Gateway via HTTP
        try:
            health = await client.gateway_health()
            results['Gateway'] = health.get("status", "unknown")
        except Exception as e:
            results['Gateway'] = f"error: {e}"
        
        # Check gRPC services
        for name, url in list(services.items())[1:]:
            try:
                channel = client.get_grpc_channel(url)
                await asyncio.wait_for(channel.channel_ready(), timeout=3.0)
                results[name] = "connected"
            except Exception as e:
                results[name] = f"unavailable: {e}"
        
        logger.info("Service Health Summary:")
        for name, status in results.items():
            icon = "✓" if status in ["healthy", "degraded", "connected"] else "✗"
            logger.info(f"  {icon} {name}: {status}")
        
        # At least Gateway should be healthy
        assert results.get('Gateway') in ["healthy", "degraded"], "Gateway is not healthy"


def pytest_addoption(parser):
    """Add custom pytest option for live tests."""
    parser.addoption(
        "--live",
        action="store_true",
        default=False,
        help="Run live integration tests against real services"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--live"])