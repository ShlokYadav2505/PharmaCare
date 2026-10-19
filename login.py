# login.py
# same simple screen as before, but login is by email

import tkinter as tk
import database as db


class LoginFrame(tk.Frame):
    def __init__(self, parent, on_success_callback):
        super().__init__(parent, bg="#F0F0F0")
        self.on_success = on_success_callback
        self.build()

    def build(self):
        tk.Label(self, text="PharmaCare Login", font=("Arial", 18, "bold"),
                 bg="#F0F0F0").pack(pady=30)

        form = tk.Frame(self, bg="#F0F0F0")
        form.pack()

        tk.Label(form, text="Email", font=("Arial", 11), bg="#F0F0F0").grid(
            row=0, column=0, sticky="w", pady=5)
        self.email_entry = tk.Entry(form, width=30, font=("Arial", 11))
        self.email_entry.grid(row=0, column=1, pady=5, padx=10)

        tk.Label(form, text="Password", font=("Arial", 11), bg="#F0F0F0").grid(
            row=1, column=0, sticky="w", pady=5)
        self.pass_entry = tk.Entry(form, width=30, show="*", font=("Arial", 11))
        self.pass_entry.grid(row=1, column=1, pady=5, padx=10)

        self.msg = tk.Label(self, text="", fg="red", bg="#F0F0F0", font=("Arial", 10))
        self.msg.pack(pady=5)

        tk.Button(self, text="Login", width=15, command=self.do_login,
                  font=("Arial", 11)).pack(pady=5)
        tk.Button(self, text="Create Account", width=15, command=self.open_signup,
                  font=("Arial", 10)).pack(pady=2)
        tk.Button(self, text="Forgot Password", width=15, command=self.open_forgot,
                  font=("Arial", 10)).pack(pady=2)

        self.email_entry.focus()
        self.pass_entry.bind("<Return>", lambda e: self.do_login())

    def do_login(self):
        self.msg.config(text="")
        email = self.email_entry.get().strip()
        password = self.pass_entry.get()

        if email == "":
            self.msg.config(text="Please enter your email.")
            return
        if "@" not in email or "." not in email.split("@")[-1]:
            self.msg.config(text="Enter a valid email address.")
            return
        if password == "":
            self.msg.config(text="Please enter your password.")
            return

        ok, msg, email, user_id = db.validate_login(email, password)
        if ok:
            self.on_success(email, user_id)
        else:
            self.msg.config(text=msg)

    def open_signup(self):
        from signup import SignupWindow
        SignupWindow(self.winfo_toplevel(), on_success=self.on_success)

    def open_forgot(self):
        from forgot_password import ForgotPasswordWindow
        ForgotPasswordWindow(self.winfo_toplevel())
