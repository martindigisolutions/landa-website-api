from flask import Flask, render_template
import sqlite3

app = Flask(__name__)

def get_products():
    conn = sqlite3.connect("../api_db.sqlite3")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, short_description, regular_price, sale_price, stock, image_url FROM products")
    products = cursor.fetchall()
    conn.close()
    return products

@app.route("/")
def show_products():
    products = get_products()
    url_base = "https://landa-beauty-supply-static-dev.s3.us-east-1.amazonaws.com/products/2000x2000/"
    return render_template("products.html", products=products, url_base=url_base)

if __name__ == "__main__":
    app.run(debug=True)
