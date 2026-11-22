"""Payments (Process Payments use case): Payment (base class), CardPayment, CashPayment, Receipt.

processPayment follows the Milestone 5 method specification 01:
    card: authorized := authorizeCard(); [authorized] valid := validatePayment(paymentID)
    cash: valid := validatePayment(paymentID); [valid] changeDue := calculateChange(total, cashReceived)
    [valid] generateReceipt(orderID, paymentID), printReceipt(orderID, paymentID): "Approved", True
    [not valid] "Declined", False (no receipt)
"""
from __future__ import annotations

import random
from contextlib import closing
from dataclasses import dataclass
from datetime import date
from typing import Optional

from database.connection import get_connection

ACCEPTED_CARD_TYPES = ("debit", "credit")   # other cards are declined by the terminal
CARD_LIMIT = 300.00                         # simulated: card payments above this are declined


@dataclass
class Payment:
    """A payment toward an order. Every payment is a CardPayment or a CashPayment (in the
    Milestone 5 implementation class diagram each child shows these attributes itself).

    Associations: Order "paid by" Payment (orderID); Payment "generates" Receipt.
    """
    paymentID: int
    amount: float
    method: str
    paymentDate: date
    status: str

    def __post_init__(self):
        if type(self) is Payment:
            raise TypeError("Create a CardPayment or a CashPayment.")
        self.orderID = ""                        # the order this payment pays
        self.receipt: Optional[Receipt] = None   # the receipt, once approved

    def create(self, total: float) -> Payment:
        """Create the payment for the order total, with the "Pending" status."""
        if total <= 0:
            raise ValueError("The amount to pay must be more than $0.")
        self.amount, self.paymentDate, self.status = round(total, 2), date.today(), "Pending"
        with closing(get_connection()) as conn:
            cursor = conn.execute(
                "INSERT INTO payments (orderID, amount, method, paymentDate, status) "
                "VALUES (?, ?, ?, ?, ?)",
                (self.orderID, self.amount, self.method, self.paymentDate.isoformat(),
                 self.status))
            self.paymentID = cursor.lastrowid
            self._save_details(conn)
            conn.commit()
        return self

    def processPayment(self, paymentID: int) -> bool:
        """Method specification 01: True ("Approved") or False ("Declined")."""
        valid = self._check(paymentID)
        self.status = "Approved" if valid else "Declined"
        with closing(get_connection()) as conn:
            conn.execute("UPDATE payments SET status = ? WHERE paymentID = ?",
                         (self.status, paymentID))
            self._save_details(conn)
            conn.commit()
        if valid:
            self.receipt = Receipt("", 0.0, date.today()).generateReceipt(self.orderID, paymentID)
            self.receipt.printReceipt(self.orderID, paymentID)
        return valid

    def validatePayment(self, paymentID: int) -> bool:
        """True when this is the right, pending payment and its amount is positive."""
        return (paymentID == self.paymentID and self.amount > 0
                and self.status.lower() == "pending")

    def refundPayment(self, paymentID: int) -> bool:
        """Give the money back for an approved payment. False if it was not approved."""
        if paymentID != self.paymentID or self.status.lower() != "approved":
            return False
        self.status = "Refunded"
        with closing(get_connection()) as conn:
            conn.execute("UPDATE payments SET status = ? WHERE paymentID = ?",
                         (self.status, paymentID))
            conn.commit()
        return True

    def _check(self, paymentID: int) -> bool:
        """The card or cash steps of processPayment (see the subclasses)."""
        raise NotImplementedError

    def _save_details(self, conn) -> None:
        """Insert or update the card_payments or cash_payments row."""
        raise NotImplementedError


@dataclass
class CardPayment(Payment):
    """A payment made by debit or credit card through the Clover terminal."""
    cardType: str
    authorizationCode: str

    def __post_init__(self):
        super().__post_init__()
        self.method = "card"

    def create(self, total: float) -> CardPayment:
        return super().create(total)

    def authorizeCard(self) -> bool:
        """Simulated card terminal: debit and credit cards are authorized up to CARD_LIMIT;
        other cards, or bigger amounts, are declined."""
        authorized = (self.cardType.strip().lower() in ACCEPTED_CARD_TYPES
                      and self.amount <= CARD_LIMIT)
        self.authorizationCode = f"AUTH-{random.randint(10000, 99999)}" if authorized else ""
        return authorized

    def _check(self, paymentID: int) -> bool:
        authorized = self.authorizeCard()
        return authorized and self.validatePayment(paymentID)

    def _save_details(self, conn) -> None:
        conn.execute("INSERT OR REPLACE INTO card_payments VALUES (?, ?, ?)",
                     (self.paymentID, self.cardType, self.authorizationCode or None))


