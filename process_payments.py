"""Process Payments (UC 02): interactive pay screen at the counter.

The employee picks an order that is Ready (or whose payment was Declined) and the
customer pays by card or cash. The payment runs the Milestone 5 method specification 01
(processPayment): approved -> receipt printed, order Paid; declined -> try again.

Run from the project folder:  python3 process_payments.py
"""
from contextlib import closing
from datetime import date

from database.connection import DB_PATH, get_connection
from database.setup_db import create_database
from models import CardPayment, CashPayment
from models.orders import load_order
from models.people import load_customer, load_employee


def ask(prompt, default=""):
    shown = f" [{default}]" if default else ""
    answer = input(f"{prompt}{shown}: ").strip()
    return answer or default


def orders_to_pay():
    with closing(get_connection()) as conn:
        rows = conn.execute("SELECT orderID, orderStatus, orderTotal FROM orders "
                            "WHERE orderStatus IN ('Ready', 'Declined') ORDER BY orderID").fetchall()
    for r in rows:
        print(f"  {r['orderID']}  {r['orderStatus']:<9}${r['orderTotal']:>6.2f}")
    if not rows:
        print("  No orders are waiting for payment (an order can be paid once it is Ready).")
    return bool(rows)


def pay(orderID):
    order = load_order(orderID)
    total = order.calculateTotal(order.orderID)
    print(f"  Order {order.orderID}: total ${total:.2f}")
    method = ask("  Pay by card (c) or cash (k)", "c").lower()
    today = date.today()
    if method == "k":
        try:
            received = float(ask("  Cash received", f"{total:.2f}"))
        except ValueError:
            print("  Please type an amount, for example 20.00.")
            return
        payment = CashPayment(0, 0.0, "cash", today, "", received, 0.0)
    else:
        payment = CardPayment(0, 0.0, "card", today, "", ask("  Card type (debit / credit)", "debit"), "")
    if order.customerID:
        approved = load_customer(order.customerID).payOrder(order.orderID, payment)
    else:
        approved = order.confirmOrder(order.orderID, payment)   # walk-in customer
    if approved:
        extra = f", change ${payment.changeDue:.2f}" if method == "k" else ""
        print(f"  Approved{extra}. Order {order.orderID} is Paid.")
    else:
        why = "not enough cash" if method == "k" else "the card was not authorized"
        print(f"  Declined ({why}). The customer can try again.")


def main():
    if not DB_PATH.exists():
        create_database()
    employee = load_employee(1)
    print("=== Soufflé: Process Payments ===")
    print(f"Logged in as {employee.getFullName()}")
    while True:
        print("\nOrders waiting for payment:")
        if not orders_to_pay():
            break
        orderID = ask("Order ID to pay (q to quit)", "q")
        if orderID.lower() == "q":
            break
        try:
            pay(orderID)
            if load_order(orderID).orderStatus == "Paid" and \
                    ask("  Customer has the order: mark it Completed? y/n", "y").lower() == "y":
                employee.markOrderComplete(orderID)
                print(f"  Order {orderID.upper()} completed.")
        except ValueError as err:
            print(f"  {err}")
    print("Goodbye.")


if __name__ == "__main__":
    main()
