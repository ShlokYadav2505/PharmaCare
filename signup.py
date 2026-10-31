# signup.py - Account creation for pharmacists and vendors

import os
import re
import secrets
import tkinter as tk
from tkinter import messagebox, ttk
import database as db
import vendor_system as vendor_db
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
        self._vendor_invite_code = os.getenv("PHARMACARE_VENDOR_INVITE_CODE", "").strip()
        self._build_ui()
        self._center(440, 760 if self._vendor_invite_code else 560)

    def _center(self, w, h):
        self.update_idletasks()
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _field(self, parent, label, show=""):
        f = tk.Frame(parent, bg=st.COLORS["white"])
        f.pack(fill="x", padx=30, pady=(0, 7))
        tk.Label(f, text=label, font=st.FONTS["body_bold"],
                 bg=st.COLORS["white"], fg=st.COLORS["text_dark"]).pack(anchor="w")
        var = tk.StringVar()
        tk.Entry(f, textvariable=var, show=show, **st.ENTRY).pack(fill="x", ipady=4, pady=(2, 0))
        return var

    def _build_ui(self):
        tk.Label(self, text="Create Account", font=st.FONTS["heading"],
                 bg=st.COLORS["white"], fg=st.COLORS["primary"]).pack(pady=(14, 8))
        self._role = tk.StringVar(value="Pharmacist")
        if self._vendor_invite_code:
            role_frame = tk.Frame(self, bg=st.COLORS["white"])
            role_frame.pack(fill="x", padx=30, pady=(0, 7))
            tk.Label(role_frame, text="Account type", font=st.FONTS["body_bold"],
                     bg=st.COLORS["white"], fg=st.COLORS["text_dark"]).pack(anchor="w")
            ttk.Combobox(role_frame, textvariable=self._role,
                         values=("Pharmacist", "Vendor"), state="readonly"
                         ).pack(fill="x", pady=(2, 0))
        self._uname = self._field(self, "Username")
        self._email = self._field(self, "Email Address")
        self._pass = self._field(self, "Password", show="*")
        self._cpass = self._field(self, "Confirm Password", show="*")
        self._vendor_invite = None
        self._business = self._contact = self._phone = self._address = None
        if self._vendor_invite_code:
            self._vendor_invite = self._field(self, "Vendor invite code")
            self._business = self._field(self, "Vendor business name")
            self._contact = self._field(self, "Contact person")
            self._phone = self._field(self, "Phone")
            self._address = self._field(self, "Business address")

        otp_f = tk.Frame(self, bg=st.COLORS["white"])
        otp_f.pack(fill="x", padx=30, pady=(0, 6))
        tk.Label(otp_f, text="Email OTP", font=st.FONTS["body_bold"],
                 bg=st.COLORS["white"], fg=st.COLORS["text_dark"]).pack(anchor="w")
        row = tk.Frame(otp_f, bg=st.COLORS["white"])
        row.pack(fill="x", pady=(2, 0))
        self._otp = tk.StringVar()
        tk.Entry(row, textvariable=self._otp, **st.ENTRY).pack(side="left", fill="x", expand=True, ipady=4)
        self._send_btn = tk.Button(row, text="Send OTP", command=self._send_otp,
                                   **st.BUTTON["sm_primary"])
        self._send_btn.pack(side="left", padx=(8, 0))
        self._msg_var = tk.StringVar()
        tk.Label(self, textvariable=self._msg_var, font=st.FONTS["small"],
                 bg=st.COLORS["white"], fg=st.COLORS["danger"], wraplength=380).pack(padx=30, pady=4)
        tk.Button(self, text="Verify OTP and Create Account", command=self._do_register,
                  **st.BUTTON["primary"]).pack(fill="x", padx=30, pady=(4, 7))
        tk.Button(self, text="Back to Login", command=self.destroy,
                  **st.BUTTON["link"]).pack(pady=(0, 10))

    def _validate(self):
        u, em, pw, cp = self._uname.get().strip(), self._email.get().strip(), self._pass.get(), self._cpass.get()
        if len(u) < 3:
            self._msg_var.set("Username must be at least 3 characters.")
            return False
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", em):
            self._msg_var.set("Enter a valid email address.")
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
        if self._role.get() == "Vendor":
            invite = self._vendor_invite.get().strip() if self._vendor_invite else ""
            if (not self._vendor_invite_code or
                    not secrets.compare_digest(invite.encode("utf-8"),
                                               self._vendor_invite_code.encode("utf-8"))):
                self._msg_var.set("A valid vendor invite code is required.")
                return False
            if not self._business.get().strip():
                self._msg_var.set("Vendor business name is required for vendor accounts.")
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
        self._otp_sent = bool(ok)
        self._msg_var.set("OTP sent. Check your email." if ok else f"Failed to send email: {msg}")

    def _do_register(self):
        self._msg_var.set("")
        if not self._otp_sent:
            self._msg_var.set("Please send the OTP first.")
            return
        if not self._validate():
            return
        ok, msg = smtp.verify_otp(self._email.get().strip(), self._otp.get().strip())
        if not ok:
            self._msg_var.set(msg)
            return
        ok, msg = db.create_user(self._uname.get().strip(), self._email.get().strip(), self._pass.get())
        if not ok:
            self._msg_var.set(msg)
            return
        if self._role.get() == "Vendor":
            user = db.get_user_by_username(self._uname.get().strip())
            ok, msg = vendor_db.register_vendor_account(
                user["id"], self._business.get(), self._contact.get(),
                self._phone.get(), self._address.get())
            if not ok:
                self._msg_var.set("Account was created but vendor profile failed: " + msg)
                return
        smtp.send_welcome_email(self._email.get().strip(), self._uname.get().strip())
        messagebox.showinfo("Account Created",
            "Vendor account created. You can log in to the Vendor Portal." if self._role.get() == "Vendor"
            else "Account created. You can now log in to the pharmacy dashboard.", parent=self)
        self.destroy()
