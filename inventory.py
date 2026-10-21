import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import database as db
import smtp_handler as smtp
import styles as st


class InventoryFrame(tk.Frame):
    def __init__(self, parent, user_email=""):
        super().__init__(parent, bg=st.COLORS["background"])
        self._user_email  = user_email
        self._selected_id = None
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        # Title + search bar
        top = tk.Frame(self, bg=st.COLORS["background"])
        top.grid(row=0, column=0, sticky="ew", padx=20, pady=(16,8))
        top.columnconfigure(1, weight=1)
        tk.Label(top, text="Inventory Management", font=st.FONTS["heading"],
                 bg=st.COLORS["background"], fg=st.COLORS["text_dark"]).grid(row=0, column=0, sticky="w")

        sf = tk.Frame(top, bg=st.COLORS["white"],
                      highlightbackground=st.COLORS["entry_border"], highlightthickness=1)
        sf.grid(row=0, column=1, sticky="e", padx=(20,0))
        tk.Label(sf, text="🔍", bg=st.COLORS["white"],
                 fg=st.COLORS["text_light"], font=("Calibri",12)).pack(side="left", padx=(8,0))
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._do_search())
        se = tk.Entry(sf, textvariable=self._search_var, font=st.FONTS["entry"],
                      bg=st.COLORS["white"], fg=st.COLORS["text_dark"],
                      relief="flat", bd=0, width=26)
        se.pack(side="left", ipady=6, padx=(4,8))

        # Buttons
        bb = tk.Frame(self, bg=st.COLORS["background"])
        bb.grid(row=1, column=0, sticky="ew", padx=20, pady=(0,8))

        add = tk.Button(bb, text="+ Add Medicine",
                        command=self._open_add, **st.BUTTON["primary"])
        add.pack(side="left", padx=(0,8))
        st.add_hover(add, st.COLORS["primary"], st.COLORS["primary_dark"])

        self._edit_btn = tk.Button(bb, text="✏ Edit",
                                   command=self._open_edit,
                                   state="disabled", **st.BUTTON["secondary"])
        self._edit_btn.pack(side="left", padx=(0,8))

        self._del_btn = tk.Button(bb, text="🗑 Delete",
                                  command=self._do_delete,
                                  state="disabled", **st.BUTTON["danger"])
        self._del_btn.pack(side="left")
        st.add_hover(self._del_btn, st.COLORS["danger"], "#B71C1C")

        ab = tk.Button(bb, text="📧 Low Stock Alert",
                       command=self._alert_low, **st.BUTTON["warning"])
        ab.pack(side="right", padx=(8,0))
        st.add_hover(ab, st.COLORS["warning"], "#BF360C")

        eb = tk.Button(bb, text="📧 Expiry Alert",
                       command=self._alert_expired, **st.BUTTON["sm_danger"])
        eb.pack(side="right", padx=(8,0))
        st.add_hover(eb, st.COLORS["danger"], "#B71C1C")

        # Treeview
        tf = tk.Frame(self, bg=st.COLORS["white"])
        tf.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0,8))
        tf.columnconfigure(0, weight=1); tf.rowconfigure(0, weight=1)

        sty = ttk.Style()
        st.apply_treeview_style(sty, "Inv.Treeview")

        cols = ("id","name","qty","price","expiry","min_stock","status")
        self._tree = ttk.Treeview(tf, columns=cols, show="headings",
                                   style="Inv.Treeview", selectmode="browse")
        cfg = [("id","ID",55,False),("name","Medicine Name",200,True),
               ("qty","Quantity",90,False),("price","Price (₹)",100,False),
               ("expiry","Expiry Date",120,False),("min_stock","Min Stock",90,False),
               ("status","Status",120,False)]
        for col, hd, w, stretch in cfg:
            self._tree.heading(col, text=hd, command=lambda c=col: self._sort(c))
            self._tree.column(col, width=w, minwidth=60, stretch=stretch, anchor="center")
        self._tree.column("name", anchor="w")

        vsb = ttk.Scrollbar(tf, orient="vertical", command=self._tree.yview)
        hsb = ttk.Scrollbar(tf, orient="horizontal", command=self._tree.xview)
        self._tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        self._tree.bind("<<TreeviewSelect>>", self._on_select)
        self._tree.bind("<Double-1>", lambda e: self._open_edit())
        self._tree.tag_configure("low",     background="#FFF3E0")
        self._tree.tag_configure("expired", background="#FFEBEE")

        self._status = tk.StringVar(value="Ready")
        tk.Label(self, textvariable=self._status, font=st.FONTS["small"],
                 bg=st.COLORS["background"], fg=st.COLORS["text_light"],
                 anchor="w").grid(row=3, column=0, sticky="ew", padx=20, pady=(0,8))

    def refresh(self, data=None):
        for r in self._tree.get_children():
            self._tree.delete(r)
        self._selected_id = None
        self._edit_btn.config(state="disabled")
        self._del_btn.config(state="disabled")
        rows = data if data is not None else db.get_all_medicines()
        for med in rows:
            qty = med["quantity"]
            minst = med["min_stock"]
            batches = db.get_batches_for_medicine(med["id"], only_available=True)
            if not batches or qty <= 0:
                status, tag = "— Empty", ""
                exp_disp = med["expiry_date"] or "—"
            else:
                earliest = min(b["expiry_date"] for b in batches)
                exp_disp = earliest
                st_label, tag = db.batch_status(earliest)
                if qty <= minst and tag != "expired":
                    status, tag = "⚡ Low Stock", "low"
                else:
                    status = st_label
            self._tree.insert(
                "", "end", iid=str(med["id"]),
                values=(med["id"], med["name"], qty,
                        f"₹{med['price']:.2f}", exp_disp, minst, status),
                tags=(tag,)
            )
        self._status.set(f"{len(rows)} medicine(s) found")

    def _do_search(self):
        q = self._search_var.get()
        self.refresh() if not q else self.refresh(db.search_medicines(q))

    _sort_rev = {}
    def _sort(self, col):
        rev  = self._sort_rev.get(col, False)
        data = [(self._tree.set(c, col), c) for c in self._tree.get_children("")]
        data.sort(key=lambda t: t[0], reverse=rev)
        for i, (_, iid) in enumerate(data): self._tree.move(iid, "", i)
        self._sort_rev[col] = not rev

    def _on_select(self, _=None):
        sel = self._tree.selection()
        if sel:
            self._selected_id = int(sel[0])
            self._edit_btn.config(state="normal")
            self._del_btn.config(state="normal")
        else:
            self._selected_id = None
            self._edit_btn.config(state="disabled")
            self._del_btn.config(state="disabled")

    def _open_add(self):
        MedicineDialog(self.winfo_toplevel(), "Add Medicine", self._handle_add)

    def _handle_add(self, name, qty, price, expiry, minst):
        ok, msg = db.add_medicine(name, qty, price, expiry, minst)
        if ok:
            self.refresh()
            messagebox.showinfo("Success", msg, parent=self.winfo_toplevel())
        else:
            messagebox.showerror("Error", msg, parent=self.winfo_toplevel())

    def _open_edit(self):
        if not self._selected_id: return
        med = db.get_medicine_by_id(self._selected_id)
        if not med: return
        MedicineDialog(self.winfo_toplevel(), "Edit Medicine",
                       lambda *a: self._handle_edit(self._selected_id, *a),
                       medicine=med)

    def _handle_edit(self, mid, name, qty, price, expiry, minst):
        ok, msg = db.update_medicine(mid, name, qty, price, expiry, minst)
        if ok:
            self.refresh()
            messagebox.showinfo("Success", msg, parent=self.winfo_toplevel())
        else:
            messagebox.showerror("Error", msg, parent=self.winfo_toplevel())

    def _do_delete(self):
        if not self._selected_id: return
        med = db.get_medicine_by_id(self._selected_id)
        if med and messagebox.askyesno("Delete",
            f"Delete '{med['name']}'? This cannot be undone.",
            parent=self.winfo_toplevel()):
            ok, msg = db.delete_medicine(self._selected_id)
            if ok:
                self.refresh()
                messagebox.showinfo("Deleted", msg, parent=self.winfo_toplevel())
            else:
                messagebox.showerror("Error", msg, parent=self.winfo_toplevel())

    def _alert_low(self):
        meds = db.get_low_stock_medicines()
        if not meds:
            messagebox.showinfo("Low Stock", "No medicines are low on stock.",
                                parent=self.winfo_toplevel()); return
        if not self._user_email:
            messagebox.showwarning("No Email", "No email configured.",
                                   parent=self.winfo_toplevel()); return
        smtp.send_low_stock_alert(self._user_email, meds,
            callback=lambda ok, m: self.after(0, lambda: messagebox.showinfo(
                "Alert", "Low stock alert sent!" if ok else f"Failed: {m}",
                parent=self.winfo_toplevel())))

    def _alert_expired(self):
        meds = db.get_expired_medicines()
        if not meds:
            messagebox.showinfo("Expiry", "No medicines have expired.",
                                parent=self.winfo_toplevel()); return
        if not self._user_email:
            messagebox.showwarning("No Email", "No email configured.",
                                   parent=self.winfo_toplevel()); return
        smtp.send_expired_medicine_alert(self._user_email, meds,
            callback=lambda ok, m: self.after(0, lambda: messagebox.showinfo(
                "Alert", "Expiry alert sent!" if ok else f"Failed: {m}",
                parent=self.winfo_toplevel())))


