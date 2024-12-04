from flask import Flask, jsonify
import sqlite3

app = Flask(_name_)

# Fetch data from database
def fetch_data():
    conn = sqlite3.connect('products.db')
    query = "SELECT * FROM armchairs"
    df = pd.read_sql(query, conn)
    conn.close()
    return df

@app.route('/products', methods=['GET'])
def get_products():
    """Retrieve all product data."""
    df = fetch_data()
    return df.to_json(orient='records')

@app.route('/products/top_changes', methods=['GET'])
def get_top_price_changes():
    """Retrieve top 10 products by price change."""
    df = fetch_data()
    top_10 = df.nlargest(10, 'price_change')
    return top_10.to_json(orient='records')

@app.route('/products/outliers', methods=['GET'])
def get_outliers():
    """Retrieve products flagged as outliers."""
    df = fetch_data()
    outliers = df[df['is_outlier']]
    return outliers.to_json(orient='records')

if _name_ == '_main_':
    app.run(debug=True)
