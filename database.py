# database.py - SQLite database layer for PharmaCare
# All database operations live here.

import sqlite3
import hashlib
import os
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pharmacy.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def initialize_database():
    """Create tables if they do not exist. Safe to call on every start."""
    conn = get_connection()
    cur = conn.cursor()

    # Existing tables
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            username   TEXT UNIQUE NOT NULL,
            email      TEXT UNIQUE NOT NULL,
            password   TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS medicines (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            quantity    INTEGER NOT NULL DEFAULT 0,
            price       REAL NOT NULL DEFAULT 0.0,
            expiry_date TEXT NOT NULL,
            min_stock   INTEGER NOT NULL DEFAULT 10,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            bill_number      TEXT NOT NULL,
            medicine_id      INTEGER NOT NULL,
            medicine_name    TEXT NOT NULL,
            quantity         INTEGER NOT NULL,
            unit_price       REAL NOT NULL,
            total_price      REAL NOT NULL,
            customer_name    TEXT DEFAULT 'Walk-in Customer',
            cost_price       REAL DEFAULT 0,
            batch_id         INTEGER,
            transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (medicine_id) REFERENCES medicines(id)
        )""")

    # New tables for vendor / purchase / batch / expense
    cur.execute("""
        CREATE TABLE IF NOT EXISTS vendors (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            name           TEXT NOT NULL,
            contact_person TEXT,
            phone          TEXT,
            email          TEXT,
            address        TEXT,
            created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS purchases (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor_id       INTEGER NOT NULL,
            invoice_number  TEXT,
            purchase_date   TEXT NOT NULL,
            total_amount    REAL NOT NULL DEFAULT 0,
            notes           TEXT,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (vendor_id) REFERENCES vendors(id)
        )""")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS batches (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            medicine_id   INTEGER NOT NULL,
            purchase_id   INTEGER,
            batch_number  TEXT NOT NULL,
            quantity      INTEGER NOT NULL DEFAULT 0,
            cost_price    REAL NOT NULL DEFAULT 0,
            expiry_date   TEXT NOT NULL,
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (medicine_id) REFERENCES medicines(id),
            FOREIGN KEY (purchase_id) REFERENCES purchases(id)
        )""")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            category      TEXT NOT NULL,
            description   TEXT,
            amount        REAL NOT NULL,
            expense_date  TEXT NOT NULL,
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")

    # Migration: add cost_price / batch_id to transactions if missing (older DBs)
    try:
        cur.execute("SELECT cost_price FROM transactions LIMIT 1")
    except sqlite3.OperationalError:
        try:
            cur.execute("ALTER TABLE transactions ADD COLUMN cost_price REAL DEFAULT 0")
        except Exception:
            pass
    try:
        cur.execute("SELECT batch_id FROM transactions LIMIT 1")
    except sqlite3.OperationalError:
        try:
            cur.execute("ALTER TABLE transactions ADD COLUMN batch_id INTEGER")
        except Exception:
            pass

    conn.commit()

    # One-time: if medicines exist but no batches, create a default batch per medicine
    # so existing stock is still usable under the new batch system.
    meds = cur.execute("SELECT * FROM medicines WHERE quantity > 0").fetchall()
    for m in meds:
        cnt = cur.execute(
            "SELECT COUNT(*) FROM batches WHERE medicine_id=?", (m["id"],)
        ).fetchone()[0]
        if cnt == 0:
            exp = m["expiry_date"] or (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
            cur.execute(
                """INSERT INTO batches (medicine_id, batch_number, quantity, cost_price, expiry_date)
                   VALUES (?, ?, ?, ?, ?)""",
                (m["id"], "LEGACY-001", m["quantity"], 0.0, exp)
            )
    conn.commit()
    conn.close()


# ── User operations ──────────────────────────────────────────────────────────

def create_user(username, email, password):
    try:
        conn = get_connection()
        conn.execute(
            "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
            (username.strip(), email.strip().lower(), hash_password(password)))
        conn.commit()
        conn.close()
        return True, "Account created successfully."
    except sqlite3.IntegrityError as e:
        try:
            conn.close()
        except Exception:
            pass
        if "username" in str(e):
            return False, "Username already taken."
        if "email" in str(e):
            return False, "Email already registered."
        return False, str(e)
    except Exception as e:
        return False, str(e)


def get_user_by_username(username):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM users WHERE username=?", (username.strip(),)
    ).fetchone()
    conn.close()
    return row


