import schedule
import time
from datetime import datetime
from pybit.unified_trading import HTTP
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from keep_alive import keep_alive
keep_alive()

class Row:
  def __init__(self, symbol, time, rate):
    self.symbol = symbol
    self.time = time
    self.rate = rate

api_key = "FUohm9A4TvvCSChSG7"
api_secret = "tJAfR9ddpKCJ3ubOXdBViuprX8R9tU3V6B1v"

token = "7877883188:AAGdqomhdm9HdOkyybIrHWfw_kXVf9u-9Tc"
chat_id = "6527491132"

# Initialize HTTP session and WebSocket
session = HTTP(demo=True, api_key=api_key, api_secret=api_secret)

def handle_wallet(message):
    avi = message.get('totalAvailableBalance', 'Valoare indisponibilă')
    mar = message.get('totalMarginBalance', 'Valoare indisponibilă')
    return(f'Available: {round(float(avi), 2)}, WithMargin: {round(float(mar), 2)}')

# Function to send Messages in Telegram
def sendMessage():
    try:
        wallet = session.get_wallet_balance(accountType="UNIFIED")
        message = wallet["result"]["list"][0]
        try: 
            url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={handle_wallet(message)}"
            requests.get(url)
        except Exception as e:
            print(f"Error seting Wallet Message: {e}")
    except Exception as e:
        print(f"Error sending Wallet Message: {e}")

# Scriptul Playwright
def fetch_table_data():
    # Configurează driverul Selenium (exemplu cu Chrome)
    options = webdriver.FirefoxOptions()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')

    driver = webdriver.Firefox(options=options)
    driver.get("https://bybit.com/en/announcement-info/fund-rate/")

    try:
        # Așteaptă încărcarea tabelului
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table"))
        )

        def get_rows():
            tbody = driver.find_element(By.CSS_SELECTOR, "table tbody")
            return tbody.find_elements(By.TAG_NAME, "tr")

        def get_row_data(row):
            cells = row.find_elements(By.TAG_NAME, "td")
            return Row(cells[0].text, cells[3].text, cells[4].text)

        # Sortează tabelul după al cincilea <th>
        th_fifth = driver.find_element(By.CSS_SELECTOR, "table thead tr th:nth-child(5)")
        th_fifth.click()
        time.sleep(1)  # Pauză pentru sortare

        rows = get_rows()
        negative = get_row_data(rows[1])

        # Sortează tabelul din nou după al cincilea <th>
        th_fifth.click()
        time.sleep(1)

        rows = get_rows()
        positive = get_row_data(rows[1])

        # Sortează după al patrulea <th>
        th_fourth = driver.find_element(By.CSS_SELECTOR, "table thead tr th:nth-child(4)")
        th_fourth.click()
        time.sleep(1)

        rows = get_rows()
        first_row_time = rows[1].find_elements(By.TAG_NAME, "td")[3].text
        max_rate_row = None
        max_rate_value = float('-inf')

        for row in rows[1:]:
            cells = row.find_elements(By.TAG_NAME, "td")
            time_cell = cells[3].text

            if time_cell == first_row_time:
                symbol = cells[0].text
                rate_text = cells[4].text
                rate = float(rate_text.replace('%', '').replace('-', ''))

                if rate > max_rate_value:
                    max_rate_value = rate
                    max_rate_row = Row(symbol, time_cell, rate_text)

        def parse_rate(rate_text):
            return float(rate_text.replace('%', '').replace('-', ''))

        if positive.time == max_rate_row.time == negative.time:
            if parse_rate(positive.rate) <= parse_rate(negative.rate):
                return negative
            else:
                return positive
        elif positive.time == max_rate_row.time != negative.time:
            if parse_rate(positive.rate) <= parse_rate(max_rate_row.rate):
                return max_rate_row
            else:
                return positive
        elif negative.time == max_rate_row.time != positive.time:
            if parse_rate(negative.rate) <= parse_rate(max_rate_row.rate):
                return max_rate_row
            else:
                return negative
        else:
            return max_rate_row

    finally:
        driver.quit()

# Function to open a position with buy/sell orders
def open_position(price, symbol, side): 
    qty = 202/price
    takeProfit = 0.0033
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
        # Place Buy Order
        order = session.place_order(
            category="linear",
            symbol=symbol,
            side=side,
            orderType="Market",
            qty=round(qty),
            price=price,
            positionIdx=idx,
        )
        time.sleep(110)
        take = session.set_trading_stop(
            category="linear",
            symbol=symbol,
            positionIdx=idx,
            stopLoss=stopPrice,
            takeProfit=takePrice,
            tpslMode='Partial',
            tpSize=str(round(qty)),
            slSize=str(round(qty)),
        )
    except Exception as e:
        print(f"Error placing BUY order: {e}")

    try:
        sendMessage()
    except Exception as e:
        print(f"Error send Message: {e}")

# Get the latest price for the symbol
def getPrice(symbol):
    tiker = session.get_tickers(
        category="linear",
        symbol=symbol,
    )
    price = tiker['result']['list'][0]['lastPrice']
    return float(price)

# Cancel all open orders for the symbol
def closeOrders():
    session.cancel_all_orders(
        category="linear",
        orderFilter='Order',
        settleCoin="USDT"
    )

# Reopen buy/sell orders after closing existing ones
def reopen(symbol, side):
    try:
        closeOrders()
    except Exception as e:
        print(f"Error closing orders: {e}")
    
    try:
        price = float(getPrice(symbol))
        open_position(price, symbol, side)
    except Exception as e:
        print(f"Error reopening orders: {e}")

def verify():
    best = fetch_table_data()
    fundingTime = datetime.strptime(best.time, '%Y-%m-%d %H:%M:%S').hour
    timeCurrent = datetime.utcnow().hour
    if fundingTime == 0: fundingTime = 24
    side = 'Buy'
    print(best.rate, best.symbol)
    if(fundingTime == (timeCurrent + 1)):
        rate_val = float(best.rate[:-1])
        if(rate_val > 0.25):
            side = 'Sell'
            reopen(best.symbol, side)
        elif(rate_val < -0.25):
            side = 'Buy'
            reopen(best.symbol, side)

# Programează funcția să ruleze la începutul fiecărei ore
schedule.every().minute.at(":58").do(verify)

while True:
    schedule.run_pending()
