import pytest
from unittest.mock import mock_open, patch
import json
from config import load_config, get_pair_config, get_risk_management_config, calculate_tp_sl, CONFIG

# Sample config data for testing
SAMPLE_CONFIG_DATA = {
    "metadata": {"version": "2.0.0"},
    "trading_pairs": {"default_pairs": [
        {"symbol": "BTC/USDT", "channel": "B-BTC_USDT@prices-futures", "enabled": True, "quantity_precision": 3},
        {"symbol": "ETH/USDT", "channel": "B-ETH_USDT@prices-futures", "enabled": False, "quantity_precision": 2}
    ]},
    "risk_management": {"take_profit": {"percentage": 5.0}, "stop_loss": {"percentage": 50.0}},
    "leverage": {"default": 10.0}
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

def test_get_pair_config(mock_config_file):
    """Test retrieving a specific pair's configuration."""
    btc_config = get_pair_config("BTC/USDT")
    assert btc_config is not None
    assert btc_config["quantity_precision"] == 3

    eth_config = get_pair_config("ETH/USDT")
    assert eth_config is not None # Should still be found

    non_existent_config = get_pair_config("LTC/USDT")
    assert non_existent_config is None

def test_get_risk_management_config(mock_config_file):
    """Test retrieving the risk management configuration."""
    risk_config = get_risk_management_config()
    assert risk_config["take_profit"]["percentage"] == 5.0

def test_calculate_tp_sl():
    """Test the take profit and stop loss calculation logic."""
    # Test with standard values
    tp, sl = calculate_tp_sl(desired_tp=5.0, desired_sl=50.0, leverage=10.0)
    assert pytest.approx(tp) == 0.005  # 5% / 10x = 0.5%
    assert pytest.approx(sl) == 0.05   # 50% / 10x = 5%

    # Test with different leverage
    tp, sl = calculate_tp_sl(desired_tp=10.0, desired_sl=20.0, leverage=5.0)
    assert pytest.approx(tp) == 0.02 # 10% / 5x = 2%
    assert pytest.approx(sl) == 0.04 # 20% / 5x = 4%

    # Test with invalid leverage
    result = calculate_tp_sl(desired_tp=10.0, desired_sl=20.0, leverage=0)
    assert result == (None, None)

    # Test with negative percentages
    result = calculate_tp_sl(desired_tp=-5.0, desired_sl=20.0, leverage=10)
    assert result == (None, None)
