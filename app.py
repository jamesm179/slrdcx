import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, dash_table, Input, Output, State, callback
import pandas as pd
import asyncio
import threading
import json

from config import COINDCX_API_KEY, COINDCX_SECRET_KEY, PRICE_DATA, TRADING_PAIRS, get_channel_from_symbol
from services.websocket_manager import MultiPairWebSocketManager
from services.coindcx_client import CoinDCXFuturesClient
from services.trade_manager import TradeManager
from models.orders import OrderSide, OrderType

# --- WebSocket Thread ---
def run_websocket_manager():
    manager = MultiPairWebSocketManager(COINDCX_API_KEY, COINDCX_SECRET_KEY)
    asyncio.run(manager.connect_all())

ws_thread = threading.Thread(target=run_websocket_manager, daemon=True)
ws_thread.start()

# --- Global Clients & Managers ---
futures_client = CoinDCXFuturesClient(COINDCX_API_KEY, COINDCX_SECRET_KEY)
trade_manager = TradeManager()

# --- Dash App ---
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = dbc.Container([
    dbc.Row(dbc.Col(html.H1("CoinDCX Scalping Dashboard"), width=12), className="mb-4 mt-4"),
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Trading Controls"),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col(dcc.Dropdown(id='trade-symbol', options=[{'label': p, 'value': p} for p in TRADING_PAIRS], value=TRADING_PAIRS[0]), width=6),
                        dbc.Col(dcc.RadioItems(id='trade-side', options=[{'label': 'Buy', 'value': 'buy'}, {'label': 'Sell', 'value': 'sell'}], value='buy', inline=True), width=6),
                    ]),
                    dbc.Row([
                        dbc.Col(dbc.Input(id='trade-quantity', type='number', placeholder='Quantity', value=1), width=6),
                        dbc.Col(dbc.Input(id='trade-leverage', type='number', placeholder='Leverage', value=10), width=6),
                    ], className="mt-2"),
                    dbc.Button("Execute Trade", id='execute-trade-button', color="primary", className="mt-3"),
                    html.Div(id='trade-output', className="mt-3")
                ])
            ], className="mb-4"),
            dbc.Card([
                dbc.CardHeader("Live Market Prices"),
                dbc.CardBody(html.Div(id='price-table-live'))
            ]),
        ], md=5),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Open Positions"),
                dbc.CardBody(html.Div(id='positions-table-live'))
            ], className="mb-4"),
            dbc.Card([
                dbc.CardHeader("Trade History"),
                dbc.CardBody(html.Div(id='history-table-live'))
            ]),
        ], md=7),
    ]),
    dcc.Interval(id='interval-component', interval=1*1000, n_intervals=0)
], fluid=True)

# --- Callbacks ---
@callback(
    Output('price-table-live', 'children'),
    Input('interval-component', 'n_intervals')
)
def update_price_table(n):
    data = list(PRICE_DATA.values())
    df = pd.DataFrame(data)
    if not df.empty:
        df = df[['symbol', 'current_price', 'status', 'last_updated']]
        df['last_updated'] = pd.to_datetime(df['last_updated'], unit='ms').dt.strftime('%H:%M:%S')
    return dash_table.DataTable(data=df.to_dict('records'), style_table={'overflowX': 'auto'})

@callback(
    Output('positions-table-live', 'children'),
    Input('interval-component', 'n_intervals')
)
def update_positions_table(n):
    positions = trade_manager.get_open_positions()
    df = pd.DataFrame(positions)
    return dash_table.DataTable(data=df.to_dict('records'), style_table={'overflowX': 'auto'})

@callback(
    Output('history-table-live', 'children'),
    Input('interval-component', 'n_intervals')
)
def update_history_table(n):
    history = trade_manager.get_trade_history()
    df = pd.DataFrame(history)
    return dash_table.DataTable(data=df.to_dict('records'), style_table={'overflowX': 'auto'})

@callback(
    Output('trade-output', 'children'),
    Input('execute-trade-button', 'n_clicks'),
    State('trade-symbol', 'value'),
    State('trade-side', 'value'),
    State('trade-quantity', 'value'),
    State('trade-leverage', 'value'),
    prevent_initial_call=True
)
def execute_trade(n_clicks, symbol, side, quantity, leverage):
    if not all([symbol, side, quantity, leverage]):
        return dbc.Alert("All fields are required.", color="warning")

    result = trade_manager.place_trade(
        client=futures_client,
        symbol=symbol,
        side=side,
        quantity=float(quantity),
        leverage=float(leverage)
    )

    if result.get("success"):
        return dbc.Alert(f"Trade placed successfully: {result.get('trade').trade_id}", color="success")
    else:
        return dbc.Alert(f"Trade failed: {result.get('error')}", color="danger")

if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0', port=8000)
