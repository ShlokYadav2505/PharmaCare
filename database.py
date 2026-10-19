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
    # signup passes the email as username (no random code)
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.callproc("sp_create_user", (
            username.strip().lower(),
            email.strip().lower(),
            hash_password(password)
        ))
        conn.commit()
        cur.close()
        conn.close()
        return True, "Account created successfully."
    except IntegrityError as e:
        msg = str(e).lower()
        if "username" in msg or "email" in msg:
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


def validate_login(email, password):
    # returns (ok, message, email, user_id)
    user = get_user_by_email(email)
    if not user:
        return False, "Email not found.", None, None
    if user["password"] != hash_password(password):
        return False, "Incorrect password.", None, None
    return True, "Login successful.", user["email"], int(user["id"])


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
