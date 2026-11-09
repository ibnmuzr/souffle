"""Create Reports (UC 06): interactive menu for the manager.

The manager picks a report type, a store and a period. The report then runs its
sequence diagram (retrieveRecords -> compile/calculate -> generate(reportID)) and the manager
can save it, export it, or both.

Run from the project folder:  python3 create_reports.py
"""
from contextlib import closing
from datetime import date

from database.connection import DB_PATH, get_connection
from database.setup_db import create_database
from models import CustomerLoyaltyReport, InventoryReport, SalesReport
from models.reports import next_report_id

REPORT_TYPES = {"1": SalesReport, "2": InventoryReport, "3": CustomerLoyaltyReport}


def ask(prompt, default=""):
    shown = f" [{default}]" if default else ""
    answer = input(f"{prompt}{shown}: ").strip()
    return answer or default


def ask_date(prompt, default):
    while True:
        text = ask(prompt, default)
        try:
            return date.fromisoformat(text)
        except ValueError:
            print("  Please use the format YYYY-MM-DD, for example 2026-10-01.")


def main():
    if not DB_PATH.exists():
        create_database()
    with closing(get_connection()) as conn:
        manager = conn.execute(
            "SELECT m.managerID, p.firstName, p.lastName FROM managers m "
            "JOIN persons p ON p.personID = m.personID ORDER BY m.managerID"
        ).fetchone()
        stores = conn.execute("SELECT storeID, storeName FROM stores ORDER BY storeID").fetchall()

    print("=== Soufflé: Create Reports ===")
    print(f"Logged in as manager {manager['firstName']} {manager['lastName']}")

    while True:
        print("\nReport type: 1 Sales   2 Inventory   3 Customer loyalty   q Quit")
        choice = ask("Choose", "1").lower()
        if choice == "q":
            break
        if choice not in REPORT_TYPES:
            print("  Please choose 1, 2, 3 or q.")
            continue

        print("Stores: " + "   ".join(f"{s['storeID']} {s['storeName']}" for s in stores))
        store_ids = {str(s["storeID"]) for s in stores}
        store = ask("Store", "1")
        if store not in store_ids:
            print("  Unknown store.")
            continue

        start = ask_date("Start date", "2026-10-01")
        end = ask_date("End date", date.today().isoformat())
        if end < start:
            print("  The end date must be on or after the start date.")
            continue

        report = REPORT_TYPES[choice](next_report_id(), start, end, date.today(), "CSV",
                                      managerID=manager["managerID"], storeID=int(store))
        print()
        if not report.retrieveRecords(start, end, int(store)):
            print("No records found for this store and period.")
            continue

        action = ask("Save (s), export (e), both (b) or neither (n)", "b").lower()
        if action in ("s", "b"):
            print(report.save(report.reportID))
        if action in ("e", "b"):
            fmt = ask("Export format, CSV or TXT", "CSV")
            try:
                print(report.export(report.reportID, fmt))
            except ValueError as err:
                print(f"  {err}")

    print("Goodbye.")


if __name__ == "__main__":
    main()
