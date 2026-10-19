# reports.py - basic reports
# UI kept. Extra: bar chart canvas + selection_sort on column header click.

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, timedelta
import csv
import database as db


class ReportsFrame(tk.Frame):
    def __init__(self, parent, user_id=None):
        super().__init__(parent, bg="#F0F0F0")
        self._user_id = user_id
        self._current = "sales"
        self._sort_rev = {}
        self._build()
        self._load("sales")

    def _build(self):
        top = tk.Frame(self, bg="#F0F0F0")
        top.pack(fill="x", padx=15, pady=10)
        tk.Label(top, text="Reports", font=("Arial", 16, "bold"), bg="#F0F0F0").pack(side="left")
        tk.Button(top, text="Export CSV", command=self._export).pack(side="right")

        tabs = tk.Frame(self, bg="#F0F0F0")
        tabs.pack(fill="x", padx=15)
        for label, key in [("Sales", "sales"), ("Stock", "stock"),
                           ("Low Stock", "low_stock"), ("Expired", "expired")]:
            tk.Button(tabs, text=label, command=lambda k=key: self._switch(k)).pack(side="left", padx=2)

        self._filter = tk.Frame(self, bg="#F0F0F0")
        self._filter.pack(fill="x", padx=15, pady=5)
        tk.Label(self._filter, text="From:", bg="#F0F0F0").pack(side="left")
        self._from = tk.Entry(self._filter, width=12)
        self._from.insert(0, (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"))
        self._from.pack(side="left", padx=3)
        tk.Label(self._filter, text="To:", bg="#F0F0F0").pack(side="left")
        self._to = tk.Entry(self._filter, width=12)
        self._to.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self._to.pack(side="left", padx=3)
        tk.Button(self._filter, text="Run", command=lambda: self._load("sales")).pack(side="left", padx=5)

        tf = tk.Frame(self)
        tf.pack(fill="both", expand=True, padx=15, pady=5)
        self._tree = ttk.Treeview(tf, show="headings")
        sb = ttk.Scrollbar(tf, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        self._tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self._summary = tk.Label(self, text="", font=("Arial", 10, "bold"), bg="#F0F0F0")
        self._summary.pack(anchor="w", padx=15, pady=4)

        # Simple visual chart (extra – does not replace existing UI)
        self._chart = tk.Canvas(self, height=120, bg="white", highlightthickness=1,
                                highlightbackground="#CCCCCC")
        self._chart.pack(fill="x", padx=15, pady=(0, 10))

    def _switch(self, key):
        self._current = key
        if key == "sales":
            self._filter.pack(fill="x", padx=15, pady=5)
        else:
            self._filter.pack_forget()
        self._load(key)

    def refresh(self):
        self._load(self._current)

    def _set_cols(self, cols):
        self._tree["columns"] = [c[0] for c in cols]
        for col, hd, w in cols:
            self._tree.heading(col, text=hd,
                               command=lambda c=col: self._sort_column(c))
            self._tree.column(col, width=w)

    def _clear(self):
        for r in self._tree.get_children():
            self._tree.delete(r)

    def _load(self, key):
        self._clear()
        getattr(self, f"_rep_{key}")()

    def _sort_column(self, col):
        """Criterion D – selection_sort on clicked column."""
        rows = []
        for iid in self._tree.get_children():
            rows.append((iid, self._tree.item(iid)["values"]))
        if not rows:
            return
        # find column index
        cols = list(self._tree["columns"])
        try:
            idx = cols.index(col)
        except ValueError:
            return
        rev = self._sort_rev.get(col, False)

        def key_func(pair):
            val = pair[1][idx]
            s = str(val).replace("₹", "").replace(",", "")
            try:
                return float(s)
            except ValueError:
                return str(val).lower()

        sorted_rows = db.selection_sort(rows, key_func, reverse=rev)
        self._clear()
        for iid, values in sorted_rows:
            self._tree.insert("", "end", values=values)
        self._sort_rev[col] = not rev

    def _draw_chart(self, labels, values, title=""):
        c = self._chart
        c.delete("all")
        w = max(c.winfo_width(), 400)
        h = 120
        if not values or max(values) <= 0:
            c.create_text(w // 2, h // 2, text="No chart data", fill="gray")
            return
        c.create_text(8, 10, text=title, anchor="w", font=("Arial", 9, "bold"))
        pad_l, pad_r, pad_t, pad_b = 8, 8, 24, 8
        n = len(values)
        gap = 6
        bar_w = max(12, (w - pad_l - pad_r - gap * (n - 1)) // n)
        mx = max(values) or 1
        chart_h = h - pad_t - pad_b
        for i, (lab, val) in enumerate(zip(labels, values)):
            x0 = pad_l + i * (bar_w + gap)
            bh = int((val / mx) * (chart_h - 4))
            y0 = h - pad_b - bh
            c.create_rectangle(x0, y0, x0 + bar_w, h - pad_b, fill="#2E7D32", outline="")
            c.create_text(x0 + bar_w // 2, y0 - 2, text=str(int(val)) if val >= 1 else f"{val:.0f}",
                          font=("Arial", 7), anchor="s")

    def _rep_sales(self):
        self._set_cols([("bill", "Bill No", 120), ("date", "Date", 140),
                        ("cust", "Customer", 120), ("med", "Medicine", 140),
                        ("qty", "Qty", 50), ("total", "Total", 90)])
        try:
            s, e = self._from.get(), self._to.get()
            datetime.strptime(s, "%Y-%m-%d")
            datetime.strptime(e, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Date", "Use YYYY-MM-DD", parent=self.winfo_toplevel()); return
        rows = db.get_transactions_by_date(self._user_id, s, e)
        grand = 0.0
        by_med = {}
        for t in rows:
            self._tree.insert("", "end", values=(
                t["bill_number"], str(t["transaction_date"])[:19],
                t["customer_name"], t["medicine_name"], t["quantity"],
                f"₹{t['total_price']:.2f}"))
            grand += float(t["total_price"])
            by_med[t["medicine_name"]] = by_med.get(t["medicine_name"], 0) + float(t["total_price"])
        self._summary.config(text=f"{len(rows)} transactions | Revenue: ₹{grand:.2f}")
        top = sorted(by_med.items(), key=lambda x: -x[1])[:8]
        self.after(50, lambda: self._draw_chart(
            [x[0][:10] for x in top], [x[1] for x in top], "Sales by medicine"))

    def _rep_stock(self):
        self._set_cols([("id", "ID", 40), ("name", "Medicine", 160),
                        ("qty", "Qty", 60), ("price", "Price", 80),
                        ("expiry", "Expiry", 100), ("status", "Status", 90)])
        meds = db.get_all_medicines(self._user_id)
        today = datetime.now().strftime("%Y-%m-%d")
        for m in meds:
            exp = str(m["expiry_date"])
            if exp <= today:
                status = "Expired"
            elif m["quantity"] <= m["min_stock"]:
                status = "Low Stock"
            else:
                status = "In Stock"
            self._tree.insert("", "end", values=(
                m["id"], m["name"], m["quantity"], f"₹{m['price']:.2f}", exp, status))
        val = sum(float(m["quantity"]) * float(m["price"]) for m in meds)
        self._summary.config(text=f"{len(meds)} SKUs | Value: ₹{val:.2f}")
        top = sorted(meds, key=lambda m: -int(m["quantity"]))[:8]
        self.after(50, lambda: self._draw_chart(
            [m["name"][:10] for m in top], [int(m["quantity"]) for m in top], "Stock levels"))

    def _rep_low_stock(self):
        self._set_cols([("id", "ID", 40), ("name", "Medicine", 180),
                        ("qty", "Current", 70), ("minst", "Min", 50), ("deficit", "Need", 60)])
        meds = db.get_low_stock_medicines(self._user_id)
        for m in meds:
            self._tree.insert("", "end", values=(
                m["id"], m["name"], m["quantity"], m["min_stock"],
                m["min_stock"] - m["quantity"]))
        self._summary.config(text=f"{len(meds)} need restocking")
        top = meds[:8]
        self.after(50, lambda: self._draw_chart(
            [m["name"][:10] for m in top],
            [max(0, m["min_stock"] - m["quantity"]) for m in top], "Units needed"))

    def _rep_expired(self):
        self._set_cols([("id", "ID", 40), ("name", "Medicine", 180),
                        ("qty", "Qty", 60), ("price", "Price", 80), ("expiry", "Expiry", 110)])
        meds = db.get_expired_medicines(self._user_id)
        for m in meds:
            self._tree.insert("", "end", values=(
                m["id"], m["name"], m["quantity"], f"₹{m['price']:.2f}", m["expiry_date"]))
        wasted = sum(float(m["quantity"]) * float(m["price"]) for m in meds)
        self._summary.config(text=f"{len(meds)} expired | Wasted: ₹{wasted:.2f}")
        top = meds[:8]
        self.after(50, lambda: self._draw_chart(
            [m["name"][:10] for m in top],
            [float(m["quantity"]) * float(m["price"]) for m in top], "Wasted value"))

    def _export(self):
        cols = self._tree["columns"]
        if not cols:
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")],
                                            parent=self.winfo_toplevel())
        if not path:
            return
        try:
            headers = [self._tree.heading(c)["text"] for c in cols]
            rows = [[self._tree.set(ch, c) for c in cols] for ch in self._tree.get_children()]
            with open(path, "w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerows([headers] + rows)
            messagebox.showinfo("Exported", path, parent=self.winfo_toplevel())
        except Exception as e:
            messagebox.showerror("Failed", str(e), parent=self.winfo_toplevel())
