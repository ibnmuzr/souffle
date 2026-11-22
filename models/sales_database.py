"""Sales Database: the data-access class that records sales and cancellations.

It "summarizes" Order. Its records are kept in the sales_records and
cancellation_records tables of souffle.db.
"""
from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import List, Optional

from database.connection import get_connection


@dataclass
class SalesDatabase:
    """Keeps the record of every sale and every cancelled order."""
    databaseID: int
    totalOrders: int = 0
    salesRecords: List = field(default_factory=list)
    cancellationRecords: List = field(default_factory=list)
    lastUpdated: Optional[datetime] = None

    def logCancellation(self, orderID: str, reason: str, managerID: Optional[int]) -> None:
        """Record a cancelled order with its reason and the manager who approved it
        (None when no approval was needed). A cancelled order is no longer a sale."""
        with closing(get_connection()) as conn:
            conn.execute("INSERT OR REPLACE INTO cancellation_records VALUES (?, ?, ?, ?)",
                         (orderID, reason, managerID, date.today().isoformat()))
            conn.execute("DELETE FROM sales_records WHERE orderID = ?", (orderID,))
            conn.commit()
        self._refresh()

    def recordOrder(self, orderID: str) -> None:
        """Record the order as a sale (once: recording it again changes nothing)."""
        with closing(get_connection()) as conn:
            conn.execute("INSERT OR IGNORE INTO sales_records (orderID, recordedDate, amount) "
                         "SELECT orderID, ?, orderTotal FROM orders WHERE orderID = ?",
                         (date.today().isoformat(), orderID))
            conn.commit()
        self._refresh()

    def _refresh(self) -> None:
        """Reload the records and totals after a change."""
        with closing(get_connection()) as conn:
            self.salesRecords = [tuple(r) for r in conn.execute(
                "SELECT orderID, recordedDate, amount FROM sales_records ORDER BY recordedDate")]
            self.cancellationRecords = [tuple(r) for r in conn.execute(
                "SELECT * FROM cancellation_records ORDER BY cancelledDate")]
        self.totalOrders = len(self.salesRecords)
        self.lastUpdated = datetime.now()
