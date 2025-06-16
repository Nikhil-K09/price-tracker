from flask import Flask, render_template, request, redirect, url_for, session
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
from flask_bcrypt import Bcrypt


app = Flask(__name__)
app.secret_key = 'supersecretkey'
bcrypt = Bcrypt(app)

# ===== MongoDB Setup =====
username = quote_plus("username")  # Encode special characters if any
password = quote_plus("password")
mongo_uri = f"mongodb+srv://admin:nikhil@cluster0.yjnzzzx.mongodb.net/price_tracker"
app.config["MONGO_URI"] = mongo_uri
mongo = PyMongo(app)

# ===== Email Setup =====
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = '<your-email>'  # Example: test@gmail.com
app.config['MAIL_PASSWORD'] = '<your-email-password>'  # App password if 2FA
mail = Mail(app)

# ===== Utility Functions =====
def extract_product_id(url):
    match = re.search(r"/dp/([A-Z0-9]+)/?", url)
    return match.group(1) if match else None

def remove_duplicates(lst):
    seen = set()
    return [x for x in lst if not (x in seen or seen.add(x))]

def scrape_product_data(pid):
    try:
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

        url = f"https://www.amazon.in/dp/{pid}"
        driver.get(url)
        time.sleep(3)
        soup = BeautifulSoup(driver.page_source, 'lxml')
        driver.quit()

        price_tag = soup.find(class_="a-price-whole")
        name_tag = soup.find(id="productTitle")
        if price_tag and name_tag:
            price = price_tag.text.strip().replace(",", "")
            name = name_tag.text.strip()
            return {
                "product_id": pid,
                "product_name": name,
                "price": price
            }
    except Exception as e:
        print(f"Error scraping {pid}: {e}")
    return None

# ===== Auth Routes =====
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = mongo.db.users.find_one({"_id": email})
        if user:
            if bcrypt.check_password_hash(user['password'], password):
                session['user'] = email
                return redirect(url_for('dashboard'))
            else:
                return "Incorrect password", 401
        else:
            # First-time user, register them
            hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
            mongo.db.users.insert_one({
                "_id": email,
                "password": hashed_pw,
                "product_ids": []
            })
            session['user'] = email
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
        price_entry = mongo.db.amazon_prices.find_one(
            {"product_id": pid, "user_id": session['user']},
            sort=[("timestamp", -1)]
        )
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

    # Immediately insert scraped product data to amazon_prices
    product_data = scrape_product_data(pid)
    if product_data:
        product_data.update({
            "user_id": session['user'],
            "timestamp": datetime.now()
        })
        mongo.db.amazon_prices.insert_one(product_data)

    return redirect(url_for('dashboard'))

# ===== Price Tracker =====
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





