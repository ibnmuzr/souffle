"""Reports (Create Reports use case, UC 06): Report (abstract), SalesReport,
InventoryReport, CustomerLoyaltyReport.

Each report type follows its Milestone 4 sequence diagram step by step, with the
same method names and parameters as the final class diagram:

    aManager -> retrieveRecords(startDate, endDate, storeID)
                    loop over the records (orders, inventory items or customers)
                    compile and calculate the figures (self-calls)
                    generate(reportID)                 -> report displayed
    aManager -> save(reportID)                         -> saveConfirmation
    aManager -> export(reportID, format)               -> exportConfirmation
"""
from __future__ import annotations

import csv
from contextlib import closing
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import List, Optional

from database.connection import get_connection
from .inventory import InventoryItem
from .orders import Order, order_from_row
from .people import Customer

EXPORT_DIR = Path(__file__).resolve().parent.parent / "exports"
EXPORT_FORMATS = ("CSV", "TXT")   # CSV opens in Excel
RESTOCK_TARGET = 2                # restock recommendation: bring stock back up to 2 x the minimum

# Completed orders of one store in a period. Cancelled orders are not sales.
COMPLETED_ORDERS_SQL = """
    SELECT * FROM orders
    WHERE storeID = ? AND orderDate BETWEEN ? AND ? AND LOWER(orderStatus) = 'completed'
    ORDER BY orderDate, orderID
"""


def next_report_id() -> int:
    """The reportID the next new report will get (one more than the highest saved one)."""
    return _rows("SELECT COALESCE(MAX(reportID), 0) + 1 AS nextID FROM reports")[0]["nextID"]


@dataclass
class Report:
    """«abstract» A business report compiled for a chosen period and store."""
    reportID: int
    startDate: date
    endDate: date
    createdDate: date
    format: str
    # Associations from the class diagram, kept as references to the related rows:
    managerID: Optional[int] = None   # Manager "generates" Report
    storeID: Optional[int] = None     # Report "covers" Store

    REPORT_NAME = "Business"

    def __post_init__(self):
        if type(self) is Report:
            raise TypeError("Report is abstract: create a Sales, Inventory or CustomerLoyalty report.")
        self.storeName = ""
        self.content: List[str] = []   # the generated report, line by line

    # ---- operations from the class diagram -------------------------------------------

    def retrieveRecords(self, startDate: date, endDate: date, storeID: int) -> bool:
        """Each report type retrieves its own records: see the subclasses."""
        raise NotImplementedError("Use a SalesReport, InventoryReport or CustomerLoyaltyReport.")

    def generate(self, reportID: int) -> None:
        """Build the report from the compiled figures and display it to the manager."""
        self._check_id(reportID)
        self.content = [
            "=" * 64,
            f"{self.REPORT_NAME.upper()} REPORT #{reportID}: {self.storeName}",
            f"Period: {self.startDate} to {self.endDate}    Created: {self.createdDate}",
            "-" * 64,
        ]
        for label, value in self._summary():
            self.content.append(f"{label:<28}{_show(value)}")
        header, rows = self._details()
        if rows:
            self.content.append("-" * 64)
            self.content.extend(_table(header, rows))
        self.content.append("=" * 64)
        print("\n".join(self.content))

    def save(self, reportID: int) -> str:
        """Store the report in the database and return the save confirmation."""
        self._check_id(reportID)
        self._check_generated()
        with closing(get_connection()) as conn:
            # saving again replaces the old copy
            conn.execute("DELETE FROM reports WHERE reportID = ?", (reportID,))
            conn.execute(
                "INSERT INTO reports (reportID, managerID, storeID, startDate, endDate, "
                "createdDate, format) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (reportID, self.managerID, self.storeID, self.startDate.isoformat(),
                 self.endDate.isoformat(), self.createdDate.isoformat(), self.format),
            )
            self._save_details(conn)
            conn.commit()
        return f"{self.REPORT_NAME} report #{reportID} saved."

    def export(self, reportID: int, format: str) -> str:
        """Write the report to a CSV or TXT file in exports/ and return the export confirmation."""
        self._check_id(reportID)
        self._check_generated()
        chosen = format.strip().upper()
        if chosen not in EXPORT_FORMATS:
            raise ValueError(f"Export format must be one of: {', '.join(EXPORT_FORMATS)}.")
        self.format = chosen
        EXPORT_DIR.mkdir(exist_ok=True)
        slug = self.REPORT_NAME.lower().replace(" ", "_")
        path = EXPORT_DIR / f"{slug}_report_{reportID}.{chosen.lower()}"
        if chosen == "TXT":
            path.write_text("\n".join(self.content) + "\n", encoding="utf-8")
        else:
            header, rows = self._details()
            # utf-8-sig so Excel shows the "é" in Soufflé correctly
            with path.open("w", newline="", encoding="utf-8-sig") as file:
                writer = csv.writer(file)
                writer.writerow([f"{self.REPORT_NAME} report #{reportID}", self.storeName])
                writer.writerow(["Period", f"{self.startDate} to {self.endDate}"])
                writer.writerow(["Created", self.createdDate])
                writer.writerows(self._summary())
                writer.writerow([])
                writer.writerow(header)
                writer.writerows(rows)
        return f"{self.REPORT_NAME} report exported to exports/{path.name}"

    # ---- helpers shared by the report types (not in the class diagram) ------------------

    def _set_period(self, startDate: date, endDate: date, storeID: int) -> None:
        if endDate < startDate:
            raise ValueError("The end date must be on or after the start date.")
        self.startDate, self.endDate, self.storeID = startDate, endDate, storeID
        found = _rows("SELECT storeName FROM stores WHERE storeID = ?", (storeID,))
        if not found:
            raise ValueError(f"There is no store with ID {storeID}.")
        self.storeName = found[0]["storeName"]

    def _completed_orders(self, storeID: int, startDate: date, endDate: date) -> list:
        return _rows(COMPLETED_ORDERS_SQL, (storeID, startDate.isoformat(), endDate.isoformat()))

    def _check_id(self, reportID: int) -> None:
        if reportID != self.reportID:
            raise ValueError(f"This is report #{self.reportID}, not report #{reportID}.")

    def _check_generated(self) -> None:
        if not self.content:
            raise RuntimeError("Retrieve the records first: the report has not been generated yet.")

    def _summary(self) -> list:
        """(label, value) pairs shown at the top of the report."""
        raise NotImplementedError

    def _details(self) -> tuple:
        """(header, rows) of the detail table under the summary."""
        raise NotImplementedError

    def _save_details(self, conn) -> None:
        """Insert the subclass row and the association rows."""
        raise NotImplementedError


