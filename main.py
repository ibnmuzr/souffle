"""Soufflé Management System, prototype 1.

Builds the database, then loads rows into the class-diagram classes to show that
the classes, their attributes and the database line up.

Run from the project folder:  python3 main.py
"""
from datetime import date

from database.connection import get_connection
from database.setup_db import create_database
from models import (
    Customer, Manager, Person, Store, InventoryItem, MenuItem,
    CashPayment, SharedPromotion, SalesReport, InventoryReport,
)

TABLES = [
    "persons", "customers", "employees", "managers", "employee_accounts",
    "stores", "inventories", "inventory_items",
    "menu_items", "orders", "order_lines",
    "payments", "card_payments", "cash_payments", "receipts",
    "promotions", "draft_promotions", "shared_promotions", "customer_shared_promotions",
    "reports", "sales_reports", "inventory_reports", "customer_loyalty_reports",
    "sales_report_orders", "inventory_report_items", "loyalty_report_customers",
]


def d(text):
    """Convert a YYYY-MM-DD string from the database into a date."""
    return date.fromisoformat(text)


def main():
    create_database()
    conn = get_connection()

    print("=== Soufflé Management System: prototype 1 ===\n")
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
        item = MenuItem(r["itemID"], r["name"], r["description"], r["category"],
                        r["price"], bool(r["isAvailable"]))
        status = "available" if item.checkAvailability() else "unavailable"
        print(f"  {item.name:<34}${item.price:>6.2f}  ({status})")

    print("\nEaton Centre stock below minimum (InventoryItem.isBelowMinimum):")
    for r in conn.execute("SELECT * FROM inventory_items WHERE inventoryID = 1"):
        item = InventoryItem(r["itemID"], r["itemName"], r["quantity"], r["minimumQuantity"])
        if item.isBelowMinimum():
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

    r = conn.execute(
        "SELECT * FROM promotions p JOIN shared_promotions s ON s.promotionID = p.promotionID"
    ).fetchone()
    promo = SharedPromotion(r["promotionID"], r["title"], r["discountType"], r["discountValue"],
                            d(r["startDate"]), d(r["endDate"]), d(r["sharingDate"]),
                            r["sharingChannel"])
    print(f"\nPromotion '{promo.title}' ({promo.discountValue}% off, shared by "
          f"{promo.sharingChannel}): runs {promo.duration} days, "
          f"discount on a $19.48 order = ${promo.calculateDiscount(19.48):.2f}")

    r = conn.execute(
        "SELECT * FROM reports r JOIN sales_reports s ON s.reportID = r.reportID"
    ).fetchone()
    sales = SalesReport(r["reportID"], d(r["startDate"]), d(r["endDate"]), d(r["createdDate"]),
                        r["format"], r["totalRevenue"], r["unitSold"], r["averageOrderTotal"])
    print(f"\nSales report {sales.startDate} to {sales.endDate}: revenue ${sales.totalRevenue:.2f}, "
          f"{sales.unitSold} units, average order ${sales.averageOrderTotal:.2f}")

    r = conn.execute(
        "SELECT * FROM reports r JOIN inventory_reports i ON i.reportID = r.reportID"
    ).fetchone()
    inv = InventoryReport(r["reportID"], d(r["startDate"]), d(r["endDate"]), d(r["createdDate"]),
                          r["format"], r["itemsBelowMinimum"])
    print(f"Inventory report: {inv.itemsBelowMinimum} items below minimum")

    print("\nAbstract classes cannot be created directly:")
    try:
        Person(99, "Test", "Person", "", "")
    except TypeError as err:
        print(f"  {err}")

    conn.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
