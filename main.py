"""Soufflé Management System: prototype demo.

Builds the database, loads rows into the class-diagram classes to show that the
classes, their attributes and the database line up, then runs the Create Reports
use case (all three report types) the way the sequence diagrams describe it.

Run from the project folder:  python3 main.py
For the interactive report menu: python3 create_reports.py
"""
from datetime import date

from database.connection import get_connection
from database.setup_db import create_database
from models import (
    Customer, Manager, Person, Store, InventoryItem, MenuItem, Order, Promotion,
    CashPayment, SalesReport, InventoryReport, CustomerLoyaltyReport,
)
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
          f"change due ${cash.calculateChange():.2f}")

    print("\nPromotions (lifecycleState, /duration):")
    for r in conn.execute("SELECT * FROM promotions"):
        promo = Promotion(r["promotionID"], r["title"], r["discountType"], r["discountValue"],
                          d(r["creationDate"]), d(r["startDate"]), d(r["endDate"]),
                          r["sharingChannel"] or "", r["lifecycleState"])
        print(f"  {promo.title:<22}{promo.lifecycleState:<9}runs {promo.duration} days")

    order = order_from_row(conn.execute("SELECT * FROM orders WHERE orderID = 'ORD-0002'").fetchone())
    discount = order.calculateDiscount(order.orderID, order.orderTotal, 3)
    print(f"Order.calculateDiscount: 'November Latte Days' on {order.orderID} "
          f"(${order.orderTotal:.2f}) = ${discount:.2f} off")

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
    create_reports_demo(manager)
    print("\nDone.")


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
