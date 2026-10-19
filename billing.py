# billing.py - basic billing
# UI unchanged. Logic: queue for line items; email bill; auto low-stock alert.

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from collections import deque
import random
import string
import database as db
import smtp_handler as smtp


def _bill_no():
    s = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"BILL-{datetime.now().strftime('%Y%m%d')}-{s}"


class BillingFrame(tk.Frame):
    def __init__(self, parent, user_id=None, user_email=""):
        super().__init__(parent, bg="#F0F0F0")
        self._user_id = user_id
        self._user_email = user_email
        # Criterion D: bill lines as FIFO queue
        self._item_queue = deque()
        self._items = []
        self._build()
        self._load_meds()

    def _build(self):
        left = tk.Frame(self, bg="#F0F0F0")
        left.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        tk.Label(left, text="New Bill", font=("Arial", 16, "bold"), bg="#F0F0F0").pack(anchor="w")

        sel = tk.LabelFrame(left, text="Select Medicine", padx=8, pady=8)
        sel.pack(fill="x", pady=8)
        self._med_var = tk.StringVar()
        self._combo = ttk.Combobox(sel, textvariable=self._med_var, state="readonly", width=40)
        self._combo.pack(anchor="w")
        self._combo.bind("<<ComboboxSelected>>", self._on_select)
        row = tk.Frame(sel)
        row.pack(anchor="w", pady=5)
        tk.Label(row, text="Qty:").pack(side="left")
        self._qty = tk.Spinbox(row, from_=1, to=9999, width=8)
        self._qty.pack(side="left", padx=5)
        tk.Button(row, text="Add to Bill", command=self._add_item).pack(side="left", padx=5)
        self._info = tk.Label(sel, text="", font=("Arial", 9), fg="gray")
        self._info.pack(anchor="w")

        mid = tk.Frame(left, bg="#F0F0F0")
        mid.pack(fill="x")
        tk.Label(mid, text="Bill Items", font=("Arial", 12, "bold"), bg="#F0F0F0").pack(side="left")
        tk.Button(mid, text="Remove", command=self._remove).pack(side="right")

        tf = tk.Frame(left)
        tf.pack(fill="both", expand=True, pady=5)
        cols = ("sno", "name", "qty", "price", "total")
        self._tree = ttk.Treeview(tf, columns=cols, show="headings", height=12)
        for col, hd, w in [("sno", "#", 40), ("name", "Medicine", 150),
                           ("qty", "Qty", 50), ("price", "Price", 80), ("total", "Total", 80)]:
            self._tree.heading(col, text=hd)
            self._tree.column(col, width=w)
        self._tree.pack(fill="both", expand=True)

        # Right summary
        right = tk.LabelFrame(self, text="Bill Summary", padx=12, pady=12)
        right.pack(side="right", fill="y", padx=10, pady=10)

        tk.Label(right, text="Bill No").pack(anchor="w")
        self._bill_no = tk.Entry(right, width=28)
        self._bill_no.insert(0, _bill_no())
        self._bill_no.config(state="readonly")
        self._bill_no.pack(pady=(0, 8))

        tk.Label(right, text="Customer").pack(anchor="w")
        self._cust = tk.Entry(right, width=28)
        self._cust.insert(0, "Walk-in Customer")
        self._cust.pack(pady=(0, 8))

        tk.Label(right, text="Customer Email").pack(anchor="w")
        self._cust_email = tk.Entry(right, width=28)
        self._cust_email.pack(pady=(0, 8))

        self._sub_lbl = tk.Label(right, text="Subtotal: ₹0.00", font=("Arial", 11))
        self._sub_lbl.pack(anchor="w", pady=2)
        tk.Label(right, text="Discount (₹):").pack(anchor="w")
        self._disc = tk.Entry(right, width=10)
        self._disc.insert(0, "0")
        self._disc.pack(anchor="w")
        self._disc.bind("<KeyRelease>", lambda e: self._update_totals())
        self._total_lbl = tk.Label(right, text="TOTAL: ₹0.00", font=("Arial", 12, "bold"))
        self._total_lbl.pack(anchor="w", pady=8)
        self._count_lbl = tk.Label(right, text="0 item(s)", font=("Arial", 9), fg="gray")
        self._count_lbl.pack(anchor="w")

        tk.Button(right, text="Generate Bill", width=20, command=self._generate).pack(pady=(20, 5))
        tk.Button(right, text="Clear", width=20, command=self._clear).pack()

    def _load_meds(self):
        meds = db.get_all_medicines(self._user_id)
        self._meds = {f"{m['name']} (Stock:{m['quantity']} ₹{m['price']:.2f})": dict(m) for m in meds}
        self._combo["values"] = list(self._meds.keys())

    def refresh(self):
        self._load_meds()

    def _on_select(self, _=None):
        m = self._meds.get(self._med_var.get())
        if m:
            self._info.config(
                text=f"Price: ₹{m['price']:.2f} | Stock: {m['quantity']} | Exp: {m['expiry_date']}")

    def _add_item(self):
        key = self._med_var.get()
        if not key:
            messagebox.showwarning("Select", "Please select a medicine from the list.",
                                   parent=self.winfo_toplevel()); return
        med = self._meds.get(key)
        if not med:
            messagebox.showerror("Error", "Invalid medicine selection.",
                                 parent=self.winfo_toplevel()); return
        qty_s = str(self._qty.get()).strip()
        if not qty_s:
            messagebox.showerror("Qty", "Quantity is required.",
                                 parent=self.winfo_toplevel()); return
        try:
            qty = int(qty_s)
        except ValueError:
            messagebox.showerror("Qty", "Quantity must be a whole number (e.g. 1, 2, 10).",
                                 parent=self.winfo_toplevel()); return
        if qty <= 0:
            messagebox.showerror("Qty", "Quantity must be at least 1.",
                                 parent=self.winfo_toplevel()); return
        if qty > 9999:
            messagebox.showerror("Qty", "Quantity is too large (max 9999).",
                                 parent=self.winfo_toplevel()); return
        already = sum(i["qty"] for i in self._items if i["medicine_id"] == med["id"])
        if qty + already > med["quantity"]:
            available = med["quantity"] - already
            messagebox.showerror(
                "Insufficient Stock",
                f"Only {available} unit(s) available for '{med['name']}'.",
                parent=self.winfo_toplevel()); return
        today = datetime.now().strftime("%Y-%m-%d")
        if str(med["expiry_date"]) <= today:
            if not messagebox.askyesno(
                    "Expired Medicine",
                    f"'{med['name']}' has expired ({med['expiry_date']}).\nAdd to bill anyway?",
                    parent=self.winfo_toplevel()):
                return
        for item in self._items:
            if item["medicine_id"] == med["id"]:
                item["qty"] += qty
                item["total"] = round(item["qty"] * item["price"], 2)
                self._refresh_tree(); self._update_totals(); return
        item = {
            "medicine_id": med["id"], "name": med["name"],
            "qty": qty, "price": med["price"],
            "total": round(qty * med["price"], 2)}
        self._item_queue.append(item)  # Criterion D – enqueue
        self._items.append(item)
        self._refresh_tree(); self._update_totals()

    def _remove(self):
        sel = self._tree.selection()
        if not sel:
            return
        idx = int(self._tree.item(sel[0])["values"][0]) - 1
        if 0 <= idx < len(self._items):
            removed = self._items.pop(idx)
            # keep queue in sync
            try:
                self._item_queue.remove(removed)
            except ValueError:
                pass
            self._refresh_tree(); self._update_totals()

    def _refresh_tree(self):
        for r in self._tree.get_children():
            self._tree.delete(r)
        for i, item in enumerate(self._items, 1):
            self._tree.insert("", "end", values=(
                i, item["name"], item["qty"],
                f"₹{item['price']:.2f}", f"₹{item['total']:.2f}"))

    def _update_totals(self):
        sub = sum(i["total"] for i in self._items)
        try:
            disc = max(float(self._disc.get() or 0), 0)
        except ValueError:
            disc = 0
        total = max(sub - disc, 0)
        self._sub_lbl.config(text=f"Subtotal: ₹{sub:.2f}")
        self._total_lbl.config(text=f"TOTAL: ₹{total:.2f}")
        self._count_lbl.config(text=f"{len(self._items)} item(s)")

    def _clear(self):
        if self._items and not messagebox.askyesno("Clear", "Clear bill?",
                                                   parent=self.winfo_toplevel()):
            return
        self._item_queue.clear()
        self._items.clear()
        self._refresh_tree(); self._update_totals()
        self._bill_no.config(state="normal")
        self._bill_no.delete(0, "end")
        self._bill_no.insert(0, _bill_no())
        self._bill_no.config(state="readonly")

    def _generate(self):
        if not self._items:
            messagebox.showwarning("Empty Bill", "Add at least one medicine before generating.",
                                   parent=self.winfo_toplevel()); return
        bill_no = self._bill_no.get()
        cust = self._cust.get().strip() or "Walk-in Customer"
        if len(cust) > 100:
            messagebox.showerror("Customer", "Customer name is too long.",
                                 parent=self.winfo_toplevel()); return
        disc_s = str(self._disc.get()).strip() or "0"
        try:
            disc = float(disc_s)
        except ValueError:
            messagebox.showerror("Discount", "Discount must be a number (e.g. 0 or 50).",
                                 parent=self.winfo_toplevel()); return
        if disc < 0:
            messagebox.showerror("Discount", "Discount cannot be negative.",
                                 parent=self.winfo_toplevel()); return
        sub = sum(i["total"] for i in self._items)
        if disc > sub:
            messagebox.showerror("Discount", f"Discount cannot exceed subtotal (₹{sub:.2f}).",
                                 parent=self.winfo_toplevel()); return
        disc = max(disc, 0)
        total = max(sub - disc, 0)
        if not messagebox.askyesno("Confirm",
                f"{bill_no}\n{cust}\nItems: {len(self._items)}\nTotal: ₹{total:.2f}\nGenerate?",
                parent=self.winfo_toplevel()):
            return
        low = []
        for item in self._items:
            ok, _ = db.reduce_medicine_quantity(self._user_id, item["medicine_id"], item["qty"])
            if not ok:
                continue
            db.add_transaction(self._user_id, bill_no, item["medicine_id"], item["name"],
                               item["qty"], item["price"], item["total"], cust)
            med = db.get_medicine_by_id(item["medicine_id"], self._user_id)
            if med and med["quantity"] <= med["min_stock"]:
                low.append(med)

        # Criterion D – push bill onto stack
        db.push_bill({
            "bill_no": bill_no, "customer": cust,
            "items": list(self._items), "sub": sub, "disc": disc, "total": total,
        })

        ReceiptWindow(self.winfo_toplevel(), bill_no, cust, self._items, sub, disc, total)

        # Email bill to the CUSTOMER (not the pharmacy staff account)
        cust_email = self._cust_email.get().strip()
        if cust_email:
            if "@" not in cust_email or "." not in cust_email.split("@")[-1]:
                messagebox.showwarning(
                    "Customer Email",
                    "Bill saved, but customer email looks invalid – email not sent.",
                    parent=self.winfo_toplevel())
            else:
                smtp.send_bill_email(
                    cust_email, bill_no, cust,
                    list(self._items), sub, disc, total,
                    callback=lambda ok, m: self.after(
                        0,
                        lambda: messagebox.showinfo(
                            "Bill Email",
                            f"Bill emailed to {cust_email}." if ok else f"Email failed: {m}",
                            parent=self.winfo_toplevel(),
                        ),
                    ),
                )
        # else: walk-in with no email – bill still saved, no email

        # Automatic low-stock alert after sale → pharmacy user
        if low and self._user_email:
            db.enqueue_alert("low_stock", self._user_email, low)
            smtp.send_low_stock_alert(self._user_email, low)

        self._clear()


class ReceiptWindow(tk.Toplevel):
    def __init__(self, parent, bill_no, customer, items, sub, disc, total):
        super().__init__(parent)
        self.title(f"Receipt - {bill_no}")
        self.geometry("400x450")
        self.grab_set()
        t = tk.Text(self, font=("Courier New", 10), wrap="none")
        t.pack(fill="both", expand=True, padx=10, pady=10)
        sep = "-" * 42
        r = (f"{'PharmaCare':^42}\n{sep}\n"
             f"Bill: {bill_no}\nCustomer: {customer}\n"
             f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n{sep}\n")
        for item in items:
            r += f"{item['name'][:18]:<18}{item['qty']:>4}  ₹{item['total']:.2f}\n"
        r += f"{sep}\nSubtotal: ₹{sub:.2f}\nDiscount: ₹{disc:.2f}\nTOTAL: ₹{total:.2f}\n"
        t.insert("1.0", r)
        t.config(state="disabled")
        tk.Button(self, text="Close", command=self.destroy).pack(pady=8)
