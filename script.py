from playwright.sync_api import sync_playwright
import schedule
from pybit.unified_trading import HTTP
from pybit.unified_trading import WebSocket
import requests
import time
import sys
sys.stdout.reconfigure(encoding='utf-8')
import csv
from datetime import datetime
import os

playwright = None
browser = None
page = None

class Row:
    def __init__(self, symbol, interval, time, rate):
        self.symbol = symbol
        self.interval = interval
        self.time = time
        self.rate = rate

# Configuration
CONFIG = {
    'excluded_coins': ['USDEUSDT'],  # Coins to exclude
    'check_times': [
        { 'time': ':01', 'row_index': 11, 'take_profit': 0.015, 'stop_loss': 0.1 },
    ]
}

api_key = "lVkoSAcz88N7Rm9Z2F"
api_secret = "XrMMIpX3q2V7CiePaMMdiZYrwmOn285zUbbo"
token = "7035583013:AAHki-p3K10U23zFi3IqOYT92LscE_-x0JE"
chat_id = "7308714189"

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

        if message['createType'] == 'CreateByUser' and message['side'] in ['Buy', 'Sell']:
            symbol = message['symbol']
            exec_qty = float(message['execQty'])
            side = message['side']
            exec_price = float(message['execPrice'])
            exec_fee = float(message['execFee'])

            open_positions.append({
                'symbol': symbol,
                'execQty': exec_qty,
                'side': side,
                'execPrice': exec_price,
                'execFee': exec_fee
            })

        elif message['createType'] in ['CreateByClosing', 'CreateByPartialTakeProfit', 
                                     'CreateByPartialStopLoss', 'CreateByTakeProfit', 'CreateByStopLoss']:
            symbol = message['symbol']
            close_qty = float(message['execQty'])
            close_price = float(message['execPrice'])
            close_fee = float(message['execFee'])

            for idx, open_position in enumerate(open_positions):
                if (open_position['symbol'] == symbol and
                    open_position['execQty'] == close_qty):
                    open_fee = open_position['execFee']
                    open_price = open_position['execPrice']
                    side = open_position['side']
                    quantity = close_qty

                    if side == 'Buy':
                        profit = (close_price - open_price) * quantity - (close_fee + open_fee)
                    else:
                        profit = (open_price - close_price) * quantity - (close_fee + open_fee)

                    profit_message = f"Poziția a fost închisă. Profit: {profit:.2f} USDT ({symbol})"
                    send_telegram_message(profit_message)

                    open_position['execQty'] -= close_qty
                    if open_position['execQty'] <= 0:
                        open_positions.pop(idx)
                    break
    except Exception as e:
        print(f"Error sending message: {e}")

def initialize_browser():
    global playwright, browser, page
    playwright = sync_playwright().start()
    browser = playwright.firefox.launch()
    page = browser.new_page()
    url = "https://bybit.com/en/announcement-info/fund-rate/"
    page.goto(url, timeout=90000)
    page.wait_for_selector("table")

def fetch_table_data(row_index):
    global page
    if not page:
        initialize_browser()

    page.click("table thead tr th:nth-child(4)")
    page.wait_for_timeout(1000)
    page.click("table thead tr th:nth-child(5)")
    page.wait_for_timeout(1000)

    symbol = page.locator(f"table tbody tr:nth-child({row_index}) td:nth-child(1)").inner_text()
    
    if symbol in CONFIG['excluded_coins']:
        print(f"Skipping excluded coin: {symbol}")
        return None

    best = Row(
        symbol,
        page.locator(f"table tbody tr:nth-child({row_index}) td:nth-child(2)").inner_text(),
        page.locator(f"table tbody tr:nth-child({row_index}) td:nth-child(4)").inner_text(),
        page.locator(f"table tbody tr:nth-child({row_index}) td:nth-child(5)").inner_text(),
    )
    return best

def open_position(price, best, take_profit, stop_loss):
    qty = 202/price
    idx = 1
    csv_file = "logs.csv"
    stopPrice = price * (1 - stop_loss)
    takePrice = price * (1 + take_profit)

    try:
        session.place_order(
            category="linear",
            symbol=best.symbol,
            side='Buy',
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

    try:
        now = datetime.now()
        file_exists = os.path.isfile(csv_file)

        with open(csv_file, mode="a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            if not file_exists:
                writer.writerow(["OpenT", "FundT", "IntervalT", "DiferenceT", "Symbol", "Price", 'Rate', 'TakeProfit', 'StopLoss'])

            best_time = datetime.strptime(best.time, "%Y-%m-%d %H:%M:%S")
            dife = best_time - now
            total_seconds = int(dife.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            dife_str = f"{hours:02d}:{minutes:02d}"

            writer.writerow([now.strftime("%Y-%m-%d %H:%M:%S"), best.time, best.interval, dife_str, 
                           best.symbol, price, best.rate, take_profit, stop_loss])
    except Exception as e:
        print(f"Error register in file: {e}")

def getPrice(symbol):
    tiker = session.get_tickers(
        category="linear",
        symbol=symbol,
    )
    price = tiker['result']['list'][0]['lastPrice']
    return float(price)

def verify(check_time_config):
    row_index = check_time_config['row_index']
    take_profit = check_time_config['take_profit']
    stop_loss = check_time_config['stop_loss']
    
    best = fetch_table_data(row_index)
    if best:
        print(best.rate, best.symbol, best.time)
        try:
            price = float(getPrice(best.symbol))
            open_position(price, best, take_profit, stop_loss)
        except Exception as e:
            print(f"Error reopening orders: {e}")

ws.execution_stream(callback=sendMessage)
initialize_browser()

# Schedule checks at multiple times with their configurations
for check_time_config in CONFIG['check_times']:
    schedule.every().hour.at(check_time_config['time']).do(verify, check_time_config=check_time_config)

while True:
    schedule.run_pending()
    time.sleep(1)
