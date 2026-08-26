# ====# ============================================================
# EASY SALES - MAIN APPLICATION
# ============================================================

import os
from datetime import timedelta

from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    session,
    redirect,
    url_for
)
import sqlite3
from werkzeug.middleware.proxy_fix import ProxyFix

from database import (
    create_database,
    add_product,
    update_product,
    get_all_products,
    get_product_by_barcode,
    complete_sale,
    get_stock_take,
    get_today_sales,
    add_stock,
    remove_stock,
    record_stocktake,
    get_stock_movements,
    get_stocktake_history,
    create_monthly_report,
    get_monthly_reports,
    get_monthly_sales_summary,
    get_connection
)

from store_controller import init_controller, get_store
from store_database import get_live_data_dir

from routes.store_access import store_access_bp
from routes.store_controller_routes import controller_bp


# ============================================================
# CREATE FLASK APPLICATION
# ============================================================

app = Flask(__name__)


# ============================================================
# PRODUCTION DEPLOYMENT SETTINGS
# ============================================================

EASY_SALES_ENV = os.environ.get(
    "EASY_SALES_ENV",
    "development"
).lower()

DEFAULT_DEVELOPMENT_SECRET = (
    "easy-sales-local-development-change-this-before-production"
)

configured_secret = os.environ.get(
    "EASY_SALES_SECRET_KEY"
)

if EASY_SALES_ENV == "production" and not configured_secret:
    raise RuntimeError(
        "EASY_SALES_SECRET_KEY must be set in production."
    )

if EASY_SALES_ENV == "production":
    app.wsgi_app = ProxyFix(
        app.wsgi_app,
        x_for=1,
        x_proto=1,
        x_host=1
    )


# ============================================================
# FLASK SESSION SETTINGS
# ============================================================

app.config["SECRET_KEY"] = (
    configured_secret or DEFAULT_DEVELOPMENT_SECRET
)

app.config["SESSION_COOKIE_HTTPONLY"] = True

app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

app.config["SESSION_COOKIE_SECURE"] = (
    EASY_SALES_ENV == "production"
    or os.environ.get(
        "EASY_SALES_HTTPS",
        "0"
    ) == "1"
)

app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(
    hours=8
)


# ============================================================
# INITIALISE EASY SALES SYSTEMS
# ============================================================

# Existing POS database startup hook.
# Store databases themselves are created per store.
create_database()

# Store controller database.
init_controller()

# ============================================================
# CONFIRM ACTIVE LIVE DATABASE LOCATION
# ============================================================

print("=" * 60)
print("EASY SALES STARTED")
print(
    f"ACTIVE POS DATA DIRECTORY: "
    f"{get_live_data_dir()}"
)
print("=" * 60)


# ============================================================
# REGISTER BLUEPRINTS
# ============================================================

# Store ID + passkey gateway.
app.register_blueprint(
    store_access_bp
)

# Easy Sales owner/controller dashboard.
app.register_blueprint(
    controller_bp
)


# ============================================================
# STORE ACCESS SUCCESS REDIRECT
# ============================================================

@app.after_request
def redirect_successful_store_access(response):
    """
    The Store Access route returns JSON for programmatic use, but a normal
    browser form submission must continue straight into the POS.
    """

    if (
        request.method == "POST"
        and request.path.rstrip("/") == "/store-access"
        and response.is_json
        and response.status_code < 300
    ):

        data = response.get_json(
            silent=True
        ) or {}

        if data.get("success") is True:

            return redirect(
                url_for("home")
            )

    return response


# ============================================================
# BASIC PRODUCTION SECURITY HEADERS
# ============================================================

@app.after_request
def add_security_headers(response):

    response.headers.setdefault(
        "X-Content-Type-Options",
        "nosniff"
    )

    response.headers.setdefault(
        "X-Frame-Options",
        "SAMEORIGIN"
    )

    response.headers.setdefault(
        "Referrer-Policy",
        "strict-origin-when-cross-origin"
    )

    return response


# ============================================================
# STORE ACCESS GUARD
# ============================================================

@app.before_request
def enforce_store_access():
    """
    Keep the Store Access gateway in front of the POS and every POS API.

    This also checks the controller on each request, so if the owner
    deactivates a store, an already-open browser session loses access
    on its next request.
    """

    # Static files must always remain reachable.
    if request.endpoint == "static":
        return None

    # Store Access gateway remains reachable before login.
    if request.path.startswith(
        "/store-access"
    ):
        return None

    # Controller dashboard is separate from customer store access.
    if request.path.startswith(
        "/controller"
    ):
        return None

    # Only POS home page and POS API are protected here.
    if (
        request.path != "/"
        and not request.path.startswith("/api/")
    ):
        return None

    store_id = session.get(
        "store_id"
    )

    if not store_id:

        if request.path.startswith(
            "/api/"
        ):

            return jsonify({
                "success": False,
                "code": "STORE_ACCESS_REQUIRED",
                "message": (
                    "Store access is required."
                )
            }), 401

        return redirect(
            url_for(
                "store_access.store_access_page"
            )
        )

    store = get_store(
        store_id
    )

    if (
        store is None
        or store["status"] != "ACTIVE"
    ):

        session.pop(
            "store_id",
            None
        )

        session.pop(
            "store_name",
            None
        )

        session.pop(
            "store_authenticated_at",
            None
        )

        if request.path.startswith(
            "/api/"
        ):

            return jsonify({
                "success": False,
                "code": "STORE_INACTIVE",
                "message": (
                    "Your Easy Sales store is currently inactive. "
                    "Please contact Easy Sales to reactivate access."
                )
            }), 403

        return redirect(
            url_for(
                "store_access.store_access_page",
                status="inactive"
            )
        )

    return None


