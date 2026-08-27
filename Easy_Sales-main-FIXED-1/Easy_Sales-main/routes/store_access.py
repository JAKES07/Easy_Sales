"""
Easy Sales - Store Access Gateway
Place this file in:

Easy_Sales/routes/store_access.py

This file does NOT replace your working POS.
It adds the access-control logic that will later sit in front of the POS.
"""

from functools import wraps

from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for

from store_controller import check_access, get_store


store_access_bp = Blueprint("store_access", __name__)


@store_access_bp.route("/store-access", methods=["GET"])
def store_access_page():
    """Show the passkey access page."""
    return render_template("store_access.html")


@store_access_bp.route("/store-access", methods=["POST"])
def store_access_login():
    """
    Check a Store ID and passkey.

    ACTIVE store  -> access is granted and the store ID is saved in the session.
    INACTIVE store -> access is denied.
    Wrong details  -> access is denied.
    """

    data = request.get_json(silent=True)

    if data is None:
        data = request.form

    store_id = str(data.get("store_id", "")).strip().upper()
    passkey = str(data.get("passkey", "")).strip()

    if not store_id or not passkey:
        return jsonify({
            "success": False,
            "code": "MISSING_DETAILS",
            "message": "Enter your Store ID and passkey."
        }), 400

    allowed, result = check_access(store_id, passkey)

    if not allowed:
        session.pop("store_id", None)
        session.pop("store_name", None)

        if result == "STORE_INACTIVE":
            return jsonify({
                "success": False,
                "code": "STORE_INACTIVE",
                "message": (
                    "This store is currently inactive. "
                    "Please contact Easy Sales to reactivate your access."
                )
            }), 403

        if result == "INVALID_PASSKEY":
            return jsonify({
                "success": False,
                "code": "INVALID_PASSKEY",
                "message": "The Store ID or passkey is incorrect."
            }), 401

        return jsonify({
            "success": False,
            "code": "STORE_NOT_FOUND",
            "message": "This store could not be found."
        }), 404

    store = get_store(store_id)

    session["store_id"] = store_id
    session["store_name"] = store["store_name"]

    return jsonify({
        "success": True,
        "message": "Access granted.",
        "store_id": store_id,
        "store_name": store["store_name"]
    })


@store_access_bp.route("/store-access/logout", methods=["POST"])
def store_access_logout():
    """Remove the current store from the browser session."""
    session.pop("store_id", None)
    session.pop("store_name", None)

    return jsonify({
        "success": True,
        "message": "Store access closed."
    })


def current_store():
    """
    Return the currently approved store ID.

    Later, the POS database layer will use this value to select the
    correct client's private database.
    """
    return session.get("store_id")


def require_store_access(view):
    """
    Protect a Flask page or API route.

    If the visitor has not passed the Store ID + passkey check,
    normal pages are redirected to the access screen and API requests
    receive a JSON error.
    """

    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_store():
            return view(*args, **kwargs)

        if request.path.startswith("/api/"):
            return jsonify({
                "success": False,
                "message": "Store access is required."
            }), 401

        return redirect(url_for("store_access.store_access_page"))

    return wrapped
