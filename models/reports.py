"""Reports (Create Reports use case): Report (abstract), SalesReport,
InventoryReport, CustomerLoyaltyReport."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass
class Report:
    """«abstract» A business report compiled for a chosen period and store."""
    reportID: int
    startDate: date
    endDate: date
    createdDate: date
    format: str

    def __post_init__(self):
        if type(self) is Report:
            raise TypeError("Report is abstract: create a Sales, Inventory or CustomerLoyalty report.")

    def retrieveRecords(self, startDate: date, endDate: date, storeID: int) -> bool:
        raise NotImplementedError("Planned for a later prototype.")

    def generate(self) -> None:
        raise NotImplementedError("Planned for a later prototype.")

    def save(self) -> None:
        raise NotImplementedError("Planned for a later prototype.")

    def export(self, format: str) -> None:
        raise NotImplementedError("Planned for a later prototype.")


@dataclass
class SalesReport(Report):
    """A report summarizing sales activity for the period."""
    totalRevenue: float
    unitSold: int
    averageOrderTotal: float

    def compileSalesFigures(self) -> None:
        raise NotImplementedError("Planned for a later prototype.")

    def calculateRevenue(self):
        raise NotImplementedError("Planned for a later prototype.")

    def calculateAverageOrderValue(self):
        raise NotImplementedError("Planned for a later prototype.")

    def calculateUnitSold(self):
        raise NotImplementedError("Planned for a later prototype.")


@dataclass
class InventoryReport(Report):
    """A report comparing stock levels against minimum quantities."""
    itemsBelowMinimum: int

    def compileStockLevels(self) -> None:
        raise NotImplementedError("Planned for a later prototype.")

    def identifyLowStockItems(self):
        raise NotImplementedError("Planned for a later prototype.")

    def generateRestockRecommendations(self):
        raise NotImplementedError("Planned for a later prototype.")


@dataclass
class CustomerLoyaltyReport(Report):
    """A report on customer loyalty activity and repeat purchases."""
    registeredCustomers: int
    repeatPurchases: int
    pointsIssued: int
    pointsRedeemed: int

    def compileLoyaltyData(self) -> None:
        raise NotImplementedError("Planned for a later prototype.")

    def calculatePointsIssued(self):
        raise NotImplementedError("Planned for a later prototype.")

    def calculatePointsRedeemed(self):
        raise NotImplementedError("Planned for a later prototype.")

    def identifyRepeatCustomers(self):
        raise NotImplementedError("Planned for a later prototype.")