@dataclass
class SalesReport(Report):
    """A report summarizing sales activity for the period."""
    totalRevenue: float = 0.0
    unitSold: int = 0
    averageOrderTotal: float = 0.0

    REPORT_NAME = "Sales"

    def __post_init__(self):
        super().__post_init__()
        self.orders: List[Order] = []    # SalesReport "summarizes" Order
        self.orderTotals = {}            # orderID -> orderTotal returned by calculateTotal
        self.orderLines = []             # order lines of the period: (orderID, quantity)

    def retrieveRecords(self, startDate: date, endDate: date, storeID: int) -> bool:
        """Sequence diagram "Create Reports: Generate Sales Report"."""
        self._set_period(startDate, endDate, storeID)
        self.orders = [order_from_row(row)
                       for row in self._completed_orders(storeID, startDate, endDate)]
        # loop [for each order in the period]
        for order in self.orders:
            self.orderTotals[order.orderID] = order.calculateTotal(order.orderID)
        if not self.orders:
            return False
        self.compileSalesFigures(storeID, startDate, endDate)
        self.calculateRevenue(storeID, list(self.orderTotals.values()))
        self.calculateUnitSold(storeID, self.orderLines)
        self.calculateAverageOrderValue(self.totalRevenue, len(self.orders))
        self.generate(self.reportID)
        return True

    def compileSalesFigures(self, storeID: int, startDate: date, endDate: date) -> None:
        """Collect the order lines of the store's completed orders in the period."""
        order_ids = [row["orderID"] for row in self._completed_orders(storeID, startDate, endDate)]
        if not order_ids:
            self.orderLines = []
            return
        marks = ", ".join("?" * len(order_ids))
        rows = _rows(f"SELECT orderID, quantity FROM order_lines WHERE orderID IN ({marks}) "
                     f"ORDER BY orderID, orderLineID", order_ids)
        self.orderLines = [(row["orderID"], row["quantity"]) for row in rows]

    def calculateRevenue(self, storeID: int, orderTotals: list) -> float:
        self.totalRevenue = round(sum(orderTotals, 0.0), 2)
        return self.totalRevenue

    def calculateUnitSold(self, storeID: int, orderLines: list) -> int:
        self.unitSold = sum(quantity for _orderID, quantity in orderLines)
        return self.unitSold

    def calculateAverageOrderValue(self, totalRevenue: float, numberOfOrders: int) -> float:
        self.averageOrderTotal = round(totalRevenue / numberOfOrders, 2) if numberOfOrders else 0.0
        return self.averageOrderTotal

    def _summary(self) -> list:
        return [("Orders", len(self.orders)),
                ("Total revenue", self.totalRevenue),
                ("Units sold", self.unitSold),
                ("Average order total", self.averageOrderTotal)]

    def _details(self) -> tuple:
        units = {}
        for orderID, quantity in self.orderLines:
            units[orderID] = units.get(orderID, 0) + quantity
        header = ["Order", "Date", "Type", "Units", "Order total"]
        rows = [[o.orderID, o.orderDate.isoformat(), o.orderType,
                 units.get(o.orderID, 0), self.orderTotals[o.orderID]]
                for o in self.orders]
        return header, rows

    def _save_details(self, conn) -> None:
        conn.execute("INSERT INTO sales_reports VALUES (?, ?, ?, ?)",
                     (self.reportID, self.totalRevenue, self.unitSold, self.averageOrderTotal))
        conn.executemany("INSERT INTO sales_report_orders VALUES (?, ?)",
                         [(self.reportID, o.orderID) for o in self.orders])


