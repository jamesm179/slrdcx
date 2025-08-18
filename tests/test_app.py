import pytest
from dash import html, dash_table
import dash_bootstrap_components as dbc
from unittest.mock import patch, MagicMock
import pandas as pd

from app import app, update_dom_table
from models.trades import Trade

def test_app_layout():
    """Test the basic structure of the app layout."""
    assert isinstance(app.layout, dbc.Container)
    assert "trade-symbol" in str(app.layout)

def test_update_dom_table_callback():
    """Test the dom table callback."""
    mock_order_book = {"bids": [], "asks": []}
    with patch('app.ORDER_BOOK_DATA', mock_order_book):
        table = update_dom_table(0)
        assert isinstance(table, dash_table.DataTable)
