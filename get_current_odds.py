#!/usr/bin/env python3
"""Run scraper once and extract current moneyline odds"""
import subprocess
import sys
import time
from pathlib import Path

# Run the scraper once
print("Fetching current odds from DraftKings...")
print("This may take 30-60 seconds...\n")

# Import and run scraper once
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime

# Configure Chrome options
options = Options()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)
options.add_argument(
    "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()), options=options
)

try:
    print("Loading page...")
    driver.get("https://sportsbook.draftkings.com/leagues/football/nfl")
    
    print("Waiting for page content...")
    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, ".sportsbook-event-accordion__container")
            )
        )
        print("Found sportsbook-event-accordion__container")
    except TimeoutException:
        print("Original selector not found, trying alternatives...")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(5)
        print("Page loaded, waiting for dynamic content...")
    
    html = driver.page_source
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"draftkings_nfl_{timestamp}.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"HTML saved to {filename}\n")
    
except Exception as e:
    print(f"Error occurred: {e}")
finally:
    driver.quit()

# Now extract the odds
print("Extracting moneyline odds...")
from extract_game_data import extract_cowboys_raiders_odds

game_info = extract_cowboys_raiders_odds(filename)

print("\n" + "="*60)
print("CURRENT MONEYLINE ODDS")
print("="*60)
if game_info.get('odds') and game_info['odds'].get('moneyline'):
    ml = game_info['odds']['moneyline']
    print(f"\nDallas Cowboys: {ml.get('cowboys', 'N/A')}")
    print(f"Las Vegas Raiders: {ml.get('raiders', 'N/A')}")
else:
    print("\nCould not extract moneyline odds from the page.")
    print("The game may not be available or the page structure has changed.")

if game_info.get('game_status'):
    status = game_info['game_status']
    if status.get('game_in_progress'):
        print(f"\nGame Status: IN PROGRESS")
        print(f"Score: Cowboys {status.get('cowboys_score', 'N/A')} - Raiders {status.get('raiders_score', 'N/A')}")
    else:
        print(f"\nGame Status: UPCOMING")

print("\n" + "="*60)

