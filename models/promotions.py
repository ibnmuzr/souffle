"""Promotions (Manage Promotions use case): Promotion.

A promotion moves through lifecycle states (in process, draft, shared, expired) instead
of being split into separate draft and shared classes.
"""
from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from datetime import date
from typing import Optional

from database.connection import get_connection


SHARING_CHANNELS = ("email", "SMS", "social media", "website")


@dataclass
class Promotion:
    """A marketing promotion that can apply a discount to orders.

    States (Milestone 4 promotion state machine): created ("in process"), then saved as a
    "draft" (and edited) or "shared" with the customers; it is only valid while shared
    and within its dates.

    Associations: Manager "creates" Promotion (managerID); Promotion "applies to" Order;
    Customer "receives" Promotion.
    """
    promotionID: int
    title: str
    discountType: str  # "percentage" or "fixed"
    discountValue: int
    creationDate: date
    startDate: date
    endDate: date
    sharingChannel: str  # email, SMS, social media or website; empty while a draft
    lifeCycleState: str  # "in process", "draft", "shared" or "expired"
    managerID: Optional[int] = None   # the manager who created it

    @property
    def duration(self) -> int:
        """/duration: derived attribute, the number of days the promotion runs."""
        return (self.endDate - self.startDate).days

    def createPromotion(self, promotionID: int, title: str, discountType: str,
                        discountValue: int, startDate: date, endDate: date) -> Promotion:
        """Fill in a new promotion ("in process"). It is saved by saveDraft or sharePromotion."""
        _check_details(title, discountType, discountValue, startDate, endDate)
        self.promotionID, self.title = promotionID, title.strip()
        self.discountType, self.discountValue = discountType, discountValue
        self.startDate, self.endDate = startDate, endDate
        self.creationDate, self.sharingChannel, self.lifeCycleState = date.today(), "", "in process"
        return self

    def sharePromotion(self, promotionID: int, sharingChannel: str) -> None:
        """Share the promotion with every customer through a channel. It becomes "shared"."""
        from .people import all_customers
        self._check_id(promotionID)
        if sharingChannel not in SHARING_CHANNELS:
            raise ValueError(f"The channel must be one of: {', '.join(SHARING_CHANNELS)}.")
        self.sharingChannel, self.lifeCycleState = sharingChannel, "shared"
        self._save()
        customers = all_customers()
        with closing(get_connection()) as conn:
            conn.executemany("INSERT OR IGNORE INTO customer_promotions VALUES (?, ?)",
                             [(c.customerID, promotionID) for c in customers])
            conn.commit()
        for customer in customers:                      # Customer "receives" Promotion
            customer.sharePromotion(self.title, self.discountType, self.discountValue,
                                    self.startDate, self.endDate)

    def isValid(self, promotionID: int) -> bool:
        """True when the promotion has been shared and today is within its dates."""
        self._check_id(promotionID)
        return self.lifeCycleState == "shared" and self.startDate <= date.today() <= self.endDate

    def trackEngagement(self, promotionID: int) -> int:
        """How many orders used the promotion."""
        self._check_id(promotionID)
        with closing(get_connection()) as conn:
            return conn.execute("SELECT COUNT(*) FROM orders WHERE promotionID = ?",
                                (promotionID,)).fetchone()[0]

    def saveDraft(self, promotionID: int) -> None:
        """Save the promotion as a draft (not shared, so not valid yet)."""
        self._check_id(promotionID)
        if self.lifeCycleState not in ("in process", "draft"):
            raise ValueError("Only a new promotion or a draft can be saved as a draft.")
        self.lifeCycleState = "draft"
        self._save()

    def editDraft(self, promotionID: int, title: Optional[str] = None,
                  discountValue: Optional[int] = None, discountType: Optional[str] = None,
                  startDate: Optional[date] = None, endDate: Optional[date] = None) -> None:
        """Change a draft and save it (only drafts can be edited)."""
        self._check_id(promotionID)
        if self.lifeCycleState != "draft":
            raise ValueError("Only a draft can be edited.")
        changed = (title or self.title, discountType or self.discountType,
                   self.discountValue if discountValue is None else discountValue,
                   startDate or self.startDate, endDate or self.endDate)
        _check_details(*changed)
        self.title, self.discountType, self.discountValue, self.startDate, self.endDate = changed
        self._save()

    @classmethod
    def getPromotion(cls, promotionID: int) -> Optional[Promotion]:
        """The promotion with this ID, read from the database (None if there is none)."""
        with closing(get_connection()) as conn:
            r = conn.execute("SELECT * FROM promotions WHERE promotionID = ?",
                             (promotionID,)).fetchone()
        return None if r is None else promotion_from_row(r)

    def getDiscountType(self, promotionID: int) -> str:
        """"percentage" or "fixed"."""
        self._check_id(promotionID)
        return self.discountType

    def getDiscountValue(self, promotionID: int) -> int:
        """The percentage off, or the number of dollars off."""
        self._check_id(promotionID)
        return self.discountValue

    def _save(self) -> None:
        if self.managerID is None:
            raise ValueError("A promotion needs the manager who creates it.")
        with closing(get_connection()) as conn:
            conn.execute("INSERT OR REPLACE INTO promotions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                         (self.promotionID, self.managerID, self.title, self.discountType,
                          self.discountValue, self.creationDate.isoformat(),
                          self.startDate.isoformat(), self.endDate.isoformat(),
                          self.sharingChannel or None, self.lifeCycleState))
            conn.commit()

    def _check_id(self, promotionID: int) -> None:
        if promotionID != self.promotionID:
            raise ValueError(f"This is promotion {self.promotionID}, not promotion {promotionID}.")


def promotion_from_row(r) -> Promotion:
    """Build a Promotion object from a row of the promotions table."""
    return Promotion(r["promotionID"], r["title"], r["discountType"], r["discountValue"],
                     date.fromisoformat(r["creationDate"]), date.fromisoformat(r["startDate"]),
                     date.fromisoformat(r["endDate"]), r["sharingChannel"] or "",
                     r["lifeCycleState"], managerID=r["managerID"])


def next_promotion_id() -> int:
    with closing(get_connection()) as conn:
        return conn.execute("SELECT COALESCE(MAX(promotionID), 0) + 1 FROM promotions").fetchone()[0]


def _check_details(title, discountType, discountValue, startDate, endDate) -> None:
    """The rules every promotion must follow."""
    problems = []
    if not str(title).strip():
        problems.append("a title")
    if discountType not in ("percentage", "fixed"):
        problems.append('a discount type of "percentage" or "fixed"')
    if not isinstance(discountValue, int) or discountValue <= 0 or (
            discountType == "percentage" and discountValue > 100):
        problems.append("a discount value above 0 (and at most 100 for a percentage)")
    if endDate < startDate:
        problems.append("an end date on or after the start date")
    if problems:
        raise ValueError("The promotion needs " + ", ".join(problems) + ".")
