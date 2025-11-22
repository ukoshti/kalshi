"""
Selenium Web Scraper - Scrapes DraftKings NBA moneylines and saves to JSON
"""

import json
import time
import os
import signal
import sys
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup


def setup_driver():
    """Setup and return a Chrome WebDriver instance"""
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--headless")  # Run in headless mode for speed
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
    # Disable images and other resources for faster loading
    prefs = {
        "profile.managed_default_content_settings.images": 2,
        "profile.default_content_setting_values.notifications": 2,
    }
    chrome_options.add_experimental_option("prefs", prefs)
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    # Set implicit wait to 0 to avoid any waiting
    driver.implicitly_wait(0)
    # Set page load timeout to avoid waiting for slow pages
    driver.set_page_load_timeout(5)
    return driver


def scrape_draftkings_page(driver, url, reload_page=False):
    """
    Scrape DraftKings sportsbook page for NBA moneyline odds only

    Args:
        driver: Selenium WebDriver instance
        url: URL to scrape
        reload_page: If True, reload the page. If False, just scrape current page content.

    Returns:
        dict: Extracted moneyline data from the page
    """
    try:
        if reload_page:
            driver.get(url)

        data = {
            "timestamp": time.time(),
            "url": url,
            "games": [],
        }

        # Get page HTML once and parse with BeautifulSoup (much faster than DOM queries)
        html = driver.page_source
        soup = BeautifulSoup(html, "lxml")

        # Find all buttons first, then get unique parent containers
        buttons = soup.select('[data-testid="button-odds-market-board"]')

        # Get unique game containers by finding parents of buttons
        seen_containers = set()
        game_containers = []

        for button in buttons:
            # Check if this button is a moneyline (no points/title)
            button_html = str(button)
            has_points = "button-points-market-board" in button_html
            has_title = "button-title-market-board" in button_html

            if not has_points and not has_title:
                # Find parent container with cb-static-parlay class
                parent = button.find_parent(
                    class_=lambda x: x and "cb-static-parlay" in str(x)
                )
                if parent:
                    # Use a unique identifier for the container
                    container_id = id(parent)
                    if container_id not in seen_containers:
                        seen_containers.add(container_id)
                        game_containers.append(parent)

        # Parse each game event - extract all data for each game in order
        for container in game_containers:
            try:
                # Extract teams for this game
                team_elements = container.select(
                    ".cb-market__label-inner.cb-market__label-inner--parlay"
                )
                if len(team_elements) < 2:
                    team_elements = container.select(".cb-market__label-inner")

                teams = []
                for team_elem in team_elements:
                    team_text = team_elem.get_text(strip=True)
                    if (
                        team_text
                        and len(team_text) > 2
                        and team_text not in ["at", "AT", "vs", "VS"]
                    ):
                        teams.append(team_text)

                if len(teams) < 2:
                    continue

                # Extract moneylines for this game - buttons at positions 3 and 6 (indices 2 and 5)
                odds_buttons = container.select(
                    '[data-testid="button-odds-market-board"]'
                )

                moneylines = []
                # Check buttons - positions 3 and 6 first (indices 2 and 5)
                for i in [2, 5]:
                    if i < len(odds_buttons):
                        button = odds_buttons[i]
                        button_html = str(button)
                        has_points = "button-points-market-board" in button_html
                        has_title = "button-title-market-board" in button_html
                        button_text = button.get_text(strip=True)

                        if not has_points and not has_title and button_text:
                            moneylines.append(button_text.replace("−", "-"))

                # Fallback: find all buttons with no points/title
                if len(moneylines) < 2:
                    moneylines = []
                    for button in odds_buttons:
                        button_html = str(button)
                        has_points = "button-points-market-board" in button_html
                        has_title = "button-title-market-board" in button_html
                        button_text = button.get_text(strip=True)

                        if not has_points and not has_title and button_text:
                            moneylines.append(button_text.replace("−", "-"))
                    if len(moneylines) >= 2:
                        moneylines = moneylines[-2:]

                # Extract game date/time for this game
                game_date = None
                date_elem = container.select_one(
                    '[data-testid="cb-event-cell__start-time"]'
                )
                if not date_elem:
                    date_elem = container.select_one(".cb-event-cell__start-time")
                if not date_elem:
                    # Check parent container
                    parent = container.find_parent(
                        class_=lambda x: x and "cb-static-parlay" in x
                    )
                    if parent:
                        date_elem = parent.select_one(
                            '[data-testid="cb-event-cell__start-time"]'
                        )

                if date_elem:
                    date_text = date_elem.get_text(strip=True)
                    if date_text and len(date_text) > 5:
                        game_date = date_text

                # Create game entry with all data for this game
                if len(teams) >= 2 and len(moneylines) >= 1:
                    game_data = {
                        "team1": teams[0],
                        "team2": teams[1],
                    }
                    if len(moneylines) >= 2:
                        game_data["team1_moneyline"] = moneylines[0]
                        game_data["team2_moneyline"] = moneylines[1]
                    elif len(moneylines) == 1:
                        game_data["team1_moneyline"] = moneylines[0]

                    if game_date:
                        game_data["draftkings_start_time"] = game_date

                    data["games"].append(game_data)

            except Exception:
                continue

        # Remove duplicates
        seen = set()
        unique_games = []
        for game in data["games"]:
            team1 = game.get("team1", "")
            team2 = game.get("team2", "")
            ml1 = game.get("team1_moneyline", "")
            ml2 = game.get("team2_moneyline", "")
            key = tuple(sorted([team1, team2])) + tuple(sorted([ml1, ml2]))
            if key not in seen:
                seen.add(key)
                unique_games.append(game)

        data["games"] = unique_games
        return data

    except TimeoutException:
        return {
            "timestamp": time.time(),
            "url": url,
            "games": [],
        }
    except Exception as e:
        return {
            "timestamp": time.time(),
            "url": url,
            "games": [],
        }