# ============================================================
# HOME / POS SCREEN
# ============================================================

@app.route("/")
def home():

    return render_template(
        "pos.html",
        store_id=session.get("store_id"),
        store_name=session.get("store_name")
    )


# ============================================================
# GET ALL PRODUCTS
# ============================================================

@app.route(
    "/api/products",
    methods=["GET"]
)
def get_products():

    try:

        products = get_all_products()

        return jsonify({
            "success": True,
            "products": products
        })

    except Exception as error:

        print(
            "GET PRODUCTS ERROR:",
            error
        )

        return jsonify({
            "success": False,
            "message": (
                "Could not load products."
            )
        }), 500


# ============================================================
# FIND PRODUCT BY BARCODE
# ============================================================

@app.route(
    "/api/products/barcode/<path:barcode>",
    methods=["GET"]
)
def find_product_by_barcode(barcode):

    barcode = str(
        barcode
    ).strip()

    if not barcode:

        return jsonify({
            "success": False,
            "message": (
                "Barcode is required."
            )
        }), 400

    try:

        print(
            "EASY SALES BARCODE LOOKUP:",
            repr(barcode)
        )

        product = get_product_by_barcode(
            barcode
        )

        if not product:

            print(
                "BARCODE NOT FOUND:",
                repr(barcode)
            )

            return jsonify({
                "success": False,
                "message": (
                    "No product is registered with this barcode."
                )
            }), 404

        print(
            "BARCODE PRODUCT FOUND:",
            product["name"]
        )

        return jsonify({
            "success": True,
            "product": product
        })

    except Exception as error:

        print(
            "BARCODE LOOKUP ERROR:",
            error
        )

        return jsonify({
            "success": False,
            "message": (
                "Could not look up barcode."
            )
        }), 500


# ============================================================
# ADD NEW PRODUCT
# ============================================================

@app.route(
    "/api/products",
    methods=["POST"]
)
def save_product():

    data = request.get_json(
        silent=True
    )

    if not data:

        return jsonify({
            "success": False,
            "message": (
                "No product data received."
            )
        }), 400

    name = str(
        data.get(
            "name",
            ""
        )
    ).strip()

    barcode = str(
        data.get(
            "barcode",
            ""
        )
    ).strip()

    try:

        price = float(
            data.get(
                "price",
                0
            )
        )

    except (
        ValueError,
        TypeError
    ):

        return jsonify({
            "success": False,
            "message": (
                "Invalid price."
            )
        }), 400

    try:

        stock = int(
            data.get(
                "stock",
                0
            )
        )

    except (
        ValueError,
        TypeError
    ):

        return jsonify({
            "success": False,
            "message": (
                "Invalid stock."
            )
        }), 400

    # Barcode is optional.
    if barcode and not barcode.isdigit():

        return jsonify({
            "success": False,
            "message": (
                "Barcode must contain numbers only."
            )
        }), 400

    if not name:

        return jsonify({
            "success": False,
            "message": (
                "Product name is required."
            )
        }), 400

    if price < 0:

        return jsonify({
            "success": False,
            "message": (
                "Price cannot be negative."
            )
        }), 400

    if stock < 0:

        return jsonify({
            "success": False,
            "message": (
                "Stock cannot be negative."
            )
        }), 400

    try:

        product_id = add_product(
            name,
            price,
            stock,
            barcode
        )

        return jsonify({
            "success": True,
            "message": (
                "Product saved successfully."
            ),
            "product": {
                "id": product_id,
                "name": name,
                "price": price,
                "stock": stock,
                "barcode": barcode or None
            }
        })

    except sqlite3.IntegrityError as error:

        print(
            "SAVE PRODUCT INTEGRITY ERROR:",
            error
        )

        return jsonify({
            "success": False,
            "message": (
                "The product could not be saved because "
                "of a database constraint."
            )
        }), 400

    except Exception as error:

        print(
            "SAVE PRODUCT ERROR:",
            error
        )

        return jsonify({
            "success": False,
            "message": (
                "Could not save product."
            )
        }), 500


# ============================================================
# EDIT PRODUCT
# ============================================================

@app.route(
    "/api/products/<int:product_id>",
    methods=["PUT"]
)
def edit_product(product_id):

    data = request.get_json(
        silent=True
    )

    if not data:

        return jsonify({
            "success": False,
            "message": (
                "No product data received."
            )
        }), 400

    name = str(
        data.get(
            "name",
            ""
        )
    ).strip()

    try:

        price = float(
            data.get(
                "price",
                0
            )
        )

        stock = int(
            data.get(
                "stock",
                0
            )
        )

    except (
        ValueError,
        TypeError
    ):

        return jsonify({
            "success": False,
            "message": (
                "Invalid product details."
            )
        }), 400

    if not name:

        return jsonify({
            "success": False,
            "message": (
                "Product name is required."
            )
        }), 400

    if price < 0:

        return jsonify({
            "success": False,
            "message": (
                "Price cannot be negative."
            )
        }), 400

    if stock < 0:

        return jsonify({
            "success": False,
            "message": (
                "Stock cannot be negative."
            )
        }), 400

    try:

        product = update_product(
            product_id,
            name,
            price,
            stock
        )

        return jsonify({
            "success": True,
            "message": (
                "Product updated successfully."
            ),
            "product": product
        })

    except ValueError as error:

        return jsonify({
            "success": False,
            "message": str(error)
        }), 404

    except Exception as error:

        print(
            "EDIT PRODUCT ERROR:",
            error
        )

        return jsonify({
            "success": False,
            "message": (
                "Could not update product."
            )
        }), 500


