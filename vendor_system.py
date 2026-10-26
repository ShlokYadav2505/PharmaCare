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
        manufacture_date TEXT,
        expiry_date TEXT NOT NULL,
        gst_rate REAL NOT NULL DEFAULT 0,
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
        manufacture_date TEXT,
        gst_rate REAL NOT NULL DEFAULT 0,
        expiry_date TEXT NOT NULL,
        FOREIGN KEY(order_id) REFERENCES vendor_orders(id),
        FOREIGN KEY(catalog_id) REFERENCES vendor_catalog(id)
    )""")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_vendor_orders_vendor ON vendor_orders(vendor_id, status)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_vendor_items_order ON vendor_order_items(order_id)")
    cur.execute("PRAGMA table_info(vendor_order_items)")
    item_cols = {row["name"] for row in cur.fetchall()}
    if "dispatch_batch_number" not in item_cols:
        cur.execute(
            "ALTER TABLE vendor_order_items ADD COLUMN dispatch_batch_number TEXT NOT NULL DEFAULT ''"
        )
    for table, required in {
        "vendor_catalog": {
            "manufacture_date": "TEXT",
            "gst_rate": "REAL NOT NULL DEFAULT 0",
        },
        "vendor_order_items": {
            "manufacture_date": "TEXT",
            "gst_rate": "REAL NOT NULL DEFAULT 0",
        },
    }.items():
        cols = {row["name"] for row in cur.execute(f"PRAGMA table_info({table})").fetchall()}
        for name, definition in required.items():
            if name not in cols:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")
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


def expiry_one_year_after(manufacture_date):
    """Return the one-year shelf-life date, handling leap-day manufacture dates."""
    mfg_date = datetime.strptime(manufacture_date, "%Y-%m-%d").date()
    try:
        expiry = mfg_date.replace(year=mfg_date.year + 1)
    except ValueError:
        expiry = mfg_date.replace(year=mfg_date.year + 1, day=28)
    return expiry.isoformat()


def add_catalog_item(vendor_id, name, unit, price, quantity,
                     manufacture_date):
    name = name.strip()
    try:
        mfg_raw = (manufacture_date or "").strip()
        mfg_date = datetime.strptime(mfg_raw, "%Y-%m-%d").date()
        expiry_date = expiry_one_year_after(mfg_raw)
        exp_date = datetime.strptime(expiry_date, "%Y-%m-%d").date()
        price, quantity = float(price), int(quantity)
        if not name or price < 0 or quantity < 0:
            return False, "Enter a medicine name and valid price and quantity."
    except (ValueError, TypeError):
        return False, "Use valid price, quantity, and manufacture date values."
    if mfg_date > datetime.now().date():
        return False, "Manufacture date cannot be in the future."
    if exp_date < datetime.now().date():
        return False, "The calculated expiry date has passed."
    conn = _conn()
    try:
        conn.execute("""INSERT INTO vendor_catalog
            (vendor_id,medicine_name,unit,wholesale_price,available_quantity,
             manufacture_date,expiry_date,gst_rate)
            VALUES (?,?,?,?,?,?,?,0)""",
            (vendor_id, name, unit.strip() or "pack", price, quantity,
             mfg_raw or None, expiry_date))
        conn.commit()
        return True, "Medicine added to vendor catalogue."
    except sqlite3.IntegrityError:
        return False, "This medicine and manufacturing date already exist in your catalogue."
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
            (order_id,catalog_id,medicine_name,quantity,unit_price,
             manufacture_date,gst_rate,expiry_date)
            VALUES (?,?,?,?,?,?,?,?)""",
            (order_id, catalog_id, item["medicine_name"], quantity,
             item["wholesale_price"], item["manufacture_date"],
             0, item["expiry_date"]))
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


def _restore_catalog_stock(conn, order_id):
    items = conn.execute("SELECT * FROM vendor_order_items WHERE order_id=?", (order_id,)).fetchall()
    for item in items:
        conn.execute(
            """UPDATE vendor_catalog SET available_quantity=available_quantity+?,
               updated_at=CURRENT_TIMESTAMP WHERE id=?""",
            (item["quantity"], item["catalog_id"]),
        )