class MedicineDialog(tk.Toplevel):
    def __init__(self, parent, title, on_save, medicine=None):
        super().__init__(parent)
        self.title(f"PharmaCare – {title}")
        self.resizable(False, False)
        self.grab_set()
        self.configure(bg=st.COLORS["white"])
        self._on_save = on_save
        self._build_ui(title)
        self._center(440, 490)
        if medicine: self._populate(medicine)

    def _center(self, w, h):
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _field(self, parent, label):
        f = tk.Frame(parent, bg=st.COLORS["white"])
        f.pack(fill="x", padx=30, pady=(0,12))
        tk.Label(f, text=label, font=st.FONTS["body_bold"],
                 bg=st.COLORS["white"], fg=st.COLORS["text_medium"]).pack(anchor="w")
        var = tk.StringVar()
        tk.Entry(f, textvariable=var, **st.ENTRY).pack(fill="x", ipady=7, pady=(4,0))
        return var

    def _build_ui(self, title):
        hdr = tk.Frame(self, bg=st.COLORS["primary"])
        hdr.pack(fill="x")
        tk.Label(hdr, text=f"💊  {title}", font=st.FONTS["subheading"],
                 bg=st.COLORS["primary"], fg=st.COLORS["white"]).pack(pady=14)
        body = tk.Frame(self, bg=st.COLORS["white"])
        body.pack(fill="both", expand=True, pady=14)
        self._name  = self._field(body, "Medicine Name *")
        self._qty   = self._field(body, "Quantity *")
        self._price = self._field(body, "Unit Price (₹) *")
        self._exp   = self._field(body, "Expiry Date (YYYY-MM-DD) *")
        self._minst = self._field(body, "Minimum Stock Level *")
        self._msg   = tk.StringVar()
        tk.Label(body, textvariable=self._msg, font=st.FONTS["small"],
                 bg=st.COLORS["white"], fg=st.COLORS["danger"],
                 wraplength=380).pack(padx=30, pady=(0,6))
        br = tk.Frame(body, bg=st.COLORS["white"])
        br.pack(padx=30, fill="x")
        tk.Button(br, text="Cancel", command=self.destroy,
                  **st.BUTTON["secondary"]).pack(side="left")
        sb = tk.Button(br, text="Save", command=self._save,
                       **st.BUTTON["primary"])
        sb.pack(side="right")
        st.add_hover(sb, st.COLORS["primary"], st.COLORS["primary_dark"])

    def _populate(self, m):
        self._name.set(m["name"]); self._qty.set(str(m["quantity"]))
        self._price.set(str(m["price"])); self._exp.set(m["expiry_date"])
        self._minst.set(str(m["min_stock"]))

    def _save(self):
        try:
            name  = self._name.get().strip()
            qty   = int(self._qty.get().strip())
            price = float(self._price.get().strip())
            exp   = self._exp.get().strip()
            minst = int(self._minst.get().strip())
            if not name: raise ValueError("Name required")
            if qty < 0 or price < 0 or minst < 0: raise ValueError("Values must be ≥ 0")
            datetime.strptime(exp, "%Y-%m-%d")
        except ValueError as e:
            self._msg.set(str(e) if str(e) != "unconverted data remains" else
                          "Date must be YYYY-MM-DD"); return
        self._on_save(name, qty, price, exp, minst)
        self.destroy()