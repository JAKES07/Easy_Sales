# ============================================================
# EASY SALES - PRIVATE STORE DATABASE MANAGER
# ============================================================
#
# Each client store has its own private database.
#
# DEVELOPMENT:
#   Easy_Sales/database/stores/STORE001.db
#
# PRODUCTION:
#   Location set by EASY_SALES_DATA_DIR.
#
# IMPORTANT:
# Customer data is stored separately from the application code so
# deployments can update Easy Sales without replacing live data.
# ============================================================

import os
import re
import sqlite3


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ------------------------------------------------------------
# LIVE DATA DIRECTORY
# ------------------------------------------------------------
# On your local Pydroid3 setup, this uses:
# Easy_Sales/database
#
# On Render, we will set EASY_SALES_DATA_DIR to the persistent
# disk location.
# ------------------------------------------------------------

LIVE_DATA_DIR = os.environ.get(
    "EASY_SALES_DATA_DIR",
    os.path.join(BASE_DIR, "database")
)

STORES_DATABASE_DIR = os.path.join(
    LIVE_DATA_DIR,
    "stores"
)


def _clean_store_id(store_id):
    """Validate and normalise a store ID before using it as a filename."""
    store_id = str(store_id or "").strip().upper()

    if not re.fullmatch(r"[A-Z0-9-]{3,64}", store_id):
        raise ValueError("Invalid Store ID.")

    return store_id


def get_store_database_path(store_id):
    """Return the private database path for one store."""
    store_id = _clean_store_id(store_id)

    return os.path.join(
        STORES_DATABASE_DIR,
        f"{store_id}.db"
    )


def get_store_connection(store_id):
    """Open a connection to one store's private database."""

    database_path = get_store_database_path(store_id)

    os.makedirs(
        STORES_DATABASE_DIR,
        exist_ok=True
    )

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


def _ensure_column(cursor, table_name, column_name, definition):
    """Add a column safely when upgrading an older store database."""

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


