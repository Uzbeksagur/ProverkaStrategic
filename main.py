import time
from pybit.unified_trading import HTTP
from pybit.unified_trading import WebSocket
import rel
import websocket
import hmac
import json
import os
from keep_alive import keep_alive
keep_alive()

api_key = os.environ.get("key")
api_secret = os.environ.get("secret")

# Initialize HTTP session and WebSocket
session = HTTP(demo=True, api_key=api_key, api_secret=api_secret)
ws = WebSocket(testnet=False, channel_type="linear")


# Trading parameters
symbol = "TIAUSDT"
interval = 30
signal = 0.016
stop_loss = 0.28
take_profit = 0.038
qty = 100

# Global variables to store order IDs
buy_order_id = None
sell_order_id = None

# Function to open a position with buy/sell orders
def open_position(price): 
    global buy_order_id, sell_order_id
    try:
        buy_price = price * (1 - signal)
        sell_price = price * (1 + signal)
        stop_priceBuy = buy_price * (1 - stop_loss)
        stop_priceSell = sell_price * (1 + stop_loss)
        takeBuy = buy_price * (1 + take_profit)
        takeSell = sell_price * (1 - take_profit)
    except Exception as e:
        print(f"Error setting variables: {e}")

    try:
        # Place Buy Order
        buy_order = session.place_order(
            category="linear",
            symbol=symbol,
            side="Buy",
            orderType="Limit",
            qty=qty,
            price=buy_price,
            stopLoss=stop_priceBuy,
            takeProfit=takeBuy,
            positionIdx=1,
            tpslMode='Partial'
        )
        buy_order_id = buy_order['result']['orderId']  # Store Buy order ID

        # Place Sell Order
        sell_order = session.place_order(
            category="linear",
            symbol=symbol,
            side="Sell",
            orderType="Limit",
            qty=qty,
            price=sell_price,
            stopLoss=stop_priceSell,
            takeProfit=takeSell,
            positionIdx=2,
            tpslMode='Partial'
        )
        sell_order_id = sell_order['result']['orderId']  # Store Sell order ID

        print('Orders Opened')

    except Exception as e:
        print(f"Error placing orders: {e}")

# Get the latest price for the symbol
def getPrice():
    kline = session.get_kline(
        category="linear",
        symbol=symbol,
        interval=interval,
        limit=1
    )
    price = kline['result']['list'][0][1]
    return float(price)

# Cancel all open orders for the symbol
def closeOrders():
    session.cancel_all_orders(
        category="linear",
        symbol=symbol,
        orderFilter='Order'
    )

# Reopen buy/sell orders after closing existing ones
def reopen():
    global buy_order_id, sell_order_id
    try:
        closeOrders()
        print("Orders Closed")
    except Exception as e:
        print(f"Error closing orders: {e}")
    
    try:
        price = float(getPrice())
        open_position(price)
    except Exception as e:
        print(f"Error reopening orders: {e}")

# Handle position updates from WebSocket
def handle_order(message):
    global buy_order_id, sell_order_id
    response = json.loads(message)
    for order in response.get("data", []):
        if order.get("orderStatus") == "Filled" and order.get("orderId") == buy_order_id:
            print("Buy order filled, canceling Sell order.")
            try:
                session.cancel_order(category='linear', symbol=symbol, orderId=sell_order_id)
                print("Sell order Canceled")
            except Exception as e:
                print(f"Error canceling sell order: {e}")
            sell_order_id = None  # Reset Sell order ID
        elif order.get("orderStatus") == "Filled" and order.get("orderId") == sell_order_id:
            print("Sell order filled, canceling Buy order.")
            try:
                session.cancel_order(category='linear', symbol=symbol, orderId=buy_order_id)
                print("Buy order Canceled")
            except Exception as e:
                print(f"Error canceling buy order: {e}")
            buy_order_id = None  # Reset Buy order ID

# Handle kline updates and check for confirmation to reopen orders
def handle_message(message):
    run = message['data'][0]['confirm']
    if run:
        reopen()

# Subscribe to kline updates
def webik():
    ws.kline_stream(
        interval=interval,
        symbol=symbol,
        callback=handle_message
    )

# Initialize WebSocket and position update listeners
webik()

def on_open(ws):
    # Generăm `expires` și `signature` când conexiunea este stabilită
    expires = int((time.time() + 5) * 1000)
    signature = str(hmac.new(
        bytes(api_secret, "utf-8"),
        bytes(f"GET/realtime{expires}", "utf-8"), digestmod="sha256"
    ).hexdigest())

    # Trimite autentificarea
    ws.send(
        json.dumps({
            "op": "auth",
            "args": [api_key, expires, signature]
        })
    )
    
    # Trimite abonarea la order stream
    ws.send(
        json.dumps({
            "op": "subscribe",
            "args": [
                "order"
            ]
        })
    )

def on_message(ws, message):
    if 'topic' in message:
        handle_order(message)

def on_error(ws, error):
    print("Eroare:", error)

def on_close(ws, close_status_code, close_msg):
    print("Conexiune inchisa", close_status_code, close_msg)

if __name__ == "__main__":
    ws = websocket.WebSocketApp(
        "wss://stream-demo.bybit.com/v5/private",
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    ws.run_forever(dispatcher=rel, reconnect=5)  # Set dispatcher to automatic reconnection, 5 second reconnect delay if connection closed unexpectedly
    rel.signal(2, rel.abort)  # Keyboard Interrupt
    rel.dispatch()
