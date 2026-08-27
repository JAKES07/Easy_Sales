# ============================================================
# EASY SALES - CURRENT STORE CONTEXT
# ============================================================
#
# Place this file in:
# Easy_Sales/store_context.py
#
# PURPOSE
# -------
# This file gives the Easy Sales website one simple way to know
# WHICH CLIENT STORE is currently open.
#
# The store_access system will put the approved store ID into the
# Flask session. From then on, the rest of the website can use this
# file to open ONLY that store's private database.
#
# IMPORTANT:
# This is one of the pieces that prevents STORE001 from accidentally
# reading or writing STORE002's data.
# ============================================================

from functools import wraps

from flask import session, redirect, url_for, abort

from store_database import get_store_connection


SESSION_STORE_KEY = "easy_sales_store_id"


def set_current_store(store_id):
    """
    Save the approved store ID in the current browser session.

    This should only be called after the passkey/access system has
    successfully verified that the store is active.
    """
    store_id = str(store_id or "").strip().upper()

    if not store_id:
        raise ValueError("A valid Store ID is required.")

    session[SESSION_STORE_KEY] = store_id


def get_current_store_id():
    """
    Return the Store ID for the currently approved client session.

    Returns None when no store has been opened yet.
    """
    store_id = session.get(SESSION_STORE_KEY)

    if not store_id:
        return None

    return str(store_id).strip().upper()


def clear_current_store():
    """
    Remove the currently open store from the browser session.

    We will use this when access is revoked, when a client logs out,
    or when a passkey changes.
    """
    session.pop(SESSION_STORE_KEY, None)


def get_current_store_connection():
    """
    Open the private database for the currently approved store.

    Example:
        connection = get_current_store_connection()

    This automatically opens:
        database/stores/STORE001.db

    instead of a shared database containing everybody's information.
    """
    store_id = get_current_store_id()

    if not store_id:
        raise PermissionError(
            "No approved store is open in this session."
        )

    return get_store_connection(store_id)


def store_access_required(view_function):
    """
    Flask decorator that protects a page.

    A visitor cannot open a protected Easy Sales page unless the
    store access system has already approved a Store ID for their
    browser session.
    """

    @wraps(view_function)
    def wrapped_view(*args, **kwargs):
        if not get_current_store_id():
            return redirect(url_for("store_access.store_access_page"))

        return view_function(*args, **kwargs)

    return wrapped_view


def require_current_store():
    """
    Use this inside routes that should fail immediately when no
    approved store exists.
    """
    store_id = get_current_store_id()

    if not store_id:
        abort(403)

    return store_id


if __name__ == "__main__":
    print("Easy Sales Store Context is ready.")
    print("This file will connect an approved client session")
    print("to that client's private store database.")
