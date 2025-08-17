import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from services.websocket_manager import MultiPairWebSocketManager

@pytest.fixture
def manager():
    """Fixture for MultiPairWebSocketManager."""
    return MultiPairWebSocketManager(api_key="test_key", secret_key="test_secret")

@pytest.mark.asyncio
async def test_connect_all(mocker, manager):
    """Test the connect_all method."""
    # Mock the SinglePairWebSocketClient and its methods
    mock_client_instance = AsyncMock()
    mocker.patch(
        'services.websocket_manager.SinglePairWebSocketClient',
        return_value=mock_client_instance
    )

    await manager.connect_all()

    # Assert that clients were created for each channel
    from config import COINDCX_CHANNELS
    assert len(manager.clients) == len(COINDCX_CHANNELS)

    # Assert that the connect method was called for each client
    assert mock_client_instance.connect.call_count == len(COINDCX_CHANNELS)

@pytest.mark.asyncio
async def test_disconnect_all(mocker, manager):
    """Test the disconnect_all method."""
    # First, populate the clients dictionary as if connect_all was called
    mock_client_instance = AsyncMock()
    from config import COINDCX_CHANNELS, get_symbol_from_channel
    for channel in COINDCX_CHANNELS:
        symbol = get_symbol_from_channel(channel)
        manager.clients[symbol] = mock_client_instance

    await manager.disconnect_all()

    # Assert that the disconnect method was called for each client
    assert mock_client_instance.disconnect.call_count == len(COINDCX_CHANNELS)
