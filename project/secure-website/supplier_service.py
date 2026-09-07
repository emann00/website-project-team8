from flask import Flask


app = Flask(__name__)


@app.get("/stock/<int:product_id>")
def stock(product_id):
    return f"{12 if product_id == 1 else 0} in stock\n"


@app.get("/config")
def config():
    return "supplier-token: demo-4381\n"


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001)
