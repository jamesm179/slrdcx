import pytest
import requests
from services.coindcx_client import CoinDCXFuturesClient
from models.orders import OrderSide, OrderType
from unittest.mock import Mock

@pytest.fixture
def client():
    """Fixture for CoinDCXFuturesClient."""
    return CoinDCXFuturesClient(api_key="test_key", secret_key="test_secret")

def test_create_futures_order_success(mocker, client):
    """Test successful futures order creation."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"orders": [{"id": "12345"}]}
    mocker.patch("requests.post", return_value=mock_response)

    result = client.create_futures_order(
        symbol="B-BTC_USDT",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=0.001,
        leverage=10
    )

    assert result["success"] is True
    assert result["data"]["orders"][0]["id"] == "12345"

def test_create_futures_order_failure(mocker, client):
    """Test failed futures order creation."""
    mock_response = Mock()
    mock_response.status_code = 400
    mock_response.text = '{"error": "Invalid quantity"}'
    mocker.patch("requests.post", return_value=mock_response)

    result = client.create_futures_order(
        symbol="B-BTC_USDT",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=0.00001,
        leverage=10
    )

    assert result["success"] is False
    assert "Invalid quantity" in result["error"]
