"""Payments (Process Payments use case): Payment (abstract), CardPayment, CashPayment, Receipt."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass
class Payment:
    """«abstract» A payment toward an order. Every payment is a card or cash payment."""
    paymentID: int
    amount: float
    method: str
    paymentDate: date
    status: str

    def __post_init__(self):
        if type(self) is Payment:
            raise TypeError("Payment is abstract: create a CardPayment or CashPayment instead.")

    def processPayment(self):
        raise NotImplementedError("Planned for a later prototype.")

    def validatePayment(self) -> bool:
        return self.amount > 0

    def refundPayment(self) -> bool:
        raise NotImplementedError("Planned for a later prototype.")


@dataclass
class CardPayment(Payment):
    """A payment made by card through the Clover terminal."""
    cardType: str
    authorizationCode: str

    def authorizeCard(self) -> bool:
        raise NotImplementedError("Planned for a later prototype.")


@dataclass
class CashPayment(Payment):
    """A payment made in cash."""
    cashReceived: float
    changeDue: float

    def calculateChange(self) -> float:
        self.changeDue = round(self.cashReceived - self.amount, 2)
        return self.changeDue


@dataclass
class Receipt:
    """Proof of payment given to the customer."""
    receiptNumber: str
    totalPaid: float
    date: date

    def generateReceipt(self):
        raise NotImplementedError("Planned for a later prototype.")

    def emailReceipt(self):
        raise NotImplementedError("Planned for a later prototype.")

    def printReceipt(self) -> None:
        raise NotImplementedError("Planned for a later prototype.")
