# Soufflé Management System: Prototype

BTM 495 team project (Fall 2026). This is a prototype of the to-be system for Soufflé, a Japanese cheesecake shop in Montréal with two locations (Eaton Centre and Rockland).

## Progress

| Prototype | What it covers | Status |
|---|---|---|
| 1 | Version control, SQLite database, every class and attribute from the Milestone 3 class diagram | Done |
| 2 | **Create Reports (UC 06)** works end to end: Sales, Inventory and Customer Loyalty reports, matching the Milestone 4 sequence diagrams | Done |
| 2 | Every class, attribute and operation matches the final Milestone 4 class diagram (24 classes), with a table for every class that is stored | Done |
| 2 | Methods of the other use cases: Inventory, Orders, Payments, Promotions, Employee Accounts | In progress, one use case per commit |
| 2 | Final sync with the Milestone 5 class diagram | Planned |

Every operation from the class diagram is present with the same name and parameters. The ones not built yet raise *Implemented in an upcoming Prototype 2 commit*.

## How to run

You need Python 3.8 or newer. Nothing else to install: SQLite is built into Python.

```bash
python3 main.py             # full demo: rebuilds the database and runs all three reports
python3 create_reports.py   # interactive menu: pick a report, store and period, then save or export
python3 database/setup_db.py   # rebuild only the database with the sample data
```

Exported reports are written to the `exports/` folder (CSV opens in Excel).

## Create Reports (UC 06)

Each report follows its Milestone 4 sequence diagram, using the same method names, parameters and order:

| Step | Sales report | Inventory report | Customer loyalty report |
|---|---|---|---|
| Manager starts it | `retrieveRecords(startDate, endDate, storeID)` | same | same |
| Loop | for each order in the period: `Order.calculateTotal(orderID)` | for each item in the store's inventory: `InventoryItem.isBelowMinimum(itemID)` | for each registered customer: `Customer.viewOrderHistory(customerID)` |
| Compile and calculate | `compileSalesFigures(storeID, startDate, endDate)`, `calculateRevenue(storeID, orderTotals)`, `calculateUnitSold(storeID, orderLines)`, `calculateAverageOrderValue(totalRevenue, numberOfOrders)` | `compileStockLevels(storeID, inventoryItems)`, `identifyLowStockItems(stockLevels)`, `generateRestockRecommendations(lowStockItems)` | `compileLoyaltyData(storeID, startDate, endDate)`, `identifyRepeatCustomers(orderHistory)` |
| Display | `generate(reportID)` | `generate(reportID)` | `generate(reportID)` |
| Manager saves or exports | `save(reportID)` returns a save confirmation, `export(reportID, format)` returns an export confirmation | same | same |

Business rules used:
- Sales count **completed** orders only (cancelled orders are not sales).
- Customer loyalty is measured by **repeat purchases** (no loyalty points, since no other use case issues or redeems them).
- A **repeat customer** has 2 or more orders in the period; every order after their first is a repeat purchase.
- Restock recommendation: order enough to bring a low item back to **2 × its minimum** (`RESTOCK_TARGET`).

## Project structure

```
main.py                 Demo: builds the database, uses the classes, runs all three reports
create_reports.py       Interactive Create Reports menu for the manager
models/                 Problem-domain classes, one file per use-case area
  people.py             Person (abstract), Customer, Employee, Manager
  accounts.py           EmployeeAccount
  order_handler.py      OrderHandler (controller for the order sequence diagrams)
  orders.py             Order, OrderLine, MenuItem
  sales_database.py     SalesDatabase
  payments.py           Payment (abstract), CardPayment, CashPayment, Receipt
  promotions.py         Promotion
  inventory_ui.py       InventoryUI (the manager's inventory screen)
  inventory.py          Store, Inventory, InventoryItem
  inventory_database.py InventoryDatabase
  reports.py            Report (abstract), SalesReport, InventoryReport, CustomerLoyaltyReport
  base.py               Shared message for operations not built yet
database/
  schema.sql            CREATE TABLE statements for every class
  setup_db.py           Builds souffle.db and loads sample data
  connection.py         Opens a connection with foreign keys turned on
souffle.db              The SQLite database
exports/                Created when a report is exported
```

## How the class diagram maps to the code and database

| Class (diagram) | Python file | Table |
|---|---|---|
| Person «abstract» | models/people.py | persons |
| Customer | models/people.py | customers |
| Employee | models/people.py | employees |
| Manager | models/people.py | managers |
| Employee Account | models/accounts.py | employee_accounts |
| OrderHandler | models/order_handler.py | none (controller, see below) |
| Order | models/orders.py | orders |
| Order Line | models/orders.py | order_lines |
| Menu Item | models/orders.py | menu_items |
| Sales Database | models/sales_database.py | sales_records, cancellation_records |
| Payment «abstract» | models/payments.py | payments |
| CardPayment | models/payments.py | card_payments |
| CashPayment | models/payments.py | cash_payments |
| Receipt | models/payments.py | receipts |
| Promotion | models/promotions.py | promotions |
| InventoryUI | models/inventory_ui.py | none (interface, see below) |
| Store | models/inventory.py | stores |
| Inventory | models/inventory.py | inventories |
| InventoryItem | models/inventory.py | inventory_items |
| Inventory Database | models/inventory_database.py | inventory_items |
| Report «abstract» | models/reports.py | reports |
| Sales Report | models/reports.py | sales_reports |
| Inventory Report | models/reports.py | inventory_reports |
| Customer Loyalty Report | models/reports.py | customer_loyalty_reports |

Design rules used (Chapter 9, data management layer):
- **Names match the diagram.** Class, attribute and operation names are the same as in the class diagram.
- **Generalization**: each subclass table shares its parent's key (for example, a `customers` row points to its `persons` row).
- **Associations**: one-to-many associations become foreign keys; many-to-many associations get a link table (`customer_promotions`, `sales_report_orders`, `inventory_report_items`, `loyalty_report_customers`).
- **Controller and interface classes**: OrderHandler and InventoryUI only hold the order or screen being worked on while the app runs, so they have no table.
- **Data-access classes**: Sales Database keeps its sales and cancellation records in `sales_records` and `cancellation_records`; Inventory Database reads and updates `inventory_items`.
- **Derived attribute**: `/duration` of Promotion is calculated from its dates, not stored.
- **Abstract classes** (Person, Payment, Report) cannot be created directly.
- **Data-layer columns**, not attributes in the class diagram: `orders.storeID` (where the order was placed, so reports can filter by store) and `orders.customerID` / `orders.employeeID` (in the diagram these links go through the OrderHandler; the order history and reports need them stored).

Sample menu items and prices come from Soufflé's Clover item list; people and orders in the sample data are fictional.

## Team

Nina Judek · Mohammad Imam Hossain · Jadynn Somerville · Rahyan-Elis Prophete · Néomie Bradshaw-Tremblay · Mai-Ly Francoeur