# ============================================================
# COMPLETE SALE
# ============================================================

@app.route(
    "/api/sales",
    methods=["POST"]
)
def save_sale():

    data = request.get_json(
        silent=True
    )

    if not data:

        return jsonify({
            "success": False,
            "message": (
                "No sale data received."
            )
        }), 400

    cart = data.get(
        "cart",
        []
    )

    if not cart:

        return jsonify({
            "success": False,
            "message": (
                "Cart is empty."
            )
        }), 400

    payment_method = str(
        data.get(
            "payment_method",
            "cash"
        )
    ).lower().strip()

    if payment_method not in [
        "cash",
        "card"
    ]:

        return jsonify({
            "success": False,
            "message": (
                "Invalid payment method."
            )
        }), 400

    try:

        sale_fee = round(
            float(
                data.get(
                    "sale_fee",
                    0
                ) or 0
            ),
            2
        )

    except (
        ValueError,
        TypeError
    ):

        return jsonify({
            "success": False,
            "message": (
                "Invalid sale fee."
            )
        }), 400

    if sale_fee < 0:

        return jsonify({
            "success": False,
            "message": (
                "Sale fee cannot be negative."
            )
        }), 400

    try:

        result = complete_sale(
            cart,
            payment_method,
            sale_fee
        )

        return jsonify({
            "success": True,
            "message": (
                "Sale completed successfully."
            ),
            "subtotal": result.get(
                "subtotal",
                result["total"]
            ),
            "sale_fee": result.get(
                "sale_fee",
                0
            ),
            "total": result["total"],
            "sold_at": result["sold_at"]
        })

    except ValueError as error:

        print(
            "SALE VALIDATION ERROR:",
            error
        )

        return jsonify({
            "success": False,
            "message": str(error)
        }), 400

    except Exception as error:

        print(
            "SALE ERROR:",
            error
        )

        return jsonify({
            "success": False,
            "message": (
                "Could not complete sale."
            )
        }), 500


# ============================================================
# STOCK TAKE - CURRENT STOCK
# ============================================================

@app.route(
    "/api/stock-take",
    methods=["GET"]
)
def stock_take():

    try:

        products = get_stock_take()

        return jsonify({
            "success": True,
            "products": products
        })

    except Exception as error:

        print(
            "STOCK TAKE ERROR:",
            error
        )

        return jsonify({
            "success": False,
            "message": (
                "Could not load stock take."
            )
        }), 500


# ============================================================
# ADD STOCK
# ============================================================

@app.route(
    "/api/stock/add",
    methods=["POST"]
)
def stock_add():

    data = request.get_json(
        silent=True
    )

    if not data:

        return jsonify({
            "success": False,
            "message": (
                "No stock data received."
            )
        }), 400

    try:

        product_id = int(
            data.get(
                "product_id"
            )
        )

        quantity = int(
            data.get(
                "quantity"
            )
        )

    except (
        ValueError,
        TypeError
    ):

        return jsonify({
            "success": False,
            "message": (
                "Invalid product or quantity."
            )
        }), 400

    reason = str(
        data.get(
            "reason",
            "Stock received"
        )
    ).strip()

    if not reason:
        reason = "Stock received"

    try:

        result = add_stock(
            product_id,
            quantity,
            reason
        )

        return jsonify({
            "success": True,
            "message": (
                "Stock added successfully."
            ),
            "stock": result
        })

    except ValueError as error:

        return jsonify({
            "success": False,
            "message": str(error)
        }), 400

    except Exception as error:

        print(
            "ADD STOCK ERROR:",
            error
        )

        return jsonify({
            "success": False,
            "message": (
                "Could not add stock."
            )
        }), 500


# ============================================================
# REMOVE STOCK
# ============================================================

@app.route(
    "/api/stock/remove",
    methods=["POST"]
)
def stock_remove():

    data = request.get_json(
        silent=True
    )

    if not data:

        return jsonify({
            "success": False,
            "message": (
                "No stock data received."
            )
        }), 400

    try:

        product_id = int(
            data.get(
                "product_id"
            )
        )

        quantity = int(
            data.get(
                "quantity"
            )
        )

    except (
        ValueError,
        TypeError
    ):

        return jsonify({
            "success": False,
            "message": (
                "Invalid product or quantity."
            )
        }), 400

    reason = str(
        data.get(
            "reason",
            "Stock removed"
        )
    ).strip()

    if not reason:
        reason = "Stock removed"

    try:

        result = remove_stock(
            product_id,
            quantity,
            reason
        )

        return jsonify({
            "success": True,
            "message": (
                "Stock removed successfully."
            ),
            "stock": result
        })

    except ValueError as error:

        return jsonify({
            "success": False,
            "message": str(error)
        }), 400

    except Exception as error:

        print(
            "REMOVE STOCK ERROR:",
            error
        )

        return jsonify({
            "success": False,
            "message": (
                "Could not remove stock."
            )
        }), 500


