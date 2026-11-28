"""OrderHandler: the controller that runs the Manage Orders sequence diagrams.

The customer and the employee "use" the OrderHandler, and it "handles" the Order
objects. Its attributes describe the order it is working on right now, so they live in
memory while the app runs and are not stored in their own table.

Sequence diagrams (Milestone 4, Manage Orders; approveCancellation follows the
Milestone 5 method specification 02):
    Create and Submit Order   startOrder -> loop [each item] checkAvailability, addItem
                              -> reviewOrder -> submitOrder
    Modify Order              selectOrder -> modifyOrder -> confirmChanges
    Cancel Order              cancelOrder -> enterReason -> approveCancellation (if started)
    Track and Complete Order  startPreparation -> requestRemake (opt) -> markReady
                              -> Process Payments -> markOrderComplete
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from typing import Optional

from .orders import (NEEDS_APPROVAL, NOT_STARTED, FINAL_STATES, Order, _in, load_order,
                     next_order_id)
from .sales_database import SalesDatabase


@dataclass
class OrderHandler:
    """«controller» Coordinates creating, modifying, cancelling, tracking and completing
    an order."""
    estTime: Optional[time] = None
    # Associations from the class diagram: Customer and Employee "use" OrderHandler;
    # OrderHandler "handles" Order
    customer: Optional[object] = None     # Customer placing the order (None = walk-in)
    employee: Optional[object] = None     # Employee using the screen
    order: Optional[Order] = None         # the order being worked on
    storeID: int = 1                      # data layer: the store where the app runs

    def __post_init__(self):
        self.pendingReason = ""           # cancellation reason waiting for approval

    # ---- Create and Submit Order ------------------------------------------------------

    def startOrder(self, orderType: str) -> Order:
        """anOrder := createOrder(orderType)"""
        order = Order(next_order_id(), [], None, orderType, 0.0, "",
                      customerID=getattr(self.customer, "customerID", None),
                      employeeID=getattr(self.employee, "employeeID", 1),
                      storeID=self.storeID)
        self.order = order.createOrder(orderType)
        return self.order

    def reviewOrder(self, orderID: str) -> Order:
        """total := calculateTotal(orderID); the order moves to "Entered" (-> orderSummary, total)."""
        order = self._order(orderID)
        order.calculateTotal(orderID)
        if order.getStatus(orderID) == "In process":
            order.updateStatus(orderID)            # In process -> Entered
        order.saveChanges()
        order.getOrderDetails()
        return order

    def submitOrder(self, orderID: str) -> bool:
        """estPrepTime := sendToKitchen(orderID): "Entered" -> "Ordered" -> "Sent"."""
        order = self._order(orderID)
        status = order.getStatus(orderID)
        if status not in ("In process", "Entered"):
            raise ValueError(f"Order {orderID} is {status}: it was already submitted.")
        if status == "In process":
            self.reviewOrder(orderID)
        order.updateStatus(orderID)                # Entered -> Ordered
        self.estTime = order.sendToKitchen(orderID)
        return True

    # ---- promotions (Manage Promotions sequence diagram, Milestone 5 appendix) ---------

    def applyPromotion(self, promotionID: int) -> float:
        """Apply a promotion to the current order: DiscountAmount := calculateDiscount(
        orderID, orderTotal, promotionID). An invalid promotion gives 0 and is not kept."""
        order = self.order
        order.promotionID, order.discountAmount = None, 0.0
        subtotal = order.calculateTotal(order.orderID)
        discount = order.calculateDiscount(order.orderID, subtotal, promotionID)
        if discount > 0:
            order.promotionID, order.discountAmount = promotionID, discount
        order.calculateTotal(order.orderID)
        order.saveChanges()
        return discount

    # ---- Modify Order -----------------------------------------------------------------

    def selectOrder(self, orderID: str) -> Order:
        """orderDetails := getOrderDetails()"""
        self.order = load_order(orderID)
        self.order.getOrderDetails()
        return self.order

    def modifyOrder(self, orderID: str, changes: Optional[list] = None) -> None:
        """updateItems(changes): add, remove or modify lines, then total := calculateTotal."""
        self._order(orderID).updateItems(changes)

    def confirmChanges(self, orderID: str) -> bool:
        """saveChanges() -> changesSaved"""
        return self._order(orderID).saveChanges()

    # ---- Cancel Order -----------------------------------------------------------------

    def cancelOrder(self, orderID: str) -> bool:
        """Cancel an order. An order the kitchen has not started is cancelled right away
        (no manager needed). Returns False when the kitchen has started: a manager must
        then approve with approveCancellation."""
        order = self.selectOrder(orderID)
        status = order.getStatus(orderID)
        if _in(status, FINAL_STATES):
            raise ValueError(f"Order {orderID} is {status}: it cannot be cancelled.")
        if not _in(status, NOT_STARTED):
            return False
        from .payments import payment_of_order
        payment = payment_of_order(orderID)
        if payment is not None and not payment.refundPayment(payment.paymentID):
            return False
        reason = self.pendingReason or "Cancelled before preparation"
        order.cancel(reason)
        self._kitchen(order).notifyCancellation(orderID)
        SalesDatabase(1).logCancellation(orderID, reason, None)
        self.pendingReason = ""
        return True

    def enterReason(self, reason: str) -> str:
        """Keep the reason for the cancellation until it is approved."""
        if not reason.strip():
            raise ValueError("Please enter a reason for the cancellation.")
        self.pendingReason = reason.strip()
        return self.pendingReason

    def approveCancellation(self, orderID: str, managerID: int, accountPassword: str) -> bool:
        """Method specification 02 (Milestone 5). True if the cancellation was approved and
        done; False if it was refused (nothing changes)."""
        from .accounts import account_of_manager
        from .payments import payment_of_order
        account = account_of_manager(managerID)                       # 1-3
        if account is None or not account.verifyAccountPassword(accountPassword):
            return False
        try:
            order = load_order(orderID)                                # 4
        except ValueError:
            return False
        status = order.getStatus(orderID)                              # 5
        if not _in(status, NEEDS_APPROVAL) or not self.pendingReason:  # 6
            return False
        payment = payment_of_order(orderID)                            # 7
        if status == "Paid" and payment is None:
            return False
        if payment is not None and not payment.refundPayment(payment.paymentID):
            return False
        order.cancel(self.pendingReason)                               # 8
        self._kitchen(order).notifyCancellation(orderID)               # 9
        SalesDatabase(1).logCancellation(orderID, self.pendingReason, managerID)   # 10
        self.pendingReason = ""
        self.order = order
        return True                                                    # 11

    # ---- Track and Complete Order -----------------------------------------------------

    def startPreparation(self, orderID: str) -> None:
        """updateStatus("In progress"), then displayStatus(orderID) to the employee."""
        order = self._order(orderID)
        order.updateStatus(orderID, "In progress")
        self._kitchen(order).displayStatus(orderID)

    def requestRemake(self, orderID: str, orderLineID: int) -> bool:
        """An item must be remade: updateWaitTime(), then displayWaitTime(orderID, newEstTime)."""
        order = self._order(orderID)
        if order.getStatus(orderID) != "In progress":
            raise ValueError(f"Order {orderID} is not being prepared.")
        order._line(orderLineID)                   # the line must belong to the order
        self.estTime = order.updateWaitTime(self.estTime)
        self._kitchen(order).displayWaitTime(orderID, self.estTime)
        return True

    def markReady(self, orderID: str) -> None:
        """updateStatus("Ready"), then notifyOrderReady(orderID)."""
        order = self._order(orderID)
        order.updateStatus(orderID, "Ready")
        from .payments import payment_of_order
        if payment_of_order(orderID) is not None:
            order.updateStatus(orderID, "Paid")
        self._kitchen(order).notifyOrderReady(orderID)

    def markOrderComplete(self, orderID: str) -> None:
        """After Process Payments: updateStatus("Completed"), then recordOrder(orderDetails)."""
        order = self._order(orderID)
        order.updateStatus(orderID, "Completed")   # only allowed once the order is Paid
        SalesDatabase(1).recordOrder(orderID)

    # ---- helpers (not in the class diagram) ---------------------------------------------

    def _order(self, orderID: str) -> Order:
        """The order being worked on, or the one with this ID."""
        if self.order is None or self.order.orderID != orderID.strip().upper():
            self.order = load_order(orderID)
        return self.order

    def _kitchen(self, order: Order):
        """The kitchen staff screen that gets the order's notifications."""
        from .people import load_employee
        if self.employee is not None:
            return self.employee
        return load_employee(order.employeeID or 1)
