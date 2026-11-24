# Soufflé Management System: Prototype

BTM 495 team project (Fall 2026). This is a prototype of the to-be system for Soufflé, a Japanese cheesecake shop in Montréal with two locations (Eaton Centre and Rockland).

## Progress

| Prototype | What it covers | Status |
|---|---|---|
| 1 | Version control, SQLite database, every class and attribute from the Milestone 3 class diagram | Done |
| 2 | **Create Reports (UC 06)** works end to end: Sales, Inventory and Customer Loyalty reports, matching the Milestone 4 sequence diagrams | Done |
| 2 | Every class, attribute and operation matches the final Milestone 4 class diagram (24 classes), with a table for every class that is stored | Done |
| 2 | **Manage Inventory (UC 04)** works end to end: view the inventory (search, below-minimum filter) and update a quantity, matching the Milestone 4 sequence diagrams | Done |
| 2 | Sales report adds units sold per menu item and sales per day (`compileSalesFigures`, Milestone 5 method specification) | Done |
| 2 | **Manage Orders (UC 01)** works end to end: create and submit, modify, cancel (manager approval once the kitchen has started), track and complete. Order states follow the Milestone 4 order state machine; `approveCancellation` and `calculateDiscount` follow the Milestone 5 method specifications | Done |
| 2 | **Process Payments (UC 02)**: card and cash, declined payments (card not authorized, not enough cash), receipts, refunds, following the Milestone 5 method specification 01 | Done |
| 2 | **Manage Employee Accounts (UC 03)** and **Manage Promotions (UC 05)**: create, validate (invalid information is refused), modify, delete accounts; create, save and edit drafts, share, validate and track promotions | Done |
| 2 | Every operation of every class is implemented | Done |
| 2 | Names and signatures match the **Milestone 5 implementation class diagram**; one main menu (`app.py`) opens every screen | Done |
| 2 | **Web frontend** (`web_app.py`) following the **Milestone 6 HCI design**: customer website and employee portal, every wireframe screen and wireflow, calling the same class operations as the terminal screens | Done |

Every operation in the Milestone 5 class diagram is in the code with the same name and parameters, and all of them are implemented.

## How to run

You need Python 3.8 or newer. Nothing else to install: SQLite is built into Python.

```bash
python3 app.py                # main menu: opens the screen of every use case
python3 main.py               # full demo: rebuilds the database and runs all six use cases
python3 database/setup_db.py  # rebuild only the database with the sample data
```

### Web frontend (in the browser)

```bash
pip install -r requirements.txt   # installs Flask, once
python3 web_app.py                # then open http://127.0.0.1:5000
```

On Windows use `python` instead of `python3`. Stop the server with Ctrl+C.

The web frontend follows the **Milestone 6 HCI design** (wireframes and wireflows). It has the two interfaces of the wireframes:

| Interface | Address | Pages |
|---|---|---|
| Customer website | http://127.0.0.1:5000 | Home, Menu, Cart (Order Summary), Select Payment Method, Order Confirmed, My Orders, Pay by Card (Secure Card Payment, Enter Payment Information, Payment Status, Payment Successful) |
| Employee portal | http://127.0.0.1:5000/portal | Sign-in, Dashboard, Orders, Kitchen, Menu, Inventory; Manager: Accounts, Promotions, Reports |

Employee portal sign-in: `sam.t` / `changeme` (employee) or `alex.m` / `manager123` (manager). Manager approval of a cancellation: manager ID `1`, password `manager123`. The website is signed in as the customer Jordan Lee.

Every button calls the operation from the class diagram, so the sequence diagrams are unchanged. For example "Submit Order" calls `OrderHandler.submitOrder`, "Confirm Payment" calls `Customer.payOrder` with a `CashPayment`, and "Save Changes" in the inventory calls `InventoryUI.updateQuantity`. What the classes print (kitchen messages, receipts, reports) is shown on the page. The terminal screens below still work and use the same `souffle.db`.

