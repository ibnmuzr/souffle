"""Sales Database: the data-access class that records sales and cancellations.

It "summarizes" Order. Its records are kept in the sales_records and
cancellation_records tables of souffle.db.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from .base import PLANNED


@dataclass
class SalesDatabase:
    """Keeps the record of every completed sale and every cancelled order."""
    databaseID: int
    totalOrders: int = 0
    salesRecords: List = field(default_factory=list)
    cancellationRecords: List = field(default_factory=list)
    lastUpdated: Optional[datetime] = None

    def logCancellation(self, orderID: str):
        raise NotImplementedError(PLANNED)

    def recordOrder(self, orderID: str):
        raise NotImplementedError(PLANNED)
