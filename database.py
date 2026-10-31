# database.py - SQLite database layer for PharmaCare
# All database operations live here.

import sqlite3
import hashlib
import os
import secrets
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pharmacy.db")
PASSWORD_HASH_ITERATIONS = 600_000
PASSWORD_HASH_PREFIX = "pbkdf2_sha256"
SALES_GST_RATE = 12.0


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def hash_password(password):
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_HASH_ITERATIONS
    )
    return f"{PASSWORD_HASH_PREFIX}${PASSWORD_HASH_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(stored_hash, password):
    """Verify PBKDF2 hashes and legacy unsalted SHA-256 hashes."""
    if not stored_hash:
        return False
    if stored_hash.startswith(f"{PASSWORD_HASH_PREFIX}$"):
        try:
            prefix, iterations_text, salt_hex, digest_hex = stored_hash.split("$", 3)
            iterations = int(iterations_text)
            salt = bytes.fromhex(salt_hex)
            expected = bytes.fromhex(digest_hex)
            if prefix != PASSWORD_HASH_PREFIX or not 100_000 <= iterations <= 2_000_000:
                return False
        except (TypeError, ValueError):
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return secrets.compare_digest(actual, expected)

    # Existing accounts used SHA-256 hex digests. Accept them only so a valid
    # login can transparently replace the old hash with a salted PBKDF2 hash.
    if len(stored_hash) == 64:
        try:
            int(stored_hash, 16)
        except ValueError:
            return False
        legacy = hashlib.sha256(password.encode("utf-8")).hexdigest()
        return secrets.compare_digest(stored_hash, legacy)
    return False


