"""Promotions (Manage Promotions use case): Promotion.

A promotion moves through lifecycle states (for example draft, then shared) instead of
being split into separate draft and shared classes.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

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
        if promotionID != self.promotionID:
            raise ValueError(f"isValid was called with promotion {promotionID} "
                             f"on promotion {self.promotionID}.")
        return self.lifecycleState == "shared" and self.startDate <= date.today() <= self.endDate

    def trackEngagement(self, promotionID: int):
        raise NotImplementedError(PLANNED)

    def saveDraft(self, promotionID: int) -> None:
        raise NotImplementedError(PLANNED)

    def editDraft(self, promotionID: int) -> None:
        raise NotImplementedError(PLANNED)
