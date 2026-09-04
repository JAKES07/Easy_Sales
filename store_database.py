# ============================================================
# EASY SALES - PRIVATE STORE DATABASE MANAGER
# ============================================================
#
# IMPORTANT:
# All customer POS data lives outside the application code when
# EASY_SALES_DATA_DIR is configured.
#
# Every store has one private database:
#
#   <LIVE_DATA_DIR>/stores/STORE001.db
#   <LIVE_DATA_DIR>/stores/STORE002.db
#
# The application NEVER copies products between stores and never
# creates a second database location when a live data directory is
# configured.
# ============================================================

import os
import re
import sqlite3


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# ============================================================
# LIVE DATA LOCATION
# ============================================================

_configured_data_dir = os.environ.get(
    "EASY_SALES_DATA_DIR",
    ""
).strip()


if _configured_data_dir:

    # Explicit configuration always wins.
    LIVE_DATA_DIR = os.path.abspath(
        os.path.expanduser(_configured_data_dir)
    )

elif os.path.isdir("/var/data"):

    # Render persistent disk. The Easy Sales Render service mounts its
    # persistent disk here, so production data survives redeployments
    # even when an environment variable was not configured manually.
    LIVE_DATA_DIR = "/var/data"

else:

    # Local Pydroid / development location.
    LIVE_DATA_DIR = os.path.join(
        BASE_DIR,
        "database"
    )


STORES_DATABASE_DIR = os.path.join(
    LIVE_DATA_DIR,
    "stores"
)


# ============================================================
# STORE ID VALIDATION
# ============================================================

def _clean_store_id(store_id):

    store_id = str(store_id or "").strip().upper()

    if not re.fullmatch(
        r"[A-Z0-9-]{3,64}",
        store_id
    ):
        raise ValueError(
            "Invalid Store ID."
        )

    return store_id


# ============================================================
# DATABASE PATHS
# ============================================================

def get_live_data_dir():
    """Return the single active Easy Sales data directory."""
    return LIVE_DATA_DIR


def get_store_database_path(store_id):

    store_id = _clean_store_id(store_id)

    return os.path.join(
        STORES_DATABASE_DIR,
        f"{store_id}.db"
    )


# ============================================================
# OPEN STORE DATABASE
# ============================================================

def get_store_connection(store_id):

    store_id = _clean_store_id(store_id)

    os.makedirs(
        STORES_DATABASE_DIR,
        exist_ok=True
    )

    database_path = get_store_database_path(
        store_id
    )

    connection = sqlite3.connect(
        database_path,
        timeout=10
    )

    connection.row_factory = sqlite3.Row

    connection.execute(
        "PRAGMA foreign_keys = ON"
    )

    connection.execute(
        "PRAGMA busy_timeout = 10000"
    )

    connection.execute(
        "PRAGMA journal_mode = WAL"
    )

    connection.execute(
        "PRAGMA synchronous = NORMAL"
    )

    return connection


# ============================================================
# SAFE DATABASE UPGRADES
# ============================================================

def _ensure_column(
    cursor,
    table_name,
    column_name,
    definition
):

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


# ============================================================
# CREATE / UPGRADE ONE STORE DATABASE
# ============================================================

def create_store_database(store_id):

    store_id = _clean_store_id(store_id)

    connection = get_store_connection(
        store_id
    )

    cursor = connection.cursor()

    try:

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                price REAL NOT NULL,
                stock INTEGER NOT NULL DEFAULT 0,
                barcode TEXT UNIQUE,
                active INTEGER NOT NULL DEFAULT 1
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
                FOREIGN KEY(product_id)
                    REFERENCES products(id)
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
                FOREIGN KEY(product_id)
                    REFERENCES products(id)
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
                FOREIGN KEY(product_id)
                    REFERENCES products(id)
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
            CREATE TABLE IF NOT EXISTS store_settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                currency_code TEXT,
                currency_symbol TEXT,
                currency_name TEXT,
                updated_at TEXT
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
                FOREIGN KEY(report_id)
                    REFERENCES monthly_reports(id),
                FOREIGN KEY(product_id)
                    REFERENCES products(id)
            )
        """)

        # Safe upgrades for older databases.
        _ensure_column(
            cursor,
            "products",
            "barcode",
            "TEXT"
        )

        _ensure_column(
            cursor,
            "products",
            "active",
            "INTEGER NOT NULL DEFAULT 1"
        )

        _ensure_column(
            cursor,
            "sales",
            "transaction_id",
            "TEXT"
        )

        _ensure_column(
            cursor,
            "sales",
            "sale_fee",
            "REAL NOT NULL DEFAULT 0"
        )

        for column_name, definition in [
            ("cash_sales_count", "INTEGER NOT NULL DEFAULT 0"),
            ("cash_sales_amount", "REAL NOT NULL DEFAULT 0"),
            ("card_sales_count", "INTEGER NOT NULL DEFAULT 0"),
            ("card_sales_amount", "REAL NOT NULL DEFAULT 0"),
            ("total_sales_count", "INTEGER NOT NULL DEFAULT 0"),
            ("total_sales_amount", "REAL NOT NULL DEFAULT 0"),
            ("total_sales_units", "INTEGER NOT NULL DEFAULT 0"),
        ]:

            _ensure_column(
                cursor,
                "monthly_reports",
                column_name,
                definition
            )

        cursor.execute("""
            UPDATE sales
            SET transaction_id = 'LEGACY-' || id
            WHERE transaction_id IS NULL
               OR transaction_id = ''
        """)

        connection.commit()

    except Exception:

        connection.rollback()
        raise

    finally:

        connection.close()

    return get_store_database_path(
        store_id
    )


# ============================================================
# DATABASE CHECK
# ============================================================

def store_database_exists(store_id):

    return os.path.isfile(
        get_store_database_path(store_id)
    )


# ============================================================
# RESET ONE STORE'S POS DATA
# ============================================================

def reset_store_data(store_id):

    store_id = _clean_store_id(store_id)

    create_store_database(store_id)

    connection = get_store_connection(
        store_id
    )

    cursor = connection.cursor()

    try:

        cursor.execute(
            "DELETE FROM monthly_report_items"
        )

        cursor.execute(
            "DELETE FROM monthly_reports"
        )

        cursor.execute(
            "DELETE FROM stock_takes"
        )

        cursor.execute(
            "DELETE FROM stock_movements"
        )

        cursor.execute(
            "DELETE FROM sales"
        )

        cursor.execute(
            "DELETE FROM products"
        )

        # Reset the store currency too. On the next store login,
        # Easy Sales will show the currency setup popup again so the
        # freshly reset store can choose its operating currency.
        cursor.execute(
            "DELETE FROM store_settings"
        )

        connection.commit()

        return {
            "success": True,
            "store_id": store_id,
            "message": (
                "Store data reset successfully."
            )
        }

    except Exception:

        connection.rollback()
        raise

    finally:

        connection.close()


# ============================================================
# STARTUP INFORMATION
# ============================================================

if __name__ == "__main__":

    os.makedirs(
        STORES_DATABASE_DIR,
        exist_ok=True
    )

    print(
        "Easy Sales Private Store Database Manager is ready."
    )

    print(
        f"ACTIVE LIVE DATA FOLDER: {LIVE_DATA_DIR}"
    )

    print(
        f"STORE DATABASE FOLDER: {STORES_DATABASE_DIR}"
    )
