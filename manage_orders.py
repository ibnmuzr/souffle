"""Manage Orders (UC 01): interactive screen for the employee (and the manager's approval).

Each choice runs its Milestone 4 sequence diagram through the OrderHandler:

    1 Create and submit an order   startOrder, addItem (loop), applyPromotion, reviewOrder, submitOrder
    2 Modify an order              selectOrder, modifyOrder, confirmChanges
    3 Cancel an order              selectOrder, enterReason, cancelOrder, approveCancellation
    4 Kitchen                      startPreparation, requestRemake, markReady
    5 Complete a paid order        Employee.markOrderComplete
    6 Open orders                  orders that are not Completed or Cancelled

Run from the project folder:  python3 manage_orders.py
"""
from contextlib import closing

from database.connection import DB_PATH, get_connection
from database.setup_db import create_database
from models import OrderHandler
from models.orders import ORDER_TYPES, load_menu, load_menu_item
from models.people import load_customer, load_employee, load_manager

STORE_ID = 1   # the screen runs at Soufflé Eaton Centre


def ask(prompt, default=""):
    shown = f" [{default}]" if default else ""
    answer = input(f"{prompt}{shown}: ").strip()
    return answer or default


def ask_int(prompt, default=""):
    text = ask(prompt, default)
    try:
        return int(text)
    except ValueError:
        return None


def show_order(order):
    """Order summary: lines, discount and total."""
    lines = order.getOrderDetails()
    print(f"  Order {order.orderID} ({order.orderType}) - {order.orderStatus}")
    for line in lines:
        note = f"  ({line.specialInstructions})" if line.specialInstructions else ""
        print(f"    line {line.orderLineID:>3}: {line.quantity} x {line.menuItem.name:<34}"
              f"${line.lineTotal:>6.2f}{note}")
    if order.discountAmount:
        print(f"    promotion {order.promotionID} discount: -${order.discountAmount:.2f}")
    print(f"    Total: ${order.orderTotal:.2f}")


def show_menu():
    for item in load_menu():
        status = "" if item.isAvailable else "  (not available)"
        print(f"    {item.menuItemID}  {item.name:<34}${item.price:>6.2f}{status}")


def add_items(handler):
    """loop [for each item]: checkAvailability, then addItem."""
    show_menu()
    while True:
        menuItemID = ask_int("  Menu item ID (Enter when done)")
        if menuItemID is None:
            return
        quantity = ask_int("  Quantity", "1")
        instructions = ask("  Special instructions (Enter for none)")
        try:
            item = load_menu_item(menuItemID)
            if not item.checkAvailability(menuItemID, quantity or 0):
                print(f"  {item.name} is not available in that quantity.")
                continue
            handler.order.addItem(menuItemID, quantity, instructions)
            print(f"  Added {quantity} x {item.name}. Total so far: "
                  f"${handler.order.orderTotal:.2f}")
        except ValueError as err:
            print(f"  {err}")


def create_order(handler):
    orderType = ask(f"Order type ({' / '.join(ORDER_TYPES)})", "in-store")
    customer = ask_int("Customer ID (Enter for a walk-in customer)")
    try:
        handler.customer = load_customer(customer) if customer else None
        order = handler.startOrder(orderType)
    except ValueError as err:
        print(f"  {err}")
        return
    print(f"  Started order {order.orderID}.")
    add_items(handler)
    if not order.getOrderDetails():
        print("  No items: the order stays open (In process). You can cancel it from the menu.")
        return
    promotion = ask_int("Promotion ID (Enter for none)")
    if promotion:
        discount = handler.applyPromotion(promotion)
        print(f"  Discount: ${discount:.2f}" if discount else
              "  That promotion is not valid right now: no discount.")
    order = handler.reviewOrder(order.orderID)
    print("\nOrder summary:")
    show_order(order)
    if ask("Submit the order to the kitchen? y/n", "y").lower() == "y":
        handler.submitOrder(order.orderID)
        print(f"  Order {order.orderID} sent to the kitchen. Ready around "
              f"{handler.estTime.strftime('%H:%M')}.")


