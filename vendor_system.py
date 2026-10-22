"""Additive SQLite vendor portal and purchase-order workflow for PharmaCare.

This module intentionally uses the existing pharmacy.db. It adds tables/columns only;
it does not recreate or delete legacy pharmacy inventory, sales, batches, vendors, or users.
"""
import sqlite3
from datetime import datetime
from html import escape
import database as db


def _conn():
    return db.get_connection()


def initialize_vendor_system():
    """Safe, repeatable migration for existing pharmacy.db files."""
    conn = _conn()
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(users)")
    cols = {row["name"] for row in cur.fetchall()}
    if "role" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'pharmacist'")
    cur.execute("""CREATE TABLE IF NOT EXISTS vendor_accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL UNIQUE,
        business_name TEXT NOT NULL,
        contact_person TEXT NOT NULL DEFAULT '',
        phone TEXT NOT NULL DEFAULT '',
        address TEXT NOT NULL DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS vendor_catalog (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vendor_id INTEGER NOT NULL,
        medicine_name TEXT NOT NULL,
        unit TEXT NOT NULL DEFAULT 'pack',
        wholesale_price REAL NOT NULL CHECK(wholesale_price >= 0),
        available_quantity INTEGER NOT NULL DEFAULT 0 CHECK(available_quantity >= 0),
        expiry_date TEXT NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(vendor_id) REFERENCES vendor_accounts(id),
        UNIQUE(vendor_id, medicine_name, expiry_date)
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS vendor_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pharmacist_user_id INTEGER NOT NULL,
        vendor_id INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'Pending'
          CHECK(status IN ('Pending','Confirmed','Dispatched','Partially Received','Received','Rejected','Cancelled')),
        total_amount REAL NOT NULL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        email_status TEXT NOT NULL DEFAULT 'Not sent',
        FOREIGN KEY(pharmacist_user_id) REFERENCES users(id),
        FOREIGN KEY(vendor_id) REFERENCES vendor_accounts(id)
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS vendor_order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        catalog_id INTEGER NOT NULL,
        medicine_name TEXT NOT NULL,
        quantity INTEGER NOT NULL CHECK(quantity > 0),
        received_quantity INTEGER NOT NULL DEFAULT 0,
        unit_price REAL NOT NULL CHECK(unit_price >= 0),
        expiry_date TEXT NOT NULL,
        FOREIGN KEY(order_id) REFERENCES vendor_orders(id),
        FOREIGN KEY(catalog_id) REFERENCES vendor_catalog(id)
    )""")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_vendor_orders_vendor ON vendor_orders(vendor_id, status)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_vendor_items_order ON vendor_order_items(order_id)")
    conn.commit()
    conn.close()


def get_user_role(username):
    conn = _conn()
    row = conn.execute("SELECT role FROM users WHERE username=?", (username.strip(),)).fetchone()
    conn.close()
    return row["role"] if row and "role" in row.keys() else "pharmacist"


def register_vendor_account(user_id, business_name, contact_person="", phone="", address=""):
    conn = _conn()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE users SET role='vendor' WHERE id=?", (user_id,))
        cur.execute("""INSERT INTO vendor_accounts
            (user_id,business_name,contact_person,phone,address) VALUES (?,?,?,?,?)""",
            (user_id, business_name.strip(), contact_person.strip(), phone.strip(), address.strip()))
        conn.commit()
        return True, "Vendor account created."
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        return False, "Vendor account already exists or details are invalid."
    finally:
        conn.close()


