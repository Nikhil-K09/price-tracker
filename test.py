from flask import Flask
from flask_pymongo import PyMongo
from urllib.parse import quote_plus

app = Flask(__name__)

# Safe encoding
username = quote_plus("your-username")
password = quote_plus("your-password")
cluster = "cluster0.mongodb.net"

app.config["MONGO_URI"] = f"mongodb+srv://admin:nikhil@cluster0.yjnzzzx.mongodb.net"
mongo = PyMongo(app)