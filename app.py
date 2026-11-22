"""Soufflé Management System: main menu.

Opens the screen of each use case. The database is created with the sample data the
first time; choose 0 to start again from the sample data.

Run from the project folder:  python3 app.py
"""
import create_reports
import manage_accounts
import manage_inventory
import manage_orders
import manage_promotions
import process_payments
from database.connection import DB_PATH
from database.setup_db import create_database

SCREENS = {
    "1": ("Manage Orders (employee)", manage_orders.main),
    "2": ("Process Payments (counter)", process_payments.main),
    "3": ("Manage Employee Accounts (manager)", manage_accounts.main),
    "4": ("Manage Inventory (manager)", manage_inventory.main),
    "5": ("Manage Promotions (manager)", manage_promotions.main),
    "6": ("Create Reports (manager)", create_reports.main),
}


def main():
    if not DB_PATH.exists():
        create_database()
    while True:
        print("\n=== Soufflé Management System ===")
        for key, (title, _screen) in SCREENS.items():
            print(f"  {key}  {title}")
        print("  0  Reset the sample data\n  q  Quit")
        choice = input("Choose: ").strip().lower()
        if choice == "q":
            break
        if choice == "0":
            create_database()
            print("Sample data loaded again.")
        elif choice in SCREENS:
            print()
            SCREENS[choice][1]()
        else:
            print("Please choose 0 to 6, or q.")
    print("Goodbye.")


if __name__ == "__main__":
    main()
