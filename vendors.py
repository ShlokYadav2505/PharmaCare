# vendors.py - Vendor management screen

import tkinter as tk
from tkinter import ttk, messagebox
import database as db
import styles as st
import vendor_system as vs


class VendorsFrame(tk.Frame):
    def __init__(self, parent, username=None):
        super().__init__(parent, bg=st.COLORS["background"])
        self._selected_id = None
        self._username = username
        self._user_id = vs.get_user_id(username) if username else None
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        # Title + search
        top = tk.Frame(self, bg=st.COLORS["background"])
        top.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 8))
        top.columnconfigure(1, weight=1)
        tk.Label(
            top, text="Vendor Management", font=st.FONTS["heading"],
            bg=st.COLORS["background"], fg=st.COLORS["text_dark"]
        ).grid(row=0, column=0, sticky="w")

        sf = tk.Frame(
            top, bg=st.COLORS["white"],
            highlightbackground=st.COLORS["entry_border"], highlightthickness=1
        )
        sf.grid(row=0, column=1, sticky="e", padx=(20, 0))
        tk.Label(
            sf, text="🔍", bg=st.COLORS["white"],
            fg=st.COLORS["text_light"], font=("Calibri", 12)
        ).pack(side="left", padx=(8, 0))
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._do_search())
        se = tk.Entry(
            sf, textvariable=self._search_var, font=st.FONTS["entry"],
            bg=st.COLORS["white"], fg=st.COLORS["text_dark"],
            relief="flat", bd=0, width=26
        )
        se.pack(side="left", ipady=6, padx=(4, 8))

        # Buttons
        bb = tk.Frame(self, bg=st.COLORS["background"])
        bb.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 8))

        add = tk.Button(
            bb, text="+ Add Vendor", command=self._open_add, **st.BUTTON["primary"]
        )
        add.pack(side="left", padx=(0, 8))
        st.add_hover(add, st.COLORS["primary"], st.COLORS["primary_dark"])

        self._edit_btn = tk.Button(
            bb, text="✏ Edit", command=self._open_edit,
            state="disabled", **st.BUTTON["secondary"]
        )
        self._edit_btn.pack(side="left", padx=(0, 8))

        self._del_btn = tk.Button(
            bb, text="🗑 Delete", command=self._do_delete,
            state="disabled", **st.BUTTON["danger"]
        )
        self._del_btn.pack(side="left", padx=(0, 8))
        st.add_hover(self._del_btn, st.COLORS["danger"], "#B71C1C")

        self._catalog_btn = tk.Button(
            bb, text="🛒 View Catalogue", command=self._view_catalogue,
            state="disabled", **st.BUTTON["primary"]
        )
        self._catalog_btn.pack(side="left", padx=(8, 0))

        self._history_btn = tk.Button(
            bb, text="📋 Order History", command=self._show_order_history,
            state="disabled", **st.BUTTON["secondary"]
        )
        self._history_btn.pack(side="left", padx=(8, 0))

        # Treeview
        tf = tk.Frame(self, bg=st.COLORS["white"])
        tf.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 8))
        tf.columnconfigure(0, weight=1)
        tf.rowconfigure(0, weight=1)

        sty = ttk.Style()
        st.apply_treeview_style(sty, "Vend.Treeview")

        cols = ("id", "name", "contact", "phone", "email", "address")
        self._tree = ttk.Treeview(
            tf, columns=cols, show="headings",
            style="Vend.Treeview", selectmode="browse"
        )
        cfg = [
            ("id", "ID", 50, False),
            ("name", "Vendor Name", 180, True),
            ("contact", "Contact Person", 140, True),
            ("phone", "Phone", 110, False),
            ("email", "Email", 160, False),
            ("address", "Address", 180, True),
        ]
        for col, hd, w, stretch in cfg:
            self._tree.heading(col, text=hd)
            self._tree.column(col, width=w, minwidth=50, stretch=stretch, anchor="center")
        self._tree.column("name", anchor="w")
        self._tree.column("address", anchor="w")

        vsb = ttk.Scrollbar(tf, orient="vertical", command=self._tree.yview)
        hsb = ttk.Scrollbar(tf, orient="horizontal", command=self._tree.xview)
        self._tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        self._tree.bind("<<TreeviewSelect>>", self._on_select)
        self._tree.bind("<Double-1>", lambda e: self._open_edit())

        self._status = tk.StringVar(value="Ready")
        tk.Label(
            self, textvariable=self._status, font=st.FONTS["small"],
            bg=st.COLORS["background"], fg=st.COLORS["text_light"],
            anchor="w"
        ).grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 8))

    def refresh(self, data=None):
        for r in self._tree.get_children():
            self._tree.delete(r)
        self._selected_id = None
        self._edit_btn.config(state="disabled")
        self._del_btn.config(state="disabled")
        self._catalog_btn.config(state="disabled")
        self._history_btn.config(state="disabled")
        rows = data if data is not None else db.get_all_vendors()
        for v in rows:
            self._tree.insert(
                "", "end", iid=str(v["id"]),
                values=(
                    v["id"], v["name"],
                    v["contact_person"] or "",
                    v["phone"] or "",
                    v["email"] or "",
                    v["address"] or ""
                )
            )
        self._status.set(f"{len(rows)} vendor(s)")

    def _do_search(self):
        q = self._search_var.get().strip()
        if not q:
            self.refresh()
        else:
            self.refresh(db.search_vendors(q))

    def _on_select(self, _=None):
        sel = self._tree.selection()
        if sel:
            self._selected_id = int(sel[0])
            self._edit_btn.config(state="normal")
            self._del_btn.config(state="normal")
            self._catalog_btn.config(state="normal")
            self._history_btn.config(state="normal")
        else:
            self._selected_id = None
            self._edit_btn.config(state="disabled")
            self._del_btn.config(state="disabled")
            self._catalog_btn.config(state="disabled")
            self._history_btn.config(state="disabled")

    def _show_order_history(self):
        if not self._selected_id or not self._user_id:
            return
        vendor = db.get_vendor_by_id(self._selected_id)
        if not vendor:
            return
        conn = db.get_connection()
        row = conn.execute("SELECT id FROM vendor_accounts WHERE lower(trim(business_name))=lower(trim(?))", (vendor["name"],)).fetchone()
        conn.close()
        if not row:
            messagebox.showinfo("Order History", "This vendor has no vendor portal account.", parent=self)
            return
        orders = [o for o in vs.list_orders(user_id=self._user_id, role="pharmacist") if o["vendor_id"] == row["id"]]
        VendorOrderHistory(self.winfo_toplevel(), vendor["name"], orders)

    def _view_catalogue(self):
        if not self._selected_id:
            return
        if not self._username or not self._user_id:
            messagebox.showerror("Supplier Catalogue", "Could not identify the logged-in pharmacist.", parent=self)
            return
        vendor = db.get_vendor_by_id(self._selected_id)
        if not vendor:
            return
        # Vendor accounts are separate from legacy pharmacy vendors; link by business name.
        conn = db.get_connection()
        row = conn.execute("SELECT id FROM vendor_accounts WHERE lower(trim(business_name))=lower(trim(?))",
                          (vendor["name"],)).fetchone()
        conn.close()
        if not row:
            messagebox.showinfo("Supplier Catalogue",
                "This vendor has no registered vendor portal/catalogue account yet.", parent=self)
            return
        CatalogueWindow(self.winfo_toplevel(), vendor["name"], row["id"], self._user_id)

    def _open_add(self):
        VendorDialog(self.winfo_toplevel(), "Add Vendor", self._handle_add)

    def _handle_add(self, name, contact, phone, email, address):
        ok, msg = db.add_vendor(name, contact, phone, email, address)
        if ok:
            self.refresh()
            messagebox.showinfo("Success", msg, parent=self.winfo_toplevel())
        else:
            messagebox.showerror("Error", msg, parent=self.winfo_toplevel())

    def _open_edit(self):
        if not self._selected_id:
            return
        v = db.get_vendor_by_id(self._selected_id)
        if not v:
            return
        VendorDialog(
            self.winfo_toplevel(), "Edit Vendor",
            lambda *a: self._handle_edit(self._selected_id, *a),
            vendor=v
        )

    def _handle_edit(self, vid, name, contact, phone, email, address):
        ok, msg = db.update_vendor(vid, name, contact, phone, email, address)
        if ok:
            self.refresh()
            messagebox.showinfo("Success", msg, parent=self.winfo_toplevel())
        else:
            messagebox.showerror("Error", msg, parent=self.winfo_toplevel())

    def _do_delete(self):
        if not self._selected_id:
            return
        v = db.get_vendor_by_id(self._selected_id)
        if v and messagebox.askyesno(
            "Delete",
            f"Delete vendor '{v['name']}'?\nThis cannot be undone.",
            parent=self.winfo_toplevel()
        ):
            ok, msg = db.delete_vendor(self._selected_id)
            if ok:
                self.refresh()
                messagebox.showinfo("Deleted", msg, parent=self.winfo_toplevel())
            else:
                messagebox.showerror("Error", msg, parent=self.winfo_toplevel())