# ============================================================
# PHYSICAL STOCK TAKE
# ============================================================

@app.route(
    "/api/stocktake/record",
    methods=["POST"]
)
def record_physical_stocktake():

    data = request.get_json(
        silent=True
    )

    if not data:

        return jsonify({
            "success": False,
            "message": (
                "No stocktake data received."
            )
        }), 400

    try:

        product_id = int(
            data.get(
                "product_id"
            )
        )

        counted_stock = int(
            data.get(
                "counted_stock"
            )
        )

    except (
        ValueError,
        TypeError
    ):

        return jsonify({
            "success": False,
            "message": (
                "Invalid product or counted stock."
            )
        }), 400

    notes = str(
        data.get(
            "notes",
            ""
        )
    ).strip()

    try:

        result = record_stocktake(
            product_id,
            counted_stock,
            notes
        )

        return jsonify({
            "success": True,
            "message": (
                "Stocktake recorded successfully."
            ),
            "stocktake": result
        })

    except ValueError as error:

        return jsonify({
            "success": False,
            "message": str(error)
        }), 400

    except Exception as error:

        print(
            "RECORD STOCKTAKE ERROR:",
            error
        )

        return jsonify({
            "success": False,
            "message": (
                "Could not record stocktake."
            )
        }), 500


# ============================================================
# STOCK MOVEMENT HISTORY
# ============================================================

@app.route(
    "/api/stock-movements",
    methods=["GET"]
)
def stock_movements():

    try:

        product_id = request.args.get(
            "product_id"
        )

        if product_id:
            product_id = int(
                product_id
            )

        movements = get_stock_movements(
            product_id
        )

        return jsonify({
            "success": True,
            "movements": movements
        })

    except ValueError:

        return jsonify({
            "success": False,
            "message": (
                "Invalid product ID."
            )
        }), 400

    except Exception as error:

        print(
            "STOCK MOVEMENTS ERROR:",
            error
        )

        return jsonify({
            "success": False,
            "message": (
                "Could not load stock movements."
            )
        }), 500


# ============================================================
# STOCKTAKE HISTORY
# ============================================================

@app.route(
    "/api/stocktake-history",
    methods=["GET"]
)
def stocktake_history():

    try:

        product_id = request.args.get(
            "product_id"
        )

        if product_id:
            product_id = int(
                product_id
            )

        history = get_stocktake_history(
            product_id
        )

        return jsonify({
            "success": True,
            "history": history
        })

    except ValueError:

        return jsonify({
            "success": False,
            "message": (
                "Invalid product ID."
            )
        }), 400

    except Exception as error:

        print(
            "STOCKTAKE HISTORY ERROR:",
            error
        )

        return jsonify({
            "success": False,
            "message": (
                "Could not load stocktake history."
            )
        }), 500


# ============================================================
# MONTHLY STOCK / CASH REPORTS
# ============================================================

@app.route(
    "/api/monthly-sales-summary",
    methods=["GET"]
)
def monthly_sales_summary():

    try:

        summary = get_monthly_sales_summary()

        return jsonify({
            "success": True,
            "summary": summary
        })

    except Exception as error:

        print(
            "MONTHLY SALES SUMMARY ERROR:",
            error
        )

        return jsonify({
            "success": False,
            "message": (
                "Could not load monthly sales summary."
            )
        }), 500


@app.route(
    "/api/monthly-reports",
    methods=["GET"]
)
def monthly_reports():

    try:

        reports = get_monthly_reports()

        return jsonify({
            "success": True,
            "reports": reports
        })

    except Exception as error:

        print(
            "MONTHLY REPORTS ERROR:",
            error
        )

        return jsonify({
            "success": False,
            "message": (
                "Could not load monthly reports."
            )
        }), 500


@app.route(
    "/api/monthly-reports",
    methods=["POST"]
)
def save_monthly_report():

    data = request.get_json(
        silent=True
    )

    if not data:

        return jsonify({
            "success": False,
            "message": (
                "No monthly report data received."
            )
        }), 400

    try:

        cash_at_hand = float(
            data.get(
                "cash_at_hand",
                0
            )
        )

    except (
        ValueError,
        TypeError
    ):

        return jsonify({
            "success": False,
            "message": (
                "Enter a valid cash amount."
            )
        }), 400

    damaged_goods = data.get(
        "damaged_goods",
        []
    )

    if not isinstance(
        damaged_goods,
        list
    ):

        return jsonify({
            "success": False,
            "message": (
                "Invalid damaged goods data."
            )
        }), 400

    try:

        report = create_monthly_report(
            cash_at_hand,
            damaged_goods
        )

        return jsonify({
            "success": True,
            "message": (
                "Monthly report saved successfully."
            ),
            "report": report
        })

    except ValueError as error:

        return jsonify({
            "success": False,
            "message": str(error)
        }), 400

    except Exception as error:

        print(
            "SAVE MONTHLY REPORT ERROR:",
            error
        )

        return jsonify({
            "success": False,
            "message": (
                "Could not save monthly report."
            )
        }), 500


# ============================================================
# TODAY'S SALES
# ============================================================

@app.route(
    "/api/sales/today",
    methods=["GET"]
)
def todays_sales():

    try:

        sales = get_today_sales()

        return jsonify({
            "success": True,
            "sales": sales
        })

    except Exception as error:

        print(
            "TODAY SALES ERROR:",
            error
        )

        return jsonify({
            "success": False,
            "message": (
                "Could not load today's sales."
            )
        }), 500