def get_user_by_email(email):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM users WHERE email=?", (email.strip().lower(),)
    ).fetchone()
    conn.close()
    return row


def validate_login(username, password):
    user = get_user_by_username(username)
    if not user:
        return False, "Username not found.", None
    if user["password"] != hash_password(password):
        return False, "Incorrect password.", None
    return True, "Login successful.", user["username"]


def update_password(email, new_password):
    try:
        conn = get_connection()
        conn.execute(
            "UPDATE users SET password=? WHERE email=?",
            (hash_password(new_password), email.strip().lower())
        )
        conn.commit()
        conn.close()
        return True, "Password reset successfully."
    except Exception as e:
        return False, str(e)


# ── Medicine operations ───────────────────────────────────────────────────────

def add_medicine(name, quantity, price, expiry_date, min_stock):
    """Add a medicine to the catalogue. Quantity starts at 0;
    stock is added via Purchases (batches)."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO medicines (name, quantity, price, expiry_date, min_stock) VALUES (?,?,?,?,?)",
            (name.strip(), int(quantity), float(price), expiry_date, int(min_stock))
        )
        mid = cur.lastrowid
        # If initial quantity given, create a simple batch
        if int(quantity) > 0:
            cur.execute(
                """INSERT INTO batches (medicine_id, batch_number, quantity, cost_price, expiry_date)
                   VALUES (?, ?, ?, 0, ?)""",
                (mid, "INIT-001", int(quantity), expiry_date)
            )
        conn.commit()
        conn.close()
        return True, "Medicine added successfully."
    except Exception as e:
        return False, str(e)


def get_all_medicines():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM medicines ORDER BY name").fetchall()
    conn.close()
    return rows


def get_medicine_by_id(mid):
    conn = get_connection()
    row = conn.execute("SELECT * FROM medicines WHERE id=?", (mid,)).fetchone()
    conn.close()
    return row


def search_medicines(query):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM medicines WHERE name LIKE ? ORDER BY name",
        (f"%{query}%",)
    ).fetchall()
    conn.close()
    return rows


def update_medicine(mid, name, quantity, price, expiry_date, min_stock):
    """Update catalogue fields. Quantity is kept in sync with batches total."""
    try:
        conn = get_connection()
        conn.execute(
            """UPDATE medicines
               SET name=?, quantity=?, price=?, expiry_date=?,
                   min_stock=?, updated_at=CURRENT_TIMESTAMP WHERE id=?""",
            (name.strip(), int(quantity), float(price), expiry_date, int(min_stock), mid)
        )
        conn.commit()
        conn.close()
        return True, "Medicine updated successfully."
    except Exception as e:
        return False, str(e)


def delete_medicine(mid):
    try:
        conn = get_connection()
        # Also remove batches for this medicine
        conn.execute("DELETE FROM batches WHERE medicine_id=?", (mid,))
        conn.execute("DELETE FROM medicines WHERE id=?", (mid,))
        conn.commit()
        conn.close()
        return True, "Medicine deleted successfully."
    except Exception as e:
        return False, str(e)


def _sync_medicine_quantity(conn, medicine_id):
    """Recalculate medicines.quantity from sum of batch quantities."""
    total = conn.execute(
        "SELECT COALESCE(SUM(quantity),0) FROM batches WHERE medicine_id=?",
        (medicine_id,)
    ).fetchone()[0]
    # Also update the "earliest" expiry for display convenience
    earliest = conn.execute(
        """SELECT expiry_date FROM batches
           WHERE medicine_id=? AND quantity>0
           ORDER BY expiry_date ASC LIMIT 1""",
        (medicine_id,)
    ).fetchone()
    exp = earliest["expiry_date"] if earliest else datetime.now().strftime("%Y-%m-%d")
    conn.execute(
        "UPDATE medicines SET quantity=?, expiry_date=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
        (total, exp, medicine_id)
    )
    return total


def reduce_medicine_quantity(mid, amount):
    """Legacy simple reduce (kept for compatibility). Prefer FEFO version."""
    try:
        conn = get_connection()
        row = conn.execute(
            "SELECT quantity FROM medicines WHERE id=?", (mid,)
        ).fetchone()
        if not row:
            conn.close()
            return False, "Medicine not found."
        new_q = row["quantity"] - amount
        if new_q < 0:
            conn.close()
            return False, "Insufficient stock."
        conn.execute(
            "UPDATE medicines SET quantity=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (new_q, mid)
        )
        conn.commit()
        conn.close()
        return True, f"Remaining: {new_q}"
    except Exception as e:
        return False, str(e)


def get_low_stock_medicines():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM medicines WHERE quantity <= min_stock ORDER BY quantity"
    ).fetchall()
    conn.close()
    return rows


def get_expired_medicines():
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM medicines WHERE expiry_date <= ? ORDER BY expiry_date",
        (today,)
    ).fetchall()
    conn.close()
    return rows


# ── Batch / FEFO helpers ──────────────────────────────────────────────────────

def get_batches_for_medicine(medicine_id, only_available=True):
    """Return batches ordered by expiry (FEFO)."""
    conn = get_connection()
    if only_available:
        rows = conn.execute(
            """SELECT * FROM batches
               WHERE medicine_id=? AND quantity > 0
               ORDER BY expiry_date ASC""",
            (medicine_id,)
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT * FROM batches WHERE medicine_id=?
               ORDER BY expiry_date ASC""",
            (medicine_id,)
        ).fetchall()
    conn.close()
    return rows