class CatalogueWindow(tk.Toplevel):
    """Catalogue for the vendor selected in the existing Vendor Management screen."""
    def __init__(self, parent, vendor_name, vendor_id, pharmacist_user_id):
        super().__init__(parent)
        self.title(f"Supplier Catalogue – {vendor_name}")
        self.geometry("850x470")
        self.transient(parent)
        self.vendor_id = vendor_id
        self.pharmacist_user_id = pharmacist_user_id
        self.vendor_name = vendor_name
        self.configure(bg=st.COLORS["background"])
        tk.Label(self, text=f"Available medicines – {vendor_name}",
                 font=st.FONTS["heading"], bg=st.COLORS["background"],
                 fg=st.COLORS["text_dark"]).pack(anchor="w", padx=16, pady=(14, 8))
        frame = tk.Frame(self, bg="white")
        frame.pack(fill="both", expand=True, padx=16, pady=4)
        cols = ("id", "medicine", "unit", "price", "qty", "expiry")
        self.tree = ttk.Treeview(frame, columns=cols, show="headings", selectmode="browse")
        for col, title, width in [("id","ID",55),("medicine","Medicine",220),("unit","Unit",100),
                                  ("price","Wholesale ₹",120),("qty","Available",100),("expiry","Expiry",130)]:
            self.tree.heading(col, text=title)
            self.tree.column(col, width=width, anchor="center")
        self.tree.column("medicine", anchor="w")
        self.tree.pack(side="left", fill="both", expand=True)
        scroll=ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set); scroll.pack(side="right", fill="y")
        bottom=tk.Frame(self, bg=st.COLORS["background"]); bottom.pack(fill="x", padx=16, pady=12)
        tk.Label(bottom, text="Quantity:", bg=st.COLORS["background"]).pack(side="left")
        self.quantity=tk.StringVar(value="1")
        tk.Entry(bottom, textvariable=self.quantity, width=10).pack(side="left", padx=8)
        self.total=tk.StringVar(value="Select a medicine")
        tk.Label(bottom, textvariable=self.total, bg=st.COLORS["background"]).pack(side="left", padx=10)
        tk.Button(bottom, text="Place Request", command=self._place, **st.BUTTON["primary"]).pack(side="right")
        self.tree.bind("<<TreeviewSelect>>", self._selected)
        self.refresh()

    def refresh(self):
        for item in self.tree.get_children(): self.tree.delete(item)
        for row in vs.get_catalog(self.vendor_id):
            self.tree.insert("", "end", iid=str(row["id"]), values=(row["id"], row["medicine_name"],
                row["unit"], f"{float(row['wholesale_price']):.2f}", row["available_quantity"], row["expiry_date"]))

    def _selected(self, _=None):
        sel=self.tree.selection()
        if not sel: self.total.set("Select a medicine"); return
        row=self.tree.item(sel[0], "values")
        try: qty=int(self.quantity.get())
        except ValueError: qty=0
        self.total.set(f"Total: ₹{float(row[3])*max(qty,0):.2f}")

    def _place(self):
        sel=self.tree.selection()
        if not sel:
            messagebox.showwarning("Place Request", "Select a medicine first.", parent=self); return
        try: qty=int(self.quantity.get())
        except ValueError:
            messagebox.showerror("Place Request", "Quantity must be a whole number.", parent=self); return
        if qty < 1:
            messagebox.showerror("Place Request", "Quantity must be at least 1.", parent=self); return
        item_id=int(sel[0])
        ok, result=vs.create_order(self.pharmacist_user_id, self.vendor_id, item_id, qty)
        if not ok:
            messagebox.showerror("Request failed", str(result), parent=self); return
        messagebox.showinfo("Request placed", f"Purchase request #{result} sent to {self.vendor_name}.", parent=self)
        self.refresh()


