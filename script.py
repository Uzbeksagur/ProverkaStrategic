from playwright.sync_api import sync_playwright
import schedule
from pybit.unified_trading import HTTP
from pybit.unified_trading import WebSocket
import requests
import time
from keep_alive import keep_alive
keep_alive()

playwright = None
browser = None
page = None

class Row:
  def __init__(self, symbol, time, rate):
    self.symbol = symbol
    self.time = time
    self.rate = rate

api_key = "LfjAunj7W0SLLbGa0s"
api_secret = "9uMKJVhFa9NhbPXfxEOfCdLQSn6QZyQtY8pi"

token = "7035583013:AAHki-p3K10U23zFi3IqOYT92LscE_-x0JE"
chat_id = "7308714189"

# Initialize HTTP session and WebSocket
session = HTTP(demo=True, api_key=api_key, api_secret=api_secret)

ws = WebSocket(
    testnet=False,
    demo=True,
    channel_type="private",
    api_key=api_key,
    api_secret=api_secret,
)

open_positions = []

def send_telegram_message(msg):
    url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={msg}"
    requests.get(url)
def sendMessage(ms):
    try:
        message = ms['data'][0]
        global open_positions

        # Verificăm dacă mesajul este pentru deschiderea unei poziții
        if message['createType'] == 'CreateByUser' and message['side'] in ['Buy', 'Sell']:
            symbol = message['symbol']
            exec_qty = float(message['execQty'])
            side = message['side']
            exec_price = float(message['execPrice'])
            exec_fee = float(message['execFee'])

            # Adăugăm poziția deschisă în lista de poziții
            open_positions.append({
                'symbol': symbol,
                'execQty': exec_qty,
                'side': side,
                'execPrice': exec_price,
                'execFee': exec_fee
            })

        # Verificăm dacă mesajul este pentru închiderea unei poziții
        elif message['createType'] in ['CreateByClosing', 'CreateByPartialTakeProfit', 'CreateByPartialStopLoss', 'CreateByTakeProfit', 'CreateByStopLoss']:
            symbol = message['symbol']
            close_qty = float(message['execQty'])
            close_price = float(message['execPrice'])
            close_fee = float(message['execFee'])

            # Căutăm poziția deschisă corespunzătoare
            for idx, open_position in enumerate(open_positions):
                if (open_position['symbol'] == symbol and
                    open_position['execQty'] == close_qty):

                    # Calculăm profitul sau pierderea pentru cantitatea închisă
                    open_fee = open_position['execFee']
                    open_price = open_position['execPrice'] 
                    side = open_position['side']
                    quantity = close_qty  # Folosim cantitatea închisă

                    if side == 'Buy':
                        profit = (close_price - open_price) * quantity - (close_fee + open_fee)
                    else:  # 'Sell'
                        profit = (open_price - close_price) * quantity - (close_fee + open_fee)

                    # Afișăm mesajul cu profitul sau pierderea
                    profit_message = f"Poziția a fost închisă. Profit: {profit:.2f} USDT ({symbol})"
                    send_telegram_message(profit_message)

                    # Ajustăm cantitatea rămasă în poziția deschisă
                    open_position['execQty'] -= close_qty

                    # Dacă cantitatea rămasă este zero, eliminăm poziția din listă
                    if open_position['execQty'] <= 0:
                        open_positions.pop(idx)

                    break
    except Exception as e:
        print(f"Error sending message: {e}")

def initialize_browser():
    global playwright, browser, page
    playwright = sync_playwright().start()
    browser = playwright.firefox.launch()  # Setează `headless=True` dacă nu vrei să vezi browserul
    page = browser.new_page()
    url = "https://bybit.com/en/announcement-info/fund-rate/"
    page.goto(url, timeout=480000)
    page.wait_for_selector("table")  # Așteaptă să se încarce tabelul

# Scriptul Playwright
def fetch_table_data():
    global page
    # Asigură-te că pagina este încă validă
    if not page:
        initialize_browser()

    # Sortează tabelul și obține datele pentru cel mai negativ și cel mai pozitiv rate
    page.click("table thead tr th:nth-child(5)")
    page.wait_for_timeout(1000)  # Pauză pentru siguranță
    negative = Row(
        page.locator("table tbody tr:nth-child(2) td:nth-child(1)").inner_text(),
        page.locator("table tbody tr:nth-child(2) td:nth-child(4)").inner_text(),
        page.locator("table tbody tr:nth-child(2) td:nth-child(5)").inner_text(),
    )

    page.click("table thead tr th:nth-child(5)")
    page.wait_for_timeout(1000)  # Pauză pentru siguranță
    positive = Row(
        page.locator("table tbody tr:nth-child(2) td:nth-child(1)").inner_text(),
        page.locator("table tbody tr:nth-child(2) td:nth-child(4)").inner_text(),
        page.locator("table tbody tr:nth-child(2) td:nth-child(5)").inner_text(),
    )

    negativeRate = float(negative.rate.replace('%', '').replace('-', ''))
    positiveRate = float(positive.rate.replace('%', '').replace('-', ''))
    if positiveRate <= negativeRate:
        return negative
    else:
        return positive

# Function to open a position with buy/sell orders
def open_position(price, symbol, side): 
    qty = 202/price
    takeProfit = 0.012
    stopLoss = 0.075
    # buy = 1
    idx = 1
    try:
        if side == 'Buy':
            stopPrice = price * (1 - stopLoss)
            takePrice = price * (1 + takeProfit)
            idx = 1
        elif side == 'Sell':
            stopPrice = price * (1 + stopLoss)
            takePrice = price * (1 - takeProfit)
            idx = 2
    except Exception as e:
        print(f"Error setting variables: {e}")

    try:
        # Place Order
        session.place_order(
            category="linear",
            symbol=symbol,
            side=side,
            orderType="Market",
            qty=round(qty),
            positionIdx=idx,
            stopLoss=stopPrice,
            takeProfit=takePrice,
            tpslMode='Partial',
            tpSize=str(round(qty)),
            slSize=str(round(qty)),
        )
    except Exception as e:
        print(f"Error placing order: {e}")

# Get the latest price for the symbol
def getPrice(symbol):
    tiker = session.get_tickers(
        category="linear",
        symbol=symbol,
    )
    price = tiker['result']['list'][0]['lastPrice']
    return float(price)

# Reopen buy/sell orders
def reopen(symbol, side):
    try:
        price = float(getPrice(symbol))
        open_position(price, symbol, side)
    except Exception as e:
        print(f"Error reopening orders: {e}")

def verify():
    best = fetch_table_data()
    side = 'Buy'
    print(best.rate, best.symbol, best.time)
    rate_val = float(best.rate[:-1])
    if(rate_val > 0.04):
        side = 'Sell'
        reopen(best.symbol, side)
    elif(rate_val < -0.04):
        side = 'Buy'
        reopen(best.symbol, side)

ws.execution_stream(callback=sendMessage)

initialize_browser()
schedule.every().hour.at(":10").do(verify)

while True:
    schedule.run_pending()
    time.sleep(1)