| Milestone 6 user story | Screens (wireframe numbers) | Alternative wireflows covered |
|---|---|---|
| 6.1 Manage Inventory | 1 Inventory List (search by item ID or name), 2 Update Inventory Quantity, 3 Inventory Updated | Cancel, invalid quantity (not saved, error shown), return to inventory |
| 6.2.1 Pay by Card | 01 Order Summary, 02 Select Payment Method, 03 Secure Card Payment, 04 Enter Payment Information, 05 Payment Status, 06 Payment Successful | Back and cancel, declined payment (Try Again / Change Payment Method), download and print receipt |
| 6.2.2 Pay by Cash | Customer: 01 Order Summary, 02 Select Pay by Cash, 03 Order Confirmed. Employee: 03 Process Cash Payment, 04 Cash Payment Status (change due), 05 Payment Successful | Insufficient cash (payment stays pending, enter the amount again) |
| 6.3.1 Create New Order | 01 Create New Order (menu with categories, search, quantity, instructions), 02 Review Order, 03 Order Submitted Successfully | Modify order from review, cancel order creation |
| 6.3.2 Modify Order | 01 Manage Orders (search by order ID, status filter), 02 Modify Order (live totals), 03 Order Updated | Cancel changes, return to orders |
| 6.3.3 Cancel Order | 01 Select order, 02 Cancel Order (reason, details, warning), 03 Cancellation Approval (manager ID and password) and confirmation | Not started: cancelled without approval. Wrong password or Reject: order unchanged. Paid order: refunded |
| 6.3.4 Track and Complete Order | 01 Kitchen Orders, 02 Track Order (progress, estimated waiting time), 03 Order Completed | Request remake (new waiting time) |

Differences from the wireframes, kept so the prototype follows the class diagram and state machine:
- **Taxes**: the wireframes show GST and QST lines. The classes do not calculate taxes, so the pages show the subtotal, the promotion discount and the total that is actually charged.
- **Pay by card online**: the order state machine allows a payment only once an order is Ready. The customer chooses card at checkout, the order goes to the kitchen, and the card screens (03 to 06) open from My Orders when the order is Ready.
- **Order IDs** are the database IDs (`ORD-0016`) instead of `#SF1025`. Statuses are those of the state machine; the filter's "Pending" groups In process, Entered, Ordered and Sent.
- **Card details** are only checked for format and are never stored; the terminal is simulated. A "simulate a declined card" box lets you test the declined path.
- **Special instructions** are kept per item (as in `OrderLine`), so they are entered with each item rather than once per order.
- Accounts, Promotions and Reports (UC 03, 05, 06) have no Milestone 6 wireframes; their pages use the same visual style.

### Terminal screens

Each screen can also be run on its own: `manage_orders.py`, `process_payments.py`, `manage_accounts.py`, `manage_inventory.py`, `manage_promotions.py`, `create_reports.py`.

Exported reports are written to the `exports/` folder (CSV opens in Excel).

## Manage Orders (UC 01)

The employee works through the OrderHandler controller. Each action follows its Milestone 4 sequence diagram:

| Action | OrderHandler | What happens |
|---|---|---|
| Create and submit | `startOrder(orderType)`, then for each item `checkAvailability` and `Order.addItem`, `reviewOrder(orderID)`, `submitOrder(orderID)` | `createOrder`, `createOrderLine`, `calculateTotal`, `sendToKitchen` returns the estimated ready time |
| Promotion | `applyPromotion(promotionID)` (Milestone 5 Manage Promotions diagram) | `Order.calculateDiscount(orderID, orderTotal, promotionID)`: an invalid promotion gives 0 |
| Modify | `selectOrder(orderID)`, `modifyOrder(orderID, changes)`, `confirmChanges(orderID)` | `getOrderDetails`, `updateItems` (add, remove or modify lines), `saveChanges` |
| Cancel | `selectOrder`, `enterReason(reason)`, `cancelOrder(orderID)`, `approveCancellation(orderID, managerID, accountPassword)` | not started: cancelled right away; started: the manager approves, a paid order is refunded, `notifyCancellation`, `logCancellation` |
| Track and complete | `startPreparation`, `requestRemake`, `markReady`, `markOrderComplete` | `updateStatus`, `displayStatus`, `updateWaitTime`, `displayWaitTime`, `notifyOrderReady`, `recordOrder` |

Order states (Milestone 4 order state machine): In process → Entered → Ordered → Sent → In progress → Ready → Paid → Completed. A declined payment moves Ready → Declined (pay again to go back). Any order that is not Completed can be Cancelled.

Business rules used:
- Items can only change before the kitchen starts (In process, Entered, Ordered or Sent).
- Cancelling an order the kitchen has not started needs no manager. Once it has started (In progress, Ready, Paid or Declined), a manager must approve with their ID and password (Milestone 5 method specification 02). A paid order is refunded.
- An order can only be completed once it is paid.

Sample logins: employee Sam (`sam.t` / `changeme`), manager Alex (manager ID 1, password `manager123`).

## Process Payments (UC 02)

