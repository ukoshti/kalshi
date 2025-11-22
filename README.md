# Selenium Web Scraper

A Python script that uses Selenium to scrape webpages, parse HTML, and save data to JSON in a loop.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Install ChromeDriver:
   - Option 1: Use webdriver-manager (automatic):
     ```python
     from selenium.webdriver.chrome.service import Service
     from webdriver_manager.chrome import ChromeDriverManager
     
     service = Service(ChromeDriverManager().install())
     driver = webdriver.Chrome(service=service, options=chrome_options)
     ```
   
   - Option 2: Download manually from https://chromedriver.chromium.org/
     - Make sure it's in your PATH or specify the path in the script

## Usage

1. Edit `scraper.py`:
   - Update the `urls` list with the websites you want to scrape
   - Modify the `scrape_page()` function to extract the specific HTML elements you need
   - Adjust `loop_interval` to set the delay between loops
   - Set `max_iterations` to limit the number of loops (or None for infinite)

2. Run the scraper:
```bash
python scraper.py
```

## Customization

### Extracting Specific Elements

Modify the `scrape_page()` function to extract specific HTML elements:

```python
# By CSS selector
element = driver.find_element(By.CSS_SELECTOR, ".class-name")

# By ID
element = driver.find_element(By.ID, "element-id")

# By XPath
element = driver.find_element(By.XPATH, "//div[@class='example']")

# Multiple elements
elements = driver.find_elements(By.TAG_NAME, "div")
```

### Example: Scraping a News Site

```python
def scrape_page(driver, url):
    driver.get(url)
    
    data = {
        "url": url,
        "title": driver.title,
        "articles": []
    }
    
    # Find all article elements
    articles = driver.find_elements(By.CLASS_NAME, "article")
    
    for article in articles:
        try:
            title = article.find_element(By.TAG_NAME, "h2").text
            link = article.find_element(By.TAG_NAME, "a").get_attribute("href")
            data["articles"].append({"title": title, "link": link})
        except NoSuchElementException:
            continue
    
    return data
```

## Notes

- The script appends data to the JSON file, so each iteration adds to the existing data
- Use `--headless` option to run without opening a browser window
- Be respectful of websites: add appropriate delays and check robots.txt
- Some websites may block automated scraping - consider using proxies or other techniques if needed

