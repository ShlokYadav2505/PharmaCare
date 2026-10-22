# vendors.py - Vendor management screen

import tkinter as tk
from tkinter import ttk, messagebox
import database as db
import styles as st


class VendorsFrame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=st.COLORS["background"])
        self._selected_id = None
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

        self._hist_btn = tk.Button(
            bb, text="📋 Purchase History", command=self._show_history,
            state="disabled", **st.BUTTON["secondary"]
        )
        self._hist_btn.pack(side="left")

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
        self._hist_btn.config(state="disabled")
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
            self._hist_btn.config(state="normal")
        else:
            self._selected_id = None
            self._edit_btn.config(state="disabled")
            self._del_btn.config(state="disabled")
            self._hist_btn.config(state="disabled")

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

    def _show_history(self):
        if not self._selected_id:
            return
        v = db.get_vendor_by_id(self._selected_id)
        if not v:
            return
        VendorHistoryWindow(self.winfo_toplevel(), v)


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


class VendorHistoryWindow(tk.Toplevel):
    def __init__(self, parent, vendor):
        super().__init__(parent)
        self.title(f"Purchase History – {vendor['name']}")
        self.resizable(True, True)
        self.grab_set()
        self.configure(bg=st.COLORS["white"])
        self._build(vendor)
        self.geometry("700x420")
        self._center(700, 420)

    def _center(self, w, h):
        self.update_idletasks()
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build(self, vendor):
        hdr = tk.Frame(self, bg=st.COLORS["primary_dark"])
        hdr.pack(fill="x")
        tk.Label(
            hdr, text=f"📋  Purchases from {vendor['name']}",
            font=st.FONTS["subheading"],
            bg=st.COLORS["primary_dark"], fg=st.COLORS["white"]
        ).pack(pady=12)

        tf = tk.Frame(self, bg=st.COLORS["white"])
        tf.pack(fill="both", expand=True, padx=12, pady=12)
        tf.columnconfigure(0, weight=1)
        tf.rowconfigure(0, weight=1)

        sty = ttk.Style()
        st.apply_treeview_style(sty, "VHist.Treeview")
        cols = ("id", "invoice", "date", "total")
        tree = ttk.Treeview(
            tf, columns=cols, show="headings",
            style="VHist.Treeview", selectmode="browse"
        )
        for col, hd, w in [
            ("id", "ID", 50), ("invoice", "Invoice", 140),
            ("date", "Date", 110), ("total", "Total (₹)", 110)
        ]:
            tree.heading(col, text=hd)
            tree.column(col, width=w, anchor="center")
        vsb = ttk.Scrollbar(tf, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        rows = db.get_purchases_by_vendor(vendor["id"])
        for p in rows:
            tree.insert(
                "", "end",
                values=(
                    p["id"], p["invoice_number"] or "—",
                    p["purchase_date"], f"₹{p['total_amount']:.2f}"
                )
            )
        tk.Label(
            self, text=f"{len(rows)} purchase(s)",
            font=st.FONTS["small"], bg=st.COLORS["white"],
            fg=st.COLORS["text_light"]
        ).pack(pady=(0, 8))
        tk.Button(
            self, text="Close", command=self.destroy, **st.BUTTON["primary"]
        ).pack(pady=(0, 12))
