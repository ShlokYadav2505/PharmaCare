# signup.py - Simple create account window

import re
import tkinter as tk
from tkinter import messagebox
import database as db
import smtp_handler as smtp
import styles as st


class SignupWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("PharmaCare - Create Account")
        self.resizable(False, False)
        self.grab_set()
        self.configure(bg=st.COLORS["white"])
        self._otp_sent = False
        self._build_ui()
        self._center(420, 520)

    def _center(self, w, h):
        self.update_idletasks()
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _field(self, parent, label, show=""):
        f = tk.Frame(parent, bg=st.COLORS["white"])
        f.pack(fill="x", padx=30, pady=(0, 8))
        tk.Label(
            f, text=label, font=st.FONTS["body_bold"],
            bg=st.COLORS["white"], fg=st.COLORS["text_dark"]
        ).pack(anchor="w")
        var = tk.StringVar()
        e = tk.Entry(f, textvariable=var, show=show, **st.ENTRY)
        e.pack(fill="x", ipady=5, pady=(2, 0))
        return var

    def _build_ui(self):
        tk.Label(
            self, text="Create Account", font=st.FONTS["heading"],
            bg=st.COLORS["white"], fg=st.COLORS["primary"]
        ).pack(pady=(18, 12))

        self._uname = self._field(self, "Username")
        self._email = self._field(self, "Email Address")
        self._pass = self._field(self, "Password", show="*")
        self._cpass = self._field(self, "Confirm Password", show="*")

        otp_f = tk.Frame(self, bg=st.COLORS["white"])
        otp_f.pack(fill="x", padx=30, pady=(0, 8))
        tk.Label(
            otp_f, text="Email OTP", font=st.FONTS["body_bold"],
            bg=st.COLORS["white"], fg=st.COLORS["text_dark"]
        ).pack(anchor="w")
        row = tk.Frame(otp_f, bg=st.COLORS["white"])
        row.pack(fill="x", pady=(2, 0))
        self._otp = tk.StringVar()
        tk.Entry(row, textvariable=self._otp, **st.ENTRY).pack(
            side="left", fill="x", expand=True, ipady=5
        )
        self._send_btn = tk.Button(
            row, text="Send OTP", command=self._send_otp, **st.BUTTON["sm_primary"]
        )
        self._send_btn.pack(side="left", padx=(8, 0))

        self._msg_var = tk.StringVar()
        tk.Label(
            self, textvariable=self._msg_var, font=st.FONTS["small"],
            bg=st.COLORS["white"], fg=st.COLORS["danger"], wraplength=360
        ).pack(padx=30, pady=4)

        tk.Button(
            self, text="Verify OTP and Create Account",
            command=self._do_register, **st.BUTTON["primary"]
        ).pack(fill="x", padx=30, pady=(6, 8))

        tk.Button(
            self, text="Back to Login", command=self.destroy, **st.BUTTON["link"]
        ).pack(pady=(0, 16))

    def _validate(self):
        u = self._uname.get().strip()
        em = self._email.get().strip()
        pw = self._pass.get()
        cp = self._cpass.get()
        if not u:
            self._msg_var.set("Username is required.")
            return False
        if len(u) < 3:
            self._msg_var.set("Username must be at least 3 characters.")
            return False
        if not em:
            self._msg_var.set("Email is required.")
            return False
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", em):
            self._msg_var.set("Enter a valid email address.")
            return False
        if not pw:
            self._msg_var.set("Password is required.")
            return False
        if len(pw) < 6:
            self._msg_var.set("Password must be at least 6 characters.")
            return False
        if pw != cp:
            self._msg_var.set("Passwords do not match.")
            return False
        if db.get_user_by_username(u):
            self._msg_var.set("Username already taken.")
            return False
        if db.get_user_by_email(em):
            self._msg_var.set("Email already registered.")
            return False
        return True

    def _send_otp(self):
        self._msg_var.set("")
        if not self._validate():
            return
        email = self._email.get().strip()
        self._msg_var.set("Sending OTP...")
        self._send_btn.config(state="disabled", text="Sending...")

        def after(ok, msg):
            self.after(0, lambda: self._after_send(ok, msg))

        smtp.send_otp_email(email, purpose="account verification", callback=after)

    def _after_send(self, ok, msg):
        self._send_btn.config(state="normal", text="Resend OTP")
        if ok:
            self._otp_sent = True
            self._msg_var.set("OTP sent. Check your email.")
        else:
            self._msg_var.set(f"Failed to send OTP: {msg}")

    def _do_register(self):
        self._msg_var.set("")
        if not self._otp_sent:
            self._msg_var.set("Please send the OTP first.")
            return
        otp = self._otp.get().strip()
        if not otp:
            self._msg_var.set("Please enter the OTP.")
            return
        ok, msg = smtp.verify_otp(self._email.get().strip(), otp)
        if not ok:
            self._msg_var.set(msg)
            return
        ok2, msg2 = db.create_user(
            self._uname.get().strip(),
            self._email.get().strip(),
            self._pass.get()
        )
        if ok2:
            smtp.send_welcome_email(
                self._email.get().strip(),
                self._uname.get().strip()
            )
            messagebox.showinfo(
                "Account Created",
                "Your account has been created. You can now log in.",
                parent=self
            )
            self.destroy()
        else:
            self._msg_var.set(msg2)
