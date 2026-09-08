# ============================================================
# EASY SALES - STORE CONTROLLER
# ============================================================
#
# The controller database stores:
# - Store IDs
# - Store names
# - Activation status
# - Store passkeys
# - Controller activity
#
# DEVELOPMENT:
#   Easy_Sales/database/controller.db
#
# PRODUCTION:
#   Location set by EASY_SALES_DATA_DIR.
#
# This keeps live controller data separate from the application
# code so future GitHub deployments do not replace store status.
# ============================================================

import os
import sqlite3
import secrets
from datetime import datetime
from pathlib import Path

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from store_database import create_store_database


# ============================================================
# LIVE DATA LOCATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

# Explicit configuration wins. Otherwise automatically use the Render
# persistent disk when it is mounted at /var/data. Local Pydroid keeps
# using the project's database folder.
_configured_data_dir = os.environ.get(
    "EASY_SALES_DATA_DIR",
    ""
).strip()

if _configured_data_dir:
    LIVE_DATA_DIR = Path(
        os.path.abspath(
            os.path.expanduser(_configured_data_dir)
        )
    )
elif os.path.isdir("/var/data"):
    LIVE_DATA_DIR = Path("/var/data")
else:
    LIVE_DATA_DIR = BASE_DIR / "database"

LIVE_DATA_DIR.mkdir(
    parents=True,
    exist_ok=True
)

CONTROLLER_DB = LIVE_DATA_DIR / "controller.db"

STARTING_STORE_COUNT = 50


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():

    conn = sqlite3.connect(
        CONTROLLER_DB,
        timeout=10
    )

    conn.row_factory = sqlite3.Row

    # Controller database safety settings
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 10000")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")

    return conn


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


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


