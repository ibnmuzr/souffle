"""Creates souffle.db from schema.sql and loads sample data.

Run from the project folder:  python3 database/setup_db.py
Running it again rebuilds the database from scratch.
"""
import sqlite3
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCHEMA = HERE / "schema.sql"
DB_PATH = HERE.parent / "souffle.db"

# Sample data. Menu items and prices come from Soufflé's Clover item list (BTM 481);
# people are fictional.
SEED = """
INSERT INTO stores VALUES
  (1, 'Soufflé Eaton Centre', '705 Ste-Catherine St W, Montréal, QC'),
  (2, 'Soufflé Rockland',     'Rockland Centre, Mount Royal, QC');

INSERT INTO inventories VALUES
  (1, 1, '2026-10-22'),
  (2, 2, '2026-10-22');

INSERT INTO menu_items (menuItemID, name, description, category, price, isAvailable, imageURL) VALUES
  (1, 'Japanese Cheesecake 4" (Small)',   'Fresh-baked, choice of toppings', 'Cheesecake',     7.99, 1, NULL),
  (2, 'Japanese Cheesecake 6" (Regular)', 'Fresh-baked, choice of toppings', 'Cheesecake',    15.99, 1, NULL),
  (3, 'Japanese Cheesecake 8" (Large)',   'Fresh-baked, choice of toppings', 'Cheesecake',    24.99, 1, NULL),
  (4, 'Japanese Tart',                    'Single tart',                     'Tart',           4.99, 1, NULL),
  (5, 'Americano',                        'Hot coffee',                      'Hot Beverages',  3.49, 1, NULL),
  (6, 'Latte',                            'Hot coffee with milk',            'Hot Beverages',  4.49, 1, NULL);

-- menuItemID links an ingredient to the menu item it is mainly used for (NULL for supplies)
INSERT INTO inventory_items (itemID, inventoryID, menuItemID, itemName, quantity, minimumQuantity) VALUES
  (1, 1, 2,    'Eggs (dozen)',         4,   5),
  (2, 1, 2,    'Cream cheese (kg)',   12,   8),
  (3, 1, 2,    'Sugar (kg)',          10,   6),
  (4, 1, 5,    'Coffee beans (kg)',    3,   4),
  (5, 1, NULL, 'Takeout boxes',      150, 100),
  (6, 2, 2,    'Eggs (dozen)',         8,   5),
  (7, 2, 2,    'Cream cheese (kg)',    9,   8);

INSERT INTO persons VALUES
  (1, 'Alex',   'Martin',   '514-555-0101', 'alex.martin@example.com'),
  (2, 'Sam',    'Tremblay', '514-555-0102', 'sam.tremblay@example.com'),
  (3, 'Jordan', 'Lee',      '514-555-0103', 'jordan.lee@example.com'),
  (4, 'Priya',  'Shah',     '514-555-0104', 'priya.shah@example.com'),
  (5, 'Marc',   'Gagnon',   '514-555-0105', 'marc.gagnon@example.com'),
  (6, 'Emma',   'Roy',      '514-555-0106', 'emma.roy@example.com');

-- Alex is the manager and is also on staff (employee 2), so Alex has an account too
INSERT INTO managers  VALUES (1, 1);
INSERT INTO employees VALUES
  (1, 2, 'sam.t',  'changeme',   'active', '2026-05-01'),
  (2, 1, 'alex.m', 'manager123', 'active', '2025-01-10');
INSERT INTO customers VALUES (1, 3), (2, 4), (3, 5), (4, 6);

INSERT INTO employee_accounts VALUES
  (1, 1, 1, 'sam.tremblay@example.com', 'changeme',   'active', 'uploads/void_cheque_1.pdf'),
  (2, 2, 1, 'alex.martin@example.com',  'manager123', 'active', NULL);

-- promotionID, managerID, title, discountType, discountValue, creationDate, startDate,
-- endDate, sharingChannel, lifeCycleState
INSERT INTO promotions VALUES
  (1, 1, 'Fall Loyalty Week',   'percentage', 10, '2026-10-15', '2026-10-20', '2026-10-31', 'email',        'expired'),
  (2, 1, 'Holiday Bundle',      'fixed',       5, '2026-11-02', '2026-12-01', '2026-12-24', NULL,           'draft'),
  (3, 1, 'Fall Latte Days',     'percentage', 15, '2026-10-30', '2026-11-01', '2026-12-31', 'social media', 'shared');
INSERT INTO customer_promotions VALUES (1, 1), (2, 3), (4, 3);

-- orderStatus uses the states of the order state machine (Milestone 4).
-- ORD-0012 to ORD-0015 are still open, so they show the Track and Complete steps.
INSERT INTO orders (orderID, customerID, employeeID, storeID, promotionID, orderLine,
                    orderDate, orderType, orderTotal, orderStatus) VALUES
  ('ORD-0001', 1,    1, 1, NULL, 2, '2026-10-22', 'in-store', 19.48, 'Completed'),
  ('ORD-0002', 2,    1, 1, NULL, 2, '2026-10-25', 'in-store', 33.97, 'Completed'),
  ('ORD-0003', 1,    1, 1, NULL, 2, '2026-10-29', 'takeout',  30.95, 'Completed'),
  ('ORD-0004', NULL, 1, 1, NULL, 2, '2026-11-02', 'in-store', 22.97, 'Completed'),
  ('ORD-0005', 2,    1, 1, NULL, 1, '2026-11-04', 'in-store', 31.98, 'Completed'),
  ('ORD-0006', 3,    1, 1, NULL, 2, '2026-11-05', 'takeout',  14.47, 'Completed'),
  ('ORD-0007', 1,    1, 1, NULL, 1, '2026-11-05', 'in-store', 24.99, 'Cancelled'),
  ('ORD-0008', 4,    1, 2, NULL, 2, '2026-10-24', 'in-store', 20.48, 'Completed'),
  ('ORD-0009', NULL, 1, 2, NULL, 2, '2026-10-30', 'takeout',  11.48, 'Completed'),
  ('ORD-0010', 4,    1, 2, NULL, 2, '2026-11-03', 'in-store', 34.97, 'Completed'),
  ('ORD-0011', 2,    1, 2, NULL, 1, '2026-11-04', 'takeout',   7.99, 'Completed'),
  ('ORD-0012', 3,    1, 1, NULL, 2, '2026-11-21', 'takeout',  13.97, 'Sent'),
  ('ORD-0013', 4,    1, 1, NULL, 1, '2026-11-21', 'in-store', 15.99, 'Ready'),
  ('ORD-0014', NULL, 1, 1, NULL, 1, '2026-11-21', 'in-store', 24.99, 'Paid'),
  ('ORD-0015', 1,    1, 1, NULL, 1, '2026-11-21', 'takeout',  31.98, 'Paid');

-- orderLineID, orderID, menuItemID, quantity, specialInstructions, lineTotal
INSERT INTO order_lines VALUES
  ( 1, 'ORD-0001', 2, 1, 'Strawberry topping', 15.99),
  ( 2, 'ORD-0001', 5, 1, NULL,                  3.49),
  ( 3, 'ORD-0002', 3, 1, NULL,                 24.99),
  ( 4, 'ORD-0002', 6, 2, NULL,                  8.98),
  ( 5, 'ORD-0003', 1, 2, 'Matcha topping',     15.98),
  ( 6, 'ORD-0003', 4, 3, NULL,                 14.97),
  ( 7, 'ORD-0004', 2, 1, NULL,                 15.99),
  ( 8, 'ORD-0004', 5, 2, NULL,                  6.98),
  ( 9, 'ORD-0005', 2, 2, 'Birthday candle',    31.98),
  (10, 'ORD-0006', 4, 2, NULL,                  9.98),
  (11, 'ORD-0006', 6, 1, 'Oat milk',            4.49),
  (12, 'ORD-0007', 3, 1, NULL,                 24.99),
  (13, 'ORD-0008', 2, 1, NULL,                 15.99),
  (14, 'ORD-0008', 6, 1, NULL,                  4.49),
  (15, 'ORD-0009', 1, 1, NULL,                  7.99),
  (16, 'ORD-0009', 5, 1, NULL,                  3.49),
  (17, 'ORD-0010', 3, 1, NULL,                 24.99),
  (18, 'ORD-0010', 4, 2, NULL,                  9.98),
  (19, 'ORD-0011', 1, 1, NULL,                  7.99),
  (20, 'ORD-0012', 6, 2, NULL,                  8.98),
  (21, 'ORD-0012', 4, 1, NULL,                  4.99),
  (22, 'ORD-0013', 2, 1, 'Write "Happy Birthday"', 15.99),
  (23, 'ORD-0014', 3, 1, NULL,                 24.99),
  (24, 'ORD-0015', 2, 2, NULL,                 31.98);

-- Sales Database records: every paid or completed order is a sale; ORD-0007 was cancelled
INSERT INTO sales_records (orderID, recordedDate, amount)
  SELECT orderID, orderDate, orderTotal FROM orders WHERE orderStatus IN ('Completed', 'Paid');
INSERT INTO cancellation_records VALUES
  ('ORD-0007', 'Customer changed their mind', NULL, '2026-11-05');

INSERT INTO payments VALUES
  (1, 'ORD-0001', 19.48, 'cash', '2026-10-22', 'Approved'),
  (2, 'ORD-0002', 33.97, 'card', '2026-10-25', 'Approved'),
  (3, 'ORD-0014', 24.99, 'cash', '2026-11-21', 'Approved'),
  (4, 'ORD-0015', 31.98, 'card', '2026-11-21', 'Approved');
INSERT INTO cash_payments VALUES (1, 20.00, 0.52), (3, 30.00, 5.01);
INSERT INTO card_payments VALUES (2, 'debit', 'AUTH-48213'), (4, 'credit', 'AUTH-51907');
INSERT INTO receipts VALUES
  ('R-0001', 1, 19.48, '2026-10-22'),
  ('R-0002', 2, 33.97, '2026-10-25'),
  ('R-0003', 3, 24.99, '2026-11-21'),
  ('R-0004', 4, 31.98, '2026-11-21');

INSERT INTO reports VALUES
  (1, 1, 1, '2026-10-01', '2026-10-22', '2026-10-22', 'PDF'),
  (2, 1, 1, '2026-10-01', '2026-10-22', '2026-10-22', 'PDF');
INSERT INTO sales_reports       VALUES (1, 19.48, 2, 19.48);
INSERT INTO sales_report_orders VALUES (1, 'ORD-0001');
INSERT INTO inventory_reports      VALUES (2, 2);
INSERT INTO inventory_report_items VALUES (2, 1), (2, 4);
"""