_DUMMY_PASSWORD_HASH = hash_password(secrets.token_hex(32))


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

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sales_invoices (
            invoice_number TEXT PRIMARY KEY,
            invoice_date TEXT NOT NULL,
            pharmacy_name TEXT NOT NULL DEFAULT 'PharmaCare',
            pharmacist_name TEXT,
            pharmacist_email TEXT,
            customer_name TEXT NOT NULL DEFAULT 'Walk-in Customer',
            customer_email TEXT,
            customer_address TEXT,
            subtotal REAL NOT NULL DEFAULT 0,
            discount_amount REAL NOT NULL DEFAULT 0,
            gst_rate REAL NOT NULL DEFAULT 0,
            gst_mode TEXT NOT NULL DEFAULT 'local',
            cgst_amount REAL NOT NULL DEFAULT 0,
            sgst_amount REAL NOT NULL DEFAULT 0,
            igst_amount REAL NOT NULL DEFAULT 0,
            grand_total REAL NOT NULL DEFAULT 0,
            payment_method TEXT NOT NULL DEFAULT 'Cash',
            payment_status TEXT NOT NULL DEFAULT 'Paid',
            pharmacist_user_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

    # Additive invoice fields preserve existing purchases, batches and sales.
    migrations = {
        "purchases": {
            "supplier_invoice_number": "TEXT",
            "subtotal": "REAL NOT NULL DEFAULT 0",
            "gst_rate": "REAL NOT NULL DEFAULT 0",
            "gst_mode": "TEXT NOT NULL DEFAULT 'local'",
            "cgst_amount": "REAL NOT NULL DEFAULT 0",
            "sgst_amount": "REAL NOT NULL DEFAULT 0",
            "igst_amount": "REAL NOT NULL DEFAULT 0",
            "payment_method": "TEXT NOT NULL DEFAULT 'Cash'",
            "payment_status": "TEXT NOT NULL DEFAULT 'Paid'",
            "pharmacy_name": "TEXT NOT NULL DEFAULT 'PharmaCare'",
            "pharmacist_name": "TEXT",
            "pharmacist_email": "TEXT",
        },
        "batches": {
            "manufacture_date": "TEXT",
            "gst_rate": "REAL NOT NULL DEFAULT 0",
            "gst_amount": "REAL NOT NULL DEFAULT 0",
        },
        "transactions": {
            "discount_amount": "REAL NOT NULL DEFAULT 0",
            "gst_rate": "REAL NOT NULL DEFAULT 0",
            "gst_amount": "REAL NOT NULL DEFAULT 0",
        },
    }
    for table, definitions in migrations.items():
        existing = {row["name"] for row in cur.execute(
            f"PRAGMA table_info({table})").fetchall()}
        for column, definition in definitions.items():
            if column not in existing:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    # Older purchases stored the pre-tax amount in total_amount.
    cur.execute("UPDATE purchases SET subtotal=total_amount WHERE subtotal=0")

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
            # Preserve the expiry date already recorded for this medicine.
            # Never invent an expiry date for legacy stock.
            exp = (m["expiry_date"] or "").strip()
            try:
                datetime.strptime(exp, "%Y-%m-%d")
            except (TypeError, ValueError):
                # Keep the legacy quantity untouched; it requires pharmacist
                # verification before it can be represented as an expiry-tracked batch.
                continue
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


def validate_login(email, password):
    """Authenticate an account using its email address and password."""
    user = get_user_by_email(email)
    if not user:
        verify_password(_DUMMY_PASSWORD_HASH, password)
        return False, "Invalid email or password.", None
    if not verify_password(user["password"], password):
        if not user["password"].startswith(f"{PASSWORD_HASH_PREFIX}$"):
            verify_password(_DUMMY_PASSWORD_HASH, password)
        return False, "Invalid email or password.", None
    if not user["password"].startswith(f"{PASSWORD_HASH_PREFIX}$"):
        upgraded_hash = hash_password(password)
        conn = get_connection()
        try:
            conn.execute(
                "UPDATE users SET password=? WHERE id=? AND password=?",
                (upgraded_hash, user["id"], user["password"]),
            )
            conn.commit()
        finally:
            conn.close()
    # Keep returning the username because the dashboard currently displays it.
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
    """
    Return the pharmacy's medicine catalogue.

    Repair quantity/batch inconsistencies before returning rows. Existing legacy
    stock is preserved when it has no batch records; it is never overwritten
    with zero merely because batch tracking was introduced later.
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        medicines = cur.execute(
            "SELECT * FROM medicines ORDER BY name"
        ).fetchall()

        for medicine in medicines:
            mid = medicine["id"]
            batch_count = cur.execute(
                "SELECT COUNT(*) FROM batches WHERE medicine_id=?", (mid,)
            ).fetchone()[0]

            # For legacy medicines that have quantity but no batches, create a
            # batch only when the recorded expiry date is valid. Keep the legacy
            # quantity untouched if expiry needs pharmacist verification.
            if batch_count == 0 and int(medicine["quantity"] or 0) > 0:
                expiry = (medicine["expiry_date"] or "").strip()
                try:
                    datetime.strptime(expiry, "%Y-%m-%d")
                except (TypeError, ValueError):
                    continue
                cur.execute(
                    """INSERT INTO batches
                       (medicine_id, batch_number, quantity, cost_price, expiry_date)
                       VALUES (?, ?, ?, ?, ?)""",
                    (mid, "LEGACY-001", int(medicine["quantity"]), 0.0, expiry)
                )
                batch_count = 1

            # Only batch-backed records are synchronized. This prevents an empty
            # batch table from erasing old inventory.
            if batch_count > 0:
                _sync_medicine_quantity(conn, mid)

        conn.commit()
        rows = cur.execute(
            "SELECT * FROM medicines ORDER BY name"
        ).fetchall()
        return rows
    finally:
        conn.close()


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

def _generate_invoice_id(conn, prefix):
    table = "sales_invoices" if prefix == "SALE" else "purchases"
    while True:
        invoice_id = f"{prefix}-{datetime.now():%Y%m%d}-{secrets.token_hex(4).upper()}"
        if not conn.execute(
            f"SELECT 1 FROM {table} WHERE invoice_number=?", (invoice_id,)
        ).fetchone():
            return invoice_id


def generate_invoice_id(prefix="SALE"):
    conn = get_connection()
    try:
        return _generate_invoice_id(conn, prefix)
    finally:
        conn.close()


def calculate_gst(amount, rate, mode="local"):
    """Return a rounded GST split and grand total for an invoice subtotal."""
    taxable = round(max(float(amount), 0.0), 2)
    rate = float(rate)
    if rate < 0 or rate > 100:
        raise ValueError("GST rate must be between 0 and 100%.")
    tax = round(taxable * rate / 100.0, 2)
    if mode == "interstate":
        cgst = sgst = 0.0
        igst = tax
    else:
        cgst = round(tax / 2.0, 2)
        sgst = round(tax - cgst, 2)
        igst = 0.0
    return {
        "cgst_amount": cgst,
        "sgst_amount": sgst,
        "igst_amount": igst,
        "gst_amount": tax,
        "grand_total": round(taxable + tax, 2),
    }


def record_purchase(vendor_id, invoice_number, purchase_date, items, notes="",
                    gst_rate=0.0, gst_mode="local", payment_method="Cash",
                    payment_status="Paid", pharmacy_name="PharmaCare",
                    pharmacist_name="", pharmacist_email=""):
    """Save a vendor invoice, its batch lines, and stock updates atomically."""
    if not items:
        return False, "Add at least one medicine line.", None
    try:
        datetime.strptime(purchase_date, "%Y-%m-%d")
        gst_rate = float(gst_rate)
        if gst_mode not in ("local", "interstate"):
            raise ValueError("Select a valid GST type.")
        inv = (invoice_number or "").strip()
        today = datetime.now().date()
        subtotal = 0.0
        for it in items:
            exp = datetime.strptime(it["expiry_date"], "%Y-%m-%d").date()
            mfg = (it.get("manufacture_date") or "").strip()
            if mfg:
                mfg_date = datetime.strptime(mfg, "%Y-%m-%d").date()
                if mfg_date > exp:
                    raise ValueError("Manufacturing date cannot be after expiry date.")
            if exp < today:
                raise ValueError("Cannot add stock with an expiry date in the past.")
            qty = int(it["quantity"])
            cost = float(it["cost_price"])
            if qty <= 0 or cost < 0:
                raise ValueError("Quantity must be positive and cost cannot be negative.")
            subtotal += qty * cost
        subtotal = round(subtotal, 2)
        tax = calculate_gst(subtotal, gst_rate, gst_mode)
    except (ValueError, KeyError, TypeError) as exc:
        return False, str(exc) or "Enter valid invoice details.", None

    conn = get_connection()
    try:
        if inv:
            dup = conn.execute(
                """SELECT id FROM purchases WHERE vendor_id=?
                   AND (supplier_invoice_number=? OR invoice_number=?)""",
                (vendor_id, inv, inv)
            ).fetchone()
            if dup:
                return False, "This vendor invoice number already exists.", None

        invoice_id = _generate_invoice_id(conn, "PUR")
        purchase_id = conn.execute(
            """INSERT INTO purchases
               (vendor_id, invoice_number, supplier_invoice_number, purchase_date,
                subtotal, total_amount, gst_rate, gst_mode, cgst_amount,
                sgst_amount, igst_amount, payment_method, payment_status,
                pharmacy_name, pharmacist_name, pharmacist_email, notes)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (vendor_id, invoice_id, inv or None, purchase_date, subtotal,
             tax["grand_total"], gst_rate, gst_mode, tax["cgst_amount"],
             tax["sgst_amount"], tax["igst_amount"], payment_method,
             payment_status, pharmacy_name, pharmacist_name, pharmacist_email,
             (notes or "").strip())
        ).lastrowid

        for it in items:
            mid = int(it["medicine_id"])
            qty = int(it["quantity"])
            cost = float(it["cost_price"])
            batch_no = str(it["batch_number"]).strip()
            line_tax = calculate_gst(qty * cost, gst_rate, gst_mode)
            conn.execute(
                """INSERT INTO batches
                   (medicine_id, purchase_id, batch_number, quantity, cost_price,
                    expiry_date, manufacture_date, gst_rate, gst_amount)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (mid, purchase_id, batch_no, qty, cost, it["expiry_date"],
                 (it.get("manufacture_date") or "").strip() or None,
                 gst_rate, line_tax["gst_amount"])
            )
            _sync_medicine_quantity(conn, mid)

        conn.commit()
        return True, f"Purchase invoice {invoice_id} recorded. Total: ₹{tax['grand_total']:.2f}", purchase_id
    except Exception as e:
        conn.rollback()
        return False, str(e), None
    finally:
        conn.close()


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


def get_purchase_invoice(purchase_id):
    conn = get_connection()
    try:
        row = conn.execute(
            """SELECT p.*, v.name AS vendor_name, v.contact_person AS vendor_contact,
                      v.phone AS vendor_phone, v.email AS vendor_email,
                      v.address AS vendor_address
               FROM purchases p JOIN vendors v ON v.id=p.vendor_id WHERE p.id=?""",
            (purchase_id,)
        ).fetchone()
        if not row:
            return None
        invoice = dict(row)
        invoice["items"] = [dict(item) for item in conn.execute(
            """SELECT b.*, m.name AS medicine_name
               FROM batches b JOIN medicines m ON m.id=b.medicine_id
               WHERE b.purchase_id=? ORDER BY b.id""",
            (purchase_id,)
        ).fetchall()]
        return invoice
    finally:
        conn.close()


def get_purchase_invoices(limit=500):
    conn = get_connection()
    try:
        return conn.execute(
            """SELECT p.id, p.invoice_number, p.purchase_date, p.total_amount,
                      p.payment_status, v.name AS vendor_name
               FROM purchases p JOIN vendors v ON v.id=p.vendor_id
               ORDER BY p.purchase_date DESC, p.id DESC LIMIT ?""",
            (limit,)
        ).fetchall()
    finally:
        conn.close()


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

def _insert_transaction(conn, bill_number, medicine_id, medicine_name,
                        quantity, unit_price, total_price, customer_name,
                        cost_price, batch_id, user_id=None,
                        discount_amount=0.0, gst_rate=0.0, gst_amount=0.0):
    """Insert a sale row, including user_id when the database requires it."""
    columns = {row["name"] for row in conn.execute(
        "PRAGMA table_info(transactions)").fetchall()}
    fields = ["bill_number", "medicine_id", "medicine_name", "quantity",
              "unit_price", "total_price", "customer_name", "cost_price",
              "batch_id", "discount_amount", "gst_rate", "gst_amount"]
    values = [bill_number, medicine_id, medicine_name, quantity, unit_price,
              total_price, customer_name, cost_price, batch_id,
              discount_amount, gst_rate, gst_amount]
    fields = [field for field in fields if field in columns]
    value_by_field = dict(zip(
        ["bill_number", "medicine_id", "medicine_name", "quantity",
         "unit_price", "total_price", "customer_name", "cost_price", "batch_id",
         "discount_amount", "gst_rate", "gst_amount"], values
    ))
    values = [value_by_field[field] for field in fields]

    if "user_id" in columns:
        if user_id is None:
            medicine = conn.execute(
                "SELECT user_id FROM medicines WHERE id=?", (medicine_id,)
            ).fetchone()
            user_id = medicine["user_id"] if medicine else None
        if user_id is None:
            raise ValueError("Could not determine the pharmacist for this bill.")
        fields.insert(0, "user_id")
        values.insert(0, user_id)

    placeholders = ",".join("?" for _ in fields)
    conn.execute(
        f"INSERT INTO transactions ({','.join(fields)}) VALUES ({placeholders})",
        values
    )


def record_bill(bill_number, customer_email, items, discount=0.0, user_id=None,
                payment_method="", payment_status="", customer_name="Walk-in Customer",
                customer_address="", pharmacy_name="PharmaCare",
                pharmacist_name="", pharmacist_email=""):
    """Save a sales invoice and its FEFO-linked transaction lines atomically."""
    conn = get_connection()
    try:
        # Sales use the application's fixed local GST rate.
        gst_rate = SALES_GST_RATE
        gst_mode = "local"
        if not bill_number:
            bill_number = _generate_invoice_id(conn, "SALE")
        subtotal = sum(round(item["qty"] * item["price"], 2) for item in items)
        discount = min(max(float(discount), 0.0), subtotal)
        taxable_subtotal = round(subtotal - discount, 2)
        tax = calculate_gst(taxable_subtotal, gst_rate, gst_mode)
        remaining_discount = round(discount, 2)
        remaining_gst = tax["gst_amount"]
        today = datetime.now().strftime("%Y-%m-%d")

        conn.execute(
            """INSERT INTO sales_invoices
               (invoice_number, invoice_date, pharmacy_name, pharmacist_name,
                pharmacist_email, customer_name, customer_email, customer_address,
                subtotal, discount_amount, gst_rate, gst_mode, cgst_amount,
                sgst_amount, igst_amount, grand_total, payment_method,
                payment_status, pharmacist_user_id)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (bill_number, today, pharmacy_name, pharmacist_name, pharmacist_email,
             customer_name or "Walk-in Customer", customer_email, customer_address,
             subtotal, discount, gst_rate, gst_mode, tax["cgst_amount"],
             tax["sgst_amount"], tax["igst_amount"], tax["grand_total"],
             payment_method, payment_status, user_id)
        )

        for item_index, item in enumerate(items):
            quantity = int(item["qty"])
            medicine_id = item["medicine_id"]
            batches = conn.execute(
                """SELECT id, quantity, cost_price FROM batches
                   WHERE medicine_id=? AND quantity>0 AND expiry_date>=?
                   ORDER BY expiry_date ASC, id ASC""",
                (medicine_id, today)
            ).fetchall()

            remaining_quantity = quantity
            allocation = []
            for batch in batches:
                if remaining_quantity <= 0:
                    break
                take = min(batch["quantity"], remaining_quantity)
                allocation.append((batch["id"], take, float(batch["cost_price"])))
                remaining_quantity -= take
            if remaining_quantity:
                raise ValueError(
                    f"Not enough non-expired stock for '{item['name']}'."
                )

            gross_line = round(quantity * item["price"], 2)
            if item_index == len(items) - 1:
                line_discount = remaining_discount
            elif subtotal:
                line_discount = round(discount * gross_line / subtotal, 2)
                line_discount = min(line_discount, remaining_discount)
            else:
                line_discount = 0.0
            remaining_discount = round(remaining_discount - line_discount, 2)
            net_line = round(gross_line - line_discount, 2)
            remaining_net = net_line
            remaining_line_qty = quantity
            if item_index == len(items) - 1:
                line_gst = remaining_gst
            elif taxable_subtotal:
                line_gst = round(tax["gst_amount"] * net_line / taxable_subtotal, 2)
                line_gst = min(line_gst, remaining_gst)
            else:
                line_gst = 0.0
            remaining_gst = round(remaining_gst - line_gst, 2)
            remaining_line_gst = line_gst

            for batch_id, take, cost_price in allocation:
                cursor = conn.execute(
                    """UPDATE batches SET quantity=quantity-?
                       WHERE id=? AND quantity>=?""",
                    (take, batch_id, take)
                )
                if cursor.rowcount != 1:
                    raise ValueError("Stock changed while generating the bill. Please try again.")

                if take == remaining_line_qty:
                    batch_total = remaining_net
                else:
                    batch_total = round(net_line * take / quantity, 2)
                    batch_total = min(batch_total, remaining_net)
                if take == remaining_line_qty:
                    batch_gst = remaining_line_gst
                elif net_line:
                    batch_gst = round(line_gst * batch_total / net_line, 2)
                    batch_gst = min(batch_gst, remaining_line_gst)
                else:
                    batch_gst = 0.0
                _insert_transaction(
                    conn, bill_number, medicine_id, item["name"], take,
                    item["price"], batch_total, customer_name, cost_price,
                    batch_id, user_id,
                    discount_amount=round(item["price"] * take - batch_total, 2),
                    gst_rate=gst_rate, gst_amount=batch_gst
                )
                remaining_net = round(remaining_net - batch_total, 2)
                remaining_line_gst = round(remaining_line_gst - batch_gst, 2)
                remaining_line_qty -= take

            _sync_medicine_quantity(conn, medicine_id)

        conn.commit()
        return True, "Bill recorded successfully."
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()


