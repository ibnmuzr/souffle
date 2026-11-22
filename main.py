"""Soufflé Management System: prototype demo.

Builds the database, loads rows into the class-diagram classes to show that the
classes, their attributes and the database line up, then runs the Create Reports
use cases built so far the way their sequence diagrams describe them:
Manage Orders (UC 01), Process Payments (UC 02), Manage Employee Accounts (UC 03),
Manage Inventory (UC 04), Manage Promotions (UC 05) and Create Reports (UC 06).

Run from the project folder:  python3 main.py
Interactive screens: python3 manage_orders.py, python3 manage_inventory.py and
python3 create_reports.py
"""
from datetime import date, timedelta

from database.connection import get_connection
from database.setup_db import create_database
from models import (
    Customer, Manager, Person, Store, InventoryItem, InventoryUI, MenuItem, OrderHandler,
    Promotion, CardPayment, CashPayment, SalesReport, InventoryReport, CustomerLoyaltyReport,
)
from models.accounts import load_account
from models.orders import load_order
from models.people import load_customer, load_employee
from models.promotions import next_promotion_id
from models.inventory import load_inventory
from models.orders import order_from_row
from models.reports import next_report_id

TABLES = [
    "persons", "customers", "employees", "managers", "employee_accounts",
    "stores", "inventories", "inventory_items",
    "menu_items", "orders", "order_lines", "sales_records", "cancellation_records",
    "payments", "card_payments", "cash_payments", "receipts",
    "promotions", "customer_promotions",
    "reports", "sales_reports", "inventory_reports", "customer_loyalty_reports",
    "sales_report_orders", "inventory_report_items", "loyalty_report_customers",
]


def d(text):
    """Convert a YYYY-MM-DD string from the database into a date."""
    return date.fromisoformat(text)


