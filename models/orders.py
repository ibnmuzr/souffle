"""Orders (Manage Orders use case): Order, OrderLine, MenuItem.

The OrderHandler controller is in order_handler.py and the Sales Database in
sales_database.py.

An order moves through the states of the Milestone 4 order state machine:

    In process -> Entered -> Ordered -> Sent -> In progress -> Ready -> Paid -> Completed
                                                               Ready -> Declined (payment not valid)
                                                            Declined -> Ready or Paid (pay again)
    any state before Completed -> Cancelled
"""
from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import List, Optional

from database.connection import get_connection

# ---- order states (Milestone 4 order state machine) ---------------------------------------
ORDER_STATES = ["In process", "Entered", "Ordered", "Sent", "In progress", "Ready", "Paid",
                "Completed"]
NEXT_STATE = dict(zip(ORDER_STATES[:-1], ORDER_STATES[1:]))
OTHER_MOVES = {("Ready", "Declined"), ("Declined", "Ready"), ("Declined", "Paid")}
NOT_STARTED = {"In process", "Entered", "Ordered", "Sent"}      # kitchen has not started
NEEDS_APPROVAL = {"In progress", "Ready", "Paid", "Declined"}   # cancelling needs a manager
FINAL_STATES = {"Completed", "Cancelled"}
ORDER_TYPES = ("in-store", "takeout", "online")

PREP_MINUTES = 10            # base preparation time of an order
PREP_MINUTES_PER_LINE = 5    # extra preparation time for each line
REMAKE_MINUTES = 15          # extra time when an item must be remade


def _status_key(status: str) -> str:
    """Statuses are compared without caring about upper or lower case."""
    return status.strip().lower()


def _same(a: str, b: str) -> bool:
    return _status_key(a) == _status_key(b)


def _in(status: str, group) -> bool:
    return _status_key(status) in {_status_key(s) for s in group}


