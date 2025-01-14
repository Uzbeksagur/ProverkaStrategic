from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

options = webdriver.FirefoxOptions()

options.add_argument("--headless")

driver = webdriver.Firefox(options=options)

driver.get("https://www.bybit.com/en/announcement-info/fund-rate/")

driver.implicitly_wait(0.5)

message = driver.find_element(By.CSS_SELECTOR, "table thead tr th:nth-child(5)")

print(message.text)

driver.quit()