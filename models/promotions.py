"""Promotions (Manage Promotions use case): Promotion, DraftPromotion, SharedPromotion."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass
class Promotion:
    """A marketing promotion that can apply a discount to orders."""
    promotionID: int
    title: str
    discountType: str  # "percentage" or "fixed"
    discountValue: int
    startDate: date
    endDate: date

    @property
    def duration(self) -> int:
        """/duration: derived attribute, number of days the promotion runs."""
        return (self.endDate - self.startDate).days

    def calculateDiscount(self, orderTotal: float) -> float:
        if self.discountType == "percentage":
            return round(orderTotal * self.discountValue / 100, 2)
        return float(min(self.discountValue, orderTotal))

    def isValid(self) -> bool:
        return self.startDate <= date.today() <= self.endDate

    def activate(self) -> None:
        raise NotImplementedError("Planned for a later prototype.")

    def deactivate(self) -> None:
        raise NotImplementedError("Planned for a later prototype.")


@dataclass
class DraftPromotion(Promotion):
    """A promotion saved but not yet shared with customers."""
    savedDate: date

    def editDraft(self) -> None:
        raise NotImplementedError("Planned for a later prototype.")

    def publish(self) -> None:
        raise NotImplementedError("Planned for a later prototype.")


@dataclass
class SharedPromotion(Promotion):
    """A promotion that has been shared with customers through a channel."""
    sharingDate: date
    sharingChannel: str

    def share(self) -> None:
        raise NotImplementedError("Planned for a later prototype.")

    def trackEngagement(self) -> None:
        raise NotImplementedError("Planned for a later prototype.")
