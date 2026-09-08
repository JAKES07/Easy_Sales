# ============================================================
# EASY SALES - DATABASE
# ============================================================

import os
import sqlite3
import datetime
import uuid
import json

from flask import has_request_context, session
from store_database import create_store_database, get_store_connection


def _current_store_id():
    """Return the logged-in store. POS data is never allowed to use a shared DB."""
    if not has_request_context():
        return None
    return session.get("store_id")


def get_connection():
    store_id = _current_store_id()
    if not store_id:
        raise RuntimeError("Store database access requires an active store session.")

    # Safe to call repeatedly; existing private store data is preserved.
    create_store_database(store_id)
    return get_store_connection(store_id)


def now_string():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ============================================================
# STORE CURRENCY SETTINGS
# ============================================================

SUPPORTED_CURRENCIES = {
    "AED": ("د.إ", "UAE Dirham"),
    "AFN": ("؋", "Afghan Afghani"),
    "ALL": ("L", "Albanian Lek"),
    "AMD": ("֏", "Armenian Dram"),
    "ANG": ("ƒ", "Netherlands Antillean Guilder"),
    "AOA": ("Kz", "Angolan Kwanza"),
    "ARS": ("$", "Argentine Peso"),
    "AUD": ("$", "Australian Dollar"),
    "AWG": ("ƒ", "Aruban Florin"),
    "AZN": ("₼", "Azerbaijani Manat"),
    "BAM": ("KM", "Bosnia and Herzegovina Convertible Mark"),
    "BBD": ("$", "Barbadian Dollar"),
    "BDT": ("৳", "Bangladeshi Taka"),
    "BGN": ("лв", "Bulgarian Lev"),
    "BHD": (".د.ب", "Bahraini Dinar"),
    "BIF": ("FBu", "Burundian Franc"),
    "BMD": ("$", "Bermudian Dollar"),
    "BND": ("$", "Brunei Dollar"),
    "BOB": ("Bs", "Bolivian Boliviano"),
    "BRL": ("R$", "Brazilian Real"),
    "BSD": ("$", "Bahamian Dollar"),
    "BTN": ("Nu.", "Bhutanese Ngultrum"),
    "BWP": ("P", "Botswana Pula"),
    "BYN": ("Br", "Belarusian Ruble"),
    "BZD": ("BZ$", "Belize Dollar"),
    "CAD": ("$", "Canadian Dollar"),
    "CDF": ("FC", "Congolese Franc"),
    "CHF": ("CHF", "Swiss Franc"),
    "CLP": ("$", "Chilean Peso"),
    "CNY": ("¥", "Chinese Yuan"),
    "COP": ("$", "Colombian Peso"),
    "CRC": ("₡", "Costa Rican Colón"),
    "CUP": ("₱", "Cuban Peso"),
    "CVE": ("$", "Cape Verdean Escudo"),
    "CZK": ("Kč", "Czech Koruna"),
    "DJF": ("Fdj", "Djiboutian Franc"),
    "DKK": ("kr", "Danish Krone"),
    "DOP": ("RD$", "Dominican Peso"),
    "DZD": ("دج", "Algerian Dinar"),
    "EGP": ("E£", "Egyptian Pound"),
    "ERN": ("Nfk", "Eritrean Nakfa"),
    "ETB": ("Br", "Ethiopian Birr"),
    "EUR": ("€", "Euro"),
    "FJD": ("$", "Fijian Dollar"),
    "FKP": ("£", "Falkland Islands Pound"),
    "GBP": ("£", "British Pound"),
    "GEL": ("₾", "Georgian Lari"),
    "GHS": ("₵", "Ghanaian Cedi"),
    "GIP": ("£", "Gibraltar Pound"),
    "GMD": ("D", "Gambian Dalasi"),
    "GNF": ("FG", "Guinean Franc"),
    "GTQ": ("Q", "Guatemalan Quetzal"),
    "GYD": ("$", "Guyanese Dollar"),
    "HKD": ("$", "Hong Kong Dollar"),
    "HNL": ("L", "Honduran Lempira"),
    "HTG": ("G", "Haitian Gourde"),
    "HUF": ("Ft", "Hungarian Forint"),
    "IDR": ("Rp", "Indonesian Rupiah"),
    "ILS": ("₪", "Israeli New Shekel"),
    "INR": ("₹", "Indian Rupee"),
    "IQD": ("ع.د", "Iraqi Dinar"),
    "IRR": ("﷼", "Iranian Rial"),
    "ISK": ("kr", "Icelandic Króna"),
    "JMD": ("J$", "Jamaican Dollar"),
    "JOD": ("د.ا", "Jordanian Dinar"),
    "JPY": ("¥", "Japanese Yen"),
    "KES": ("KSh", "Kenyan Shilling"),
    "KGS": ("с", "Kyrgyzstani Som"),
    "KHR": ("៛", "Cambodian Riel"),
    "KMF": ("CF", "Comorian Franc"),
    "KPW": ("₩", "North Korean Won"),
    "KRW": ("₩", "South Korean Won"),
    "KWD": ("د.ك", "Kuwaiti Dinar"),
    "KYD": ("$", "Cayman Islands Dollar"),
    "KZT": ("₸", "Kazakhstani Tenge"),
    "LAK": ("₭", "Lao Kip"),
    "LBP": ("ل.ل", "Lebanese Pound"),
    "LKR": ("Rs", "Sri Lankan Rupee"),
    "LRD": ("$", "Liberian Dollar"),
    "LSL": ("L", "Lesotho Loti"),
    "LYD": ("ل.د", "Libyan Dinar"),
    "MAD": ("د.م.", "Moroccan Dirham"),
    "MDL": ("L", "Moldovan Leu"),
    "MGA": ("Ar", "Malagasy Ariary"),
    "MKD": ("ден", "Macedonian Denar"),
    "MMK": ("K", "Myanmar Kyat"),
    "MNT": ("₮", "Mongolian Tögrög"),
    "MOP": ("MOP$", "Macanese Pataca"),
    "MRU": ("UM", "Mauritanian Ouguiya"),
    "MUR": ("₨", "Mauritian Rupee"),
    "MVR": ("Rf", "Maldivian Rufiyaa"),
    "MWK": ("MK", "Malawian Kwacha"),
    "MXN": ("$", "Mexican Peso"),
    "MYR": ("RM", "Malaysian Ringgit"),
    "MZN": ("MT", "Mozambican Metical"),
    "NAD": ("$", "Namibian Dollar"),
    "NGN": ("₦", "Nigerian Naira"),
    "NIO": ("C$", "Nicaraguan Córdoba"),
    "NOK": ("kr", "Norwegian Krone"),
    "NPR": ("₨", "Nepalese Rupee"),
    "NZD": ("$", "New Zealand Dollar"),
    "OMR": ("ر.ع.", "Omani Rial"),
    "PAB": ("B/.", "Panamanian Balboa"),
    "PEN": ("S/", "Peruvian Sol"),
    "PGK": ("K", "Papua New Guinean Kina"),
    "PHP": ("₱", "Philippine Peso"),
    "PKR": ("₨", "Pakistani Rupee"),
    "PLN": ("zł", "Polish Złoty"),
    "PYG": ("₲", "Paraguayan Guaraní"),
    "QAR": ("ر.ق", "Qatari Riyal"),
    "RON": ("lei", "Romanian Leu"),
    "RSD": ("дин", "Serbian Dinar"),
    "RUB": ("₽", "Russian Ruble"),
    "RWF": ("FRw", "Rwandan Franc"),
    "SAR": ("﷼", "Saudi Riyal"),
    "SBD": ("$", "Solomon Islands Dollar"),
    "SCR": ("₨", "Seychellois Rupee"),
    "SDG": ("ج.س.", "Sudanese Pound"),
    "SEK": ("kr", "Swedish Krona"),
    "SGD": ("$", "Singapore Dollar"),
    "SHP": ("£", "Saint Helena Pound"),
    "SLE": ("Le", "Sierra Leonean Leone"),
    "SOS": ("Sh", "Somali Shilling"),
    "SRD": ("$", "Surinamese Dollar"),
    "SSP": ("£", "South Sudanese Pound"),
    "STN": ("Db", "São Tomé and Príncipe Dobra"),
    "SVC": ("₡", "Salvadoran Colón"),
    "SYP": ("£", "Syrian Pound"),
    "SZL": ("E", "Eswatini Lilangeni"),
    "THB": ("฿", "Thai Baht"),
    "TJS": ("SM", "Tajikistani Somoni"),
    "TMT": ("m", "Turkmenistani Manat"),
    "TND": ("د.ت", "Tunisian Dinar"),
    "TOP": ("T$", "Tongan Paʻanga"),
    "TRY": ("₺", "Turkish Lira"),
    "TTD": ("TT$", "Trinidad and Tobago Dollar"),
    "TWD": ("NT$", "New Taiwan Dollar"),
    "TZS": ("TSh", "Tanzanian Shilling"),
    "UAH": ("₴", "Ukrainian Hryvnia"),
    "UGX": ("USh", "Ugandan Shilling"),
    "USD": ("$", "US Dollar"),
    "UYU": ("$U", "Uruguayan Peso"),
    "UZS": ("soʻm", "Uzbekistani Som"),
    "VES": ("Bs.", "Venezuelan Bolívar"),
    "VND": ("₫", "Vietnamese Đồng"),
    "VUV": ("VT", "Vanuatu Vatu"),
    "WST": ("T", "Samoan Tālā"),
    "XAF": ("FCFA", "Central African CFA Franc"),
    "XCD": ("$", "East Caribbean Dollar"),
    "XOF": ("CFA", "West African CFA Franc"),
    "XPF": ("₣", "CFP Franc"),
    "YER": ("﷼", "Yemeni Rial"),
    "ZAR": ("R", "South African Rand"),
    "ZMW": ("ZK", "Zambian Kwacha"),
    "ZWL": ("Z$", "Zimbabwean Dollar"),
}


