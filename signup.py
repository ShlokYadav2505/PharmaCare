# signup.py
# create account with email + OTP
# no username and no random code
# after success -> go straight to dashboard

import re
import tkinter as tk
from tkinter import messagebox
import database as db
import smtp_handler as smtp


class SignupWindow(tk.Toplevel):
    def __init__(self, parent, on_success=None):
        super().__init__(parent)
        self.title("Create Account")
        self.resizable(False, False)
        self.grab_set()
        self.on_success = on_success
        self.otp_sent = False
        self.build()
        self.geometry("420x420")

    def build(self):
        tk.Label(self, text="Create Account", font=("Arial", 14, "bold")).pack(pady=12)

        f = tk.Frame(self)
        f.pack(padx=30)

        tk.Label(f, text="Email *", font=("Arial", 10)).grid(row=0, column=0, sticky="w")
        self.email = tk.Entry(f, width=36)
        self.email.grid(row=1, column=0, pady=(0, 8))

        tk.Label(f, text="Password * (min 6 characters)", font=("Arial", 10)).grid(
            row=2, column=0, sticky="w")
        self.password = tk.Entry(f, width=36, show="*")
        self.password.grid(row=3, column=0, pady=(0, 8))

        tk.Label(f, text="Confirm Password *", font=("Arial", 10)).grid(
            row=4, column=0, sticky="w")
        self.cpassword = tk.Entry(f, width=36, show="*")
        self.cpassword.grid(row=5, column=0, pady=(0, 8))

        tk.Label(f, text="OTP (6 digits from email)", font=("Arial", 10)).grid(
            row=6, column=0, sticky="w")
        otp_row = tk.Frame(f)
        otp_row.grid(row=7, column=0, sticky="ew", pady=(0, 8))
        self.otp = tk.Entry(otp_row, width=18)
        self.otp.pack(side="left")
        self.send_btn = tk.Button(otp_row, text="Send OTP", command=self.send_otp)
        self.send_btn.pack(side="left", padx=6)

        self.msg = tk.Label(self, text="", fg="red", font=("Arial", 9), wraplength=360)
        self.msg.pack(pady=4)

        tk.Button(self, text="Verify OTP & Create Account",
                  command=self.do_register, width=32).pack(pady=6)
        tk.Button(self, text="Back", command=self.destroy).pack()

    def validate_form(self):
        em = self.email.get().strip()
        pw = self.password.get()
        cp = self.cpassword.get()

        if em == "":
            self.msg.config(text="Email is required.", fg="red")
            return False
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", em):
            self.msg.config(text="Enter a valid email (e.g. name@gmail.com).", fg="red")
            return False
        if len(em) > 100:
            self.msg.config(text="Email is too long.", fg="red")
            return False
        if pw == "":
            self.msg.config(text="Password is required.", fg="red")
            return False
        if len(pw) < 6:
            self.msg.config(text="Password must be at least 6 characters.", fg="red")
            return False
        if pw != cp:
            self.msg.config(text="Passwords do not match.", fg="red")
            return False
        if db.get_user_by_email(em):
            self.msg.config(text="Email already registered.", fg="red")
            return False
        return True

    def send_otp(self):
        if not self.validate_form():
            return
        email = self.email.get().strip()
        self.msg.config(text="Sending OTP…", fg="blue")
        self.send_btn.config(state="disabled")

        def after(ok, msg):
            self.after(0, lambda: self.after_send(ok, msg))
        smtp.send_otp_email(email, purpose="account verification", callback=after)

    def after_send(self, ok, msg):
        self.send_btn.config(state="normal", text="Resend OTP")
        if ok:
            self.otp_sent = True
            self.msg.config(text="OTP sent. Check your email (and Spam).", fg="green")
        else:
            self.msg.config(text="Failed to send OTP: " + str(msg), fg="red")

    def do_register(self):
        if not self.otp_sent:
            self.msg.config(text="Please send OTP to your email first.", fg="red")
            return
        otp = self.otp.get().strip()
        if otp == "":
            self.msg.config(text="Enter the OTP from your email.", fg="red")
            return
        if not otp.isdigit() or len(otp) != 6:
            self.msg.config(text="OTP must be a 6-digit number.", fg="red")
            return
        email = self.email.get().strip().lower()
        ok, msg = smtp.verify_otp(email, otp)
        if not ok:
            self.msg.config(text=msg, fg="red")
            return

        # username column stores the email so there is no extra login name
        ok2, msg2 = db.create_user(email, email, self.password.get())
        if not ok2:
            self.msg.config(text=msg2, fg="red")
            return

        user = db.get_user_by_email(email)
        if not user:
            self.msg.config(text="Account created but login failed. Please log in.", fg="red")
            return

        user_id = int(user["id"])
        smtp.send_welcome_email(email, email)

        messagebox.showinfo(
            "Welcome",
            "Account created.\n\nLog in next time with this email.\n\nOpening dashboard…",
            parent=self)

        callback = self.on_success
        self.destroy()
        if callback:
            callback(email, user_id)
