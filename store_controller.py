# EASY SALES - STORE CONTROLLER (UPDATED)
import sqlite3
import secrets
from datetime import datetime
from pathlib import Path
from store_database import create_store_database

BASE_DIR = Path(__file__).resolve().parent
DATABASE_DIR = BASE_DIR / "database"
DATABASE_DIR.mkdir(exist_ok=True)
CONTROLLER_DB = DATABASE_DIR / "controller.db"
STARTING_STORE_COUNT = 50

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

def generate_store_id():
    return "ES-" + secrets.token_hex(4).upper()

def generate_passkey():
    return "KEY-" + secrets.token_urlsafe(8)

def init_controller():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS stores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        store_id TEXT NOT NULL UNIQUE,
        store_name TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'INACTIVE',
        passkey TEXT NOT NULL,
        created_at TEXT NOT NULL,
        activated_at TEXT,
        deactivated_at TEXT,
        notes TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS store_activity (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        store_id TEXT NOT NULL,
        action TEXT NOT NULL,
        description TEXT,
        created_at TEXT NOT NULL
    )""")
    existing_count = cur.execute("SELECT COUNT(*) FROM stores").fetchone()[0]
    if existing_count == 0:
        for number in range(1, STARTING_STORE_COUNT + 1):
            store_id = f"STORE{number:03d}"
            cur.execute("""INSERT INTO stores
                (store_id, store_name, status, passkey, created_at, notes)
                VALUES (?, ?, 'AVAILABLE', ?, ?, ?)""",
                (store_id, f"Store Space {number:03d}", generate_passkey(),
                 now(), "Initial Easy Sales store space"))
            cur.execute("""INSERT INTO store_activity
                (store_id, action, description, created_at)
                VALUES (?, ?, ?, ?)""",
                (store_id, "SPACE_CREATED", "Initial store space created", now()))
    conn.commit()
    conn.close()

def create_store(store_name, notes=""):
    store_name = str(store_name).strip()
    if not store_name:
        raise ValueError("A store name is required.")
    store_id = generate_store_id()
    passkey = generate_passkey()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""INSERT INTO stores
        (store_id, store_name, status, passkey, created_at, notes)
        VALUES (?, ?, 'AVAILABLE', ?, ?, ?)""",
        (store_id, store_name, passkey, now(), str(notes).strip()))
    cur.execute("""INSERT INTO store_activity
        (store_id, action, description, created_at)
        VALUES (?, ?, ?, ?)""",
        (store_id, "CREATED", "Additional store space created", now()))
    conn.commit()
    conn.close()
    return {"store_id": store_id, "passkey": passkey, "status": "AVAILABLE"}

def get_store(store_id):
    conn = get_connection()
    try:
        return conn.execute("SELECT * FROM stores WHERE store_id = ?",
                            (str(store_id).strip().upper(),)).fetchone()
    finally:
        conn.close()

def get_all_stores():
    conn = get_connection()
    try:
        return conn.execute("SELECT * FROM stores ORDER BY id ASC").fetchall()
    finally:
        conn.close()

def get_store_counts():
    conn = get_connection()
    try:
        return {
            "total": conn.execute("SELECT COUNT(*) FROM stores").fetchone()[0],
            "active": conn.execute("SELECT COUNT(*) FROM stores WHERE status='ACTIVE'").fetchone()[0],
            "inactive": conn.execute("SELECT COUNT(*) FROM stores WHERE status='INACTIVE'").fetchone()[0],
            "available": conn.execute("SELECT COUNT(*) FROM stores WHERE status='AVAILABLE'").fetchone()[0]
        }
    finally:
        conn.close()

def activate_store(store_id):
    store_id = str(store_id).strip().upper()
    create_store_database(store_id)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""UPDATE stores SET status='ACTIVE', activated_at=?,
        deactivated_at=NULL WHERE store_id=?""", (now(), store_id))
    if cur.rowcount == 0:
        conn.close()
        raise ValueError("Store not found.")
    cur.execute("""INSERT INTO store_activity
        (store_id, action, description, created_at)
        VALUES (?, ?, ?, ?)""",
        (store_id, "ACTIVATED", "Store manually activated", now()))
    conn.commit()
    conn.close()

def deactivate_store(store_id):
    store_id = str(store_id).strip().upper()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE stores SET status='INACTIVE', deactivated_at=? WHERE store_id=?",
                (now(), store_id))
    if cur.rowcount == 0:
        conn.close()
        raise ValueError("Store not found.")
    cur.execute("""INSERT INTO store_activity
        (store_id, action, description, created_at)
        VALUES (?, ?, ?, ?)""",
        (store_id, "DEACTIVATED", "Store access manually disabled", now()))
    conn.commit()
    conn.close()

def reset_passkey(store_id):
    store_id = str(store_id).strip().upper()
    new_passkey = generate_passkey()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE stores SET passkey=? WHERE store_id=?", (new_passkey, store_id))
    if cur.rowcount == 0:
        conn.close()
        raise ValueError("Store not found.")
    cur.execute("""INSERT INTO store_activity
        (store_id, action, description, created_at)
        VALUES (?, ?, ?, ?)""",
        (store_id, "PASSKEY_RESET", "Store passkey reset", now()))
    conn.commit()
    conn.close()
    return new_passkey

def check_access(store_id, passkey):
    store = get_store(store_id)
    if store is None:
        return False, "STORE_NOT_FOUND"
    if store["passkey"] != str(passkey).strip():
        return False, "INVALID_PASSKEY"
    if store["status"] == "AVAILABLE":
        return False, "STORE_AVAILABLE"
    if store["status"] != "ACTIVE":
        return False, "STORE_INACTIVE"
    return True, "ACCESS_GRANTED"

if __name__ == "__main__":
    init_controller()
    print("Easy Sales Store Controller is ready.")
    print(f"Controller database: {CONTROLLER_DB}")
    print(f"Starting store spaces: {STARTING_STORE_COUNT}")
