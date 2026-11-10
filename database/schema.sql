-- Soufflé Management System: database schema (SQLite)
-- Built from the final Milestone 4 class diagram.
--   * One table per class whose objects must be kept. Columns use the exact attribute
--     names from the class diagram.
--   * OrderHandler («controller») and InventoryUI («interface») only hold what is on
--     screen or in progress while the app runs, so they have no table.
--   * Sales Database and Inventory Database are the data-access classes: their
--     records are sales_records, cancellation_records and inventory_items.
--   * Generalization (a-kind-of): each subclass table shares its parent's key
--     (class-table inheritance, Chapter 9).
--   * Associations become foreign keys; many-to-many associations get a link table.
--   * Dates are stored as text in YYYY-MM-DD format; booleans as 0/1.

PRAGMA foreign_keys = ON;

-- ============================================================
-- People: Person (abstract) -> Customer, Employee, Manager
-- ============================================================
CREATE TABLE persons (
    personID   INTEGER PRIMARY KEY,
    firstName  TEXT NOT NULL,
    lastName   TEXT NOT NULL,
    phone      TEXT,
    email      TEXT
);

CREATE TABLE customers (
    customerID INTEGER PRIMARY KEY,
    personID   INTEGER NOT NULL UNIQUE REFERENCES persons(personID)
);

CREATE TABLE employees (
    employeeID       INTEGER PRIMARY KEY,
    personID         INTEGER NOT NULL UNIQUE REFERENCES persons(personID),
    registerUserName TEXT NOT NULL UNIQUE,
    registerPassword TEXT NOT NULL,
    employeeStatus   TEXT NOT NULL,
    hireDate         TEXT
);

CREATE TABLE managers (
    managerID INTEGER PRIMARY KEY,
    personID  INTEGER NOT NULL UNIQUE REFERENCES persons(personID)
);

-- ============================================================
-- Employee accounts
-- ============================================================
-- Employee "has" EmployeeAccount (1 to 1); Manager "creates" EmployeeAccount (1 to many)
CREATE TABLE employee_accounts (
    accountID       INTEGER PRIMARY KEY,
    employeeID      INTEGER NOT NULL UNIQUE REFERENCES employees(employeeID),
    managerID       INTEGER REFERENCES managers(managerID),
    employeeEmail   TEXT NOT NULL,
    accountPassword TEXT NOT NULL,
    accountStatus   TEXT NOT NULL,
    voidCheque      TEXT  -- file path of the uploaded void cheque
);

-- ============================================================
-- Stores and inventory: Store, Inventory, InventoryItem
-- ============================================================
CREATE TABLE stores (
    storeID   INTEGER PRIMARY KEY,
    storeName TEXT NOT NULL,
    address   TEXT
);

-- Store "has" Inventory (1 to 1)
CREATE TABLE inventories (
    inventoryID INTEGER PRIMARY KEY,
    storeID     INTEGER NOT NULL UNIQUE REFERENCES stores(storeID),
    lastUpdated TEXT
);

-- ============================================================
-- Menu and orders: MenuItem, Order, OrderLine
-- ============================================================
CREATE TABLE menu_items (
    menuItemID  INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    description TEXT,
    category    TEXT,
    price       REAL NOT NULL CHECK (price >= 0),
    isAvailable INTEGER NOT NULL DEFAULT 1 CHECK (isAvailable IN (0, 1))
);

-- Inventory "contains" InventoryItem (composition, 1 to many);
-- MenuItem is linked to InventoryItem (1 to many; supplies like takeout boxes have none)
CREATE TABLE inventory_items (
    itemID          INTEGER PRIMARY KEY,
    inventoryID     INTEGER NOT NULL REFERENCES inventories(inventoryID) ON DELETE CASCADE,
    menuItemID      INTEGER REFERENCES menu_items(menuItemID),
    itemName        TEXT NOT NULL,
    quantity        INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    minimumQuantity INTEGER NOT NULL DEFAULT 0 CHECK (minimumQuantity >= 0)
);

