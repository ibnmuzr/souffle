"""Promotions (Manage Promotions use case): Promotion.

A promotion moves through lifecycle states (for example draft, then shared) instead of
being split into separate draft and shared classes.
"""
from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from datetime import date
from typing import Optional

from database.connection import get_connection
from .base import PLANNED


@dataclass
class Promotion:
    """A marketing promotion that can apply a discount to orders.

    Associations: Manager "creates" Promotion; Promotion "applies to" Order;
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
    lifecycleState: str  # "draft", "shared" or "expired"

    @property
    def duration(self) -> int:
        """/duration: derived attribute, the number of days the promotion runs."""
        return (self.endDate - self.startDate).days

    def createPromotion(self, promotionID: int, title: str, discountType: str,
                        discountValue: int, startDate: date, endDate: date):
        raise NotImplementedError(PLANNED)

    def sharePromotion(self, promotionID: int, sharingChannel: str) -> None:
        raise NotImplementedError(PLANNED)

    def isValid(self, promotionID: int) -> bool:
        """True when the promotion has been shared and today is within its dates."""
        self._check_id(promotionID)
        return self.lifecycleState == "shared" and self.startDate <= date.today() <= self.endDate

    def trackEngagement(self, promotionID: int):
        raise NotImplementedError(PLANNED)

    def saveDraft(self, promotionID: int) -> None:
        raise NotImplementedError(PLANNED)

    def editDraft(self, promotionID: int) -> None:
        raise NotImplementedError(PLANNED)

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

    def _check_id(self, promotionID: int) -> None:
        if promotionID != self.promotionID:
            raise ValueError(f"This is promotion {self.promotionID}, not promotion {promotionID}.")


def promotion_from_row(r) -> Promotion:
    """Build a Promotion object from a row of the promotions table."""
    return Promotion(r["promotionID"], r["title"], r["discountType"], r["discountValue"],
                     date.fromisoformat(r["creationDate"]), date.fromisoformat(r["startDate"]),
                     date.fromisoformat(r["endDate"]), r["sharingChannel"] or "",
                     r["lifecycleState"])