def get_currency_settings():
    connection = get_connection()
    try:
        row = connection.execute("""
            SELECT currency_code, currency_symbol, currency_name, updated_at
            FROM store_settings
            WHERE id = 1
        """).fetchone()
        if not row or not row["currency_code"]:
            return None
        return dict(row)
    finally:
        connection.close()


def set_currency_settings(currency_code):
    currency_code = str(currency_code or "").strip().upper()
    if currency_code not in SUPPORTED_CURRENCIES:
        raise ValueError("Unsupported currency.")

    symbol, name = SUPPORTED_CURRENCIES[currency_code]
    connection = get_connection()
    try:
        existing = connection.execute("""
            SELECT currency_code
            FROM store_settings
            WHERE id = 1
        """).fetchone()
        if existing and existing["currency_code"]:
            raise ValueError("Store currency is already configured.")

        connection.execute("""
            INSERT INTO store_settings
            (id, currency_code, currency_symbol, currency_name, updated_at)
            VALUES (1, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                currency_code = excluded.currency_code,
                currency_symbol = excluded.currency_symbol,
                currency_name = excluded.currency_name,
                updated_at = excluded.updated_at
        """, (currency_code, symbol, name, now_string()))
        connection.commit()
        return {
            "currency_code": currency_code,
            "currency_symbol": symbol,
            "currency_name": name
        }
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def create_database():
    """Compatibility startup hook. Client databases are created per store."""
    return None


# ============================================================
# EMPLOYEE MODE SECURITY
# ============================================================


def get_employee_mode_password_hash():
    connection = get_connection()
    try:
        row = connection.execute("""
            SELECT employee_mode_password_hash
            FROM store_settings
            WHERE id = 1
        """).fetchone()
        return row["employee_mode_password_hash"] if row else None
    finally:
        connection.close()