def main():
    create_database()
    conn = get_connection()

    print("=== Soufflé Management System: prototype demo ===\n")
    print("Database tables (rows):")
    for table in TABLES:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table:<28}{count}")

    print("\nStores:")
    for r in conn.execute("SELECT * FROM stores"):
        store = Store(r["storeID"], r["storeName"], r["address"])
        print(f"  {store.storeName}, {store.address}")

    print("\nMenu:")
    for r in conn.execute("SELECT * FROM menu_items"):
        item = MenuItem(r["menuItemID"], r["name"], r["description"], r["category"],
                        r["price"], bool(r["isAvailable"]))
        status = "available" if item.checkAvailability(item.menuItemID, 1) else "unavailable"
        print(f"  {item.name:<34}${item.price:>6.2f}  ({status})")

    print("\nEaton Centre stock below minimum (InventoryItem.isBelowMinimum):")
    for r in conn.execute("SELECT * FROM inventory_items WHERE inventoryID = 1"):
        item = InventoryItem(r["itemID"], r["itemName"], r["quantity"], r["minimumQuantity"])
        if item.isBelowMinimum(item.itemID):
            print(f"  {item.itemName}: {item.quantity} left, minimum {item.minimumQuantity}")

    r = conn.execute(
        "SELECT p.*, m.managerID FROM managers m JOIN persons p ON p.personID = m.personID"
    ).fetchone()
    manager = Manager(r["personID"], r["firstName"], r["lastName"], r["phone"], r["email"],
                      r["managerID"])
    print(f"\nManager (Person.getFullName): {manager.getFullName()}")

    r = conn.execute(
        "SELECT p.*, c.customerID FROM customers c JOIN persons p ON p.personID = c.personID"
    ).fetchone()
    customer = Customer(r["personID"], r["firstName"], r["lastName"], r["phone"], r["email"],
                        r["customerID"])
    print(f"Customer: {customer.getFullName()}")

    r = conn.execute(
        "SELECT * FROM payments p JOIN cash_payments c ON c.paymentID = p.paymentID"
    ).fetchone()
    cash = CashPayment(r["paymentID"], r["amount"], r["method"], d(r["paymentDate"]),
                       r["status"], r["cashReceived"], 0.0)
    print(f"\nCash payment of ${cash.amount:.2f} with ${cash.cashReceived:.2f} received: "
          f"change due ${cash.calculateChange(cash.amount, cash.cashReceived):.2f}")

    print("\nPromotions (lifeCycleState, /duration):")
    for r in conn.execute("SELECT * FROM promotions"):
        promo = Promotion(r["promotionID"], r["title"], r["discountType"], r["discountValue"],
                          d(r["creationDate"]), d(r["startDate"]), d(r["endDate"]),
                          r["sharingChannel"] or "", r["lifeCycleState"])
        print(f"  {promo.title:<22}{promo.lifeCycleState:<9}runs {promo.duration} days")

    order = order_from_row(conn.execute("SELECT * FROM orders WHERE orderID = 'ORD-0002'").fetchone())
    discount = order.calculateDiscount(order.orderID, order.orderTotal, 3)
    print(f"Order.calculateDiscount: 'Fall Latte Days' on {order.orderID} "
          f"(${order.orderTotal:.2f}) = ${discount:.2f} off")
    print(f"Order.calculateDiscount with the draft 'Holiday Bundle' (not valid): "
          f"${order.calculateDiscount(order.orderID, order.orderTotal, 2):.2f} off")

    r = conn.execute(
        "SELECT * FROM reports r JOIN sales_reports s ON s.reportID = r.reportID"
    ).fetchone()
    sales = SalesReport(r["reportID"], d(r["startDate"]), d(r["endDate"]), d(r["createdDate"]),
                        r["format"], managerID=r["managerID"], storeID=r["storeID"],
                        totalRevenue=r["totalRevenue"], unitSold=r["unitSold"],
                        averageOrderTotal=r["averageOrderTotal"])
    print(f"\nSaved sales report {sales.startDate} to {sales.endDate}: revenue "
          f"${sales.totalRevenue:.2f}, {sales.unitSold} units, average order "
          f"${sales.averageOrderTotal:.2f}")

    r = conn.execute(
        "SELECT * FROM reports r JOIN inventory_reports i ON i.reportID = r.reportID"
    ).fetchone()
    inv = InventoryReport(r["reportID"], d(r["startDate"]), d(r["endDate"]), d(r["createdDate"]),
                          r["format"], managerID=r["managerID"], storeID=r["storeID"],
                          itemsBelowMinimum=r["itemsBelowMinimum"])
    print(f"Saved inventory report: {inv.itemsBelowMinimum} items below minimum")

    print("\nAbstract classes cannot be created directly:")
    try:
        Person(99, "Test", "Person", "", "")
    except TypeError as err:
        print(f"  {err}")

    conn.close()
    manage_orders_demo()
    process_payments_demo()
    manage_accounts_demo(manager)
    manage_inventory_demo(manager)
    manage_promotions_demo(manager)
    create_reports_demo(manager)
    print("\nDone.")


def show_order(order):
    for line in order.getOrderDetails():
        print(f"    {line.quantity} x {line.menuItem.name:<34}${line.lineTotal:>6.2f}")
    if order.discountAmount:
        print(f"    promotion discount               -${order.discountAmount:.2f}")
    print(f"    Total ${order.orderTotal:.2f} ({order.orderStatus})")