class VendorDialog(tk.Toplevel):
    def __init__(self, parent, title, on_save, vendor=None):
        super().__init__(parent)
        self.title(f"PharmaCare – {title}")
        self.resizable(False, False)
        self.grab_set()
        self.configure(bg=st.COLORS["white"])
        self._on_save = on_save
        self._build_ui(title)
        self._center(440, min(470, self.winfo_screenheight() - 80))
        if vendor:
            self._populate(vendor)

    def _center(self, w, h):
        self.update_idletasks()
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _field(self, parent, label):
        f = tk.Frame(parent, bg=st.COLORS["white"])
        f.pack(fill="x", padx=30, pady=(0, 6))
        tk.Label(
            f, text=label, font=st.FONTS["body_bold"],
            bg=st.COLORS["white"], fg=st.COLORS["text_medium"]
        ).pack(anchor="w")
        var = tk.StringVar()
        tk.Entry(f, textvariable=var, **st.ENTRY).pack(fill="x", ipady=4, pady=(2, 0))
        return var

    def _build_ui(self, title):
        hdr = tk.Frame(self, bg=st.COLORS["primary"])
        hdr.pack(fill="x")
        tk.Label(
            hdr, text=f"🏢  {title}", font=st.FONTS["subheading"],
            bg=st.COLORS["primary"], fg=st.COLORS["white"]
        ).pack(pady=10)
        # Pin actions to the bottom so they remain visible on shorter displays.
        footer = tk.Frame(self, bg=st.COLORS["white"])
        footer.pack(side="bottom", fill="x", padx=30, pady=(4, 12))
        tk.Button(footer, text="Cancel", command=self.destroy,
                  **st.BUTTON["secondary"]).pack(side="left")
        sb = tk.Button(footer, text="Save", command=self._save,
                       **st.BUTTON["primary"])
        sb.pack(side="right")
        st.add_hover(sb, st.COLORS["primary"], st.COLORS["primary_dark"])
        body = tk.Frame(self, bg=st.COLORS["white"])
        body.pack(side="top", fill="both", expand=True, pady=(8, 0))
        self._name = self._field(body, "Vendor / Company Name *")
        self._contact = self._field(body, "Contact Person")
        self._phone = self._field(body, "Phone")
        self._email = self._field(body, "Email")
        self._address = self._field(body, "Address")
        self._msg = tk.StringVar()
        tk.Label(
            body, textvariable=self._msg, font=st.FONTS["small"],
            bg=st.COLORS["white"], fg=st.COLORS["danger"], wraplength=380
        ).pack(padx=30, pady=(0, 6))

    def _populate(self, v):
        self._name.set(v["name"] or "")
        self._contact.set(v["contact_person"] or "")
        self._phone.set(v["phone"] or "")
        self._email.set(v["email"] or "")
        self._address.set(v["address"] or "")

    def _save(self):
        name = self._name.get().strip()
        if not name:
            self._msg.set("Vendor name is required.")
            return
        self._on_save(
            name,
            self._contact.get().strip(),
            self._phone.get().strip(),
            self._email.get().strip(),
            self._address.get().strip()
        )
        self.destroy()