# ============================================================
# LIVE STORE SESSION STATUS
# ============================================================

@app.route(
    "/api/session-status",
    methods=["GET"]
)
def session_status():
    """
    Used by the POS to periodically confirm that the current store is
    still ACTIVE.
    """

    store = get_store(
        session.get("store_id")
    )

    return jsonify({
        "success": True,
        "active": True,
        "store_id": store["store_id"],
        "store_name": store["store_name"]
    })


# ============================================================
# STORE / POS LOGOUT
# ============================================================

@app.route(
    "/logout",
    methods=["POST", "GET"]
)
def logout():

    # Remove only the customer store identity.
    session.pop(
        "store_id",
        None
    )

    session.pop(
        "store_name",
        None
    )

    session.pop(
        "store_authenticated_at",
        None
    )

    return redirect(
        url_for(
            "store_access.store_access_page"
        )
    )


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,
        use_reloader=False
)
    EASY_SALES_ENV = os.environ.get(
    "EASY_SALES_ENV",
    "development"
).lower()

DEFAULT_DEVELOPMENT_SECRET = (
    "easy-sales-local-development-change-this-before-production"
)

configured_secret = os.environ.get("EASY_SALES_SECRET_KEY")

if EASY_SALES_ENV == "production" and not configured_secret:
    raise RuntimeError(
        "EASY_SALES_SECRET_KEY must be set in production."
    )

# Trust HTTPS information supplied by one reverse proxy, such as a
# normal managed hosting platform. This is only enabled in production.
if EASY_SALES_ENV == "production":
    app.wsgi_app = ProxyFix(
        app.wsgi_app,
        x_for=1,
        x_proto=1,
        x_host=1
    )

# Flask sessions are signed on the server. Set EASY_SALES_SECRET_KEY
# as an environment variable when the system is hosted.
app.config["SECRET_KEY"] = (
    configured_secret or DEFAULT_DEVELOPMENT_SECRET
)

# Session security. HTTPS cookies are enabled when EASY_SALES_HTTPS=1
# so the same code can still run on the local Pydroid development server.
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = (
    EASY_SALES_ENV == "production"
    or os.environ.get("EASY_SALES_HTTPS", "0") == "1"
)
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=8)

# ============================================================
# INITIALISE EASY SALES SYSTEMS
# ============================================================

# Existing POS database (current Easy Sales development data).
create_database()

# Store controller database (permanent client store spaces).
init_controller()

# Register the Store ID + passkey gateway.
app.register_blueprint(store_access_bp)

# Register the Easy Sales owner/controller dashboard.
app.register_blueprint(controller_bp)


# ============================================================
# STORE ACCESS SUCCESS REDIRECT
# ============================================================

@app.after_request
def redirect_successful_store_access(response):
    """
    The Store Access route returns JSON for programmatic use, but a normal
    browser form submission must continue straight into the POS.
    """
    if (
        request.method == "POST"
        and request.path.rstrip("/") == "/store-access"
        and response.is_json
        and response.status_code < 300
    ):
        data = response.get_json(silent=True) or {}

        if data.get("success") is True:
            return redirect(url_for("home"))

    return response


# ============================================================
# BASIC PRODUCTION SECURITY HEADERS
# ============================================================

@app.after_request
def add_security_headers(response):
    response.headers.setdefault(
        "X-Content-Type-Options",
        "nosniff"
    )
    response.headers.setdefault(
        "X-Frame-Options",
        "SAMEORIGIN"
    )
    response.headers.setdefault(
        "Referrer-Policy",
        "strict-origin-when-cross-origin"
    )
    return response


# ============================================================
# STORE ACCESS GUARD
# ============================================================

@app.before_request
def enforce_store_access():
    """
    Keep the Store Access gateway in front of the POS and every POS API.

    This also checks the controller on each request, so if the owner
    deactivates a store, an already-open browser session loses access on
    its next request.
    """

    # Static files must always remain reachable.
    if request.endpoint == "static":
        return None

    # The Store Access gateway must remain reachable before login.
    if request.path.startswith("/store-access"):
        return None

    # The Easy Sales owner/controller dashboard is separate from
    # customer store access.
    if request.path.startswith("/controller"):
        return None

    # At this stage only the POS home page and POS API are protected.
    if request.path != "/" and not request.path.startswith("/api/"):
        return None

    store_id = session.get("store_id")

    if not store_id:
        if request.path.startswith("/api/"):
            return jsonify({
                "success": False,
                "code": "STORE_ACCESS_REQUIRED",
                "message": "Store access is required."
            }), 401

        return redirect(url_for("store_access.store_access_page"))

    store = get_store(store_id)

    if store is None or store["status"] != "ACTIVE":
        session.pop("store_id", None)
        session.pop("store_name", None)
        session.pop("store_authenticated_at", None)

        if request.path.startswith("/api/"):
            return jsonify({
                "success": False,
                "code": "STORE_INACTIVE",
                "message": (
                    "Your Easy Sales store is currently inactive. "
                    "Please contact Easy Sales to reactivate access."
                )
            }), 403

        return redirect(
            url_for(
                "store_access.store_access_page",
                status="inactive"
            )
        )

    return None


# ============================================================
# HOME / POS SCREEN
# ============================================================

@app.route("/")
def home():

    return render_template(
        "pos.html",
        store_id=session.get("store_id"),
        store_name=session.get("store_name")
    )


