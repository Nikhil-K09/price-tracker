from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from pymongo import MongoClient
from datetime import datetime
import time

# ---- MongoDB Setup ----
from urllib.parse import quote_plus

username = quote_plus("")  # Encode special characters if any
password = quote_plus("")
mongo_uri = f"mongodb+srv://mongodb.net/"
client = MongoClient(mongo_uri)
db = client["price_tracker"]
collection = db["flipkart_prices"]

# ---- Selenium Setup ----
options = Options()
options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# ---- Flipkart Product URL ----
url = "https://www.flipkart.com/sony-playstation-5-console-825-gb/p/itm62f0f8b3c0bfb?pid=GMCGHMTYZ8BUBMFB"
driver.get(url)
time.sleep(3)

# ---- Scrape Product Info ----
soup = BeautifulSoup(driver.page_source, 'lxml')
driver.quit()
price_tag = soup.find("div", class_="Nx9bqj CxhGGd")
name_tag = soup.find("span", class_="VU-ZEz")
product_name = name_tag.text.strip()
price = price_tag.text.strip()
data = {
        "product_name": product_name,
        "price": price,
        "timestamp": datetime.now()
    }

collection.insert_one(data)
print(f"[LOGGED] {product_name} | ₹{price}")


