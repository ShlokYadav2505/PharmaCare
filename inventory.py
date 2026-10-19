# inventory.py
# inventory add / edit / delete + google-like name search

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import database as db
import smtp_handler as smtp


class InventoryFrame(tk.Frame):
    def __init__(self, parent, user_id=None, user_email=""):
        super().__init__(parent, bg="#F0F0F0")
        self._user_id = user_id
        self._user_email = user_email
        self._selected_id = None
        self._build()
        self.refresh()

    def _build(self):
        top = tk.Frame(self, bg="#F0F0F0")
        top.pack(fill="x", padx=15, pady=10)
        tk.Label(top, text="Inventory", font=("Arial", 16, "bold"),
                 bg="#F0F0F0").pack(side="left")
        self._search = tk.Entry(top, width=25)
        self._search.pack(side="right")
        self._search.bind("<KeyRelease>", lambda e: self._do_search())

        btns = tk.Frame(self, bg="#F0F0F0")
        btns.pack(fill="x", padx=15, pady=5)
        tk.Button(btns, text="Add", command=self._open_add).pack(side="left", padx=2)
        self._edit_btn = tk.Button(btns, text="Edit", command=self._open_edit, state="disabled")
        self._edit_btn.pack(side="left", padx=2)
        self._del_btn = tk.Button(btns, text="Delete", command=self._do_delete, state="disabled")
        self._del_btn.pack(side="left", padx=2)
        tk.Button(btns, text="Low Stock Alert", command=self._alert_low).pack(side="right", padx=2)
        tk.Button(btns, text="Expiry Alert", command=self._alert_expired).pack(side="right", padx=2)

        tf = tk.Frame(self)
        tf.pack(fill="both", expand=True, padx=15, pady=5)
        cols = ("sno", "name", "qty", "price", "expiry", "min_stock", "status")
        self._tree = ttk.Treeview(tf, columns=cols, show="headings", selectmode="browse")
        for col, hd, w in [("sno", "S.No.", 50), ("name", "Medicine", 160),
                           ("qty", "Qty", 60), ("price", "Price", 80),
                           ("expiry", "Expiry", 100), ("min_stock", "Min", 50),
                           ("status", "Status", 90)]:
            self._tree.heading(col, text=hd)
            self._tree.column(col, width=w)
        sb = ttk.Scrollbar(tf, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        self._tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self._tree.bind("<<TreeviewSelect>>", self._on_select)
        self._tree.bind("<Double-1>", lambda e: self._open_edit())

        self._status = tk.Label(self, text="Ready", font=("Arial", 9), bg="#F0F0F0")
        self._status.pack(anchor="w", padx=15, pady=5)

    def refresh(self, data=None):
        for r in self._tree.get_children():
            self._tree.delete(r)
        self._selected_id = None
        self._edit_btn.config(state="disabled")
        self._del_btn.config(state="disabled")
        today = datetime.now().strftime("%Y-%m-%d")
        rows = data if data is not None else db.get_all_medicines(self._user_id)
        sno = 1
        for med in rows:
            qty = med["quantity"]
            minst = med["min_stock"]
            exp = str(med["expiry_date"])
            if exp <= today:
                status = "Expired"
            elif qty <= minst:
                status = "Low Stock"
            else:
                status = "In Stock"
            # show S.No. 1,2,3... keep real db id in iid for edit/delete
            self._tree.insert("", "end", iid=str(med["id"]), values=(
                sno, med["name"], qty, "₹{:.2f}".format(med["price"]),
                exp, minst, status))
            sno = sno + 1
        self._status.config(text=str(len(rows)) + " medicine(s)")

    def _do_search(self):
        q = self._search.get().strip()
        if not q:
            self.refresh()
        else:
            self.refresh(db.search_medicines(self._user_id, q))

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

    def _auto_alert_if_needed(self):
        # email if low stock or expired after change
        if not self._user_email:
            return
        ls = db.get_low_stock_medicines(self._user_id)
        if ls:
            db.enqueue_alert("low_stock", self._user_email, ls)
            smtp.send_low_stock_alert(self._user_email, ls)
        ex = db.get_expired_medicines(self._user_id)
        if ex:
            db.enqueue_alert("expired", self._user_email, ex)
            smtp.send_expired_medicine_alert(self._user_email, ex)

    def _open_add(self):
        MedicineDialog(self.winfo_toplevel(), "Add Medicine", self._handle_add)

    def _handle_add(self, name, qty, price, expiry, minst):
        ok, msg = db.add_medicine(self._user_id, name, qty, price, expiry, minst)
        if ok:
            self.refresh()
            self._auto_alert_if_needed()
            messagebox.showinfo("Success", msg, parent=self.winfo_toplevel())
        else:
            messagebox.showerror("Error", msg, parent=self.winfo_toplevel())

    def _open_edit(self):
        if not self._selected_id:
            messagebox.showwarning("Select", "Select a medicine first.",
                                   parent=self.winfo_toplevel())
            return
        med = db.get_medicine_by_id(self._selected_id, self._user_id)
        if not med:
            messagebox.showerror("Error", "Medicine not found.",
                                 parent=self.winfo_toplevel())
            return
        mid = self._selected_id
        MedicineDialog(
            self.winfo_toplevel(),
            "Edit Medicine",
            lambda name, qty, price, expiry, minst: self._handle_edit(
                mid, name, qty, price, expiry, minst),
            medicine=med,
        )

    def _handle_edit(self, mid, name, qty, price, expiry, minst):
        ok, msg = db.update_medicine(self._user_id, mid, name, qty, price, expiry, minst)
        if ok:
            self.refresh()
            self._auto_alert_if_needed()
            messagebox.showinfo("Success", msg, parent=self.winfo_toplevel())
        else:
            messagebox.showerror("Error", msg, parent=self.winfo_toplevel())

    def _do_delete(self):
        if not self._selected_id:
            messagebox.showwarning("Select", "Select a medicine first.",
                                   parent=self.winfo_toplevel())
            return
        med = db.get_medicine_by_id(self._selected_id, self._user_id)
        if not med:
            return
        if messagebox.askyesno(
                "Delete",
                "Delete '" + med["name"] + "'?\nThis cannot be undone.",
                parent=self.winfo_toplevel()):
            ok, msg = db.delete_medicine(self._user_id, self._selected_id)
            if ok:
                self.refresh()
                messagebox.showinfo("Deleted", msg, parent=self.winfo_toplevel())
            else:
                messagebox.showerror("Error", msg, parent=self.winfo_toplevel())

    def _alert_low(self):
        meds = db.get_low_stock_medicines(self._user_id)
        if not meds:
            messagebox.showinfo("Low Stock", "No medicines are low on stock.",
                                parent=self.winfo_toplevel())
            return
        if not self._user_email:
            messagebox.showwarning("No Email", "No email configured for alerts.",
                                   parent=self.winfo_toplevel())
            return
        smtp.send_low_stock_alert(
            self._user_email, meds,
            callback=lambda ok, m: self.after(
                0,
                lambda: messagebox.showinfo(
                    "Alert",
                    "Low stock alert sent!" if ok else "Failed: " + str(m),
                    parent=self.winfo_toplevel(),
                ),
            ),
        )

    def _alert_expired(self):
        meds = db.get_expired_medicines(self._user_id)
        if not meds:
            messagebox.showinfo("Expiry", "No expired medicines.",
                                parent=self.winfo_toplevel())
            return
        if not self._user_email:
            messagebox.showwarning("No Email", "No email configured for alerts.",
                                   parent=self.winfo_toplevel())
            return
        smtp.send_expired_medicine_alert(
            self._user_email, meds,
            callback=lambda ok, m: self.after(
                0,
                lambda: messagebox.showinfo(
                    "Alert",
                    "Expiry alert sent!" if ok else "Failed: " + str(m),
                    parent=self.winfo_toplevel(),
                ),
            ),
        )


class MedicineDialog(tk.Toplevel):
    def __init__(self, parent, title, on_save, medicine=None):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.grab_set()
        self.on_save = on_save
        self.saved = False
        self.geometry("400x560")
        # load medicine names from catalog table
        catalog = db.get_medicine_catalog()
        self.catalog_names = []
        if catalog:
            for r in catalog:
                self.catalog_names.append(r["name"])
        self.build(title)
        if medicine:
            self.populate(medicine)

    def build(self, title):
        tk.Label(self, text=title, font=("Arial", 13, "bold")).pack(pady=10)

        f = tk.Frame(self)
        f.pack(padx=25, fill="x")

        # medicine name
        tk.Label(f, text="Medicine Name * (type to search)",
                 font=("Arial", 10)).pack(anchor="w")
        self.name_entry = tk.Entry(f, width=34)
        self.name_entry.pack(pady=(0, 2), fill="x")
        self.name_entry.bind("<KeyRelease>", self.show_suggestions)
        self.name_entry.bind("<Down>", self.focus_list)
        self.name_entry.bind("<Escape>", self.hide_suggestions)

        # suggestion list (shown under name when typing)
        self.list_frame = tk.Frame(f)
        self.suggest_list = tk.Listbox(self.list_frame, height=4, width=34,
                                       font=("Arial", 10), activestyle="dotbox")
        self.suggest_list.pack(side="left", fill="x", expand=True)
        sb = tk.Scrollbar(self.list_frame, orient="vertical",
                          command=self.suggest_list.yview)
        sb.pack(side="right", fill="y")
        self.suggest_list.config(yscrollcommand=sb.set)
        self.suggest_list.bind("<<ListboxSelect>>", self.pick_suggestion)
        self.suggest_list.bind("<Return>", self.pick_suggestion)

        # quantity
        tk.Label(f, text="Quantity * (whole number)",
                 font=("Arial", 10)).pack(anchor="w", pady=(8, 0))
        self.qty_entry = tk.Entry(f, width=34)
        self.qty_entry.pack(pady=(0, 4), fill="x")

        # price
        tk.Label(f, text="Unit Price (₹) *",
                 font=("Arial", 10)).pack(anchor="w")
        self.price_entry = tk.Entry(f, width=34)
        self.price_entry.pack(pady=(0, 4), fill="x")

        # expiry
        tk.Label(f, text="Expiry Date (YYYY-MM-DD) *",
                 font=("Arial", 10)).pack(anchor="w")
        self.exp_entry = tk.Entry(f, width=34)
        self.exp_entry.pack(pady=(0, 4), fill="x")

        # minimum stock
        tk.Label(f, text="Minimum Stock * (whole number)",
                 font=("Arial", 10)).pack(anchor="w")
        self.min_entry = tk.Entry(f, width=34)
        self.min_entry.pack(pady=(0, 4), fill="x")

        self.msg = tk.Label(self, text="", fg="red", font=("Arial", 9), wraplength=340)
        self.msg.pack(pady=4)

        row = tk.Frame(self)
        row.pack(pady=8)
        tk.Button(row, text="Cancel", width=10, command=self.destroy).pack(side="left", padx=5)
        self.save_btn = tk.Button(row, text="Save", width=10, command=self.save)
        self.save_btn.pack(side="left", padx=5)

    def show_suggestions(self, event=None):
        # show matching names while typing
        typed = self.name_entry.get().strip().lower()
        self.suggest_list.delete(0, tk.END)
        if typed == "":
            self.list_frame.pack_forget()
            return
        matches = []
        for name in self.catalog_names:
            if typed in name.lower():
                matches.append(name)
        if len(matches) == 0:
            self.list_frame.pack_forget()
            return
        for name in matches[:15]:
            self.suggest_list.insert(tk.END, name)
        self.list_frame.pack(fill="x", after=self.name_entry)

    def hide_suggestions(self, event=None):
        self.list_frame.pack_forget()

    def focus_list(self, event=None):
        if self.suggest_list.size() > 0:
            self.suggest_list.focus_set()
            self.suggest_list.selection_set(0)
        return "break"

    def pick_suggestion(self, event=None):
        sel = self.suggest_list.curselection()
        if not sel:
            return
        name = self.suggest_list.get(sel[0])
        self.name_entry.delete(0, tk.END)
        self.name_entry.insert(0, name)
        self.list_frame.pack_forget()
        self.name_entry.focus_set()

    def populate(self, m):
        self.name_entry.insert(0, m["name"])
        self.qty_entry.insert(0, str(m["quantity"]))
        self.price_entry.insert(0, str(m["price"]))
        self.exp_entry.insert(0, str(m["expiry_date"]))
        self.min_entry.insert(0, str(m["min_stock"]))

    def save(self):
        if self.saved:
            return

        self.msg.config(text="")
        name = self.name_entry.get().strip()
        qty_s = self.qty_entry.get().strip()
        price_s = self.price_entry.get().strip()
        exp = self.exp_entry.get().strip()
        minst_s = self.min_entry.get().strip()

        if name == "":
            self.msg.config(text="Medicine name is required.")
            return
        if len(name) < 2:
            self.msg.config(text="Medicine name must be at least 2 characters.")
            return
        if qty_s == "":
            self.msg.config(text="Quantity is required.")
            return
        if price_s == "":
            self.msg.config(text="Price is required.")
            return
        if exp == "":
            self.msg.config(text="Expiry date is required.")
            return
        if minst_s == "":
            self.msg.config(text="Minimum stock is required.")
            return

        try:
            qty = int(qty_s)
        except ValueError:
            self.msg.config(text="Quantity must be a whole number (e.g. 50).")
            return
        if qty <= 0:
            self.msg.config(text="Quantity must be greater than 0.")
            return
        if qty > 1000000:
            self.msg.config(text="Quantity is too large.")
            return

        try:
            price = float(price_s)
        except ValueError:
            self.msg.config(text="Price must be a number (e.g. 25.50).")
            return
        if price <= 0:
            self.msg.config(text="Price must be greater than 0.")
            return
        if price > 1000000:
            self.msg.config(text="Price is too large.")
            return

        try:
            exp_date = datetime.strptime(exp, "%Y-%m-%d")
        except ValueError:
            self.msg.config(text="Expiry date must be YYYY-MM-DD (e.g. 2027-06-30).")
            return

        if exp_date.date() < datetime.now().date():
            self.msg.config(text="Expiry date cannot be in the past.")
            return

        try:
            minst = int(minst_s)
        except ValueError:
            self.msg.config(text="Minimum stock must be a whole number.")
            return
        if minst <= 0:
            self.msg.config(text="Minimum stock must be greater than 0.")
            return

        self.saved = True
        self.save_btn.config(state="disabled")
        self.on_save(name, qty, price, exp, minst)
        self.destroy()