# ============================================================
# GET ALL PRODUCTS
# ============================================================

@app.route(
    "/api/products",
    methods=["GET"]
)
def get_products():

    try:

        products = get_all_products()

        return jsonify({

            "success":
                True,

            "products":
                products

        })

    except Exception as error:

        print(
            "GET PRODUCTS ERROR:",
            error
        )

        return jsonify({

            "success":
                False,

            "message":
                "Could not load products."

        }), 500
# ============================================================
# FIND PRODUCT BY BARCODE
# ============================================================

@app.route(
    "/api/products/barcode/<path:barcode>",
    methods=["GET"]
)
def find_product_by_barcode(barcode):

    barcode = str(barcode).strip()

    if not barcode:
        return jsonify({
            "success": False,
            "message": "Barcode is required."
        }), 400

    try:

        print("EASY SALES BARCODE LOOKUP:", repr(barcode))

        product = get_product_by_barcode(barcode)

        if not product:

            print("BARCODE NOT FOUND:", repr(barcode))

            return jsonify({
                "success": False,
                "message": "No product is registered with this barcode."
            }), 404

        print(
            "BARCODE PRODUCT FOUND:",
            product["name"]
        )

        return jsonify({
            "success": True,
            "product": product
        })

    except Exception as error:

        print(
            "BARCODE LOOKUP ERROR:",
            error
        )

        return jsonify({
            "success": False,
            "message": "Could not look up barcode."
        }), 500

# ============================================================
# ADD NEW PRODUCT
# ============================================================

@app.route(
    "/api/products",
    methods=["POST"]
)
def save_product():

    data = request.get_json(
        silent=True
    )

    if not data:

        return jsonify({

            "success":
                False,

            "message":
                "No product data received."

        }), 400

    name = str(
        data.get(
            "name",
            ""
        )
    ).strip()

    barcode = str(
    data.get(
        "barcode",
        ""
        )
    ).strip()
    
    try:

        price = float(
            data.get(
                "price",
                0
            )
        )

    except (
        ValueError,
        TypeError
    ):

        return jsonify({

            "success":
                False,

            "message":
                "Invalid price."

        }), 400
    try:
        stock = int(
            data.get(
                "stock",
                0
            )
        )

    except (
        ValueError,
        TypeError
    ):
        return jsonify({
            "success": False,
            "message": "Invalid stock."
        }), 400


    # Barcode is optional.
    # Products without barcodes can still be created.
    if barcode and not barcode.isdigit():
        return jsonify({
            "success": False,
            "message": "Barcode must contain numbers only."
        }), 400     

    

    if not name:

        return jsonify({

            "success":
                False,

            "message":
                "Product name is required."

        }), 400

    if price < 0:

        return jsonify({

            "success":
                False,

            "message":
                "Price cannot be negative."

        }), 400

    if stock < 0:

        return jsonify({

            "success":
                False,

            "message":
                "Stock cannot be negative."

        }), 400

    try:

        product_id = add_product(
    name,
    price,
    stock,
    barcode
)
        

        return jsonify({
    "success": True,
    "message": "Product saved successfully.",
    "product": {
        "id": product_id,
        "name": name,
        "price": price,
        "stock": stock,
        "barcode": barcode or None
    }
})

    except sqlite3.IntegrityError as error:

        print(
            "SAVE PRODUCT INTEGRITY ERROR:",
            error
        )

        return jsonify({
            "success": False,
            "message": "The product could not be saved because of a database constraint."
        }), 400

    except Exception as error:

        print(
            "SAVE PRODUCT ERROR:",
            error
        )

        return jsonify({

            "success":
                False,

            "message":
                "Could not save product."

        }), 500




# ============================================================
# EDIT PRODUCT
# ============================================================

@app.route(
    "/api/products/<int:product_id>",
    methods=["PUT"]
)
def edit_product(product_id):

    data = request.get_json(silent=True)

    if not data:
        return jsonify({
            "success": False,
            "message": "No product data received."
        }), 400

    name = str(data.get("name", "")).strip()

    try:
        price = float(data.get("price", 0))
        stock = int(data.get("stock", 0))
    except (ValueError, TypeError):
        return jsonify({
            "success": False,
            "message": "Invalid product details."
        }), 400

    if not name:
        return jsonify({
            "success": False,
            "message": "Product name is required."
        }), 400

    if price < 0:
        return jsonify({
            "success": False,
            "message": "Price cannot be negative."
        }), 400

    if stock < 0:
        return jsonify({
            "success": False,
            "message": "Stock cannot be negative."
        }), 400

    try:
        product = update_product(
            product_id,
            name,
            price,
            stock
        )

        return jsonify({
            "success": True,
            "message": "Product updated successfully.",
            "product": product
        })

    except ValueError as error:
        return jsonify({
            "success": False,
            "message": str(error)
        }), 404

    except Exception as error:
        print("EDIT PRODUCT ERROR:", error)

        return jsonify({
            "success": False,
            "message": "Could not update product."
        }), 500


# ============================================================
# COMPLETE SALE
# ============================================================

