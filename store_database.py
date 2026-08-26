# ============================================================
# EASY SALES - PRIVATE STORE DATABASE MANAGER
# ============================================================
#
# Place this file in:
# Easy_Sales/store_database.py
#
# PURPOSE
# -------
# Each client store receives its own SQLite database:
#
# database/stores/STORE001.db
# database/stores/STORE002.db
# ...
#
# A store database is NEVER deleted when a store is deactivated.
# Deactivation only removes access. This keeps the client's data
# available if they return and reactivate their store later.
# ============================================================

import os
import re
import sqlite3


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STORES_DATABASE_DIR = os.path.join(BASE_DIR, "database", "stores")


def _clean_store_id(store_id):
    """Validate and normalise a store ID before using it as a filename."""
    store_id = str(store_id or "").strip().upper()

    if not re.fullmatch(r"[A-Z0-9-]{3,64}", store_id):
        raise ValueError("Invalid Store ID.")

    return store_id


def get_store_database_path(store_id):
    """Return the private database path for one store."""
    store_id = _clean_store_id(store_id)
    return os.path.join(STORES_DATABASE_DIR, f"{store_id}.db")


def get_store_connection(store_id):
    """Open a connection to one store's private database."""

    database_path = get_store_database_path(store_id)
    os.makedirs(STORES_DATABASE_DIR, exist_ok=True)

    connection = sqlite3.connect(
        database_path,
        timeout=10
    )

    connection.row_factory = sqlite3.Row

    # Database safety settings
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 10000")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA synchronous = NORMAL")

    return connection


def create_store_database(store_id):
    """
    Create the private Easy Sales database for a store if it does not
    already exist.

    Safe to run more than once. Existing client data is preserved.
    """
    connection = get_store_connection(store_id)
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            stock INTEGER NOT NULL DEFAULT 0,
            barcode TEXT UNIQUE
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
            sale_fee REAL NOT NULL DEFAULT 0,
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

    # Safe migrations for databases created by earlier versions.
    _ensure_column(cursor, "products", "barcode", "TEXT")
    _ensure_column(cursor, "sales", "transaction_id", "TEXT")
    _ensure_column(cursor, "sales", "sale_fee", "REAL NOT NULL DEFAULT 0")
    _ensure_column(cursor, "monthly_reports", "cash_sales_count",
                   "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(cursor, "monthly_reports", "cash_sales_amount",
                   "REAL NOT NULL DEFAULT 0")
    _ensure_column(cursor, "monthly_reports", "card_sales_count",
                   "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(cursor, "monthly_reports", "card_sales_amount",
                   "REAL NOT NULL DEFAULT 0")
    _ensure_column(cursor, "monthly_reports", "total_sales_count",
                   "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(cursor, "monthly_reports", "total_sales_amount",
                   "REAL NOT NULL DEFAULT 0")
    _ensure_column(cursor, "monthly_reports", "total_sales_units",
                   "INTEGER NOT NULL DEFAULT 0")

    cursor.execute("""
        UPDATE sales
        SET transaction_id = 'LEGACY-' || id
        WHERE transaction_id IS NULL OR transaction_id = ''
    """)

    connection.commit()
    connection.close()

    return get_store_database_path(store_id)


def _ensure_column(cursor, table_name, column_name, definition):
    columns = {
        row[1]
        for row in cursor.execute(
            f"PRAGMA table_info({table_name})"
        ).fetchall()
    }

    if column_name not in columns:
        cursor.execute(
            f"ALTER TABLE {table_name} "
            f"ADD COLUMN {column_name} {definition}"
        )


def store_database_exists(store_id):
    """Check whether a private database already exists for a store."""
    return os.path.exists(get_store_database_path(store_id))
# ============================================================
# RESET ONE STORE'S POS DATA
# ============================================================

def reset_store_data(store_id):
    """
    Reset ONLY the POS data belonging to one store.

    The store itself is NOT deleted from the controller system.
    Its Store ID, name, passkey and activation status remain intact.

    Other stores are completely untouched.
    """

    store_id = _clean_store_id(store_id)

    # Make sure the store has its private database.
    create_store_database(store_id)

    connection = get_store_connection(store_id)
    cursor = connection.cursor()

    try:

        # Child/history tables first.
        cursor.execute("DELETE FROM monthly_report_items")
        cursor.execute("DELETE FROM monthly_reports")
        cursor.execute("DELETE FROM stock_takes")
        cursor.execute("DELETE FROM stock_movements")
        cursor.execute("DELETE FROM sales")

        # Finally remove all products and remaining stock.
        cursor.execute("DELETE FROM products")

        connection.commit()

        return {
            "success": True,
            "store_id": store_id,
            "message": "Store data reset successfully."
        }

    except Exception:

        connection.rollback()
        raise

    finally:

        connection.close()

if __name__ == "__main__":
    os.makedirs(STORES_DATABASE_DIR, exist_ok=True)

    print("Easy Sales Private Store Database Manager is ready.")
    print(f"Store databases folder: {STORES_DATABASE_DIR}")
    print("Client databases will be created only when a store is assigned.")
