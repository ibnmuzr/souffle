"""Inventory (Manage Inventory use case): Store, Inventory, InventoryItem.

The InventoryUI interface class is in inventory_ui.py and the Inventory Database in
inventory_database.py.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .base import PLANNED


@dataclass
class Store:
    """A Soufflé location (Eaton Centre, Rockland).

    Associations: Store "has" Inventory (1 to 1); Report "covers" Store.
    """
    storeID: int
    storeName: str
    address: str

    def generateDailySales(self):
        raise NotImplementedError(PLANNED)


@dataclass
class Inventory:
    """The inventory kept for one Soufflé store.

    Associations: InventoryUI "represents" Inventory; Inventory "accesses" Inventory
    Database; Inventory "contains" InventoryItem (composition).
    """
    inventoryID: int
    lastUpdated: date

    def getInventoryList(self, inventoryID: int):
        raise NotImplementedError(PLANNED)

    def updateInventoryRecord(self, itemID: int, newQuant: int):
        raise NotImplementedError(PLANNED)


@dataclass
class InventoryItem:
    """An item stored and tracked in a store's inventory.

    Associations: Inventory "contains" InventoryItem; MenuItem is linked to
    InventoryItem; Inventory Report "checks" InventoryItem.
    """
    itemID: int
    itemName: str
    quantity: int
    minimumQuantity: int

    def validateQuantity(self, newQuant: int) -> bool:
        """A quantity is valid when it is a whole number that is not negative."""
        return isinstance(newQuant, int) and not isinstance(newQuant, bool) and newQuant >= 0

    def isBelowMinimum(self, itemID: int) -> bool:
        """True when the item's quantity is under its minimum quantity.

        Called by the Inventory Report for each item in the store's inventory (sequence
        diagram: isBelowMinimum(itemID) -> belowMinimum).
        """
        if itemID != self.itemID:
            raise ValueError(f"isBelowMinimum was called with item {itemID} on item {self.itemID}.")
        return self.quantity < self.minimumQuantity
