# ============================================================
# EASY SALES - DATABASE (MULTI-STORE CONNECTED)
# ============================================================

import os
import sqlite3
import datetime
import uuid

from flask import has_request_context, session

from store_database import (
    get_store_connection,
    create_store_database
)
from storage import DATA_DIR


# The shared data directory is local during development and can be
# mapped to Render's Persistent Disk in production.
DATABASE = os.path.join(str(DATA_DIR), "test_sales.db")


def get_connection():
    """
    Open the correct database for the current request.

    - A logged-in client uses ONLY their private store database.
    - Startup/admin code without a store session continues to use the
      original Easy Sales development database.

    This means the existing POS functions below do not need to know a
    Store ID. They automatically work inside the approved client's store.
    """
    if has_request_context():
        store_id = session.get("store_id")

        if store_id:
            # Safe to call repeatedly; existing client data is preserved.
            create_store_database(store_id)
            return get_store_connection(store_id)

    os.makedirs(os.path.dirname(DATABASE), exist_ok=True)
    connection = sqlite3.connect(DATABASE, timeout=30)
    connection.execute("PRAGMA busy_timeout = 30000")
    connection.row_factory = sqlite3.Row
    return connection


def now_string():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def create_database():
    connection = get_connection()
    cursor = connection.cursor()

    # Enable WAL once during startup. Do not change journal mode on every request.
    cursor.execute("PRAGMA journal_mode = WAL")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            stock INTEGER NOT NULL DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            total REAL NOT NULL,
            payment_method TEXT NOT NULL,
            transaction_id TEXT,
            sold_at TEXT NOT NULL,
            FOREIGN KEY(product_id) REFERENCES products(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stock_movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            movement_type TEXT NOT NULL,
            stock_before INTEGER NOT NULL,
            quantity_added INTEGER NOT NULL DEFAULT 0,
            quantity_sold INTEGER NOT NULL DEFAULT 0,
            adjustment INTEGER NOT NULL DEFAULT 0,
            stock_after INTEGER NOT NULL,
            reason TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(product_id) REFERENCES products(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stock_takes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            system_stock INTEGER NOT NULL,
            counted_stock INTEGER NOT NULL,
            variance INTEGER NOT NULL,
            notes TEXT,
            taken_at TEXT NOT NULL,
            FOREIGN KEY(product_id) REFERENCES products(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS monthly_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_month TEXT NOT NULL,
            cash_at_hand REAL NOT NULL,
            expected_cash REAL NOT NULL,
            cash_variance REAL NOT NULL,
            stock_units INTEGER NOT NULL,
            stock_value REAL NOT NULL,
            damaged_units INTEGER NOT NULL,
            damaged_value REAL NOT NULL,
            total_loss REAL NOT NULL,
            cash_sales_count INTEGER NOT NULL DEFAULT 0,
            cash_sales_amount REAL NOT NULL DEFAULT 0,
            card_sales_count INTEGER NOT NULL DEFAULT 0,
            card_sales_amount REAL NOT NULL DEFAULT 0,
            total_sales_count INTEGER NOT NULL DEFAULT 0,
            total_sales_amount REAL NOT NULL DEFAULT 0,
            total_sales_units INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS monthly_report_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            value REAL NOT NULL,
            FOREIGN KEY(report_id) REFERENCES monthly_reports(id),
            FOREIGN KEY(product_id) REFERENCES products(id)
        )
    """)

    # Safe migrations for older Easy Sales databases.
    _ensure_column(cursor, "sales", "transaction_id", "TEXT")
    _ensure_column(cursor, "monthly_reports", "cash_sales_count", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(cursor, "monthly_reports", "cash_sales_amount", "REAL NOT NULL DEFAULT 0")
    _ensure_column(cursor, "monthly_reports", "card_sales_count", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(cursor, "monthly_reports", "card_sales_amount", "REAL NOT NULL DEFAULT 0")
    _ensure_column(cursor, "monthly_reports", "total_sales_count", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(cursor, "monthly_reports", "total_sales_amount", "REAL NOT NULL DEFAULT 0")
    _ensure_column(cursor, "monthly_reports", "total_sales_units", "INTEGER NOT NULL DEFAULT 0")

    cursor.execute("""
        UPDATE sales
        SET transaction_id = 'LEGACY-' || id
        WHERE transaction_id IS NULL OR transaction_id = ''
    """)

    connection.commit()
    connection.close()


def _ensure_column(cursor, table_name, column_name, definition):
    columns = {
        row[1] for row in cursor.execute(
            f"PRAGMA table_info({table_name})"
        ).fetchall()
    }
    if column_name not in columns:
        cursor.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}"
        )



def add_product(name, price, stock):
    """Add a product and ALWAYS release the SQLite connection."""
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            INSERT INTO products (name, price, stock)
            VALUES (?, ?, ?)
        """, (name, price, stock))

        product_id = cursor.lastrowid
        connection.commit()
        return product_id

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def get_all_products():
    connection = get_connection()
    rows = connection.execute("""
        SELECT id, name, price, stock
        FROM products
        ORDER BY name
    """).fetchall()
    connection.close()
    return [dict(row) for row in rows]


def complete_sale(cart, payment_method):
    connection = get_connection()
    cursor = connection.cursor()
    sold_at = now_string()
    transaction_id = str(uuid.uuid4())
    total_sale = 0.0

    try:
        for item in cart:
            product_id = int(item.get("id"))
            quantity = int(item.get("quantity"))

            if quantity <= 0:
                raise ValueError("Invalid sale quantity.")

            product = cursor.execute(
                "SELECT id, name, price, stock FROM products WHERE id = ?",
                (product_id,)
            ).fetchone()

            if not product:
                raise ValueError("Product no longer exists.")

            if product["stock"] < quantity:
                raise ValueError(
                    f"Not enough stock for {product['name']}."
                )

            unit_price = float(product["price"])
            line_total = unit_price * quantity
            before = int(product["stock"])
            after = before - quantity

            cursor.execute(
                "UPDATE products SET stock = ? WHERE id = ?",
                (after, product_id)
            )

            cursor.execute("""
                INSERT INTO sales
                (product_id, product_name, quantity, unit_price,
                 total, payment_method, transaction_id, sold_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                product_id,
                product["name"],
                quantity,
                unit_price,
                line_total,
                payment_method,
                transaction_id,
                sold_at
            ))

            cursor.execute("""
                INSERT INTO stock_movements
                (product_id, product_name, movement_type,
                 stock_before, quantity_added, quantity_sold,
                 adjustment, stock_after, reason, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                product_id,
                product["name"],
                "SALE",
                before,
                0,
                quantity,
                0,
                after,
                "Sale",
                sold_at
            ))

            total_sale += line_total

        connection.commit()
        return {
            "total": round(total_sale, 2),
            "sold_at": sold_at,
            "transaction_id": transaction_id
        }

    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def get_stock_take():
    connection = get_connection()
    rows = connection.execute("""
        SELECT
            p.id,
            p.name,
            p.price,
            p.stock,
            COALESCE(SUM(
                CASE
                    WHEN s.sold_at LIKE date('now', 'localtime') || '%' THEN s.quantity
                    ELSE 0
                END
            ), 0) AS sold_today,
            COALESCE(SUM(
                CASE
                    WHEN s.sold_at LIKE date('now', 'localtime') || '%' THEN s.total
                    ELSE 0
                END
            ), 0) AS sales_today
        FROM products p
        LEFT JOIN sales s ON s.product_id = p.id
        GROUP BY p.id
        ORDER BY p.name
    """).fetchall()
    connection.close()
    return [dict(row) for row in rows]


def get_today_sales():
    connection = get_connection()
    rows = connection.execute("""
        SELECT id, product_name, quantity, unit_price, total,
               payment_method, sold_at
        FROM sales
        WHERE sold_at LIKE date('now', 'localtime') || '%'
        ORDER BY id DESC
    """).fetchall()
    connection.close()
    return [dict(row) for row in rows]


def add_stock(product_id, quantity, reason):
    if quantity <= 0:
        raise ValueError("Quantity must be greater than zero.")

    connection = get_connection()
    cursor = connection.cursor()

    try:
        product = cursor.execute(
            "SELECT id, name, stock FROM products WHERE id = ?",
            (product_id,)
        ).fetchone()

        if not product:
            raise ValueError("Product not found.")

        before = int(product["stock"])
        after = before + quantity
        created_at = now_string()

        cursor.execute(
            "UPDATE products SET stock = ? WHERE id = ?",
            (after, product_id)
        )

        cursor.execute("""
            INSERT INTO stock_movements
            (product_id, product_name, movement_type,
             stock_before, quantity_added, quantity_sold,
             adjustment, stock_after, reason, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            product_id, product["name"], "STOCK_IN",
            before, quantity, 0, quantity, after,
            reason, created_at
        ))

        connection.commit()
        return {
            "stock_before": before,
            "quantity_added": quantity,
            "stock_after": after,
            "created_at": created_at
        }
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def remove_stock(product_id, quantity, reason):
    if quantity <= 0:
        raise ValueError("Quantity must be greater than zero.")

    connection = get_connection()
    cursor = connection.cursor()

    try:
        product = cursor.execute(
            "SELECT id, name, stock FROM products WHERE id = ?",
            (product_id,)
        ).fetchone()

        if not product:
            raise ValueError("Product not found.")

        before = int(product["stock"])
        if quantity > before:
            raise ValueError("Cannot remove more stock than is available.")

        after = before - quantity
        created_at = now_string()

        cursor.execute(
            "UPDATE products SET stock = ? WHERE id = ?",
            (after, product_id)
        )

        cursor.execute("""
            INSERT INTO stock_movements
            (product_id, product_name, movement_type,
             stock_before, quantity_added, quantity_sold,
             adjustment, stock_after, reason, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            product_id, product["name"], "STOCK_OUT",
            before, 0, 0, -quantity, after,
            reason, created_at
        ))

        connection.commit()
        return {
            "stock_before": before,
            "quantity_removed": quantity,
            "stock_after": after,
            "created_at": created_at
        }
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def record_stocktake(product_id, counted_stock, notes):
    if counted_stock < 0:
        raise ValueError("Counted stock cannot be negative.")

    connection = get_connection()
    cursor = connection.cursor()

    try:
        product = cursor.execute(
            "SELECT id, name, stock FROM products WHERE id = ?",
            (product_id,)
        ).fetchone()

        if not product:
            raise ValueError("Product not found.")

        system_stock = int(product["stock"])
        variance = counted_stock - system_stock
        taken_at = now_string()

        cursor.execute(
            "UPDATE products SET stock = ? WHERE id = ?",
            (counted_stock, product_id)
        )

        cursor.execute("""
            INSERT INTO stock_takes
            (product_id, product_name, system_stock,
             counted_stock, variance, notes, taken_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            product_id, product["name"], system_stock,
            counted_stock, variance, notes, taken_at
        ))

        if variance:
            cursor.execute("""
                INSERT INTO stock_movements
                (product_id, product_name, movement_type,
                 stock_before, quantity_added, quantity_sold,
                 adjustment, stock_after, reason, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                product_id, product["name"], "STOCKTAKE",
                system_stock,
                max(variance, 0),
                0,
                variance,
                counted_stock,
                notes or "Physical stocktake",
                taken_at
            ))

        connection.commit()
        return {
            "system_stock": system_stock,
            "counted_stock": counted_stock,
            "variance": variance,
            "stock_after": counted_stock,
            "taken_at": taken_at
        }
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def get_stock_movements(product_id=None):
    connection = get_connection()
    if product_id:
        rows = connection.execute("""
            SELECT * FROM stock_movements
            WHERE product_id = ?
            ORDER BY id DESC
        """, (product_id,)).fetchall()
    else:
        rows = connection.execute("""
            SELECT * FROM stock_movements
            ORDER BY id DESC
        """).fetchall()
    connection.close()
    return [dict(row) for row in rows]


def get_stocktake_history(product_id=None):
    connection = get_connection()
    if product_id:
        rows = connection.execute("""
            SELECT * FROM stock_takes
            WHERE product_id = ?
            ORDER BY id DESC
        """, (product_id,)).fetchall()
    else:
        rows = connection.execute("""
            SELECT * FROM stock_takes
            ORDER BY id DESC
        """).fetchall()
    connection.close()
    return [dict(row) for row in rows]


def create_monthly_report(cash_at_hand, damaged_goods):
    cash_at_hand = float(cash_at_hand)
    if cash_at_hand < 0:
        raise ValueError("Cash at hand cannot be negative.")

    connection = get_connection()
    cursor = connection.cursor()

    try:
        report_month = datetime.datetime.now().strftime("%Y-%m")
        created_at = now_string()
        damaged_units = 0
        damaged_value = 0.0
        damaged_items = []

        # Remove every damaged item from actual stock and record it.
        for item in damaged_goods:
            product_id = int(item.get("product_id"))
            quantity = int(item.get("quantity"))

            if quantity <= 0:
                raise ValueError("Damaged quantity must be greater than zero.")

            product = cursor.execute("""
                SELECT id, name, price, stock
                FROM products
                WHERE id = ?
            """, (product_id,)).fetchone()

            if not product:
                raise ValueError("Damaged product not found.")

            if quantity > product["stock"]:
                raise ValueError(
                    f"Damaged quantity for {product['name']} is greater than stock."
                )

            before = int(product["stock"])
            after = before - quantity
            value = float(product["price"]) * quantity

            cursor.execute(
                "UPDATE products SET stock = ? WHERE id = ?",
                (after, product_id)
            )

            cursor.execute("""
                INSERT INTO stock_movements
                (product_id, product_name, movement_type,
                 stock_before, quantity_added, quantity_sold,
                 adjustment, stock_after, reason, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                product_id, product["name"], "DAMAGED",
                before, 0, 0, -quantity, after,
                "Damaged goods - monthly report", created_at
            ))

            damaged_units += quantity
            damaged_value += value
            damaged_items.append({
                "product_id": product_id,
                "product_name": product["name"],
                "quantity": quantity,
                "value": round(value, 2)
            })

        stock_summary = cursor.execute("""
            SELECT
                COALESCE(SUM(stock), 0) AS stock_units,
                COALESCE(SUM(stock * price), 0) AS stock_value
            FROM products
        """).fetchone()

        # Reconcile the register against recorded sales for this month.
        sales_summary = cursor.execute("""
            SELECT
                COUNT(DISTINCT CASE WHEN payment_method = 'cash' THEN transaction_id END) AS cash_sales_count,
                COALESCE(SUM(CASE WHEN payment_method = 'cash' THEN total ELSE 0 END), 0) AS cash_sales_amount,
                COUNT(DISTINCT CASE WHEN payment_method = 'card' THEN transaction_id END) AS card_sales_count,
                COALESCE(SUM(CASE WHEN payment_method = 'card' THEN total ELSE 0 END), 0) AS card_sales_amount,
                COUNT(DISTINCT transaction_id) AS total_sales_count,
                COALESCE(SUM(total), 0) AS total_sales_amount,
                COALESCE(SUM(quantity), 0) AS total_sales_units
            FROM sales
            WHERE substr(sold_at, 1, 7) = ?
        """, (report_month,)).fetchone()

        cash_sales_count = int(sales_summary["cash_sales_count"] or 0)
        cash_sales_amount = float(sales_summary["cash_sales_amount"] or 0)
        card_sales_count = int(sales_summary["card_sales_count"] or 0)
        card_sales_amount = float(sales_summary["card_sales_amount"] or 0)
        total_sales_count = int(sales_summary["total_sales_count"] or 0)
        total_sales_amount = float(sales_summary["total_sales_amount"] or 0)
        total_sales_units = int(sales_summary["total_sales_units"] or 0)

        # No opening-float input exists yet, so expected register cash
        # is the recorded cash sales for this reporting period.
        expected_cash = cash_sales_amount
        cash_variance = cash_at_hand - expected_cash
        cash_shortage = max(0.0, -cash_variance)
        total_loss = damaged_value + cash_shortage

        cursor.execute("""
            INSERT INTO monthly_reports
            (report_month, cash_at_hand, expected_cash, cash_variance,
             stock_units, stock_value, damaged_units, damaged_value,
             total_loss, cash_sales_count, cash_sales_amount,
             card_sales_count, card_sales_amount, total_sales_count,
             total_sales_amount, total_sales_units, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            report_month,
            cash_at_hand,
            expected_cash,
            cash_variance,
            int(stock_summary["stock_units"]),
            float(stock_summary["stock_value"]),
            damaged_units,
            damaged_value,
            total_loss,
            cash_sales_count,
            cash_sales_amount,
            card_sales_count,
            card_sales_amount,
            total_sales_count,
            total_sales_amount,
            total_sales_units,
            created_at
        ))

        report_id = cursor.lastrowid

        for damaged_item in damaged_items:
            cursor.execute("""
                INSERT INTO monthly_report_items
                (report_id, product_id, product_name, quantity, value)
                VALUES (?, ?, ?, ?, ?)
            """, (
                report_id,
                damaged_item["product_id"],
                damaged_item["product_name"],
                damaged_item["quantity"],
                damaged_item["value"]
            ))

        connection.commit()

        return {
            "id": report_id,
            "report_month": report_month,
            "cash_at_hand": round(cash_at_hand, 2),
            "expected_cash": round(expected_cash, 2),
            "cash_variance": round(cash_variance, 2),
            "cash_sales_count": cash_sales_count,
            "cash_sales_amount": round(cash_sales_amount, 2),
            "card_sales_count": card_sales_count,
            "card_sales_amount": round(card_sales_amount, 2),
            "total_sales_count": total_sales_count,
            "total_sales_amount": round(total_sales_amount, 2),
            "total_sales_units": total_sales_units,
            "stock_units": int(stock_summary["stock_units"]),
            "stock_value": round(float(stock_summary["stock_value"]), 2),
            "damaged_units": damaged_units,
            "damaged_value": round(damaged_value, 2),
            "total_loss": round(total_loss, 2),
            "created_at": created_at,
            "damaged_items": damaged_items
        }

    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def get_monthly_sales_summary():
    connection = get_connection()
    try:
        report_month = datetime.datetime.now().strftime("%Y-%m")
        row = connection.execute("""
            SELECT
                COUNT(DISTINCT CASE WHEN payment_method = 'cash' THEN transaction_id END) AS cash_sales_count,
                COALESCE(SUM(CASE WHEN payment_method = 'cash' THEN total ELSE 0 END), 0) AS cash_sales_amount,
                COUNT(DISTINCT CASE WHEN payment_method = 'card' THEN transaction_id END) AS card_sales_count,
                COALESCE(SUM(CASE WHEN payment_method = 'card' THEN total ELSE 0 END), 0) AS card_sales_amount,
                COUNT(DISTINCT transaction_id) AS total_sales_count,
                COALESCE(SUM(total), 0) AS total_sales_amount,
                COALESCE(SUM(quantity), 0) AS total_sales_units
            FROM sales
            WHERE substr(sold_at, 1, 7) = ?
        """, (report_month,)).fetchone()

        return {
            "report_month": report_month,
            "cash_sales_count": int(row["cash_sales_count"] or 0),
            "cash_sales_amount": round(float(row["cash_sales_amount"] or 0), 2),
            "card_sales_count": int(row["card_sales_count"] or 0),
            "card_sales_amount": round(float(row["card_sales_amount"] or 0), 2),
            "total_sales_count": int(row["total_sales_count"] or 0),
            "total_sales_amount": round(float(row["total_sales_amount"] or 0), 2),
            "total_sales_units": int(row["total_sales_units"] or 0)
        }
    finally:
        connection.close()

def get_monthly_reports():
    connection = get_connection()
    reports = connection.execute("""
        SELECT * FROM monthly_reports
        ORDER BY id DESC
    """).fetchall()

    result = []
    for report in reports:
        item = dict(report)
        item["damaged_items"] = [
            dict(row)
            for row in connection.execute("""
                SELECT
                    product_id,
                    product_name,
                    quantity,
                    value
                FROM monthly_report_items
                WHERE report_id = ?
                ORDER BY id
            """, (report["id"],)).fetchall()
        ]
        result.append(item)

    connection.close()
    return result