def get_all_batches():
    """All batches with medicine name for inventory reports."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT b.*, m.name AS medicine_name, m.price AS selling_price
           FROM batches b
           JOIN medicines m ON m.id = b.medicine_id
           ORDER BY m.name, b.expiry_date"""
    ).fetchall()
    conn.close()
    return rows


def get_expiring_soon_batches(days=30):
    today = datetime.now().date()
    limit = (today + timedelta(days=days)).strftime("%Y-%m-%d")
    today_s = today.strftime("%Y-%m-%d")
    conn = get_connection()
    rows = conn.execute(
        """SELECT b.*, m.name AS medicine_name
           FROM batches b
           JOIN medicines m ON m.id = b.medicine_id
           WHERE b.quantity > 0 AND b.expiry_date >= ? AND b.expiry_date <= ?
           ORDER BY b.expiry_date""",
        (today_s, limit)
    ).fetchall()
    conn.close()
    return rows


def get_expired_batches():
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_connection()
    rows = conn.execute(
        """SELECT b.*, m.name AS medicine_name
           FROM batches b
           JOIN medicines m ON m.id = b.medicine_id
           WHERE b.quantity > 0 AND b.expiry_date < ?
           ORDER BY b.expiry_date""",
        (today,)
    ).fetchall()
    conn.close()
    return rows


def batch_status(expiry_date_str):
    """Return (status_label, tag) based on current date."""
    try:
        exp = datetime.strptime(expiry_date_str, "%Y-%m-%d").date()
    except ValueError:
        return "Invalid", "expired"
    today = datetime.now().date()
    if exp < today:
        return "⚠ Expired", "expired"
    if exp <= today + timedelta(days=30):
        return "⚡ Expiring Soon", "low"
    return "✔ OK", ""