def create_store_database(store_id):
    """
    Create the private Easy Sales database for a store if it does not
    already exist.

    Safe to run repeatedly. Existing products, sales and stock are
    never deleted by this function.
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

    # --------------------------------------------------------
    # SAFE DATABASE UPGRADES
    # --------------------------------------------------------

    _ensure_column(cursor, "products", "barcode", "TEXT")
    _ensure_column(cursor, "sales", "transaction_id", "TEXT")
    _ensure_column(
        cursor,
        "sales",
        "sale_fee",
        "REAL NOT NULL DEFAULT 0"
    )

    _ensure_column(
        cursor,
        "monthly_reports",
        "cash_sales_count",
        "INTEGER NOT NULL DEFAULT 0"
    )
    _ensure_column(
        cursor,
        "monthly_reports",
        "cash_sales_amount",
        "REAL NOT NULL DEFAULT 0"
    )
    _ensure_column(
        cursor,
        "monthly_reports",
        "card_sales_count",
        "INTEGER NOT NULL DEFAULT 0"
    )
    _ensure_column(
        cursor,
        "monthly_reports",
        "card_sales_amount",
        "REAL NOT NULL DEFAULT 0"
    )
    _ensure_column(
        cursor,
        "monthly_reports",
        "total_sales_count",
        "INTEGER NOT NULL DEFAULT 0"
    )
    _ensure_column(
        cursor,
        "monthly_reports",
        "total_sales_amount",
        "REAL NOT NULL DEFAULT 0"
    )
    _ensure_column(
        cursor,
        "monthly_reports",
        "total_sales_units",
        "INTEGER NOT NULL DEFAULT 0"
    )

    # Give older sales a transaction ID if they do not have one.
    cursor.execute("""
        UPDATE sales
        SET transaction_id = 'LEGACY-' || id
        WHERE transaction_id IS NULL OR transaction_id = ''
    """)

    connection.commit()
    connection.close()

    return get_store_database_path(store_id)


def store_database_exists(store_id):
    """Check whether a private database already exists for a store."""

    return os.path.exists(
        get_store_database_path(store_id)
    )


# ============================================================
# RESET ONE STORE'S POS DATA
# ============================================================

def reset_store_data(store_id):
    """
    Reset ONLY the POS data belonging to one store.

    The store's controller account and activation status are NOT
    changed. Other stores are completely untouched.
    """

    store_id = _clean_store_id(store_id)

    create_store_database(store_id)

    connection = get_store_connection(store_id)
    cursor = connection.cursor()

    try:

        # History tables first.
        cursor.execute("DELETE FROM monthly_report_items")
        cursor.execute("DELETE FROM monthly_reports")
        cursor.execute("DELETE FROM stock_takes")
        cursor.execute("DELETE FROM stock_movements")
        cursor.execute("DELETE FROM sales")

        # Products are removed last.
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

    os.makedirs(
        STORES_DATABASE_DIR,
        exist_ok=True
    )

    print("Easy Sales Private Store Database Manager is ready.")
    print(f"Live data folder: {LIVE_DATA_DIR}")
    print(f"Store databases folder: {STORES_DATABASE_DIR}")    conn.execute("PRAGMA busy_timeout = 10000")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")

    return conn


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def generate_store_id():
    return "ES-" + secrets.token_hex(4).upper()


def generate_passkey():
    return "KEY-" + secrets.token_urlsafe(8)


def hash_passkey(passkey):
    """Create a secure one-way hash for a store passkey."""
    return generate_password_hash(passkey)


def is_hashed_passkey(value):
    """
    Detect Werkzeug password hashes.

    Existing stores may still contain their old plain-text passkeys.
    """
    value = str(value or "")
    return value.startswith(("scrypt:", "pbkdf2:"))


# ============================================================
# INITIALISE CONTROLLER DATABASE
# ============================================================

def init_controller():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS stores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id TEXT NOT NULL UNIQUE,
            store_name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'INACTIVE',
            passkey TEXT NOT NULL,
            created_at TEXT NOT NULL,
            activated_at TEXT,
            deactivated_at TEXT,
            notes TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS store_activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id TEXT NOT NULL,
            action TEXT NOT NULL,
            description TEXT,
            created_at TEXT NOT NULL
        )
    """)

    existing_count = cur.execute(
        "SELECT COUNT(*) FROM stores"
    ).fetchone()[0]

    # Only create the starter store spaces on a completely new database.
    if existing_count == 0:

        for number in range(1, STARTING_STORE_COUNT + 1):

            store_id = f"STORE{number:03d}"
            plain_passkey = generate_passkey()

            cur.execute("""
                INSERT INTO stores
                (store_id, store_name, status, passkey, created_at, notes)
                VALUES (?, ?, 'AVAILABLE', ?, ?, ?)
            """, (
                store_id,
                f"Store Space {number:03d}",
                hash_passkey(plain_passkey),
                now(),
                "Initial Easy Sales store space"
            ))

            cur.execute("""
                INSERT INTO store_activity
                (store_id, action, description, created_at)
                VALUES (?, ?, ?, ?)
            """, (
                store_id,
                "SPACE_CREATED",
                "Initial store space created",
                now()
            ))

    conn.commit()
    conn.close()


# ============================================================
# CREATE A NEW CLIENT STORE
# ============================================================

def create_store(store_name, notes=""):

    store_name = str(store_name).strip()

    if not store_name:
        raise ValueError("A store name is required.")

    store_id = generate_store_id()
    plain_passkey = generate_passkey()

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO stores
        (store_id, store_name, status, passkey, created_at, notes)
        VALUES (?, ?, 'AVAILABLE', ?, ?, ?)
    """, (
        store_id,
        store_name,
        hash_passkey(plain_passkey),
        now(),
        str(notes).strip()
    ))

    cur.execute("""
        INSERT INTO store_activity
        (store_id, action, description, created_at)
        VALUES (?, ?, ?, ?)
    """, (
        store_id,
        "CREATED",
        "Additional store space created",
        now()
    ))

    conn.commit()
    conn.close()

    # Return the plain passkey ONCE so the controller can give it
    # to the client. Only the hash is stored in the database.
    return {
        "store_id": store_id,
        "passkey": plain_passkey,
        "status": "AVAILABLE"
    }


# ============================================================
# STORE LOOKUPS
# ============================================================

def get_store(store_id):

    conn = get_connection()

    try:
        return conn.execute(
            "SELECT * FROM stores WHERE store_id = ?",
            (str(store_id).strip().upper(),)
        ).fetchone()

    finally:
        conn.close()


def get_all_stores():

    conn = get_connection()

    try:
        return conn.execute(
            "SELECT * FROM stores ORDER BY id ASC"
        ).fetchall()

    finally:
        conn.close()


def get_store_counts():

    conn = get_connection()

    try:
        return {
            "total": conn.execute(
                "SELECT COUNT(*) FROM stores"
            ).fetchone()[0],

            "active": conn.execute(
                "SELECT COUNT(*) FROM stores WHERE status='ACTIVE'"
            ).fetchone()[0],

            "inactive": conn.execute(
                "SELECT COUNT(*) FROM stores WHERE status='INACTIVE'"
            ).fetchone()[0],

            "available": conn.execute(
                "SELECT COUNT(*) FROM stores WHERE status='AVAILABLE'"
            ).fetchone()[0]
        }

    finally:
        conn.close()


# ============================================================
# ACTIVATE / DEACTIVATE STORE
# ============================================================

def activate_store(store_id):

    store_id = str(store_id).strip().upper()

    create_store_database(store_id)

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE stores
        SET status='ACTIVE',
            activated_at=?,
            deactivated_at=NULL
        WHERE store_id=?
    """, (
        now(),
        store_id
    ))

    if cur.rowcount == 0:
        conn.close()
        raise ValueError("Store not found.")

    cur.execute("""
        INSERT INTO store_activity
        (store_id, action, description, created_at)
        VALUES (?, ?, ?, ?)
    """, (
        store_id,
        "ACTIVATED",
        "Store manually activated",
        now()
    ))

    conn.commit()
    conn.close()