-- ============================================================
-- Promotions
-- ============================================================
-- Manager "creates" Promotion (1 to many). /duration is derived, so it is not stored.
CREATE TABLE promotions (
    promotionID    INTEGER PRIMARY KEY,
    managerID      INTEGER NOT NULL REFERENCES managers(managerID),
    title          TEXT NOT NULL,
    discountType   TEXT NOT NULL CHECK (discountType IN ('percentage', 'fixed')),
    discountValue  INTEGER NOT NULL CHECK (discountValue >= 0),
    creationDate   TEXT NOT NULL,
    startDate      TEXT NOT NULL,
    endDate        TEXT NOT NULL,
    sharingChannel TEXT,
    lifecycleState TEXT NOT NULL CHECK (lifecycleState IN ('draft', 'shared', 'expired')),
    CHECK (endDate >= startDate)
);

-- Customer "receives" Promotion (many to many)
CREATE TABLE customer_promotions (
    customerID  INTEGER NOT NULL REFERENCES customers(customerID),
    promotionID INTEGER NOT NULL REFERENCES promotions(promotionID) ON DELETE CASCADE,
    PRIMARY KEY (customerID, promotionID)
);

-- Promotion "applies to" Order (an order may have no promotion).
-- The customer, employee and store of an order are kept as foreign keys so the
-- order history, the Sales Report and the Customer Loyalty Report can find them
-- (in the class diagram these links go through the OrderHandler).
--   storeID is a data-layer column: it is not an attribute in the class diagram.
CREATE TABLE orders (
    orderID     TEXT PRIMARY KEY,
    customerID  INTEGER REFERENCES customers(customerID),
    employeeID  INTEGER NOT NULL REFERENCES employees(employeeID),
    storeID     INTEGER NOT NULL REFERENCES stores(storeID),
    promotionID INTEGER REFERENCES promotions(promotionID),
    orderLine   INTEGER NOT NULL DEFAULT 0,
    orderDate   TEXT NOT NULL,
    orderType   TEXT NOT NULL,
    orderTotal  REAL NOT NULL DEFAULT 0 CHECK (orderTotal >= 0),
    orderStatus TEXT NOT NULL
);

-- Order "contains" OrderLine (aggregation, 1..*); OrderLine "refers to" MenuItem (many to 1)
CREATE TABLE order_lines (
    orderLineID         INTEGER PRIMARY KEY,
    orderID             TEXT NOT NULL REFERENCES orders(orderID) ON DELETE CASCADE,
    menuItemID          INTEGER NOT NULL REFERENCES menu_items(menuItemID),
    quantity            INTEGER NOT NULL CHECK (quantity > 0),
    specialInstructions TEXT,
    lineTotal           REAL NOT NULL DEFAULT 0
);

-- ============================================================
-- Sales Database: salesRecords and cancellationRecords
-- ============================================================
-- Sales Database "summarizes" Order: one record per sale (recordOrder)
CREATE TABLE sales_records (
    orderID      TEXT PRIMARY KEY REFERENCES orders(orderID),
    recordedDate TEXT NOT NULL,
    amount       REAL NOT NULL CHECK (amount >= 0)
);

-- one record per cancelled order (logCancellation)
CREATE TABLE cancellation_records (
    orderID       TEXT PRIMARY KEY REFERENCES orders(orderID),
    reason        TEXT NOT NULL,
    approvedBy    INTEGER REFERENCES managers(managerID),  -- needed once preparation started
    cancelledDate TEXT NOT NULL
);

-- ============================================================
-- Payments: Payment (abstract) -> CardPayment, CashPayment; Receipt
-- ============================================================
-- Order "paid by" Payment
CREATE TABLE payments (
    paymentID   INTEGER PRIMARY KEY,
    orderID     TEXT NOT NULL REFERENCES orders(orderID),
    amount      REAL NOT NULL CHECK (amount >= 0),
    method      TEXT NOT NULL CHECK (method IN ('card', 'cash')),
    paymentDate TEXT NOT NULL,
    status      TEXT NOT NULL
);