@dataclass
class Order:
    """A customer's request for one or more menu items, tracked until it is completed.

    Associations (kept as references to the related rows): OrderHandler "handles" Order;
    Order "contains" OrderLine (the orderLine list); Order "paid by" Payment; Promotion
    "applies to" Order (promotionID); Sales Database "summarizes" Order; Sales Report
    "summarizes" Order.
    """
    orderID: str
    orderLine: List[OrderLine]
    orderDate: date
    orderType: str
    orderTotal: float
    orderStatus: str
    # Data-layer references (not attributes in the class diagram)
    customerID: Optional[int] = None     # NULL for a walk-in customer
    employeeID: Optional[int] = None     # the employee who entered the order
    storeID: Optional[int] = None        # the store where the order was placed
    promotionID: Optional[int] = None    # the promotion applied to the order, if any
    discountAmount: float = 0.0          # discount given by that promotion

    def __post_init__(self):
        self.cancellationReason = ""

    # ---- Create and Submit Order ------------------------------------------------------

    def createOrder(self, orderType: str) -> Order:
        """Create the order in the database with the "In process" state and return it."""
        if orderType not in ORDER_TYPES:
            raise ValueError(f"The order type must be one of: {', '.join(ORDER_TYPES)}.")
        if self.employeeID is None or self.storeID is None:
            raise ValueError("An order needs the employee and the store that create it.")
        self.orderType, self.orderDate = orderType, date.today()
        self.orderStatus, self.orderTotal, self.orderLine = "In process", 0.0, []
        with closing(get_connection()) as conn:
            conn.execute(
                "INSERT INTO orders (orderID, customerID, employeeID, storeID, promotionID, "
                "orderLine, orderDate, orderType, orderTotal, orderStatus, discountAmount) "
                "VALUES (?, ?, ?, ?, NULL, 0, ?, ?, 0, ?, 0)",
                (self.orderID, self.customerID, self.employeeID, self.storeID,
                 self.orderDate.isoformat(), orderType, self.orderStatus))
            conn.commit()
        return self

    def addItem(self, menuItemID: int, quantity: int = 1, specialInstructions: str = "") -> None:
        """Add a menu item to the order. The same item with the same instructions is added
        to its existing line; otherwise a new order line is created."""
        self._check_can_change()
        menuItem = load_menu_item(menuItemID)
        if not menuItem.checkAvailability(menuItemID, quantity):
            raise ValueError(f"{menuItem.name} is not available in that quantity.")
        for line in self.getOrderDetails():
            if (line.menuItem.menuItemID == menuItemID
                    and line.specialInstructions == specialInstructions):
                line.addLine(menuItemID, quantity, specialInstructions)
                break
        else:
            line = OrderLine(0, quantity, specialInstructions, 0.0, orderID=self.orderID)
            line.createOrderLine(menuItemID)
        self._refresh_total()

    def removeItem(self, menuItemID: int) -> None:
        """Remove every line of this menu item from the order."""
        self._check_can_change()
        for line in self.getOrderDetails():
            if line.menuItem.menuItemID == menuItemID:
                line.removeLine(line.orderLineID)
        self._refresh_total()

    def calculateTotal(self, orderID: str) -> float:
        """Add up the line totals, take off the promotion discount, store the result in
        orderTotal and return it (sequence diagrams: calculateTotal(orderID) -> total)."""
        self._check_id(orderID)
        with closing(get_connection()) as conn:
            subtotal = conn.execute(
                "SELECT COALESCE(SUM(lineTotal), 0) FROM order_lines WHERE orderID = ?",
                (orderID,)).fetchone()[0]
        self.orderTotal = round(max(subtotal - self.discountAmount, 0.0), 2)
        return self.orderTotal

    def calculateDiscount(self, orderID: str, orderTotal: float, promotionID: int) -> float:
        """Method specification 03 (Milestone 5): the discount a promotion gives on the
        order total. Invalid promotions return a discount of 0."""
        from .promotions import Promotion   # imported here to avoid a circular import
        self._check_id(orderID)
        if orderTotal <= 0:
            return 0.0
        promotion = Promotion.getPromotion(promotionID)
        if promotion is None or not promotion.isValid(promotionID):
            return 0.0
        discountType = promotion.getDiscountType(promotionID)
        discountValue = promotion.getDiscountValue(promotionID)
        if discountType == "percentage":
            discountAmount = orderTotal * discountValue / 100
        else:
            discountAmount = discountValue
        discountAmount = min(discountAmount, orderTotal)
        return round(discountAmount, 2)

    def sendToKitchen(self, orderID: str) -> time:
        """Send the order to the kitchen ("Ordered" -> "Sent") and return the estimated
        time it will be ready (sequence diagram: estPrepTime)."""
        self._check_id(orderID)
        if not self.getOrderDetails():
            raise ValueError("An order needs at least one item before it goes to the kitchen.")
        self.updateStatus(orderID, "Sent")
        minutes = PREP_MINUTES + PREP_MINUTES_PER_LINE * len(self.orderLine)
        return (datetime.now() + timedelta(minutes=minutes)).time().replace(second=0,
                                                                          microsecond=0)

    def getOrderDetails(self) -> List[OrderLine]:
        """Return the order's lines, each with its menu item (and keep them in orderLine)."""
        with closing(get_connection()) as conn:
            rows = conn.execute(
                "SELECT l.*, m.name, m.description, m.category, m.price, m.isAvailable "
                "FROM order_lines l JOIN menu_items m ON m.menuItemID = l.menuItemID "
                "WHERE l.orderID = ? ORDER BY l.orderLineID", (self.orderID,)).fetchall()
        self.orderLine = [
            OrderLine(r["orderLineID"], r["quantity"], r["specialInstructions"] or "",
                      r["lineTotal"], orderID=self.orderID,
                      menuItem=MenuItem(r["menuItemID"], r["name"], r["description"],
                                        r["category"], r["price"], bool(r["isAvailable"])))
            for r in rows]
        return self.orderLine

    # ---- Modify Order ---------------------------------------------------------------------

    def updateItems(self, changes: Optional[list] = None) -> None:
        """Apply the employee's changes (sequence diagram "Modify Order"):
            ("add", menuItemID, quantity[, instructions])  -> new or bigger line
            ("remove", orderLineID)                         -> OrderLine.removeLine
            ("modify", orderLineID, quantity)               -> OrderLine.updateLine
        then recalculate the total."""
        self._check_can_change()
        for change in changes or []:
            action = change[0]
            if action == "add":
                self.addItem(*change[1:])
                continue
            line = self._line(change[1])
            if action == "remove":
                line.removeLine(line.orderLineID)
            elif action == "modify":
                line.updateLine(line.orderLineID, change[2])
            else:
                raise ValueError(f"Unknown change: {action}.")
        self._refresh_total()

    def saveChanges(self) -> bool:
        """Save the order's total, number of lines and promotion (-> changesSaved)."""
        self.getOrderDetails()
        with closing(get_connection()) as conn:
            conn.execute(
                "UPDATE orders SET orderTotal = ?, orderLine = ?, promotionID = ?, "
                "discountAmount = ? WHERE orderID = ?",
                (self.orderTotal, len(self.orderLine), self.promotionID, self.discountAmount,
                 self.orderID))
            conn.commit()
        return True

    # ---- Cancel Order -----------------------------------------------------------------

    def cancel(self, reason: str = "") -> bool:
        """Set the order to "Cancelled" and keep the reason. False if it is already final."""
        if _in(self.getStatus(self.orderID), FINAL_STATES):
            return False
        self.updateStatus(self.orderID, "Cancelled")
        self.cancellationReason = reason
        return True

    # ---- states -----------------------------------------------------------------------

    def updateStatus(self, orderID: str, newStatus: Optional[str] = None) -> None:
        """Move the order to newStatus, or to its next state when no status is given.
        Only the moves of the order state machine are allowed."""
        self._check_id(orderID)
        current = self.getStatus(orderID)
        target = newStatus or NEXT_STATE.get(_canonical(current))
        if target is None:
            raise ValueError(f"Order {orderID} is {current}: it has no next state.")
        target = _canonical(target)
        allowed = (NEXT_STATE.get(_canonical(current)) == target
                   or (_canonical(current), target) in OTHER_MOVES
                   or (target == "Cancelled" and not _in(current, FINAL_STATES)))
        if not allowed:
            raise ValueError(f"Order {orderID} is {current}: it cannot become {target}.")
        with closing(get_connection()) as conn:
            conn.execute("UPDATE orders SET orderStatus = ? WHERE orderID = ?", (target, orderID))
            conn.commit()
        self.orderStatus = target

    def getStatus(self, orderID: str) -> str:
        """Read the order's current state from the database."""
        self._check_id(orderID)
        with closing(get_connection()) as conn:
            row = conn.execute("SELECT orderStatus FROM orders WHERE orderID = ?",
                               (orderID,)).fetchone()
        if row is None:
            raise ValueError(f"There is no order {orderID}.")
        self.orderStatus = row["orderStatus"]
        return self.orderStatus

    def updateWaitTime(self, estTime: Optional[time] = None) -> time:
        """An item must be remade: return the new estimated time the order will be ready
        (REMAKE_MINUTES after the old estimate, or after now if that has passed)."""
        now = datetime.now()
        start = now
        if estTime is not None:
            start = max(now, datetime.combine(now.date(), estTime))
        return (start + timedelta(minutes=REMAKE_MINUTES)).time().replace(second=0,
                                                                          microsecond=0)

    # ---- Process Payments -------------------------------------------------------------

    def confirmOrder(self, orderID: str, payment=None) -> bool:
        """Sequence diagrams "Pay by Card" and "Pay by Cash": create(total), then
        processPayment(paymentID). Approved: recordSale(orderID) and the order is "Paid".
        Declined: the order is "Declined" and can be paid again."""
        self._check_id(orderID)
        status = self.getStatus(orderID)
        if status not in ("Ready", "Declined"):
            raise ValueError(f"Order {orderID} is {status}: it can be paid once it is Ready.")
        if payment is None:
            raise ValueError("Choose how to pay: a CardPayment or a CashPayment.")
        if status == "Declined":
            self.updateStatus(orderID, "Ready")              # pay again
        payment.orderID = orderID
        payment.create(self.calculateTotal(orderID))
        approved = payment.processPayment(payment.paymentID)
        if approved:
            self.recordSale(orderID)
            self.updateStatus(orderID, "Paid")
        else:
            self.updateStatus(orderID, "Declined")
        return approved

    def recordSale(self, orderID: str) -> bool:
        """Record the order as a sale in the Sales Database."""
        from .sales_database import SalesDatabase
        self._check_id(orderID)
        SalesDatabase(1).recordOrder(orderID)
        return True

    # ---- helpers (not in the class diagram) ---------------------------------------------

    def _check_id(self, orderID: str) -> None:
        if orderID != self.orderID:
            raise ValueError(f"This is order {self.orderID}, not order {orderID}.")

    def _check_can_change(self) -> None:
        status = self.getStatus(self.orderID)
        if not _in(status, NOT_STARTED):
            raise ValueError(f"Order {self.orderID} is {status}: items can only change "
                             f"before the kitchen starts preparing it.")

    def _line(self, orderLineID: int) -> OrderLine:
        for line in self.getOrderDetails():
            if line.orderLineID == orderLineID:
                return line
        raise ValueError(f"Order {self.orderID} has no line {orderLineID}.")

    def _refresh_total(self) -> float:
        """Recalculate the promotion discount (the items changed) and the total."""
        self.discountAmount = 0.0
        subtotal = self.calculateTotal(self.orderID)
        if self.promotionID is not None:
            self.discountAmount = self.calculateDiscount(self.orderID, subtotal, self.promotionID)
        return self.calculateTotal(self.orderID)


