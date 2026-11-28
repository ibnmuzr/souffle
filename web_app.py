"""Soufflé Management System: web frontend (Milestone 6 HCI design).

Two interfaces, as in the Milestone 6 wireframes:
  * the customer website  (/)        Home, Menu, Cart (Order Summary), checkout,
                                      My Orders, Pay by Card (Story 6.2.1 A)
  * the employee portal   (/portal)  sign-in, Dashboard, Orders (create, modify, cancel,
                                      track and complete), Kitchen, Pay by Cash
                                      (Story 6.2.2 B), Menu, Inventory (Story 6.1),
                                      and the manager's Accounts, Promotions and Reports

Every button calls the same class-diagram operations as the terminal screens
(OrderHandler, Customer.payOrder, InventoryUI.updateQuantity, Promotion, the Report
classes...), so the sequence diagrams are unchanged. Messages the classes print
(kitchen notices, receipts, reports) are captured and shown on the page.

Run from the project folder:
    pip install -r requirements.txt
    python3 web_app.py          then open http://127.0.0.1:5000
"""
import io
from contextlib import closing, redirect_stdout
from datetime import date, datetime
from functools import wraps

from flask import (Flask, Response, flash, redirect, render_template, request,
                   send_from_directory, session, url_for)

from database.connection import DB_PATH, get_connection
from database.setup_db import create_database, migrate_database
from models import (CardPayment, CashPayment, CustomerLoyaltyReport, InventoryReport,
                    InventoryUI, OrderHandler, Promotion, Receipt, SalesReport)
from models.inventory import load_inventory
from models.inventory_ui import LOW_STOCK_FILTER
from models.orders import (FINAL_STATES, NEEDS_APPROVAL, NOT_STARTED, load_menu,
                           load_menu_item, load_order)
from models.people import load_customer, load_employee, load_manager
from models.promotions import SHARING_CHANNELS, next_promotion_id
from models.reports import EXPORT_DIR, EXPORT_FORMATS, next_report_id

app = Flask(__name__)
app.secret_key = "souffle-prototype"   # signs the session cookie (cart, sign-in)

STORE_ID = 1        # the website and the portal run for Soufflé Eaton Centre
CUSTOMER_ID = 1     # the customer signed in on the website: Jordan Lee (sample data)

ORDER_TYPE_LABELS = {"takeout": "Pickup", "in-store": "In-store", "online": "Online pickup"}
CANCEL_REASONS = ["Customer request", "Item unavailable", "Order entered by mistake",
                  "Payment problem", "Other"]
REPORT_TYPES = {"sales": SalesReport, "inventory": InventoryReport,
                "loyalty": CustomerLoyaltyReport}

# Order filter of the Manage Orders wireframe -> states of the order state machine
STATUS_GROUPS = {
    "pending": ("Pending", NOT_STARTED),
    "in-progress": ("In Progress", {"In progress"}),
    "ready": ("Ready", {"Ready", "Declined", "Paid"}),
    "completed": ("Completed", {"Completed"}),
    "cancelled": ("Cancelled", {"Cancelled"}),
}

# OrderHandler.estTime lives in memory only (no table), so the web app keeps each order's
# estimated ready time here between pages, as the terminal screen keeps its handler.
EST_TIMES = {}


# ---- helpers ---------------------------------------------------------------------------

def run(action, *args, **kwargs):
    """Call a class operation, capture what it prints, and turn errors into messages.
    Returns (result, printed text, error text)."""
    out = io.StringIO()
    try:
        with redirect_stdout(out):
            result = action(*args, **kwargs)
        return result, out.getvalue().strip(), None
    except (ValueError, TypeError) as err:
        return None, out.getvalue().strip(), str(err)


def show(printed="", error=None, success=None):
    """Flash the error, the screen messages the classes printed, then the success line."""
    if error:
        flash(error, "error")
    for line in (printed or "").splitlines():
        if line.strip():
            flash(line.strip(), "info")
    if success and not error:
        flash(success, "success")


def query(sql, params=()):
    with closing(get_connection()) as conn:
        return conn.execute(sql, params).fetchall()


def to_int(text, default=None):
    try:
        return int(str(text).strip())
    except (TypeError, ValueError):
        return default


def to_date(text, default=None):
    try:
        return date.fromisoformat(str(text).strip())
    except ValueError:
        return default


def find_order(orderID):
    """The order with this ID, or None (with an error message)."""
    order, _, error = run(load_order, orderID or "")
    if error:
        flash(error, "error")
    return order


def order_view(order):
    """Everything the order screens show: lines, subtotal, customer, promotion, pickup time."""
    lines = order.getOrderDetails()
    customer = load_customer(order.customerID) if order.customerID else None
    est = EST_TIMES.get(order.orderID)
    return {
        "order": order,
        "lines": lines,
        "item_count": sum(line.quantity for line in lines),
        "subtotal": round(sum(line.lineTotal for line in lines), 2),
        "customer": customer,
        "customer_name": customer.getFullName() if customer else "Walk-in customer",
        "promotion": Promotion.getPromotion(order.promotionID) if order.promotionID else None,
        "type_label": ORDER_TYPE_LABELS.get(order.orderType, order.orderType),
        "pickup": est.strftime("%I:%M %p").lstrip("0") if est else None,
        "wait": minutes_until(est),
    }