CREATE TABLE card_payments (
    paymentID         INTEGER PRIMARY KEY REFERENCES payments(paymentID) ON DELETE CASCADE,
    cardType          TEXT NOT NULL,
    authorizationCode TEXT
);

CREATE TABLE cash_payments (
    paymentID    INTEGER PRIMARY KEY REFERENCES payments(paymentID) ON DELETE CASCADE,
    cashReceived REAL NOT NULL,
    changeDue    REAL NOT NULL DEFAULT 0
);

-- Payment "generates" Receipt (1 to 1)
CREATE TABLE receipts (
    receiptNumber TEXT PRIMARY KEY,
    paymentID     INTEGER NOT NULL UNIQUE REFERENCES payments(paymentID),
    totalPaid     REAL NOT NULL,
    date          TEXT NOT NULL
);

-- ============================================================
-- Reports: Report (abstract) -> SalesReport, InventoryReport, CustomerLoyaltyReport
-- ============================================================
-- Manager "generates" Report (1 to many); Report "covers" Store (many to 1)
CREATE TABLE reports (
    reportID    INTEGER PRIMARY KEY,
    managerID   INTEGER NOT NULL REFERENCES managers(managerID),
    storeID     INTEGER NOT NULL REFERENCES stores(storeID),
    startDate   TEXT NOT NULL,
    endDate     TEXT NOT NULL,
    createdDate TEXT NOT NULL,
    format      TEXT NOT NULL,
    CHECK (endDate >= startDate)
);

CREATE TABLE sales_reports (
    reportID          INTEGER PRIMARY KEY REFERENCES reports(reportID) ON DELETE CASCADE,
    totalRevenue      REAL NOT NULL DEFAULT 0,
    unitSold          INTEGER NOT NULL DEFAULT 0,
    averageOrderTotal REAL NOT NULL DEFAULT 0
);

CREATE TABLE inventory_reports (
    reportID          INTEGER PRIMARY KEY REFERENCES reports(reportID) ON DELETE CASCADE,
    itemsBelowMinimum INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE customer_loyalty_reports (
    reportID            INTEGER PRIMARY KEY REFERENCES reports(reportID) ON DELETE CASCADE,
    registeredCustomers INTEGER NOT NULL DEFAULT 0,
    repeatPurchases     INTEGER NOT NULL DEFAULT 0
);

-- SalesReport "summarizes" Order (many to many)
CREATE TABLE sales_report_orders (
    reportID INTEGER NOT NULL REFERENCES sales_reports(reportID) ON DELETE CASCADE,
    orderID  TEXT NOT NULL REFERENCES orders(orderID),
    PRIMARY KEY (reportID, orderID)
);

-- InventoryReport "checks" InventoryItem (many to many)
CREATE TABLE inventory_report_items (
    reportID INTEGER NOT NULL REFERENCES inventory_reports(reportID) ON DELETE CASCADE,
    itemID   INTEGER NOT NULL REFERENCES inventory_items(itemID),
    PRIMARY KEY (reportID, itemID)
);

-- CustomerLoyaltyReport "analyses" Customer (many to many)
CREATE TABLE loyalty_report_customers (
    reportID   INTEGER NOT NULL REFERENCES customer_loyalty_reports(reportID) ON DELETE CASCADE,
    customerID INTEGER NOT NULL REFERENCES customers(customerID),
    PRIMARY KEY (reportID, customerID)
);

-- Indexes on foreign keys used for lookups (Chapter 9: optimizing access speed)
CREATE INDEX idx_orders_date        ON orders(orderDate);
CREATE INDEX idx_orders_store       ON orders(storeID);
CREATE INDEX idx_orders_customer    ON orders(customerID);
CREATE INDEX idx_order_lines_order  ON order_lines(orderID);
CREATE INDEX idx_payments_order     ON payments(orderID);
CREATE INDEX idx_items_inventory    ON inventory_items(inventoryID);
CREATE INDEX idx_reports_store      ON reports(storeID);