def create_database(path=DB_PATH, seed=True):
    """Build the database from schema.sql. Deletes any existing database file first."""
    path = Path(path)
    if path.exists():
        path.unlink()
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA.read_text(encoding="utf-8"))
    if seed:
        conn.executescript(SEED)
    conn.commit()
    conn.close()
    migrate_database(path)
    return path


def migrate_database(path=DB_PATH):
    """Add menu image URLs to an existing database without replacing its data."""
    path = Path(path)
    if not path.exists():
        return

    conn = sqlite3.connect(path)
    try:
        tables = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'")}
        if "menu_items" not in tables:
            return
        columns = {row[1] for row in conn.execute("PRAGMA table_info(menu_items)")}
        if "imageURL" not in columns:
            conn.execute("ALTER TABLE menu_items ADD COLUMN imageURL TEXT")
        image_updates = []
        params = []
        for name in MENU_ITEM_IMAGES:
            previous_urls = PREVIOUS_MENU_ITEM_IMAGES.get(name, ())
            clause = "(name = ? AND (imageURL IS NULL OR TRIM(imageURL) = ''"
            params.append(name)
            if previous_urls:
                placeholders = ",".join("?" for _ in previous_urls)
                clause += f" OR imageURL IN ({placeholders})"
                params.extend(previous_urls)
            image_updates.append(clause + "))")
        needs_update = conn.execute(
            f"SELECT 1 FROM menu_items WHERE {' OR '.join(image_updates)} LIMIT 1",
            params).fetchone()
        if needs_update is None:
            conn.commit()
            return
        for name, image_url in MENU_ITEM_IMAGES.items():
            previous_urls = PREVIOUS_MENU_ITEM_IMAGES.get(name, ())
            condition = "imageURL IS NULL OR TRIM(imageURL) = ''"
            params = [image_url, name]
            if previous_urls:
                placeholders = ",".join("?" for _ in previous_urls)
                condition += f" OR imageURL IN ({placeholders})"
                params.extend(previous_urls)
            conn.execute(f"UPDATE menu_items SET imageURL = ? WHERE name = ? AND ({condition})",
                         params)
        conn.commit()
    finally:
        conn.close()


