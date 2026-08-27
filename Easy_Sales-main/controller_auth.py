# ============================================================
# EASY SALES - CONTROLLER AUTHENTICATION
# ============================================================

from functools import wraps
from flask import session, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash

from store_controller import get_connection


def init_controller_auth():
    """Create the controller authentication table if it does not exist."""
    conn = get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS controller_auth (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                password_hash TEXT NOT NULL
            )
        """)
        conn.commit()
    finally:
        conn.close()


def controller_is_configured():
    init_controller_auth()

    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id FROM controller_auth WHERE id = 1"
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def set_controller_password(password):
    password = str(password or "")

    if len(password) < 10:
        raise ValueError(
            "Controller password must contain at least 10 characters."
        )

    password_hash = generate_password_hash(password)

    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO controller_auth (id, password_hash)
            VALUES (1, ?)
            ON CONFLICT(id) DO UPDATE
            SET password_hash = excluded.password_hash
        """, (password_hash,))
        conn.commit()
    finally:
        conn.close()


def verify_controller_password(password):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT password_hash FROM controller_auth WHERE id = 1"
        ).fetchone()

        if row is None:
            return False

        return check_password_hash(
            row["password_hash"],
            str(password or "")
        )
    finally:
        conn.close()


def controller_login_required(view):
    """Protect every controller route with a separate controller session."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("controller_authenticated"):
            return redirect(url_for("controller.login"))
        return view(*args, **kwargs)
    return wrapped
