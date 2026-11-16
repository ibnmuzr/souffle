"""Manage Inventory (UC 04): interactive screen for the manager.

The manager picks a store, views its inventory (with an optional search keyword and a
"below minimum" filter) and updates the quantity of an item. Each action runs its
Milestone 4 sequence diagram through the InventoryUI:

    View Inventory         viewInventoryList()
    Update Inventory Item  updateQuantity(itemID, newQuant)

Run from the project folder:  python3 manage_inventory.py
"""
from contextlib import closing

from database.connection import DB_PATH, get_connection
from database.setup_db import create_database
from models import InventoryUI
from models.inventory import load_inventory
from models.inventory_ui import LOW_STOCK_FILTER


def ask(prompt, default=""):
    shown = f" [{default}]" if default else ""
    answer = input(f"{prompt}{shown}: ").strip()
    return answer or default


def to_quantity(text):
    """Whole numbers become int; anything else is passed on as typed, so that
    InventoryItem.validateQuantity rejects it."""
    try:
        return int(text)
    except ValueError:
        return text


def main():
    if not DB_PATH.exists():
        create_database()
    with closing(get_connection()) as conn:
        manager = conn.execute(
            "SELECT p.firstName, p.lastName FROM managers m "
            "JOIN persons p ON p.personID = m.personID ORDER BY m.managerID"
        ).fetchone()
        stores = conn.execute("SELECT storeID, storeName FROM stores ORDER BY storeID").fetchall()

    print("=== Soufflé: Manage Inventory ===")
    print(f"Logged in as manager {manager['firstName']} {manager['lastName']}")
    print("Stores: " + "   ".join(f"{s['storeID']} {s['storeName']}" for s in stores))
    store = ask("Store", "1")
    if store not in {str(s["storeID"]) for s in stores}:
        print("Unknown store.")
        return

    screen = InventoryUI(inventory=load_inventory(int(store)))
    print()
    screen.viewInventoryList()

    while True:
        print("\n1 View inventory   2 Update a quantity   q Quit")
        choice = ask("Choose", "1").lower()
        if choice == "q":
            break
        if choice == "1":
            screen.searchKeyword = ask("Search item name (Enter for all)")
            low_only = ask("Only items below minimum? y/n", "n").lower() == "y"
            screen.filterCategory = LOW_STOCK_FILTER if low_only else ""
            print()
            screen.viewInventoryList()
        elif choice == "2":
            try:
                itemID = int(ask("Item ID"))
                item = screen.inventory._find_item(itemID)
            except ValueError as err:
                print(f"  {err if 'item' in str(err) else 'Please type the item ID number.'}")
                continue
            print(f"  {item.itemName}: current quantity {item.quantity}, "
                  f"minimum {item.minimumQuantity}")
            newQuant = to_quantity(ask("New quantity"))
            screen.updateQuantity(itemID, newQuant)
        else:
            print("  Please choose 1, 2 or q.")

    print("Goodbye.")


if __name__ == "__main__":
    main()
