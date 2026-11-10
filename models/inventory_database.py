"""Inventory Database: the data-access class the Inventory uses to read and save items.

Inventory "accesses" the Inventory Database. Its records are the inventory_items table
of souffle.db.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from .base import PLANNED


@dataclass
class InventoryDatabase:
    """Reads and updates the stored inventory items."""
    databaseID: int
    lastUpdated: Optional[datetime] = None

    def getInventoryItems(self, inventoryID: int):
        raise NotImplementedError(PLANNED)

    def updateItem(self, itemID: int, newQuant: int):
        raise NotImplementedError(PLANNED)
