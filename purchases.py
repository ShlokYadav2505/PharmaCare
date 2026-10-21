# purchases.py - Record stock received from vendors (batches)

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import database as db
import styles as st


class PurchasesFrame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=st.COLORS["background"])
        self._items = []  # list of pending line items
        self._build_ui()
        self._load_lists()

    def _build_ui(self):
        self.columnconfigure(0, weight=3)
        self.columnconfigure(1, weight=2)
        self.rowconfigure(0, weight=1)

        left = tk.Frame(self, bg=st.COLORS["background"])
        left.grid(row=0, column=0, sticky="nsew", padx=(16, 8), pady=16)
        left.columnconfigure(0, weight=1)
        left.rowconfigure(4, weight=1)
        self._build_left(left)

        right = tk.Frame(
            self, bg=st.COLORS["white"],
            highlightbackground=st.COLORS["border"], highlightthickness=1
        )
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 16), pady=16)
        right.columnconfigure(0, weight=1)
        self._build_right(right)

    def _build_left(self, p):
        tk.Label(
            p, text="Record Purchase / Add Stock", font=st.FONTS["heading"],
            bg=st.COLORS["background"], fg=st.COLORS["text_dark"]
        ).grid(row=0, column=0, sticky="w", pady=(0, 10))

        # Header fields: vendor, invoice, date
        hdr = tk.Frame(
            p, bg=st.COLORS["white"],
            highlightbackground=st.COLORS["border"], highlightthickness=1
        )
        hdr.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        hdr.columnconfigure(1, weight=1)

        tk.Label(
            hdr, text="Vendor *", font=st.FONTS["body_bold"],
            bg=st.COLORS["white"], fg=st.COLORS["text_medium"]
        ).grid(row=0, column=0, padx=(12, 6), pady=8, sticky="w")
        self._vendor_var = tk.StringVar()
        self._vendor_combo = ttk.Combobox(
            hdr, textvariable=self._vendor_var, state="readonly",
            width=28, font=st.FONTS["body"]
        )
        self._vendor_combo.grid(row=0, column=1, padx=(0, 12), pady=8, sticky="ew")

        tk.Label(
            hdr, text="Invoice No.", font=st.FONTS["body_bold"],
            bg=st.COLORS["white"], fg=st.COLORS["text_medium"]
        ).grid(row=1, column=0, padx=(12, 6), pady=4, sticky="w")
        self._invoice_var = tk.StringVar()
        tk.Entry(hdr, textvariable=self._invoice_var, **st.ENTRY).grid(
            row=1, column=1, padx=(0, 12), pady=4, sticky="ew", ipady=4
        )

        tk.Label(
            hdr, text="Purchase Date *", font=st.FONTS["body_bold"],
            bg=st.COLORS["white"], fg=st.COLORS["text_medium"]
        ).grid(row=2, column=0, padx=(12, 6), pady=4, sticky="w")
        self._pdate_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        tk.Entry(hdr, textvariable=self._pdate_var, **st.ENTRY).grid(
            row=2, column=1, padx=(0, 12), pady=4, sticky="ew", ipady=4
        )

        # Line item entry
        line = tk.Frame(
            p, bg=st.COLORS["white"],
            highlightbackground=st.COLORS["border"], highlightthickness=1
        )
        line.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        line.columnconfigure(1, weight=1)

        tk.Label(
            line, text="Add Medicine Batch", font=st.FONTS["body_bold"],
            bg=st.COLORS["white"], fg=st.COLORS["text_medium"]
        ).grid(row=0, column=0, columnspan=3, sticky="w", padx=12, pady=(10, 4))

        tk.Label(
            line, text="Medicine *", font=st.FONTS["body"],
            bg=st.COLORS["white"], fg=st.COLORS["text_medium"]
        ).grid(row=1, column=0, padx=(12, 6), pady=4, sticky="w")
        self._med_var = tk.StringVar()
        self._med_combo = ttk.Combobox(
            line, textvariable=self._med_var, state="readonly",
            width=28, font=st.FONTS["body"]
        )
        self._med_combo.grid(row=1, column=1, columnspan=2, padx=(0, 12), pady=4, sticky="ew")

        tk.Label(
            line, text="Batch No. *", font=st.FONTS["body"],
            bg=st.COLORS["white"], fg=st.COLORS["text_medium"]
        ).grid(row=2, column=0, padx=(12, 6), pady=4, sticky="w")
        self._batch_var = tk.StringVar()
        tk.Entry(line, textvariable=self._batch_var, **st.ENTRY).grid(
            row=2, column=1, columnspan=2, padx=(0, 12), pady=4, sticky="ew", ipady=4
        )

        tk.Label(
            line, text="Qty *", font=st.FONTS["body"],
            bg=st.COLORS["white"], fg=st.COLORS["text_medium"]
        ).grid(row=3, column=0, padx=(12, 6), pady=4, sticky="w")
        self._qty_var = tk.StringVar(value="1")
        tk.Entry(line, textvariable=self._qty_var, width=10, **st.ENTRY).grid(
            row=3, column=1, padx=(0, 8), pady=4, sticky="w", ipady=4
        )

        tk.Label(
            line, text="Cost/Unit (₹) *", font=st.FONTS["body"],
            bg=st.COLORS["white"], fg=st.COLORS["text_medium"]
        ).grid(row=4, column=0, padx=(12, 6), pady=4, sticky="w")
        self._cost_var = tk.StringVar(value="0")
        tk.Entry(line, textvariable=self._cost_var, width=10, **st.ENTRY).grid(
            row=4, column=1, padx=(0, 8), pady=4, sticky="w", ipady=4
        )

        tk.Label(
            line, text="Expiry (YYYY-MM-DD) *", font=st.FONTS["body"],
            bg=st.COLORS["white"], fg=st.COLORS["text_medium"]
        ).grid(row=5, column=0, padx=(12, 6), pady=4, sticky="w")
        self._exp_var = tk.StringVar()
        tk.Entry(line, textvariable=self._exp_var, **st.ENTRY).grid(
            row=5, column=1, columnspan=2, padx=(0, 12), pady=4, sticky="ew", ipady=4
        )

        ab = tk.Button(
            line, text="+ Add Line", command=self._add_line, **st.BUTTON["primary"]
        )
        ab.grid(row=6, column=0, columnspan=3, padx=12, pady=(6, 12), sticky="ew")
        st.add_hover(ab, st.COLORS["primary"], st.COLORS["primary_dark"])

        # Items list
        lbl_row = tk.Frame(p, bg=st.COLORS["background"])
        lbl_row.grid(row=3, column=0, sticky="ew")
        tk.Label(
            lbl_row, text="Purchase Lines", font=st.FONTS["subheading"],
            bg=st.COLORS["background"], fg=st.COLORS["text_dark"]
        ).pack(side="left")
        rb = tk.Button(
            lbl_row, text="🗑 Remove", command=self._remove_line, **st.BUTTON["sm_danger"]
        )
        rb.pack(side="right")

        tf = tk.Frame(p, bg=st.COLORS["white"])
        tf.grid(row=4, column=0, sticky="nsew", pady=(4, 0))
        tf.columnconfigure(0, weight=1)
        tf.rowconfigure(0, weight=1)

        sty = ttk.Style()
        st.apply_treeview_style(sty, "Purch.Treeview")
        cols = ("med", "batch", "qty", "cost", "exp", "line_total")
        self._tree = ttk.Treeview(
            tf, columns=cols, show="headings",
            style="Purch.Treeview", selectmode="browse"
        )
        for col, hd, w in [
            ("med", "Medicine", 140), ("batch", "Batch", 90),
            ("qty", "Qty", 50), ("cost", "Cost", 70),
            ("exp", "Expiry", 100), ("line_total", "Line Total", 90)
        ]:
            self._tree.heading(col, text=hd)
            self._tree.column(col, width=w, anchor="center")
        self._tree.column("med", anchor="w")
        vsb = ttk.Scrollbar(tf, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

    def _build_right(self, p):
        hdr = tk.Frame(p, bg=st.COLORS["primary_dark"])
        hdr.pack(fill="x")
        tk.Label(
            hdr, text="📦  Purchase Summary", font=st.FONTS["subheading"],
            bg=st.COLORS["primary_dark"], fg=st.COLORS["white"]
        ).pack(pady=14)

        body = tk.Frame(p, bg=st.COLORS["white"])
        body.pack(fill="both", expand=True, padx=20, pady=20)

        self._total_var = tk.StringVar(value="₹0.00")
        self._count_var = tk.StringVar(value="0 line(s)")

        tk.Label(
            body, text="Total Purchase Cost", font=st.FONTS["body_bold"],
            bg=st.COLORS["white"], fg=st.COLORS["text_medium"]
        ).pack(anchor="w")
        tk.Label(
            body, textvariable=self._total_var, font=st.FONTS["card_number"],
            bg=st.COLORS["white"], fg=st.COLORS["primary"]
        ).pack(anchor="w", pady=(4, 12))

        tk.Label(
            body, textvariable=self._count_var, font=st.FONTS["small"],
            bg=st.COLORS["white"], fg=st.COLORS["text_light"]
        ).pack(anchor="w")

        tk.Label(
            body, text="Notes", font=st.FONTS["body_bold"],
            bg=st.COLORS["white"], fg=st.COLORS["text_medium"]
        ).pack(anchor="w", pady=(16, 4))
        self._notes_var = tk.StringVar()
        tk.Entry(body, textvariable=self._notes_var, **st.ENTRY).pack(
            fill="x", ipady=6
        )

        tk.Frame(body, bg=st.COLORS["white"]).pack(expand=True)

        gb = tk.Button(
            body, text="✅  Confirm Receipt",
            command=self._confirm, **st.BUTTON["primary"]
        )
        gb.pack(fill="x", pady=(0, 8))
        st.add_hover(gb, st.COLORS["primary"], st.COLORS["primary_dark"])

        cb = tk.Button(
            body, text="🗑  Clear", command=self._clear, **st.BUTTON["danger"]
        )
        cb.pack(fill="x")
        st.add_hover(cb, st.COLORS["danger"], "#B71C1C")

        # Recent purchases mini list
        tk.Label(
            body, text="Recent Purchases", font=st.FONTS["small_bold"],
            bg=st.COLORS["white"], fg=st.COLORS["text_medium"]
        ).pack(anchor="w", pady=(20, 4))
        self._recent = tk.Label(
            body, text="", font=st.FONTS["small"],
            bg=st.COLORS["white"], fg=st.COLORS["text_light"],
            justify="left", wraplength=220
        )
        self._recent.pack(anchor="w")

    def _load_lists(self):
        vendors = db.get_all_vendors()
        self._vendors = {f"{v['name']}  (ID:{v['id']})": v for v in vendors}
        self._vendor_combo["values"] = list(self._vendors.keys())

        meds = db.get_all_medicines()
        self._meds = {f"{m['name']}  (ID:{m['id']})": m for m in meds}
        self._med_combo["values"] = list(self._meds.keys())

        # recent
        recent = db.get_all_purchases()[:5]
        if recent:
            lines = [
                f"• {p['vendor_name']}: ₹{p['total_amount']:.0f} ({p['purchase_date']})"
                for p in recent
            ]
            self._recent.config(text="\n".join(lines))
        else:
            self._recent.config(text="No purchases yet.")

    def refresh(self):
        self._load_lists()

    def _add_line(self):
        key = self._med_var.get()
        if not key:
            messagebox.showwarning(
                "Select Medicine", "Please select a medicine.",
                parent=self.winfo_toplevel()
            )
            return
        med = self._meds.get(key)
        batch = self._batch_var.get().strip()
        if not batch:
            messagebox.showwarning(
                "Batch Required", "Enter the batch number from the packaging.",
                parent=self.winfo_toplevel()
            )
            return
        try:
            qty = int(self._qty_var.get())
            if qty <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror(
                "Invalid Qty", "Quantity must be a positive integer.",
                parent=self.winfo_toplevel()
            )
            return
        try:
            cost = float(self._cost_var.get())
            if cost < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror(
                "Invalid Cost", "Cost price must be a non-negative number.",
                parent=self.winfo_toplevel()
            )
            return
        exp = self._exp_var.get().strip()
        try:
            exp_d = datetime.strptime(exp, "%Y-%m-%d").date()
        except ValueError:
            messagebox.showerror(
                "Invalid Date", "Expiry date must be YYYY-MM-DD.",
                parent=self.winfo_toplevel()
            )
            return
        if exp_d < datetime.now().date():
            messagebox.showerror(
                "Expired Stock",
                "Cannot receive stock that is already expired.",
                parent=self.winfo_toplevel()
            )
            return

        # soft warning for duplicate batch number
        existing = db.get_batches_for_medicine(med["id"], only_available=False)
        for b in existing:
            if b["batch_number"] == batch:
                if not messagebox.askyesno(
                    "Duplicate Batch",
                    f"Batch '{batch}' already exists for {med['name']}.\n"
                    "Add as a separate batch record anyway?",
                    parent=self.winfo_toplevel()
                ):
                    return
                break

        line_total = round(qty * cost, 2)
        self._items.append({
            "medicine_id": med["id"],
            "name": med["name"],
            "batch_number": batch,
            "quantity": qty,
            "cost_price": cost,
            "expiry_date": exp,
            "line_total": line_total,
        })
        self._refresh_tree()
        # clear line fields
        self._batch_var.set("")
        self._qty_var.set("1")
        self._cost_var.set("0")
        self._exp_var.set("")

    def _remove_line(self):
        sel = self._tree.selection()
        if not sel:
            return
        idx = self._tree.index(sel[0])
        if 0 <= idx < len(self._items):
            self._items.pop(idx)
            self._refresh_tree()

    def _refresh_tree(self):
        for r in self._tree.get_children():
            self._tree.delete(r)
        total = 0.0
        for it in self._items:
            self._tree.insert(
                "", "end",
                values=(
                    it["name"], it["batch_number"], it["quantity"],
                    f"₹{it['cost_price']:.2f}", it["expiry_date"],
                    f"₹{it['line_total']:.2f}"
                )
            )
            total += it["line_total"]
        self._total_var.set(f"₹{total:.2f}")
        self._count_var.set(f"{len(self._items)} line(s)")

    def _clear(self):
        if self._items and not messagebox.askyesno(
            "Clear", "Clear all lines?", parent=self.winfo_toplevel()
        ):
            return
        self._items.clear()
        self._refresh_tree()
        self._invoice_var.set("")
        self._notes_var.set("")

    def _confirm(self):
        if not self._items:
            messagebox.showwarning(
                "Empty", "Add at least one medicine batch.",
                parent=self.winfo_toplevel()
            )
            return
        vkey = self._vendor_var.get()
        if not vkey:
            messagebox.showwarning(
                "Vendor", "Select a vendor.", parent=self.winfo_toplevel()
            )
            return
        vendor = self._vendors[vkey]
        pdate = self._pdate_var.get().strip()
        try:
            datetime.strptime(pdate, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror(
                "Date", "Purchase date must be YYYY-MM-DD.",
                parent=self.winfo_toplevel()
            )
            return

        total = sum(i["line_total"] for i in self._items)
        if not messagebox.askyesno(
            "Confirm Purchase",
            f"Vendor: {vendor['name']}\n"
            f"Invoice: {self._invoice_var.get() or '—'}\n"
            f"Lines: {len(self._items)}\n"
            f"Total Cost: ₹{total:.2f}\n\n"
            "This will increase inventory. Continue?",
            parent=self.winfo_toplevel()
        ):
            return

        items_payload = [
            {
                "medicine_id": it["medicine_id"],
                "batch_number": it["batch_number"],
                "quantity": it["quantity"],
                "cost_price": it["cost_price"],
                "expiry_date": it["expiry_date"],
            }
            for it in self._items
        ]
        ok, msg, pid = db.record_purchase(
            vendor["id"],
            self._invoice_var.get().strip(),
            pdate,
            items_payload,
            self._notes_var.get().strip()
        )
        if ok:
            messagebox.showinfo("Success", msg, parent=self.winfo_toplevel())
            self._items.clear()
            self._refresh_tree()
            self._invoice_var.set("")
            self._notes_var.set("")
            self._load_lists()
        else:
            messagebox.showerror("Error", msg, parent=self.winfo_toplevel())
