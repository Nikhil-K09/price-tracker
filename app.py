# Project: Amazon Price Tracker Web App
# Features: User Auth, Product Tracking, Email Alerts, Scheduler

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_pymongo import PyMongo
from flask_mail import Mail, Message
from apscheduler.schedulers.background import BackgroundScheduler
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
from datetime import datetime
import re, time, os


app = Flask(__name__)
app.secret_key = 'supersecretkey'

# ===== MongoDB Setup =====
username = quote_plus("PunithKumar")  # Encode special characters if any
password = quote_plus("Kkk@162114")
mongo_uri = f"mongodb+srv://{username}:{password}@cluster0.szcharl.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

app.config["MONGO_URI"] = mongo_uri
mongo = PyMongo(app)

# ===== Email Setup =====
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = '<your-email>'
app.config['MAIL_PASSWORD'] = '<your-email-password>'
mail = Mail(app)

# ===== Util Functions =====
def extract_product_id(url):
    match = re.search(r"/dp/([A-Z0-9]+)/?", url)
    return match.group(1) if match else None

def remove_duplicates(lst):
    seen = set()
    return [x for x in lst if not (x in seen or seen.add(x))]

# ===== Auth Routes =====
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        session['user'] = email
        mongo.db.users.update_one({"_id": email}, {"$setOnInsert": {"product_ids": []}}, upsert=True)
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ===== Dashboard =====
@app.route('/')
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    user = mongo.db.users.find_one({"_id": session['user']})
    products = []
    for pid in user.get("product_ids", []):
        price_entry = mongo.db.amazon_prices.find_one({"product_id": pid, "user_id": session['user']}, sort=[("timestamp", -1)])
        if price_entry:
            products.append(price_entry)
    return render_template('dashboard.html', products=products)

# ===== Add Product =====
@app.route('/add_product', methods=['POST'])
def add_product():
    if 'user' not in session:
        return redirect(url_for('login'))
    url = request.form['url']
    pid = extract_product_id(url)
    if not pid:
        return "Invalid URL", 400
    user = mongo.db.users.find_one({"_id": session['user']})
    new_list = remove_duplicates(user['product_ids'] + [pid])
    mongo.db.users.update_one({"_id": session['user']}, {"$set": {"product_ids": new_list}})
    return redirect(url_for('dashboard'))

# ===== Scraper and Email Notification =====
def track_prices():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    users = mongo.db.users.find()
    for user in users:
        uid = user['_id']
        for pid in remove_duplicates(user.get('product_ids', [])):
            url = f"https://www.amazon.in/dp/{pid}"
            driver.get(url)
            time.sleep(3)
            soup = BeautifulSoup(driver.page_source, 'lxml')
            price_tag = soup.find(class_="a-price-whole")
            name_tag = soup.find(id="productTitle")

            if price_tag and name_tag:
                price = price_tag.text.strip().replace(",", "")
                name = name_tag.text.strip()
                data = {
                    "user_id": uid,
                    "product_id": pid,
                    "product_name": name,
                    "price": price,
                    "timestamp": datetime.now()
                }
                mongo.db.amazon_prices.insert_one(data)
                # Send email if price is below threshold (example: ₹3000)
                if float(price) < 3000:
                    send_email(uid, name, price, url)
    driver.quit()

def send_email(to, name, price, url):
    msg = Message('Price Drop Alert!', sender=app.config['MAIL_USERNAME'], recipients=[to])
    msg.body = f"Good news! '{name}' is now available for ₹{price}.\nCheck it here: {url}"
    mail.send(msg)

# ===== Scheduler =====
scheduler = BackgroundScheduler()
scheduler.add_job(func=track_prices, trigger="interval", minutes=30)
scheduler.start()

# ===== Run =====
if __name__ == '__main__':
    app.run(debug=True)