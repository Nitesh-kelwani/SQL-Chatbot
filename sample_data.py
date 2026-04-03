# sample_data.py — creates and seeds a demo SQLite database with e-commerce data
# Run this file once: python sample_data.py

import sqlite3
import random
from datetime import datetime, timedelta

DB_PATH = "demo.db"

# --- Sample data pools ---
FIRST_NAMES = ["Alice", "Bob", "Carol", "David", "Eva", "Frank", "Grace", "Henry", "Iris", "Jack"]
LAST_NAMES  = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis"]
CITIES      = ["New York", "London", "Paris", "Tokyo", "Sydney", "Berlin", "Toronto", "Dubai"]
COUNTRIES   = ["USA", "UK", "France", "Japan", "Australia", "Germany", "Canada", "UAE"]

PRODUCTS = [
    ("Wireless Headphones",  "Electronics",   89.99,  120),
    ("Mechanical Keyboard",  "Electronics",  129.99,   80),
    ("USB-C Hub",            "Electronics",   39.99,  200),
    ("Standing Desk",        "Furniture",    349.99,   30),
    ("Ergonomic Chair",      "Furniture",    499.99,   25),
    ("Desk Lamp",            "Furniture",     49.99,  150),
    ("Python Cookbook",      "Books",         34.99,  300),
    ("Clean Code",           "Books",         29.99,  250),
    ("Running Shoes",        "Sports",        79.99,   90),
    ("Yoga Mat",             "Sports",        24.99,  180),
    ("Water Bottle",         "Sports",        19.99,  400),
    ("Coffee Maker",         "Kitchen",       59.99,   70),
    ("Air Purifier",         "Home",         119.99,   60),
    ("Notebook (A5)",        "Stationery",    9.99,   500),
    ("Webcam 1080p",         "Electronics",   69.99,  100),
]

ORDER_STATUSES = ["Completed", "Completed", "Completed", "Pending", "Shipped", "Cancelled"]


def seed_database():
    """Drop existing tables and repopulate with fresh demo data."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # --- Drop old tables if they exist ---
    cursor.executescript("""
        DROP TABLE IF EXISTS order_items;
        DROP TABLE IF EXISTS orders;
        DROP TABLE IF EXISTS products;
        DROP TABLE IF EXISTS customers;
    """)

    # --- Create tables ---
    cursor.executescript("""
        CREATE TABLE customers (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT    NOT NULL,
            email      TEXT    NOT NULL UNIQUE,
            city       TEXT,
            country    TEXT,
            created_at TEXT    NOT NULL
        );

        CREATE TABLE products (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            name     TEXT    NOT NULL,
            category TEXT,
            price    REAL    NOT NULL,
            stock    INTEGER DEFAULT 0
        );

        CREATE TABLE orders (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id  INTEGER NOT NULL,
            order_date   TEXT    NOT NULL,
            status       TEXT    NOT NULL,
            total_amount REAL    NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        );

        CREATE TABLE order_items (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id    INTEGER NOT NULL,
            product_id  INTEGER NOT NULL,
            quantity    INTEGER NOT NULL,
            unit_price  REAL    NOT NULL,
            FOREIGN KEY (order_id)   REFERENCES orders(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        );
    """)

    # --- Insert customers (50 customers) ---
    customers = []
    for i in range(1, 51):
        name    = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        email   = f"user{i}@example.com"
        city    = random.choice(CITIES)
        country = random.choice(COUNTRIES)
        created = (datetime(2023, 1, 1) + timedelta(days=random.randint(0, 365))).strftime("%Y-%m-%d")
        customers.append((name, email, city, country, created))

    cursor.executemany(
        "INSERT INTO customers (name, email, city, country, created_at) VALUES (?, ?, ?, ?, ?)",
        customers
    )

    # --- Insert products ---
    cursor.executemany(
        "INSERT INTO products (name, category, price, stock) VALUES (?, ?, ?, ?)",
        PRODUCTS
    )

    # --- Insert orders and order_items (200 orders) ---
    base_date = datetime(2024, 1, 1)
    for _ in range(200):
        customer_id  = random.randint(1, 50)
        order_date   = (base_date + timedelta(days=random.randint(0, 365))).strftime("%Y-%m-%d")
        status       = random.choice(ORDER_STATUSES)

        # Pick 1–4 random products for each order
        num_items   = random.randint(1, 4)
        chosen      = random.sample(range(1, len(PRODUCTS) + 1), num_items)
        total       = 0.0
        items       = []

        for pid in chosen:
            qty        = random.randint(1, 5)
            unit_price = PRODUCTS[pid - 1][2]   # price from PRODUCTS list
            total     += qty * unit_price
            items.append((pid, qty, unit_price))

        cursor.execute(
            "INSERT INTO orders (customer_id, order_date, status, total_amount) VALUES (?, ?, ?, ?)",
            (customer_id, order_date, status, round(total, 2))
        )
        order_id = cursor.lastrowid

        cursor.executemany(
            "INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (?, ?, ?, ?)",
            [(order_id, pid, qty, price) for pid, qty, price in items]
        )

    conn.commit()
    conn.close()
    print(f"✅ Demo database created: {DB_PATH}")
    print("   Tables: customers (50), products (15), orders (200), order_items")


if __name__ == "__main__":
    seed_database()
