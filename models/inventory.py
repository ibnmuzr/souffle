"""Inventory (Manage Inventory use case): Store, Inventory, InventoryItem.

The InventoryUI interface class is in inventory_ui.py and the Inventory Database in
inventory_database.py.
"""
from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional

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

    def generateDailySales(self) -> Dict[date, float]:
        """Total sales of this store for each day that had sales, oldest day first.

        Uses the Sales Database records (completed orders only; cancelled orders are not
        sales). Also used by the Sales Report for its sales-per-day table.
        """
        with closing(get_connection()) as conn:
            rows = conn.execute(
                "SELECT s.recordedDate AS day, ROUND(SUM(s.amount), 2) AS total "
                "FROM sales_records s JOIN orders o ON o.orderID = s.orderID "
                "WHERE o.storeID = ? GROUP BY s.recordedDate ORDER BY s.recordedDate",
                (self.storeID,)).fetchall()
        return {date.fromisoformat(r["day"]): r["total"] for r in rows}


@dataclass
class Inventory:
    """The inventory kept for one Soufflé store.

    Associations: InventoryUI "represents" Inventory; Inventory "accesses" Inventory
    Database; Inventory "contains" InventoryItem (composition).
    """
    inventoryID: int
    lastUpdated: date
    # Association from the class diagram: Inventory "accesses" Inventory Database
    database: InventoryDatabase = field(default_factory=lambda: InventoryDatabase(1))

    def __post_init__(self):
        self.inventoryItems: List[InventoryItem] = []   # Inventory "contains" InventoryItem

    def getInventoryList(self, inventoryID: int) -> List[InventoryItem]:
        """Sequence diagram "View Inventory": get the items from the Inventory Database and
        return them as the inventory list."""
        if inventoryID != self.inventoryID:
            raise ValueError(f"This is inventory {self.inventoryID}, not inventory {inventoryID}.")
        self.inventoryItems = self.database.getInventoryItems(inventoryID)
        return self.inventoryItems

    def updateInventoryRecord(self, itemID: int, newQuant: int) -> bool:
        """Sequence diagram "Update Inventory Item": validate the new quantity with the
        item, then save it in the Inventory Database. Returns updateConfirmed."""
        item = self._find_item(itemID)
        isValid = item.validateQuantity(newQuant)
        if not isValid:
            return False
        saveSuccess = self.database.updateItem(itemID, newQuant)
        if saveSuccess:
            item.quantity = newQuant
            self.lastUpdated = date.today()
        return saveSuccess

    # ---- helper (not in the class diagram) ------------------------------------------

    def _find_item(self, itemID: int) -> InventoryItem:
        if not self.inventoryItems:
            self.getInventoryList(self.inventoryID)
        for item in self.inventoryItems:
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