def set_employee_mode_password_hash(password_hash):
    connection = get_connection()
    try:
        connection.execute("""
            INSERT INTO store_settings
                (id, employee_mode_password_hash, updated_at)
            VALUES (1, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                employee_mode_password_hash = excluded.employee_mode_password_hash,
                updated_at = excluded.updated_at
        """, (password_hash, now_string()))
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

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



def add_product(name, price, stock, barcode=None, warranty_days=0):
    """Add a product with an optional barcode."""
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            INSERT INTO products (name, price, stock, barcode, warranty_days)
            VALUES (?, ?, ?, ?, ?)
        """, (
            name,
            price,
            stock,
            barcode.strip() if barcode else None,
            max(0, int(warranty_days or 0))
        ))

        product_id = cursor.lastrowid

        opening_stock = int(stock)
        if opening_stock > 0:
            created_at = now_string()
            cursor.execute("""
                INSERT INTO stock_movements
                (product_id, product_name, movement_type,
                 stock_before, quantity_added, quantity_sold,
                 adjustment, stock_after, reason, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                product_id,
                name,
                "STOCK_IN",
                0,
                opening_stock,
                0,
                opening_stock,
                opening_stock,
                "Opening stock",
                created_at
            ))

        connection.commit()
        return product_id

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def get_all_products():
    connection = get_connection()

    rows = connection.execute("""
        SELECT id, name, price, stock, barcode, warranty_days
        FROM products
        WHERE active = 1
        ORDER BY name
    """).fetchall()

    connection.close()

    return [dict(row) for row in rows]


# ============================================================
# UNDO PRODUCT TILE REMOVAL
# ============================================================

def undo_product_tile_removal(movement_id):
    """
    Restore a product that was hidden by a PRODUCT_REMOVED movement.
    The original product row (including its barcode, stock and history) is
    preserved. A PRODUCT_RESTORED movement is added for a complete audit trail.
    """
    connection = get_connection()
    cursor = connection.cursor()

    try:
        movement = cursor.execute("""
            SELECT id, product_id, product_name, movement_type, stock_after
            FROM stock_movements
            WHERE id = ?
        """, (movement_id,)).fetchone()

        if not movement:
            raise ValueError("Removal movement not found.")

        if str(movement["movement_type"]).upper() != "PRODUCT_REMOVED":
            raise ValueError("Only a product removal can be undone.")

        product = cursor.execute("""
            SELECT id, name, price, stock, barcode, active
            FROM products
            WHERE id = ?
        """, (movement["product_id"],)).fetchone()

        if not product:
            raise ValueError("Product not found.")

        if int(product["active"]) == 1:
            raise ValueError("Product tile is already active.")

        before = int(product["stock"])
        created_at = now_string()

        cursor.execute("""
            UPDATE products
            SET active = 1
            WHERE id = ?
        """, (product["id"],))

        cursor.execute("""
            INSERT INTO stock_movements
            (product_id, product_name, movement_type,
             stock_before, quantity_added, quantity_sold,
             adjustment, stock_after, reason, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            product["id"],
            product["name"],
            "PRODUCT_RESTORED",
            before,
            0,
            0,
            0,
            before,
            "Product tile restored using Undo (original barcode and history retained)",
            created_at
        ))

        connection.commit()

        return {
            "id": int(product["id"]),
            "name": product["name"],
            "stock": before,
            "barcode": product["barcode"],
            "restored_at": created_at
        }

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


# ============================================================
# REMOVE PRODUCT TILE (KEEP PRODUCT HISTORY)
# ============================================================

def remove_product_tile(product_id):
    """
    Hide a product tile without deleting the product or any history.
    A PRODUCT_REMOVED movement is written so the action is auditable.
    """
    connection = get_connection()
    cursor = connection.cursor()

    try:
        product = cursor.execute("""
            SELECT id, name, price, stock, active
            FROM products
            WHERE id = ?
        """, (product_id,)).fetchone()

        if not product:
            raise ValueError("Product not found.")

        if int(product["active"]) == 0:
            raise ValueError("Product tile is already removed.")

        before = int(product["stock"])
        created_at = now_string()

        cursor.execute("""
            UPDATE products
            SET active = 0
            WHERE id = ?
        """, (product_id,))

        cursor.execute("""
            INSERT INTO stock_movements
            (product_id, product_name, movement_type,
             stock_before, quantity_added, quantity_sold,
             adjustment, stock_after, reason, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            product_id,
            product["name"],
            "PRODUCT_REMOVED",
            before,
            0,
            0,
            0,
            before,
            "Product tile removed from POS (product history retained)",
            created_at
        ))

        connection.commit()

        return {
            "id": product_id,
            "name": product["name"],
            "stock": before,
            "removed_at": created_at
        }

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


# ============================================================
# FIND PRODUCT BY BARCODE
# ============================================================

def get_product_by_barcode(barcode):

    connection = get_connection()

    try:

        product = connection.execute("""
            SELECT id, name, price, stock, barcode, warranty_days
            FROM products
            WHERE barcode = ?
        """, (str(barcode).strip(),)).fetchone()

        if not product:
            return None

        return dict(product)

    finally:

        connection.close()




