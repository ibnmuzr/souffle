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

INSERT INTO inventory_items VALUES
  (1, 1, 'Eggs (dozen)',         4,  5),
  (2, 1, 'Cream cheese (kg)',   12,  8),
  (3, 1, 'Sugar (kg)',          10,  6),
  (4, 1, 'Coffee beans (kg)',    3,  4),
  (5, 1, 'Takeout boxes',      150, 100),
  (6, 2, 'Eggs (dozen)',         8,  5),
  (7, 2, 'Cream cheese (kg)',    9,  8);

INSERT INTO persons VALUES
  (1, 'Alex',   'Martin',   '514-555-0101', 'alex.martin@example.com'),
  (2, 'Sam',    'Tremblay', '514-555-0102', 'sam.tremblay@example.com'),
  (3, 'Jordan', 'Lee',      '514-555-0103', 'jordan.lee@example.com');

INSERT INTO managers  VALUES (1, 1, 1);
INSERT INTO employees VALUES (1, 2, 'sam.t', 'changeme', 'active', '2026-05-01');
INSERT INTO customers VALUES (1, 3);

INSERT INTO employee_accounts VALUES
  (1, 1, 1, 'sam.tremblay@example.com', 'changeme', 'active', 'uploads/void_cheque_1.pdf');

INSERT INTO menu_items VALUES
  (1, 'Japanese Cheesecake 4" (Small)',   'Fresh-baked, choice of toppings', 'Cheesecake',     7.99, 1),
  (2, 'Japanese Cheesecake 6" (Regular)', 'Fresh-baked, choice of toppings', 'Cheesecake',    15.99, 1),
  (3, 'Japanese Cheesecake 8" (Large)',   'Fresh-baked, choice of toppings', 'Cheesecake',    24.99, 1),
  (4, 'Japanese Tart',                    'Single tart',                     'Tart',           4.99, 1),
  (5, 'Americano',                        'Hot coffee',                      'Hot Beverages',  3.49, 1),
  (6, 'Latte',                            'Hot coffee with milk',            'Hot Beverages',  4.49, 1);

INSERT INTO promotions VALUES
  (1, 1, 'Fall Loyalty Week', 'percentage', 10, '2026-10-20', '2026-10-31'),
  (2, 1, 'Holiday Bundle',    'fixed',       5, '2026-12-01', '2026-12-24');
INSERT INTO shared_promotions VALUES (1, '2026-10-20', 'email');
INSERT INTO draft_promotions  VALUES (2, '2026-10-22');
INSERT INTO customer_shared_promotions VALUES (1, 1);

INSERT INTO orders VALUES
  ('ORD-0001', 1, 1, NULL, 2, '2026-10-22', 'in-store', 19.48, 'completed', 1001);
INSERT INTO order_lines VALUES
  (1, 'ORD-0001', 2, 1, 'Strawberry topping', 15.99),
  (2, 'ORD-0001', 5, 1, NULL,                  3.49);

INSERT INTO payments      VALUES (1, 'ORD-0001', 19.48, 'cash', '2026-10-22', 'approved');
INSERT INTO cash_payments VALUES (1, 20.00, 0.52);
INSERT INTO receipts      VALUES ('R-0001', 1, 19.48, '2026-10-22');

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
    return path


if __name__ == "__main__":
    created = create_database()
    print(f"Database created: {created}")
