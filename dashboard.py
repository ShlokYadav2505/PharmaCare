# dashboard.py - basic sidebar + pages
# UI unchanged. Login identity is the email.

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import database as db


class DashboardApp(tk.Frame):
    def __init__(self, parent, email, user_id, on_logout_callback):
        super().__init__(parent, bg="#F0F0F0")
        self._user_id = user_id
        self._on_logout = on_logout_callback
        user = db.get_user_by_email(email)
        if not user:
            user = db.get_user_by_username(email)
        self._user_email = user["email"] if user else email
        self._username = self._user_email
        self._role = (user.get("role") or "user").lower() if user else "user"
        self._is_admin = self._role == "admin"
        self._frames = {}
        self._current = ""
        self._build()
        self._switch("home")
        self._check_alerts()

    def _build(self):
        self.rowconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        sb = tk.Frame(self, bg="#1B5E20", width=160)
        sb.grid(row=0, column=0, sticky="ns")
        sb.grid_propagate(False)

        tk.Label(sb, text="PharmaCare", font=("Arial", 14, "bold"),
                 bg="#1B5E20", fg="white").pack(pady=(20, 2))
        role_label = self._role
        tk.Label(sb, text=role_label, font=("Arial", 9),
                 bg="#1B5E20", fg="#A5D6A7").pack(pady=(0, 15))

        nav_items = [("Dashboard", "home"), ("Inventory", "inventory"),
                     ("Billing", "billing"), ("Reports", "reports")]
        if self._is_admin:
            nav_items.append(("Users", "users"))

        for label, key in nav_items:
            tk.Button(sb, text=label, font=("Arial", 11), width=14,
                      command=lambda k=key: self._switch(k)).pack(pady=3)

        tk.Frame(sb, bg="#1B5E20").pack(fill="both", expand=True)
        tk.Button(sb, text="Logout", font=("Arial", 11), width=14,
                  command=self._logout).pack(pady=15)

        self._content = tk.Frame(self, bg="#F0F0F0")
        self._content.grid(row=0, column=1, sticky="nsew")
        self._content.rowconfigure(0, weight=1)
        self._content.columnconfigure(0, weight=1)

    def _switch(self, key):
        if self._current and self._current in self._frames:
            self._frames[self._current].grid_remove()
        if key not in self._frames:
            self._frames[key] = self._make(key)
        f = self._frames[key]
        f.grid(row=0, column=0, sticky="nsew")
        if hasattr(f, "refresh"):
            f.refresh()
        self._current = key

    def _make(self, key):
        if key == "home":
            return HomeFrame(self._content, self._user_email, self._user_id, self._switch)
        if key == "inventory":
            from inventory import InventoryFrame
            return InventoryFrame(self._content, user_id=self._user_id, user_email=self._user_email)
        if key == "billing":
            from billing import BillingFrame
            return BillingFrame(self._content, user_id=self._user_id, user_email=self._user_email)
        if key == "reports":
            from reports import ReportsFrame
            return ReportsFrame(self._content, user_id=self._user_id)
        if key == "users":
            from users import UsersFrame
            return UsersFrame(self._content, current_user_id=self._user_id)

    def _check_alerts(self):
        import smtp_handler as smtp
        ls = db.get_low_stock_medicines(self._user_id)
        ex = db.get_expired_medicines(self._user_id)
        parts = []
        if ls:
            parts.append(f"{len(ls)} medicine(s) low on stock")
            if self._user_email:
                db.enqueue_alert("low_stock", self._user_email, ls)
                smtp.send_low_stock_alert(self._user_email, ls)
        if ex:
            parts.append(f"{len(ex)} medicine(s) expired")
            if self._user_email:
                db.enqueue_alert("expired", self._user_email, ex)
                smtp.send_expired_medicine_alert(self._user_email, ex)
        while db.pending_alert_count() > 0:
            db.dequeue_alert()
        if parts and self._user_email:
            msg = "Automatic alert:\n" + "\n".join(f"• {p}" for p in parts)
            msg += f"\n\nEmail sent to {self._user_email}."
            self.after(600, lambda: messagebox.showwarning(
                "Stock / Expiry Alert", msg, parent=self.winfo_toplevel()))
        self.after(21600000, self._check_alerts)

    def _logout(self):
        if messagebox.askyesno("Logout", "Logout?", parent=self.winfo_toplevel()):
            self._on_logout()


