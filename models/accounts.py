"""Employee accounts (Manage Employee Accounts use case): EmployeeAccount."""
from __future__ import annotations

from dataclasses import dataclass

from .base import PLANNED


@dataclass
class EmployeeAccount:
    """An account holding an employee's login and payroll information.

    Associations: Employee "has" EmployeeAccount (1 to 1); Manager "creates"
    EmployeeAccount (1 to many).
    """
    accountID: int
    employeeID: int
    employeeEmail: str
    accountPassword: str
    accountStatus: str
    voidCheque: str  # "File" in the class diagram: stored as a file path

    def validateAccountInformation(self, accountID: int) -> None:
        raise NotImplementedError(PLANNED)

    def saveAccount(self, accountID: int, accountStatus: str) -> None:
        raise NotImplementedError(PLANNED)

    def updateAccount(self, accountID: int):
        raise NotImplementedError(PLANNED)

    def deleteAccount(self, accountID: int) -> None:
        raise NotImplementedError(PLANNED)
