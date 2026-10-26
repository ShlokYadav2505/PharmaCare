import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
import database as db
import invoices
import styles as st


class ReportsFrame(tk.Frame):
    TABS = [("Sales","sales"), ("Stock","stock"),
            ("Low Stock","low_stock"), ("Expired","expired"),
            ("Purchases","purchases"), ("Batches","batches"),
            ("Financial","financial"), ("Vendor Hist.","vendor_hist")]

    def __init__(self, parent):
        super().__init__(parent, bg=st.COLORS["background"])
        self._current = "sales"
        self._build_ui()
        self._load("sales")

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)

        # Title
        top = tk.Frame(self, bg=st.COLORS["background"])
        top.grid(row=0, column=0, sticky="ew", padx=20, pady=(16,8))
        tk.Label(top, text="Reports & Analytics", font=st.FONTS["heading"],
                 bg=st.COLORS["background"], fg=st.COLORS["text_dark"]).pack(side="left")
        tk.Button(top, text="View Invoice", command=self._open_invoice,
                  **st.BUTTON["secondary"]).pack(side="right", padx=(8, 0))
        tk.Button(top, text="📥 Export CSV", command=self._export,
                  **st.BUTTON["secondary"]).pack(side="right")

        # Tab selector
        tabs = tk.Frame(self, bg=st.COLORS["white"],
                        highlightbackground=st.COLORS["border"], highlightthickness=1)
        tabs.grid(row=1, column=0, sticky="ew", padx=20, pady=(0,8))
        self._tab_btns = {}
        for label, key in self.TABS:
            b = tk.Button(tabs, text=label, font=st.FONTS["body_bold"],
                          relief="flat", cursor="hand2", padx=18, pady=10, bd=0,
                          command=lambda k=key: self._switch(k))
            b.pack(side="left")
            self._tab_btns[key] = b
        self._highlight("sales")

        # Date filter (sales only)
        self._filter = tk.Frame(self, bg=st.COLORS["background"])
        self._filter.grid(row=2, column=0, sticky="ew", padx=20, pady=(0,6))
        self._filter.columnconfigure(4, weight=1)
        tk.Label(self._filter, text="From:", font=st.FONTS["body_bold"],
                 bg=st.COLORS["background"], fg=st.COLORS["text_medium"]
                 ).grid(row=0, column=0, padx=(0,6))
        self._from = tk.StringVar(value=(datetime.now()-timedelta(days=30)).strftime("%Y-%m-%d"))
        tk.Entry(self._filter, textvariable=self._from, width=13, **st.ENTRY
                 ).grid(row=0, column=1, ipady=5, padx=(0,12))
        tk.Label(self._filter, text="To:", font=st.FONTS["body_bold"],
                 bg=st.COLORS["background"], fg=st.COLORS["text_medium"]
                 ).grid(row=0, column=2, padx=(0,6))
        self._to = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        tk.Entry(self._filter, textvariable=self._to, width=13, **st.ENTRY
                 ).grid(row=0, column=3, ipady=5, padx=(0,12))
        rb = tk.Button(self._filter, text="🔍 Run",
                       command=lambda: self._load(self._current), **st.BUTTON["sm_primary"])
        rb.grid(row=0, column=4, padx=(0,8))
        st.add_hover(rb, st.COLORS["primary"], st.COLORS["primary_dark"])
        for label, days in [("Today",0),("7 Days",7),("30 Days",30)]:
            b = tk.Button(self._filter, text=label, font=st.FONTS["small"],
                          bg=st.COLORS["light_green"], fg=st.COLORS["primary"],
                          relief="flat", cursor="hand2", padx=8, pady=4, bd=0,
                          command=lambda d=days: self._quick(d))
            b.grid(row=0, column=5+[0,7,30].index(days), padx=4)
            st.add_hover(b, st.COLORS["light_green"], st.COLORS["secondary"])

        # Treeview
        tf = tk.Frame(self, bg=st.COLORS["white"],
                      highlightbackground=st.COLORS["border"], highlightthickness=1)
        tf.grid(row=3, column=0, sticky="nsew", padx=20, pady=(0,8))
        tf.columnconfigure(0, weight=1); tf.rowconfigure(0, weight=1)

        sty = ttk.Style()
        st.apply_treeview_style(sty, "Rep.Treeview")
        self._tree = ttk.Treeview(tf, show="headings",
                                   style="Rep.Treeview", selectmode="browse")
        vsb = ttk.Scrollbar(tf, orient="vertical", command=self._tree.yview)
        hsb = ttk.Scrollbar(tf, orient="horizontal", command=self._tree.xview)
        self._tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        self._tree.tag_configure("low",     background="#FFF3E0")
        self._tree.tag_configure("expired", background="#FFEBEE")
        self._tree.tag_configure("alt",     background=st.COLORS["row_even"])
        self._tree.bind("<Double-1>", self._open_invoice)

        self._summary = tk.StringVar()
        tk.Label(self, textvariable=self._summary, font=st.FONTS["body_bold"],
                 bg=st.COLORS["background"], fg=st.COLORS["primary"], anchor="w"
                 ).grid(row=4, column=0, sticky="ew", padx=20, pady=(0,12))

    def _highlight(self, key):
        for k, b in self._tab_btns.items():
            b.config(bg=st.COLORS["primary"] if k==key else st.COLORS["white"],
                     fg=st.COLORS["white"]   if k==key else st.COLORS["text_medium"])

    def _switch(self, key):
        self._current = key
        self._highlight(key)
        if key in ("sales", "purchases", "financial", "vendor_hist"):
            self._filter.grid()
        else:
            self._filter.grid_remove()
        self._load(key)

    def refresh(self):
        self._load(self._current)

    def _set_cols(self, cols):
        self._tree["columns"] = [c[0] for c in cols]
        for col, hd, w, anchor in cols:
            self._tree.heading(col, text=hd,
                               command=lambda c=col: self._sort(c))
            self._tree.column(col, width=w, minwidth=50,
                              anchor=anchor, stretch=(col==cols[1][0]))

    def _clear(self):
        for r in self._tree.get_children(): self._tree.delete(r)

    def _load(self, key):
        self._clear()
        getattr(self, f"_rep_{key}")()

    def _open_invoice(self, _event=None):
        selection = self._tree.selection()
        if not selection:
            messagebox.showinfo("Select an invoice", "Select a sales or purchase row first.",
                                parent=self.winfo_toplevel())
            return
        values = self._tree.item(selection[0], "values")
        if self._current == "sales":
            invoices.open_invoice(self.winfo_toplevel(), "sale", values[0])
        elif self._current in ("purchases", "vendor_hist"):
            invoices.open_invoice(self.winfo_toplevel(), "purchase", values[0])
        else:
            messagebox.showinfo("Invoice view", "Open Sales or Purchases and select a row.",
                                parent=self.winfo_toplevel())

    def _quick(self, days):
        end = datetime.now(); start = end - timedelta(days=days)
        self._from.set(start.strftime("%Y-%m-%d"))
        self._to.set(end.strftime("%Y-%m-%d"))
        self._load("sales")

    def _rep_sales(self):
        self._set_cols([("bill","Bill No",130,"center"),("date","Date",150,"center"),
                        ("cust","Customer",140,"w"),("med","Medicine",170,"w"),
                        ("qty","Qty",60,"center"),("up","Unit Price",100,"center"),
                        ("total","Total (₹)",100,"center")])
        try:
            s = self._from.get(); e = self._to.get()
            datetime.strptime(s,"%Y-%m-%d"); datetime.strptime(e,"%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Date Error","Use YYYY-MM-DD format.",
                                 parent=self.winfo_toplevel()); return
        rows = db.get_transactions_by_date(s, e)
        grand = 0.0
        for i, t in enumerate(rows):
            self._tree.insert("","end", tags=("alt" if i%2==0 else "",),
                values=(t["bill_number"],t["transaction_date"][:19],
                        t["customer_name"],t["medicine_name"],t["quantity"],
                        f"₹{t['unit_price']:.2f}",f"₹{t['total_price']:.2f}"))
            grand += t["total_price"]
        self._summary.set(f"{len(rows)} transaction(s)  |  Revenue: ₹{grand:.2f}  |  {s} → {e}")

    def _rep_stock(self):
        self._set_cols([("id","ID",55,"center"),("name","Medicine",200,"w"),
                        ("qty","Quantity",90,"center"),("price","Price (₹)",100,"center"),
                        ("expiry","Expiry Date",120,"center"),("minst","Min Stock",90,"center"),
                        ("status","Status",120,"center")])
        meds  = db.get_all_medicines()
        today = datetime.now().strftime("%Y-%m-%d")
        for i, m in enumerate(meds):
            if m["expiry_date"] <= today:   status, tag = "⚠ Expired",   "expired"
            elif m["quantity"] <= m["min_stock"]: status, tag = "⚡ Low Stock", "low"
            else:                            status, tag = "✔ In Stock",  "alt" if i%2==0 else ""
            self._tree.insert("","end", tags=(tag,),
                values=(m["id"],m["name"],m["quantity"],
                        f"₹{m['price']:.2f}",m["expiry_date"],m["min_stock"],status))
        val = sum(float(m["quantity"])*float(m["price"]) for m in meds)
        self._summary.set(f"Total SKUs: {len(meds)}  |  Inventory Value: ₹{val:.2f}")

    def _rep_low_stock(self):
        self._set_cols([("id","ID",55,"center"),("name","Medicine",220,"w"),
                        ("qty","Current Qty",110,"center"),("minst","Min Stock",90,"center"),
                        ("deficit","Deficit",80,"center"),("price","Price (₹)",100,"center"),
                        ("expiry","Expiry Date",120,"center")])
        meds = db.get_low_stock_medicines()
        for i, m in enumerate(meds):
            deficit = m["min_stock"] - m["quantity"]
            self._tree.insert("","end", tags=("low" if i%2==0 else "expired",),
                values=(m["id"],m["name"],m["quantity"],m["min_stock"],
                        deficit,f"₹{m['price']:.2f}",m["expiry_date"]))
        self._summary.set(f"⚡  {len(meds)} medicine(s) require restocking")

    def _rep_expired(self):
        self._set_cols([("id","ID",55,"center"),("name","Medicine",220,"w"),
                        ("qty","Quantity",90,"center"),("price","Price (₹)",100,"center"),
                        ("expiry","Expiry Date",130,"center"),("minst","Min Stock",90,"center")])
        meds = db.get_expired_medicines()
        for m in meds:
            self._tree.insert("","end", tags=("expired",),
                values=(m["id"],m["name"],m["quantity"],
                        f"₹{m['price']:.2f}",m["expiry_date"],m["min_stock"]))
        wasted = sum(float(m["quantity"])*float(m["price"]) for m in meds)
        self._summary.set(f"⚠  {len(meds)} expired  |  Wasted Value: ₹{wasted:.2f}")


    def _rep_purchases(self):
        self._set_cols([("id","ID",50,"center"),("vendor","Vendor",150,"w"),
                        ("invoice","Invoice",120,"center"),("date","Date",110,"center"),
                        ("total","Total (₹)",110,"center")])
        try:
            s = self._from.get(); e = self._to.get()
            datetime.strptime(s,"%Y-%m-%d"); datetime.strptime(e,"%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Date Error","Use YYYY-MM-DD format.",
                                 parent=self.winfo_toplevel()); return
        rows = db.get_purchases_by_date(s, e)
        grand = 0.0
        for i, p in enumerate(rows):
            self._tree.insert("","end", tags=("alt" if i%2==0 else "",),
                values=(p["id"], p["vendor_name"], p["invoice_number"] or "—",
                        p["purchase_date"], f"₹{p['total_amount']:.2f}"))
            grand += float(p["total_amount"])
        self._summary.set(f"{len(rows)} purchase(s)  |  Total Purchases: ₹{grand:.2f}  |  {s} → {e}")

    def _rep_batches(self):
        self._set_cols([("id","ID",50,"center"),("med","Medicine",160,"w"),
                        ("batch","Batch No",100,"center"),("qty","Qty",60,"center"),
                        ("cost","Cost/Unit",90,"center"),("expiry","Expiry",110,"center"),
                        ("status","Status",120,"center")])
        rows = db.get_all_batches()
        for i, b in enumerate(rows):
            status, tag = db.batch_status(b["expiry_date"])
            if b["quantity"] <= 0:
                status, tag = "— Empty", ""
            self._tree.insert("","end", tags=(tag or ("alt" if i%2==0 else ""),),
                values=(b["id"], b["medicine_name"], b["batch_number"],
                        b["quantity"], f"₹{b['cost_price']:.2f}",
                        b["expiry_date"], status))
        self._summary.set(f"{len(rows)} batch record(s)")

    def _rep_financial(self):
        self._set_cols([("metric","Metric",220,"w"),("value","Value (₹)",140,"center")])
        try:
            s = self._from.get(); e = self._to.get()
            datetime.strptime(s,"%Y-%m-%d"); datetime.strptime(e,"%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Date Error","Use YYYY-MM-DD format.",
                                 parent=self.winfo_toplevel()); return
        fin = db.get_financial_summary(s, e)
        rows = [
            ("Revenue (Sales)", fin["revenue"]),
            ("Expenditure: Vendor Purchases (received)", fin["purchases_total"]),
            ("Expenditure: Operating Expenses", fin["expenses"]),
            ("Total Expenditure", fin["expenditure"]),
            ("Profit (Revenue - Expenditure)", fin["profit"]),
        ]
        for i, (metric, val) in enumerate(rows):
            self._tree.insert("","end", tags=("alt" if i%2==0 else "",),
                values=(metric, f"₹{val:,.2f}"))
        self._summary.set(
            f"Financial Summary  |  {s} → {e}  |  "
            f"Revenue: ₹{fin['revenue']:,.2f}  Expenditure: ₹{fin['expenditure']:,.2f}  Profit: ₹{fin['profit']:,.2f}"
        )

    def _rep_vendor_hist(self):
        self._set_cols([("id","ID",50,"center"),("vendor","Vendor",150,"w"),
                        ("invoice","Invoice",120,"center"),("date","Date",110,"center"),
                        ("total","Total (₹)",110,"center")])
        try:
            s = self._from.get(); e = self._to.get()
            datetime.strptime(s,"%Y-%m-%d"); datetime.strptime(e,"%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Date Error","Use YYYY-MM-DD format.",
                                 parent=self.winfo_toplevel()); return
        rows = db.get_purchases_by_date(s, e)
        for i, p in enumerate(rows):
            self._tree.insert("","end", tags=("alt" if i%2==0 else "",),
                values=(p["id"], p["vendor_name"], p["invoice_number"] or "—",
                        p["purchase_date"], f"₹{p['total_amount']:.2f}"))
        self._summary.set(f"Vendor purchase history  |  {len(rows)} record(s)  |  {s} → {e}")

    _sort_rev = {}
    def _sort(self, col):
        rev  = self._sort_rev.get(col, False)
        data = [(self._tree.set(c, col), c) for c in self._tree.get_children("")]
        data.sort(key=lambda t: t[0], reverse=rev)
        for i, (_, iid) in enumerate(data): self._tree.move(iid, "", i)
        self._sort_rev[col] = not rev

    def _export(self):
        from tkinter import filedialog
        import csv
        cols = self._tree["columns"]
        if not cols:
            messagebox.showinfo("Export","No data to export.",
                                parent=self.winfo_toplevel()); return
        name = f"PharmaCare_{self._current}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        path = filedialog.asksaveasfilename(defaultextension=".csv",
            filetypes=[("CSV","*.csv")], initialfile=name,
            parent=self.winfo_toplevel())
        if not path: return
        try:
            headers = [self._tree.heading(c)["text"] for c in cols]
            rows = [[self._tree.set(ch, c) for c in cols]
                    for ch in self._tree.get_children()]
            with open(path, "w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerows([headers] + rows)
            messagebox.showinfo("Exported", f"Saved to:\n{path}",
                                parent=self.winfo_toplevel())
        except Exception as e:
            messagebox.showerror("Failed", str(e), parent=self.winfo_toplevel())
