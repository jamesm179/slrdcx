import pytest
from dash import html, dash_table
import dash_bootstrap_components as dbc
from unittest.mock import patch
import pandas as pd

from app import app, update_price_table, execute_trade, update_positions_table, update_history_table
from models.trades import Trade

def test_app_layout():
    """Test the basic structure of the app layout."""
    assert isinstance(app.layout, dbc.Container)
    assert "trade-symbol" in str(app.layout)

def test_update_price_table_callback():
    """Test the update_price_table callback."""
    mock_price_data = {
        "BTC/USDT": {"symbol": "BTC/USDT", "current_price": "$50000.00", "status": "Live", "last_updated": 1672531200000},
    }
    with patch('app.PRICE_DATA', mock_price_data):
        table = update_price_table(0)
        assert isinstance(table, dash_table.DataTable)

def test_update_positions_table_callback():
    """Test the positions table callback."""
    with patch('app.trade_manager') as mock_tm:
        mock_tm.get_open_positions.return_value = []
        table = update_positions_table(0)
        assert isinstance(table, dash_table.DataTable)

def test_update_history_table_callback():
    """Test the history table callback."""
    with patch('app.trade_manager') as mock_tm:
        mock_tm.get_trade_history.return_value = []
        table = update_history_table(0)
        assert isinstance(table, dash_table.DataTable)

def test_execute_trade_callback_success():
    """Test the execute_trade callback on success."""
    mock_trade = Trade(
        trade_id="test_trade_123", symbol="BTC/USDT", action="buy",
        entry_price=50000, quantity=0.01, leverage=10,
        entry_time="2023-01-01T00:00:00", exit_price=None, exit_time=None,
        pnl=0, status='open', stop_loss=None, take_profit=None,
        exit_reason=None, order_id='order123', order_status='filled'
    )

    with patch('app.trade_manager') as mock_tm:
        mock_tm.place_trade.return_value = {"success": True, "trade": mock_trade}

        alert = execute_trade(1, "BTC/USDT", "buy", 0.01, 10)
        assert alert.color == "success"
        assert "Trade placed successfully" in str(alert.children)

def test_execute_trade_callback_failure():
    """Test the execute_trade callback on failure."""
    with patch('app.trade_manager') as mock_tm:
        mock_tm.place_trade.return_value = {"success": False, "error": "Insufficient funds"}

        alert = execute_trade(1, "BTC/USDT", "buy", 0.01, 10)
        assert alert.color == "danger"
        assert "Trade failed: Insufficient funds" in str(alert.children)

def test_execute_trade_callback_missing_input():
    """Test the execute_trade callback with missing inputs."""
    alert = execute_trade(1, "BTC/USDT", "buy", None, 10) # Missing quantity
    assert alert.color == "warning"
    assert "All fields are required" in str(alert.children)
