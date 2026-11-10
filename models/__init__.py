"""Problem-domain classes of the Soufflé management system, one module per use case area."""
from .people import Person, Customer, Employee, Manager
from .accounts import EmployeeAccount
from .orders import Order, OrderLine, MenuItem
from .order_handler import OrderHandler
from .sales_database import SalesDatabase
from .payments import Payment, CardPayment, CashPayment, Receipt
from .promotions import Promotion
from .inventory import Store, Inventory, InventoryItem
from .inventory_ui import InventoryUI
from .inventory_database import InventoryDatabase
from .reports import Report, SalesReport, InventoryReport, CustomerLoyaltyReport

__all__ = [
    "Person", "Customer", "Employee", "Manager",
    "EmployeeAccount",
    "OrderHandler", "Order", "OrderLine", "MenuItem", "SalesDatabase",
    "Payment", "CardPayment", "CashPayment", "Receipt",
    "Promotion",
    "Store", "Inventory", "InventoryItem", "InventoryUI", "InventoryDatabase",
    "Report", "SalesReport", "InventoryReport", "CustomerLoyaltyReport",
]