@dataclass
class InventoryReport(Report):
    """A report comparing stock levels against minimum quantities."""
    itemsBelowMinimum: int = 0

    REPORT_NAME = "Inventory"

    def __post_init__(self):
        super().__post_init__()
        self.items: List[InventoryItem] = []   # InventoryReport "checks" InventoryItem
        self.belowMinimum = {}                 # itemID -> answer from isBelowMinimum
        self.stockLevels = []                  # (item, quantity, minimumQuantity, belowMinimum)
        self.lowStockItems: List[InventoryItem] = []
        self.restockRecommendations = []       # (item, quantity to order)
        self.lastUpdated = ""

    def retrieveRecords(self, startDate: date, endDate: date, storeID: int) -> bool:
        """Sequence diagram "Create Reports: Generate Inventory Report"."""
        self._set_period(startDate, endDate, storeID)
        rows = _rows("SELECT i.*, v.lastUpdated FROM inventory_items i "
                     "JOIN inventories v ON v.inventoryID = i.inventoryID "
                     "WHERE v.storeID = ? ORDER BY i.itemName", (storeID,))
        self.items = [InventoryItem(r["itemID"], r["itemName"], r["quantity"], r["minimumQuantity"])
                      for r in rows]
        self.lastUpdated = rows[0]["lastUpdated"] if rows else ""
        # loop [for each item in the store's inventory]
        for item in self.items:
            self.belowMinimum[item.itemID] = item.isBelowMinimum(item.itemID)
        if not self.items:
            return False
        self.compileStockLevels(storeID, self.items)
        self.identifyLowStockItems(self.stockLevels)
        self.generateRestockRecommendations(self.lowStockItems)
        self.generate(self.reportID)
        return True

    def compileStockLevels(self, storeID: int, inventoryItems: list) -> None:
        """Record each item's current quantity, its minimum and whether it is below it."""
        self.stockLevels = [(item, item.quantity, item.minimumQuantity, self.belowMinimum[item.itemID])
                            for item in inventoryItems]

    def identifyLowStockItems(self, stockLevels: list) -> list:
        self.lowStockItems = [item for item, _qty, _min, below in stockLevels if below]
        self.itemsBelowMinimum = len(self.lowStockItems)
        return self.lowStockItems

    def generateRestockRecommendations(self, lowStockItems: list) -> list:
        """Suggest how much to order so each low item is back at RESTOCK_TARGET x its minimum."""
        self.restockRecommendations = [(item, RESTOCK_TARGET * item.minimumQuantity - item.quantity)
                                       for item in lowStockItems]
        return self.restockRecommendations

    def _summary(self) -> list:
        return [("Items checked", len(self.items)),
                ("Items below minimum", self.itemsBelowMinimum),
                ("Stock last updated", self.lastUpdated)]

    def _details(self) -> tuple:
        to_order = {item.itemID: qty for item, qty in self.restockRecommendations}
        header = ["Item", "Quantity", "Minimum", "Status", "Order to restock"]
        rows = [[item.itemName, quantity, minimum, "LOW" if below else "OK",
                 to_order.get(item.itemID, "")]
                for item, quantity, minimum, below in self.stockLevels]
        return header, rows

    def _save_details(self, conn) -> None:
        conn.execute("INSERT INTO inventory_reports VALUES (?, ?)",
                     (self.reportID, self.itemsBelowMinimum))
        conn.executemany("INSERT INTO inventory_report_items VALUES (?, ?)",
                         [(self.reportID, item.itemID) for item in self.lowStockItems])


