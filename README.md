# Soufflé Management System: Prototype 1

BTM 495 team project (Fall 2026). This is a prototype of the to-be system for Soufflé, a Japanese cheesecake shop in Montréal with two locations (Eaton Centre and Rockland).

Prototype 1 covers:
1. **Version control**: this GitHub repository
2. **Database**: SQLite database `souffle.db`, built from `database/schema.sql`
3. **Classes and attributes**: every class in the Milestone 3 class diagram, in `models/`
4. **Methods** (optional for this version): every operation from the class diagram is present with the same name. The simple ones work now; the rest are marked *Planned for a later prototype*.

## How to run

You need Python 3.8 or newer. Nothing else to install: SQLite is built into Python.

```bash
python3 main.py
```

This rebuilds `souffle.db` with sample data, loads rows into the classes and prints a short demo.

To rebuild only the database:

```bash
python3 database/setup_db.py
```

## Project structure

```
main.py                 Demo: builds the database and uses the classes
models/                 Problem-domain classes, one file per use-case area
  people.py             Person (abstract), Customer, Employee, Manager
  accounts.py           EmployeeAccount
  orders.py             Order, OrderLine, MenuItem
  payments.py           Payment (abstract), CardPayment, CashPayment, Receipt
  promotions.py         Promotion, DraftPromotion, SharedPromotion
  inventory.py          Store, Inventory, InventoryItem
  reports.py            Report (abstract), SalesReport, InventoryReport, CustomerLoyaltyReport
database/
  schema.sql            CREATE TABLE statements for every class
  setup_db.py           Builds souffle.db and loads sample data
  connection.py         Opens a connection with foreign keys turned on
souffle.db              The SQLite database
```

## How the class diagram maps to the code and database

| Class (diagram) | Python file | Table |
|---|---|---|
| Person «abstract» | models/people.py | persons |
| Customer | models/people.py | customers |
| Employee | models/people.py | employees |
| Manager | models/people.py | managers |
| Employee Account | models/accounts.py | employee_accounts |
| Order | models/orders.py | orders |
| Order Line | models/orders.py | order_lines |
| Menu Item | models/orders.py | menu_items |
| Payment «abstract» | models/payments.py | payments |
| CardPayment | models/payments.py | card_payments |
| CashPayment | models/payments.py | cash_payments |
| Receipt | models/payments.py | receipts |
| Promotion | models/promotions.py | promotions |
| Draft Promotion | models/promotions.py | draft_promotions |
| Shared Promotion | models/promotions.py | shared_promotions |
| Store | models/inventory.py | stores |
| Inventory | models/inventory.py | inventories |
| InventoryItem | models/inventory.py | inventory_items |
| Report «abstract» | models/reports.py | reports |
| Sales Report | models/reports.py | sales_reports |
| Inventory Report | models/reports.py | inventory_reports |
| Customer Loyalty Report | models/reports.py | customer_loyalty_reports |

Design rules used (Chapter 9, data management layer):
- **Names match the diagram.** Class, attribute and operation names are the same as in the class diagram.
- **Generalization**: each subclass table shares its parent's key (for example, a `customers` row points to its `persons` row).
- **Associations**: one-to-many associations become foreign keys; many-to-many associations get a link table (`customer_shared_promotions`, `sales_report_orders`, `inventory_report_items`, `loyalty_report_customers`).
- **Derived attribute**: `/duration` of Promotion is calculated from its dates, not stored.
- **Abstract classes** (Person, Payment, Report) cannot be created directly.

Sample menu items and prices come from Soufflé's Clover item list; people in the sample data are fictional.

## Team

Nina Judek · Mohammad Imam Hossain · Jadynn Somerville · Rahyan-Elis Prophete · Néomie Bradshaw-Tremblay · Mai-Ly Francoeur
