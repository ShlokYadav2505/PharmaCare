# users.py - Admin User Management (Edit / Delete users)
# UI style matches the rest of the app (simple Arial + #F0F0F0)
# Login identity is the email. There is no separate username.

import re
import tkinter as tk
from tkinter import ttk, messagebox
import database as db


class UsersFrame(tk.Frame):
    def __init__(self, parent, current_user_id=None):
        super().__init__(parent, bg="#F0F0F0")
        self._current_user_id = current_user_id
        self._selected_id = None
        self._build()
        self.refresh()

    def _build(self):
        top = tk.Frame(self, bg="#F0F0F0")
        top.pack(fill="x", padx=15, pady=10)
        tk.Label(top, text="User Management", font=("Arial", 16, "bold"),
                 bg="#F0F0F0").pack(side="left")
        tk.Label(top, text="(Admin only)", font=("Arial", 9),
                 bg="#F0F0F0", fg="gray").pack(side="left", padx=8)

        btns = tk.Frame(self, bg="#F0F0F0")
        btns.pack(fill="x", padx=15, pady=5)
        self._edit_btn = tk.Button(btns, text="Edit", command=self._open_edit,
                                   state="disabled")
        self._edit_btn.pack(side="left", padx=2)
        self._del_btn = tk.Button(btns, text="Delete", command=self._do_delete,
                                  state="disabled")
        self._del_btn.pack(side="left", padx=2)
        tk.Button(btns, text="Refresh", command=self.refresh).pack(side="right", padx=2)

        tf = tk.Frame(self)
        tf.pack(fill="both", expand=True, padx=15, pady=5)
        cols = ("id", "email", "role", "created")
        self._tree = ttk.Treeview(tf, columns=cols, show="headings",
                                  selectmode="browse")
        for col, hd, w in [("id", "ID", 50), ("email", "Email", 240),
                           ("role", "Role", 80), ("created", "Created", 140)]:
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

    def refresh(self):
        for r in self._tree.get_children():
            self._tree.delete(r)
        self._selected_id = None
        self._edit_btn.config(state="disabled")
        self._del_btn.config(state="disabled")
        rows = db.get_all_users()
        for u in rows:
            created = str(u.get("created_at", ""))[:19]
            self._tree.insert("", "end", iid=str(u["id"]), values=(
                u["id"], u["email"], u.get("role", "user"), created))
        self._status.config(text=f"{len(rows)} user(s)")

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

    def _open_edit(self):
        if not self._selected_id:
            messagebox.showwarning("Select", "Select a user first.",
                                   parent=self.winfo_toplevel())
            return
        user = db.get_user_by_id(self._selected_id)
        if not user:
            messagebox.showerror("Error", "User not found.",
                                 parent=self.winfo_toplevel())
            return
        UserDialog(self.winfo_toplevel(), "Edit User",
                   lambda email, role: self._handle_edit(
                       self._selected_id, email, role),
                   user=user)

    def _handle_edit(self, uid, email, role):
        ok, msg = db.update_user(uid, email, email, role)
        if ok:
            self.refresh()
            messagebox.showinfo("Success", msg, parent=self.winfo_toplevel())
        else:
            messagebox.showerror("Error", msg, parent=self.winfo_toplevel())

    def _do_delete(self):
        if not self._selected_id:
            messagebox.showwarning("Select", "Select a user first.",
                                   parent=self.winfo_toplevel())
            return
        if self._selected_id == self._current_user_id:
            messagebox.showerror(
                "Not Allowed",
                "You cannot delete your own account while logged in.",
                parent=self.winfo_toplevel())
            return
        user = db.get_user_by_id(self._selected_id)
        if not user:
            return
        if messagebox.askyesno(
                "Delete User",
                f"Delete user '{user['email']}'?\n"
                "This will also delete their medicines and transactions.\n"
                "This cannot be undone.",
                parent=self.winfo_toplevel()):
            ok, msg = db.delete_user(self._selected_id)
            if ok:
                self.refresh()
                messagebox.showinfo("Deleted", msg, parent=self.winfo_toplevel())
            else:
                messagebox.showerror("Error", msg, parent=self.winfo_toplevel())


class UserDialog(tk.Toplevel):
    def __init__(self, parent, title, on_save, user=None):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.grab_set()
        self._on_save = on_save
        self.geometry("360x240")
        self._build(title)
        if user:
            self._populate(user)

    def _build(self, title):
        tk.Label(self, text=title, font=("Arial", 13, "bold")).pack(pady=10)
        f = tk.Frame(self)
        f.pack(padx=25)

        tk.Label(f, text="Email *", font=("Arial", 10)).grid(row=0, column=0, sticky="w")
        self._email = tk.Entry(f, width=32)
        self._email.grid(row=1, column=0, pady=(0, 8))

        tk.Label(f, text="Role *", font=("Arial", 10)).grid(row=2, column=0, sticky="w")
        self._role = ttk.Combobox(f, values=["user", "admin"], state="readonly", width=30)
        self._role.set("user")
        self._role.grid(row=3, column=0, pady=(0, 8))

        self._msg = tk.Label(self, text="", fg="red", font=("Arial", 9), wraplength=300)
        self._msg.pack(pady=4)

        row = tk.Frame(self)
        row.pack(pady=8)
        tk.Button(row, text="Cancel", width=10, command=self.destroy).pack(side="left", padx=5)
        tk.Button(row, text="Save", width=10, command=self._save).pack(side="left", padx=5)

    def _populate(self, u):
        self._email.insert(0, u.get("email", ""))
        self._role.set(u.get("role", "user") or "user")

    def _save(self):
        self._msg.config(text="")
        email = self._email.get().strip().lower()
        role = self._role.get().strip().lower()

        if not email:
            self._msg.config(text="Email is required."); return
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            self._msg.config(text="Enter a valid email address."); return
        if len(email) > 100:
            self._msg.config(text="Email is too long."); return
        if role not in ("user", "admin"):
            self._msg.config(text="Role must be 'user' or 'admin'."); return

        self._on_save(email, role)
        self.destroy()
