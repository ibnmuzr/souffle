"""InventoryUI: the screen the manager uses to view and update the inventory.

The manager "manages" the InventoryUI, and it "represents" one Inventory. Its
attributes describe what is on the screen right now, so they live in memory while the
app runs and are not stored in their own table.

Sequence diagrams (Milestone 4, Manage Inventory):
    aManager -> viewInventory()          -> Inventory.getInventoryList(inventoryID)
                                             -> InventoryDatabase.getInventoryItems(inventoryID)
                <- displayInventoryList(inventoryList)
    aManager -> updateQuantity(itemID, newQuantity)
                                             -> Inventory.updateInventoryRecord(itemID, newQuantity)
                                             -> InventoryItem.validateQuantity(newQuantity)
                                             -> InventoryDatabase.updateItem(itemID, newQuantity)
                <- displayUpdateConfirmation()
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional

from .inventory import Inventory

LOW_STOCK_FILTER = "below minimum"   # filterCategory value that shows only low items


@dataclass
class InventoryUI:
    """«interface» Shows the inventory list and takes the manager's quantity updates."""
    lastUpdated: Optional[date] = None
    filterCategory: str = ""      # "" shows every item, "below minimum" only the low ones
    searchKeyword: str = ""       # part of an item name, not case sensitive
    displayedItems: List = field(default_factory=list)
    # Association from the class diagram: InventoryUI "represents" Inventory
    inventory: Optional[Inventory] = None

    def viewInventory(self) -> list:
        """Show the inventory list, using the search keyword and filter on screen."""
        inventoryList = self.inventory.getInventoryList(self.inventory.inventoryID)
        keyword = self.searchKeyword.strip().lower()
        self.displayedItems = [
            item for item in inventoryList
            if keyword in item.itemName.lower()
            and (self.filterCategory.strip().lower() != LOW_STOCK_FILTER
                 or item.isBelowMinimum(item.itemID))
        ]
        self.lastUpdated = self.inventory.lastUpdated
        self._display_inventory_list(self.displayedItems)
        return self.displayedItems

    def updateQuantity(self, itemID: int, newQuantity: int) -> bool:
        """Save a new quantity for one item and show the result to the manager.

        Returns True when the update was confirmed (valid quantity, saved in the database).
        """
        item = self.inventory._find_item(itemID)
        oldQuant = item.quantity
        updateConfirmed = self.inventory.updateInventoryRecord(itemID, newQuantity)
        if updateConfirmed:
            self.lastUpdated = self.inventory.lastUpdated
            self._display_update_confirmation(item, oldQuant)
        else:
            print(f"Not saved: the quantity must be a whole number, 0 or more "
                  f"({item.itemName} is still {oldQuant}).")
        return updateConfirmed

    # ---- what the screen shows (return messages in the sequence diagrams) ----------------

    def _display_inventory_list(self, inventoryList: list) -> None:
        print(f"{'ID':>3}  {'Item':<22}{'Quantity':>9}{'Minimum':>9}  Status")
        for item in inventoryList:
            status = "LOW" if item.isBelowMinimum(item.itemID) else "ok"
            print(f"{item.itemID:>3}  {item.itemName:<22}{item.quantity:>9}"
                  f"{item.minimumQuantity:>9}  {status}")
        if not inventoryList:
            print("  No items match the search or filter.")
        print(f"Last updated: {self.lastUpdated}")

    def _display_update_confirmation(self, item, oldQuant: int) -> None:
        status = "still below minimum" if item.isBelowMinimum(item.itemID) else "stock ok"
        print(f"Saved: {item.itemName} changed from {oldQuant} to {item.quantity} "
              f"(minimum {item.minimumQuantity}, {status}).")
