"""People in the Soufflé system: Person (abstract), Customer, Employee, Manager.

Attributes and operations follow the team class diagram (Milestone 3) exactly.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date


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
        raise NotImplementedError("Planned for a later prototype.")


@dataclass
class Customer(Person):
    """A person who places, confirms and pays for an order."""
    customerID: int

    def placeOrder(self):
        raise NotImplementedError("Planned for a later prototype.")

    def confirmOrder(self):
        raise NotImplementedError("Planned for a later prototype.")

    def payOrder(self):
        raise NotImplementedError("Planned for a later prototype.")

    def viewOrderHistory(self):
        raise NotImplementedError("Planned for a later prototype.")

    def redeemPoints(self):
        raise NotImplementedError("Planned for a later prototype.")

    def updateProfile(self):
        raise NotImplementedError("Planned for a later prototype.")


@dataclass
class Employee(Person):
    """A staff member who logs in to enter, modify and complete customer orders."""
    employeeID: int
    registerUserName: str
    registerPassword: str
    employeeStatus: str
    hireDate: date

    def login(self):
        raise NotImplementedError("Planned for a later prototype.")

    def enterOrder(self):
        raise NotImplementedError("Planned for a later prototype.")

    def modifyOrder(self):
        raise NotImplementedError("Planned for a later prototype.")

    def markOrderComplete(self, orderID):
        raise NotImplementedError("Planned for a later prototype.")

    def viewSchedule(self):
        raise NotImplementedError("Planned for a later prototype.")

    def logout(self):
        raise NotImplementedError("Planned for a later prototype.")


@dataclass
class Manager(Person):
    """A staff member with higher authority (owners and hired managers)."""
    managerID: int

    def approveCancellation(self):
        raise NotImplementedError("Planned for a later prototype.")

    def createPromotion(self):
        raise NotImplementedError("Planned for a later prototype.")

    def sharePromotion(self):
        raise NotImplementedError("Planned for a later prototype.")

    def savePromotion(self):
        raise NotImplementedError("Planned for a later prototype.")

    def deletePromotion(self):
        raise NotImplementedError("Planned for a later prototype.")

    def modifyPromotion(self):
        raise NotImplementedError("Planned for a later prototype.")

    def generateReport(self):
        raise NotImplementedError("Planned for a later prototype.")

    def manageInventory(self):
        raise NotImplementedError("Planned for a later prototype.")