def update_product(product_id, name, price, stock, warranty_days=0):
    """Update product details and record stock changes in movement history."""
    connection = get_connection()
    cursor = connection.cursor()

    try:
        product = cursor.execute(
            "SELECT id, name, price, stock, warranty_days FROM products WHERE id = ?",
            (product_id,)
        ).fetchone()

        if not product:
            raise ValueError("Product not found.")

        old_stock = int(product["stock"])
        new_stock = int(stock)
        adjustment = new_stock - old_stock
        created_at = now_string()

        cursor.execute("""
            UPDATE products
            SET name = ?, price = ?, stock = ?, warranty_days = ?
            WHERE id = ?
        """, (name, float(price), new_stock, max(0, int(warranty_days or 0)), product_id))

        if adjustment != 0:
            cursor.execute("""
                INSERT INTO stock_movements
                (product_id, product_name, movement_type,
                 stock_before, quantity_added, quantity_sold,
                 adjustment, stock_after, reason, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                product_id,
                name,
                "PRODUCT_EDIT",
                old_stock,
                adjustment if adjustment > 0 else 0,
                0,
                adjustment,
                new_stock,
                "Stock changed while editing product",
                created_at
            ))

        connection.commit()

        return {
            "id": product_id,
            "name": name,
            "price": float(price),
            "stock": new_stock,
            "warranty_days": max(0, int(warranty_days or 0))
        }

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def complete_sale(cart, payment_method, sale_fee=0.0, sold_at_override=None):
    connection = get_connection()
    cursor = connection.cursor()
    # Prefer the POS device's local time when supplied by the client.
    # Fall back to the server clock for non-browser/internal callers.
    sold_at = str(sold_at_override).strip() if sold_at_override else now_string()
    transaction_id = str(uuid.uuid4())
    receipt_token = uuid.uuid4().hex + uuid.uuid4().hex
    total_sale = 0.0
    receipt_items = []

    try:
        sale_fee = round(float(sale_fee or 0), 2)
        if sale_fee < 0:
            raise ValueError("Sale fee cannot be negative.")

        for item_index, item in enumerate(cart):
            product_id = int(item.get("id"))
            quantity = int(item.get("quantity"))

            if quantity <= 0:
                raise ValueError("Invalid sale quantity.")

            product = cursor.execute(
                "SELECT id, name, price, stock, warranty_days FROM products WHERE id = ?",
                (product_id,)
            ).fetchone()

            if not product:
                raise ValueError("Product no longer exists.")

            if product["stock"] < quantity:
                raise ValueError(
                    f"Not enough stock for {product['name']}."
                )

            unit_price = float(product["price"])
            line_total = unit_price * quantity
            before = int(product["stock"])
            after = before - quantity

            cursor.execute(
                "UPDATE products SET stock = ? WHERE id = ?",
                (after, product_id)
            )

            cursor.execute("""
                INSERT INTO sales
                (product_id, product_name, quantity, unit_price,
                 total, payment_method, transaction_id, sale_fee, sold_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                product_id,
                product["name"],
                quantity,
                unit_price,
                line_total,
                payment_method,
                transaction_id,
                sale_fee if item_index == 0 else 0.0,
                sold_at
            ))

            cursor.execute("""
                INSERT INTO stock_movements
                (product_id, product_name, movement_type,
                 stock_before, quantity_added, quantity_sold,
                 adjustment, stock_after, reason, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                product_id,
                product["name"],
                "SALE",
                before,
                0,
                quantity,
                0,
                after,
                "Sale",
                sold_at
            ))

            total_sale += line_total
            warranty_days = int(product["warranty_days"] or 0)
            try:
                sold_dt = datetime.datetime.strptime(sold_at, "%Y-%m-%d %H:%M:%S")
                expiry_at = (sold_dt + datetime.timedelta(days=warranty_days)).strftime("%Y-%m-%d %H:%M:%S") if warranty_days > 0 else None
            except Exception:
                expiry_at = None
            receipt_items.append({
                "product_id": product_id,
                "name": product["name"],
                "quantity": quantity,
                "unit_price": round(unit_price, 2),
                "line_total": round(line_total, 2),
                "warranty_days": warranty_days,
                "warranty_start": sold_at,
                "warranty_expiry": expiry_at,
                "warranty_status": "ACTIVE" if warranty_days > 0 else "NO WARRANTY"
            })

        connection.commit()
        return {
            "subtotal": round(total_sale, 2),
            "sale_fee": round(sale_fee, 2),
            "total": round(total_sale + sale_fee, 2),
            "sold_at": sold_at,
            "transaction_id": transaction_id,
            "receipt_token": receipt_token,
            "items": receipt_items
        }

    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def get_stock_take():
    connection = get_connection()
    rows = connection.execute("""
        SELECT
            p.id,
            p.name,
            p.price,
            p.stock,
            COALESCE(SUM(
                CASE
                    WHEN s.sold_at LIKE date('now', 'localtime') || '%' THEN s.quantity
                    ELSE 0
                END
            ), 0) AS sold_today,
            COALESCE(SUM(
                CASE
                    WHEN s.sold_at LIKE date('now', 'localtime') || '%' THEN s.total
                    ELSE 0
                END
            ), 0) AS sales_today
        FROM products p
        LEFT JOIN sales s ON s.product_id = p.id
        GROUP BY p.id
        ORDER BY p.name
    """).fetchall()
    connection.close()
    return [dict(row) for row in rows]


def get_today_sales():
    connection = get_connection()
    rows = connection.execute("""
        SELECT id, product_name, quantity, unit_price, total, sale_fee,
               payment_method, sold_at
        FROM sales
        WHERE sold_at LIKE date('now', 'localtime') || '%'
        ORDER BY id DESC
    """).fetchall()
    connection.close()
    return [dict(row) for row in rows]


def add_stock(product_id, quantity, reason):
    if quantity <= 0:
        raise ValueError("Quantity must be greater than zero.")

    connection = get_connection()
    cursor = connection.cursor()

    try:
        product = cursor.execute(
            "SELECT id, name, stock FROM products WHERE id = ?",
            (product_id,)
        ).fetchone()

        if not product:
            raise ValueError("Product not found.")

        before = int(product["stock"])
        after = before + quantity
        created_at = now_string()

        cursor.execute(
            "UPDATE products SET stock = ? WHERE id = ?",
            (after, product_id)
        )

        cursor.execute("""
            INSERT INTO stock_movements
            (product_id, product_name, movement_type,
             stock_before, quantity_added, quantity_sold,
             adjustment, stock_after, reason, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            product_id, product["name"], "STOCK_IN",
            before, quantity, 0, quantity, after,
            reason, created_at
        ))

        connection.commit()
        return {
            "stock_before": before,
            "quantity_added": quantity,
            "stock_after": after,
            "created_at": created_at
        }
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def remove_stock(product_id, quantity, reason):
    if quantity <= 0:
        raise ValueError("Quantity must be greater than zero.")

    connection = get_connection()
    cursor = connection.cursor()

    try:
        product = cursor.execute(
            "SELECT id, name, stock FROM products WHERE id = ?",
            (product_id,)
        ).fetchone()

        if not product:
            raise ValueError("Product not found.")

        before = int(product["stock"])
        if quantity > before:
            raise ValueError("Cannot remove more stock than is available.")

        after = before - quantity
        created_at = now_string()

        cursor.execute(
            "UPDATE products SET stock = ? WHERE id = ?",
            (after, product_id)
        )

        cursor.execute("""
            INSERT INTO stock_movements
            (product_id, product_name, movement_type,
             stock_before, quantity_added, quantity_sold,
             adjustment, stock_after, reason, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            product_id, product["name"], "STOCK_OUT",
            before, 0, 0, -quantity, after,
            reason, created_at
        ))

        connection.commit()
        return {
            "stock_before": before,
            "quantity_removed": quantity,
            "stock_after": after,
            "created_at": created_at
        }
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def record_stocktake(product_id, counted_stock, notes):
    if counted_stock < 0:
        raise ValueError("Counted stock cannot be negative.")

    connection = get_connection()
    cursor = connection.cursor()

    try:
        product = cursor.execute(
            "SELECT id, name, stock FROM products WHERE id = ?",
            (product_id,)
        ).fetchone()

        if not product:
            raise ValueError("Product not found.")

        system_stock = int(product["stock"])
        variance = counted_stock - system_stock
        taken_at = now_string()

        cursor.execute(
            "UPDATE products SET stock = ? WHERE id = ?",
            (counted_stock, product_id)
        )

        cursor.execute("""
            INSERT INTO stock_takes
            (product_id, product_name, system_stock,
             counted_stock, variance, notes, taken_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            product_id, product["name"], system_stock,
            counted_stock, variance, notes, taken_at
        ))

        if variance:
            cursor.execute("""
                INSERT INTO stock_movements
                (product_id, product_name, movement_type,
                 stock_before, quantity_added, quantity_sold,
                 adjustment, stock_after, reason, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                product_id, product["name"], "STOCKTAKE",
                system_stock,
                max(variance, 0),
                0,
                variance,
                counted_stock,
                notes or "Physical stocktake",
                taken_at
            ))

        connection.commit()
        return {
            "system_stock": system_stock,
            "counted_stock": counted_stock,
            "variance": variance,
            "stock_after": counted_stock,
            "taken_at": taken_at
        }
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def get_stock_report_data():
    """Return the full inventory audit data used by the PDF report."""
    connection = get_connection()
    try:
        products = connection.execute("""
            SELECT id, name, price, stock, barcode, active
            FROM products
            ORDER BY name
        """).fetchall()

        movements = connection.execute("""
            SELECT *
            FROM stock_movements
            ORDER BY id ASC
        """).fetchall()

        stocktakes = connection.execute("""
            SELECT *
            FROM stock_takes
            ORDER BY id ASC
        """).fetchall()

        monthly_reports = connection.execute("""
            SELECT *
            FROM monthly_reports
            ORDER BY id ASC
        """).fetchall()

        return {
            "products": [dict(row) for row in products],
            "movements": [dict(row) for row in movements],
            "stocktakes": [dict(row) for row in stocktakes],
            "monthly_reports": [dict(row) for row in monthly_reports],
        }
    finally:
        connection.close()


def get_stock_movements(product_id=None):
    connection = get_connection()
    if product_id:
        rows = connection.execute("""
            SELECT * FROM stock_movements
            WHERE product_id = ?
            ORDER BY id DESC
        """, (product_id,)).fetchall()
    else:
        rows = connection.execute("""
            SELECT * FROM stock_movements
            ORDER BY id DESC
        """).fetchall()
    connection.close()
    return [dict(row) for row in rows]


def get_stocktake_history(product_id=None):
    connection = get_connection()
    if product_id:
        rows = connection.execute("""
            SELECT * FROM stock_takes
            WHERE product_id = ?
            ORDER BY id DESC
        """, (product_id,)).fetchall()
    else:
        rows = connection.execute("""
            SELECT * FROM stock_takes
            ORDER BY id DESC
        """).fetchall()
    connection.close()
    return [dict(row) for row in rows]


def create_monthly_report(cash_at_hand, damaged_goods, created_at_override=None):
    cash_at_hand = float(cash_at_hand)
    if cash_at_hand < 0:
        raise ValueError("Cash at hand cannot be negative.")

    connection = get_connection()
    cursor = connection.cursor()

    try:
        created_at = str(created_at_override or now_string()).strip() or now_string()
        report_month = created_at[:7] if len(created_at) >= 7 else datetime.datetime.now().strftime("%Y-%m")
        damaged_units = 0
        damaged_value = 0.0
        damaged_items = []

        # Warranty returns are permanently classified as damaged goods. They
        # were never returned to sellable stock, so the report records their
        # value here without subtracting stock a second time.
        warranty_damaged = cursor.execute("""
            SELECT product_id, product_name, SUM(quantity) AS quantity,
                   SUM(quantity * (SELECT price FROM products WHERE products.id = warranty_claims.product_id)) AS value
            FROM warranty_claims
            WHERE substr(action_at,1,7)=?
            GROUP BY product_id, product_name
        """, (report_month,)).fetchall()
        for item in warranty_damaged:
            qty=int(item["quantity"] or 0); value=float(item["value"] or 0)
            damaged_units += qty; damaged_value += value
            damaged_items.append({"product_id": item["product_id"], "product_name": item["product_name"], "quantity": qty, "value": round(value,2), "source": "WARRANTY_RETURN"})

        # Remove every manually entered damaged item from actual stock and record it.
        for item in damaged_goods:
            product_id = int(item.get("product_id"))
            quantity = int(item.get("quantity"))

            if quantity <= 0:
                raise ValueError("Damaged quantity must be greater than zero.")

            product = cursor.execute("""
                SELECT id, name, price, stock
                FROM products
                WHERE id = ?
            """, (product_id,)).fetchone()

            if not product:
                raise ValueError("Damaged product not found.")

            if quantity > product["stock"]:
                raise ValueError(
                    f"Damaged quantity for {product['name']} is greater than stock."
                )

            before = int(product["stock"])
            after = before - quantity
            value = float(product["price"]) * quantity

            cursor.execute(
                "UPDATE products SET stock = ? WHERE id = ?",
                (after, product_id)
            )

            cursor.execute("""
                INSERT INTO stock_movements
                (product_id, product_name, movement_type,
                 stock_before, quantity_added, quantity_sold,
                 adjustment, stock_after, reason, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                product_id, product["name"], "DAMAGED",
                before, 0, 0, -quantity, after,
                "Damaged goods - monthly report", created_at
            ))

            damaged_units += quantity
            damaged_value += value
            damaged_items.append({
                "product_id": product_id,
                "product_name": product["name"],
                "quantity": quantity,
                "value": round(value, 2)
            })

        stock_summary = cursor.execute("""
            SELECT
                COALESCE(SUM(stock), 0) AS stock_units,
                COALESCE(SUM(stock * price), 0) AS stock_value
            FROM products
        """).fetchone()

        # Reconcile the register against recorded sales for this month.
        sales_summary = cursor.execute("""
            SELECT
                COUNT(DISTINCT CASE WHEN payment_method = 'cash' THEN transaction_id END) AS cash_sales_count,
                COALESCE(SUM(CASE WHEN payment_method = 'cash' THEN total + COALESCE(sale_fee, 0) ELSE 0 END), 0) - COALESCE((SELECT SUM(refund_value) FROM warranty_claims wc WHERE wc.payment_method='cash' AND wc.action='REFUND' AND substr(wc.action_at,1,7)=?),0) AS cash_sales_amount,
                COUNT(DISTINCT CASE WHEN payment_method = 'card' THEN transaction_id END) AS card_sales_count,
                COALESCE(SUM(CASE WHEN payment_method = 'card' THEN total + COALESCE(sale_fee, 0) ELSE 0 END), 0) - COALESCE((SELECT SUM(refund_value) FROM warranty_claims wc WHERE wc.payment_method='card' AND wc.action='REFUND' AND substr(wc.action_at,1,7)=?),0) AS card_sales_amount,
                COUNT(DISTINCT transaction_id) AS total_sales_count,
                COALESCE(SUM(total + COALESCE(sale_fee, 0)), 0) AS total_sales_amount,
                COALESCE(SUM(quantity), 0) AS total_sales_units
            FROM sales
            WHERE substr(sold_at, 1, 7) = ?
        """, (report_month, report_month, report_month)).fetchone()

        cash_sales_count = int(sales_summary["cash_sales_count"] or 0)
        cash_sales_amount = float(sales_summary["cash_sales_amount"] or 0)
        card_sales_count = int(sales_summary["card_sales_count"] or 0)
        card_sales_amount = float(sales_summary["card_sales_amount"] or 0)
        total_sales_count = int(sales_summary["total_sales_count"] or 0)
        total_sales_amount = float(sales_summary["total_sales_amount"] or 0)
        total_sales_units = int(sales_summary["total_sales_units"] or 0)

        # No opening-float input exists yet, so expected register cash
        # is the recorded cash sales for this reporting period.
        expected_cash = cash_sales_amount
        cash_variance = cash_at_hand - expected_cash
        cash_shortage = max(0.0, -cash_variance)
        total_loss = damaged_value + cash_shortage

        cursor.execute("""
            INSERT INTO monthly_reports
            (report_month, cash_at_hand, expected_cash, cash_variance,
             stock_units, stock_value, damaged_units, damaged_value,
             total_loss, cash_sales_count, cash_sales_amount,
             card_sales_count, card_sales_amount, total_sales_count,
             total_sales_amount, total_sales_units, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            report_month,
            cash_at_hand,
            expected_cash,
            cash_variance,
            int(stock_summary["stock_units"]),
            float(stock_summary["stock_value"]),
            damaged_units,
            damaged_value,
            total_loss,
            cash_sales_count,
            cash_sales_amount,
            card_sales_count,
            card_sales_amount,
            total_sales_count,
            total_sales_amount,
            total_sales_units,
            created_at
        ))

        report_id = cursor.lastrowid

        for damaged_item in damaged_items:
            cursor.execute("""
                INSERT INTO monthly_report_items
                (report_id, product_id, product_name, quantity, value)
                VALUES (?, ?, ?, ?, ?)
            """, (
                report_id,
                damaged_item["product_id"],
                damaged_item["product_name"],
                damaged_item["quantity"],
                damaged_item["value"]
            ))

        connection.commit()

        return {
            "id": report_id,
            "report_month": report_month,
            "cash_at_hand": round(cash_at_hand, 2),
            "expected_cash": round(expected_cash, 2),
            "cash_variance": round(cash_variance, 2),
            "cash_sales_count": cash_sales_count,
            "cash_sales_amount": round(cash_sales_amount, 2),
            "card_sales_count": card_sales_count,
            "card_sales_amount": round(card_sales_amount, 2),
            "total_sales_count": total_sales_count,
            "total_sales_amount": round(total_sales_amount, 2),
            "total_sales_units": total_sales_units,
            "stock_units": int(stock_summary["stock_units"]),
            "stock_value": round(float(stock_summary["stock_value"]), 2),
            "damaged_units": damaged_units,
            "damaged_value": round(damaged_value, 2),
            "total_loss": round(total_loss, 2),
            "created_at": created_at,
            "damaged_items": damaged_items
        }

    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def save_receipt_document(receipt):
    """Persist a completed receipt so it can be recalled and regenerated as a PDF."""
    connection = get_connection()
    try:
        transaction_id = str(receipt.get("transaction_id") or "").strip()
        if not transaction_id:
            raise ValueError("Receipt transaction ID is required.")

        sold_at = str(receipt.get("sold_at") or now_string()).strip()
        store_name = str(receipt.get("store_name") or "Easy Sales").strip()
        payment_method = str(receipt.get("payment_method") or "").upper().strip()
        currency = receipt.get("currency") or {}
        items = receipt.get("items") or []
        cash_received = receipt.get("cash_received", None)
        change_amount = receipt.get("change", None)
        receipt_token = str(receipt.get("receipt_token") or uuid.uuid4().hex + uuid.uuid4().hex)

        connection.execute("""
            INSERT OR REPLACE INTO receipt_documents
            (transaction_id, store_name, sold_at, payment_method,
             subtotal, sale_fee, total, cash_received, change_amount,
             currency_json, items_json, receipt_token, receipt_status, refund_total, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            transaction_id,
            store_name,
            sold_at,
            payment_method,
            float(receipt.get("subtotal") or 0),
            float(receipt.get("sale_fee") or 0),
            float(receipt.get("total") or 0),
            None if cash_received is None else float(cash_received),
            None if change_amount is None else float(change_amount),
            json.dumps(currency, ensure_ascii=False),
            json.dumps(items, ensure_ascii=False),
            receipt_token,
            str(receipt.get("receipt_status") or "COMPLETED"),
            float(receipt.get("refund_total") or 0),
            sold_at
        ))
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def get_receipt_documents(limit=500):
    connection = get_connection()
    try:
        rows = connection.execute("""
            SELECT id, transaction_id, store_name, sold_at, payment_method,
                   subtotal, sale_fee, total, cash_received, change_amount,
                   currency_json, items_json, receipt_token, receipt_status, refund_total, created_at
            FROM receipt_documents
            ORDER BY id DESC
            LIMIT ?
        """, (int(limit),)).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            try:
                item["currency"] = json.loads(item.pop("currency_json") or "{}")
            except Exception:
                item["currency"] = {}
            try:
                item["items"] = json.loads(item.pop("items_json") or "[]")
            except Exception:
                item["items"] = []
            result.append(item)
        return result
    finally:
        connection.close()