# ============================================================
# STORE ID / PASSKEY GENERATION
# ============================================================

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

    Older stores may still have plain-text passkeys. We keep
    compatibility so existing customers are not locked out.
    """

    value = str(value or "")

    return value.startswith((
        "scrypt:",
        "pbkdf2:"
    ))


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
            notes TEXT,
            employee_mode_feature_enabled INTEGER NOT NULL DEFAULT 0,
            employee_mode_active INTEGER NOT NULL DEFAULT 0,
            employee_mode_password_hash TEXT,
            restaurant_mode_enabled INTEGER NOT NULL DEFAULT 0
        )
    """)

    # Safe upgrades for controller databases created by older Easy_Sales versions.
    _ensure_column(cur, "stores", "employee_mode_feature_enabled", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(cur, "stores", "employee_mode_active", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(cur, "stores", "employee_mode_password_hash", "TEXT")
    _ensure_column(cur, "stores", "restaurant_mode_enabled", "INTEGER NOT NULL DEFAULT 0")

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

    # Only create the starter store spaces on a completely new
    # controller database.
    if existing_count == 0:

        for number in range(
            1,
            STARTING_STORE_COUNT + 1
        ):

            store_id = f"STORE{number:03d}"
            plain_passkey = generate_passkey()

            cur.execute("""
                INSERT INTO stores
                (store_id, store_name, status, passkey,
                 created_at, notes)
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
        raise ValueError(
            "A store name is required."
        )

    store_id = generate_store_id()
    plain_passkey = generate_passkey()

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO stores
        (store_id, store_name, status, passkey,
         created_at, notes)
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

    # The readable passkey is returned only once so the controller
    # can give it to the customer. The database stores only the hash.
    return {
        "store_id": store_id,
        "passkey": plain_passkey,
        "status": "AVAILABLE"
    }


# ============================================================
# STORE NAME UPDATE
# ============================================================

def update_store_name(store_id, store_name):
    """Update the customer-facing business/store name used on receipts."""

    store_id = str(store_id).strip().upper()
    store_name = str(store_name or "").strip()

    if not store_name:
        raise ValueError("A store name is required.")

    if len(store_name) > 120:
        raise ValueError("Store name is too long (maximum 120 characters).")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE stores
        SET store_name=?
        WHERE store_id=?
    """, (store_name, store_id))

    if cur.rowcount == 0:
        conn.close()
        raise ValueError("Store not found.")

    cur.execute("""
        INSERT INTO store_activity
        (store_id, action, description, created_at)
        VALUES (?, ?, ?, ?)
    """, (
        store_id,
        "STORE_NAME_UPDATED",
        f"Store/receipt name changed to: {store_name}",
        now()
    ))

    conn.commit()
    conn.close()


# ============================================================
# EMPLOYEE MODE ADD-ON / PASSWORD CONTROL
# ============================================================

def get_employee_mode_config(store_id):
    """Return the Employee Mode add-on configuration for one store."""
    store_id = str(store_id).strip().upper()
    conn = get_connection()
    try:
        row = conn.execute("""
            SELECT employee_mode_feature_enabled,
                   employee_mode_active,
                   employee_mode_password_hash
            FROM stores
            WHERE store_id=?
        """, (store_id,)).fetchone()
        if row is None:
            raise ValueError("Store not found.")
        return {
            "feature_enabled": bool(row["employee_mode_feature_enabled"]),
            "active": bool(row["employee_mode_active"]),
            "password_configured": bool(row["employee_mode_password_hash"]),
            "password_hash": row["employee_mode_password_hash"]
        }
    finally:
        conn.close()


def set_employee_mode_feature(store_id, enabled):
    """Enable/disable the Employee Mode paid/requested add-on for one store."""
    store_id = str(store_id).strip().upper()
    enabled = 1 if enabled else 0
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE stores
        SET employee_mode_feature_enabled=?,
            employee_mode_active=CASE WHEN ?=0 THEN 0 ELSE employee_mode_active END
        WHERE store_id=?
    """, (enabled, enabled, store_id))
    if cur.rowcount == 0:
        conn.close()
        raise ValueError("Store not found.")
    cur.execute("""
        INSERT INTO store_activity (store_id, action, description, created_at)
        VALUES (?, ?, ?, ?)
    """, (
        store_id,
        "EMPLOYEE_MODE_ADDON_ENABLED" if enabled else "EMPLOYEE_MODE_ADDON_DISABLED",
        "Employee Mode add-on enabled by controller." if enabled else "Employee Mode add-on disabled by controller.",
        now()
    ))
    conn.commit()
    conn.close()


def set_employee_mode_password(store_id, password):
    """Set the store-specific Employee Mode password as a one-way hash."""
    store_id = str(store_id).strip().upper()
    password = str(password or "")
    if len(password) < 4:
        raise ValueError("Employee Mode password must be at least 4 characters.")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE stores
        SET employee_mode_password_hash=?, employee_mode_active=0
        WHERE store_id=?
    """, (generate_password_hash(password), store_id))
    if cur.rowcount == 0:
        conn.close()
        raise ValueError("Store not found.")
    cur.execute("""
        INSERT INTO store_activity (store_id, action, description, created_at)
        VALUES (?, ?, ?, ?)
    """, (store_id, "EMPLOYEE_MODE_PASSWORD_SET", "Employee Mode password set/reset.", now()))
    conn.commit()
    conn.close()


def reset_employee_mode_password(store_id):
    """Clear the store's Employee Mode password so the setup popup appears again."""
    store_id = str(store_id).strip().upper()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE stores
        SET employee_mode_password_hash=NULL, employee_mode_active=0
        WHERE store_id=?
    """, (store_id,))
    if cur.rowcount == 0:
        conn.close()
        raise ValueError("Store not found.")
    cur.execute("""
        INSERT INTO store_activity (store_id, action, description, created_at)
        VALUES (?, ?, ?, ?)
    """, (store_id, "EMPLOYEE_MODE_PASSWORD_RESET", "Employee Mode password cleared; store must create a new password.", now()))
    conn.commit()
    conn.close()


def set_employee_mode_active(store_id, active):
    """Persist the current Employee/Owner mode for a store."""
    store_id = str(store_id).strip().upper()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE stores
        SET employee_mode_active=?
        WHERE store_id=? AND employee_mode_feature_enabled=1 AND employee_mode_password_hash IS NOT NULL
    """, (1 if active else 0, store_id))
    if cur.rowcount == 0:
        conn.close()
        raise ValueError("Employee Mode is not configured for this store.")
    cur.execute("""
        INSERT INTO store_activity (store_id, action, description, created_at)
        VALUES (?, ?, ?, ?)
    """, (
        store_id,
        "EMPLOYEE_MODE_ON" if active else "OWNER_MODE_RESTORED",
        "Employee Mode enabled." if active else "Owner Mode restored.",
        now()
    ))
    conn.commit()
    conn.close()