def _add_pharmacy_inventory_for_order(conn, order_id, order, items):
    """Increase pharmacy stock once per dispatched order (idempotent batch numbers)."""
    vendor_profile = conn.execute(
        """SELECT va.business_name, va.contact_person, va.phone, va.address,
                  u.email AS email
           FROM vendor_accounts va JOIN users u ON u.id=va.user_id WHERE va.id=?""",
        (order["vendor_id"],)
    ).fetchone()
    vendor_name = vendor_profile["business_name"]
    legacy_vendor = conn.execute(
        "SELECT id FROM vendors WHERE lower(name)=lower(?)", (vendor_name,)
    ).fetchone()
    if legacy_vendor:
        legacy_vendor_id = legacy_vendor["id"]
        conn.execute(
            """UPDATE vendors SET contact_person=?, phone=?, email=?, address=? WHERE id=?""",
            (vendor_profile["contact_person"], vendor_profile["phone"],
             vendor_profile["email"], vendor_profile["address"], legacy_vendor_id)
        )
    else:
        legacy_vendor_id = conn.execute(
            """INSERT INTO vendors(name,contact_person,phone,email,address)
               VALUES (?,?,?,?,?)""",
            (vendor_name, vendor_profile["contact_person"], vendor_profile["phone"],
             vendor_profile["email"], vendor_profile["address"])
        ).lastrowid

    invoice_id = f"PUR-PORTAL-{order_id:08d}"
    purchase = conn.execute(
        "SELECT id FROM purchases WHERE invoice_number IN (?,?)",
        (invoice_id, f"PO-{order_id}"),
    ).fetchone()
    order_subtotal = round(sum(int(it["quantity"]) * float(it["unit_price"]) for it in items), 2)
    tax_lines = [db.calculate_gst(
        int(it["quantity"]) * float(it["unit_price"]), float(it["gst_rate"] or 0), "local"
    ) for it in items]
    cgst = round(sum(line["cgst_amount"] for line in tax_lines), 2)
    sgst = round(sum(line["sgst_amount"] for line in tax_lines), 2)
    igst = 0.0
    gst_total = round(cgst + sgst, 2)
    order_total = round(order_subtotal + gst_total, 2)
    pharmacist = conn.execute(
        "SELECT username,email FROM users WHERE id=?", (order["pharmacist_user_id"],)
    ).fetchone()
    gst_rates = {float(it["gst_rate"] or 0) for it in items}
    header_gst_rate = next(iter(gst_rates)) if len(gst_rates) == 1 else 0.0
    if purchase:
        purchase_id = purchase["id"]
        conn.execute(
            """UPDATE purchases SET invoice_number=?, subtotal=?, total_amount=?,
               gst_rate=?, gst_mode='local', cgst_amount=?, sgst_amount=?, igst_amount=?,
               payment_method='Credit', payment_status='Pending',
               pharmacy_name='PharmaCare', pharmacist_name=?, pharmacist_email=?
               WHERE id=?""",
            (invoice_id, order_subtotal, order_total, header_gst_rate, cgst, sgst,
             igst, pharmacist["username"] if pharmacist else "",
             pharmacist["email"] if pharmacist else "", purchase_id)
        )
    else:
        purchase_id = conn.execute(
            """INSERT INTO purchases
               (vendor_id,invoice_number,purchase_date,subtotal,total_amount,gst_rate,
                gst_mode,cgst_amount,sgst_amount,igst_amount,payment_method,
                payment_status,pharmacy_name,pharmacist_name,pharmacist_email,notes)
               VALUES (?,?,?,?,?,?,'local',?,?,?,'Credit','Pending','PharmaCare',?,?,?)""",
            (
                legacy_vendor_id,
                invoice_id,
                datetime.now().strftime("%Y-%m-%d"),
                order_subtotal,
                order_total,
                header_gst_rate,
                cgst,
                sgst,
                igst,
                pharmacist["username"] if pharmacist else "",
                pharmacist["email"] if pharmacist else "",
                f"Vendor portal order #{order_id} (dispatched)",
            ),
        ).lastrowid

    for item_index, item in enumerate(items):
        batch_no = f"VENDOR-ORDER-{order_id}-ITEM-{item['id']}"
        if conn.execute(
            "SELECT id FROM batches WHERE batch_number=?", (batch_no,)
        ).fetchone():
            continue

        med = conn.execute(
            "SELECT id FROM medicines WHERE lower(name)=lower(?) ORDER BY id LIMIT 1",
            (item["medicine_name"],),
        ).fetchone()
        if med:
            medicine_id = med["id"]
            batch_count = conn.execute(
                "SELECT COUNT(*) FROM batches WHERE medicine_id=?", (medicine_id,)
            ).fetchone()[0]
            if batch_count == 0:
                legacy = conn.execute(
                    "SELECT quantity, expiry_date FROM medicines WHERE id=?", (medicine_id,)
                ).fetchone()
                legacy_expiry = (legacy["expiry_date"] or "").strip()
                try:
                    datetime.strptime(legacy_expiry, "%Y-%m-%d")
                except (TypeError, ValueError):
                    legacy_expiry = ""
                if int(legacy["quantity"]) > 0 and legacy_expiry:
                    conn.execute(
                        """INSERT INTO batches
                           (medicine_id,batch_number,quantity,cost_price,expiry_date)
                           VALUES (?,?,?,?,?)""",
                        (
                            medicine_id,
                            f"LEGACY-PO-{order_id}",
                            int(legacy["quantity"]),
                            0.0,
                            legacy_expiry,
                        ),
                    )
        else:
            medicine_id = conn.execute(
                """INSERT INTO medicines(name,quantity,price,expiry_date,min_stock)
                   VALUES (?,0,?,?,10)""",
                (item["medicine_name"], item["unit_price"], item["expiry_date"]),
            ).lastrowid

        qty = int(item["quantity"])
        conn.execute(
            """INSERT INTO batches
               (medicine_id,purchase_id,batch_number,quantity,cost_price,expiry_date,
                manufacture_date,gst_rate,gst_amount)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (medicine_id, purchase_id, batch_no, qty, item["unit_price"], item["expiry_date"],
             item["manufacture_date"], item["gst_rate"], tax_lines[item_index]["gst_amount"]),
        )
        db._sync_medicine_quantity(conn, medicine_id)
        conn.execute(
            "UPDATE vendor_order_items SET received_quantity=? WHERE id=?",
            (qty, item["id"]),
        )


def transition_order(
    order_id,
    action,
    actor_role,
    actor_id,
    receive_quantity=None,
):
    """Apply order workflow transitions. Pharmacy inventory increases on vendor dispatch."""
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
                stock = conn.execute(
                    "SELECT available_quantity FROM vendor_catalog WHERE id=?",
                    (item["catalog_id"],),
                ).fetchone()
                if not stock or stock["available_quantity"] < item["quantity"]:
                    return False, "Not enough catalogue stock to confirm and reserve this order."
            for item in items:
                conn.execute(
                    """UPDATE vendor_catalog SET available_quantity=available_quantity-?,
                       updated_at=CURRENT_TIMESTAMP WHERE id=?""",
                    (item["quantity"], item["catalog_id"]),
                )
            new_status = "Confirmed"
        elif action == "dispatch" and actor_role == "vendor" and status == "Confirmed":
            items = conn.execute(
                "SELECT * FROM vendor_order_items WHERE order_id=?", (order_id,)
            ).fetchall()
            _add_pharmacy_inventory_for_order(conn, order_id, order, items)
            new_status = "Dispatched"
        elif action == "receive" and actor_role == "pharmacist" and status in ("Dispatched", "Partially Received"):
            items = conn.execute("SELECT * FROM vendor_order_items WHERE order_id=?", (order_id,)).fetchall()
            if len(items) != 1:
                return False, "This receipt screen supports one medicine per order."
            item = items[0]
            if int(item["received_quantity"]) >= int(item["quantity"]):
                new_status = "Received"
            else:
                return False, "Stock is added when the vendor dispatches. Wait for dispatch, then refresh."
        elif action == "reject" and actor_role == "vendor" and status in ("Pending", "Confirmed"):
            if status == "Confirmed":
                _restore_catalog_stock(conn, order_id)
            new_status = "Rejected"
        elif action == "cancel" and actor_role == "pharmacist" and status == "Pending":
            new_status = "Cancelled"
        else:
            return False, f"Action '{action}' is not valid when order status is {status}."

        conn.execute("UPDATE vendor_orders SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                     (new_status, order_id))
        conn.commit()
        if action == "dispatch" and new_status == "Dispatched":
            send_pharmacist_dispatch_notification(order_id)
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


def _order_email_table(order_id):
    items = get_order_items(order_id)
    rows = "".join(
        f"<tr><td>{escape(item['medicine_name'])}</td><td>{item['quantity']}</td>"
        f"<td>₹{item['unit_price']:.2f}</td><td>₹{item['quantity'] * item['unit_price']:.2f}</td></tr>"
        for item in items
    )
    total = sum(item["quantity"] * item["unit_price"] for item in items)
    return rows, total


def send_order_receipt(order_id, pharmacist_email):
    """Email confirmation is best-effort and never rolls back a saved order."""
    import smtp_handler as smtp
    rows, total = _order_email_table(order_id)
    body = f"""<h2>Order #{order_id} placed successfully</h2>
    <p>This email confirms order placement; it is not a delivery confirmation.</p>
    <table style="width:100%;border-collapse:collapse" border="1" cellpadding="8">
    <tr><th>Medicine</th><th>Quantity</th><th>Unit price</th><th>Subtotal</th></tr>{rows}</table>
    <p><strong>Total: ₹{total:.2f}</strong></p>"""
    def callback(ok, message):
        mark_order_email_status(order_id, "Sent" if ok else "Failed")
    smtp.send_email_async(pharmacist_email, f"PharmaCare order receipt #{order_id}", smtp._wrap(body), callback)


def send_vendor_new_order_notification(order_id):
    """Notify the vendor by email when a pharmacist places an order."""
    import smtp_handler as smtp
    conn = _conn()
    row = conn.execute(
        """SELECT o.id, u.username AS pharmacist_name, u.email AS pharmacist_email,
                  vu.email AS vendor_email, va.business_name
           FROM vendor_orders o
           JOIN users u ON u.id = o.pharmacist_user_id
           JOIN vendor_accounts va ON va.id = o.vendor_id
           JOIN users vu ON vu.id = va.user_id
           WHERE o.id=?""",
        (order_id,),
    ).fetchone()
    conn.close()
    if not row or not row["vendor_email"]:
        return
    rows, total = _order_email_table(order_id)
    body = f"""<h2>New purchase order #{order_id}</h2>
    <p><strong>Pharmacist:</strong> {escape(row['pharmacist_name'])}</p>
    <p>Please review and confirm this order in the Vendor Portal.</p>
    <table style="width:100%;border-collapse:collapse" border="1" cellpadding="8">
    <tr><th>Medicine</th><th>Quantity</th><th>Unit price</th><th>Subtotal</th></tr>{rows}</table>
    <p><strong>Total: ₹{total:.2f}</strong></p>"""
    smtp.send_email_async(
        row["vendor_email"],
        f"PharmaCare: new order #{order_id} from {row['pharmacist_name']}",
        smtp._wrap(body),
    )


def send_pharmacist_dispatch_notification(order_id):
    """Notify the pharmacist when the vendor dispatches their order."""
    import smtp_handler as smtp
    conn = _conn()
    row = conn.execute(
        """SELECT o.id, u.username AS pharmacist_name, u.email AS pharmacist_email,
                  va.business_name
           FROM vendor_orders o
           JOIN users u ON u.id = o.pharmacist_user_id
           JOIN vendor_accounts va ON va.id = o.vendor_id
           WHERE o.id=?""",
        (order_id,),
    ).fetchone()
    conn.close()
    if not row or not row["pharmacist_email"]:
        return
    rows, total = _order_email_table(order_id)
    body = f"""<h2>Order #{order_id} dispatched</h2>
    <p><strong>Vendor:</strong> {escape(row['business_name'])}</p>
    <p>Your pharmacy inventory has been updated with the items below.</p>
    <table style="width:100%;border-collapse:collapse" border="1" cellpadding="8">
    <tr><th>Medicine</th><th>Quantity</th><th>Unit price</th><th>Subtotal</th></tr>{rows}</table>
    <p><strong>Total: ₹{total:.2f}</strong></p>"""
    smtp.send_email_async(
        row["pharmacist_email"],
        f"PharmaCare: order #{order_id} dispatched by {row['business_name']}",
        smtp._wrap(body),
    )


def notify_order_placed(order_id, pharmacist_email):
    """Pharmacist receipt + vendor alert after a successful order."""
    if pharmacist_email:
        send_order_receipt(order_id, pharmacist_email)
    send_vendor_new_order_notification(order_id)


def financial_summary():
    conn = _conn()
    sales = conn.execute("SELECT COALESCE(SUM(total_price),0) FROM transactions").fetchone()[0]
    cogs = conn.execute("SELECT COALESCE(SUM(cost_price*quantity),0) FROM transactions").fetchone()[0]
    expenses = conn.execute("SELECT COALESCE(SUM(amount),0) FROM expenses").fetchone()[0]
    purchases = conn.execute("""SELECT COALESCE(SUM(subtotal),0) FROM purchases""").fetchone()[0]
    conn.close()
    return {"revenue": float(sales or 0), "cogs": float(cogs or 0),
            "gross_profit": float(sales or 0)-float(cogs or 0),
            "expenses": float(expenses or 0),
            "net_profit": float(sales or 0)-float(cogs or 0)-float(expenses or 0),
            "vendor_purchase_expenditure": float(purchases or 0)}