@dataclass
class CashPayment(Payment):
    """A payment made in cash. Records the cash received and the change owed."""
    cashReceived: float
    changeDue: float

    def __post_init__(self):
        super().__post_init__()
        self.method = "cash"

    def create(self, total: float) -> CashPayment:
        return super().create(total)

    def validatePayment(self, paymentID: int) -> bool:
        """A cash payment is also valid only if the cash received covers the amount."""
        return super().validatePayment(paymentID) and self.cashReceived >= self.amount

    def calculateChange(self, total: float, cashReceived: float) -> float:
        """Change to give back: cash received - total."""
        self.changeDue = round(cashReceived - total, 2)
        return self.changeDue

    def _check(self, paymentID: int) -> bool:
        valid = self.validatePayment(paymentID)
        if valid:
            self.calculateChange(self.amount, self.cashReceived)
        return valid

    def _save_details(self, conn) -> None:
        conn.execute("INSERT OR REPLACE INTO cash_payments VALUES (?, ?, ?)",
                     (self.paymentID, self.cashReceived, self.changeDue))


@dataclass
class Receipt:
    """Proof of a completed payment, given to the customer once the order is paid."""
    receiptNumber: str
    totalPaid: float
    date: date

    def generateReceipt(self, orderID: str, paymentID: int) -> Receipt:
        """Create the receipt of an approved payment and return it."""
        with closing(get_connection()) as conn:
            paid = conn.execute("SELECT amount FROM payments WHERE paymentID = ? AND orderID = ?",
                                (paymentID, orderID)).fetchone()
            if paid is None:
                raise ValueError(f"Payment {paymentID} is not a payment of order {orderID}.")
            last = conn.execute("SELECT MAX(CAST(SUBSTR(receiptNumber, 3) AS INTEGER)) "
                                "FROM receipts").fetchone()[0] or 0
            self.receiptNumber, self.totalPaid = f"R-{last + 1:04d}", paid["amount"]
            conn.execute("INSERT INTO receipts VALUES (?, ?, ?, ?)",
                         (self.receiptNumber, paymentID, self.totalPaid, self.date.isoformat()))
            conn.commit()
        return self

    def printReceipt(self, orderID: str, paymentID: int) -> None:
        """Print the receipt: the order's lines, the total paid and how it was paid."""
        from .orders import load_order
        order = load_order(orderID)
        with closing(get_connection()) as conn:
            pay = conn.execute(
                "SELECT p.method, c.cardType, h.cashReceived, h.changeDue FROM payments p "
                "LEFT JOIN card_payments c ON c.paymentID = p.paymentID "
                "LEFT JOIN cash_payments h ON h.paymentID = p.paymentID "
                "WHERE p.paymentID = ?", (paymentID,)).fetchone()
        print(f"  ------------- SOUFFLÉ  receipt {self.receiptNumber} -------------")
        print(f"  Order {orderID}   {self.date}")
        for line in order.getOrderDetails():
            print(f"    {line.quantity} x {line.menuItem.name:<34}${line.lineTotal:>7.2f}")
        if order.discountAmount:
            print(f"    {'Promotion discount':<38}-${order.discountAmount:>6.2f}")
        print(f"    {'TOTAL PAID':<38}${self.totalPaid:>7.2f}")
        if pay["method"] == "card":
            print(f"    Paid by {pay['cardType']} card")
        else:
            print(f"    Cash ${pay['cashReceived']:.2f}, change ${pay['changeDue']:.2f}")
        print("  " + "-" * 51)


def payment_of_order(orderID: str) -> Optional[Payment]:
    """The approved card or cash payment of an order, or None."""
    with closing(get_connection()) as conn:
        r = conn.execute(
            "SELECT p.*, c.cardType, c.authorizationCode, h.cashReceived, h.changeDue "
            "FROM payments p LEFT JOIN card_payments c ON c.paymentID = p.paymentID "
            "LEFT JOIN cash_payments h ON h.paymentID = p.paymentID "
            "WHERE p.orderID = ? AND LOWER(p.status) = 'approved'", (orderID,)).fetchone()
    if r is None:
        return None
    common = (r["paymentID"], r["amount"], r["method"], date.fromisoformat(r["paymentDate"]),
              r["status"])
    if r["method"] == "card":
        payment = CardPayment(*common, r["cardType"], r["authorizationCode"] or "")
    else:
        payment = CashPayment(*common, r["cashReceived"], r["changeDue"])
    payment.orderID = orderID
    return payment
