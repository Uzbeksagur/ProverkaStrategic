from playwright.sync_api import sync_playwright
import schedule
import csv
import time
import os
from datetime import datetime
from pybit.unified_trading import HTTP
from keep_alive import keep_alive
keep_alive()

playwright = None
browser = None
page = None

api_key = "LfjAunj7W0SLLbGa0s"
api_secret = "9uMKJVhFa9NhbPXfxEOfCdLQSn6QZyQtY8pi"
session = HTTP(demo=True, api_key=api_key, api_secret=api_secret)

def initialize_browser():
    global playwright, browser, page
    playwright = sync_playwright().start()
    browser = playwright.firefox.launch()  # Setează `headless=True` dacă nu vrei să vezi browserul
    page = browser.new_page()
    url = "https://bybit.com/en/announcement-info/fund-rate/"
    page.goto(url, timeout=90000)
    page.wait_for_selector("table")  # Așteaptă să se încarce tabelul

def get_price(symbol):
    try:
        ticker = session.get_tickers(category="linear", symbol=symbol)
        price = ticker['result']['list'][0]['lastPrice']
        return float(price)
    except Exception as e:
        print(f"Eroare preluare preț pentru {symbol}: {e}")
        return "N/A"

def fetch_table_data():
    global page
    page.click("table thead tr th:nth-child(4)")
    page.wait_for_timeout(1000)
    page.click("table thead tr th:nth-child(5)")
    page.wait_for_timeout(1000)
    
    rows = page.locator("table tbody tr").all()[1:]
    data = []
    for row in rows:
        symbol = row.locator("td:nth-child(1)").inner_text()
        time = row.locator("td:nth-child(4)").inner_text()
        rate = row.locator("td:nth-child(5)").inner_text()
        price = get_price(symbol)
        side = "Buy" if float(rate.replace('%', '')) > 0 else "Sell"
        data.append([symbol, side, price, rate])
    return data

def save_to_csv(data):
    csv_file = "trades.csv"
    file_exists = os.path.isfile(csv_file)
    
    with open(csv_file, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(["Timestamp", "Symbol", "Side", "Price", "Rate"])
        for row in data:
            writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), *row])

def job():
    data = fetch_table_data()
    save_to_csv(data)

initialize_browser()
# Programare la fiecare 5 minute (ex. 10, 15, 20...)
schedule.every().minute.at(":00").do(job)

while True:
    schedule.run_pending()
    time.sleep(1)
