# database.py
# All database functions using MySQL stored procedures
# pip install mysql-connector-python

import hashlib
from collections import deque
from datetime import date, datetime
from decimal import Decimal

import mysql.connector
from mysql.connector import Error, IntegrityError

# MySQL connection details - change password if needed
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "k6oQ@8]&6>*_",
    "database": "pharmacy",
}

# for alerts and bills (queue and stack)
alert_queue = deque()
bill_stack = []


def get_connection():
    # connect to mysql
    return mysql.connector.connect(**DB_CONFIG)


def hash_password(password):
    # hash password using sha256
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def convert_value(v):
    # convert mysql types to normal python types
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(v, date):
        return v.strftime("%Y-%m-%d")
    if isinstance(v, Decimal):
        return float(v)
    return v


def fetch_one(cursor):
    # get one row as dictionary
    row = cursor.fetchone()
    if row is None:
        return None
    cols = [d[0] for d in cursor.description]
    result = {}
    for i in range(len(cols)):
        result[cols[i]] = convert_value(row[i])
    return result


def fetch_all(cursor):
    # get all rows as list of dictionaries
    rows = cursor.fetchall()
    cols = [d[0] for d in cursor.description]
    result = []
    for row in rows:
        item = {}
        for i in range(len(cols)):
            item[cols[i]] = convert_value(row[i])
        result.append(item)
    return result


def initialize_database():
    # check if mysql is running
    try:
        conn = get_connection()
        conn.close()
    except Error as e:
        raise RuntimeError(
            "Cannot connect to MySQL. Start MySQL and run pharmacy_schema.sql. Error: " + str(e)
        )


# selection sort - used in reports
def selection_sort(rows, key_func, reverse=False):
    data = list(rows)
    n = len(data)
    for i in range(n):
        extreme = i
        for j in range(i + 1, n):
            a = key_func(data[j])
            b = key_func(data[extreme])
            if reverse:
                if a > b:
                    extreme = j
            else:
                if a < b:
                    extreme = j
        # swap
        temp = data[i]
        data[i] = data[extreme]
        data[extreme] = temp
    return data


# alert queue functions
def enqueue_alert(alert_type, email, medicines):
    alert_queue.append({
        "type": alert_type,
        "email": email,
        "medicines": medicines,
        "at": datetime.now().isoformat(),
    })


def dequeue_alert():
    if len(alert_queue) > 0:
        return alert_queue.popleft()
    return None


def pending_alert_count():
    return len(alert_queue)


# bill stack functions
def push_bill(snapshot):
    bill_stack.append(snapshot)


def pop_bill():
    if len(bill_stack) > 0:
        return bill_stack.pop()
    return None


def peek_bill_stack():
    if len(bill_stack) > 0:
        return bill_stack[-1]
    return None


# ---------- USER FUNCTIONS ----------

def create_user(username, email, password):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.callproc("sp_create_user", (
            username.strip(),
            email.strip().lower(),
            hash_password(password)
        ))
        conn.commit()
        cur.close()
        conn.close()
        return True, "Account created successfully."
    except IntegrityError as e:
        msg = str(e).lower()
        if "username" in msg:
            return False, "Username already taken."
        if "email" in msg:
            return False, "Email already registered."
        return False, str(e)
    except Error as e:
        return False, str(e)


def get_user_by_username(username):
    conn = get_connection()
    cur = conn.cursor()
    cur.callproc("sp_get_user_by_username", (username.strip(),))
    row = None
    for result in cur.stored_results():
        row = fetch_one(result)
    cur.close()
    conn.close()
    return row


def get_user_by_email(email):
    conn = get_connection()
    cur = conn.cursor()
    cur.callproc("sp_get_user_by_email", (email.strip().lower(),))
    row = None
    for result in cur.stored_results():
        row = fetch_one(result)
    cur.close()
    conn.close()
    return row


def validate_login(username, password):
    # returns (ok, message, username, user_id)
    user = get_user_by_username(username)
    if not user:
        return False, "Username not found.", None, None
    if user["password"] != hash_password(password):
        return False, "Incorrect password.", None, None
    return True, "Login successful.", user["username"], int(user["id"])


def update_password(email, new_password):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.callproc("sp_update_password", (
            email.strip().lower(),
            hash_password(new_password)
        ))
        conn.commit()
        cur.close()
        conn.close()
        return True, "Password reset successfully."
    except Error as e:
        return False, str(e)


# ---------- ADMIN USER MANAGEMENT ----------

def get_all_users():
    conn = get_connection()
    cur = conn.cursor()
    cur.callproc("sp_get_all_users")
    rows = []
    for result in cur.stored_results():
        rows = fetch_all(result)
    cur.close()
    conn.close()
    return rows


def get_user_by_id(user_id):
    # find user from list by id
    rows = get_all_users()
    for u in rows:
        if int(u["id"]) == int(user_id):
            return u
    return None


def update_user(user_id, username, email, role):
    try:
        role = (role or "user").strip().lower()
        if role != "user" and role != "admin":
            return False, "Role must be user or admin."
        conn = get_connection()
        cur = conn.cursor()
        cur.callproc("sp_update_user", (
            int(user_id),
            username.strip(),
            email.strip().lower(),
            role
        ))
        conn.commit()
        cur.close()
        conn.close()
        return True, "User updated successfully."
    except IntegrityError as e:
        msg = str(e).lower()
        if "username" in msg:
            return False, "Username already taken."
        if "email" in msg:
            return False, "Email already registered."
        return False, str(e)
    except Error as e:
        return False, str(e)


