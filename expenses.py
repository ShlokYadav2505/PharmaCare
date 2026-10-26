# expenses.py - Operating expenses for financial reports

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import database as db
import styles as st


class ExpensesFrame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=st.COLORS["background"])
        self._selected_id = None
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        top = tk.Frame(self, bg=st.COLORS["background"])
        top.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 8))
        tk.Label(
            top, text="Operating Expenses", font=st.FONTS["heading"],
            bg=st.COLORS["background"], fg=st.COLORS["text_dark"]
        ).pack(side="left")

        bb = tk.Frame(self, bg=st.COLORS["background"])
        bb.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 8))

        add = tk.Button(
            bb, text="+ Add Expense", command=self._open_add, **st.BUTTON["primary"]
        )
        add.pack(side="left", padx=(0, 8))
        st.add_hover(add, st.COLORS["primary"], st.COLORS["primary_dark"])

        self._del_btn = tk.Button(
            bb, text="🗑 Delete", command=self._do_delete,
            state="disabled", **st.BUTTON["danger"]
        )
        self._del_btn.pack(side="left")
        st.add_hover(self._del_btn, st.COLORS["danger"], "#B71C1C")

        tf = tk.Frame(self, bg=st.COLORS["white"])
        tf.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 8))
        tf.columnconfigure(0, weight=1)
        tf.rowconfigure(0, weight=1)

        sty = ttk.Style()
        st.apply_treeview_style(sty, "Exp.Treeview")
        cols = ("id", "date", "category", "description", "amount")
        self._tree = ttk.Treeview(
            tf, columns=cols, show="headings",
            style="Exp.Treeview", selectmode="browse"
        )
        for col, hd, w in [
            ("id", "ID", 50), ("date", "Date", 110),
            ("category", "Category", 140), ("description", "Description", 240),
            ("amount", "Amount (₹)", 110)
        ]:
            self._tree.heading(col, text=hd)
            self._tree.column(col, width=w, anchor="center")
        self._tree.column("description", anchor="w")
        self._tree.column("category", anchor="w")
        vsb = ttk.Scrollbar(tf, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        self._tree.bind("<<TreeviewSelect>>", self._on_select)

        self._status = tk.StringVar(value="Ready")
        tk.Label(
            self, textvariable=self._status, font=st.FONTS["small"],
            bg=st.COLORS["background"], fg=st.COLORS["text_light"],
            anchor="w"
        ).grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 8))

    def refresh(self):
        for r in self._tree.get_children():
            self._tree.delete(r)
        self._selected_id = None
        self._del_btn.config(state="disabled")
        rows = db.get_all_expenses()
        total = 0.0
        for e in rows:
            self._tree.insert(
                "", "end", iid=str(e["id"]),
                values=(
                    e["id"], e["expense_date"], e["category"],
                    e["description"] or "", f"₹{e['amount']:.2f}"
                )
            )
            total += float(e["amount"])
        self._status.set(f"{len(rows)} expense(s)  |  Total: ₹{total:.2f}")

    def _on_select(self, _=None):
        sel = self._tree.selection()
        if sel:
            self._selected_id = int(sel[0])
            self._del_btn.config(state="normal")
        else:
            self._selected_id = None
            self._del_btn.config(state="disabled")

    def _open_add(self):
        ExpenseDialog(self.winfo_toplevel(), self._handle_add)

    def _handle_add(self, category, description, amount, date):
        ok, msg = db.add_expense(category, description, amount, date)
        if ok:
            self.refresh()
            messagebox.showinfo("Success", msg, parent=self.winfo_toplevel())
            return True
        else:
            messagebox.showerror("Error", msg, parent=self.winfo_toplevel())
            return False

    def _do_delete(self):
        if not self._selected_id:
            return
        if messagebox.askyesno(
            "Delete", "Delete this expense record?",
            parent=self.winfo_toplevel()
        ):
            ok, msg = db.delete_expense(self._selected_id)
            if ok:
                self.refresh()
            else:
                messagebox.showerror("Error", msg, parent=self.winfo_toplevel())


class ExpenseDialog(tk.Toplevel):
    def __init__(self, parent, on_save):
        super().__init__(parent)
        self.title("PharmaCare – Add Expense")
        self.resizable(False, False)
        self.grab_set()
        self.configure(bg=st.COLORS["white"])
        self._on_save = on_save
        self._build_ui()
        self._center(420, 470)

    def _center(self, w, h):
        self.update_idletasks()
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _field(self, parent, label):
        f = tk.Frame(parent, bg=st.COLORS["white"])
        f.pack(fill="x", padx=28, pady=(0, 10))
        tk.Label(
            f, text=label, font=st.FONTS["body_bold"],
            bg=st.COLORS["white"], fg=st.COLORS["text_medium"]
        ).pack(anchor="w")
        var = tk.StringVar()
        tk.Entry(f, textvariable=var, **st.ENTRY).pack(fill="x", ipady=7, pady=(4, 0))
        return var

    def _build_ui(self):
        hdr = tk.Frame(self, bg=st.COLORS["primary"])
        hdr.pack(fill="x")
        tk.Label(
            hdr, text="💸  Add Operating Expense", font=st.FONTS["subheading"],
            bg=st.COLORS["primary"], fg=st.COLORS["white"]
        ).pack(pady=14)
        body = tk.Frame(self, bg=st.COLORS["white"])
        body.pack(fill="both", expand=True, pady=12)
        self._cat = self._field(body, "Category * (e.g. Rent, Electricity)")
        self._desc = self._field(body, "Description")
        self._amt = self._field(body, "Amount (₹) *")
        self._date = self._field(body, "Date (YYYY-MM-DD) *")
        self._date.set(datetime.now().strftime("%Y-%m-%d"))
        self._msg = tk.StringVar()
        tk.Label(
            body, textvariable=self._msg, font=st.FONTS["small"],
            bg=st.COLORS["white"], fg=st.COLORS["danger"]
        ).pack(padx=28)
        br = tk.Frame(body, bg=st.COLORS["white"])
        br.pack(padx=28, fill="x", pady=8)
        tk.Button(
            br, text="Cancel", command=self.destroy, **st.BUTTON["secondary"]
        ).pack(side="left")
        sb = tk.Button(br, text="Add Expense", command=self._save,
                       **st.BUTTON["primary"])
        sb.pack(side="right")
        st.add_hover(sb, st.COLORS["primary"], st.COLORS["primary_dark"])

    def _save(self):
        try:
            cat = self._cat.get().strip()
            if not cat:
                raise ValueError("Category is required.")
            amt = float(self._amt.get().strip())
            if amt <= 0:
                raise ValueError("Amount must be > 0.")
            d = self._date.get().strip()
            datetime.strptime(d, "%Y-%m-%d")
        except ValueError as e:
            self._msg.set(str(e))
            return
        if self._on_save(cat, self._desc.get().strip(), amt, d):
            self.destroy()
