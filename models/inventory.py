"""Inventory (Manage Inventory use case): Store, Inventory, InventoryItem."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass
class Store:
    """A Soufflé location (Eaton Centre, Rockland)."""
    storeID: int
    storeName: str
    address: str

    def generateDailySales(self):
        raise NotImplementedError("Planned for a later prototype.")


@dataclass
class Inventory:
    """The inventory maintained for one Soufflé store."""
    inventoryID: int
    lastUpdated: date

    def validateInventoryInformation(self) -> bool:
        raise NotImplementedError("Planned for a later prototype.")

    def updateInventoryRecord(self) -> None:
        raise NotImplementedError("Planned for a later prototype.")

    def addInventoryItem(self):
        raise NotImplementedError("Planned for a later prototype.")

    def removeInventoryItem(self):
        raise NotImplementedError("Planned for a later prototype.")

    def generateInventoryReport(self):
        raise NotImplementedError("Planned for a later prototype.")

    def checkLowStock(self):
        raise NotImplementedError("Planned for a later prototype.")


@dataclass
class InventoryItem:
    """An individual item stored and tracked in a store's inventory."""
    itemID: int
    itemName: str
    quantity: int
    minimumQuantity: int

    def updateQuantity(self, quantity: int) -> None:
        self.quantity = quantity

    def isBelowMinimum(self) -> bool:
        return self.quantity < self.minimumQuantity

    def restock(self, quantity: int) -> None:
        self.quantity += quantity