def modify_order(handler):
    try:
        order = handler.selectOrder(ask("Order ID"))
    except ValueError as err:
        print(f"  {err}")
        return
    show_order(order)
    changes = []
    while True:
        action = ask("  a add item / r remove line / m change quantity / d done", "d").lower()
        if action == "d":
            break
        if action == "a":
            show_menu()
            changes.append(("add", ask_int("  Menu item ID"), ask_int("  Quantity", "1") or 1,
                            ask("  Special instructions (Enter for none)")))
        elif action == "r":
            changes.append(("remove", ask_int("  Line number")))
        elif action == "m":
            changes.append(("modify", ask_int("  Line number"), ask_int("  New quantity")))
    if not changes:
        return
    try:
        handler.modifyOrder(order.orderID, changes)
    except ValueError as err:
        print(f"  Not changed: {err}")
        return
    print("\nUpdated order:")
    show_order(order)
    if ask("Save the changes? y/n", "y").lower() == "y" and handler.confirmChanges(order.orderID):
        print(f"  Order {order.orderID} updated.")


def cancel_order(handler):
    try:
        order = handler.selectOrder(ask("Order ID"))
    except ValueError as err:
        print(f"  {err}")
        return
    show_order(order)
    try:
        handler.enterReason(ask("Reason for the cancellation"))
        if handler.cancelOrder(order.orderID):
            print(f"  Order {order.orderID} cancelled (the kitchen had not started it).")
            return
    except ValueError as err:
        print(f"  {err}")
        return
    manager = load_manager(1)
    print(f"\n  Manager approval needed. {manager.requestReason(order.orderID)}")
    print(f"  Reason: {handler.pendingReason}")
    managerID = ask_int("  Manager ID", "1")
    password = ask("  Manager password")
    if handler.approveCancellation(order.orderID, managerID, password):
        print(f"  Order {order.orderID} cancelled with the manager's approval.")
    else:
        print("  Not approved (wrong manager ID or password): the order is unchanged.")


def kitchen(handler):
    orderID = ask("Order ID")
    action = ask("  s start preparation / r remake an item / k mark ready", "s").lower()
    try:
        if action == "s":
            handler.startPreparation(orderID)
        elif action == "r":
            show_order(handler.selectOrder(orderID))
            handler.requestRemake(orderID, ask_int("  Line to remake"))
        elif action == "k":
            handler.markReady(orderID)
    except ValueError as err:
        print(f"  {err}")


def complete_order(employee):
    orderID = ask("Order ID")
    try:
        employee.markOrderComplete(orderID)
        print(f"  Order {orderID.upper()} completed and recorded as a sale.")
    except ValueError as err:
        print(f"  {err}")


def open_orders():
    with closing(get_connection()) as conn:
        rows = conn.execute(
            "SELECT orderID, orderType, orderStatus, orderTotal FROM orders WHERE storeID = ? "
            "AND orderStatus NOT IN ('Completed', 'Cancelled') ORDER BY orderID",
            (STORE_ID,)).fetchall()
    for r in rows:
        print(f"  {r['orderID']}  {r['orderType']:<9}{r['orderStatus']:<12}${r['orderTotal']:>6.2f}")
    if not rows:
        print("  No open orders.")


def main():
    if not DB_PATH.exists():
        create_database()
    employee = load_employee(1)
    print("=== Soufflé: Manage Orders ===")
    print(f"Logged in as {employee.getFullName()} at Soufflé Eaton Centre")
    while True:
        print("\n1 New order  2 Modify  3 Cancel  4 Kitchen  5 Complete a paid order  "
              "6 Open orders  q Quit")
        choice = ask("Choose", "6").lower()
        handler = OrderHandler(employee=employee, storeID=STORE_ID)
        if choice == "q":
            break
        actions = {"1": lambda: create_order(handler), "2": lambda: modify_order(handler),
                   "3": lambda: cancel_order(handler), "4": lambda: kitchen(handler),
                   "5": lambda: complete_order(employee), "6": open_orders}
        if choice in actions:
            print()
            actions[choice]()
        else:
            print("  Please choose 1 to 6, or q.")
    print("Goodbye.")


if __name__ == "__main__":
    main()