def _canonical(status: str) -> str:
    """The state-machine spelling of a status ("completed" -> "Completed")."""
    for name in ORDER_STATES + ["Declined", "Cancelled"]:
        if _same(name, status):
            return name
    raise ValueError(f"Unknown order status: {status}.")


def order_from_row(row) -> Order:
    """Build an Order object from a row of the orders table."""
    return Order(row["orderID"], [], date.fromisoformat(row["orderDate"]), row["orderType"],
                 row["orderTotal"], row["orderStatus"], customerID=row["customerID"],
                 employeeID=row["employeeID"], storeID=row["storeID"],
                 promotionID=row["promotionID"], discountAmount=row["discountAmount"])


def load_order(orderID: str) -> Order:
    """The order with this ID, read from the database."""
    with closing(get_connection()) as conn:
        row = conn.execute("SELECT * FROM orders WHERE orderID = ?",
                           (orderID.strip().upper(),)).fetchone()
    if row is None:
        raise ValueError(f"There is no order {orderID}.")
    return order_from_row(row)


def next_order_id() -> str:
    """The ID the next new order gets (ORD-0001, ORD-0002, ...)."""
    with closing(get_connection()) as conn:
        row = conn.execute(
            "SELECT MAX(CAST(SUBSTR(orderID, 5) AS INTEGER)) FROM orders").fetchone()
    return f"ORD-{(row[0] or 0) + 1:04d}"