class VendorOrderHistory(tk.Toplevel):
    """Read-only history of vendor portal orders for the selected supplier."""
    def __init__(self, parent, vendor_name, orders):
        super().__init__(parent)
        self.title(f"Order History – {vendor_name}")
        self.geometry("850x500")
        self.transient(parent)
        self.configure(bg=st.COLORS["background"])
        tk.Label(self, text=f"Orders from {vendor_name}", font=st.FONTS["heading"],
                 bg=st.COLORS["background"], fg=st.COLORS["text_dark"]).pack(anchor="w", padx=16, pady=12)
        frame=tk.Frame(self, bg=st.COLORS["white"]); frame.pack(fill="both", expand=True, padx=16, pady=4)
        cols=("order","medicine","qty","received","total","status","placed")
        self.tree=ttk.Treeview(frame,columns=cols,show="headings",selectmode="browse")
        for c,h,w in [("order","Order #",70),("medicine","Medicine",180),("qty","Ordered",80),("received","Received",80),("total","Total ₹",100),("status","Status",130),("placed","Placed",150)]:
            self.tree.heading(c,text=h); self.tree.column(c,width=w,anchor="center")
        self.tree.column("medicine",anchor="w")
        self.tree.pack(side="left",fill="both",expand=True)
        sb=ttk.Scrollbar(frame,orient="vertical",command=self.tree.yview); self.tree.configure(yscrollcommand=sb.set); sb.pack(side="right",fill="y")
        for order in orders:
            items=vs.get_order_items(order["id"])
            if not items:
                self.tree.insert("","end",values=(order["id"],"—","—","—",f"{float(item['quantity']) * float(item['unit_price']):.2f}",order["status"],str(order["created_at"] or "")[:16]))
            for item in items:
                self.tree.insert("","end",values=(order["id"],item["medicine_name"],item["quantity"],item["received_quantity"],f"{float(order['total_amount']):.2f}",order["status"],str(order["created_at"] or "")[:16]))
        footer=tk.Frame(self,bg=st.COLORS["background"]); footer.pack(fill="x",padx=16,pady=12)
        tk.Label(footer,text=f"{len(orders)} order(s)",bg=st.COLORS["background"],fg=st.COLORS["text_light"]).pack(side="left")
        tk.Button(footer,text="Close",command=self.destroy,**st.BUTTON["primary"]).pack(side="right")