def manage_orders_demo():
    """Manage Orders (UC 01): Sam creates, modifies, tracks, cancels and completes orders."""
    print("\n=== Manage Orders (UC 01) ===")
    employee = load_employee(1)
    handler = OrderHandler(customer=load_customer(2), employee=employee, storeID=1)
    print(f"Employee: {employee.getFullName()}")

    print("\nCreate and Submit Order: startOrder, addItem (loop), applyPromotion, reviewOrder, "
          "submitOrder")
    order = handler.startOrder("takeout")
    order.addItem(2, 1, "Strawberry topping")
    order.addItem(6, 2)
    handler.applyPromotion(3)
    handler.reviewOrder(order.orderID)
    show_order(order)
    handler.submitOrder(order.orderID)
    print(f"  {order.orderID} is {order.orderStatus}, ready around {handler.estTime.strftime('%H:%M')}")

    print("\nModify Order: one more tart, two lattes -> one")
    order = handler.selectOrder(order.orderID)
    latte = [line for line in order.getOrderDetails() if line.menuItem.menuItemID == 6][0]
    handler.modifyOrder(order.orderID, [("add", 4, 1), ("modify", latte.orderLineID, 1)])
    handler.confirmChanges(order.orderID)
    show_order(order)

    print("\nTrack and Complete Order: startPreparation, requestRemake, markReady")
    handler.startPreparation(order.orderID)
    handler.requestRemake(order.orderID, order.getOrderDetails()[0].orderLineID)
    handler.markReady(order.orderID)

    print("\nCancel Order: ORD-0012 has not started, so no manager is needed")
    handler.enterReason("Customer changed their mind")
    print(f"  cancelOrder -> {handler.cancelOrder('ORD-0012')}")

    print(f"\nCancel Order: {order.orderID} is Ready, so a manager must approve")
    handler.enterReason("Customer could not wait")
    print(f"  cancelOrder -> {handler.cancelOrder(order.orderID)} (approval needed)")
    print(f"  approveCancellation with a wrong password -> "
          f"{handler.approveCancellation(order.orderID, 1, 'wrong')}")
    print(f"  approveCancellation with the right password -> "
          f"{handler.approveCancellation(order.orderID, 1, 'manager123')}")

    print("\nCancel Order: ORD-0015 was already paid by card, so it is refunded")
    handler.enterReason("Duplicate order")
    handler.cancelOrder("ORD-0015")
    print(f"  approveCancellation -> {handler.approveCancellation('ORD-0015', 1, 'manager123')}")

    print("\nComplete Order: ORD-0014 is paid, the customer picks it up")
    employee.markOrderComplete("ORD-0014")
    print(f"  {employee.displayStatus('ORD-0014')}")


def process_payments_demo():
    """Process Payments (UC 02): Emma pays for ORD-0013 (Ready). The card is declined,
    then too little cash is declined, then the cash payment is approved."""
    print("\n=== Process Payments (UC 02) ===")
    customer = load_customer(4)
    print(f"Customer: {customer.getFullName()}, order ORD-0013 "
          f"(${load_order('ORD-0013').orderTotal:.2f})")
    today = date.today()
    card = CardPayment(0, 0.0, "card", today, "", "gift card", "")
    print(f"  payOrder with a gift card -> {customer.payOrder('ORD-0013', card)} "
          f"(declined: only debit and credit cards; order is {load_order('ORD-0013').orderStatus})")
    cash = CashPayment(0, 0.0, "cash", today, "", 10.00, 0.0)
    print(f"  payOrder with $10.00 cash -> {customer.payOrder('ORD-0013', cash)} "
          f"(declined: not enough cash)")
    cash = CashPayment(0, 0.0, "cash", today, "", 20.00, 0.0)
    approved = customer.payOrder("ORD-0013", cash)
    print(f"  payOrder with $20.00 cash -> {approved}, change ${cash.changeDue:.2f}, "
          f"order is {load_order('ORD-0013').orderStatus}")
    load_employee(1).markOrderComplete("ORD-0013")
    print(f"  Employee.markOrderComplete -> {load_order('ORD-0013').orderStatus}")


def manage_accounts_demo(manager):
    """Manage Employee Accounts (UC 03): invalid information is refused, then Sam's
    account is updated and Alex logs in."""
    print("\n=== Manage Employee Accounts (UC 03) ===")
    try:
        manager.createAccount(1, "not-an-email", "cheque.docx", "123")
    except ValueError as err:
        print(f"  createAccount with bad information -> {err}")
    print(f"  modifyAccount(1) with a bad email -> {manager.modifyAccount(1, employeeEmail='sam')}")
    print(f"  modifyAccount(1) with a new password -> "
          f"{manager.modifyAccount(1, accountPassword='SamBakes2026')}")
    print(f"  verifyAccountPassword -> {load_account(1).verifyAccountPassword('SamBakes2026')}")
    alex = load_employee(2)
    print(f"  Employee.login('alex.m', 'manager123') -> {alex.login('alex.m', 'manager123')}")
    alex.logout()