def save_to_json(data, filename="scraped_data.json"):
    """Save or append data to a JSON file in a date-based folder"""
    try:
        # Create folder path with today's date
        today = datetime.now().strftime("%Y-%m-%d")
        folder_path = os.path.join(today)

        # Create directory if it doesn't exist
        os.makedirs(folder_path, exist_ok=True)

        # Full file path
        filepath = os.path.join(folder_path, filename)

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    existing_data = json.loads(content)
                else:
                    existing_data = []
        except (FileNotFoundError, json.JSONDecodeError):
            existing_data = []

        if not isinstance(existing_data, list):
            existing_data = [existing_data]

        if isinstance(data, list):
            existing_data.extend(data)
        else:
            existing_data.append(data)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(existing_data, f, indent=2, ensure_ascii=False)

        print(f"Data saved to {filepath}")

    except Exception as e:
        print(f"Error saving to JSON: {str(e)}")


def get_jsonl_filepath(filename="scraped_data.jsonl"):
    """Get the filepath for JSONL file based on today's date"""
    today = datetime.now().strftime("%Y-%m-%d")
    folder_path = os.path.join(today)
    os.makedirs(folder_path, exist_ok=True)
    return os.path.join(folder_path, filename)


def write_stop_marker(filename="scraped_data.jsonl"):
    """Write a stop marker to the JSONL file"""
    try:
        filepath = get_jsonl_filepath(filename)
        stop_marker = {
            "timestamp": time.time(),
            "message": "stop",
        }
        with open(filepath, "a", encoding="utf-8") as f:
            json_line = json.dumps(stop_marker, ensure_ascii=False)
            f.write(json_line + "\n")
        print(f"Stop marker written to {filepath}")
    except Exception as e:
        print(f"Error writing stop marker: {str(e)}")


def write_start_marker(filename="scraped_data.jsonl"):
    """Write a start marker to the JSONL file"""
    try:
        filepath = get_jsonl_filepath(filename)
        start_marker = {
            "timestamp": time.time(),
            "message": "start",
        }
        with open(filepath, "a", encoding="utf-8") as f:
            json_line = json.dumps(start_marker, ensure_ascii=False)
            f.write(json_line + "\n")
        print(f"Start marker written to {filepath}")
    except Exception as e:
        print(f"Error writing start marker: {str(e)}")


def save_to_jsonl(data, filename="scraped_data.jsonl"):
    """Save data to a JSONL file (JSON Lines) where each line is a single snapshot"""
    try:
        filepath = get_jsonl_filepath(filename)

        # Convert data to list if needed
        if isinstance(data, list):
            data_list = data
        else:
            data_list = [data]

        # Append each snapshot as a single line
        with open(filepath, "a", encoding="utf-8") as f:
            # Write data snapshots
            for snapshot in data_list:
                json_line = json.dumps(snapshot, ensure_ascii=False)
                f.write(json_line + "\n")

        print(f"Data saved to {filepath}")

    except Exception as e:
        print(f"Error saving to JSONL: {str(e)}")


def main():
    """Main loop - scrapes pages and saves to JSON"""
    urls = ["https://sportsbook.draftkings.com/leagues/basketball/ncaab"]
    output_file = "draftkings_nba_data.json"
    max_iterations = 1000
    reload_interval = 60  # Reload page every 60 seconds (every 60 iterations)

    driver = None
    iteration = 0
    jsonl_filename = output_file.replace(".json", ".jsonl")

    # Set up signal handlers for graceful shutdown
    def signal_handler(sig, frame):
        print("\nReceived termination signal")
        write_stop_marker(jsonl_filename)
        if driver:
            driver.quit()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        driver = setup_driver()
        # Write start marker when logging begins
        write_start_marker(jsonl_filename)

        while True:
            iteration += 1
            print(f"\n=== Iteration {iteration} ===")

            all_data = []

            for url in urls:
                print(f"Scraping: {url}")
                # Reload page every minute (every reload_interval iterations) or on first iteration
                should_reload = (iteration == 1) or (iteration % reload_interval == 0)
                data = scrape_draftkings_page(driver, url, reload_page=should_reload)
                all_data.append(data)

            # Also save as JSONL (one snapshot per line)
            save_to_jsonl(all_data, jsonl_filename)

            if max_iterations and iteration >= max_iterations:
                print(f"Reached maximum iterations ({max_iterations})")
                break

            # Wait 1 second before next iteration
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nStopped by user")
        jsonl_filename = output_file.replace(".json", ".jsonl")
        write_stop_marker(jsonl_filename)
    except Exception as e:
        print(f"Error in main loop: {str(e)}")
        jsonl_filename = output_file.replace(".json", ".jsonl")
        write_stop_marker(jsonl_filename)
    finally:
        if driver:
            driver.quit()
        print("Driver closed")
        # Write stop marker on normal completion too
        jsonl_filename = output_file.replace(".json", ".jsonl")
        write_stop_marker(jsonl_filename)


if __name__ == "__main__":
    main()
