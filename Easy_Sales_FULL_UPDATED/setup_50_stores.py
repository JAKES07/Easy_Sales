"""
Easy Sales - 50 Store Space Setup
This file creates the store_spaces table inside database/controller.db
and safely adds STORE001 through STORE050.

It can be run more than once without creating duplicate stores.
"""

import os
import sqlite3
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_DIR = os.path.join(BASE_DIR, "database")
CONTROLLER_DB = os.path.join(DATABASE_DIR, "controller.db")


def setup_store_spaces():
    os.makedirs(DATABASE_DIR, exist_ok=True)

    conn = sqlite3.connect(CONTROLLER_DB)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS store_spaces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_code TEXT UNIQUE NOT NULL,
            status TEXT NOT NULL DEFAULT 'AVAILABLE',
            client_name TEXT,
            client_store_name TEXT,
            passkey TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    added = 0
    for number in range(1, 51):
        store_code = f"STORE{number:03d}"

        cursor.execute("""
            INSERT OR IGNORE INTO store_spaces
            (store_code, status, created_at, updated_at)
            VALUES (?, 'AVAILABLE', ?, ?)
        """, (store_code, now, now))

        if cursor.rowcount > 0:
            added += 1

    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM store_spaces")
    total = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM store_spaces WHERE status = 'AVAILABLE'"
    )
    available = cursor.fetchone()[0]

    conn.close()

    print("Easy Sales Store Spaces are ready.")
    print(f"Database: {CONTROLLER_DB}")
    print(f"Stores added this run: {added}")
    print(f"Total store spaces: {total}")
    print(f"Available spaces: {available}")
    print("\nExample spaces: STORE001 ... STORE050")


if __name__ == "__main__":
    setup_store_spaces()