@dataclass
class CustomerLoyaltyReport(Report):
    """A report on customer loyalty, measured by repeat purchases."""
    registeredCustomers: int = 0
    repeatPurchases: int = 0

    REPORT_NAME = "Customer loyalty"

    def __post_init__(self):
        super().__post_init__()
        self.customers: List[Customer] = []   # CustomerLoyaltyReport "analyses" Customer
        self.orderHistory = []                # one list of orders per customer, from viewOrderHistory
        self.repeatCustomers: List[Customer] = []

    def retrieveRecords(self, startDate: date, endDate: date, storeID: int) -> bool:
        """Sequence diagram "Create Reports: Generate Customer Loyalty Report"."""
        self._set_period(startDate, endDate, storeID)
        rows = _rows("SELECT p.*, c.customerID FROM customers c "
                     "JOIN persons p ON p.personID = c.personID ORDER BY c.customerID")
        self.customers = [Customer(r["personID"], r["firstName"], r["lastName"], r["phone"],
                                   r["email"], r["customerID"]) for r in rows]
        # loop [for each registered customer]
        self.orderHistory = [customer.viewOrderHistory(customer.customerID)
                             for customer in self.customers]
        if not self.customers:
            return False
        self.compileLoyaltyData(storeID, startDate, endDate)
        self.identifyRepeatCustomers(self.orderHistory)
        self.generate(self.reportID)
        return True

    def compileLoyaltyData(self, storeID: int, startDate: date, endDate: date) -> None:
        """Keep, in each customer's order history, only the completed orders of this
        store and period."""
        in_scope = {row["orderID"] for row in self._completed_orders(storeID, startDate, endDate)}
        self.orderHistory = [[order for order in history if order.orderID in in_scope]
                             for history in self.orderHistory]
        self.registeredCustomers = len(self.customers)

    def identifyRepeatCustomers(self, orderHistory: list) -> list:
        """Customers with 2 or more orders in the period. Every order after their first
        one counts as a repeat purchase."""
        pairs = list(zip(self.customers, orderHistory))
        self.repeatCustomers = [customer for customer, orders in pairs if len(orders) >= 2]
        self.repeatPurchases = sum(len(orders) - 1 for _customer, orders in pairs if len(orders) >= 2)
        return self.repeatCustomers

    def _summary(self) -> list:
        ordering = sum(1 for orders in self.orderHistory if orders)
        return [("Registered customers", self.registeredCustomers),
                ("Customers who ordered", ordering),
                ("Repeat customers", len(self.repeatCustomers)),
                ("Repeat purchases", self.repeatPurchases)]

    def _details(self) -> tuple:
        header = ["Customer", "Orders", "Spent", "Repeat"]
        repeat_ids = {c.customerID for c in self.repeatCustomers}
        rows = [[customer.getFullName(), len(orders),
                 round(sum((o.orderTotal for o in orders), 0.0), 2),
                 "yes" if customer.customerID in repeat_ids else "no"]
                for customer, orders in zip(self.customers, self.orderHistory)]
        return header, rows

    def _save_details(self, conn) -> None:
        conn.execute("INSERT INTO customer_loyalty_reports VALUES (?, ?, ?)",
                     (self.reportID, self.registeredCustomers, self.repeatPurchases))
        conn.executemany("INSERT INTO loyalty_report_customers VALUES (?, ?)",
                         [(self.reportID, c.customerID) for c in self.customers])


# ---- module helpers -----------------------------------------------------------------------

def _rows(sql: str, params=()) -> list:
    """Run a read query and return all rows."""
    with closing(get_connection()) as conn:
        return conn.execute(sql, params).fetchall()


def _show(value) -> str:
    """Money values are floats; show them as dollars."""
    return f"${value:,.2f}" if isinstance(value, float) else str(value)


def _table(header: list, rows: list) -> List[str]:
    cells = [[str(h) for h in header]] + [[_show(v) for v in row] for row in rows]
    widths = [max(len(row[i]) for row in cells) + 2 for i in range(len(header))]
    return ["".join(cell.ljust(width) for cell, width in zip(row, widths)).rstrip()
            for row in cells]
