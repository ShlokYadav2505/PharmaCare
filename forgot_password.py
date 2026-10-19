# forgot_password.py - basic reset with OTP

import tkinter as tk
from tkinter import messagebox
import database as db
import smtp_handler as smtp


class ForgotPasswordWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Reset Password")
        self.resizable(False, False)
        self.grab_set()
        self._email = ""
        self._step = 1
        self.geometry("360x300")
        self._build()
        self._show_step1()

    def _build(self):
        self._title = tk.Label(self, text="Reset Password", font=("Arial", 14, "bold"))
        self._title.pack(pady=12)
        self._body = tk.Frame(self)
        self._body.pack(padx=25, fill="x")
        self._msg = tk.Label(self, text="", fg="red", font=("Arial", 9))
        self._msg.pack(pady=5)
        tk.Button(self, text="Cancel", command=self.destroy).pack(pady=5)

    def _clear_body(self):
        for w in self._body.winfo_children():
            w.destroy()

    def _show_step1(self):
        self._clear_body()
        self._step = 1
        tk.Label(self._body, text="Registered Email", font=("Arial", 10)).pack(anchor="w")
        self._email_ent = tk.Entry(self._body, width=35)
        self._email_ent.pack(pady=5)
        tk.Button(self._body, text="Send OTP", command=self._send_otp).pack(pady=5)

    def _show_step2(self):
        self._clear_body()
        self._step = 2
        tk.Label(self._body, text="Enter OTP", font=("Arial", 10)).pack(anchor="w")
        self._otp_ent = tk.Entry(self._body, width=20)
        self._otp_ent.pack(pady=5)
        row = tk.Frame(self._body)
        row.pack()
        tk.Button(row, text="Resend", command=self._send_otp).pack(side="left", padx=4)
        tk.Button(row, text="Verify", command=self._verify).pack(side="left", padx=4)

    def _show_step3(self):
        self._clear_body()
        self._step = 3
        tk.Label(self._body, text="New Password", font=("Arial", 10)).pack(anchor="w")
        self._np = tk.Entry(self._body, width=30, show="*")
        self._np.pack(pady=3)
        tk.Label(self._body, text="Confirm Password", font=("Arial", 10)).pack(anchor="w")
        self._cnp = tk.Entry(self._body, width=30, show="*")
        self._cnp.pack(pady=3)
        tk.Button(self._body, text="Reset Password", command=self._reset).pack(pady=8)

    def _send_otp(self):
        if self._step == 1:
            email = self._email_ent.get().strip().lower()
        else:
            email = self._email
        if not email:
            self._msg.config(text="Please enter your registered email.", fg="red"); return
        if "@" not in email or "." not in email.split("@")[-1]:
            self._msg.config(text="Enter a valid email address.", fg="red"); return
        if not db.get_user_by_email(email):
            self._msg.config(text="No account found with that email.", fg="red"); return
        self._email = email
        self._msg.config(text="Sending...", fg="blue")

        def after(ok, msg):
            self.after(0, lambda: self._after_send(ok, msg))
        smtp.send_otp_email(email, purpose="password reset", callback=after)

    def _after_send(self, ok, msg):
        if ok:
            self._msg.config(text="OTP sent.", fg="green")
            self._show_step2()
        else:
            self._msg.config(text=f"Failed: {msg}", fg="red")

    def _verify(self):
        otp = self._otp_ent.get().strip()
        if not otp:
            self._msg.config(text="Please enter the OTP.", fg="red"); return
        if not otp.isdigit() or len(otp) != 6:
            self._msg.config(text="OTP must be a 6-digit number.", fg="red"); return
        ok, msg = smtp.verify_otp(self._email, otp)
        if ok:
            self._msg.config(text="Verified.", fg="green")
            self._show_step3()
        else:
            self._msg.config(text=msg, fg="red")

    def _reset(self):
        np = self._np.get()
        cnp = self._cnp.get()
        if not np:
            self._msg.config(text="Enter a new password.", fg="red"); return
        if len(np) < 6:
            self._msg.config(text="Password must be at least 6 characters.", fg="red"); return
        if np != cnp:
            self._msg.config(text="Passwords do not match.", fg="red"); return
        ok, msg = db.update_password(self._email, np)
        if ok:
            messagebox.showinfo("Done", "Password reset. You can log in.", parent=self)
            self.destroy()
        else:
            self._msg.config(text=msg, fg="red")
