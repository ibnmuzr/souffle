"""Manage Employee Accounts (UC 03): interactive screen for the manager.

Create an account (invalid information is refused with the reasons), change an
account's email, password or status, or delete it.

Run from the project folder:  python3 manage_accounts.py
"""
from contextlib import closing

from database.connection import DB_PATH, get_connection
from database.setup_db import create_database
from models.people import load_manager


def ask(prompt, default=""):
    shown = f" [{default}]" if default else ""
    answer = input(f"{prompt}{shown}: ").strip()
    return answer or default


def ask_int(prompt):
    text = ask(prompt)
    return int(text) if text.isdigit() else -1


def list_accounts():
    with closing(get_connection()) as conn:
        rows = conn.execute(
            "SELECT a.accountID, a.employeeID, p.firstName, p.lastName, a.employeeEmail, "
            "a.accountStatus FROM employee_accounts a JOIN employees e ON e.employeeID = a.employeeID "
            "JOIN persons p ON p.personID = e.personID ORDER BY a.accountID").fetchall()
        staff = conn.execute(
            "SELECT e.employeeID, p.firstName, p.lastName FROM employees e JOIN persons p "
            "ON p.personID = e.personID WHERE e.employeeID NOT IN "
            "(SELECT employeeID FROM employee_accounts)").fetchall()
    for r in rows:
        print(f"  account {r['accountID']}: employee {r['employeeID']} {r['firstName']} "
              f"{r['lastName']:<10} {r['employeeEmail']:<28} {r['accountStatus']}")
    for r in staff:
        print(f"  (no account) employee {r['employeeID']} {r['firstName']} {r['lastName']}")


def main():
    if not DB_PATH.exists():
        create_database()
    manager = load_manager(1)
    print("=== Soufflé: Manage Employee Accounts ===")
    print(f"Logged in as manager {manager.getFullName()}")
    while True:
        print("\n1 List accounts   2 Create   3 Modify   4 Delete   q Quit")
        choice = ask("Choose", "1").lower()
        if choice == "q":
            break
        if choice == "1":
            list_accounts()
        elif choice == "2":
            try:
                account = manager.createAccount(
                    ask_int("Employee ID"), ask("Employee email"),
                    ask("Void cheque file", "uploads/void_cheque.pdf"),
                    ask("Password (8 characters or more)"))
                print(f"  Account {account.accountID} created and active.")
            except ValueError as err:
                print(f"  Not created. {err}")
        elif choice == "3":
            ok = manager.modifyAccount(
                ask_int("Account ID"), employeeEmail=ask("New email (Enter to keep)") or None,
                accountPassword=ask("New password (Enter to keep)") or None,
                accountStatus=ask("New status: active / inactive (Enter to keep)") or None)
            print("  Account updated." if ok else "  Not updated: the new information is not valid.")
        elif choice == "4":
            accountID = ask_int("Account ID")
            if ask(f"Delete account {accountID}? y/n", "n").lower() == "y":
                print("  Deleted." if manager.deleteAccount(accountID) else "  There is no such account.")
        else:
            print("  Please choose 1 to 4, or q.")
    print("Goodbye.")


if __name__ == "__main__":
    main()
