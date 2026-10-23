"""Problem-domain classes of the Soufflé management system, one module per use case area."""
from .people import Person, Customer, Employee, Manager
from .accounts import EmployeeAccount
from .orders import Order, OrderLine, MenuItem
from .payments import Payment, CardPayment, CashPayment, Receipt
from .promotions import Promotion, DraftPromotion, SharedPromotion
from .inventory import Store, Inventory, InventoryItem
from .reports import Report, SalesReport, InventoryReport, CustomerLoyaltyReport

__all__ = [
    "Person", "Customer", "Employee", "Manager",
    "EmployeeAccount",
    "Order", "OrderLine", "MenuItem",
    "Payment", "CardPayment", "CashPayment", "Receipt",
    "Promotion", "DraftPromotion", "SharedPromotion",
    "Store", "Inventory", "InventoryItem",
    "Report", "SalesReport", "InventoryReport", "CustomerLoyaltyReport",
]