def get_receipt_document(transaction_id):
    connection = get_connection()
    try:
        row = connection.execute("""
            SELECT id, transaction_id, store_name, sold_at, payment_method,
                   subtotal, sale_fee, total, cash_received, change_amount,
                   currency_json, items_json, receipt_token, receipt_status, refund_total, created_at
            FROM receipt_documents
            WHERE transaction_id = ?
        """, (str(transaction_id).strip(),)).fetchone()
        if not row:
            return None
        item = dict(row)
        try:
            item["currency"] = json.loads(item.pop("currency_json") or "{}")
        except Exception:
            item["currency"] = {}
        try:
            item["items"] = json.loads(item.pop("items_json") or "[]")
        except Exception:
            item["items"] = []
        return item
    finally:
        connection.close()



def get_receipt_by_token(receipt_token):
    connection = get_connection()
    try:
        row = connection.execute("SELECT * FROM receipt_documents WHERE receipt_token = ?", (str(receipt_token).strip(),)).fetchone()
        if not row:
            return None
        item = dict(row)
        for key, default in (("currency_json", {}), ("items_json", [])):
            try: item[key[:-5] if key.endswith("_json") else key] = json.loads(item.pop(key) or json.dumps(default))
            except Exception: item[key[:-5] if key.endswith("_json") else key] = default
        return item
    finally:
        connection.close()


