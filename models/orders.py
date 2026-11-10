"""Orders (Manage Orders use case): Order, OrderLine, MenuItem.

The OrderHandler controller is in order_handler.py and the Sales Database in
sales_database.py.
"""
from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from datetime import date

from database.connection import get_connection
from .base import PLANNED


@dataclass
class Order:
    """A customer's request for one or more menu items, tracked until it is completed.

    Associations: OrderHandler "handles" Order; Order "contains" OrderLine (aggregation);
    Order "paid by" Payment; Promotion "applies to" Order; Sales Database "summarizes"
    Order; Sales Report "summarizes" Order.
    """
    orderID: str
    orderLine: int
    orderDate: date
    orderType: str
    orderTotal: float
    orderStatus: str

    def createOrder(self, orderType: str):
        raise NotImplementedError(PLANNED)

    def addItem(self, menuItemID: int):
        raise NotImplementedError(PLANNED)

    def removeItem(self, orderID: str):
        raise NotImplementedError(PLANNED)

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

    def calculateDiscount(self, orderID: str, orderTotal: float, promotionID: int) -> float:
        """Return the discount a promotion gives on this order total.

        A percentage promotion takes discountValue % off; a fixed promotion takes
        discountValue dollars off, never more than the total itself.
        """
        with closing(get_connection()) as conn:
            promo = conn.execute(
                "SELECT discountType, discountValue FROM promotions WHERE promotionID = ?",
                (promotionID,),
            ).fetchone()
        if promo is None:
            raise ValueError(f"There is no promotion with ID {promotionID}.")
        if promo["discountType"] == "percentage":
            return round(orderTotal * promo["discountValue"] / 100, 2)
        return round(min(float(promo["discountValue"]), orderTotal), 2)

    def sendToKitchen(self, orderID: str):
        raise NotImplementedError(PLANNED)

    def getOrderDetails(self):
        raise NotImplementedError(PLANNED)

    def updateItems(self):
        raise NotImplementedError(PLANNED)

    def saveChanges(self):
        raise NotImplementedError(PLANNED)

    def cancel(self):
        raise NotImplementedError(PLANNED)

    def updateStatus(self, orderID: str):
        raise NotImplementedError(PLANNED)

    def updateWaitTime(self):
        raise NotImplementedError(PLANNED)

    def recordSale(self, orderID: str):
        raise NotImplementedError(PLANNED)

    def confirmOrder(self, orderID: str):
        raise NotImplementedError(PLANNED)


def order_from_row(row) -> Order:
    """Build an Order object from a row of the orders table."""
    return Order(row["orderID"], row["orderLine"], date.fromisoformat(row["orderDate"]),
                 row["orderType"], row["orderTotal"], row["orderStatus"])


@dataclass
class OrderLine:
    """One line of an order: a menu item, its quantity and any special instructions.

    Associations: Order "contains" OrderLine; OrderLine "refers to" MenuItem.
    """
    orderLineID: int
    quantity: int
    specialInstructions: str
    lineTotal: float

    def createOrderLine(self, menuItemID: int):
        raise NotImplementedError(PLANNED)

    def addLine(self, menuItemID: int, quantity: int):
        raise NotImplementedError(PLANNED)

    def removeLine(self, orderLineID: int):
        raise NotImplementedError(PLANNED)

    def updateLine(self, orderLineID: int, quantity: int):
        raise NotImplementedError(PLANNED)

    def calculateLineTotal(self):
        raise NotImplementedError(PLANNED)


@dataclass
class MenuItem:
    """A product on Soufflé's menu (prices from Soufflé's Clover item list).

    Associations: OrderLine "refers to" MenuItem; MenuItem is linked to InventoryItem.
    """
    menuItemID: int
    name: str
    description: str
    category: str
    price: float
    isAvailable: bool

    def checkAvailability(self, menuItemID: int, quantity: int) -> bool:
        """True when this item is on sale and the requested quantity is valid."""
        if menuItemID != self.menuItemID:
            raise ValueError(f"checkAvailability was called with item {menuItemID} "
                             f"on item {self.menuItemID}.")
        return self.isAvailable and quantity > 0

    def updatePrice(self):
        raise NotImplementedError(PLANNED)
