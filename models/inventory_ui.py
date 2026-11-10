"""InventoryUI: the screen the manager uses to view and update the inventory.

The manager "manages" the InventoryUI, and it "represents" one Inventory. Its
attributes describe what is on the screen right now, so they live in memory while the
app runs and are not stored in their own table.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional

from .base import PLANNED


@dataclass
class InventoryUI:
    """«interface» Shows the inventory list and takes the manager's quantity updates."""
    lastUpdated: Optional[date] = None
    filterCategory: str = ""
    searchKeyword: str = ""
    displayedItems: List = field(default_factory=list)

    def viewInventoryList(self):
        raise NotImplementedError(PLANNED)

    def updateQuantity(self, itemID: int, newQuant: int):
        raise NotImplementedError(PLANNED)