def deactivate_store(store_id):

    store_id = str(store_id).strip().upper()

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE stores
        SET status='INACTIVE',
            deactivated_at=?
        WHERE store_id=?
    """, (
        now(),
        store_id
    ))

    if cur.rowcount == 0:
        conn.close()
        raise ValueError("Store not found.")

    cur.execute("""
        INSERT INTO store_activity
        (store_id, action, description, created_at)
        VALUES (?, ?, ?, ?)
    """, (
        store_id,
        "DEACTIVATED",
        "Store access manually disabled",
        now()
    ))

    conn.commit()
    conn.close()


# ============================================================
# RESET STORE PASSKEY
# ============================================================

def reset_passkey(store_id):

    store_id = str(store_id).strip().upper()
    plain_passkey = generate_passkey()

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "UPDATE stores SET passkey=? WHERE store_id=?",
        (
            hash_passkey(plain_passkey),
            store_id
        )
    )

    if cur.rowcount == 0:
        conn.close()
        raise ValueError("Store not found.")

    cur.execute("""
        INSERT INTO store_activity
        (store_id, action, description, created_at)
        VALUES (?, ?, ?, ?)
    """, (
        store_id,
        "PASSKEY_RESET",
        "Store passkey reset",
        now()
    ))

    conn.commit()
    conn.close()

    # The new readable passkey is returned once to the controller.
    return plain_passkey


# ============================================================
# SECURE STORE ACCESS CHECK
# ============================================================

def check_access(store_id, passkey):

    store_id = str(store_id).strip().upper()
    entered_passkey = str(passkey).strip()

    store = get_store(store_id)

    if store is None:
        return False, "STORE_NOT_FOUND"

    stored_passkey = str(store["passkey"] or "")

    # New stores use a secure password hash.
    if is_hashed_passkey(stored_passkey):

        passkey_valid = check_password_hash(
            stored_passkey,
            entered_passkey
        )

    else:
        # Temporary compatibility for stores created before hashing.
        # If the correct old passkey is used, upgrade it immediately.
        passkey_valid = secrets.compare_digest(
            stored_passkey,
            entered_passkey
        )

        if passkey_valid:
            conn = get_connection()

            try:
                conn.execute(
                    "UPDATE stores SET passkey=? WHERE store_id=?",
                    (
                        hash_passkey(entered_passkey),
                        store_id
                    )
                )

                conn.commit()

            finally:
                conn.close()

    if not passkey_valid:
        return False, "INVALID_PASSKEY"

    if store["status"] == "AVAILABLE":
        return False, "STORE_AVAILABLE"

    if store["status"] != "ACTIVE":
        return False, "STORE_INACTIVE"

    return True, "ACCESS_GRANTED"


# ============================================================
# STARTUP
# ============================================================

if __name__ == "__main__":

    init_controller()

    print("Easy Sales Store Controller is ready.")
    print(f"Controller database: {CONTROLLER_DB}")
    print(f"Starting store spaces: {STARTING_STORE_COUNT}")
