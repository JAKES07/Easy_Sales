# ====# ============================================================
# EASY SALES - MAIN APPLICATION
# ============================================================

import os
from io import BytesIO
from datetime import timedelta, datetime

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

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether
)

from database import (
    create_database,
    add_product,
    update_product,
    get_all_products,
    remove_product_tile,
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
    get_stock_report_data,
    get_connection,
    get_currency_settings,
    set_currency_settings,
    SUPPORTED_CURRENCIES
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

# Never allow a production deployment to silently fall back to the
# application folder for SQLite data. On Render this would be replaced
# during deployments and could make stores appear to reset.
configured_data_dir = os.environ.get(
    "EASY_SALES_DATA_DIR",
    ""
).strip()

if EASY_SALES_ENV == "production" and not configured_data_dir:
    raise RuntimeError(
        "EASY_SALES_DATA_DIR must point to persistent storage in production."
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
        store_name=session.get("store_name"),
        currency=get_currency_settings()
    )


# ============================================================
# GET ALL PRODUCTS
# ============================================================



# ============================================================
# GET / ADD PRODUCTS
# ============================================================

@app.route("/api/products", methods=["GET", "POST"])
def products():

    if request.method == "GET":
        try:
            return jsonify({
                "success": True,
                "products": get_all_products(),
                "currency": get_currency_settings()
            })
        except Exception as error:
            print("GET PRODUCTS ERROR:", error)
            return jsonify({
                "success": False,
                "message": "Could not load products."
            }), 500

    data = request.get_json(silent=True) or {}

    name = str(data.get("name", "")).strip()
    barcode = str(data.get("barcode", "")).strip() or None

    try:
        price = float(data.get("price"))
        stock = int(data.get("stock"))
    except (TypeError, ValueError):
        return jsonify({
            "success": False,
            "message": "Enter a valid price and stock quantity."
        }), 400

    if not name:
        return jsonify({
            "success": False,
            "message": "Product name is required."
        }), 400

    if price < 0 or stock < 0:
        return jsonify({
            "success": False,
            "message": "Price and stock cannot be negative."
        }), 400

    try:
        product_id = add_product(name, price, stock, barcode)
        return jsonify({
            "success": True,
            "message": "Product saved successfully.",
            "product_id": product_id
        }), 201
    except sqlite3.IntegrityError as error:
        print("ADD PRODUCT INTEGRITY ERROR:", error)
        return jsonify({
            "success": False,
            "message": "A product with that barcode already exists."
        }), 400
    except Exception as error:
        print("ADD PRODUCT ERROR:", error)
        return jsonify({
            "success": False,
            "message": "Could not save product."
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
# STORE CURRENCY SETTINGS
# ============================================================

@app.route("/api/settings/currency", methods=["GET", "POST"])
def currency_settings():
    if request.method == "GET":
        current = get_currency_settings()
        return jsonify({
            "success": True,
            "configured": current is not None,
            "currency": current,
            "currencies": [
                {
                    "code": code,
                    "symbol": values[0],
                    "name": values[1]
                }
                for code, values in sorted(SUPPORTED_CURRENCIES.items())
            ]
        })

    data = request.get_json(silent=True) or {}
    currency_code = str(data.get("currency_code", "")).strip().upper()

    try:
        currency = set_currency_settings(currency_code)
        return jsonify({
            "success": True,
            "message": "Store currency saved successfully.",
            "currency": currency
        })
    except ValueError as error:
        return jsonify({
            "success": False,
            "message": str(error)
        }), 400
    except Exception as error:
        print("CURRENCY SETTINGS ERROR:", error)
        return jsonify({
            "success": False,
            "message": "Could not save store currency."
        }), 500


# ============================================================
# REMOVE PRODUCT TILE WITHOUT DELETING HISTORY
# ============================================================

@app.route(
    "/api/products/<int:product_id>/remove",
    methods=["POST"]
)
def remove_product(product_id):

    try:
        result = remove_product_tile(product_id)

        return jsonify({
            "success": True,
            "message": "Product tile removed. Product history was retained.",
            "product": result
        })

    except ValueError as error:
        return jsonify({
            "success": False,
            "message": str(error)
        }), 400

    except Exception as error:
        print("REMOVE PRODUCT ERROR:", error)
        return jsonify({
            "success": False,
            "message": "Could not remove product tile."
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
# STOCK CONTROL PDF REPORT
# ============================================================

@app.route(
    "/api/stock-report/pdf",
    methods=["GET"]
)
def stock_report_pdf():

    try:
        report = get_stock_report_data()
        currency = get_currency_settings() or {
            "currency_code": "ZAR",
            "currency_symbol": "R",
            "currency_name": "South African Rand"
        }

        buffer = BytesIO()

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "ReportTitle",
            parent=styles["Title"],
            alignment=TA_CENTER,
            fontSize=18,
            leading=22,
            spaceAfter=6
        )
        section_style = ParagraphStyle(
            "Section",
            parent=styles["Heading2"],
            fontSize=13,
            leading=16,
            spaceBefore=10,
            spaceAfter=7
        )
        small_style = ParagraphStyle(
            "Small",
            parent=styles["BodyText"],
            fontSize=7.5,
            leading=9
        )

        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=10 * mm,
            leftMargin=10 * mm,
            topMargin=25 * mm,
            bottomMargin=15 * mm,
            title="Easy Sales Stock Control Report"
        )

        logo_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "static",
            "images",
            "logo.png"
        )

        generated_date = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        def draw_page_header(canvas, document):
            canvas.saveState()
            page_width, page_height = A4

            if os.path.isfile(logo_path):
                try:
                    canvas.drawImage(
                        logo_path,
                        10 * mm,
                        page_height - 20 * mm,
                        width=28 * mm,
                        height=12 * mm,
                        preserveAspectRatio=True,
                        mask="auto"
                    )
                except Exception:
                    pass

            canvas.setFont("Helvetica", 8)
            canvas.drawRightString(
                page_width - 10 * mm,
                page_height - 14 * mm,
                f"Date: {generated_date}"
            )

            canvas.setStrokeColor(colors.grey)
            canvas.line(
                10 * mm,
                page_height - 22 * mm,
                page_width - 10 * mm,
                page_height - 22 * mm
            )

            canvas.setFont("Helvetica", 7)
            canvas.drawCentredString(
                page_width / 2,
                7 * mm,
                f"Easy Sales • Stock Control Report • Page {document.page}"
            )
            canvas.restoreState()

        story = [
            Paragraph(
                f"EASY SALES STOCK CONTROL REPORT — {currency['currency_code']}",
                title_style
            ),
            Paragraph(
                "Complete inventory audit: current stock, stock movement, stock added, "
                "and stock reconciliation.",
                styles["BodyText"]
            ),
            Spacer(1, 5 * mm)
        ]

        # --------------------------------------------------------
        # 1. CURRENT STOCK
        # --------------------------------------------------------
        story.append(Paragraph("1. Current Stock", section_style))

        product_rows = [["Product", "Price", "Stock", "Status", "Barcode"]]
        total_units = 0
        total_value = 0.0

        for p in report["products"]:
            stock = int(p.get("stock", 0) or 0)
            price = float(p.get("price", 0) or 0)
            total_units += stock
            total_value += stock * price
            status = "ACTIVE" if int(p.get("active", 1) or 0) else "REMOVED"
            product_rows.append([
                p.get("name", ""),
                f"{currency['currency_code']} {price:,.2f}",
                str(stock),
                status,
                p.get("barcode") or "-"
            ])

        product_rows.append([
            "TOTAL",
            "",
            str(total_units),
            "",
            f"Value: {currency['currency_code']} {total_value:,.2f}"
        ])

        t = Table(product_rows, colWidths=[60*mm, 25*mm, 18*mm, 23*mm, 48*mm], repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#333333")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,-1), 7.5),
            ("GRID", (0,0), (-1,-1), 0.35, colors.grey),
            ("ALIGN", (1,1), (3,-1), "RIGHT"),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("BACKGROUND", (0,-1), (-1,-1), colors.lightgrey),
            ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"),
            ("TOPPADDING", (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ]))
        story.append(t)

        # --------------------------------------------------------
        # 2. STOCK MOVEMENT
        # --------------------------------------------------------
        story.append(Paragraph("2. Stock Movement History", section_style))
        movement_rows = [[
            "Date", "Product", "Type", "Before", "Added",
            "Sold", "Adj.", "After", "Reason"
        ]]

        for m in report["movements"]:
            movement_rows.append([
                str(m.get("created_at", "")),
                str(m.get("product_name", "")),
                str(m.get("movement_type", "")),
                str(m.get("stock_before", 0)),
                str(m.get("quantity_added", 0)),
                str(m.get("quantity_sold", 0)),
                str(m.get("adjustment", 0)),
                str(m.get("stock_after", 0)),
                str(m.get("reason") or "")
            ])

        if len(movement_rows) == 1:
            movement_rows.append(["-", "No movements recorded", "-", "-", "-", "-", "-", "-", "-"])

        t = Table(
            movement_rows,
            colWidths=[27*mm, 35*mm, 28*mm, 15*mm, 15*mm, 15*mm, 13*mm, 15*mm, 32*mm],
            repeatRows=1
        )
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#333333")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,-1), 6.5),
            ("GRID", (0,0), (-1,-1), 0.3, colors.grey),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("TOPPADDING", (0,0), (-1,-1), 3),
            ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ]))
        story.append(t)

        # --------------------------------------------------------
        # 3. STOCK ADDED
        # --------------------------------------------------------
        story.append(Paragraph("3. Stock Added / Received", section_style))
        added = [
            m for m in report["movements"]
            if str(m.get("movement_type", "")).upper() == "STOCK_IN"
        ]

        added_rows = [["Date", "Product", "Before", "Quantity Added", "After", "Reason"]]
        for m in added:
            added_rows.append([
                str(m.get("created_at", "")),
                str(m.get("product_name", "")),
                str(m.get("stock_before", 0)),
                str(m.get("quantity_added", 0)),
                str(m.get("stock_after", 0)),
                str(m.get("reason") or "")
            ])
        if len(added_rows) == 1:
            added_rows.append(["-", "No stock received records", "-", "-", "-", "-"])

        t = Table(
            added_rows,
            colWidths=[30*mm, 48*mm, 22*mm, 30*mm, 22*mm, 35*mm],
            repeatRows=1
        )
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#333333")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,-1), 7),
            ("GRID", (0,0), (-1,-1), 0.3, colors.grey),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("TOPPADDING", (0,0), (-1,-1), 3),
            ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ]))
        story.append(t)

        # --------------------------------------------------------
        # 4. STOCK RECONCILIATION
        # --------------------------------------------------------
        story.append(Paragraph("4. Stock Reconciliation Report", section_style))
        reconciliation_rows = [[
            "Date", "Product", "System Stock", "Counted Stock",
            "Variance", "Final Stock", "Notes"
        ]]

        for r in report["stocktakes"]:
            reconciliation_rows.append([
                str(r.get("taken_at", "")),
                str(r.get("product_name", "")),
                str(r.get("system_stock", 0)),
                str(r.get("counted_stock", 0)),
                str(r.get("variance", 0)),
                str(r.get("counted_stock", 0)),
                str(r.get("notes") or "")
            ])

        if len(reconciliation_rows) == 1:
            reconciliation_rows.append([
                "-", "No physical stock reconciliations recorded",
                "-", "-", "-", "-", "-"
            ])

        t = Table(
            reconciliation_rows,
            colWidths=[27*mm, 40*mm, 27*mm, 27*mm, 20*mm, 22*mm, 30*mm],
            repeatRows=1
        )
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#333333")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,-1), 6.8),
            ("GRID", (0,0), (-1,-1), 0.3, colors.grey),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("TOPPADDING", (0,0), (-1,-1), 3),
            ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ]))
        story.append(t)

        # --------------------------------------------------------
        # 5. MONTHLY RECONCILIATION SUMMARY
        # --------------------------------------------------------
        story.append(Paragraph("5. Saved Reconciliation Summaries", section_style))
        monthly_rows = [[
            "Month", "Cash Expected", "Cash Actual", "Cash Variance",
            "Stock Units", "Stock Value", "Damaged", "Total Loss"
        ]]

        for r in report["monthly_reports"]:
            monthly_rows.append([
                str(r.get("report_month", "")),
                f"{currency['currency_code']} {float(r.get('expected_cash',0) or 0):,.2f}",
                f"{currency['currency_code']} {float(r.get('cash_at_hand',0) or 0):,.2f}",
                f"{currency['currency_code']} {float(r.get('cash_variance',0) or 0):,.2f}",
                str(r.get("stock_units", 0)),
                f"{currency['currency_code']} {float(r.get('stock_value',0) or 0):,.2f}",
                str(r.get("damaged_units", 0)),
                f"{currency['currency_code']} {float(r.get('total_loss',0) or 0):,.2f}"
            ])

        if len(monthly_rows) == 1:
            monthly_rows.append(["-", "-", "-", "-", "-", "-", "-", "-"])

        t = Table(
            monthly_rows,
            colWidths=[22*mm, 27*mm, 27*mm, 25*mm, 20*mm, 28*mm, 18*mm, 25*mm],
            repeatRows=1
        )
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#333333")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,-1), 6.8),
            ("GRID", (0,0), (-1,-1), 0.3, colors.grey),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("TOPPADDING", (0,0), (-1,-1), 3),
            ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ]))
        story.append(t)

        story.append(Spacer(1, 5 * mm))
        story.append(Paragraph(
            "Report note: Removed product tiles are retained in the database and "
            "their removal is recorded as PRODUCT_REMOVED in the stock movement history.",
            small_style
        ))

        doc.build(
            story,
            onFirstPage=draw_page_header,
            onLaterPages=draw_page_header
        )

        buffer.seek(0)

        filename = (
            "Easy_Sales_Stock_Control_Report_"
            + datetime.now().strftime("%Y-%m-%d")
            + ".pdf"
        )

        return send_file(
            buffer,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=filename
        )

    except Exception as error:
        print("STOCK PDF REPORT ERROR:", error)
        return jsonify({
            "success": False,
            "message": "Could not generate stock control PDF."
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
        "store_name": store["store_name"],
        "currency": get_currency_settings()
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
