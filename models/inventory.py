"""Inventory (Manage Inventory use case): Store, Inventory, InventoryItem.

The InventoryUI interface class is in inventory_ui.py and the Inventory Database in
inventory_database.py.
"""
from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass, field
from datetime import date
from typing import List

from database.connection import get_connection
from .inventory_database import InventoryDatabase


@dataclass
class Store:
    """A Soufflé location (Eaton Centre, Rockland).

    Associations: Store "has" Inventory (1 to 1); Report "covers" Store.
    """
    storeID: int
    storeName: str
    address: str

    def generateDailySales(self, storeID: int):
        """Today's Sales Report for this store (completed orders of the day). It is
        displayed and returned; the manager can then save or export it."""
        from .reports import SalesReport, next_report_id   # imported here: reports imports this module
        if storeID != self.storeID:
            raise ValueError(f"This is store {self.storeID}, not store {storeID}.")
        today = date.today()
        report = SalesReport(next_report_id(), today, today, today, "CSV", storeID=storeID)
        if not report.retrieveRecords(today, today, storeID):
            print(f"No completed orders at {self.storeName} today.")
        return report


@dataclass
class Inventory:
    """The inventory kept for one Soufflé store.

    Associations: InventoryUI "represents" Inventory; Inventory "accesses" Inventory
    Database; Inventory "contains" InventoryItem (composition).
    """
    inventoryID: int
    lastUpdated: date
    # Association from the class diagram: Inventory "accesses" Inventory Database
    inventoryDatabase: InventoryDatabase = field(default_factory=lambda: InventoryDatabase(1))
    # Association from the class diagram: Inventory "contains" InventoryItem
    items: List[InventoryItem] = field(default_factory=list)

    def getInventoryList(self, inventoryID: int) -> List[InventoryItem]:
        """Sequence diagram "View Inventory": get the items from the Inventory Database and
        return them as the inventory list."""
        if inventoryID != self.inventoryID:
            raise ValueError(f"This is inventory {self.inventoryID}, not inventory {inventoryID}.")
        self.items = self.inventoryDatabase.getInventoryItems(inventoryID)
        return self.items

    def updateInventoryRecord(self, itemID: int, newQuantity: int) -> bool:
        """Sequence diagram "Update Inventory Item": validate the new quantity with the
        item, then save it in the Inventory Database. Returns updateConfirmed."""
        item = self._find_item(itemID)
        isValid = item.validateQuantity(newQuantity)
        if not isValid:
            return False
        saveSuccess = self.inventoryDatabase.updateItem(itemID, newQuantity)
        if saveSuccess:
            item.quantity = newQuantity
            self.lastUpdated = date.today()
        return saveSuccess

    # ---- helper (not in the class diagram) ------------------------------------------

    def _find_item(self, itemID: int) -> InventoryItem:
        if not self.items:
            self.getInventoryList(self.inventoryID)
        for item in self.items:
            if item.itemID == itemID:
                return item
        raise ValueError(f"There is no item with ID {itemID} in this store's inventory.")


def load_inventory(storeID: int) -> Inventory:
    """The Inventory of one store, read from the inventories table."""
    with closing(get_connection()) as conn:
        row = conn.execute("SELECT inventoryID, lastUpdated FROM inventories WHERE storeID = ?",
                           (storeID,)).fetchone()
    if row is None:
        raise ValueError(f"There is no inventory for store {storeID}.")
    return Inventory(row["inventoryID"], date.fromisoformat(row["lastUpdated"]))


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

    def validateQuantity(self, newQuantity: int) -> bool:
        """A quantity is valid when it is a whole number that is not negative."""
        return isinstance(newQuantity, int) and not isinstance(newQuantity, bool) and newQuantity >= 0

    def isBelowMinimum(self, itemID: int) -> bool:
        """True when the item's quantity is under its minimum quantity.

        Called by the Inventory Report for each item in the store's inventory (sequence
        diagram: isBelowMinimum(itemID) -> belowMinimum).
        """
        if itemID != self.itemID:
            raise ValueError(f"isBelowMinimum was called with item {itemID} on item {self.itemID}.")
        return self.quantity < self.minimumQuantity
