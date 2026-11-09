"""Orders (Manage Orders use case): Order, OrderLine, MenuItem."""
from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from datetime import date

from database.connection import get_connection


@dataclass
class Order:
    """A customer's request for one or more menu items, tracked until completed."""
    orderID: str
    orderLine: int
    orderDate: date
    orderType: str
    orderTotal: float
    orderStatus: str
    confirmationNumber: int

    def addItem(self):
        raise NotImplementedError("Planned for a later prototype.")

    def removeItem(self):
        raise NotImplementedError("Planned for a later prototype.")

    def calculateTotal(self, orderID: str) -> float:
        """Add up the line totals of the order, store the result in orderTotal and return it.

        Called by the Sales Report for each order in the period (sequence diagram:
        calculateTotal(orderID) -> orderTotal).
        """
        with closing(get_connection()) as conn:
            total = conn.execute(
                "SELECT COALESCE(SUM(lineTotal), 0) FROM order_lines WHERE orderID = ?",
                (orderID,),
            ).fetchone()[0]
        self.orderTotal = round(total, 2)
        return self.orderTotal

    def sendToKitchen(self):
        raise NotImplementedError("Planned for a later prototype.")

    def updateStatus(self):
        raise NotImplementedError("Planned for a later prototype.")

    def recordSale(self):
        raise NotImplementedError("Planned for a later prototype.")

    def cancelOrder(self):
        raise NotImplementedError("Planned for a later prototype.")

    def confirmOrder(self):
        raise NotImplementedError("Planned for a later prototype.")

    def estimateReadyTime(self):
        raise NotImplementedError("Planned for a later prototype.")


def order_from_row(row) -> Order:
    """Build an Order object from a row of the orders table."""
    return Order(row["orderID"], row["orderLine"], date.fromisoformat(row["orderDate"]),
                 row["orderType"], row["orderTotal"], row["orderStatus"],
                 row["confirmationNumber"])


@dataclass
class OrderLine:
    """One line of an order: a menu item and its quantity."""
    orderLineID: int
    quantity: int
    specialInstructions: str
    lineTotal: float

    def calculateLineTotal(self):
        raise NotImplementedError("Planned for a later prototype.")

    def updateQuantity(self):
        raise NotImplementedError("Planned for a later prototype.")

    def addSpecialInstructions(self):
        raise NotImplementedError("Planned for a later prototype.")


@dataclass
class MenuItem:
    """A product on Soufflé's menu."""
    itemID: int
    name: str
    description: str
    category: str
    price: float
    isAvailable: bool

    def checkAvailability(self) -> bool:
        return self.isAvailable

    def updatePrice(self):
        raise NotImplementedError("Planned for a later prototype.")

    def setAvailability(self):
        raise NotImplementedError("Planned for a later prototype.")