def minutes_until(est):
    if est is None:
        return None
    now = datetime.now()
    delta = datetime.combine(now.date(), est) - now
    return max(int(delta.total_seconds() // 60), 0)


def payment_status(order):
    """The payment status shown on the order screens."""
    rows = query("SELECT status FROM payments WHERE orderID = ? "
                 "ORDER BY paymentID DESC LIMIT 1", (order.orderID,))
    if rows:
        status = rows[0]["status"].lower()
        if status == "approved":
            return "Paid"
        if status == "refunded":
            return "Refunded"
        if status == "declined":
            return "Declined"
    return {"Paid": "Paid", "Completed": "Paid", "Cancelled": "Cancelled"}.get(
        order.orderStatus, "Awaiting Payment")


def approved_payment(orderID):
    rows = query("SELECT p.*, c.cardType, h.cashReceived, h.changeDue, r.receiptNumber, r.date "
                 "AS receiptDate FROM payments p "
                 "LEFT JOIN card_payments c ON c.paymentID = p.paymentID "
                 "LEFT JOIN cash_payments h ON h.paymentID = p.paymentID "
                 "LEFT JOIN receipts r ON r.paymentID = p.paymentID "
                 "WHERE p.orderID = ? AND LOWER(p.status) IN ('approved', 'refunded') "
                 "ORDER BY p.paymentID DESC", (orderID,))
    return rows[0] if rows else None


def receipt_text(orderID):
    """The receipt exactly as Receipt.printReceipt prints it (for Download Receipt)."""
    pay = approved_payment(orderID)
    if pay is None or not pay["receiptNumber"]:
        return None
    receipt = Receipt(pay["receiptNumber"], pay["amount"], date.fromisoformat(pay["receiptDate"]))
    _, printed, _ = run(receipt.printReceipt, orderID, pay["paymentID"])
    return printed


# ---- sign-in for the employee portal ------------------------------------------------------

def staff_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get("employeeID"):
            return redirect(url_for("portal_login", next=request.path))
        return view(*args, **kwargs)
    return wrapper


def manager_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        staff = current_staff()
        if staff is None:
            return redirect(url_for("portal_login", next=request.path))
        if not staff["managerID"]:
            flash("Manager access is required for that page.", "error")
            return redirect(url_for("dashboard"))
        return view(*args, **kwargs)
    return wrapper


def current_staff():
    """The signed-in employee, and whether they are also a manager."""
    employeeID = session.get("employeeID")
    if not employeeID:
        return None
    rows = query("SELECT e.employeeID, p.firstName, p.lastName, m.managerID FROM employees e "
                 "JOIN persons p ON p.personID = e.personID "
                 "LEFT JOIN managers m ON m.personID = e.personID WHERE e.employeeID = ?",
                 (employeeID,))
    if not rows:
        return None
    r = rows[0]
    return {"employeeID": r["employeeID"], "name": f"{r['firstName']} {r['lastName']}",
            "managerID": r["managerID"],
            "role": "Bakery Manager" if r["managerID"] else "Employee"}


def employee():
    return load_employee(session.get("employeeID") or 1)


def handler():
    """An OrderHandler for the signed-in employee, like manage_orders.py creates."""
    return OrderHandler(employee=employee(), storeID=STORE_ID)


@app.before_request
def make_sure_database_exists():
    if not DB_PATH.exists():
        create_database()
    migrate_database()


@app.context_processor
def page_globals():
    cart_id = session.get("cart")
    cart_count = 0
    if cart_id:
        rows = query("SELECT COALESCE(SUM(quantity), 0) FROM order_lines WHERE orderID = ?",
                     (cart_id,))
        cart_count = rows[0][0]
    return {"staff": current_staff(), "today": date.today(), "cart_count": cart_count,
            "website_customer": load_customer(CUSTOMER_ID).getFullName(),
            "type_labels": ORDER_TYPE_LABELS}


# ============================================================================================
# CUSTOMER WEBSITE
# ============================================================================================

def customer_order(orderID):
    """An order of the signed-in customer, or None."""
    order = find_order(orderID)
    if order and order.customerID != CUSTOMER_ID:
        flash(f"Order {order.orderID} is not one of your orders.", "error")
        return None
    return order


def cart_order():
    """The customer's open order (the cart), if it is still being filled in."""
    orderID = session.get("cart")
    if not orderID:
        return None
    order, _, error = run(load_order, orderID)
    if error or order.orderStatus != "In process":
        session.pop("cart", None)
        return None
    return order


@app.route("/")
def home():
    return render_template("site/home.html", menu=load_menu())


@app.route("/menu")
def site_menu():
    order = cart_order()
    return render_template("site/menu.html", menu=load_menu(),
                           cart=order_view(order) if order else None)


@app.post("/cart/add")
def cart_add():
    """Create and Submit Order from the website: startOrder("online") on the first item,
    then checkAvailability and addItem for each item."""
    order = cart_order()
    h = OrderHandler(customer=load_customer(CUSTOMER_ID), storeID=STORE_ID)
    if order is None:
        order, printed, error = run(h.startOrder, "online")
        if error:
            show(printed, error)
            return redirect(url_for("site_menu"))
        session["cart"] = order.orderID
    else:
        h.selectOrder(order.orderID)
    menuItemID = to_int(request.form.get("menuItemID"))
    quantity = to_int(request.form.get("quantity"), 0)
    item, printed, error = run(load_menu_item, menuItemID)
    if not error and not item.checkAvailability(menuItemID, quantity):
        error = f"{item.name} is not available in that quantity."
    if not error:
        _, printed, error = run(h.modifyOrder, order.orderID,
                                [("add", menuItemID, quantity,
                                  request.form.get("instructions", "").strip())])
    if not error:
        h.confirmChanges(order.orderID)
    show(printed, error, None if error else f"Added {quantity} × {item.name} to your cart.")
    return redirect(request.form.get("next") or url_for("site_menu"))


@app.post("/cart/line")
def cart_line():
    """Edit Order: change the quantity of a line or remove it (Modify Order)."""
    order = cart_order()
    if order is None:
        return redirect(url_for("site_menu"))
    h = OrderHandler(customer=load_customer(CUSTOMER_ID), storeID=STORE_ID)
    h.selectOrder(order.orderID)
    lineID = to_int(request.form.get("orderLineID"))
    quantity = to_int(request.form.get("quantity"), 0)
    change = ("remove", lineID) if quantity <= 0 else ("modify", lineID, quantity)
    _, printed, error = run(h.modifyOrder, order.orderID, [change])
    if not error:
        h.confirmChanges(order.orderID)
    show(printed, error)
    return redirect(request.form.get("next") or url_for("cart"))


@app.route("/cart")
def cart():
    """Wireframe 01 - Order Summary: order items, quantity and total."""
    order = cart_order()
    return render_template("site/order_summary.html", view=order_view(order) if order else None)


@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    """Choose payment, process online card payments, and send approved orders to the kitchen."""
    order = cart_order()
    if order is None or not order.getOrderDetails():
        flash("Your cart is empty. Add items from the menu first.", "error")
        return redirect(url_for("site_menu"))
    if request.method == "POST":
        if request.form.get("checkout_card") == "1":
            return checkout_card_payment(order)
        method = request.form.get("method")
        if method not in ("cash", "card"):
            flash("Please choose a payment method to continue.", "error")
            return redirect(url_for("checkout"))
        if method == "card":
            return render_template("pay/card_form.html", layout="site", view=order_view(order),
                                   cancel=url_for("checkout"), action=url_for("checkout"),
                                   form={})
        h = OrderHandler(customer=load_customer(CUSTOMER_ID), storeID=STORE_ID)
        h.selectOrder(order.orderID)
        _, printed, error = run(h.reviewOrder, order.orderID)
        if not error:
            _, printed, error = run(h.submitOrder, order.orderID)
        if error:
            show(printed, error)
            return redirect(url_for("checkout"))
        EST_TIMES[order.orderID] = h.estTime
        session.pop("cart", None)
        session.setdefault("methods", {})[order.orderID] = method
        session.modified = True
        return redirect(url_for("order_confirmed", orderID=order.orderID))
    return render_template("site/payment_method.html", view=order_view(order),
                           back=url_for("cart"), action=url_for("checkout"))


def checkout_card_payment(order):
    """Charge the card before submitting the order; a declined attempt leaves the cart open."""
    paid = query("SELECT 1 FROM payments WHERE orderID = ? AND LOWER(status) = 'approved' "
                 "LIMIT 1", (order.orderID,))
    customer = load_customer(order.customerID)
    if not paid:
        form = request.form
        payment, problems = card_payment_details(form)
        if problems:
            return render_template("pay/card_form.html", layout="site", view=order_view(order),
                                   cancel=url_for("checkout"), action=url_for("checkout"),
                                   form={"brand": form.get("brand", "visa")}, problems=problems)
        approved, printed, error = run(customer.payOrder, order.orderID, payment, True)
        if error:
            show(printed, error)
            return redirect(url_for("checkout"))
        if not approved:
            return render_template(
                "pay/card_form.html", layout="site", view=order_view(order),
                cancel=url_for("checkout"), action=url_for("checkout"),
                form={"brand": form.get("brand", "visa")},
                payment_error="Your card could not be authorized. Please check your details or "
                              "try another card.")

    h = OrderHandler(customer=customer, storeID=STORE_ID)
    h.selectOrder(order.orderID)
    _, printed, error = run(h.submitOrder, order.orderID)
    if error:
        show(printed, error)
        return redirect(url_for("checkout"))
    EST_TIMES[order.orderID] = h.estTime
    session.pop("cart", None)
    session.setdefault("methods", {})[order.orderID] = "card"
    session.modified = True
    return redirect(url_for("site_receipt", orderID=order.orderID))


@app.route("/my-orders/<orderID>/confirmed")
def order_confirmed(orderID):
    """Pay by Cash wireframe 03 - Order Confirmed (payment status Awaiting Payment)."""
    order = customer_order(orderID)
    if order is None:
        return redirect(url_for("my_orders"))
    method = session.get("methods", {}).get(order.orderID, "cash")
    return render_template("site/order_confirmed.html", view=order_view(order), method=method,
                           payment_status=payment_status(order))


@app.route("/my-orders")
def my_orders():
    rows = query("SELECT * FROM orders WHERE customerID = ? ORDER BY orderID DESC",
                 (CUSTOMER_ID,))
    orders = []
    for r in rows:
        order = load_order(r["orderID"])
        orders.append({"view": order_view(order), "payment": payment_status(order)})
    return render_template("site/my_orders.html", orders=orders)


@app.route("/my-orders/<orderID>/pay", methods=["GET", "POST"])
def site_pay(orderID):
    """Pay by Card wireframe 02 - Select Payment Method for an order that is Ready."""
    order = customer_order(orderID)
    if order is None:
        return redirect(url_for("my_orders"))
    if order.orderStatus not in ("Ready", "Declined"):
        flash(f"Order {order.orderID} is {order.orderStatus}: it can be paid once it is Ready.",
              "error")
        return redirect(url_for("my_orders"))
    if request.method == "POST":
        if request.form.get("method") == "card":
            return redirect(url_for("site_secure", orderID=order.orderID))
        session.setdefault("methods", {})[order.orderID] = "cash"
        session.modified = True
        return redirect(url_for("order_confirmed", orderID=order.orderID))
    return render_template("site/payment_method.html", view=order_view(order),
                           back=url_for("my_orders"), back_label="Back to My Orders",
                           action=url_for("site_pay", orderID=order.orderID))


@app.route("/my-orders/<orderID>/pay/secure")
def site_secure(orderID):
    """Pay by Card wireframe 03 - Secure Card Payment (third-party provider)."""
    order = customer_order(orderID)
    if order is None:
        return redirect(url_for("my_orders"))
    return render_template("pay/secure.html", layout="site", view=order_view(order),
                           back=url_for("site_pay", orderID=orderID),
                           next=url_for("site_card", orderID=orderID))


@app.route("/my-orders/<orderID>/pay/card", methods=["GET", "POST"])
def site_card(orderID):
    """Pay by Card wireframes 04 (Enter Payment Information) and 05 (Payment Status)."""
    order = customer_order(orderID)
    if order is None:
        return redirect(url_for("my_orders"))
    return card_payment(order, layout="site",
                        cancel=url_for("site_pay", orderID=orderID),
                        confirmation=url_for("site_receipt", orderID=orderID),
                        change_method=url_for("site_pay", orderID=orderID))


@app.route("/my-orders/<orderID>/receipt")
def site_receipt(orderID):
    """Pay by Card wireframe 06 - Payment Successful."""
    order = customer_order(orderID)
    if order is None:
        return redirect(url_for("my_orders"))
    return payment_confirmation(order, layout="site", done=url_for("home"),
                                done_label="Return to Home")


# ---- shared payment screens (website and portal use the same wireframes) ---------------------

CARD_BRANDS = {"visa": "credit", "mastercard": "credit", "debit": "debit"}


def card_payment(order, layout, cancel, confirmation, change_method):
    """Enter Payment Information, then Payment Status. The card is authorized by the
    simulated terminal (CardPayment.authorizeCard); the card details are not stored."""
    view = order_view(order)
    if request.method == "GET":
        if order.orderStatus not in ("Ready", "Declined"):
            flash(f"Order {order.orderID} is {order.orderStatus}: it can be paid once it is "
                  f"Ready.", "error")
            return redirect(cancel)
        return render_template("pay/card_form.html", layout=layout, view=view, cancel=cancel,
                               form={})
    f = request.form
    payment, problems = card_payment_details(f)
    if problems:
        return render_template("pay/card_form.html", layout=layout, view=view, cancel=cancel,
                               form={"brand": f.get("brand", "visa")}, problems=problems)
    if order.customerID:
        approved, printed, error = run(load_customer(order.customerID).payOrder,
                                       order.orderID, payment)
    else:
        approved, printed, error = run(order.confirmOrder, order.orderID, payment)
    if error:
        show(printed, error)
        return redirect(cancel)
    return render_template("pay/status.html", layout=layout, view=order_view(load_order(order.orderID)),
                           approved=approved, amount=payment.amount,
                           confirmation=confirmation, retry=request.path,
                           change_method=change_method)


def card_payment_details(form):
    """Validate submitted card fields and build the existing simulated card payment."""
    problems = []
    digits = "".join(ch for ch in form.get("cardNumber", "") if ch.isdigit())
    if not form.get("cardholder", "").strip():
        problems.append("Enter the name shown on the card.")
    if len(digits) < 13 or len(digits) > 19:
        problems.append("Enter a card number of 13 to 19 digits.")
    expiry = form.get("expiry", "").strip()
    try:
        month, year = expiry.split("/")
        if not (1 <= int(month) <= 12 and len(year.strip()) == 2):
            raise ValueError
    except ValueError:
        problems.append("Enter the expiration date as MM/YY.")
    cvv = form.get("cvv", "")
    if not (cvv.isdigit() and len(cvv) in (3, 4)):
        problems.append("Enter the 3 or 4 digit CVV.")
    if problems:
        return None, problems
    # Prototype aid: "simulate a declined card" sends a card type the terminal refuses.
    card_type = "declined-test" if form.get("simulateDecline") else \
        CARD_BRANDS.get(form.get("brand", "visa"), "credit")
    return CardPayment(0, 0.0, "card", date.today(), "", card_type, ""), []


def payment_confirmation(order, layout, done, done_label):
    pay = approved_payment(order.orderID)
    if pay is None:
        flash(f"Order {order.orderID} has no approved payment yet.", "error")
        return redirect(done)
    return render_template("pay/confirmation.html", layout=layout, view=order_view(order),
                           pay=pay, done=done, done_label=done_label,
                           download=url_for("download_receipt", orderID=order.orderID))


@app.route("/receipt/<orderID>.txt")
def download_receipt(orderID):
    text = receipt_text(orderID.upper())
    if text is None:
        flash("There is no receipt for this order.", "error")
        return redirect(url_for("home"))
    return Response(text + "\n", mimetype="text/plain", headers={
        "Content-Disposition": f"attachment; filename=receipt_{orderID.upper()}.txt"})


# ============================================================================================
# EMPLOYEE PORTAL
# ============================================================================================

@app.route("/portal/login", methods=["GET", "POST"])
def portal_login():
    """Employee.login(registerUserName, registerPassword)."""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        rows = query("SELECT employeeID FROM employees WHERE registerUserName = ?", (username,))
        if rows and load_employee(rows[0][0]).login(username, request.form.get("password", "")):
            session["employeeID"] = rows[0][0]
            return redirect(request.args.get("next") or url_for("dashboard"))
        flash("Wrong user name or password, or the account is not active.", "error")
    return render_template("portal/login.html")


@app.route("/portal/logout")
def portal_logout():
    if session.get("employeeID"):
        employee().logout()
    session.pop("employeeID", None)
    flash("You are signed out.", "success")
    return redirect(url_for("portal_login"))


@app.route("/portal/profile", methods=["GET", "POST"])
@staff_required
def portal_profile():
    staff_member = employee()
    if request.method == "POST":
        f = request.form
        try:
            staff_member.updateContactInformation(
                f.get("firstName", ""), f.get("lastName", ""),
                f.get("phone", ""), f.get("email", ""))
        except ValueError as error:
            flash(str(error), "error")
        else:
            flash("Your profile was updated.", "success")
            return redirect(url_for("portal_profile"))
    return render_template("portal/profile.html", profile=staff_member)


@app.route("/portal")
@staff_required
def dashboard():
    def count(sql, params=()):
        return query(sql, params)[0][0]
    counts = {
        "pending": count("SELECT COUNT(*) FROM orders WHERE storeID = ? AND orderStatus IN "
                         "('In process', 'Entered', 'Ordered', 'Sent')", (STORE_ID,)),
        "kitchen": count("SELECT COUNT(*) FROM orders WHERE storeID = ? AND orderStatus = "
                         "'In progress'", (STORE_ID,)),
        "to_pay": count("SELECT COUNT(*) FROM orders WHERE storeID = ? AND orderStatus IN "
                        "('Ready', 'Declined')", (STORE_ID,)),
    }
    if current_staff()["managerID"]:
        counts["low"] = count("SELECT COUNT(*) FROM inventory_items i JOIN inventories v ON "
                              "v.inventoryID = i.inventoryID WHERE v.storeID = ? AND "
                              "i.quantity < i.minimumQuantity", (STORE_ID,))
    return render_template("portal/dashboard.html", counts=counts)


@app.post("/portal/reset")
@manager_required
def reset():
    create_database()
    EST_TIMES.clear()
    session.pop("cart", None)
    flash("Sample data loaded again.", "success")
    return redirect(url_for("dashboard"))


# ---- Manage Orders: select order ------------------------------------------------------------

@app.route("/portal/orders")
@staff_required
def orders():
    """Manage Orders - Select Order: search by order ID, filter by status, View Details."""
    search = request.args.get("q", "").strip()
    if search:
        order, _, error = run(load_order, search)
        if error:
            flash(f"No order {search.upper()} was found. Check the order ID.", "error")
        else:
            return redirect(url_for("track_order", orderID=order.orderID))
    group = request.args.get("status", "all")
    rows = query("SELECT o.*, p.firstName || ' ' || p.lastName AS customerName FROM orders o "
                 "LEFT JOIN customers c ON c.customerID = o.customerID "
                 "LEFT JOIN persons p ON p.personID = c.personID WHERE o.storeID = ? "
                 "ORDER BY o.orderID DESC", (STORE_ID,))
    if group in STATUS_GROUPS:
        rows = [r for r in rows if r["orderStatus"] in STATUS_GROUPS[group][1]]
    else:
        group = "all"
        rows = [r for r in rows if r["orderStatus"] != "Cancelled"]
    return render_template("portal/orders.html", orders=rows, group=group, groups=STATUS_GROUPS)


# ---- Story A: Create New Order ----------------------------------------------------------------

@app.route("/portal/orders/new")
@staff_required
def create_order_start():
    """Wireframe 01 - Create New Order, before the first item is added."""
    return render_template("portal/create_order.html", view=None, menu=load_menu(),
                           customers=customer_list())


def customer_list():
    return query("SELECT c.customerID, p.firstName || ' ' || p.lastName AS name FROM customers c "
                 "JOIN persons p ON p.personID = c.personID ORDER BY c.customerID")


@app.route("/portal/orders/<orderID>/create")
@staff_required
def create_order(orderID):
    order = find_order(orderID)
    if order is None:
        return redirect(url_for("orders"))
    if order.orderStatus not in NOT_STARTED:
        return redirect(url_for("track_order", orderID=order.orderID))
    return render_template("portal/create_order.html", view=order_view(order), menu=load_menu(),
                           customers=customer_list())


@app.post("/portal/orders/add")
@staff_required
def create_order_add():
    """Add to Order: startOrder(orderType) on the first item, then checkAvailability and
    addItem (the loop of the Create New Order sequence diagram)."""
    f = request.form
    h = handler()
    orderID = f.get("orderID")
    if orderID:
        order, printed, error = run(h.selectOrder, orderID)
    else:
        customerID = to_int(f.get("customerID"))
        h.customer = load_customer(customerID) if customerID else None
        order, printed, error = run(h.startOrder, f.get("orderType", "takeout"))
    if error:
        show(printed, error)
        return redirect(url_for("create_order_start"))
    menuItemID = to_int(f.get("menuItemID"))
    quantity = to_int(f.get(f"qty_{menuItemID}"), 0)
    note = f.get(f"note_{menuItemID}", "").strip()
    item, printed, error = run(load_menu_item, menuItemID)
    if not error and not item.checkAvailability(menuItemID, quantity):
        error = f"{item.name} is not available in that quantity."
    if not error:
        _, printed, error = run(h.modifyOrder, order.orderID,
                                [("add", menuItemID, quantity, note)])
    if not error:
        h.confirmChanges(order.orderID)
    show(printed, error)
    return redirect(url_for("create_order", orderID=order.orderID))


@app.post("/portal/orders/<orderID>/remove-line")
@staff_required
def create_order_remove(orderID):
    h = handler()
    _, printed, error = run(h.selectOrder, orderID)
    if not error:
        _, printed, error = run(h.modifyOrder, orderID.upper(),
                                [("remove", to_int(request.form.get("orderLineID")))])
    if not error:
        h.confirmChanges(orderID.upper())
    show(printed, error)
    return redirect(url_for("create_order", orderID=orderID))


@app.post("/portal/orders/<orderID>/discard")
@staff_required
def create_order_cancel(orderID):
    """Alternative wireflow B - Cancel Order Creation: no order is submitted."""
    h = handler()
    _, printed, error = run(h.enterReason, "Order creation cancelled")
    if not error:
        _, printed, error = run(h.cancelOrder, orderID)
    show(printed, error, "Order creation cancelled. No order was submitted.")
    return redirect(url_for("orders"))


@app.post("/portal/orders/<orderID>/continue")
@staff_required
def create_order_continue(orderID):
    """Continue: reviewOrder(orderID) -> order summary and total (status Entered)."""
    h = handler()
    order, printed, error = run(h.selectOrder, orderID)
    if not error and not order.getOrderDetails():
        error = "Add at least one item to continue."
    if not error:
        _, printed, error = run(h.reviewOrder, order.orderID)
    if error:
        show(printed, error)
        return redirect(url_for("create_order", orderID=orderID))
    return redirect(url_for("review_order", orderID=order.orderID))


@app.route("/portal/orders/<orderID>/review")
@staff_required
def review_order(orderID):
    """Wireframe 02 - Review Order."""
    order = find_order(orderID)
    if order is None:
        return redirect(url_for("orders"))
    promotions = [p for p in (Promotion.getPromotion(r[0]) for r in
                              query("SELECT promotionID FROM promotions ORDER BY promotionID"))
                  if p.isValid(p.promotionID)]
    return render_template("portal/review_order.html", view=order_view(order),
                           promotions=promotions)


@app.post("/portal/orders/<orderID>/promotion")
@staff_required
def apply_promotion(orderID):
    """applyPromotion(promotionID) -> Order.calculateDiscount (Manage Promotions diagram)."""
    h = handler()
    _, printed, error = run(h.selectOrder, orderID)
    if not error:
        discount, printed, error = run(h.applyPromotion, to_int(request.form.get("promotionID"), 0))
        if not error and not discount:
            error = "That promotion is not valid right now: no discount."
        show(printed, error, None if error else f"Promotion applied: ${discount:.2f} off.")
    else:
        show(printed, error)
    return redirect(url_for("review_order", orderID=orderID))


@app.post("/portal/orders/<orderID>/submit")
@staff_required
def submit_order(orderID):
    """Submit Order: submitOrder -> sendToKitchen returns the estimated pickup time."""
    h = handler()
    order, printed, error = run(h.selectOrder, orderID)
    if not error:
        _, printed, error = run(h.submitOrder, order.orderID)
    if error:
        show(printed, error)
        return redirect(url_for("review_order", orderID=orderID))
    EST_TIMES[order.orderID] = h.estTime
    return redirect(url_for("order_submitted", orderID=order.orderID))


@app.route("/portal/orders/<orderID>/submitted")
@staff_required
def order_submitted(orderID):
    """Wireframe 03 - Order Submitted Successfully."""
    order = find_order(orderID)
    if order is None:
        return redirect(url_for("orders"))
    return render_template("portal/order_submitted.html", view=order_view(order))


# ---- Story B: Modify Order --------------------------------------------------------------------

@app.route("/portal/orders/<orderID>/modify", methods=["GET", "POST"])
@staff_required
def modify_order(orderID):
    """Wireframe 02 - Modify Order: selectOrder, then modifyOrder(changes) and
    confirmChanges when the employee clicks Save Changes."""
    h = handler()
    order, printed, error = run(h.selectOrder, orderID)
    if error:
        show(printed, error)
        return redirect(url_for("orders"))
    if order.orderStatus not in NOT_STARTED:
        flash(f"Order {order.orderID} is {order.orderStatus}: items can only change before the "
              f"kitchen starts preparing it.", "error")
        return redirect(url_for("track_order", orderID=order.orderID))
    if request.method == "POST":
        f = request.form
        changes = []
        for line in order.getOrderDetails():
            qty = to_int(f.get(f"qty_{line.orderLineID}"), line.quantity)
            if f.get(f"remove_{line.orderLineID}") or qty <= 0:
                changes.append(("remove", line.orderLineID))
            elif qty != line.quantity:
                changes.append(("modify", line.orderLineID, qty))
        for menuItemID, qty, note in zip(f.getlist("add_item"), f.getlist("add_qty"),
                                         f.getlist("add_note")):
            if to_int(menuItemID) and to_int(qty, 0) > 0:
                changes.append(("add", to_int(menuItemID), to_int(qty), note.strip()))
        if not changes:
            flash("Nothing was changed.", "info")
            return redirect(url_for("modify_order", orderID=order.orderID))
        _, printed, error = run(h.modifyOrder, order.orderID, changes)
        if error:
            show(printed, f"Not saved: {error}")
            return redirect(url_for("modify_order", orderID=order.orderID))
        h.confirmChanges(order.orderID)
        return redirect(url_for("order_updated", orderID=order.orderID))
    return render_template("portal/modify_order.html", view=order_view(order), menu=load_menu())


@app.route("/portal/orders/<orderID>/updated")
@staff_required
def order_updated(orderID):
    """Wireframe 03 - Order Updated."""
    order = find_order(orderID)
    if order is None:
        return redirect(url_for("orders"))
    return render_template("portal/order_updated.html", view=order_view(order))


# ---- Story C: Cancel Order --------------------------------------------------------------------

@app.route("/portal/orders/<orderID>/cancel", methods=["GET", "POST"])
@staff_required
def cancel_order(orderID):
    """Wireframe 02 - Cancel Order: enterReason, then cancelOrder. An order the kitchen has
    not started is cancelled right away; otherwise the manager must approve."""
    order = find_order(orderID)
    if order is None:
        return redirect(url_for("orders"))
    if order.orderStatus in FINAL_STATES:
        flash(f"Order {order.orderID} is {order.orderStatus}: it cannot be cancelled.", "error")
        return redirect(url_for("track_order", orderID=order.orderID))
    if request.method == "POST":
        reason = request.form.get("reason", "").strip()
        details = request.form.get("details", "").strip()
        full_reason = f"{reason}: {details}" if reason and details else reason
        h = handler()
        _, printed, error = run(h.enterReason, full_reason)
        if error:
            show(printed, "Select a cancellation reason to continue.")
            return redirect(url_for("cancel_order", orderID=order.orderID))
        cancelled, printed, error = run(h.cancelOrder, order.orderID)
        if error:
            show(printed, error)
            return redirect(url_for("track_order", orderID=order.orderID))
        if cancelled:
            show(printed)
            return redirect(url_for("order_cancelled", orderID=order.orderID))
        return render_template("portal/cancel_approval.html", view=order_view(order),
                               reason=full_reason, done=False)
    return render_template("portal/cancel_order.html", view=order_view(order),
                           reasons=CANCEL_REASONS,
                           needs_approval=order.orderStatus in NEEDS_APPROVAL)


@app.post("/portal/orders/<orderID>/approve")
@staff_required
def approve_cancellation(orderID):
    """Wireframe 03 - Cancellation Approval: approveCancellation(orderID, managerID,
    accountPassword) (Milestone 5 method specification 02)."""
    order = find_order(orderID)
    if order is None:
        return redirect(url_for("orders"))
    reason = request.form.get("reason", "")
    if request.form.get("decision") == "reject":
        flash(f"Cancellation rejected. Order {order.orderID} is unchanged.", "info")
        return redirect(url_for("track_order", orderID=order.orderID))
    h = handler()
    was_paid = order.orderStatus == "Paid"
    h.enterReason(reason or "Cancelled with manager approval")
    approved, printed, error = run(h.approveCancellation, order.orderID,
                                   to_int(request.form.get("managerID"), -1),
                                   request.form.get("password", ""))
    if error or not approved:
        return render_template("portal/cancel_approval.html", view=order_view(order),
                               reason=reason, done=False,
                               problem=error or "Not approved: wrong manager ID or password. "
                                                "The order is unchanged.")
    show(printed)
    return render_template("portal/cancel_approval.html", view=order_view(load_order(orderID)),
                           reason=reason, done=True, refunded=was_paid)


@app.route("/portal/orders/<orderID>/cancelled")
@staff_required
def order_cancelled(orderID):
    order = find_order(orderID)
    if order is None:
        return redirect(url_for("orders"))
    record = query("SELECT * FROM cancellation_records WHERE orderID = ?", (order.orderID,))
    return render_template("portal/cancel_approval.html", view=order_view(order),
                           reason=record[0]["reason"] if record else "", done=True,
                           no_approval=True)


# ---- Story D: Track and Complete Order --------------------------------------------------------

@app.route("/portal/kitchen")
@staff_required
def kitchen():
    """Wireframe 01 - Kitchen Orders: incoming orders and their items."""
    def rows(states):
        marks = ",".join("?" * len(states))
        out = []
        for r in query(f"SELECT orderID FROM orders WHERE storeID = ? AND orderStatus IN "
                       f"({marks}) ORDER BY orderID", (STORE_ID, *states)):
            out.append(order_view(load_order(r["orderID"])))
        return out
    incoming = rows(("Ordered", "Sent"))
    preparing = rows(("In progress",))
    selected = request.args.get("selected") or (incoming[0]["order"].orderID if incoming else None)
    return render_template("portal/kitchen.html", incoming=incoming, preparing=preparing,
                           selected=selected)


@app.route("/portal/orders/<orderID>")
@staff_required
def track_order(orderID):
    """Wireframe 02 - Track Order: current status, estimated waiting time, details."""
    order = find_order(orderID)
    if order is None:
        return redirect(url_for("orders"))
    return render_template("portal/track_order.html", view=order_view(order),
                           payment=payment_status(order),
                           can_modify=order.orderStatus in NOT_STARTED,
                           can_cancel=order.orderStatus not in FINAL_STATES)


@app.post("/portal/orders/<orderID>/status")
@staff_required
def order_status(orderID):
    """startPreparation, requestRemake, markReady, markOrderComplete."""
    h = handler()
    order, printed, error = run(h.selectOrder, orderID)
    action = request.form.get("action")
    if not error:
        h.estTime = EST_TIMES.get(order.orderID)
        if action == "start":
            _, printed, error = run(h.startPreparation, order.orderID)
        elif action == "remake":
            _, printed, error = run(h.requestRemake, order.orderID,
                                    to_int(request.form.get("orderLineID")))
            if not error:
                EST_TIMES[order.orderID] = h.estTime
        elif action == "ready":
            _, printed, error = run(h.markReady, order.orderID)
        elif action == "complete":
            _, printed, error = run(employee().markOrderComplete, order.orderID)
            if not error:
                show(printed)
                return redirect(url_for("order_completed", orderID=order.orderID))
    show(printed, error)
    return redirect(request.form.get("next") or url_for("track_order", orderID=orderID))


@app.route("/portal/orders/<orderID>/completed")
@staff_required
def order_completed(orderID):
    """Wireframe 03 - Order Completed."""
    order = find_order(orderID)
    if order is None:
        return redirect(url_for("orders"))
    return render_template("portal/order_completed.html", view=order_view(order),
                           payment=payment_status(order))


# ---- Process Payments at the counter (Story 6.2.2 B, employee's side) ---------------------------

@app.route("/portal/orders/<orderID>/payment", methods=["GET", "POST"])
@staff_required
def portal_pay(orderID):
    """Select the payment method for an order that is Ready."""
    order = find_order(orderID)
    if order is None:
        return redirect(url_for("orders"))
    if order.orderStatus not in ("Ready", "Declined"):
        flash(f"Order {order.orderID} is {order.orderStatus}: it can be paid once it is Ready.",
              "error")
        return redirect(url_for("track_order", orderID=order.orderID))
    if request.method == "POST":
        if request.form.get("method") == "card":
            return redirect(url_for("portal_card", orderID=order.orderID))
        return redirect(url_for("cash_payment", orderID=order.orderID))
    return render_template("site/payment_method.html", layout="portal", view=order_view(order),
                           back=url_for("track_order", orderID=order.orderID),
                           back_label="Back to Order",
                           action=url_for("portal_pay", orderID=order.orderID), method="cash")


@app.route("/portal/orders/<orderID>/payment/cash", methods=["GET", "POST"])
@staff_required
def cash_payment(orderID):
    """Wireframe 03 - Process Cash Payment, then 04 - Cash Payment Status. Validate Payment
    compares the cash with the total (CashPayment.calculateChange); nothing is recorded
    until the employee confirms."""
    order = find_order(orderID)
    if order is None:
        return redirect(url_for("orders"))
    view = order_view(order)
    total = order.calculateTotal(order.orderID)
    if order.orderStatus not in ("Ready", "Declined"):
        flash(f"Order {order.orderID} is {order.orderStatus}: it can be paid once it is Ready.",
              "error")
        return redirect(url_for("track_order", orderID=order.orderID))
    if request.method == "POST":
        try:
            received = round(float(request.form.get("cashReceived", "")), 2)
        except ValueError:
            return render_template("portal/cash_entry.html", view=view, total=total,
                                   received=request.form.get("cashReceived", ""),
                                   problem="Enter the cash received, for example 30.00.")
        if received < total:
            return render_template("portal/cash_entry.html", view=view, total=total,
                                   received=f"{received:.2f}",
                                   problem=f"Insufficient cash. Enter at least ${total:.2f}.")
        change = CashPayment(0, total, "cash", date.today(), "", received, 0.0)\
            .calculateChange(total, received)
        return render_template("portal/cash_status.html", view=view, total=total,
                               received=received, change=change)
    return render_template("portal/cash_entry.html", view=view, total=total, received="")


@app.post("/portal/orders/<orderID>/payment/cash/confirm")
@staff_required
def cash_confirm(orderID):
    """Confirm Payment: Customer.payOrder(orderID, CashPayment) -> confirmOrder ->
    processPayment -> generateReceipt, printReceipt, recordSale (method specification 01)."""
    order = find_order(orderID)
    if order is None:
        return redirect(url_for("orders"))
    received = float(request.form.get("cashReceived", "0") or 0)
    payment = CashPayment(0, 0.0, "cash", date.today(), "", received, 0.0)
    if order.customerID:
        approved, printed, error = run(load_customer(order.customerID).payOrder,
                                       order.orderID, payment)
    else:
        approved, printed, error = run(order.confirmOrder, order.orderID, payment)
    if error or not approved:
        show(printed, error or "Insufficient cash: the payment was declined. Enter the amount "
                               "again.")
        return redirect(url_for("cash_payment", orderID=orderID))
    return redirect(url_for("portal_receipt", orderID=order.orderID))


@app.route("/portal/orders/<orderID>/payment/card", methods=["GET", "POST"])
@staff_required
def portal_card(orderID):
    order = find_order(orderID)
    if order is None:
        return redirect(url_for("orders"))
    return card_payment(order, layout="portal",
                        cancel=url_for("portal_pay", orderID=orderID),
                        confirmation=url_for("portal_receipt", orderID=orderID),
                        change_method=url_for("portal_pay", orderID=orderID))


@app.route("/portal/orders/<orderID>/receipt")
@staff_required
def portal_receipt(orderID):
    """Wireframe 05 - Payment Successful (employee's side)."""
    order = find_order(orderID)
    if order is None:
        return redirect(url_for("orders"))
    return payment_confirmation(order, layout="portal", done=url_for("orders"),
                                done_label="Return to Orders")


# ---- Menu --------------------------------------------------------------------------------------

@app.route("/portal/menu")
@staff_required
def portal_menu():
    return render_template("portal/menu.html", menu=load_menu())


# ---- Manage Inventory (Story 6.1) ---------------------------------------------------------------

def stores():
    return query("SELECT * FROM stores ORDER BY storeID")


@app.route("/portal/inventory")
@manager_required
def inventory():
    """Wireframe 1 - Inventory List: InventoryUI.viewInventory() with the search keyword
    (item ID or name) and the below-minimum filter."""
    storeID = to_int(request.args.get("store"), STORE_ID)
    screen = InventoryUI(inventory=load_inventory(storeID))
    search = request.args.get("q", "").strip()
    screen.filterCategory = LOW_STOCK_FILTER if request.args.get("low") == "1" else ""
    if search.isdigit():                      # search by item ID
        items, _, _ = run(screen.viewInventory)
        items = [i for i in items or [] if i.itemID == int(search)]
    else:                                     # search by item name
        screen.searchKeyword = search
        items, _, _ = run(screen.viewInventory)
    return render_template("portal/inventory.html", stores=stores(), storeID=storeID,
                           screen=screen, items=items or [], search=search)


@app.route("/portal/inventory/<int:storeID>/<int:itemID>", methods=["GET", "POST"])
@manager_required
def inventory_update(storeID, itemID):
    """Wireframe 2 - Update Inventory Quantity: InventoryUI.updateQuantity(itemID, newQuantity)
    -> Inventory.updateInventoryRecord -> InventoryItem.validateQuantity -> InventoryDatabase."""
    screen = InventoryUI(inventory=load_inventory(storeID))
    item, _, error = run(screen.inventory._find_item, itemID)
    if error:
        flash(error, "error")
        return redirect(url_for("inventory", store=storeID))
    if request.method == "POST":
        text = request.form.get("newQuantity", "").strip()
        newQuantity = to_int(text, text)      # not a whole number: validateQuantity refuses it
        oldQuantity = item.quantity
        ok, printed, error = run(screen.updateQuantity, itemID, newQuantity)
        if ok:
            return redirect(url_for("inventory_updated", storeID=storeID, itemID=itemID,
                                    old=oldQuantity))
        return render_template("portal/inventory_update.html", item=item, storeID=storeID,
                               store=store_name(storeID), value=text,
                               problem="Enter a valid quantity: a whole number, 0 or more. "
                                       "Nothing was saved.")
    return render_template("portal/inventory_update.html", item=item, storeID=storeID,
                           store=store_name(storeID), value="")


def store_name(storeID):
    rows = query("SELECT storeName FROM stores WHERE storeID = ?", (storeID,))
    return rows[0][0] if rows else ""


@app.route("/portal/inventory/<int:storeID>/<int:itemID>/updated")
@manager_required
def inventory_updated(storeID, itemID):
    """Wireframe 3 - Inventory Updated: the updated quantity and the confirmation."""
    screen = InventoryUI(inventory=load_inventory(storeID))
    item, _, error = run(screen.inventory._find_item, itemID)
    if error:
        flash(error, "error")
        return redirect(url_for("inventory", store=storeID))
    return render_template("portal/inventory_updated.html", item=item, storeID=storeID,
                           store=store_name(storeID), old=request.args.get("old", ""),
                           lastUpdated=screen.inventory.lastUpdated)


# ---- Manage Employee Accounts (UC 03, no Milestone 6 wireframe) ----------------------------------

@app.route("/portal/accounts")
@manager_required
def accounts():
    rows = query("SELECT a.*, p.firstName, p.lastName FROM employee_accounts a "
                 "JOIN employees e ON e.employeeID = a.employeeID "
                 "JOIN persons p ON p.personID = e.personID ORDER BY a.accountID")
    staff_without = query("SELECT e.employeeID, p.firstName, p.lastName FROM employees e "
                          "JOIN persons p ON p.personID = e.personID WHERE e.employeeID NOT IN "
                          "(SELECT employeeID FROM employee_accounts) ORDER BY e.employeeID")
    return render_template("portal/accounts.html", accounts=rows, without=staff_without)


def manager():
    staff = current_staff()
    return load_manager((staff and staff["managerID"]) or 1)


@app.post("/portal/accounts/new")
@manager_required
def account_new():
    f = request.form
    account, printed, error = run(manager().createAccount, to_int(f.get("employeeID"), -1),
                                  f.get("employeeEmail", ""), f.get("voidCheque", ""),
                                  f.get("accountPassword", ""))
    show(printed, error and f"Not created. {error}",
         account and f"Account {account.accountID} created and active.")
    return redirect(url_for("accounts"))


@app.post("/portal/accounts/<int:accountID>/edit")
@manager_required
def account_edit(accountID):
    f = request.form
    ok, printed, error = run(manager().modifyAccount, accountID,
                             employeeEmail=f.get("employeeEmail") or None,
                             accountPassword=f.get("accountPassword") or None,
                             accountStatus=f.get("accountStatus") or None)
    if not error and not ok:
        error = "Not updated: the new information is not valid."
    show(printed, error, "Account updated.")
    return redirect(url_for("accounts"))


@app.post("/portal/accounts/<int:accountID>/delete")
@manager_required
def account_delete(accountID):
    ok, printed, error = run(manager().deleteAccount, accountID)
    show(printed, error or (None if ok else "There is no such account."),
         f"Account {accountID} deleted.")
    return redirect(url_for("accounts"))


# ---- Manage Promotions (UC 05, no Milestone 6 wireframe) ------------------------------------------

@app.route("/portal/promotions")
@manager_required
def promotions():
    rows = []
    for (promotionID,) in query("SELECT promotionID FROM promotions ORDER BY promotionID"):
        p = Promotion.getPromotion(promotionID)
        rows.append({"p": p, "valid": p.isValid(promotionID),
                     "used": p.trackEngagement(promotionID)})
    return render_template("portal/promotions.html", promotions=rows, channels=SHARING_CHANNELS)


@app.post("/portal/promotions/new")
@manager_required
def promotion_new():
    f = request.form
    today = date.today()
    promotion = Promotion(0, "", "", 0, today, today, today, "", "",
                          managerID=manager().managerID)
    _, printed, error = run(promotion.createPromotion, next_promotion_id(), f.get("title", ""),
                            f.get("discountType", ""), to_int(f.get("discountValue"), -1),
                            to_date(f.get("startDate"), today), to_date(f.get("endDate"), today))
    if not error:
        if f.get("action") == "share":
            _, printed, error = run(promotion.sharePromotion, promotion.promotionID,
                                    f.get("sharingChannel", ""))
            success = f"Promotion {promotion.promotionID} shared with every customer."
        else:
            _, printed, error = run(promotion.saveDraft, promotion.promotionID)
            success = f"Promotion {promotion.promotionID} saved as a draft."
        show(printed, error, success)
    else:
        show(printed, error)
    return redirect(url_for("promotions"))


@app.post("/portal/promotions/<int:promotionID>/edit")
@manager_required
def promotion_edit(promotionID):
    f = request.form
    promotion = Promotion.getPromotion(promotionID)
    if promotion is None:
        show("", "There is no such promotion.")
        return redirect(url_for("promotions"))
    _, printed, error = run(promotion.editDraft, promotionID, title=f.get("title") or None,
                            discountValue=to_int(f.get("discountValue")),
                            discountType=f.get("discountType") or None,
                            startDate=to_date(f.get("startDate")),
                            endDate=to_date(f.get("endDate")))
    show(printed, error, f"Draft {promotionID} saved.")
    return redirect(url_for("promotions"))


@app.post("/portal/promotions/<int:promotionID>/share")
@manager_required
def promotion_share(promotionID):
    promotion = Promotion.getPromotion(promotionID)
    if promotion is None:
        show("", "There is no such promotion.")
        return redirect(url_for("promotions"))
    _, printed, error = run(promotion.sharePromotion, promotionID,
                            request.form.get("sharingChannel", ""))
    show(printed, error, f"Promotion {promotionID} shared with every customer.")
    return redirect(url_for("promotions"))


# ---- Create Reports (UC 06, no Milestone 6 wireframe) ---------------------------------------------

@app.route("/portal/reports", methods=["GET", "POST"])
@manager_required
def reports():
    form = request.form if request.method == "POST" else {}
    result = None
    if request.method == "POST":
        kind = form.get("type", "sales")
        storeID = to_int(form.get("storeID"), STORE_ID)
        start, end = to_date(form.get("startDate")), to_date(form.get("endDate"))
        if start is None or end is None:
            show("", "Please choose a start and an end date.")
        elif end < start:
            show("", "The end date must be on or after the start date.")
        else:
            report = REPORT_TYPES.get(kind, SalesReport)(
                next_report_id(), start, end, date.today(), "CSV",
                managerID=manager().managerID, storeID=storeID)
            found, printed, error = run(report.retrieveRecords, start, end, storeID)
            if error or not found:
                show("", error or "No records found for this store and period.")
            else:
                header, rows = report._details()
                result = {"text": "\n".join(report.content), "summary": report._summary(),
                          "header": header, "rows": rows, "file": None,
                          "title": f"{report.REPORT_NAME} report #{report.reportID}",
                          "store": report.storeName}
                if form.get("save"):
                    flash(report.save(report.reportID), "success")
                if form.get("export"):
                    message, _, error = run(report.export, report.reportID,
                                            form.get("format", "CSV"))
                    show("", error, message)
                    if not error:
                        result["file"] = message.rsplit("/", 1)[-1]
    return render_template("portal/reports.html", stores=stores(), form=form, result=result,
                           formats=EXPORT_FORMATS, default_start="2026-10-01")


@app.route("/portal/exports/<path:filename>")
@manager_required
def download_export(filename):
    return send_from_directory(EXPORT_DIR, filename, as_attachment=True)


if __name__ == "__main__":
    print("Soufflé web app running.")
    print("  Customer website: http://127.0.0.1:5000")
    print("  Employee portal:  http://127.0.0.1:5000/portal  (sam.t / changeme, alex.m / manager123)")
    print("Press Ctrl+C to stop.")
    app.run(debug=True)