@app.route(
    "/api/sales",
    methods=["POST"]
)
def save_sale():

    data = request.get_json(
        silent=True
    )

    if not data:

        return jsonify({

            "success":
                False,

            "message":
                "No sale data received."

        }), 400

    cart = data.get(
        "cart",
        []
    )

    if not cart:

        return jsonify({

            "success":
                False,

            "message":
                "Cart is empty."

        }), 400

    payment_method = str(
        data.get(
            "payment_method",
            "cash"
        )
    ).lower().strip()

    if payment_method not in [
        "cash",
        "card"
    ]:

        return jsonify({

            "success":
                False,

            "message":
                "Invalid payment method."

        }), 400

    # Optional fee chosen by the person processing THIS sale.
    # It belongs only to this transaction and is never saved as a product price.
    try:
        sale_fee = round(float(data.get("sale_fee", 0) or 0), 2)
    except (ValueError, TypeError):
        return jsonify({
            "success": False,
            "message": "Invalid sale fee."
        }), 400

    if sale_fee < 0:
        return jsonify({
            "success": False,
            "message": "Sale fee cannot be negative."
        }), 400

    try:

        result = complete_sale(
            cart,
            payment_method,
            sale_fee
        )

        return jsonify({

            "success":
                True,

            "message":
                "Sale completed successfully.",

            "subtotal":
                result.get("subtotal", result["total"]),

            "sale_fee":
                result.get("sale_fee", 0),

            "total":
                result["total"],

            "sold_at":
                result["sold_at"]

        })

    except ValueError as error:

        print(
            "SALE VALIDATION ERROR:",
            error
        )

        return jsonify({

            "success":
                False,

            "message":
                str(error)

        }), 400

    except Exception as error:

        print(
            "SALE ERROR:",
            error
        )

        return jsonify({

            "success":
                False,

            "message":
                "Could not complete sale."

        }), 500


# ============================================================
# STOCK TAKE - CURRENT STOCK
# ============================================================

@app.route(
    "/api/stock-take",
    methods=["GET"]
)
def stock_take():

    try:

        products = get_stock_take()

        return jsonify({

            "success":
                True,

            "products":
                products

        })

    except Exception as error:

        print(
            "STOCK TAKE ERROR:",
            error
        )

        return jsonify({

            "success":
                False,

            "message":
                "Could not load stock take."

        }), 500


# ============================================================
# ADD STOCK
# ============================================================

@app.route(
    "/api/stock/add",
    methods=["POST"]
)
def stock_add():

    data = request.get_json(
        silent=True
    )

    if not data:

        return jsonify({

            "success":
                False,

            "message":
                "No stock data received."

        }), 400

    try:

        product_id = int(
            data.get(
                "product_id"
            )
        )

        quantity = int(
            data.get(
                "quantity"
            )
        )

    except (
        ValueError,
        TypeError
    ):

        return jsonify({

            "success":
                False,

            "message":
                "Invalid product or quantity."

        }), 400

    reason = str(
        data.get(
            "reason",
            "Stock received"
        )
    ).strip()

    if not reason:
        reason = "Stock received"

    try:

        result = add_stock(
            product_id,
            quantity,
            reason
        )

        return jsonify({

            "success":
                True,

            "message":
                "Stock added successfully.",

            "stock":
                result

        })

    except ValueError as error:

        return jsonify({

            "success":
                False,

            "message":
                str(error)

        }), 400

    except Exception as error:

        print(
            "ADD STOCK ERROR:",
            error
        )

        return jsonify({

            "success":
                False,

            "message":
                "Could not add stock."

        }), 500


# ============================================================
# REMOVE STOCK
# ============================================================

@app.route(
    "/api/stock/remove",
    methods=["POST"]
)
def stock_remove():

    data = request.get_json(
        silent=True
    )

    if not data:

        return jsonify({

            "success":
                False,

            "message":
                "No stock data received."

        }), 400

    try:

        product_id = int(
            data.get(
                "product_id"
            )
        )

        quantity = int(
            data.get(
                "quantity"
            )
        )

    except (
        ValueError,
        TypeError
    ):

        return jsonify({

            "success":
                False,

            "message":
                "Invalid product or quantity."

        }), 400

    reason = str(
        data.get(
            "reason",
            "Stock removed"
        )
    ).strip()

    if not reason:
        reason = "Stock removed"

    try:

        result = remove_stock(
            product_id,
            quantity,
            reason
        )

        return jsonify({

            "success":
                True,

            "message":
                "Stock removed successfully.",

            "stock":
                result

        })

    except ValueError as error:

        return jsonify({

            "success":
                False,

            "message":
                str(error)

        }), 400

    except Exception as error:

        print(
            "REMOVE STOCK ERROR:",
            error
        )

        return jsonify({

            "success":
                False,

            "message":
                "Could not remove stock."

        }), 500


# ============================================================
# PHYSICAL STOCK TAKE
# ============================================================

@app.route(
    "/api/stocktake/record",
    methods=["POST"]
)
def record_physical_stocktake():

    data = request.get_json(
        silent=True
    )

    if not data:

        return jsonify({

            "success":
                False,

            "message":
                "No stocktake data received."

        }), 400

    try:

        product_id = int(
            data.get(
                "product_id"
            )
        )

        counted_stock = int(
            data.get(
                "counted_stock"
            )
        )

    except (
        ValueError,
        TypeError
    ):

        return jsonify({

            "success":
                False,

            "message":
                "Invalid product or counted stock."

        }), 400

    notes = str(
        data.get(
            "notes",
            ""
        )
    ).strip()

    try:

        result = record_stocktake(
            product_id,
            counted_stock,
            notes
        )

        return jsonify({

            "success":
                True,

            "message":
                "Stocktake recorded successfully.",

            "stocktake":
                result

        })

    except ValueError as error:

        return jsonify({

            "success":
                False,

            "message":
                str(error)

        }), 400

    except Exception as error:

        print(
            "RECORD STOCKTAKE ERROR:",
            error
        )

        return jsonify({

            "success":
                False,

            "message":
                "Could not record stocktake."

        }), 500


