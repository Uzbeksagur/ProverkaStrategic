import time
from pybit.unified_trading import HTTP
from pybit.unified_trading import WebSocket
import rel
import websocket
import hmac
import json
import os
import requests
from keep_alive import keep_alive
keep_alive()

api_key = os.environ.get("key")
api_secret = os.environ.get("secret")

token = os.environ.get("token")
chat_id = os.environ.get("chat")

# Initialize HTTP session and WebSocket
session = HTTP(demo=True, api_key=api_key, api_secret=api_secret)
ws = WebSocket(testnet=False, channel_type="linear")

# Trading parameters
symbol = "TIAUSDT"
interval = 30
signal = 0.016
stop_loss = 0.28
take_profit = 0.038
fill_price = 5 * 10

# Global variables to store order IDs
buy_order_id = None
sell_order_id = None

def handle_wallet(message):
    avi = message.get('availableToWithdraw', '0')
    mar = message.get('equity', '0')
    return(f'Available: {round(float(avi), 2)}, Total: {round(float(mar), 2)}')

# Function to send Messages in Telegram
def sendMessage(msg):
    url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={msg}"
    try:
        requests.get(url)
    except Exception as e:
        print(f"Error sending Message: {e}")
    try:
        wallet = session.get_wallet_balance(accountType="UNIFIED",coin="USDT")
        message = wallet["result"]["list"][0]["coin"][0]
        try: 
            url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={handle_wallet(message)}"
            requests.get(url)
        except Exception as e:
            print(f"Error seting Wallet Message: {e}")
    except Exception as e:
        print(f"Error sending Wallet Message: {e}")

# Function to open a position with buy/sell orders
def open_position(price): 
    global buy_order_id, sell_order_id
    qty = fill_price / price
    try:
        buy_price = price * (1 - signal)
        sell_price = price * (1 + signal)
        stop_priceBuy = buy_price * (1 - stop_loss)
        stop_priceSell = sell_price * (1 + stop_loss)
        takeBuy = buy_price * (1 + take_profit)
        takeSell = sell_price * (1 - take_profit)
    except Exception as e:
        print(f"Error setting variables: {e}")
    
    wallet = session.get_wallet_balance(accountType="UNIFIED",coin="USDT")
    message = wallet["result"]["list"][0]["coin"][0]
    avi = message.get('availableToWithdraw', '0')

    if (float(avi) > 50):
        try:
            # Place Buy Order
            buy_order = session.place_order(
                category="linear",
                symbol=symbol,
                side="Buy",
                orderType="Limit",
                qty=round(qty, 1),
                price=round(buy_price, 3),
                stopLoss=round(stop_priceBuy, 3),
                takeProfit=round(takeBuy, 3),
                positionIdx=1,
                tpslMode='Partial'
            )
            buy_order_id = buy_order['result']['orderId']  # Store Buy order ID
        
        except Exception as e:
            print(f"Error placing BUY order: {e}")

        try:
            # Place Sell Order
            sell_order = session.place_order(
                category="linear",
                symbol=symbol,
                side="Sell",
                orderType="Limit",
                qty=round(qty, 1),
                price=round(sell_price, 3),
                stopLoss=round(stop_priceSell, 3),
                takeProfit=round(takeSell, 3),
                positionIdx=2,
                tpslMode='Partial'
            )
            sell_order_id = sell_order['result']['orderId']  # Store Sell order ID

        except Exception as e:
            print(f"Error placing SELL order: {e}")
    else:
        print('Caroce Balansul e mai mic de 50')

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
        pnl = order.get("closedPnl")
        # if pnl != "0":
        #     sendMessage(f"Position Closed with Profit: {round(float(pnl), 2)}")
        if order.get("orderStatus") == "Filled" and order.get("orderId") == buy_order_id:
            qty = order.get("qty")
            price = order.get("price")
            print("Buy order filled")
            sendMessage(f"Buy Order Filled on Price: {price}, on Quantity: {qty}, with total Price: {round((float(qty)*float(price)), 2)}")
            sell_order_id = None  # Reset Sell order ID
        elif order.get("orderStatus") == "Filled" and order.get("orderId") == sell_order_id:
            qty = order.get("qty")
            price = order.get("price")
            print("Sell order filled")
            sendMessage(f"Sell Order Filled on Price: {price}, on Quantity: {qty}, with total Price: {round((float(qty)*float(price)), 2)}")
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