Follows the Milestone 4 "Pay by Card" and "Pay by Cash" sequence diagrams and the Milestone 5 method specification 01:

`Customer.payOrder(orderID, paymentInfo)` → `Order.calculateTotal(orderID)` → `Order.confirmOrder(orderID, paymentInfo)` → `create(total)` → `processPayment(paymentID)`:
- **Card**: `authorizeCard()`, then `validatePayment(paymentID)`. The terminal is simulated: debit and credit cards up to $300 are authorized, anything else is declined.
- **Cash**: `validatePayment(paymentID)` (the cash received must cover the total), then `calculateChange(total, cashReceived)`.
- **Approved**: `generateReceipt(orderID, paymentID)`, `printReceipt(orderID, paymentID)`, `recordSale(orderID)`, the order becomes Paid.
- **Declined**: no receipt, the order becomes Declined and the customer can pay again.

An order can be paid once it is Ready (order state machine). A cancelled paid order is refunded with `refundPayment(paymentID)`.

## Manage Employee Accounts (UC 03)

- `Manager.createAccount(employeeID, employeeEmail, voidCheque, accountPassword)` → `validateAccountInformation(accountID)` → `saveAccount(accountID, "active")`. Invalid information is refused with every problem listed (no such employee, employee already has an account, bad email, password under 8 characters, void cheque not a PDF/JPG/PNG).
- `modifyAccount(accountID)` → `updateAccount(...)` (False and nothing saved if invalid); `deleteAccount(accountID)`.
- `verifyAccountPassword(accountPassword)` is used by the manager's cancellation approval. `Employee.login` / `logout`.

## Manage Promotions (UC 05)

- `createPromotion(...)` fills in a new promotion; `saveDraft` keeps it as a draft, `editDraft` changes a draft, `sharePromotion(promotionID, sharingChannel)` shares it with every customer (`Customer.sharePromotion`).
- `isValid(promotionID)`: shared and today is within its dates. `getPromotion`, `getDiscountType`, `getDiscountValue` are used by `Order.calculateDiscount`; `trackEngagement` counts the orders that used it.

## Manage Inventory (UC 04)

The manager works through the InventoryUI screen. Each action follows its Milestone 4 sequence diagram:

| Step | View Inventory | Update Inventory Item |
|---|---|---|
| Manager | `InventoryUI.viewInventory()` | `InventoryUI.updateQuantity(itemID, newQuantity)` |
| Inventory | `getInventoryList(inventoryID)` returns the inventory list | `updateInventoryRecord(itemID, newQuantity)` returns updateConfirmed |
| Inventory Item | | `validateQuantity(newQuantity)` returns isValid |
| Inventory Database | `getInventoryItems(inventoryID)` returns the items | `updateItem(itemID, newQuantity)` returns saveSuccess |
| Screen shows | the list (ID, item, quantity, minimum, LOW status) | the confirmation with the old and new quantity |

Business rules used:
- A new quantity must be a whole number, 0 or more. Anything else is not saved and the screen says so.
- The screen can search by item name (`searchKeyword`) and show only the items below minimum (`filterCategory = "below minimum"`).
- Saving a quantity also updates the inventory's `lastUpdated` date, so the Inventory Report shows the new stock right away.

`Store.generateDailySales(storeID)` returns today's Sales Report for the store (completed orders of the day).

## Create Reports (UC 06)

Each report follows its Milestone 4 sequence diagram, using the same method names, parameters and order:

| Step | Sales report | Inventory report | Customer loyalty report |
|---|---|---|---|
| Manager starts it | `retrieveRecords(startDate, endDate, storeID)` | same | same |
| Loop | for each order in the period: `Order.calculateTotal(orderID)` | for each item in the store's inventory: `InventoryItem.isBelowMinimum(itemID)` | for each registered customer: `Customer.viewOrderHistory(customerID)` |
| Compile and calculate | `compileSalesFigures(storeID, startDate, endDate)` (order lines, units per menu item, sales per day), `calculateRevenue(storeID, orderTotals)`, `calculateUnitSold(storeID, orderLines)`, `calculateAverageOrderValue(totalRevenue, numberOfOrders)` | `compileStockLevels(storeID, inventoryItems)`, `identifyLowStockItems(stockLevels)`, `generateRestockRecommendations(lowStockItems)` | `compileLoyaltyData(storeID, startDate, endDate)`, `identifyRepeatCustomers(orderHistory)` |
| Display | `generate(reportID)` | `generate(reportID)` | `generate(reportID)` |
| Manager saves or exports | `save(reportID)` returns a save confirmation, `export(reportID, format)` returns an export confirmation | same | same |