def delete_user(user_id):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.callproc("sp_delete_user", (int(user_id),))
        conn.commit()
        cur.close()
        conn.close()
        return True, "User deleted successfully."
    except Error as e:
        return False, str(e)


# ---------- MEDICINE CATALOG (for dropdown) ----------

def get_medicine_catalog():
    # list of standard medicines for dropdown
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.callproc("sp_get_catalog")
        rows = []
        for result in cur.stored_results():
            rows = fetch_all(result)
        cur.close()
        conn.close()
        return rows
    except Error:
        return []


def search_medicine_catalog(query):
    # search in catalog while typing
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.callproc("sp_search_catalog", (query.strip(),))
        rows = []
        for result in cur.stored_results():
            rows = fetch_all(result)
        cur.close()
        conn.close()
        return rows
    except Error:
        return []


# ---------- MEDICINE FUNCTIONS ----------

def add_medicine(user_id, name, quantity, price, expiry_date, min_stock):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.callproc("sp_add_medicine", (
            int(user_id),
            name.strip(),
            int(quantity),
            float(price),
            expiry_date,
            int(min_stock)
        ))
        conn.commit()
        cur.close()
        conn.close()
        return True, "Medicine added successfully."
    except Error as e:
        return False, str(e)


def get_all_medicines(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.callproc("sp_get_all_medicines", (int(user_id),))
    rows = []
    for result in cur.stored_results():
        rows = fetch_all(result)
    cur.close()
    conn.close()
    return rows


def get_medicine_by_id(mid, user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.callproc("sp_get_medicine_by_id", (mid, int(user_id)))
    row = None
    for result in cur.stored_results():
        row = fetch_one(result)
    cur.close()
    conn.close()
    return row


def search_medicines(user_id, query):
    conn = get_connection()
    cur = conn.cursor()
    cur.callproc("sp_search_medicines", (int(user_id), query))
    rows = []
    for result in cur.stored_results():
        rows = fetch_all(result)
    cur.close()
    conn.close()
    return rows


def update_medicine(user_id, mid, name, quantity, price, expiry_date, min_stock):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.callproc("sp_update_medicine", (
            int(user_id),
            mid,
            name.strip(),
            int(quantity),
            float(price),
            expiry_date,
            int(min_stock)
        ))
        conn.commit()
        cur.close()
        conn.close()
        return True, "Medicine updated successfully."
    except Error as e:
        return False, str(e)


def delete_medicine(user_id, mid):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.callproc("sp_delete_medicine", (int(user_id), mid))
        conn.commit()
        cur.close()
        conn.close()
        return True, "Medicine deleted successfully."
    except Error as e:
        return False, str(e)


def reduce_medicine_quantity(user_id, mid, amount):
    # reduce stock after billing
    try:
        med = get_medicine_by_id(mid, user_id)
        if not med:
            return False, "Medicine not found."
        if med["quantity"] < amount:
            return False, "Insufficient stock."
        conn = get_connection()
        cur = conn.cursor()
        cur.callproc("sp_reduce_quantity", (int(user_id), mid, amount))
        conn.commit()
        cur.close()
        conn.close()
        remaining = med["quantity"] - amount
        return True, "Remaining: " + str(remaining)
    except Error as e:
        return False, str(e)


def get_low_stock_medicines(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.callproc("sp_get_low_stock", (int(user_id),))
    rows = []
    for result in cur.stored_results():
        rows = fetch_all(result)
    cur.close()
    conn.close()
    return rows


def get_expired_medicines(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.callproc("sp_get_expired", (int(user_id),))
    rows = []
    for result in cur.stored_results():
        rows = fetch_all(result)
    cur.close()
    conn.close()
    return rows


# ---------- TRANSACTION FUNCTIONS ----------

def add_transaction(user_id, bill_number, medicine_id, medicine_name,
                    quantity, unit_price, total_price,
                    customer_name="Walk-in Customer"):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.callproc("sp_add_transaction", (
            int(user_id),
            bill_number,
            medicine_id,
            medicine_name,
            quantity,
            unit_price,
            total_price,
            customer_name
        ))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Error:
        return False


def get_all_transactions(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.callproc("sp_get_all_transactions", (int(user_id),))
    rows = []
    for result in cur.stored_results():
        rows = fetch_all(result)
    cur.close()
    conn.close()
    return rows


def get_transactions_by_date(user_id, start, end):
    conn = get_connection()
    cur = conn.cursor()
    cur.callproc("sp_get_transactions_by_date", (int(user_id), start, end))
    rows = []
    for result in cur.stored_results():
        rows = fetch_all(result)
    cur.close()
    conn.close()
    return rows


def get_dashboard_stats(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.callproc("sp_dashboard_stats", (int(user_id),))
    stats = {
        "total_medicines": 0,
        "total_sales": 0.0,
        "low_stock_count": 0,
        "expired_count": 0,
        "total_transactions": 0,
    }
    for result in cur.stored_results():
        row = fetch_one(result)
        if row:
            stats["total_medicines"] = int(row["total_medicines"])
            stats["total_sales"] = round(float(row["total_sales"]), 2)
            stats["low_stock_count"] = int(row["low_stock_count"])
            stats["expired_count"] = int(row["expired_count"])
            stats["total_transactions"] = int(row["total_transactions"])
    cur.close()
    conn.close()
    return stats
