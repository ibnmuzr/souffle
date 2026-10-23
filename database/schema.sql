-- Soufflé Management System: database schema (SQLite)
-- One table per class in the Milestone 3 class diagram.
--   * Columns use the exact attribute names from the class diagram.
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

-- Inventory "contains" InventoryItem (composition, 1 to many)
CREATE TABLE inventory_items (
    itemID          INTEGER PRIMARY KEY,
    inventoryID     INTEGER NOT NULL REFERENCES inventories(inventoryID) ON DELETE CASCADE,
    itemName        TEXT NOT NULL,
    quantity        INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    minimumQuantity INTEGER NOT NULL DEFAULT 0 CHECK (minimumQuantity >= 0)
);

-- Manager "manages" Inventory (many to 1)
CREATE TABLE managers (
    managerID   INTEGER PRIMARY KEY,
    personID    INTEGER NOT NULL UNIQUE REFERENCES persons(personID),
    inventoryID INTEGER REFERENCES inventories(inventoryID)
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
-- Promotions: Promotion -> DraftPromotion, SharedPromotion
-- ============================================================
-- Manager "creates" Promotion (1 to many). /duration is derived, so it is not stored.
CREATE TABLE promotions (
    promotionID   INTEGER PRIMARY KEY,
    managerID     INTEGER NOT NULL REFERENCES managers(managerID),
    title         TEXT NOT NULL,
    discountType  TEXT NOT NULL CHECK (discountType IN ('percentage', 'fixed')),
    discountValue INTEGER NOT NULL CHECK (discountValue >= 0),
    startDate     TEXT NOT NULL,
    endDate       TEXT NOT NULL,
    CHECK (endDate >= startDate)
);

CREATE TABLE draft_promotions (
    promotionID INTEGER PRIMARY KEY REFERENCES promotions(promotionID) ON DELETE CASCADE,
    savedDate   TEXT NOT NULL
);

CREATE TABLE shared_promotions (
    promotionID    INTEGER PRIMARY KEY REFERENCES promotions(promotionID) ON DELETE CASCADE,
    sharingDate    TEXT NOT NULL,
    sharingChannel TEXT NOT NULL
);

-- Customer "receives" SharedPromotion (many to many)
CREATE TABLE customer_shared_promotions (
    customerID  INTEGER NOT NULL REFERENCES customers(customerID),
    promotionID INTEGER NOT NULL REFERENCES shared_promotions(promotionID),
    PRIMARY KEY (customerID, promotionID)
);

-- ============================================================
-- Orders: Order, OrderLine, MenuItem
-- ============================================================
CREATE TABLE menu_items (
    itemID      INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    description TEXT,
    category    TEXT,
    price       REAL NOT NULL CHECK (price >= 0),
    isAvailable INTEGER NOT NULL DEFAULT 1 CHECK (isAvailable IN (0, 1))
);

-- Customer "places" Order (0..1 to many); Employee "enters" Order (1 to many);
-- Promotion "applies to" Order (an order may have no promotion)
CREATE TABLE orders (
    orderID            TEXT PRIMARY KEY,
    customerID         INTEGER REFERENCES customers(customerID),
    employeeID         INTEGER NOT NULL REFERENCES employees(employeeID),
    promotionID        INTEGER REFERENCES promotions(promotionID),
    orderLine          INTEGER NOT NULL DEFAULT 0,
    orderDate          TEXT NOT NULL,
    orderType          TEXT NOT NULL,
    orderTotal         REAL NOT NULL DEFAULT 0 CHECK (orderTotal >= 0),
    orderStatus        TEXT NOT NULL,
    confirmationNumber INTEGER UNIQUE
);

-- Order "contains" OrderLine (aggregation, 1..*); OrderLine "refers to" MenuItem (many to 1)
CREATE TABLE order_lines (
    orderLineID         INTEGER PRIMARY KEY,
    orderID             TEXT NOT NULL REFERENCES orders(orderID) ON DELETE CASCADE,
    itemID              INTEGER NOT NULL REFERENCES menu_items(itemID),
    quantity            INTEGER NOT NULL CHECK (quantity > 0),
    specialInstructions TEXT,
    lineTotal           REAL NOT NULL DEFAULT 0
);

-- ============================================================
-- Payments: Payment (abstract) -> CardPayment, CashPayment; Receipt
-- ============================================================
-- Order "paid by" Payment (1 to 1..*)
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

-- Payment "generates" Receipt (0..1 to 1)
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
    repeatPurchases     INTEGER NOT NULL DEFAULT 0,
    pointsIssued        INTEGER NOT NULL DEFAULT 0,
    pointsRedeemed      INTEGER NOT NULL DEFAULT 0
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
CREATE INDEX idx_orders_customer    ON orders(customerID);
CREATE INDEX idx_order_lines_order  ON order_lines(orderID);
CREATE INDEX idx_payments_order     ON payments(orderID);
CREATE INDEX idx_items_inventory    ON inventory_items(inventoryID);
CREATE INDEX idx_reports_store      ON reports(storeID);