MENU_ITEM_IMAGES = {
    'Japanese Cheesecake 4" (Small)': (
        "/static/images/menu/souffle-cheesecake-small.png"),
    'Japanese Cheesecake 6" (Regular)': (
        "/static/images/menu/souffle-cheesecake-regular.png"),
    'Japanese Cheesecake 8" (Large)': (
        "/static/images/menu/souffle-cheesecake-large.png"),
    "Japanese Tart": (
        "/static/images/Designer (5).png"),
    "Americano": (
        "/static/images/Designer (6).png"),
    "Latte": (
        "/static/images/Designer (7).png"),
}

PREVIOUS_MENU_ITEM_IMAGES = {
    'Japanese Cheesecake 4" (Small)': (
        "/static/images/menu/souffle-cheesecake-small.svg",
        "https://images.unsplash.com/photo-1578985545062-69928b1d9587"
        "?auto=format&fit=crop&w=800&q=80",),
    'Japanese Cheesecake 6" (Regular)': (
        "/static/images/menu/souffle-cheesecake-regular.svg",
        "https://images.unsplash.com/photo-1565958011703-44f9829ba187"
        "?auto=format&fit=crop&w=800&q=80",),
    'Japanese Cheesecake 8" (Large)': (
        "/static/images/menu/souffle-cheesecake-large.svg",
        "https://images.unsplash.com/photo-1571115177098-24ec42ed204d"
        "?auto=format&fit=crop&w=800&q=80",),
    "Japanese Tart": (
        "/static/images/menu/japanese-tart.svg",
        "https://images.unsplash.com/photo-1488477181946-6428a0291777"
        "?auto=format&fit=crop&w=800&q=80",
        "https://chefstrawlicious.one/wp-content/uploads/2025/12/4-26.webp"),
    "Americano": (
        "https://images.unsplash.com/photo-1509042239860-a550ce710b93"
        "?auto=format&fit=crop&w=800&q=80",
        "https://res.cloudinary.com/joe-coffee/image/upload/"
        "v1572900558/menu-items/zjslvvn4zpqsbevdenvu.jpg",),
    "Latte": (
        "https://images.unsplash.com/photo-1461023058943-07fcbe16d735"
        "?auto=format&fit=crop&w=800&q=80",),
}


if __name__ == "__main__":
    created = create_database()
    print(f"Database created: {created}")
