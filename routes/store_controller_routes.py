# ============================================================
# EASY SALES - SECURE CONTROLLER ROUTES
# ============================================================

from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    request,
    session
)

from store_controller import (
    init_controller,
    create_store,
    get_all_stores,
    get_store,
    activate_store,
    deactivate_store,
    reset_passkey,
    update_store_name,
    set_employee_mode_feature,
    reset_employee_mode_password,
    set_restaurant_mode,
    get_restaurant_mode,
    activate_30_day_subscription,
    deactivate_subscription,
    subscription_status,
)

from controller_auth import (
    init_controller_auth,
    controller_is_configured,
    set_controller_password,
    verify_controller_password,
    controller_login_required,
)

# Rename the imported database function so it does not conflict
# with the Flask route function below.
from store_database import reset_store_data as reset_store_database


# ============================================================
# CONTROLLER BLUEPRINT
# ============================================================

controller_bp = Blueprint(
    "controller",
    __name__,
    url_prefix="/controller"
)


# ============================================================
# LOAD DASHBOARD
# ============================================================

def load_dashboard():
    """Load stores and calculate dashboard totals."""

    stores = get_all_stores()

    total = len(stores)

    active = sum(
        1 for store in stores
        if store["status"] == "ACTIVE"
    )

    inactive = sum(
        1 for store in stores
        if store["status"] == "INACTIVE"
    )

    available = sum(
        1 for store in stores
        if store["status"] == "AVAILABLE"
    )

    return stores, {
        "total": total,
        "active": active,
        "inactive": inactive,
        "available": available,
    }


# ============================================================
# FIRST-TIME CONTROLLER SETUP
# ============================================================

