"""
Easy Sales Store Manager
Step 3: Assign clients to store spaces and control their access.

Run this file once to test the manager. It uses:
database/controller.db
"""

import os
import sqlite3
import secrets
import hashlib
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONTROLLER_DB = os.path.join(BASE_DIR, "database", "controller.db")


def get_connection():
    return sqlite3.connect(CONTROLLER_DB)


def ensure_columns():
    """Adds security columns if they do not already exist."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(store_spaces)")
    columns = {row[1] for row in cursor.fetchall()}

    if "passkey_hash" not in columns:
        cursor.execute("ALTER TABLE store_spaces ADD COLUMN passkey_hash TEXT")

    if "passkey_salt" not in columns:
        cursor.execute("ALTER TABLE store_spaces ADD COLUMN passkey_salt TEXT")

    conn.commit()
    conn.close()


def hash_passkey(passkey, salt):
    return hashlib.pbkdf2_hmac(
        "sha256",
        passkey.encode("utf-8"),
        salt.encode("utf-8"),
        100_000
    ).hex()


def generate_passkey():
    """Creates a strong passkey for a client."""
    return secrets.token_urlsafe(9)


def activate_store(store_code, client_name, store_name):
    """
    Assigns a client to an AVAILABLE store, activates access,
    and returns the new passkey ONCE.
    """
    ensure_columns()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT status, client_name FROM store_spaces WHERE store_code = ?",
        (store_code.upper(),)
    )
    store = cursor.fetchone()

    if not store:
        conn.close()
        return False, "Store space does not exist."

    if store[0] != "AVAILABLE":
        conn.close()
        return False, f"{store_code.upper()} is already assigned to {store[1]}."

    passkey = generate_passkey()
    salt = secrets.token_hex(16)
    passkey_hash = hash_passkey(passkey, salt)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        UPDATE store_spaces
        SET status = 'ACTIVE',
            client_name = ?,
            client_store_name = ?,
            passkey = NULL,
            passkey_hash = ?,
            passkey_salt = ?,
            updated_at = ?
        WHERE store_code = ?
    """, (
        client_name,
        store_name,
        passkey_hash,
        salt,
        now,
        store_code.upper()
    ))

    conn.commit()
    conn.close()

    return True, passkey


def deactivate_store(store_code):
    """
    Disables access but keeps the client's store assignment and data.
    """
    conn = get_connection()
    cursor = conn.cursor()

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        UPDATE store_spaces
        SET status = 'INACTIVE',
            updated_at = ?
        WHERE store_code = ?
          AND status = 'ACTIVE'
    """, (now, store_code.upper()))

    changed = cursor.rowcount
    conn.commit()
    conn.close()

    if changed:
        return True, f"{store_code.upper()} has been deactivated. Client data is kept."
    return False, "Store was not active or does not exist."


def reactivate_store(store_code):
    """Restores access to the same client and store."""
    conn = get_connection()
    cursor = conn.cursor()

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        UPDATE store_spaces
        SET status = 'ACTIVE',
            updated_at = ?
        WHERE store_code = ?
          AND status = 'INACTIVE'
    """, (now, store_code.upper()))

    changed = cursor.rowcount
    conn.commit()
    conn.close()

    if changed:
        return True, f"{store_code.upper()} is active again."
    return False, "Store was not inactive or does not exist."


def verify_store_access(store_code, entered_passkey):
    """
    Used later by the website popup.
    Returns: ACTIVE, INACTIVE, or DENIED.
    """
    ensure_columns()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT status, passkey_hash, passkey_salt
        FROM store_spaces
        WHERE store_code = ?
    """, (store_code.upper(),))

    row = cursor.fetchone()
    conn.close()

    if not row:
        return "DENIED"

    status, saved_hash, salt = row

    if not saved_hash or not salt:
        return "DENIED"

    entered_hash = hash_passkey(entered_passkey, salt)

    if not secrets.compare_digest(entered_hash, saved_hash):
        return "DENIED"

    if status == "ACTIVE":
        return "ACTIVE"

    if status == "INACTIVE":
        return "INACTIVE"

    return "DENIED"


def show_store(store_code):
    """Shows basic store information without exposing the passkey."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT store_code, status, client_name, client_store_name, updated_at
        FROM store_spaces
        WHERE store_code = ?
    """, (store_code.upper(),))

    row = cursor.fetchone()
    conn.close()

    return row


if __name__ == "__main__":
    ensure_columns()

    print("Easy Sales Store Manager is ready.")
    print("Controller database:", CONTROLLER_DB)
    print()
    print("The manager can now:")
    print("1. Activate a store for a client")
    print("2. Generate a secure passkey")
    print("3. Deactivate access without deleting the client")
    print("4. Reactivate the same store later")
    print("5. Verify a passkey for website access")
    print()
    print("No client store has been assigned yet.")
