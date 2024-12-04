import requests
import json
import pandas as pd
from flask import Flask, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
import matplotlib.pyplot as plt
import seaborn as sns
import os

# Flask app and database setup
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///armchairs.db'  # Using SQLite for simplicity
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Database model for Armchairs
class Armchair(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    current_price = db.Column(db.Float)
    previous_price = db.Column(db.Float)
    price_change = db.Column(db.Float)

    def __init__(self, name, current_price, previous_price, price_change):
        self.name = name
        self.current_price = current_price
        self.previous_price = previous_price
        self.price_change = price_change

# Create the database tables
with app.app_context():
    db.create_all()

# Function to fetch and process armchair data
def fetch_and_process_data():
    url = 'https://sik.search.blue.cdtapps.com/us/en/search?c=listaf&v=20240110'
    payload = '''{"searchParameters":{"input":"16239","type":"CATEGORY"},"optimizely":{"listing_3050_ablate_image_hover_effect":"b","sik_null_test_20241113_default":"b"},"isUserLoggedIn":false,"components":[{"component":"PRIMARY_AREA","columns":4,"types":{"main":"PRODUCT","breakouts":["PLANNER","LOGIN_REMINDER","MATTRESS_WARRANTY"]},"filterConfig":{"max-num-filters":2},"sort":"RELEVANCE","window":{"offset":12,"size":100}}]}'''
    headers = {
        'accept': '*/*',
        'content-type': 'text/plain;charset=UTF-8',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
    }

    r = requests.post(url, data=payload, headers=headers)
    data = json.loads(r.content)
    
    # Normalize the JSON data to create a DataFrame
    try:
        df = pd.json_normalize(data['results'][0]['items'])
        # Clean and process the data
        df['product.salesPrice.current.wholeNumber'] = df.get('product.salesPrice.current.wholeNumber', 0).fillna(0)
        df['product.salesPrice.previous.wholeNumber'] = df.get('product.salesPrice.previous.wholeNumber', 0).fillna(0)
        df['product.salesPrice.current.wholeNumber'] = pd.to_numeric(df['product.salesPrice.current.wholeNumber'], errors='coerce')
        df['product.salesPrice.previous.wholeNumber'] = pd.to_numeric(df['product.salesPrice.previous.wholeNumber'], errors='coerce')
        df['price_change'] = df['product.salesPrice.previous.wholeNumber'] - df['product.salesPrice.current.wholeNumber']
        
        # Store the results in the database
        with app.app_context():
            for _, row in df.iterrows():
                armchair = Armchair(
                    name=row.get('product.name', 'Unknown'),
                    current_price=row['product.salesPrice.current.wholeNumber'],
                    previous_price=row['product.salesPrice.previous.wholeNumber'],
                    price_change=row['price_change']
                )
                db.session.add(armchair)
            db.session.commit()
    except KeyError:
        print("Unexpected response structure. Check the API response format.")

# Flask route to get armchair data
@app.route('/armchairs', methods=['GET'])
def get_armchairs():
    armchairs = Armchair.query.all()
    result = [{"name": armchair.name, "current_price": armchair.current_price, "previous_price": armchair.previous_price, "price_change": armchair.price_change} for armchair in armchairs]
    return jsonify(result)

# Flask route for price change visualization
@app.route('/price-change-chart', methods=['GET'])
def price_change_chart():
    # Query data from the database
    armchairs = Armchair.query.all()
    df = pd.DataFrame([{
        'name': armchair.name,
        'price_change': armchair.price_change
    } for armchair in armchairs])
    
    # Top 10 armchairs with the highest price change
    top_10_price_change = df.nlargest(10, 'price_change')
    
    plt.figure(figsize=(10, 6))
    sns.barplot(x='price_change', y='name', data=top_10_price_change, palette='coolwarm')
    plt.title('Top 10 Armchairs with Highest Price Change')
    plt.xlabel('Price Change ($)')
    plt.ylabel('Product Name')
    plt.tight_layout()
    
    chart_path = 'price_change_chart.png'
    plt.savefig(chart_path)  # Save chart as image
    return send_file(chart_path, mimetype='image/png')

# Main function to run the application and fetch data
if __name__ == "__main__":
    fetch_and_process_data()  # Fetch and process data on app start
    app.run(debug=True)