def fefo_allocate(medicine_id, qty_needed):
    """
    Allocate stock using FEFO (earliest expiry first).
    Returns list of (batch_id, take_qty, cost_price) or empty list if insufficient.
    Does NOT update the database – caller must call fefo_commit after confirmation.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_connection()
    batches = conn.execute(
        """SELECT * FROM batches
           WHERE medicine_id=? AND quantity > 0 AND expiry_date >= ?
           ORDER BY expiry_date ASC""",
        (medicine_id, today)
    ).fetchall()
    conn.close()

    remaining = qty_needed
    allocation = []
    for b in batches:
        if remaining <= 0:
            break
        take = min(b["quantity"], remaining)
        allocation.append((b["id"], take, float(b["cost_price"])))
        remaining -= take
    if remaining > 0:
        return []  # not enough non-expired stock
    return allocation


def fefo_commit(medicine_id, allocation):
    """
    Apply the allocation returned by fefo_allocate.
    Returns list of (batch_id, qty, cost_price) that were actually deducted.
    """
    conn = get_connection()
    try:
        for batch_id, take, cost in allocation:
            row = conn.execute(
                "SELECT quantity FROM batches WHERE id=?", (batch_id,)
            ).fetchone()
            if not row or row["quantity"] < take:
                conn.rollback()
                conn.close()
                return False, "Stock changed – please try again."
            conn.execute(
                "UPDATE batches SET quantity = quantity - ? WHERE id=?",
                (take, batch_id)
            )
        _sync_medicine_quantity(conn, medicine_id)
        conn.commit()
        conn.close()
        return True, allocation
    except Exception as e:
        conn.rollback()
        conn.close()
        return False, str(e)


# ── Vendor operations ─────────────────────────────────────────────────────────

def add_vendor(name, contact_person="", phone="", email="", address=""):
    try:
        name = name.strip()
        if not name:
            return False, "Vendor name is required."
        conn = get_connection()
        # simple duplicate check by name
        exists = conn.execute(
            "SELECT id FROM vendors WHERE lower(name)=lower(?)", (name,)
        ).fetchone()
        if exists:
            conn.close()
            return False, "A vendor with this name already exists."
        conn.execute(
            """INSERT INTO vendors (name, contact_person, phone, email, address)
               VALUES (?,?,?,?,?)""",
            (name, contact_person.strip(), phone.strip(),
             email.strip().lower(), address.strip())
        )
        conn.commit()
        conn.close()
        return True, "Vendor added successfully."
    except Exception as e:
        return False, str(e)


def update_vendor(vid, name, contact_person="", phone="", email="", address=""):
    try:
        name = name.strip()
        if not name:
            return False, "Vendor name is required."
        conn = get_connection()
        conn.execute(
            """UPDATE vendors SET name=?, contact_person=?, phone=?,
               email=?, address=? WHERE id=?""",
            (name, contact_person.strip(), phone.strip(),
             email.strip().lower(), address.strip(), vid)
        )
        conn.commit()
        conn.close()
        return True, "Vendor updated successfully."
    except Exception as e:
        return False, str(e)


def delete_vendor(vid):
    try:
        conn = get_connection()
        # prevent delete if purchases exist
        cnt = conn.execute(
            "SELECT COUNT(*) FROM purchases WHERE vendor_id=?", (vid,)
        ).fetchone()[0]
        if cnt > 0:
            conn.close()
            return False, "Cannot delete vendor that has purchase records."
        conn.execute("DELETE FROM vendors WHERE id=?", (vid,))
        conn.commit()
        conn.close()
        return True, "Vendor deleted."
    except Exception as e:
        return False, str(e)


def get_all_vendors():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM vendors ORDER BY name").fetchall()
    conn.close()
    return rows


def get_vendor_by_id(vid):
    conn = get_connection()
    row = conn.execute("SELECT * FROM vendors WHERE id=?", (vid,)).fetchone()
    conn.close()
    return row


def search_vendors(query):
    conn = get_connection()
    q = f"%{query}%"
    rows = conn.execute(
        """SELECT * FROM vendors
           WHERE name LIKE ? OR contact_person LIKE ? OR phone LIKE ?
           ORDER BY name""",
        (q, q, q)
    ).fetchall()
    conn.close()
    return rows


# ── Purchase operations ───────────────────────────────────────────────────────

def record_purchase(vendor_id, invoice_number, purchase_date, items, notes=""):
    """
    items = list of dicts:
      {medicine_id, batch_number, quantity, cost_price, expiry_date}

    Atomic: either everything is saved or nothing is.
    Returns (ok, message, purchase_id or None)
    """
    if not items:
        return False, "Add at least one medicine line.", None
    if not purchase_date:
        return False, "Purchase date is required.", None

    # Validate dates and reject past expiry for new stock
    today = datetime.now().date()
    for it in items:
        try:
            exp = datetime.strptime(it["expiry_date"], "%Y-%m-%d").date()
        except (ValueError, KeyError):
            return False, f"Invalid expiry date for batch {it.get('batch_number','')}.", None
        if exp < today:
            return False, (
                f"Expiry date {it['expiry_date']} is already past. "
                "Cannot add expired stock for sale."
            ), None
        if int(it["quantity"]) <= 0:
            return False, "Quantity must be greater than zero.", None
        if float(it["cost_price"]) < 0:
            return False, "Cost price cannot be negative.", None

    conn = get_connection()
    try:
        # Duplicate invoice check (same vendor + same invoice)
        inv = (invoice_number or "").strip()
        if inv:
            dup = conn.execute(
                "SELECT id FROM purchases WHERE vendor_id=? AND invoice_number=?",
                (vendor_id, inv)
            ).fetchone()
            if dup:
                conn.close()
                return False, "This invoice number already exists for the selected vendor.", None

        total = sum(int(it["quantity"]) * float(it["cost_price"]) for it in items)
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO purchases (vendor_id, invoice_number, purchase_date, total_amount, notes)
               VALUES (?,?,?,?,?)""",
            (vendor_id, inv or None, purchase_date, total, notes.strip())
        )
        purchase_id = cur.lastrowid

        for it in items:
            mid = int(it["medicine_id"])
            qty = int(it["quantity"])
            cost = float(it["cost_price"])
            batch_no = str(it["batch_number"]).strip()
            exp = it["expiry_date"]

            # Warn-level: same medicine + same batch already exists – still allow
            # but we keep them as separate rows if quantities differ; for simplicity
            # we always insert a new batch row (FEFO works with multiple rows).
            cur.execute(
                """INSERT INTO batches
                   (medicine_id, purchase_id, batch_number, quantity, cost_price, expiry_date)
                   VALUES (?,?,?,?,?,?)""",
                (mid, purchase_id, batch_no, qty, cost, exp)
            )
            _sync_medicine_quantity(conn, mid)

        conn.commit()
        conn.close()
        return True, f"Purchase recorded. Total cost: ₹{total:.2f}", purchase_id
    except Exception as e:
        conn.rollback()
        conn.close()
        return False, str(e), None