# ============================================================
# STOCK MOVEMENT HISTORY
# ============================================================

@app.route(
    "/api/stock-movements",
    methods=["GET"]
)
def stock_movements():

    try:

        product_id = request.args.get(
            "product_id"
        )

        if product_id:
            product_id = int(
                product_id
            )

        movements = get_stock_movements(
            product_id
        )

        return jsonify({

            "success":
                True,

            "movements":
                movements

        })

    except ValueError:

        return jsonify({

            "success":
                False,

            "message":
                "Invalid product ID."

        }), 400

    except Exception as error:

        print(
            "STOCK MOVEMENTS ERROR:",
            error
        )

        return jsonify({

            "success":
                False,

            "message":
                "Could not load stock movements."

        }), 500


# ============================================================
# STOCKTAKE HISTORY
# ============================================================

@app.route(
    "/api/stocktake-history",
    methods=["GET"]
)
def stocktake_history():

    try:

        product_id = request.args.get(
            "product_id"
        )

        if product_id:
            product_id = int(
                product_id
            )

        history = get_stocktake_history(
            product_id
        )

        return jsonify({

            "success":
                True,

            "history":
                history

        })

    except ValueError:

        return jsonify({

            "success":
                False,

            "message":
                "Invalid product ID."

        }), 400

    except Exception as error:

        print(
            "STOCKTAKE HISTORY ERROR:",
            error
        )

        return jsonify({

            "success":
                False,

            "message":
                "Could not load stocktake history."

        }), 500


# ============================================================
# MONTHLY STOCK / CASH REPORTS
# ============================================================

@app.route(
    "/api/monthly-sales-summary",
    methods=["GET"]
)
def monthly_sales_summary():

    try:

        summary = get_monthly_sales_summary()

        return jsonify({

            "success": True,

            "summary": summary

        })

    except Exception as error:

        print(
            "MONTHLY SALES SUMMARY ERROR:",
            error
        )

        return jsonify({

            "success": False,

            "message": "Could not load monthly sales summary."

        }), 500


@app.route(
    "/api/monthly-reports",
    methods=["GET"]
)
def monthly_reports():

    try:

        reports = get_monthly_reports()

        return jsonify({

            "success": True,

            "reports": reports

        })

    except Exception as error:

        print(
            "MONTHLY REPORTS ERROR:",
            error
        )

        return jsonify({

            "success": False,

            "message": "Could not load monthly reports."

        }), 500


@app.route(
    "/api/monthly-reports",
    methods=["POST"]
)
def save_monthly_report():

    data = request.get_json(
        silent=True
    )

    if not data:

        return jsonify({

            "success": False,

            "message": "No monthly report data received."

        }), 400

    try:

        cash_at_hand = float(
            data.get(
                "cash_at_hand",
                0
            )
        )

    except (ValueError, TypeError):

        return jsonify({

            "success": False,

            "message": "Enter a valid cash amount."

        }), 400

    damaged_goods = data.get(
        "damaged_goods",
        []
    )

    if not isinstance(damaged_goods, list):

        return jsonify({

            "success": False,

            "message": "Invalid damaged goods data."

        }), 400

    try:

        report = create_monthly_report(
            cash_at_hand,
            damaged_goods
        )

        return jsonify({

            "success": True,

            "message": "Monthly report saved successfully.",

            "report": report

        })

    except ValueError as error:

        return jsonify({

            "success": False,

            "message": str(error)

        }), 400

    except Exception as error:

        print(
            "SAVE MONTHLY REPORT ERROR:",
            error
        )

        return jsonify({

            "success": False,

            "message": "Could not save monthly report."

        }), 500


# ============================================================
# TODAY'S SALES
# ============================================================

@app.route(
    "/api/sales/today",
    methods=["GET"]
)
def todays_sales():

    try:

        sales = get_today_sales()

        return jsonify({

            "success":
                True,

            "sales":
                sales

        })

    except Exception as error:

        print(
            "TODAY SALES ERROR:",
            error
        )

        return jsonify({

            "success":
                False,

            "message":
                "Could not load today's sales."

        }), 500


# ============================================================
# LIVE STORE SESSION STATUS
# ============================================================

@app.route("/api/session-status", methods=["GET"])
def session_status():
    """
    Used by the POS to periodically confirm that the current store is
    still ACTIVE. The before_request security guard runs before this
    route, so an inactive store is blocked immediately.
    """
    store = get_store(session.get("store_id"))

    return jsonify({
        "success": True,
        "active": True,
        "store_id": store["store_id"],
        "store_name": store["store_name"]
    })


# ============================================================
# STORE / POS LOGOUT
# ============================================================

@app.route("/logout", methods=["POST", "GET"])
def logout():
    # Only remove the customer store identity. Controller authentication,
    # when used in another session context, is not granted to the POS.
    session.pop("store_id", None)
    session.pop("store_name", None)
    session.pop("store_authenticated_at", None)

    return redirect(url_for("store_access.store_access_page"))


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,
        use_reloader=False
    )