@dataclass
class OrderLine:
    """One line of an order: a menu item, its quantity and any special instructions.

    Associations: Order "contains" OrderLine (orderID); OrderLine "refers to" MenuItem
    (menuItem).
    """
    orderLineID: int
    quantity: int
    specialInstructions: str
    lineTotal: float
    orderID: str = ""                     # the order this line belongs to
    menuItem: Optional[MenuItem] = None   # the menu item of this line

    def createOrderLine(self, menuItemID: int) -> OrderLine:
        """Create this line for a menu item in the database and return it."""
        if self.quantity <= 0:
            raise ValueError("The quantity must be at least 1.")
        self.menuItem = load_menu_item(menuItemID)
        self.calculateLineTotal()
        with closing(get_connection()) as conn:
            cursor = conn.execute(
                "INSERT INTO order_lines (orderID, menuItemID, quantity, specialInstructions, "
                "lineTotal) VALUES (?, ?, ?, ?, ?)",
                (self.orderID, menuItemID, self.quantity, self.specialInstructions or None,
                 self.lineTotal))
            conn.commit()
        self.orderLineID = cursor.lastrowid
        return self

    def addLine(self, menuItemID: int, quantity: int, specialInstructions: str = "") -> None:
        """Add more of the same menu item to this line (and its instructions, if any)."""
        if self.menuItem is None or menuItemID != self.menuItem.menuItemID:
            raise ValueError(f"Line {self.orderLineID} is not for menu item {menuItemID}.")
        if specialInstructions and specialInstructions != self.specialInstructions:
            self.specialInstructions = specialInstructions
            with closing(get_connection()) as conn:
                conn.execute("UPDATE order_lines SET specialInstructions = ? WHERE orderLineID = ?",
                             (specialInstructions, self.orderLineID))
                conn.commit()
        self.updateLine(self.orderLineID, self.quantity + quantity)

    def removeLine(self, orderLineID: int) -> None:
        """Delete this line from the order."""
        self._check_id(orderLineID)
        with closing(get_connection()) as conn:
            conn.execute("DELETE FROM order_lines WHERE orderLineID = ?", (orderLineID,))
            conn.commit()

    def updateLine(self, orderLineID: int, quantity: int) -> None:
        """Change the quantity of this line and save it."""
        self._check_id(orderLineID)
        if not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("The quantity must be a whole number of at least 1.")
        self.quantity = quantity
        self.calculateLineTotal()
        with closing(get_connection()) as conn:
            conn.execute("UPDATE order_lines SET quantity = ?, lineTotal = ? WHERE orderLineID = ?",
                         (self.quantity, self.lineTotal, orderLineID))
            conn.commit()

    def calculateLineTotal(self) -> float:
        """Quantity x the menu item's price."""
        self.lineTotal = round(self.quantity * self.menuItem.price, 2)
        return self.lineTotal

    def _check_id(self, orderLineID: int) -> None:
        if orderLineID != self.orderLineID:
            raise ValueError(f"This is line {self.orderLineID}, not line {orderLineID}.")


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
    imageURL: Optional[str] = None

    def checkAvailability(self, menuItemID: int, quantity: int) -> bool:
        """True when this item is on sale and the requested quantity is valid."""
        if menuItemID != self.menuItemID:
            raise ValueError(f"checkAvailability was called with item {menuItemID} "
                             f"on item {self.menuItemID}.")
        return self.isAvailable and isinstance(quantity, int) and quantity > 0

    def updatePrice(self, newPrice: float) -> None:
        """Change the item's price (orders already placed keep their old line totals)."""
        if newPrice < 0:
            raise ValueError("A price cannot be negative.")
        self.price = round(float(newPrice), 2)
        with closing(get_connection()) as conn:
            conn.execute("UPDATE menu_items SET price = ? WHERE menuItemID = ?",
                         (self.price, self.menuItemID))
            conn.commit()


def load_menu_item(menuItemID: int) -> MenuItem:
    """The menu item with this ID, read from the database."""
    with closing(get_connection()) as conn:
        r = conn.execute("SELECT * FROM menu_items WHERE menuItemID = ?", (menuItemID,)).fetchone()
    if r is None:
        raise ValueError(f"There is no menu item {menuItemID}.")
    return MenuItem(r["menuItemID"], r["name"], r["description"], r["category"], r["price"],
                    bool(r["isAvailable"]), r["imageURL"] if "imageURL" in r.keys() else None)


def load_menu() -> List[MenuItem]:
    """Every menu item, in menu order."""
    with closing(get_connection()) as conn:
        rows = conn.execute("SELECT menuItemID FROM menu_items ORDER BY menuItemID").fetchall()
    return [load_menu_item(r["menuItemID"]) for r in rows]
