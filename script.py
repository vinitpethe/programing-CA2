import requests
import pandas as pd
import sqlite3
import numpy as np

# Define API details
url = 'https://sik.search.blue.cdtapps.com/us/en/search?c=listaf&v=20240110'
payload = '''{"searchParameters":{"input":"16239","type":"CATEGORY"},"optimizely":{"listing_3050_ablate_image_hover_effect":"b","sik_null_test_20241113_default":"b"},"isUserLoggedIn":false,"components":[{"component":"PRIMARY_AREA","columns":4,"types":{"main":"PRODUCT","breakouts":["PLANNER","LOGIN_REMINDER","MATTRESS_WARRANTY"]},"filterConfig":{"max-num-filters":2},"sort":"RELEVANCE","window":{"offset":12,"size":100}}]}'''
headers = {
    'accept': '/',
    'content-type': 'text/plain;charset=UTF-8',
    'user-agent': 'Mozilla/5.0'
}

# Fetch data
response = requests.post(url, data=payload, headers=headers)
data = response.json()

# Normalize JSON into a DataFrame
df = pd.json_normalize(data['results'][0]['items'])

# Feature Engineering
if 'product.salesPrice.current.wholeNumber' in df.columns and 'product.salesPrice.previous.wholeNumber' in df.columns:
    # Handle missing values
    df['product.salesPrice.current.wholeNumber'] = pd.to_numeric(
        df['product.salesPrice.current.wholeNumber'], errors='coerce').fillna(0)
    df['product.salesPrice.previous.wholeNumber'] = pd.to_numeric(
        df['product.salesPrice.previous.wholeNumber'], errors='coerce').fillna(0)
    
    # Create derived features
    df['price_change'] = df['product.salesPrice.previous.wholeNumber'] - df['product.salesPrice.current.wholeNumber']
    df['price_change_percentage'] = np.where(df['product.salesPrice.previous.wholeNumber'] > 0,
                                             (df['price_change'] / df['product.salesPrice.previous.wholeNumber']) * 100, 0)
    
    # Handle outliers
    Q1 = df['price_change'].quantile(0.25)
    Q3 = df['price_change'].quantile(0.75)
    IQR = Q3 - Q1
    df['is_outlier'] = (df['price_change'] < (Q1 - 1.5 * IQR)) | (df['price_change'] > (Q3 + 1.5 * IQR))
else:
    print("Required columns missing!")

# Save to SQLite database
conn = sqlite3.connect('products.db')
df.to_sql('armchairs', conn, if_exists='replace', index=False)
conn.close()

print("Data saved to database.")