class HomeFrame(tk.Frame):
    def __init__(self, parent, username, user_id, navigate):
        super().__init__(parent, bg="#F0F0F0")
        self._username = username
        self._user_id = user_id
        self._navigate = navigate
        self._build()
        self.refresh()

    def _build(self):
        tk.Label(self, text=f"Welcome, {self._username}",
                 font=("Arial", 16, "bold"), bg="#F0F0F0").pack(anchor="w", padx=20, pady=(20, 5))
        tk.Label(self, text=datetime.now().strftime("%A, %d %B %Y"),
                 font=("Arial", 10), bg="#F0F0F0").pack(anchor="w", padx=20)

        stats = tk.Frame(self, bg="#F0F0F0")
        stats.pack(fill="x", padx=20, pady=15)
        self._lbl_meds = self._stat_box(stats, "Total Medicines")
        self._lbl_sales = self._stat_box(stats, "Total Sales")
        self._lbl_low = self._stat_box(stats, "Low Stock")
        self._lbl_exp = self._stat_box(stats, "Expired")

        btns = tk.Frame(self, bg="#F0F0F0")
        btns.pack(anchor="w", padx=20, pady=5)
        tk.Button(btns, text="Inventory", command=lambda: self._navigate("inventory")).pack(side="left", padx=3)
        tk.Button(btns, text="New Bill", command=lambda: self._navigate("billing")).pack(side="left", padx=3)
        tk.Button(btns, text="Reports", command=lambda: self._navigate("reports")).pack(side="left", padx=3)

        tk.Label(self, text="Recent Transactions", font=("Arial", 12, "bold"),
                 bg="#F0F0F0").pack(anchor="w", padx=20, pady=(15, 5))

        tf = tk.Frame(self)
        tf.pack(fill="both", expand=True, padx=20, pady=(0, 15))
        cols = ("bill", "date", "customer", "medicine", "qty", "total")
        self._tree = ttk.Treeview(tf, columns=cols, show="headings", height=10)
        for col, hd, w in [("bill", "Bill No", 120), ("date", "Date", 130),
                           ("customer", "Customer", 120), ("medicine", "Medicine", 150),
                           ("qty", "Qty", 50), ("total", "Total", 90)]:
            self._tree.heading(col, text=hd)
            self._tree.column(col, width=w)
        sb = ttk.Scrollbar(tf, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        self._tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

    def _stat_box(self, parent, title):
        f = tk.Frame(parent, bg="white", relief="solid", bd=1)
        f.pack(side="left", padx=8, ipadx=15, ipady=8)
        tk.Label(f, text=title, font=("Arial", 9), bg="white").pack()
        val = tk.Label(f, text="0", font=("Arial", 18, "bold"), bg="white")
        val.pack()
        return val

    def refresh(self):
        s = db.get_dashboard_stats(self._user_id)
        self._lbl_meds.config(text=str(s["total_medicines"]))
        self._lbl_sales.config(text=f"₹{s['total_sales']:,.2f}")
        self._lbl_low.config(text=str(s["low_stock_count"]))
        self._lbl_exp.config(text=str(s["expired_count"]))
        for r in self._tree.get_children():
            self._tree.delete(r)
        for t in db.get_all_transactions(self._user_id)[:15]:
            self._tree.insert("", "end", values=(
                t["bill_number"], str(t["transaction_date"])[:16],
                t["customer_name"], t["medicine_name"],
                t["quantity"], f"₹{t['total_price']:.2f}"))
