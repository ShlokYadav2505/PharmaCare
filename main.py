# main.py
# starting point of the application

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tkinter as tk
import database as db
from login import LoginFrame


class PharmaCareApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("PharmaCare - Pharmacy Management System")
        self.root.configure(bg="#F0F0F0")
        db.initialize_database()
        self.frame = None
        self.show_login()

    def center(self, w, h):
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(str(w) + "x" + str(h) + "+" + str(x) + "+" + str(y))

    def clear(self):
        if self.frame:
            self.frame.destroy()
            self.frame = None

    def show_login(self):
        self.clear()
        self.center(420, 340)
        self.root.resizable(False, False)
        self.frame = LoginFrame(self.root, on_success_callback=self.show_dashboard)
        self.frame.pack(fill="both", expand=True)

    def show_dashboard(self, email, user_id):
        from dashboard import DashboardApp
        self.clear()
        self.root.resizable(True, True)
        self.center(1000, 650)
        self.frame = DashboardApp(self.root, email, user_id, on_logout_callback=self.show_login)
        self.frame.pack(fill="both", expand=True)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = PharmaCareApp()
    app.run()