def get_vendor_for_user(user_id):
    conn = _conn()
    row = conn.execute("SELECT * FROM vendor_accounts WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return row


def get_user_id(username):
    row = db.get_user_by_username(username)
    return row["id"] if row else None


def add_catalog_item(vendor_id, name, unit, price, quantity, expiry_date):
    name = name.strip()
    try:
        datetime.strptime(expiry_date, "%Y-%m-%d")
        price, quantity = float(price), int(quantity)
        if not name or price < 0 or quantity < 0:
            return False, "Enter a medicine name and valid non-negative price/quantity."
    except (ValueError, TypeError):
        return False, "Use a valid price, whole-number quantity, and expiry date (YYYY-MM-DD)."
    if datetime.strptime(expiry_date, "%Y-%m-%d").date() < datetime.now().date():
        return False, "Expiry date must be today or later."
    conn = _conn()
    try:
        conn.execute("""INSERT INTO vendor_catalog
            (vendor_id,medicine_name,unit,wholesale_price,available_quantity,expiry_date)
            VALUES (?,?,?,?,?,?)""",
            (vendor_id, name, unit.strip() or "pack", price, quantity, expiry_date))
        conn.commit()
        return True, "Medicine added to vendor catalogue."
    except sqlite3.IntegrityError:
        return False, "This medicine and expiry date already exist in your catalogue."
    finally:
        conn.close()


def get_catalog(vendor_id=None):
    conn = _conn()
    if vendor_id is None:
        rows = conn.execute("""SELECT c.*, v.business_name FROM vendor_catalog c
            JOIN vendor_accounts v ON v.id=c.vendor_id
            WHERE c.available_quantity > 0 AND c.expiry_date >= date('now')
            ORDER BY c.medicine_name""").fetchall()
    else:
        rows = conn.execute("SELECT * FROM vendor_catalog WHERE vendor_id=? ORDER BY medicine_name", (vendor_id,)).fetchall()
    conn.close()
    return rows


def create_order(pharmacist_user_id, vendor_id, catalog_id, quantity):
    try:
        quantity = int(quantity)
        if quantity < 1:
            return False, "Quantity must be at least 1."
    except (TypeError, ValueError):
        return False, "Enter a whole-number quantity."
    conn = _conn()
    try:
        item = conn.execute("""SELECT * FROM vendor_catalog
            WHERE id=? AND vendor_id=? AND expiry_date >= date('now')""",
            (catalog_id, vendor_id)).fetchone()
        if not item:
            return False, "Catalogue item not found or expired."
        if item["available_quantity"] < quantity:
            return False, f"Only {item['available_quantity']} units are available."
        total = round(float(item["wholesale_price"]) * quantity, 2)
        cur = conn.execute("""INSERT INTO vendor_orders
            (pharmacist_user_id,vendor_id,total_amount,status) VALUES (?,?,?,'Pending')""",
            (pharmacist_user_id, vendor_id, total))
        order_id = cur.lastrowid
        conn.execute("""INSERT INTO vendor_order_items
            (order_id,catalog_id,medicine_name,quantity,unit_price,expiry_date)
            VALUES (?,?,?,?,?,?)""",
            (order_id, catalog_id, item["medicine_name"], quantity,
             item["wholesale_price"], item["expiry_date"]))
        conn.commit()
        return True, order_id
    except Exception as exc:
        conn.rollback()
        return False, str(exc)
    finally:
        conn.close()


def list_orders(user_id=None, role="pharmacist", vendor_id=None):
    conn = _conn()
    if role == "vendor":
        rows = conn.execute("""SELECT o.*, u.username AS pharmacist_name,
            v.business_name FROM vendor_orders o JOIN users u ON u.id=o.pharmacist_user_id
            JOIN vendor_accounts v ON v.id=o.vendor_id
            WHERE o.vendor_id=? ORDER BY o.id DESC""", (vendor_id,)).fetchall()
    else:
        rows = conn.execute("""SELECT o.*, v.business_name FROM vendor_orders o
            JOIN vendor_accounts v ON v.id=o.vendor_id
            WHERE o.pharmacist_user_id=? ORDER BY o.id DESC""", (user_id,)).fetchall()
    conn.close()
    return rows


def get_order_items(order_id):
    conn = _conn()
    rows = conn.execute("SELECT * FROM vendor_order_items WHERE order_id=? ORDER BY id", (order_id,)).fetchall()
    conn.close()
    return rows


def transition_order(order_id, action, actor_role, actor_id):
    """Perform valid order transitions; confirmation reserves vendor stock."""
    conn = _conn()
    try:
        order = conn.execute("SELECT * FROM vendor_orders WHERE id=?", (order_id,)).fetchone()
        if not order:
            return False, "Order not found."
        if actor_role == "vendor":
            vendor = conn.execute("SELECT id FROM vendor_accounts WHERE user_id=?", (actor_id,)).fetchone()
            if not vendor or vendor["id"] != order["vendor_id"]:
                return False, "You cannot update another vendor's order."
        elif order["pharmacist_user_id"] != actor_id:
            return False, "You cannot update another pharmacist's order."

        status = order["status"]
        if action == "confirm" and actor_role == "vendor" and status == "Pending":
            items = conn.execute("SELECT * FROM vendor_order_items WHERE order_id=?", (order_id,)).fetchall()
            for item in items:
                stock = conn.execute("SELECT available_quantity FROM vendor_catalog WHERE id=?", (item["catalog_id"],)).fetchone()
                if not stock or stock["available_quantity"] < item["quantity"]:
                    return False, "Vendor stock changed; the order cannot be confirmed."
            for item in items:
                conn.execute("UPDATE vendor_catalog SET available_quantity=available_quantity-?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                             (item["quantity"], item["catalog_id"]))
            new_status = "Confirmed"
        elif action == "dispatch" and actor_role == "vendor" and status == "Confirmed":
            new_status = "Dispatched"
        elif action == "receive" and actor_role == "pharmacist" and status in ("Dispatched", "Partially Received"):
            items = conn.execute("SELECT * FROM vendor_order_items WHERE order_id=?", (order_id,)).fetchall()
            # Create one legacy purchase record per order, linked to received batches.
            vendor_profile = conn.execute("SELECT business_name FROM vendor_accounts WHERE id=?",
                                          (order["vendor_id"],)).fetchone()
            vendor_name = vendor_profile["business_name"]
            legacy_vendor = conn.execute("SELECT id FROM vendors WHERE lower(name)=lower(?)",
                                         (vendor_name,)).fetchone()
            if legacy_vendor:
                legacy_vendor_id = legacy_vendor["id"]
            else:
                legacy_vendor_id = conn.execute("INSERT INTO vendors(name) VALUES (?)",
                                                (vendor_name,)).lastrowid
            purchase = conn.execute("SELECT id FROM purchases WHERE invoice_number=?",
                                    (f"PO-{order_id}",)).fetchone()
            if purchase:
                purchase_id = purchase["id"]
            else:
                purchase_id = conn.execute(
                    """INSERT INTO purchases(vendor_id,invoice_number,purchase_date,total_amount,notes)
                       VALUES (?,?,?,?,?)""",
                    (legacy_vendor_id, f"PO-{order_id}", datetime.now().strftime("%Y-%m-%d"),
                     float(order["total_amount"]), f"Received from vendor portal order #{order_id}")).lastrowid
            for item in items:
                outstanding = item["quantity"] - item["received_quantity"]
                if outstanding <= 0:
                    continue
                med = conn.execute("SELECT id FROM medicines WHERE lower(name)=lower(?) ORDER BY id LIMIT 1",
                                   (item["medicine_name"],)).fetchone()
                if med:
                    medicine_id = med["id"]
                else:
                    cur = conn.execute("""INSERT INTO medicines(name,quantity,price,expiry_date,min_stock)
                        VALUES (?,0,?, ?,10)""", (item["medicine_name"], item["unit_price"], item["expiry_date"]))
                    medicine_id = cur.lastrowid
                batch_no = f"ORD-{order_id}-ITEM-{item['id']}"
                existing_batch = conn.execute("SELECT id FROM batches WHERE batch_number=? AND medicine_id=?",
                                              (batch_no, medicine_id)).fetchone()
                if not existing_batch:
                    conn.execute("""INSERT INTO batches
                        (medicine_id,purchase_id,batch_number,quantity,cost_price,expiry_date)
                        VALUES (?,?,?,?,?,?)""",
                        (medicine_id, purchase_id, batch_no, outstanding, item["unit_price"], item["expiry_date"]))
                db._sync_medicine_quantity(conn, medicine_id)
                conn.execute("UPDATE vendor_order_items SET received_quantity=quantity WHERE id=?", (item["id"],))
            new_status = "Received"
        elif action == "reject" and actor_role == "vendor" and status == "Pending":
            new_status = "Rejected"
        elif action == "cancel" and actor_role == "pharmacist" and status == "Pending":
            new_status = "Cancelled"
        else:
            return False, f"Action '{action}' is not valid when order status is {status}."
        conn.execute("UPDATE vendor_orders SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?", (new_status, order_id))
        conn.commit()
        return True, f"Order #{order_id} marked {new_status}."
    except Exception as exc:
        conn.rollback()
        return False, str(exc)
    finally:
        conn.close()


def mark_order_email_status(order_id, status):
    conn = _conn()
    conn.execute("UPDATE vendor_orders SET email_status=? WHERE id=?", (status, order_id))
    conn.commit()
    conn.close()


def send_order_receipt(order_id, pharmacist_email):
    """Email confirmation is best-effort and never rolls back a saved order."""
    import smtp_handler as smtp
    items = get_order_items(order_id)
    rows = "".join(
        f"<tr><td>{escape(item['medicine_name'])}</td><td>{item['quantity']}</td>"
        f"<td>₹{item['unit_price']:.2f}</td><td>₹{item['quantity'] * item['unit_price']:.2f}</td></tr>"
        for item in items
    )
    total = sum(item["quantity"] * item["unit_price"] for item in items)
    body = f"""<h2>Order #{order_id} placed successfully</h2>
    <p>This email confirms order placement; it is not a delivery confirmation.</p>
    <table style="width:100%;border-collapse:collapse" border="1" cellpadding="8">
    <tr><th>Medicine</th><th>Quantity</th><th>Unit price</th><th>Subtotal</th></tr>{rows}</table>
    <p><strong>Total: ₹{total:.2f}</strong></p>"""
    def callback(ok, message):
        mark_order_email_status(order_id, "Sent" if ok else "Failed")
    smtp.send_email_async(pharmacist_email, f"PharmaCare order receipt #{order_id}", smtp._wrap(body), callback)


def financial_summary():
    conn = _conn()
    sales = conn.execute("SELECT COALESCE(SUM(total_price),0) FROM transactions").fetchone()[0]
    cogs = conn.execute("SELECT COALESCE(SUM(cost_price*quantity),0) FROM transactions").fetchone()[0]
    expenses = conn.execute("SELECT COALESCE(SUM(amount),0) FROM expenses").fetchone()[0]
    purchases = conn.execute("""SELECT COALESCE(SUM(total_amount),0) FROM purchases""").fetchone()[0]
    conn.close()
    return {"revenue": float(sales or 0), "cogs": float(cogs or 0),
            "gross_profit": float(sales or 0)-float(cogs or 0),
            "expenses": float(expenses or 0),
            "net_profit": float(sales or 0)-float(cogs or 0)-float(expenses or 0),
            "vendor_purchase_expenditure": float(purchases or 0)}
