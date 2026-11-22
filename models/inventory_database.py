"""Inventory Database: the data-access class the Inventory uses to read and save items.

Inventory "accesses" the Inventory Database. Its records are the inventory_items table
of souffle.db.
"""
from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from datetime import date, datetime
from typing import List, Optional

from database.connection import get_connection


@dataclass
class InventoryDatabase:
    """Reads and updates the stored inventory items."""
    databaseID: int
    lastUpdated: Optional[datetime] = None

    def getInventoryItems(self, inventoryID: int) -> List:
        """Return the items of one store's inventory (sequence diagram: -> inventoryItems)."""
        from .inventory import InventoryItem   # imported here: inventory.py imports this module
        with closing(get_connection()) as conn:
            rows = conn.execute(
                "SELECT itemID, itemName, quantity, minimumQuantity FROM inventory_items "
                "WHERE inventoryID = ? ORDER BY itemID", (inventoryID,)
            ).fetchall()
        return [InventoryItem(r["itemID"], r["itemName"], r["quantity"], r["minimumQuantity"])
                for r in rows]

    def updateItem(self, itemID: int, newQuantity: int) -> bool:
        """Save the new quantity of an item (sequence diagram: -> saveSuccess)."""
        with closing(get_connection()) as conn:
            saved = conn.execute("UPDATE inventory_items SET quantity = ? WHERE itemID = ?",
                                 (newQuantity, itemID)).rowcount == 1
            if saved:
                conn.execute(
                    "UPDATE inventories SET lastUpdated = ? WHERE inventoryID = "
                    "(SELECT inventoryID FROM inventory_items WHERE itemID = ?)",
                    (date.today().isoformat(), itemID))
                conn.commit()
        if saved:
            self.lastUpdated = datetime.now()
        return saved
