import re, tkinter as tk
from tkinter import messagebox
import database as db
import smtp_handler as smtp
import styles as st


class SignupWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("PharmaCare – Create Account")
        self.resizable(False, False)
        self.grab_set()
        self.configure(bg=st.COLORS["white"])
        self._otp_sent = False
        self._build_ui()
        self._center(520, 620)

    def _center(self, w, h):
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _make_field(self, parent, label, show=""):
        f = tk.Frame(parent, bg=st.COLORS["white"])
        f.pack(fill="x", padx=36, pady=(0, 10))
        tk.Label(f, text=label,
                 font=("Calibri", 11, "bold"),
                 bg=st.COLORS["white"],
                 fg=st.COLORS["text_medium"]).pack(anchor="w")
        var = tk.StringVar()
        e = tk.Entry(f, textvariable=var, show=show,
                     font=("Calibri", 12),
                     bg=st.COLORS["entry_bg"],
                     fg=st.COLORS["text_dark"],
                     relief="solid", bd=1,
                     highlightthickness=1,
                     highlightbackground=st.COLORS["entry_border"],
                     highlightcolor=st.COLORS["primary"])
        e.pack(fill="x", ipady=7, pady=(4, 0))
        return var, e

    def _build_ui(self):
        # Header
        hdr = tk.Frame(self, bg=st.COLORS["primary_dark"])
        hdr.pack(fill="x")
        tk.Label(hdr, text="✚  Create Account",
                 font=("Calibri", 16, "bold"),
                 bg=st.COLORS["primary_dark"],
                 fg=st.COLORS["white"]).pack(pady=18)

        tk.Frame(self, bg=st.COLORS["white"], height=10).pack()

        # Form fields
        self._uname, _ = self._make_field(self, "Username")
        self._email, _ = self._make_field(self, "Email Address")
        self._pass,  _ = self._make_field(self, "Password", show="•")
        self._cpass, _ = self._make_field(self, "Confirm Password", show="•")

        # OTP row
        otp_f = tk.Frame(self, bg=st.COLORS["white"])
        otp_f.pack(fill="x", padx=36, pady=(0, 10))
        tk.Label(otp_f, text="Email OTP",
                 font=("Calibri", 11, "bold"),
                 bg=st.COLORS["white"],
                 fg=st.COLORS["text_medium"]).pack(anchor="w")
        row = tk.Frame(otp_f, bg=st.COLORS["white"])
        row.pack(fill="x", pady=(4, 0))
        self._otp = tk.StringVar()
        tk.Entry(row, textvariable=self._otp,
                 font=("Calibri", 12),
                 bg=st.COLORS["entry_bg"],
                 fg=st.COLORS["text_dark"],
                 relief="solid", bd=1).pack(side="left", fill="x",
                                            expand=True, ipady=7)
        self._send_btn = tk.Button(row, text="Send OTP",
                                   command=self._send_otp,
                                   font=("Calibri", 10, "bold"),
                                   bg=st.COLORS["primary"],
                                   fg=st.COLORS["white"],
                                   relief="flat", bd=0, cursor="hand2",
                                   padx=14, pady=6,
                                   activebackground=st.COLORS["primary_dark"],
                                   activeforeground=st.COLORS["white"])
        self._send_btn.pack(side="left", padx=(8, 0))

        # Message label
        self._msg_var = tk.StringVar()
        self._msg_lbl = tk.Label(self, textvariable=self._msg_var,
                                  font=("Calibri", 10),
                                  bg=st.COLORS["white"],
                                  fg=st.COLORS["danger"],
                                  wraplength=440, justify="center")
        self._msg_lbl.pack(padx=36, pady=(0, 6))

        # Register button  ← renamed to _do_register (fixes the Tkinter conflict)
        btn = tk.Button(self, text="Verify OTP & Create Account",
                        command=self._do_register,
                        font=("Calibri", 12, "bold"),
                        bg=st.COLORS["primary"],
                        fg=st.COLORS["white"],
                        relief="flat", bd=0, cursor="hand2",
                        padx=24, pady=10,
                        activebackground=st.COLORS["primary_dark"],
                        activeforeground=st.COLORS["white"])
        btn.pack(fill="x", padx=36, pady=(0, 12))

        tk.Button(self, text="← Back to Login",
                  command=self.destroy,
                  font=("Calibri", 10),
                  bg=st.COLORS["white"],
                  fg=st.COLORS["primary"],
                  relief="flat", bd=0,
                  cursor="hand2",
                  activebackground=st.COLORS["white"],
                  activeforeground=st.COLORS["primary_dark"]
                  ).pack(pady=(0, 16))

    def _set_msg(self, text, error=True):
        self._msg_var.set(text)
        self._msg_lbl.config(
            fg=st.COLORS["danger"] if error else st.COLORS["success"])

    def _validate(self):
        u  = self._uname.get().strip()
        em = self._email.get().strip()
        pw = self._pass.get()
        cp = self._cpass.get()
        if not u:
            self._set_msg("Username is required."); return False
        if len(u) < 3:
            self._set_msg("Username must be at least 3 characters."); return False
        if not em:
            self._set_msg("Email is required."); return False
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", em):
            self._set_msg("Enter a valid email address."); return False
        if not pw:
            self._set_msg("Password is required."); return False
        if len(pw) < 6:
            self._set_msg("Password must be at least 6 characters."); return False
        if pw != cp:
            self._set_msg("Passwords do not match."); return False
        if db.get_user_by_username(u):
            self._set_msg("Username already taken."); return False
        if db.get_user_by_email(em):
            self._set_msg("Email already registered."); return False
        return True

    def _send_otp(self):
        self._msg_var.set("")
        if not self._validate():
            return
        email = self._email.get().strip()
        self._set_msg("Sending OTP… please wait.", error=False)
        self._send_btn.config(state="disabled", text="Sending…")

        def after(ok, msg):
            self.after(0, lambda: self._after_send(ok, msg))

        smtp.send_otp_email(email, purpose="account verification", callback=after)

    def _after_send(self, ok, msg):
        self._send_btn.config(state="normal", text="Resend OTP")
        if ok:
            self._otp_sent = True
            self._set_msg(
                f"OTP sent to {self._email.get().strip()}. Check your inbox.",
                error=False)
        else:
            self._set_msg(f"Failed to send OTP: {msg}")

    # ← KEY FIX: renamed from _register to _do_register
    def _do_register(self):
        self._msg_var.set("")
        if not self._otp_sent:
            self._set_msg("Please send the OTP to your email first.")
            return
        otp = self._otp.get().strip()
        if not otp:
            self._set_msg("Please enter the OTP from your email.")
            return
        ok, msg = smtp.verify_otp(self._email.get().strip(), otp)
        if not ok:
            self._set_msg(msg)
            return
        ok2, msg2 = db.create_user(
            self._uname.get().strip(),
            self._email.get().strip(),
            self._pass.get())
        if ok2:
            smtp.send_welcome_email(
                self._email.get().strip(),
                self._uname.get().strip())
            messagebox.showinfo(
                "Account Created",
                "Your account has been created!\nYou can now log in.",
                parent=self)
            self.destroy()
        else:
            self._set_msg(msg2)