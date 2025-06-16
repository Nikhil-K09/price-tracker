import requests as r
import bs4
from bs4 import BeautifulSoup
import schedule
import time

from pymongo import MongoClient
from datetime import datetime

# Replace with your own MongoDB URI
client = MongoClient("mongodb+srv://mongodb.net/")

db = client["amazon_tracker"]        # Database
collection = db["price_history"]     # Collection


product_list = ['B0C1GX5RVW', 'B0C9J97S7Q']  # Add ASINs here
base_url = 'https://www.amazon.in'
url = 'https://www.amazon.in/dp/'

headers = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def track_prices():
    base_response = r.get(base_url, headers=headers)
    cookies = base_response.cookies

    for prod in product_list:
        product_url = url + prod
        response = r.get(product_url, headers=headers, cookies=cookies)

        soup = BeautifulSoup(response.text, 'lxml')

        # Get price parts
        price_whole = soup.find('span', {'class': 'a-price-whole'})
        price_decimal = soup.find('span', {'class': 'a-price-fraction'})

        if price_whole and price_decimal:
            final_price = price_whole.text.strip() + '.' + price_decimal.text.strip()
        elif price_whole:
            final_price = price_whole.text.strip()  # fallback
        else:
            final_price = "Price not found"
        

        data = {
            "asin": prod,
            "url": product_url,
            "price": final_price,
            "timestamp": datetime.now()
        }
        collection.insert_one(data)

        print(f"{product_url} --> ₹{final_price}")


track_prices()

# Schedule the job
# schedule.every(1).minutes.do(track_prices)

# # Keep running
# while True:
#     schedule.run_pending()
#     time.sleep(1)

