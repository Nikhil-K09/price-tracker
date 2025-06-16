from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
from pymongo import MongoClient
from datetime import datetime

from urllib.parse import quote_plus

username = quote_plus("PunithKumar")  # Encode special characters if any
password = quote_plus("Kkk@162114")
mongo_uri = f"mongodb+srv://{username}:{password}@cluster0.szcharl.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(mongo_uri)
db = client["price_tracker"]
collection = db["amazon_prices"]

options = Options()
options.add_argument("--headless")  # comment this line if you want to see the browser
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()), options=options
)
url = "https://www.amazon.in/dp/B0BCFKG49M"

driver.get(url)
time.sleep(3)  # wait for JS to load
soup = BeautifulSoup(driver.page_source, "lxml")
driver.quit()
price_tag = soup.find(class_="a-price-whole")
name = soup.find(id="productTitle")
price = price_tag.text.strip()
pname = name.text.strip()
data = {"product_name": pname, "price": price, "timestamp": datetime.now()}

collection.insert_one(data)
print(f"[LOGGED] {pname} | ₹{price}")