def manage_promotions_demo(manager):
    """Manage Promotions (UC 05): a draft is saved and edited, then a promotion is shared
    and applied to an order (calculateDiscount)."""
    print("\n=== Manage Promotions (UC 05) ===")
    today = date.today()
    draft = Promotion(0, "", "", 0, today, today, today, "", "", managerID=manager.managerID)
    draft.createPromotion(next_promotion_id(), "Spring Tarts", "percentage", 20,
                          date(2027, 3, 1), date(2027, 3, 31))
    draft.saveDraft(draft.promotionID)
    draft.editDraft(draft.promotionID, discountValue=25)
    print(f"  Draft #{draft.promotionID} '{draft.title}': {draft.discountValue}% off, "
          f"{draft.lifeCycleState}, valid now: {draft.isValid(draft.promotionID)}")
    print("  createPromotion('Winter Warm-Up', $3 off), then sharePromotion by SMS:")
    promotion = Promotion(0, "", "", 0, today, today, today, "", "", managerID=manager.managerID)
    promotion.createPromotion(next_promotion_id(), "Winter Warm-Up", "fixed", 3, today,
                              today + timedelta(days=30))
    promotion.sharePromotion(promotion.promotionID, "SMS")
    print(f"  #{promotion.promotionID} is {promotion.lifeCycleState}, valid now: "
          f"{promotion.isValid(promotion.promotionID)}")
    handler = OrderHandler(customer=load_customer(3), employee=load_employee(1))
    order = handler.startOrder("in-store")
    order.addItem(1, 2)
    discount = handler.applyPromotion(promotion.promotionID)
    print(f"  applyPromotion on {order.orderID} (${order.orderTotal + discount:.2f}): "
          f"${discount:.2f} off, total ${order.orderTotal:.2f}")
    print(f"  trackEngagement -> {promotion.trackEngagement(promotion.promotionID)} order(s)")

    print(f"\n  {order.orderID} goes through the whole flow: submit, prepare, ready, pay, complete")
    handler.reviewOrder(order.orderID)
    handler.submitOrder(order.orderID)
    handler.startPreparation(order.orderID)
    handler.markReady(order.orderID)
    card = CardPayment(0, 0.0, "card", today, "", "credit", "")
    print(f"  payOrder by credit card -> {load_customer(3).payOrder(order.orderID, card)}")
    load_employee(1).markOrderComplete(order.orderID)

    print("\nStore.generateDailySales(1): today's sales report for Eaton Centre")
    Store(1, "Soufflé Eaton Centre", "").generateDailySales(1)


def manage_inventory_demo(manager):
    """Manage Inventory (UC 04): the manager views the Eaton Centre inventory, filters the
    low items, restocks the eggs and tries a quantity that is not valid."""
    print("\n=== Manage Inventory (UC 04) ===")
    print(f"Manager: {manager.getFullName()}")
    screen = InventoryUI(inventory=load_inventory(1))

    print("\nView Inventory: viewInventory()")
    screen.viewInventory()

    print("\nFilter: items below minimum only")
    screen.filterCategory = "below minimum"
    screen.viewInventory()
    screen.filterCategory = ""

    print("\nUpdate Inventory Item: updateQuantity(1, 12)")
    screen.updateQuantity(1, 12)
    print("Update Inventory Item: updateQuantity(4, -3)")
    screen.updateQuantity(4, -3)


def create_reports_demo(manager):
    """Create Reports (UC 06): the manager generates, saves and exports each report type
    for Soufflé Eaton Centre, October 1 to November 30, 2026."""
    print("\n=== Create Reports (UC 06) ===")
    print(f"Manager: {manager.getFullName()}")
    start, end, store = date(2026, 10, 1), date(2026, 11, 30), 1
    for report_type in (SalesReport, InventoryReport, CustomerLoyaltyReport):
        report = report_type(next_report_id(), start, end, date.today(), "CSV",
                             managerID=manager.managerID, storeID=store)
        print()
        if report.retrieveRecords(start, end, store):
            print(report.save(report.reportID))
            print(report.export(report.reportID, "CSV"))
        else:
            print(f"No records for the {report.REPORT_NAME.lower()} report in this period.")


if __name__ == "__main__":
    main()