def process_warranty_claim(receipt_token, product_id, quantity, action, device_time=None, replacement_product_id=None, reason=""):
    action = str(action or "").upper().strip()
    if action not in {"REFUND", "REPLACEMENT"}: raise ValueError("Invalid warranty action.")
    quantity = int(quantity)
    if quantity <= 0: raise ValueError("Quantity must be greater than zero.")
    connection = get_connection(); cursor = connection.cursor()
    try:
        receipt = cursor.execute("SELECT * FROM receipt_documents WHERE receipt_token = ?", (str(receipt_token).strip(),)).fetchone()
        if not receipt: raise ValueError("Receipt not found.")
        items = json.loads(receipt["items_json"] or "[]")
        target = next((i for i in items if int(i.get("product_id", -1)) == int(product_id)), None)
        if not target: raise ValueError("Product is not on this receipt.")
        already = cursor.execute("SELECT COALESCE(SUM(quantity),0) FROM warranty_claims WHERE receipt_token=? AND product_id=?", (receipt_token, product_id)).fetchone()[0]
        if int(already or 0) + quantity > int(target.get("quantity") or 0): raise ValueError("Claim quantity exceeds the quantity on the receipt.")
        warranty_days = int(target.get("warranty_days") or 0)
        unit_value = float(target.get("unit_price") or 0) * quantity
        sold_at = str(receipt["sold_at"])
        expiry = target.get("warranty_expiry")
        if warranty_days <= 0: raise ValueError("This product has no warranty.")
        now = str(device_time or now_string()).strip()
        try: expired = datetime.datetime.strptime(now, "%Y-%m-%d %H:%M:%S") > datetime.datetime.strptime(expiry, "%Y-%m-%d %H:%M:%S")
        except Exception: expired = False
        if expired: raise ValueError("Warranty has expired for this product.")
        replacement = None
        if action == "REPLACEMENT":
            if replacement_product_id is None: raise ValueError("Select a replacement product.")
            replacement = cursor.execute("SELECT id,name,stock,price FROM products WHERE id=? AND active=1", (int(replacement_product_id),)).fetchone()
            if not replacement: raise ValueError("Replacement product not found.")
            if int(replacement["stock"]) < quantity: raise ValueError("Not enough stock for the replacement product.")
            before=int(replacement["stock"]); after=before-quantity
            cursor.execute("UPDATE products SET stock=? WHERE id=?", (after, replacement["id"]))
            cursor.execute("""INSERT INTO stock_movements (product_id,product_name,movement_type,stock_before,quantity_added,quantity_sold,adjustment,stock_after,reason,created_at) VALUES (?,?,?,?,?,?,?,?,?,?)""", (replacement["id"],replacement["name"],"WARRANTY_REPLACEMENT",before,0,quantity,-quantity,after,"Replacement issued for receipt " + str(receipt["transaction_id"]),now))
        # Returned goods never go back into sellable stock. Record the physical
        # return as a DAMAGED movement without changing sellable stock.
        current_product = cursor.execute("SELECT stock FROM products WHERE id=?", (target["product_id"],)).fetchone()
        current_stock = int(current_product["stock"] or 0)
        cursor.execute("""INSERT INTO stock_movements (product_id,product_name,movement_type,stock_before,quantity_added,quantity_sold,adjustment,stock_after,reason,created_at) VALUES (?,?,?,?,?,?,?,?,?,?)""", (target["product_id"],target["name"],"DAMAGED_RETURN",current_stock,0,0,0,current_stock,"Warranty return - damaged goods - receipt " + str(receipt["transaction_id"]),now))
        cursor.execute("""INSERT INTO warranty_claims (transaction_id,receipt_token,product_id,product_name,quantity,action,warranty_days,sold_at,expiry_at,action_at,replacement_product_id,replacement_product_name,replacement_quantity,refund_value,payment_method,reason) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (receipt["transaction_id"],receipt_token,target["product_id"],target["name"],quantity,action,warranty_days,sold_at,expiry,now,replacement["id"] if replacement else None,replacement["name"] if replacement else None,quantity if replacement else 0,unit_value if action=="REFUND" else 0,receipt["payment_method"],str(reason or "Warranty claim")))
        # Update saved receipt item state permanently.
        claimed = int(already or 0) + quantity
        target["claimed_quantity"] = claimed
        target["claim_status"] = "REFUNDED" if action == "REFUND" and claimed >= int(target.get("quantity") or 0) else ("REPLACED" if action == "REPLACEMENT" and claimed >= int(target.get("quantity") or 0) else "PARTIALLY REFUNDED" if action == "REFUND" else "PARTIALLY REPLACED")
        target["last_claim_action"] = action
        target["last_claim_at"] = now
        target["warranty_status"] = target["claim_status"]
        previous_refund = float(receipt["refund_total"] or 0)
        new_refund = previous_refund + (unit_value if action == "REFUND" else 0)
        receipt_status = "REFUNDED" if action == "REFUND" and claimed >= int(target.get("quantity") or 0) else ("REPLACED" if action == "REPLACEMENT" and claimed >= int(target.get("quantity") or 0) else "PARTIALLY REFUNDED" if action == "REFUND" else "PARTIALLY REPLACED")
        cursor.execute("UPDATE receipt_documents SET items_json=?, receipt_status=?, refund_total=? WHERE transaction_id=?", (json.dumps(items, ensure_ascii=False), receipt_status, new_refund, receipt["transaction_id"]))
        connection.commit()
        return get_receipt_by_token(receipt_token)
    except Exception:
        connection.rollback(); raise
    finally: connection.close()


def get_warranty_claims(receipt_token=None, report_month=None):
    connection=get_connection()
    try:
        if receipt_token:
            rows=connection.execute("SELECT * FROM warranty_claims WHERE receipt_token=? ORDER BY id DESC",(receipt_token,)).fetchall()
        else:
            rows=connection.execute("SELECT * FROM warranty_claims WHERE substr(action_at,1,7)=? ORDER BY id",(report_month,)).fetchall()
        return [dict(r) for r in rows]
    finally: connection.close()

def get_monthly_sales_summary():
    connection = get_connection()
    try:
        report_month = datetime.datetime.now().strftime("%Y-%m")
        row = connection.execute("""
            SELECT
                COUNT(DISTINCT CASE WHEN payment_method = 'cash' THEN transaction_id END) AS cash_sales_count,
                COALESCE(SUM(CASE WHEN payment_method = 'cash' THEN total + COALESCE(sale_fee, 0) ELSE 0 END), 0) - COALESCE((SELECT SUM(refund_value) FROM warranty_claims wc WHERE wc.payment_method='cash' AND wc.action='REFUND' AND substr(wc.action_at,1,7)=?),0) AS cash_sales_amount,
                COUNT(DISTINCT CASE WHEN payment_method = 'card' THEN transaction_id END) AS card_sales_count,
                COALESCE(SUM(CASE WHEN payment_method = 'card' THEN total + COALESCE(sale_fee, 0) ELSE 0 END), 0) - COALESCE((SELECT SUM(refund_value) FROM warranty_claims wc WHERE wc.payment_method='card' AND wc.action='REFUND' AND substr(wc.action_at,1,7)=?),0) AS card_sales_amount,
                COUNT(DISTINCT transaction_id) AS total_sales_count,
                COALESCE(SUM(total + COALESCE(sale_fee, 0)), 0) AS total_sales_amount,
                COALESCE(SUM(quantity), 0) AS total_sales_units
            FROM sales
            WHERE substr(sold_at, 1, 7) = ?
        """, (report_month, report_month, report_month)).fetchone()

        return {
            "report_month": report_month,
            "cash_sales_count": int(row["cash_sales_count"] or 0),
            "cash_sales_amount": round(float(row["cash_sales_amount"] or 0), 2),
            "card_sales_count": int(row["card_sales_count"] or 0),
            "card_sales_amount": round(float(row["card_sales_amount"] or 0), 2),
            "total_sales_count": int(row["total_sales_count"] or 0),
            "total_sales_amount": round(float(row["total_sales_amount"] or 0), 2),
            "total_sales_units": int(row["total_sales_units"] or 0)
        }
    finally:
        connection.close()

def get_monthly_reports():
    connection = get_connection()
    reports = connection.execute("""
        SELECT * FROM monthly_reports
        ORDER BY id DESC
    """).fetchall()

    result = []
    for report in reports:
        item = dict(report)
        item["damaged_items"] = [
            dict(row)
            for row in connection.execute("""
                SELECT
                    product_id,
                    product_name,
                    quantity,
                    value
                FROM monthly_report_items
                WHERE report_id = ?
                ORDER BY id
            """, (report["id"],)).fetchall()
        ]
        result.append(item)

    connection.close()
    return result
