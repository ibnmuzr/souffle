"""People in the Soufflé system: Person (abstract), Customer, Employee, Manager.

Attributes and operations follow the final Milestone 4 class diagram.
"""
from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from datetime import date, time
from typing import List

from database.connection import get_connection
from .base import PLANNED
from .orders import Order, order_from_row


@dataclass
class Person:
    """«abstract» A person known to the system. Never created directly."""
    personID: int
    firstName: str
    lastName: str
    phone: str
    email: str

    def __post_init__(self):
        if type(self) is Person:
            raise TypeError("Person is abstract: create a Customer, Employee or Manager instead.")

    def getFullName(self) -> str:
        return f"{self.firstName} {self.lastName}"

    def updateContactInformation(self) -> None:
        raise NotImplementedError(PLANNED)


@dataclass
class Customer(Person):
    """A person who places, confirms and pays for an order.

    Associations: Customer "uses" OrderHandler; Customer "receives" Promotion;
    Customer Loyalty Report "analyses" Customer.
    """
    customerID: int

    def confirmOrder(self):
        raise NotImplementedError(PLANNED)

    def payOrder(self, orderID: str):
        raise NotImplementedError(PLANNED)

    def updateProfile(self):
        raise NotImplementedError(PLANNED)

    def sharePromotion(self, title: str, discountType: str, discountValue: int,
                       startDate: date, endDate: date) -> None:
        raise NotImplementedError(PLANNED)

    def viewOrderHistory(self, customerID: int) -> List[Order]:
        """Return the customer's orders, newest first.

        Called by the Customer Loyalty Report for each registered customer (sequence
        diagram: viewOrderHistory(customerID) -> orderHistory).
        """
        with closing(get_connection()) as conn:
            rows = conn.execute(
                "SELECT * FROM orders WHERE customerID = ? ORDER BY orderDate DESC, orderID DESC",
                (customerID,),
            ).fetchall()
        return [order_from_row(row) for row in rows]


@dataclass
class Employee(Person):
    """A staff member who logs in to enter, track and complete customer orders.

    Associations: Employee "has" EmployeeAccount; Employee "uses" OrderHandler.
    """
    employeeID: int
    registerUserName: str
    registerPassword: str
    employeeStatus: str
    hireDate: date

    def login(self, registerUserName: str, registerPassword: str):
        raise NotImplementedError(PLANNED)

    def notifyCancellation(self, orderID: str):
        raise NotImplementedError(PLANNED)

    def displayStatus(self, orderID: str):
        raise NotImplementedError(PLANNED)

    def displayWaitTime(self, orderID: str, estTime: time) -> time:
        raise NotImplementedError(PLANNED)

    def notifyOrderReady(self, orderID: str):
        raise NotImplementedError(PLANNED)

    def markOrderComplete(self, orderID: str):
        raise NotImplementedError(PLANNED)

    def logout(self):
        raise NotImplementedError(PLANNED)


@dataclass
class Manager(Person):
    """A staff member with higher authority (owners and hired managers).

    Associations: Manager "creates" EmployeeAccount; Manager "manages" InventoryUI;
    Manager "creates" Promotion; Manager "generates" Report.
    """
    managerID: int

    def requestReason(self, orderID: str):
        raise NotImplementedError(PLANNED)

    def createAccount(self, employeeID: int, employeeEmail: str, voidCheque: str,
                      accountPassword: str):
        raise NotImplementedError(PLANNED)

    def modifyAccount(self, accountID: int):
        raise NotImplementedError(PLANNED)

    def deleteAccount(self, accountID: int):
        raise NotImplementedError(PLANNED)

    def sharePromotion(self, title: str, discountType: str, discountValue: int,
                       startDate: date, endDate: date):
        raise NotImplementedError(PLANNED)