def get_all_purchases():
    conn = get_connection()
    rows = conn.execute(
        """SELECT p.*, v.name AS vendor_name
           FROM purchases p
           JOIN vendors v ON v.id = p.vendor_id
           ORDER BY p.purchase_date DESC, p.id DESC"""
    ).fetchall()
    conn.close()
    return rows


def get_purchases_by_date(start, end):
    conn = get_connection()
    rows = conn.execute(
        """SELECT p.*, v.name AS vendor_name
           FROM purchases p
           JOIN vendors v ON v.id = p.vendor_id
           WHERE p.purchase_date BETWEEN ? AND ?
           ORDER BY p.purchase_date DESC""",
        (start, end)
    ).fetchall()
    conn.close()
    return rows


def get_purchases_by_vendor(vendor_id):
    conn = get_connection()
    rows = conn.execute(
        """SELECT p.*, v.name AS vendor_name
           FROM purchases p
           JOIN vendors v ON v.id = p.vendor_id
           WHERE p.vendor_id=?
           ORDER BY p.purchase_date DESC""",
        (vendor_id,)
    ).fetchall()
    conn.close()
    return rows


def get_purchase_items(purchase_id):
    conn = get_connection()
    rows = conn.execute(
        """SELECT b.*, m.name AS medicine_name
           FROM batches b
           JOIN medicines m ON m.id = b.medicine_id
           WHERE b.purchase_id=?
           ORDER BY m.name""",
        (purchase_id,)
    ).fetchall()
    conn.close()
    return rows


# ── Expense operations ────────────────────────────────────────────────────────

def add_expense(category, description, amount, expense_date):
    try:
        if not category.strip():
            return False, "Category is required."
        if float(amount) <= 0:
            return False, "Amount must be greater than zero."
        datetime.strptime(expense_date, "%Y-%m-%d")
        conn = get_connection()
        conn.execute(
            """INSERT INTO expenses (category, description, amount, expense_date)
               VALUES (?,?,?,?)""",
            (category.strip(), description.strip(), float(amount), expense_date)
        )
        conn.commit()
        conn.close()
        return True, "Expense recorded."
    except ValueError:
        return False, "Date must be YYYY-MM-DD."
    except Exception as e:
        return False, str(e)


def get_expenses_by_date(start, end):
    conn = get_connection()
    rows = conn.execute(
        """SELECT * FROM expenses
           WHERE expense_date BETWEEN ? AND ?
           ORDER BY expense_date DESC""",
        (start, end)
    ).fetchall()
    conn.close()
    return rows


