

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from pymongo import MongoClient
from datetime import datetime
from urllib.parse import quote_plus
import re
import time

# ========== MongoDB Setup ==========
username = quote_plus("PunithKumar")  # Encode special characters if any
password = quote_plus("Kkk@162114")
mongo_uri = f"mongodb+srv://admin:nikhil@cluster0.yjnzzzx.mongodb.net/"
client = MongoClient(mongo_uri)
db = client["price_tracker"]
collection = db["amazon_prices"]

# ========== Amazon URLs ==========
amazon_urls = [
    "https://www.amazon.in/ref=PS5BAU25QCPS5digital/dp/B0CY5QW186/?_encoding=UTF8&ref_=pd_hp_d_atf_unk",
    "https://www.amazon.in/Sony-Dualsense-Charging-Playstation5-Multicolor/dp/B08FVMT8QN/ref=pd_bxgy_thbs_d_sccl_2/260-3150565-6593854?psc=1"
]

# ========== Extract Product IDs ==========
product_ids = []
for url in amazon_urls:
    match = re.search(r"/dp/([A-Z0-9]+)/?", url)
    if match:
        product_ids.append(match.group(1))

# ========== Setup Selenium ==========
options = Options()
options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)



def remove_duplicates(lst):
    seen = set()
    return [x for x in lst if not (x in seen or seen.add(x))]

# ========== Track Prices ==========
for pid in product_ids:
    url = f"https://www.amazon.in/dp/{pid}"
    driver.get(url)
    time.sleep(3)

    soup = BeautifulSoup(driver.page_source, "lxml")
    price_tag = soup.find(class_="a-price-whole")
    name = soup.find(id="productTitle")

    if price_tag and name:
        price = price_tag.text.strip().replace(",", "")
        pname = name.text.strip()
        data = {
            "product_id": pid,
            "product_name": pname,
            "price": price,
            "timestamp": datetime.now()
        }
        collection.insert_one(data)
        print(f"[LOGGED] {pname} | ₹{price}")
    else:
        print(f"[ERROR] Could not fetch price or name for product ID: {pid}")

driver.quit()
