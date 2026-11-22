"""People in the Soufflé system: Person (abstract), Customer, Employee, Manager.

Attributes and operations follow the Milestone 5 implementation class diagram.
"""
from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from datetime import date, time
from typing import List, Optional

from database.connection import get_connection
from .orders import Order, load_order, order_from_row


@dataclass
class Person:
    """«abstract» A person known to the system. Never created directly."""
    personID: int
    firstName: str
    lastName: str
    phone: str
    email: str

    def __post_init__(self):
        if type(self) is Person:
            raise TypeError("Person is abstract: create a Customer, Employee or Manager instead.")

    def getFullName(self) -> str:
        return f"{self.firstName} {self.lastName}"

    def updateContactInformation(self, firstName: str, lastName: str, phone: str,
                                 email: str) -> None:
        """Change the person's name, phone and email (saved in the database)."""
        if not firstName.strip() or not lastName.strip():
            raise ValueError("The first and last name cannot be empty.")
        if email and ("@" not in email or "." not in email.split("@")[-1]):
            raise ValueError("The email is not valid.")
        self.firstName, self.lastName = firstName.strip(), lastName.strip()
        self.phone, self.email = phone.strip(), email.strip()
        with closing(get_connection()) as conn:
            conn.execute("UPDATE persons SET firstName = ?, lastName = ?, phone = ?, email = ? "
                         "WHERE personID = ?",
                         (self.firstName, self.lastName, self.phone, self.email, self.personID))
            conn.commit()


@dataclass
class Customer(Person):
    """A person who places, confirms and pays for an order.

    Associations: Customer "uses" OrderHandler; Customer "receives" Promotion;
    Customer Loyalty Report "analyses" Customer.
    """
    customerID: int

    def confirmOrder(self, orderID: str) -> bool:
        """The customer confirms the order summary: it is submitted to the kitchen."""
        from .order_handler import OrderHandler
        return OrderHandler(customer=self).submitOrder(orderID)

    def payOrder(self, orderID: str, paymentInfo) -> bool:
        """Sequence diagrams "Pay by Card" / "Pay by Cash": total := calculateTotal(orderID),
        then confirmOrder(orderID) with the card or cash payment. True if approved."""
        order = load_order(orderID)
        if order.customerID != self.customerID:
            raise ValueError(f"Order {orderID} is not {self.getFullName()}'s order.")
        order.calculateTotal(orderID)
        return order.confirmOrder(orderID, paymentInfo)

    def updateProfile(self, customerID: int, updatedInfo: Customer) -> bool:
        """Copy the new contact information into the customer's profile."""
        if customerID != self.customerID:
            raise ValueError(f"This is customer {self.customerID}, not customer {customerID}.")
        self.updateContactInformation(updatedInfo.firstName, updatedInfo.lastName,
                                      updatedInfo.phone, updatedInfo.email)
        return True

    def sharePromotion(self, title: str, discountType: str, discountValue: int,
                       startDate: date, endDate: date) -> None:
        """The customer receives a shared promotion."""
        off = f"{discountValue}% off" if discountType == "percentage" else f"${discountValue} off"
        print(f"  [to {self.getFullName()}] {title}: {off}, {startDate} to {endDate}")

    def viewOrderHistory(self, customerID: int) -> List[Order]:
        """Return the customer's orders, newest first.

        Called by the Customer Loyalty Report for each registered customer (sequence
        diagram: viewOrderHistory(customerID) -> orderHistory).
        """
        with closing(get_connection()) as conn:
            rows = conn.execute(
                "SELECT * FROM orders WHERE customerID = ? ORDER BY orderDate DESC, orderID DESC",
                (customerID,),
            ).fetchall()
        return [order_from_row(row) for row in rows]


@dataclass
class Employee(Person):
    """A staff member who logs in to enter, track and complete customer orders.

    Associations: Employee "has" EmployeeAccount; Employee "uses" OrderHandler.
    """
    employeeID: int
    registerUserName: str
    registerPassword: str
    employeeStatus: str
    hireDate: date

    def login(self, registerUserName: str, registerPassword: str) -> bool:
        """True when the user name and password match and the employee is active."""
        self.loggedIn = (registerUserName == self.registerUserName
                         and registerPassword == self.registerPassword
                         and self.employeeStatus.lower() == "active")
        return self.loggedIn

    def notifyCancellation(self, orderID: str) -> None:
        """Tell the kitchen staff to stop preparing a cancelled order."""
        print(f"  [{self.firstName}'s screen] Order {orderID} was cancelled: stop preparing it.")

    def displayStatus(self, orderID: str) -> str:
        """Show the order's current state."""
        message = f"Order {orderID}: {load_order(orderID).getStatus(orderID)}"
        print(f"  [{self.firstName}'s screen] {message}")
        return message

    def displayWaitTime(self, orderID: str, estTime: time) -> time:
        """Show the new estimated time the order will be ready."""
        print(f"  [{self.firstName}'s screen] Order {orderID} will now be ready at "
              f"{estTime.strftime('%H:%M')}.")
        return estTime

    def notifyOrderReady(self, orderID: str) -> None:
        """Tell the front counter the order is ready for the customer."""
        print(f"  [{self.firstName}'s screen] Order {orderID} is ready for the customer.")

    def markOrderComplete(self, orderID: str) -> None:
        """The customer has the order and it is paid: complete it through the OrderHandler."""
        from .order_handler import OrderHandler
        OrderHandler(employee=self).markOrderComplete(orderID)

    def logout(self) -> None:
        self.loggedIn = False