def get_all_expenses():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM expenses ORDER BY expense_date DESC"
    ).fetchall()
    conn.close()
    return rows


def delete_expense(eid):
    try:
        conn = get_connection()
        conn.execute("DELETE FROM expenses WHERE id=?", (eid,))
        conn.commit()
        conn.close()
        return True, "Expense deleted."
    except Exception as e:
        return False, str(e)


# ── Transaction / sales operations ────────────────────────────────────────────

def add_transaction(bill_number, medicine_id, medicine_name,
                    quantity, unit_price, total_price,
                    customer_name="Walk-in Customer",
                    cost_price=0.0, batch_id=None):
    try:
        conn = get_connection()
        conn.execute(
            """INSERT INTO transactions
               (bill_number, medicine_id, medicine_name, quantity,
                unit_price, total_price, customer_name, cost_price, batch_id)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (bill_number, medicine_id, medicine_name, quantity,
             unit_price, total_price, customer_name, cost_price, batch_id)
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def get_all_transactions():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM transactions ORDER BY transaction_date DESC"
    ).fetchall()
    conn.close()
    return rows


def get_transactions_by_date(start, end):
    conn = get_connection()
    rows = conn.execute(
        """SELECT * FROM transactions
           WHERE DATE(transaction_date) BETWEEN ? AND ?
           ORDER BY transaction_date DESC""",
        (start, end)
    ).fetchall()
    conn.close()
    return rows


# ── Financial / dashboard stats ───────────────────────────────────────────────

def get_dashboard_stats():
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_connection()
    tm = conn.execute("SELECT COUNT(*) FROM medicines").fetchone()[0]
    ts = conn.execute(
        "SELECT COALESCE(SUM(total_price),0) FROM transactions"
    ).fetchone()[0]
    ls = conn.execute(
        "SELECT COUNT(*) FROM medicines WHERE quantity <= min_stock"
    ).fetchone()[0]
    ex = conn.execute(
        "SELECT COUNT(*) FROM medicines WHERE expiry_date <= ?", (today,)
    ).fetchone()[0]
    # batches expiring in 30 days
    limit = (datetime.now().date() + timedelta(days=30)).strftime("%Y-%m-%d")
    exp_soon = conn.execute(
        """SELECT COUNT(*) FROM batches
           WHERE quantity > 0 AND expiry_date >= ? AND expiry_date <= ?""",
        (today, limit)
    ).fetchone()[0]
    conn.close()
    return {
        "total_medicines": tm,
        "total_sales": round(ts, 2),
        "low_stock_count": ls,
        "expired_count": ex,
        "expiring_soon": exp_soon,
    }


def get_financial_summary(start, end):
    """
    Revenue, COGS, Gross Profit, Expenses, Net Profit, Purchases total.
    Uses completed transactions only.
    """
    conn = get_connection()
    revenue = conn.execute(
        """SELECT COALESCE(SUM(total_price),0) FROM transactions
           WHERE DATE(transaction_date) BETWEEN ? AND ?""",
        (start, end)
    ).fetchone()[0]
    cogs = conn.execute(
        """SELECT COALESCE(SUM(quantity * cost_price),0) FROM transactions
           WHERE DATE(transaction_date) BETWEEN ? AND ?""",
        (start, end)
    ).fetchone()[0]
    expenses = conn.execute(
        """SELECT COALESCE(SUM(amount),0) FROM expenses
           WHERE expense_date BETWEEN ? AND ?""",
        (start, end)
    ).fetchone()[0]
    purchases = conn.execute(
        """SELECT COALESCE(SUM(total_amount),0) FROM purchases
           WHERE purchase_date BETWEEN ? AND ?""",
        (start, end)
    ).fetchone()[0]
    conn.close()
    revenue = float(revenue)
    cogs = float(cogs)
    expenses = float(expenses)
    purchases = float(purchases)
    gross = revenue - cogs
    net = gross - expenses
    return {
        "revenue": round(revenue, 2),
        "cogs": round(cogs, 2),
        "gross_profit": round(gross, 2),
        "expenses": round(expenses, 2),
        "net_profit": round(net, 2),
        "purchases_total": round(purchases, 2),
    }
