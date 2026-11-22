"""Employee accounts (Manage Employee Accounts use case): EmployeeAccount."""
from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from typing import Optional

from database.connection import get_connection
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

    def verifyAccountPassword(self, accountPassword: str) -> bool:
        """True when the password is this account's password and the account is active."""
        return (self.accountStatus.lower() == "active"
                and accountPassword == self.accountPassword)


def account_from_row(r) -> EmployeeAccount:
    """Build an EmployeeAccount object from a row of the employee_accounts table."""
    return EmployeeAccount(r["accountID"], r["employeeID"], r["employeeEmail"],
                           r["accountPassword"], r["accountStatus"], r["voidCheque"] or "")


def account_of_manager(managerID: int) -> Optional[EmployeeAccount]:
    """The manager's own account (a manager is also on staff), or None."""
    with closing(get_connection()) as conn:
        r = conn.execute(
            "SELECT a.* FROM employee_accounts a "
            "JOIN employees e ON e.employeeID = a.employeeID "
            "JOIN managers m ON m.personID = e.personID WHERE m.managerID = ?",
            (managerID,)).fetchone()
    return None if r is None else account_from_row(r)
