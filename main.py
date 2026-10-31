import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tkinter as tk
from tkinter import messagebox
import database as db
import vendor_system as vendor_db
from login import LoginFrame


class PharmaCareApp:
    def __init__(self):
        self._root = tk.Tk()
        self._root.title("PharmaCare – Pharmacy Management System")
        self._root.configure(bg="#1B5E20")
        self._root.resizable(False, False)
        db.initialize_database()
        # Additive migration: preserves existing users, medicines, batches and sales.
        vendor_db.initialize_vendor_system()
        self._frame = None
        self._center(900, 580)
        self._show_login()

    def _center(self, w, h):
        self._root.update_idletasks()
        sw = self._root.winfo_screenwidth()
        sh = self._root.winfo_screenheight()
        self._root.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    def _clear(self):
        if self._frame:
            self._frame.destroy()
            self._frame = None

    def _show_login(self):
        self._clear()
        self._root.resizable(False, False)
        self._center(900, 580)
        self._frame = LoginFrame(self._root, on_success_callback=self._show_dashboard)
        self._frame.place(x=0, y=0, relwidth=1, relheight=1)

    def _show_dashboard(self, username):
        self._clear()
        self._root.resizable(True, True)
        self._center(1300, 780)
        role = vendor_db.get_user_role(username)
        if role == "vendor":
            from vendor_portal import VendorPortalFrame
            self._frame = VendorPortalFrame(self._root, username, self._show_login)
        elif role in ("pharmacist", "user", "admin"):
            from dashboard import DashboardApp
            self._frame = DashboardApp(self._root, username, on_logout_callback=self._show_login)
        else:
            self._root.resizable(False, False)
            self._center(900, 580)
            messagebox.showerror("Account unavailable", "This account does not have an active application role.",
                                 parent=self._root)
            self._show_login()
            return
        self._frame.place(x=0, y=0, relwidth=1, relheight=1)

    def run(self):
        self._root.mainloop()

if __name__ == "__main__":
    PharmaCareApp().run()
