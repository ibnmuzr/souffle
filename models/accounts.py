"""Employee accounts (Manage Employee Accounts use case): EmployeeAccount."""
from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from typing import Optional

from database.connection import get_connection

ACCOUNT_STATUSES = ("pending", "active", "inactive")
CHEQUE_FILE_TYPES = (".pdf", ".jpg", ".jpeg", ".png")
MIN_PASSWORD_LENGTH = 8


@dataclass
class EmployeeAccount:
    """An account holding an employee's login and payroll information.

    Associations: Employee "has" EmployeeAccount (employeeID, 1 to 1); Manager "creates"
    EmployeeAccount (managerID, 1 to many).
    """
    accountID: int
    employeeID: int
    employeeEmail: str
    accountPassword: str
    accountStatus: str
    voidCheque: str  # "File" in the class diagram: stored as a file path
    managerID: Optional[int] = None   # the manager who created the account

    def validateAccountInformation(self, accountID: int) -> None:
        """Check the account information. Raises ValueError listing every problem
        (invalid account information), so nothing is saved."""
        self._check_id(accountID)
        problems = []
        with closing(get_connection()) as conn:
            if conn.execute("SELECT 1 FROM employees WHERE employeeID = ?",
                            (self.employeeID,)).fetchone() is None:
                problems.append(f"there is no employee {self.employeeID}")
            elif conn.execute("SELECT 1 FROM employee_accounts WHERE employeeID = ? "
                              "AND accountID != ?", (self.employeeID, accountID)).fetchone():
                problems.append(f"employee {self.employeeID} already has an account")
        email = self.employeeEmail.strip()
        if "@" not in email or "." not in email.split("@")[-1]:
            problems.append("the email is not valid")
        if len(self.accountPassword) < MIN_PASSWORD_LENGTH:
            problems.append(f"the password needs at least {MIN_PASSWORD_LENGTH} characters")
        if self.voidCheque and not self.voidCheque.lower().endswith(CHEQUE_FILE_TYPES):
            problems.append("the void cheque must be a PDF, JPG or PNG file")
        if self.accountStatus not in ACCOUNT_STATUSES:
            problems.append(f"the status must be one of: {', '.join(ACCOUNT_STATUSES)}")
        if problems:
            raise ValueError("Invalid account information: " + "; ".join(problems) + ".")

    def saveAccount(self, accountID: int, accountStatus: str) -> None:
        """Save the account with the given status (a new account becomes active)."""
        self._check_id(accountID)
        self.accountStatus = accountStatus
        with closing(get_connection()) as conn:
            conn.execute("INSERT OR REPLACE INTO employee_accounts VALUES (?, ?, ?, ?, ?, ?, ?)",
                         (accountID, self.employeeID, self.managerID, self.employeeEmail,
                          self.accountPassword, accountStatus, self.voidCheque or None))
            conn.commit()

    def updateAccount(self, accountID: int, employeeEmail: str, accountPassword: str,
                      accountStatus: str) -> bool:
        """Change the email, password and status. False (nothing saved) if they are invalid."""
        old = (self.employeeEmail, self.accountPassword, self.accountStatus)
        self.employeeEmail, self.accountPassword, self.accountStatus = (
            employeeEmail, accountPassword, accountStatus)
        try:
            self.validateAccountInformation(accountID)
        except ValueError:
            self.employeeEmail, self.accountPassword, self.accountStatus = old
            return False
        self.saveAccount(accountID, accountStatus)
        return True

    def deleteAccount(self, accountID: int) -> None:
        """Remove the account."""
        self._check_id(accountID)
        with closing(get_connection()) as conn:
            conn.execute("DELETE FROM employee_accounts WHERE accountID = ?", (accountID,))
            conn.commit()

    def verifyAccountPassword(self, accountPassword: str) -> bool:
        """True when the password is this account's password and the account is active."""
        return (self.accountStatus.lower() == "active"
                and accountPassword == self.accountPassword)

    def _check_id(self, accountID: int) -> None:
        if accountID != self.accountID:
            raise ValueError(f"This is account {self.accountID}, not account {accountID}.")


def account_from_row(r) -> EmployeeAccount:
    """Build an EmployeeAccount object from a row of the employee_accounts table."""
    return EmployeeAccount(r["accountID"], r["employeeID"], r["employeeEmail"],
                           r["accountPassword"], r["accountStatus"], r["voidCheque"] or "",
                           managerID=r["managerID"])


def load_account(accountID: int) -> EmployeeAccount:
    with closing(get_connection()) as conn:
        r = conn.execute("SELECT * FROM employee_accounts WHERE accountID = ?",
                         (accountID,)).fetchone()
    if r is None:
        raise ValueError(f"There is no account {accountID}.")
    return account_from_row(r)


def next_account_id() -> int:
    with closing(get_connection()) as conn:
        return conn.execute("SELECT COALESCE(MAX(accountID), 0) + 1 FROM employee_accounts"
                            ).fetchone()[0]


def account_of_manager(managerID: int) -> Optional[EmployeeAccount]:
    """The manager's own account (a manager is also on staff), or None."""
    with closing(get_connection()) as conn:
        r = conn.execute(
            "SELECT a.* FROM employee_accounts a "
            "JOIN employees e ON e.employeeID = a.employeeID "
            "JOIN managers m ON m.personID = e.personID WHERE m.managerID = ?",
            (managerID,)).fetchone()
    return None if r is None else account_from_row(r)