Business rules used:
- Sales count **completed** orders only (cancelled orders are not sales).
- Customer loyalty is measured by **repeat purchases** (no loyalty points, since no other use case issues or redeems them).
- A **repeat customer** has 2 or more orders in the period; every order after their first is a repeat purchase.
- Restock recommendation: order enough to bring a low item back to **2 × its minimum** (`RESTOCK_TARGET`).

## Project structure

```
main.py                 Demo: builds the database, uses the classes, runs every use case
manage_orders.py        Interactive Manage Orders screen for the employee
app.py                  Main menu: opens every screen below
process_payments.py     Interactive Process Payments screen at the counter
manage_accounts.py      Interactive Manage Employee Accounts screen for the manager
manage_promotions.py    Interactive Manage Promotions screen for the manager
manage_inventory.py     Interactive Manage Inventory screen for the manager
create_reports.py       Interactive Create Reports menu for the manager
web_app.py              Web frontend (Milestone 6 HCI design), calling the classes in models/
templates/site/         Customer website pages (Home, Menu, Order Summary, checkout, My Orders)
templates/portal/       Employee portal pages (one per wireframe screen)
templates/pay/          Card payment screens shared by the website and the portal
static/style.css        Styles of the web frontend (black and white, as in the wireframes)
requirements.txt        Flask, needed only for the web frontend
models/                 Problem-domain classes, one file per use-case area
  people.py             Person (base class), Customer, Employee, Manager
  accounts.py           EmployeeAccount
  order_handler.py      OrderHandler (controller for the order sequence diagrams)
  orders.py             Order, OrderLine, MenuItem
  sales_database.py     SalesDatabase
  payments.py           Payment (base class), CardPayment, CashPayment, Receipt
  promotions.py         Promotion
  inventory_ui.py       InventoryUI (the manager's inventory screen)
  inventory.py          Store, Inventory, InventoryItem
  inventory_database.py InventoryDatabase
  reports.py            Report (base class), SalesReport, InventoryReport, CustomerLoyaltyReport
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
| Person (base class) | models/people.py | persons |
| Customer | models/people.py | customers |
| Employee | models/people.py | employees |
| Manager | models/people.py | managers |
| Employee Account | models/accounts.py | employee_accounts |
| OrderHandler | models/order_handler.py | none (controller, see below) |
| Order | models/orders.py | orders |
| Order Line | models/orders.py | order_lines |
| Menu Item | models/orders.py | menu_items |
| Sales Database | models/sales_database.py | sales_records, cancellation_records |
| Payment (base class) | models/payments.py | payments |
| CardPayment | models/payments.py | card_payments |
| CashPayment | models/payments.py | cash_payments |
| Receipt | models/payments.py | receipts |
| Promotion | models/promotions.py | promotions |
| InventoryUI | models/inventory_ui.py | none (interface, see below) |
| Store | models/inventory.py | stores |
| Inventory | models/inventory.py | inventories |
| InventoryItem | models/inventory.py | inventory_items |
| Inventory Database | models/inventory_database.py | inventory_items |
| Report (base class) | models/reports.py | reports |
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
- **Generalization (Milestone 5, guideline 8)**: the implementation class diagram removes the abstract classes and shows each child with the attributes and methods it inherits. In the code, those shared attributes and methods are written once in a base class (Person, Payment, Report), so each child class has exactly what the diagram shows. The base classes cannot be created on their own.
- **Association attributes (Milestone 5, guideline 5)**: each association is kept as a reference to the related object or as its ID, which is also the foreign key in the database. For example `OrderLine.menuItem`, `Order.orderLine` (the list of lines), `Inventory.inventoryDatabase`, `Inventory.items`, `InventoryUI.inventory`, `Order.promotionID`, `Order.customerID`, `EmployeeAccount.managerID`, `Promotion.managerID`, and each report's `managerID` and `storeID`.
- **Data-layer columns**, not attributes in the class diagram: `orders.storeID` (where the order was placed, so reports can filter by store), `orders.customerID` / `orders.employeeID` (in the diagram these links go through the OrderHandler; the order history and reports need them stored) and `orders.discountAmount` (the discount the promotion gave).

Sample menu items and prices come from Soufflé's Clover item list; people and orders in the sample data are fictional.

## Team

Nina Judek · Mohammad Imam Hossain · Jadynn Somerville · Rahyan-Elis Prophete · Néomie Bradshaw-Tremblay · Mai-Ly Francoeur
