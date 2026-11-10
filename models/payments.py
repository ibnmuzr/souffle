"""Payments (Process Payments use case): Payment (abstract), CardPayment, CashPayment, Receipt."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .base import PLANNED


@dataclass
class Payment:
    """«abstract» A payment toward an order. Every payment is a card or cash payment.

    Associations: Order "paid by" Payment; Payment "generates" Receipt.
    """
    paymentID: int
    amount: float
    method: str
    paymentDate: date
    status: str

    def __post_init__(self):
        if type(self) is Payment:
            raise TypeError("Payment is abstract: create a CardPayment or CashPayment instead.")

    def create(self, total: float):
        raise NotImplementedError(PLANNED)

    def processPayment(self, paymentID: int):
        raise NotImplementedError(PLANNED)

    def validatePayment(self, paymentID: int) -> bool:
        """True when this is the right payment and its amount is positive."""
        return paymentID == self.paymentID and self.amount > 0

    def refundPayment(self, paymentID: int) -> bool:
        raise NotImplementedError(PLANNED)


@dataclass
class CardPayment(Payment):
    """A payment made by debit or credit card through the Clover terminal."""
    cardType: str
    authorizationCode: str

    def authorizeCard(self) -> bool:
        raise NotImplementedError(PLANNED)


@dataclass
class CashPayment(Payment):
    """A payment made in cash. Records the cash received and the change owed."""
    cashReceived: float
    changeDue: float

    def calculateChange(self) -> float:
        self.changeDue = round(self.cashReceived - self.amount, 2)
        return self.changeDue


@dataclass
class Receipt:
    """Proof of a completed payment, given to the customer once the order is paid."""
    receiptNumber: str
    totalPaid: float
    date: date

    def generateReceipt(self, orderID: str, paymentID: int):
        raise NotImplementedError(PLANNED)

    def printReceipt(self, orderID: str, paymentID: int) -> None:
        raise NotImplementedError(PLANNED)