@controller_bp.route(
    "/setup",
    methods=["GET", "POST"]
)
def setup():

    init_controller_auth()

    if controller_is_configured():
        return redirect(
            url_for("controller.login")
        )

    if request.method == "POST":

        password = request.form.get(
            "password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        if password != confirm_password:

            flash(
                "Passwords do not match.",
                "error"
            )

            return redirect(
                url_for("controller.setup")
            )

        try:

            set_controller_password(
                password
            )

        except ValueError as error:

            flash(
                str(error),
                "error"
            )

            return redirect(
                url_for("controller.setup")
            )

        flash(
            "Controller password created. Please log in.",
            "success"
        )

        return redirect(
            url_for("controller.login")
        )

    return render_template(
        "login.html",
        mode="setup"
    )


# ============================================================
# CONTROLLER LOGIN
# ============================================================

@controller_bp.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    init_controller_auth()

    if not controller_is_configured():

        return redirect(
            url_for("controller.setup")
        )

    if session.get(
        "controller_authenticated"
    ):

        return redirect(
            url_for("controller.dashboard")
        )

    if request.method == "POST":

        password = request.form.get(
            "password",
            ""
        )

        if verify_controller_password(password):

            session.clear()

            session[
                "controller_authenticated"
            ] = True

            session.permanent = False

            return redirect(
                url_for("controller.dashboard")
            )

        flash(
            "Invalid controller password.",
            "error"
        )

    return render_template(
        "login.html",
        mode="login"
    )

# ============================================================
# CONTROLLER LOGOUT
# ============================================================

@controller_bp.route(
    "/logout",
    methods=["POST", "GET"]
)
def logout():

    session.pop(
        "controller_authenticated",
        None
    )

    return redirect(
        url_for("controller.login")
    )


# ============================================================
# CONTROLLER DASHBOARD
# ============================================================

@controller_bp.route("/")
@controller_login_required
def dashboard():

    init_controller()

    stores, stats = load_dashboard()

    return render_template(
        "controller_dashboard.html",
        stores=stores,
        stats=stats,
    )


# ============================================================
# CREATE A NEW CLIENT STORE
# ============================================================

@controller_bp.route(
    "/create-store",
    methods=["POST"]
)
@controller_login_required
def create_new_store():

    try:

        store_name = request.form.get(
            "store_name",
            ""
        ).strip()

        notes = request.form.get(
            "notes",
            ""
        ).strip()

        result = create_store(
            store_name,
            notes
        )

        flash(
            f"Store created successfully! "
            f"Store ID: {result['store_id']} | "
            f"Passkey: {result['passkey']}",
            "success",
        )

    except Exception as error:

        flash(
            str(error),
            "error"
        )

    return redirect(
        url_for("controller.dashboard")
    )


# ============================================================
# ACTIVATE A STORE
# ============================================================

@controller_bp.route(
    "/activate/<store_id>",
    methods=["POST"]
)
@controller_login_required
def activate(store_id):

    try:

        activate_store(
            store_id.upper()
        )

        flash(
            f"{store_id.upper()} has been activated.",
            "success"
        )

    except Exception as error:

        flash(
            str(error),
            "error"
        )

    return redirect(
        url_for("controller.dashboard")
    )


# ============================================================
# DEACTIVATE A STORE
# ============================================================

@controller_bp.route(
    "/deactivate/<store_id>",
    methods=["POST"]
)
@controller_login_required
def deactivate(store_id):

    try:

        deactivate_store(
            store_id.upper()
        )

        flash(
            f"{store_id.upper()} has been deactivated. "
            f"The client's private store data has been kept safe.",
            "success",
        )

    except Exception as error:

        flash(
            str(error),
            "error"
        )

    return redirect(
        url_for("controller.dashboard")
    )


# ============================================================
# RESET A STORE PASSKEY
# ============================================================

@controller_bp.route(
    "/reset-passkey/<store_id>",
    methods=["POST"]
)
@controller_login_required
def reset_store_passkey(store_id):

    try:

        new_passkey = reset_passkey(
            store_id.upper()
        )

        flash(
            f"New passkey for {store_id.upper()}: "
            f"{new_passkey}",
            "success",
        )

    except Exception as error:

        flash(
            str(error),
            "error"
        )

    return redirect(
        url_for("controller.dashboard")
    )


# ============================================================
# RESET STORE DATA
# ============================================================

@controller_bp.route(
    "/reset-store/<store_id>",
    methods=["POST"]
)
@controller_login_required
def reset_store_data(store_id):
    """
    Reset all POS data for ONE store only.

    The store account, Store ID, passkey and status remain unchanged.
    """

    try:

        store_id = store_id.upper()

        # Make sure the store exists.
        store = get_store(store_id)

        if store is None:

            raise ValueError(
                "Store not found."
            )

        # Reset ONLY this store's private database.
        reset_store_database(
            store_id
        )

        flash(
            f"All POS data for {store_id} "
            "has been reset successfully. "
            "The store account and access details were kept.",
            "success"
        )

    except ValueError as error:

        flash(
            str(error),
            "error"
        )

    except Exception as error:

        print(
            "RESET STORE DATA ERROR:",
            error
        )

        flash(
            "Could not reset the store data.",
            "error"
        )

    return redirect(
        url_for("controller.dashboard")
    )


# ============================================================
# 30-DAY SUBSCRIPTION
# ============================================================

@controller_bp.route("/subscription/activate/<store_id>", methods=["POST"])
@controller_login_required
def activate_subscription(store_id):
    try:
        expiry = activate_30_day_subscription(store_id.upper())
        flash(f"30-day subscription activated for {store_id.upper()}. Expires: {expiry}.", "success")
    except Exception as error:
        flash(str(error), "error")
    return redirect(url_for("controller.store_details", store_id=store_id.upper()))


@controller_bp.route("/subscription/disable/<store_id>", methods=["POST"])
@controller_login_required
def disable_subscription(store_id):
    try:
        deactivate_subscription(store_id.upper())
        flash(f"Subscription disabled for {store_id.upper()}.", "success")
    except Exception as error:
        flash(str(error), "error")
    return redirect(url_for("controller.store_details", store_id=store_id.upper()))


# ============================================================
# UPDATE STORE / RECEIPT NAME
# ============================================================

@controller_bp.route(
    "/store/<store_id>/update-name",
    methods=["POST"]
)
@controller_login_required
def update_name(store_id):

    try:

        store_name = request.form.get(
            "store_name",
            ""
        ).strip()

        update_store_name(
            store_id.upper(),
            store_name
        )

        flash(
            f"Store/receipt name updated for {store_id.upper()}.",
            "success"
        )

    except Exception as error:

        flash(
            str(error),
            "error"
        )

    return redirect(
        url_for(
            "controller.store_details",
            store_id=store_id.upper()
        )
    )




# ============================================================
# EMPLOYEE MODE ADD-ON
# ============================================================

@controller_bp.route(
    "/store/<store_id>/employee-mode/enable",
    methods=["POST"]
)
@controller_login_required
def enable_employee_mode_addon(store_id):
    try:
        set_employee_mode_feature(store_id.upper(), True)
        flash(
            f"Employee Mode add-on enabled for {store_id.upper()}. "
            "The store will ask the owner to create its Employee Mode password.",
            "success"
        )
    except Exception as error:
        flash(str(error), "error")
    return redirect(url_for("controller.store_details", store_id=store_id.upper()))


@controller_bp.route(
    "/store/<store_id>/employee-mode/disable",
    methods=["POST"]
)
@controller_login_required
def disable_employee_mode_addon(store_id):
    try:
        set_employee_mode_feature(store_id.upper(), False)
        flash(
            f"Employee Mode add-on disabled for {store_id.upper()}.",
            "success"
        )
    except Exception as error:
        flash(str(error), "error")
    return redirect(url_for("controller.store_details", store_id=store_id.upper()))


@controller_bp.route(
    "/store/<store_id>/employee-mode/reset-password",
    methods=["POST"]
)
@controller_login_required
def reset_employee_mode_store_password(store_id):
    try:
        reset_employee_mode_password(store_id.upper())
        flash(
            f"Employee Mode password reset for {store_id.upper()}. "
            "The setup popup will appear the next time the store is opened.",
            "success"
        )
    except Exception as error:
        flash(str(error), "error")
    return redirect(url_for("controller.store_details", store_id=store_id.upper()))



# ============================================================
# RESTAURANT ADD-ON
# ============================================================
@controller_bp.route("/store/<store_id>/restaurant/enable", methods=["POST"])
@controller_login_required
def enable_restaurant_addon(store_id):
    try:
        set_restaurant_mode(store_id.upper(), True)
        flash(f"Restaurant add-on enabled for {store_id.upper()}.", "success")
    except Exception as error:
        flash(str(error), "error")
    return redirect(url_for("controller.store_details", store_id=store_id.upper()))

@controller_bp.route("/store/<store_id>/restaurant/disable", methods=["POST"])
@controller_login_required
def disable_restaurant_addon(store_id):
    try:
        set_restaurant_mode(store_id.upper(), False)
        flash(f"Restaurant add-on disabled for {store_id.upper()}.", "success")
    except Exception as error:
        flash(str(error), "error")
    return redirect(url_for("controller.store_details", store_id=store_id.upper()))

# ============================================================
# VIEW STORE DETAILS
# ============================================================

@controller_bp.route(
    "/store/<store_id>"
)
@controller_login_required
def store_details(store_id):

    store = get_store(
        store_id.upper()
    )

    if store is None:

        flash(
            "Store not found.",
            "error"
        )

        return redirect(
            url_for("controller.dashboard")
        )

    return render_template(
        "store_details.html",
        store=store
    )
