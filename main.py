from playwright.sync_api import sync_playwright
from keep_alive import keep_alive
keep_alive()

# Scriptul Playwright
def fetch_table_data():
    with sync_playwright() as p:
        # Pornește browserul headless
        browser = p.chromium.launch(headless=False)  # Setează la True dacă nu vrei să vezi browserul
        page = browser.new_page()

        # Deschide URL-ul
        url = "https://bybit.com/en/announcement-info/fund-rate/"
        page.goto(url)

        # Așteaptă încărcarea tabelului
        page.wait_for_selector("table")

        # Apasă pe al cincilea <th> pentru a sorta tabelul
        page.click("table thead tr th:nth-child(5)")
        page.wait_for_timeout(1000)  # Pauză mică pentru a permite sortarea

        # Extrage datele din prima linie, coloanele 1, 4 și 5
        contract_name = page.locator("table tbody tr:nth-child(2) td:nth-child(1)").inner_text()
        estimated_funding_rate = page.locator("table tbody tr:nth-child(2) td:nth-child(4)").inner_text()
        current_upper_lower_limit = page.locator("table tbody tr:nth-child(2) td:nth-child(5)").inner_text()

        print("Cea mai profitabila:")
        print(f"Contract Name: {contract_name}, Estimated Funding Rate: {estimated_funding_rate}, Upper/Lower Limit: {current_upper_lower_limit}")

        # Apasă pe al patrulea <th> pentru a sorta tabelul
        page.click("table thead tr th:nth-child(4)")
        page.wait_for_timeout(1000)  # Pauză mică pentru a permite sortarea

        # Extrage datele din prima linie, coloanele 1, 4 și 5 (după sortare pe coloana 4)
        contract_name = page.locator("table tbody tr:nth-child(2) td:nth-child(1)").inner_text()
        estimated_funding_rate = page.locator("table tbody tr:nth-child(2) td:nth-child(4)").inner_text()
        current_upper_lower_limit = page.locator("table tbody tr:nth-child(2) td:nth-child(5)").inner_text()

        print("\nCea mai apropiata:")
        print(f"Contract Name: {contract_name}, Estimated Funding Rate: {estimated_funding_rate}, Upper/Lower Limit: {current_upper_lower_limit}")

        # Închide browserul
        browser.close()

# Rulează funcția
fetch_table_data()
