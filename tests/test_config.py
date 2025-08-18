import pytest
from unittest.mock import mock_open, patch
import json
from config import load_config, CONFIG

# Sample config data for testing
SAMPLE_CONFIG_DATA = {
    "metadata": {"version": "2.0.0"},
    "trading_pairs": {"default_pairs": [
        {"symbol": "BTC/USDT", "channel": "B-BTC_USDT@prices-futures", "enabled": True, "quantity_precision": 3},
        {"symbol": "ETH/USDT", "channel": "B-ETH_USDT@prices-futures", "enabled": False, "quantity_precision": 2}
    ]},
    "exchange": {"websocket_url": "wss://test.url"},
    "websocket": {"ping_interval": 10},
    "api_credentials": {"key": "test", "secret": "test"}
}

@pytest.fixture
def mock_config_file(mocker):
    """Fixture to mock the config file."""
    mocker.patch('builtins.open', mock_open(read_data=json.dumps(SAMPLE_CONFIG_DATA)))
    # This patch is to ensure that when load_config is called, it uses the mocked open
    mocker.patch('config.CONFIG', SAMPLE_CONFIG_DATA)
    return SAMPLE_CONFIG_DATA

def test_load_config(mock_config_file):
    """Test that the configuration loads correctly."""
    config = load_config()
    assert config["metadata"]["version"] == "2.0.0"
    assert len(config["trading_pairs"]["default_pairs"]) == 2
