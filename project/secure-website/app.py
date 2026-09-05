import os
import sqlite3
import subprocess
import re
from flask import Flask
from flask_wtf.csrf import CSRFProtect
from functools import wraps
from pathlib import Path
from urllib.request import urlopen

from flask import (
    Flask,
    g,
    redirect,
    render_template,
    render_template_string,
    request,
    send_file,
    session,
    url_for,
)
from markupsafe import Markup

TRACKING_PATTERN = re.compile(r"^[A-Za-z0-9-]{1,64}$")
ROOT = Path(__file__).parent
DATABASE = ROOT / "shop.db"
CARRIER_LOOKUP = ROOT / "bin" / "carrier_lookup"
TRACKING_TEMPLATE = ROOT / "templates" / "tracking_result.html"
SUPPLIER_SERVICE_URL = os.environ.get(
    "SUPPLIER_SERVICE_URL", "http://127.0.0.1:5001"
).rstrip("/")

app = Flask(__name__)
app.config["SECRET_KEY"] = "local-dev-secure-key-change-this-to-a-long-random-value-2026"

csrf = CSRFProtect(app)

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

def db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_error):
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def setup_database():
    connection = sqlite3.connect(DATABASE)
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            display_name TEXT NOT NULL,
            email TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            image TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY,
            product_id INTEGER NOT NULL,
            body TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS notification_templates (
            username TEXT PRIMARY KEY,
            body TEXT NOT NULL,
            FOREIGN KEY (username) REFERENCES accounts(username)
        );

        INSERT OR IGNORE INTO accounts (username, password, display_name, email)
        VALUES ('peter', 'wiener', 'Peter', 'peter@example.com');

        INSERT OR IGNORE INTO products (id, name, description, image)
        VALUES (1, 'Travel mug', 'A stainless steel mug with a screw top.', 'mug.svg');
        """
    )
    connection.execute(
        "INSERT OR IGNORE INTO notification_templates (username, body) VALUES (?, ?)",
        ("peter", TRACKING_TEMPLATE.read_text()),
    )
    connection.commit()
    connection.close()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def get_product(product_id):
    return db().execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()


def get_notification_template(username):
    row = db().execute(
        "SELECT body FROM notification_templates WHERE username = ?", (username,)
    ).fetchone()
    return row["body"] if row is not None else TRACKING_TEMPLATE.read_text()


def product_page(product_id, stock=None):
    product = get_product(product_id)
    review_rows = db().execute(
        "SELECT * FROM reviews WHERE product_id = ? ORDER BY id DESC", (product_id,)
    ).fetchall()
    reviews = [Markup(row["body"].replace("\n", "<br>")) for row in review_rows]
    stock_api = f"{SUPPLIER_SERVICE_URL}/stock/{product_id}"
    return render_template(
        "product.html",
        product=product,
        reviews=reviews,
        stock=stock,
        stock_api=stock_api,
    )


@app.route("/", methods=["GET"])
@login_required
def products():
    q = request.args.get("q", "")
    search_summary = None
    if q:
        rows = db().execute(
            "SELECT * FROM products WHERE name LIKE ?", (f"%{q}%",)
        ).fetchall()
        search_summary = Markup(f"Results for <mark>{q}</mark>")
    else:
        rows = db().execute("SELECT * FROM products").fetchall()

    account = db().execute(
        "SELECT * FROM accounts WHERE username = ?", (session["user"],)
    ).fetchone()
    greeting = "Hello " + account["display_name"]

    tracking = request.args.get("tracking")
    tracking_result = None
    if tracking is not None:
        try:
            if not TRACKING_PATTERN.fullmatch(tracking):
             return "Invalid tracking reference", 400

            result = subprocess.run(
             ["bash", str(CARRIER_LOOKUP), tracking],
             capture_output=True,
             text=True,
             timeout=4,
)
            status = result.stdout + result.stderr or "No matching order."
            source = get_notification_template(session["user"])
            tracking_result = Markup(
                render_template_string(
                    source,
                    tracking_reference=tracking,
                    status=status,
                )
            )
        except Exception as error:
            tracking_result = str(error)

    return render_template(
        "products.html",
        products=rows,
        q=q,
        search_summary=search_summary,
        greeting=greeting,
        tracking=tracking,
        tracking_result=tracking_result,
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    next_url = request.values.get("next", url_for("products"))
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        query = (
            "SELECT username FROM accounts WHERE username = '"
            + username
            + "' AND password = '"
            + password
            + "' LIMIT 1"
        )
        try:
            user = db().execute(query).fetchone()
        except sqlite3.Error:
            user = None

        if user:
            session["user"] = user["username"]
            return redirect(next_url)
        error = "That login did not work."

    return render_template("login.html", error=error, next_url=next_url)


@app.get("/product/<int:product_id>")
@login_required
def product(product_id):
    return product_page(product_id)


@app.post("/product/<int:product_id>/reviews")
@login_required
def add_review(product_id):
    db().execute(
        "INSERT INTO reviews (product_id, body) VALUES (?, ?)",
        (product_id, request.form.get("body", "")),
    )
    db().commit()
    return redirect(url_for("product", product_id=product_id) + "?message=Review%20submitted")


@app.post("/product/<int:product_id>/stock")
@login_required
def check_stock(product_id):
    try:
        with urlopen(request.form.get("stock_api", ""), timeout=4) as response:
            stock = response.read(12000).decode("utf-8", errors="replace")
    except Exception as error:
        stock = str(error)
    return product_page(product_id, stock)


@app.route("/account", methods=["GET", "POST"])
@login_required
def account():
    if request.method == "POST":
        connection = db()
        connection.execute(
            "UPDATE accounts SET display_name = ?, email = ? WHERE username = ?",
            (
                request.form.get("display_name", ""),
                request.form.get("email", ""),
                session["user"],
            ),
        )
        connection.execute(
            """
            INSERT INTO notification_templates (username, body) VALUES (?, ?)
            ON CONFLICT(username) DO UPDATE SET body = excluded.body
            """,
            (session["user"], request.form.get("notification_template", "")),
        )
        connection.commit()
        return redirect(url_for("products"))

    details = db().execute(
        "SELECT * FROM accounts WHERE username = ?", (session["user"],)
    ).fetchone()
    return render_template(
        "account.html",
        account=details,
        notification_template=get_notification_template(session["user"]),
    )


@app.get("/image")
@login_required
def image():
    return send_file(ROOT / "images" / request.args.get("filename", ""))

if __name__ == "__main__":
    setup_database()
    app.run(host="127.0.0.1", port=5000)
