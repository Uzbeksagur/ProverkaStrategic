from playwright.sync_api import sync_playwright
import schedule
import time
from datetime import datetime
from pybit.unified_trading import HTTP
from pybit.unified_trading import WebSocket
import requests
import os
from keep_alive import keep_alive
keep_alive()

class Row:
  def __init__(self, symbol, time, rate):
    self.symbol = symbol
    self.time = time
    self.rate = rate

api_key = os.environ.get("KEY")
api_secret = os.environ.get("SECRET")

token = os.environ.get("TOKEN")
chat_id = os.environ.get("CHAT")

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
    with sync_playwright() as p:
        print('6')
        # Pornește browserul headless
        browser = p.chromium.launch(headless=True)  # Setează la True dacă nu vrei să vezi browserul
        page = browser.new_page()

        # Deschide URL-ul
        url = "https://bybit.com/en/announcement-info/fund-rate/"
        page.goto(url)

        # Așteaptă încărcarea tabelului
        page.wait_for_selector("table")

        # Apasă pe al patrulea <th> pentru a sorta tabelul
        page.click("table thead tr th:nth-child(4)")
        page.wait_for_timeout(1000)  # Pauză mică pentru a permite sortarea

        # Obține toate rândurile din tabel
        rows = page.locator("table tbody tr")
        row_count = rows.count()

        # Obține ora din primul rând
        first_row_time = rows.nth(1).locator("td:nth-child(4)").inner_text()

        # Variabilă pentru a ține minte linia cu cel mai mare rate
        max_rate_row = None
        max_rate_value = float('-inf')  # Inițializăm cu cel mai mic număr posibil

        # Parcurge toate rândurile care au aceeași oră ca prima linie
        for i in range(1, row_count):  # Începem de la al doilea rând (index 1)
            time = rows.nth(i).locator("td:nth-child(4)").inner_text()

            # Verifică dacă ora curentă este aceeași cu ora primei linii
            if time == first_row_time:
                symbol = rows.nth(i).locator("td:nth-child(1)").inner_text()
                rate_text = rows.nth(i).locator("td:nth-child(5)").inner_text()
                rate = float(rate_text.replace('%', '').replace('-', ''))

                # Actualizează rândul cu cel mai mare rate
                if rate > max_rate_value:
                    max_rate_value = rate
                    max_rate_row = Row(symbol, time, rate_text)

        # Închide browserul
        browser.close()

        # Returnează rândul cu cel mai mare rate
        return max_rate_row

# Function to open a position with buy/sell orders
def open_position(price, symbol, side): 
    qty = 200/price
    takeProfit = 0.0031
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
            orderType="Limit",
            qty=round(qty),
            price=price,
            stopLoss=stopPrice,
            takeProfit=takePrice,
            positionIdx=idx,
            tpslMode='Partial'
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
    print(best.rate)
    if(fundingTime == (timeCurrent + 1)):
        rate_val = float(best.rate[:-1])
        if(rate_val > 0.25):
            side = 'Sell'
            reopen(best.symbol, side)
        elif(rate_val < -0.25):
            side = 'Buy'
            reopen(best.symbol, side)

# Programează funcția să ruleze la începutul fiecărei ore
schedule.every().hour.at(":58").do(verify)

while True:
    schedule.run_pending()
    time.sleep(1)  # Așteaptă 1 secundă între verificări