@dataclass
class Manager(Person):
    """A staff member with higher authority (owners and hired managers).

    Associations: Manager "creates" EmployeeAccount; Manager "manages" InventoryUI;
    Manager "creates" Promotion; Manager "generates" Report.
    """
    managerID: int

    def requestReason(self, orderID: str) -> str:
        """The message asking for the reason an order is being cancelled."""
        return f"Order {orderID} has started: enter the reason and a manager's approval to cancel it."

    def createAccount(self, employeeID: int, employeeEmail: str, voidCheque: str,
                      accountPassword: str):
        """Sequence diagram "Create Employee Account": validateAccountInformation, then
        saveAccount. Raises ValueError (nothing saved) if the information is invalid."""
        from .accounts import EmployeeAccount, next_account_id
        account = EmployeeAccount(next_account_id(), employeeID, employeeEmail.strip(),
                                  accountPassword, "pending", voidCheque, managerID=self.managerID)
        account.validateAccountInformation(account.accountID)
        account.saveAccount(account.accountID, "active")
        return account

    def modifyAccount(self, accountID: int, employeeEmail: Optional[str] = None,
                      accountPassword: Optional[str] = None,
                      accountStatus: Optional[str] = None) -> bool:
        """Change an account (only the values given). False if the new values are invalid."""
        from .accounts import load_account
        account = load_account(accountID)
        return account.updateAccount(accountID, employeeEmail or account.employeeEmail,
                                     accountPassword or account.accountPassword,
                                     accountStatus or account.accountStatus)

    def deleteAccount(self, accountID: int) -> bool:
        """Delete an account. False if there is no such account."""
        from .accounts import load_account
        try:
            load_account(accountID).deleteAccount(accountID)
        except ValueError:
            return False
        return True

    def sharePromotion(self, title: str, discountType: str, discountValue: int,
                       startDate: date, endDate: date, sharingChannel: str = "email") -> None:
        """Create a promotion and share it with the customers right away."""
        from .promotions import Promotion, next_promotion_id
        promotion = Promotion(0, "", "", 0, date.today(), startDate, endDate, "", "",
                              managerID=self.managerID)
        promotion.createPromotion(next_promotion_id(), title, discountType, discountValue,
                                  startDate, endDate)
        promotion.sharePromotion(promotion.promotionID, sharingChannel)


def load_employee(employeeID: int) -> Employee:
    """The employee with this ID, read from the database."""
    with closing(get_connection()) as conn:
        r = conn.execute("SELECT p.*, e.* FROM employees e JOIN persons p ON p.personID = e.personID "
                         "WHERE e.employeeID = ?", (employeeID,)).fetchone()
    if r is None:
        raise ValueError(f"There is no employee {employeeID}.")
    return Employee(r["personID"], r["firstName"], r["lastName"], r["phone"], r["email"],
                    r["employeeID"], r["registerUserName"], r["registerPassword"],
                    r["employeeStatus"], date.fromisoformat(r["hireDate"]))


def load_manager(managerID: int) -> Manager:
    """The manager with this ID, read from the database."""
    with closing(get_connection()) as conn:
        r = conn.execute("SELECT p.*, m.managerID FROM managers m JOIN persons p "
                         "ON p.personID = m.personID WHERE m.managerID = ?", (managerID,)).fetchone()
    if r is None:
        raise ValueError(f"There is no manager {managerID}.")
    return Manager(r["personID"], r["firstName"], r["lastName"], r["phone"], r["email"],
                   r["managerID"])


def load_customer(customerID: int) -> Customer:
    """The customer with this ID, read from the database."""
    with closing(get_connection()) as conn:
        r = conn.execute("SELECT p.*, c.customerID FROM customers c JOIN persons p "
                         "ON p.personID = c.personID WHERE c.customerID = ?", (customerID,)).fetchone()
    if r is None:
        raise ValueError(f"There is no customer {customerID}.")
    return Customer(r["personID"], r["firstName"], r["lastName"], r["phone"], r["email"],
                    r["customerID"])


def all_customers() -> List[Customer]:
    with closing(get_connection()) as conn:
        ids = [r[0] for r in conn.execute("SELECT customerID FROM customers ORDER BY customerID")]
    return [load_customer(customerID) for customerID in ids]
