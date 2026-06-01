from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time

def run_selenium_task():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    options.binary_location = "/usr/bin/chromium"

    driver = webdriver.Chrome(options=options)

    try:
        driver.get("https://example.com")
        title = driver.title
        print(f"Title: {title}")
        return title
    finally:
        driver.quit()