# ============================================================
# STORE LOOKUPS
# ============================================================

def get_store(store_id):

    conn = get_connection()

    try:

        return conn.execute(
            """
            SELECT *
            FROM stores
            WHERE store_id = ?
            """,
            (
                str(store_id)
                .strip()
                .upper(),
            )
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
                """
                SELECT COUNT(*)
                FROM stores
                WHERE status='ACTIVE'
                """
            ).fetchone()[0],

            "inactive": conn.execute(
                """
                SELECT COUNT(*)
                FROM stores
                WHERE status='INACTIVE'
                """
            ).fetchone()[0],

            "available": conn.execute(
                """
                SELECT COUNT(*)
                FROM stores
                WHERE status='AVAILABLE'
                """
            ).fetchone()[0]
        }

    finally:

        conn.close()


# ============================================================
# ACTIVATE STORE
# ============================================================

def activate_store(store_id):

    store_id = str(
        store_id
    ).strip().upper()

    # Create the private database if this store does not have one.
    # Existing store data is preserved.
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

        raise ValueError(
            "Store not found."
        )

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


# ============================================================
# DEACTIVATE STORE
# ============================================================

def deactivate_store(store_id):

    store_id = str(
        store_id
    ).strip().upper()

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

        raise ValueError(
            "Store not found."
        )

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

    store_id = str(
        store_id
    ).strip().upper()

    plain_passkey = generate_passkey()

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE stores
        SET passkey=?
        WHERE store_id=?
        """,
        (
            hash_passkey(plain_passkey),
            store_id
        )
    )

    if cur.rowcount == 0:

        conn.close()

        raise ValueError(
            "Store not found."
        )

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

    return plain_passkey


# ============================================================
# STORE ACCESS CHECK
# ============================================================

def check_access(store_id, passkey):

    store_id = str(
        store_id
    ).strip().upper()

    entered_passkey = str(
        passkey
    ).strip()

    store = get_store(store_id)

    if store is None:

        return False, "STORE_NOT_FOUND"

    stored_passkey = str(
        store["passkey"] or ""
    )

    # New stores use secure password hashes.
    if is_hashed_passkey(stored_passkey):

        passkey_valid = check_password_hash(
            stored_passkey,
            entered_passkey
        )

    else:

        # Compatibility with existing stores that were created
        # before passkey hashing was added.
        passkey_valid = secrets.compare_digest(
            stored_passkey,
            entered_passkey
        )

        # Upgrade the passkey after a successful login.
        if passkey_valid:

            conn = get_connection()

            try:

                conn.execute(
                    """
                    UPDATE stores
                    SET passkey=?
                    WHERE store_id=?
                    """,
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

    print(
        "Easy Sales Store Controller is ready."
    )
    print(
        f"Controller database: {CONTROLLER_DB}"
    )
    print(
        f"Starting store spaces: {STARTING_STORE_COUNT}"
    )


# ============================================================
# RESTAURANT ADD-ON
# ============================================================
def get_restaurant_mode(store_id):
    conn = get_connection(); row = conn.execute("SELECT restaurant_mode_enabled FROM stores WHERE store_id=?", (str(store_id).upper(),)).fetchone(); conn.close()
    return bool(row and row[0])

def set_restaurant_mode(store_id, enabled):
    sid=str(store_id).upper(); conn=get_connection();
    conn.execute("UPDATE stores SET restaurant_mode_enabled=? WHERE store_id=?", (1 if enabled else 0, sid))
    conn.execute("INSERT INTO store_activity(store_id,action,description,created_at) VALUES(?,?,?,?,?)".replace('VALUES(?,?,?,?,?)','VALUES(?,?,?,?)'), (sid, "RESTAURANT_ADDON_ENABLED" if enabled else "RESTAURANT_ADDON_DISABLED", "Restaurant add-on " + ("enabled" if enabled else "disabled"), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit(); conn.close()
    if enabled:
        try:
            from restaurant import init_restaurant_db
            init_restaurant_db(sid)
        except Exception:
            pass
