"""OrderHandler: the controller that runs the Manage Orders sequence diagrams.

The customer and the employee "use" the OrderHandler, and it "handles" the Order
objects. Its attributes describe the order it is working on right now, so they live in
memory while the app runs and are not stored in their own table.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from typing import Optional

from .base import PLANNED


@dataclass
class OrderHandler:
    """«controller» Coordinates creating, modifying, cancelling, tracking and completing
    an order."""
    orderID: str = ""
    orderType: str = ""
    orderStatus: str = ""
    estTime: Optional[time] = None

    def startOrder(self, orderType: str):
        raise NotImplementedError(PLANNED)

    def reviewOrder(self, orderID: str):
        raise NotImplementedError(PLANNED)

    def submitOrder(self, orderID: str):
        raise NotImplementedError(PLANNED)

    def selectOrder(self, orderID: str):
        raise NotImplementedError(PLANNED)

    def modifyOrder(self, orderID: str):
        raise NotImplementedError(PLANNED)

    def confirmChanges(self, orderID: str):
        raise NotImplementedError(PLANNED)

    def cancelOrder(self, orderID: str):
        raise NotImplementedError(PLANNED)

    def enterReason(self):
        raise NotImplementedError(PLANNED)

    def approveCancellation(self, managerID: int):
        raise NotImplementedError(PLANNED)

    def startPreparation(self, orderID: str):
        raise NotImplementedError(PLANNED)

    def requestRemake(self, orderID: str, orderLineID: int):
        raise NotImplementedError(PLANNED)

    def markReady(self, orderID: str):
        raise NotImplementedError(PLANNED)

    def markOrderComplete(self, orderID: str):
        raise NotImplementedError(PLANNED)
