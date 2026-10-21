import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import random, string
import database as db
import smtp_handler as smtp
import styles as st


def _gen_bill_no():
    s = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"BILL-{datetime.now().strftime('%Y%m%d')}-{s}"


class BillingFrame(tk.Frame):
    def __init__(self, parent, user_email=""):
        super().__init__(parent, bg=st.COLORS["background"])
        self._user_email = user_email
        self._items = []
        self._build_ui()
        self._load_medicines()

    def _build_ui(self):
        self.columnconfigure(0, weight=3)
        self.columnconfigure(1, weight=2)
        self.rowconfigure(0, weight=1)

        left  = tk.Frame(self, bg=st.COLORS["background"])
        left.grid(row=0, column=0, sticky="nsew", padx=(16,8), pady=16)
        left.columnconfigure(0, weight=1)
        left.rowconfigure(3, weight=1)
        self._build_left(left)

        right = tk.Frame(self, bg=st.COLORS["white"],
                         highlightbackground=st.COLORS["border"], highlightthickness=1)
        right.grid(row=0, column=1, sticky="nsew", padx=(8,16), pady=16)
        right.columnconfigure(0, weight=1)
        self._build_right(right)

    def _build_left(self, p):
        tk.Label(p, text="New Bill", font=st.FONTS["heading"],
                 bg=st.COLORS["background"], fg=st.COLORS["text_dark"]
                 ).grid(row=0, column=0, sticky="w", pady=(0,10))

        sel = tk.Frame(p, bg=st.COLORS["white"],
                       highlightbackground=st.COLORS["border"], highlightthickness=1)
        sel.grid(row=1, column=0, sticky="ew", pady=(0,10))
        sel.columnconfigure(1, weight=1)

        tk.Label(sel, text="Select Medicine", font=st.FONTS["body_bold"],
                 bg=st.COLORS["white"], fg=st.COLORS["text_medium"]
                 ).grid(row=0, column=0, columnspan=3, sticky="w", padx=14, pady=(12,4))

        tk.Label(sel, text="Medicine:", font=st.FONTS["body"],
                 bg=st.COLORS["white"], fg=st.COLORS["text_medium"]
                 ).grid(row=1, column=0, padx=(14,6), pady=6, sticky="w")
        self._med_var = tk.StringVar()
        self._combo   = ttk.Combobox(sel, textvariable=self._med_var,
                                     state="readonly", width=28, font=st.FONTS["body"])
        self._combo.grid(row=1, column=1, padx=(0,10), pady=6, sticky="ew")
        self._combo.bind("<<ComboboxSelected>>", self._on_med_select)

        tk.Label(sel, text="Qty:", font=st.FONTS["body"],
                 bg=st.COLORS["white"], fg=st.COLORS["text_medium"]
                 ).grid(row=2, column=0, padx=(14,6), pady=6, sticky="w")
        self._qty_var = tk.StringVar(value="1")
        tk.Spinbox(sel, textvariable=self._qty_var, from_=1, to=9999,
                   font=st.FONTS["body"], width=8, relief="solid", bd=1
                   ).grid(row=2, column=1, padx=(0,10), pady=6, sticky="w")

        self._info_var = tk.StringVar(value="Select a medicine to see details")
        tk.Label(sel, textvariable=self._info_var, font=st.FONTS["small"],
                 bg=st.COLORS["white"], fg=st.COLORS["text_light"]
                 ).grid(row=3, column=0, columnspan=3, padx=14, pady=(0,6), sticky="w")

        ab = tk.Button(sel, text="+ Add to Bill",
                       command=self._add_item, **st.BUTTON["primary"])
        ab.grid(row=4, column=0, columnspan=3, padx=14, pady=(0,12), sticky="ew")
        st.add_hover(ab, st.COLORS["primary"], st.COLORS["primary_dark"])

        lbl_row = tk.Frame(p, bg=st.COLORS["background"])
        lbl_row.grid(row=2, column=0, sticky="ew")
        tk.Label(lbl_row, text="Bill Items", font=st.FONTS["subheading"],
                 bg=st.COLORS["background"], fg=st.COLORS["text_dark"]).pack(side="left")
        rb = tk.Button(lbl_row, text="🗑 Remove", command=self._remove_item,
                       **st.BUTTON["sm_danger"])
        rb.pack(side="right")

        tf = tk.Frame(p, bg=st.COLORS["white"])
        tf.grid(row=3, column=0, sticky="nsew", pady=(4,0))
        tf.columnconfigure(0, weight=1); tf.rowconfigure(0, weight=1)

        sty = ttk.Style()
        st.apply_treeview_style(sty, "Bill.Treeview")
        cols = ("sno","name","qty","price","total")
        self._tree = ttk.Treeview(tf, columns=cols, show="headings",
                                   style="Bill.Treeview", selectmode="browse")
        for col, hd, w in [("sno","#",40),("name","Medicine",200),
                            ("qty","Qty",60),("price","Unit Price",100),("total","Total",100)]:
            self._tree.heading(col, text=hd)
            self._tree.column(col, width=w, anchor="center")
        self._tree.column("name", anchor="w")
        vsb = ttk.Scrollbar(tf, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

    def _build_right(self, p):
        hdr = tk.Frame(p, bg=st.COLORS["primary_dark"])
        hdr.pack(fill="x")
        tk.Label(hdr, text="📋  Bill Summary", font=st.FONTS["subheading"],
                 bg=st.COLORS["primary_dark"], fg=st.COLORS["white"]).pack(pady=14)

        body = tk.Frame(p, bg=st.COLORS["white"])
        body.pack(fill="both", expand=True, padx=20, pady=20)

        tk.Label(body, text="Bill Number", font=st.FONTS["body_bold"],
                 bg=st.COLORS["white"], fg=st.COLORS["text_medium"]).pack(anchor="w")
        self._bill_no = tk.StringVar(value=_gen_bill_no())
        tk.Entry(body, textvariable=self._bill_no, state="readonly", **st.ENTRY
                 ).pack(fill="x", ipady=6, pady=(4,12))

        tk.Label(body, text="Customer Name", font=st.FONTS["body_bold"],
                 bg=st.COLORS["white"], fg=st.COLORS["text_medium"]).pack(anchor="w")
        self._cust = tk.StringVar(value="Walk-in Customer")
        tk.Entry(body, textvariable=self._cust, **st.ENTRY).pack(fill="x", ipady=6, pady=(4,16))

        tk.Frame(body, bg=st.COLORS["border"], height=1).pack(fill="x", pady=4)

        def tot_row(lbl, attr, colour=None):
            r = tk.Frame(body, bg=st.COLORS["white"]); r.pack(fill="x", pady=4)
            tk.Label(r, text=lbl, font=st.FONTS["body"],
                     bg=st.COLORS["white"], fg=st.COLORS["text_medium"]).pack(side="left")
            v = tk.StringVar(value="₹0.00")
            setattr(self, attr, v)
            tk.Label(r, textvariable=v, font=st.FONTS["body_bold"],
                     bg=st.COLORS["white"],
                     fg=colour or st.COLORS["text_dark"]).pack(side="right")

        tot_row("Subtotal:",  "_subtotal")
        tot_row("Discount (₹):", "_disc_lbl", st.COLORS["warning"])
        tk.Frame(body, bg=st.COLORS["border"], height=1).pack(fill="x", pady=4)
        tot_row("TOTAL:",     "_total_lbl", st.COLORS["primary"])

        dr = tk.Frame(body, bg=st.COLORS["white"]); dr.pack(fill="x", pady=(8,4))
        tk.Label(dr, text="Discount (₹):", font=st.FONTS["body"],
                 bg=st.COLORS["white"], fg=st.COLORS["text_medium"]).pack(side="left")
        self._disc_var = tk.StringVar(value="0")
        self._disc_var.trace_add("write", lambda *_: self._update_totals())
        tk.Entry(dr, textvariable=self._disc_var, width=10, **st.ENTRY
                 ).pack(side="right", ipady=4)

        self._count_var = tk.StringVar(value="0 item(s)")
        tk.Label(body, textvariable=self._count_var, font=st.FONTS["small"],
                 bg=st.COLORS["white"], fg=st.COLORS["text_light"]).pack(anchor="e", pady=(4,0))

        tk.Frame(body, bg=st.COLORS["white"]).pack(expand=True)

        gb = tk.Button(body, text="💳  Generate Bill",
                       command=self._generate, **st.BUTTON["primary"])
        gb.pack(fill="x", pady=(0,8))
        st.add_hover(gb, st.COLORS["primary"], st.COLORS["primary_dark"])

        cb = tk.Button(body, text="🗑  Clear Bill",
                       command=self._clear, **st.BUTTON["danger"])
        cb.pack(fill="x")
        st.add_hover(cb, st.COLORS["danger"], "#B71C1C")

    def _load_medicines(self):
        meds = db.get_all_medicines()
        self._meds = {
            f"{m['name']}  (Stock:{m['quantity']}  ₹{m['price']:.2f})": dict(m)
            for m in meds}
        self._combo["values"] = list(self._meds.keys())

    def refresh(self):
        self._load_medicines()

    def _on_med_select(self, _=None):
        m = self._meds.get(self._med_var.get())
        if m:
            self._info_var.set(f"Price: ₹{m['price']:.2f}  |  Stock: {m['quantity']}  |  Expiry: {m['expiry_date']}")

    def _add_item(self):
        key = self._med_var.get()
        if not key:
            messagebox.showwarning("Select Medicine", "Please select a medicine.",
                                   parent=self.winfo_toplevel()); return
        med = self._meds.get(key)
        try:
            qty = int(self._qty_var.get())
            if qty <= 0: raise ValueError
        except ValueError:
            messagebox.showerror("Invalid Qty", "Quantity must be ≥ 1.",
                                 parent=self.winfo_toplevel()); return

        # Check non-expired stock via FEFO allocation (preview only)
        already = sum(i["qty"] for i in self._items if i["medicine_id"] == med["id"])
        needed = qty + already
        allocation = db.fefo_allocate(med["id"], needed)
        if not allocation:
            # how much is actually available?
            avail = sum(b["quantity"] for b in db.get_batches_for_medicine(med["id"])
                        if b["expiry_date"] >= datetime.now().strftime("%Y-%m-%d"))
            messagebox.showerror(
                "Insufficient / Expired Stock",
                f"Only {avail} non-expired unit(s) available for '{med['name']}'.\n"
                "Expired batches cannot be sold.",
                parent=self.winfo_toplevel()
            )
            return

        for item in self._items:
            if item["medicine_id"] == med["id"]:
                item["qty"] += qty
                item["total"] = round(item["qty"] * item["price"], 2)
                self._refresh_tree(); self._update_totals(); return

        self._items.append({"medicine_id": med["id"], "name": med["name"],
                            "qty": qty, "price": med["price"],
                            "total": round(qty * med["price"], 2)})
        self._refresh_tree(); self._update_totals()

    def _remove_item(self):
        sel = self._tree.selection()
        if not sel: return
        idx = int(self._tree.item(sel[0])["values"][0]) - 1
        if 0 <= idx < len(self._items):
            self._items.pop(idx)
            self._refresh_tree(); self._update_totals()

    def _refresh_tree(self):
        for r in self._tree.get_children(): self._tree.delete(r)
        for i, item in enumerate(self._items, 1):
            self._tree.insert("", "end", values=(
                i, item["name"], item["qty"],
                f"₹{item['price']:.2f}", f"₹{item['total']:.2f}"))

    def _update_totals(self):
        sub = sum(i["total"] for i in self._items)
        try:
            disc = max(float(self._disc_var.get() or 0), 0)
        except ValueError:
            disc = 0
        total = max(sub - disc, 0)
        self._subtotal.set(f"₹{sub:.2f}")
        self._disc_lbl.set(f"₹{disc:.2f}")
        self._total_lbl.set(f"₹{total:.2f}")
        self._count_var.set(f"{len(self._items)} item(s)")

    def _clear(self):
        if self._items and not messagebox.askyesno("Clear", "Clear the bill?",
                                                    parent=self.winfo_toplevel()): return
        self._items.clear(); self._refresh_tree(); self._update_totals()
        self._bill_no.set(_gen_bill_no())

    def _generate(self):
        if not self._items:
            messagebox.showwarning("Empty", "Add at least one medicine.",
                                   parent=self.winfo_toplevel()); return
        bill_no = self._bill_no.get()
        cust    = self._cust.get().strip() or "Walk-in Customer"
        try:
            disc = max(float(self._disc_var.get() or 0), 0)
        except ValueError:
            disc = 0
        sub   = sum(i["total"] for i in self._items)
        total = max(sub - disc, 0)

        if not messagebox.askyesno("Confirm Bill",
            f"Bill: {bill_no}\nCustomer: {cust}\n"
            f"Items: {len(self._items)}\nTotal: ₹{total:.2f}\n\nGenerate?",
            parent=self.winfo_toplevel()): return

        low_stock_meds = []
        for item in self._items:
            # FEFO: allocate from earliest-expiry non-expired batches
            allocation = db.fefo_allocate(item["medicine_id"], item["qty"])
            if not allocation:
                messagebox.showerror(
                    "Stock Error",
                    f"Not enough non-expired stock for '{item['name']}'.",
                    parent=self.winfo_toplevel()
                )
                return
            ok, result = db.fefo_commit(item["medicine_id"], allocation)
            if not ok:
                messagebox.showerror("Stock Error", str(result),
                                     parent=self.winfo_toplevel())
                return
            # Record one transaction line per batch used (for accurate COGS)
            remaining_to_record = item["qty"]
            for batch_id, take, cost_price in result:
                if remaining_to_record <= 0:
                    break
                line_qty = min(take, remaining_to_record)
                line_total = round(line_qty * item["price"], 2)
                db.add_transaction(
                    bill_no, item["medicine_id"], item["name"],
                    line_qty, item["price"], line_total, cust,
                    cost_price=cost_price, batch_id=batch_id
                )
                remaining_to_record -= line_qty
            med = db.get_medicine_by_id(item["medicine_id"])
            if med and med["quantity"] <= med["min_stock"]:
                low_stock_meds.append(med)

        ReceiptWindow(self.winfo_toplevel(), bill_no, cust,
                      self._items, sub, disc, total)
        if low_stock_meds and self._user_email:
            smtp.send_low_stock_alert(self._user_email, low_stock_meds)
        self._clear()
        self._load_medicines()


class ReceiptWindow(tk.Toplevel):
    def __init__(self, parent, bill_no, customer, items, sub, disc, total):
        super().__init__(parent)
        self.title(f"Receipt – {bill_no}")
        self.resizable(False, False)
        self.grab_set()
        self.configure(bg=st.COLORS["white"])
        self._build(bill_no, customer, items, sub, disc, total)
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - 440) // 2
        y = (self.winfo_screenheight() - 580) // 2
        self.geometry(f"440x580+{x}+{y}")

    def _build(self, bill_no, customer, items, sub, disc, total):
        txt = tk.Text(self, font=("Courier New", 11), bg=st.COLORS["white"],
                      fg=st.COLORS["text_dark"], relief="flat", bd=0,
                      padx=20, pady=10, wrap="none", state="normal")
        txt.pack(fill="both", expand=True, padx=10, pady=(10,0))
        sep = "-" * 50
        r = (f"{'PharmaCare':^50}\n{'Pharmacy Management System':^50}\n{sep}\n"
             f"Bill No  : {bill_no}\nCustomer : {customer}\n"
             f"Date     : {datetime.now().strftime('%Y-%m-%d  %H:%M:%S')}\n{sep}\n"
             f"{'Item':<22}{'Qty':>5}{'Price':>10}{'Total':>11}\n{sep}\n")
        for item in items:
            r += (f"{item['name'][:22]:<22}{item['qty']:>5}"
                  f"{'₹'+str(round(item['price'],2)):>10}"
                  f"{'₹'+str(round(item['total'],2)):>11}\n")
        r += (f"{sep}\n{'Subtotal':<38}{'₹'+str(round(sub,2)):>10}\n"
              f"{'Discount':<38}{'₹'+str(round(disc,2)):>10}\n{'='*50}\n"
              f"{'TOTAL':<38}{'₹'+str(round(total,2)):>10}\n{'='*50}\n"
              f"{'Thank You! Visit Again.':^50}\n")
        txt.insert("1.0", r)
        txt.config(state="disabled")
        vsb = ttk.Scrollbar(self, orient="vertical", command=txt.yview)
        vsb.pack(side="right", fill="y")
        txt.config(yscrollcommand=vsb.set)
        tk.Button(self, text="Close", command=self.destroy,
                  **st.BUTTON["primary"]).pack(pady=10)