def add_transaction(bill_number, medicine_id, medicine_name,
                    quantity, unit_price, total_price,
                    customer_name="Walk-in Customer",
                    cost_price=0.0, batch_id=None, user_id=None,
                    discount_amount=0.0, gst_rate=0.0, gst_amount=0.0):
    try:
        conn = get_connection()
        _insert_transaction(
            conn, bill_number, medicine_id, medicine_name, quantity,
            unit_price, total_price, customer_name, cost_price, batch_id,
            user_id, discount_amount, gst_rate, gst_amount
        )
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


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


def get_sales_invoice(invoice_number):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM sales_invoices WHERE invoice_number=?",
            (invoice_number,)
        ).fetchone()
        if not row:
            return None
        invoice = dict(row)
        invoice["items"] = [dict(item) for item in conn.execute(
            """SELECT t.*, m.id AS medicine_id, m.name AS invoice_medicine_name,
                      b.batch_number, b.manufacture_date, b.expiry_date
               FROM transactions t
               LEFT JOIN medicines m ON m.id=t.medicine_id
               LEFT JOIN batches b ON b.id=t.batch_id
               WHERE t.bill_number=? ORDER BY t.id""",
            (invoice_number,)
        ).fetchall()]
        return invoice
    finally:
        conn.close()


def get_sales_invoices(limit=500):
    conn = get_connection()
    try:
        return conn.execute(
            """SELECT invoice_number, invoice_date, customer_name, customer_email,
                      grand_total
               FROM sales_invoices
               ORDER BY invoice_date DESC, created_at DESC LIMIT ?""",
            (limit,)
        ).fetchall()
    finally:
        conn.close()


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
        """SELECT COALESCE(SUM(subtotal),0) FROM purchases
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
    # Expenditure = medicine purchases actually received + operating expenses.
    # Profit = Revenue - Expenditure (cash basis, no double counting).
    expenditure = purchases + expenses
    profit = revenue - expenditure
    return {
        "expenditure": round(expenditure, 2),
        "profit": round(profit, 2),
        "revenue": round(revenue, 2),
        "cogs": round(cogs, 2),
        "gross_profit": round(gross, 2),
        "expenses": round(expenses, 2),
        "net_profit": round(net, 2),
        "purchases_total": round(purchases, 2),
    }
