import pytest
from services.trade_manager import TradeManager
from services.coindcx_client import CoinDCXFuturesClient
from models.trades import Trade
from unittest.mock import MagicMock, mock_open, patch
import os

@pytest.fixture
def mock_futures_client():
    """Fixture for a mocked CoinDCXFuturesClient."""
    client = MagicMock(spec=CoinDCXFuturesClient)
    client.create_futures_order.return_value = {
        "success": True,
        "data": {
            "orders": [{
                "id": "test_order_id",
                "avg_price": "50000.0"
            }]
        }
    }
    return client

@pytest.fixture
def trade_manager(tmp_path):
    """Fixture for TradeManager using a temporary directory."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return TradeManager(data_dir=str(data_dir))

def test_place_trade(trade_manager, mock_futures_client):
    """Test placing a trade."""
    symbol = "BTC/USDT"
    side = "buy"
    quantity = 0.01
    leverage = 10

    with patch("builtins.open", mock_open()) as mocked_file:
        result = trade_manager.place_trade(
            client=mock_futures_client,
            symbol=symbol,
            side=side,
            quantity=quantity,
            leverage=leverage
        )

        assert result["success"] is True
        trade = result["trade"]
        assert isinstance(trade, Trade)
        assert trade.symbol == symbol
        assert len(trade_manager.open_positions) == 1

        mocked_file.assert_called_with(trade_manager.trades_file, 'a', newline='', encoding='utf-8')

def test_load_existing_data(tmp_path):
    """Test loading data from an existing CSV file."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    trades_file = data_dir / "trades.csv"

    csv_content = (
        "trade_id,symbol,action,entry_price,exit_price,quantity,leverage,entry_time,exit_time,pnl,status,stop_loss,take_profit,exit_reason,order_id,order_status\n"
        "trade_1,BTC/USDT,buy,50000,,0.01,10,2023-01-01T12:00:00,,,open,,,,,,\n"
        "trade_2,ETH/USDT,sell,4000,3900,0.1,5,2023-01-01T13:00:00,2023-01-01T14:00:00,50.0,closed,,,manual,,\n"
    )
    trades_file.write_text(csv_content)

    manager = TradeManager(data_dir=str(data_dir))

    assert len(manager.open_positions) == 1
    assert "trade_1" in manager.open_positions
    assert manager.open_positions["trade_1"].symbol == "BTC/USDT"

    assert len(manager.closed_trades) == 1
    assert manager.closed_trades[0].symbol == "ETH/USDT"
