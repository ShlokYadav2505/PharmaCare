"""Simple role-specific Tkinter screens for the vendor purchase workflow."""
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import date
import database as db
import vendor_system as vs


class VendorPortalFrame(tk.Frame):
    def __init__(self, parent, username, on_logout_callback):
        super().__init__(parent, bg="#F4F7F4")
        self.username = username
        self.user_id = vs.get_user_id(username)
        self.role = vs.get_user_role(username)
        self.vendor = vs.get_vendor_for_user(self.user_id) if self.role == "vendor" else None
        self._logout = on_logout_callback
        self._build()

    def _build(self):
        head = tk.Frame(self, bg="#1B5E20")
        head.pack(fill="x")
        tk.Label(head, text=("Vendor Portal" if self.role == "vendor" else "Supplier Catalogue & Orders"),
                 bg="#1B5E20", fg="white", font=("Segoe UI", 18, "bold")).pack(side="left", padx=18, pady=14)
        tk.Label(head, text=f"{self.username} · {self.role.title()}",
                 bg="#1B5E20", fg="white", font=("Segoe UI", 10)).pack(side="left", padx=12)
        tk.Button(head, text="Logout", command=self._logout, padx=12).pack(side="right", padx=16, pady=10)

        self.body = tk.Frame(self, bg="#F4F7F4")
        self.body.pack(fill="both", expand=True, padx=18, pady=16)
        if self.role == "vendor":
            if not self.vendor:
                tk.Label(self.body, text="This vendor account has no business profile. Contact the administrator.",
                         bg="#F4F7F4", fg="#B71C1C").pack(anchor="w")
                return
            self._vendor_view()
        else:
            self._pharmacist_view()

    def _table(self, parent, columns, height=9):
        frame = tk.Frame(parent, bg="white")
        frame.pack(fill="both", expand=True, pady=(8, 10))

        # Extract column identifiers from (identifier, title, width) tuples.
        column_ids = [col[0] for col in columns]

        tree = ttk.Treeview(
            frame,
            columns=column_ids,
            show="headings",
            height=height
        )

        for col, title, width in columns:
            tree.heading(col, text=title)
            tree.column(
                col,
                width=width,
                anchor="w" if col in ("name", "vendor", "status") else "center"
            )

        scroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)

        tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        return tree

    def _vendor_view(self):
        tk.Label(self.body, text=self.vendor["business_name"], bg="#F4F7F4",
                 fg="#1B5E20", font=("Segoe UI", 14, "bold")).pack(anchor="w")
        form = tk.LabelFrame(self.body, text="Add medicine to wholesale catalogue", bg="#F4F7F4", padx=10, pady=8)
        form.pack(fill="x", pady=(8, 4))
        self.v_name = tk.StringVar()
        self.v_unit = tk.StringVar(value="pack")
        self.v_price = tk.StringVar()
        self.v_qty = tk.StringVar()
        self.v_expiry = tk.StringVar(value=date.today().replace(year=date.today().year + 1).isoformat())
        fields = [("Medicine", self.v_name, 22), ("Unit", self.v_unit, 10),
                  ("Wholesale price ₹", self.v_price, 14), ("Available quantity", self.v_qty, 14),
                  ("Expiry YYYY-MM-DD", self.v_expiry, 17)]
        for i, (label, var, width) in enumerate(fields):
            cell = tk.Frame(form, bg="#F4F7F4")
            cell.grid(row=0, column=i, padx=4, sticky="ew")
            tk.Label(cell, text=label, bg="#F4F7F4").pack(anchor="w")
            tk.Entry(cell, textvariable=var, width=width).pack(fill="x")
            form.columnconfigure(i, weight=1)
        tk.Button(form, text="Add to catalogue", command=self._add_catalog, bg="#2E7D32",
                  fg="white", padx=12).grid(row=0, column=len(fields), padx=8, pady=16)
        tk.Label(self.body, text="Your catalogue", bg="#F4F7F4",
                 font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.catalog_tree = self._table(self.body, [("name","Medicine",220),("unit","Unit",90),
            ("price","Wholesale ₹",120),("qty","Available",100),("expiry","Expiry",130)], 6)
        tk.Label(self.body, text="Orders", bg="#F4F7F4", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.orders_tree = self._table(self.body, [("id","Order #",80),("pharmacist","Pharmacist",150),
            ("total","Total ₹",120),("status","Status",150),("date","Placed",160)], 5)
        buttons = tk.Frame(self.body, bg="#F4F7F4")
        buttons.pack(fill="x")
        for label, action in [("Confirm selected", "confirm"), ("Reject selected", "reject"), ("Mark dispatched", "dispatch"), ("Refresh", "refresh")]:
            tk.Button(buttons, text=label, command=(self.refresh if action=="refresh" else lambda a=action: self._act(a)),
                      padx=12, pady=5).pack(side="left", padx=(0,8))
        self.refresh()

    def _pharmacist_view(self):
        tk.Label(self.body, text="Available wholesale medicines", bg="#F4F7F4",
                 font=("Segoe UI", 14, "bold")).pack(anchor="w")
        self.catalog_tree = self._table(self.body, [("id","Item ID",70),("vendor","Vendor",180),
            ("name","Medicine",220),("unit","Unit",80),("price","Wholesale ₹",120),
            ("qty","Available",90),("expiry","Expiry",120)], 12)
        form = tk.Frame(self.body, bg="#F4F7F4")
        form.pack(fill="x", pady=8)
        tk.Label(form, text="Order quantity:", bg="#F4F7F4").pack(side="left")
        self.order_qty = tk.StringVar(value="1")
        tk.Entry(form, textvariable=self.order_qty, width=10).pack(side="left", padx=8)
        tk.Button(form, text="Place order & email receipt", command=self._place_order,
                  bg="#2E7D32", fg="white", padx=12, pady=5).pack(side="left", padx=4)
        tk.Button(form, text="Receive selected dispatched order", command=self._receive_selected,
                  padx=12, pady=5).pack(side="left", padx=4)
        tk.Button(form, text="Cancel pending order", command=lambda: self._act("cancel"),
                  padx=12, pady=5).pack(side="left", padx=4)
        tk.Label(self.body, text="My orders", bg="#F4F7F4",
                 font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.orders_tree = self._table(self.body, [("id","Order #",80),("vendor","Vendor",180),
            ("total","Total ₹",120),("status","Status",150),("date","Placed",160)], 7)
        self.refresh()

    def _add_catalog(self):
        ok, msg = vs.add_catalog_item(self.vendor["id"], self.v_name.get(), self.v_unit.get(),
                                      self.v_price.get(), self.v_qty.get(), self.v_expiry.get())
        if not ok:
            messagebox.showerror("Catalogue", msg, parent=self)
            return
        for var in (self.v_name, self.v_price, self.v_qty):
            var.set("")
        self.refresh()
        messagebox.showinfo("Catalogue", msg, parent=self)

    def _selected_id(self, tree):
        selection = tree.selection()
        if not selection:
            messagebox.showwarning("Select a row", "Select a row first.", parent=self)
            return None
        return int(selection[0])

    def _place_order(self):
        item_id = self._selected_id(self.catalog_tree)
        if item_id is None:
            return
        rows = vs.get_catalog()
        item = next((row for row in rows if row["id"] == item_id), None)
        if not item:
            messagebox.showerror("Order", "Catalogue item is no longer available.", parent=self)
            self.refresh()
            return
        ok, result = vs.create_order(self.user_id, item["vendor_id"], item_id, self.order_qty.get())
        if not ok:
            messagebox.showerror("Order failed", result, parent=self)
            return
        user = db.get_user_by_username(self.username)
        vs.send_order_receipt(result, user["email"])
        self.refresh()
        messagebox.showinfo("Order placed", f"Order #{result} saved. An email receipt will be sent if SMTP is configured.", parent=self)

    def _receive_selected(self):
        order_id = self._selected_id(self.orders_tree)
        if order_id is None:
            return
        items = vs.get_order_items(order_id)
        if len(items) != 1:
            messagebox.showerror("Receive order", "This screen supports one medicine per order.", parent=self)
            return
        item = items[0]
        remaining = int(item["quantity"]) - int(item["received_quantity"])
        if remaining <= 0:
            messagebox.showinfo("Receive order", "This order has already been fully received.", parent=self)
            return
        qty = simpledialog.askinteger(
            "Verify delivery",
            f"Ordered: {item['quantity']}\\nAlready received: {item['received_quantity']}\\nStill expected: {remaining}\\n\\nEnter the quantity physically received now:",
            parent=self, minvalue=1, maxvalue=remaining
        )
        if qty is None:
            return
        ok, msg = vs.transition_order(order_id, "receive", self.role, self.user_id, receive_quantity=qty)
        if not ok:
            messagebox.showerror("Receive order", msg, parent=self)
        else:
            messagebox.showinfo("Receive order", msg, parent=self)
        self.refresh()

    def _act(self, action):
        tree = self.orders_tree
        order_id = self._selected_id(tree)
        if order_id is None:
            return
        ok, msg = vs.transition_order(order_id, action, self.role, self.user_id)
        if not ok:
            messagebox.showerror("Order", msg, parent=self)
        else:
            messagebox.showinfo("Order", msg, parent=self)
        self.refresh()

    def refresh(self):
        if not hasattr(self, "catalog_tree"):
            return
        for tree in (self.catalog_tree, self.orders_tree):
            for item in tree.get_children():
                tree.delete(item)
        if self.role == "vendor":
            for row in vs.get_catalog(self.vendor["id"]):
                self.catalog_tree.insert("", "end", iid=str(row["id"]), values=(row["medicine_name"], row["unit"],
                    f"{row['wholesale_price']:.2f}", row["available_quantity"], row["expiry_date"]))
            orders = vs.list_orders(vendor_id=self.vendor["id"], role="vendor")
            for row in orders:
                self.orders_tree.insert("", "end", iid=str(row["id"]), values=(row["id"], row["pharmacist_name"],
                    f"{row['total_amount']:.2f}", row["status"], row["created_at"][:16]))
        else:
            for row in vs.get_catalog():
                self.catalog_tree.insert("", "end", iid=str(row["id"]), values=(row["id"], row["business_name"],
                    row["medicine_name"], row["unit"], f"{row['wholesale_price']:.2f}",
                    row["available_quantity"], row["expiry_date"]))
            orders = vs.list_orders(user_id=self.user_id)
            for row in orders:
                self.orders_tree.insert("", "end", iid=str(row["id"]), values=(row["id"], row["business_name"],
                    f"{row['total_amount']:.2f}", row["status"], row["created_at"][:16]))
