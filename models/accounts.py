"""Employee accounts (Manage Employee Account use case)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EmployeeAccount:
    """An account holding an employee's login and payroll information."""
    accountID: int
    employeeID: int
    employeeEmail: str
    accountPassword: str
    accountStatus: str
    voidCheque: str  # "File" in the class diagram: stored as a file path

    def validateAccountInformation(self):
        raise NotImplementedError("Planned for a later prototype.")

    def saveAccount(self):
        raise NotImplementedError("Planned for a later prototype.")

    def updateAccount(self):
        raise NotImplementedError("Planned for a later prototype.")

    def deleteAccount(self):
        raise NotImplementedError("Planned for a later prototype.")
