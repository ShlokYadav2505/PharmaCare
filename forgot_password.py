import tkinter as tk
from tkinter import messagebox
import database as db
import smtp_handler as smtp
import styles as st


class ForgotPasswordWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("PharmaCare – Reset Password")
        self.resizable(False, False)
        self.grab_set()
        self.configure(bg=st.COLORS["white"])
        self._email = ""
        self._build_ui()
        self._center(460, 440)
        self._show_step(1)

    def _center(self, w, h):
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build_ui(self):
        hdr = tk.Frame(self, bg=st.COLORS["primary_dark"])
        hdr.pack(fill="x")
        tk.Label(hdr, text="🔑  Reset Password", font=st.FONTS["subheading"],
                 bg=st.COLORS["primary_dark"], fg=st.COLORS["white"]).pack(pady=16)

        body = tk.Frame(self, bg=st.COLORS["white"])
        body.pack(fill="both", expand=True, padx=36, pady=20)

        self._step_lbl = tk.Label(body, text="Step 1 of 3",
                                   font=st.FONTS["small_bold"],
                                   bg=st.COLORS["white"], fg=st.COLORS["text_light"])
        self._step_lbl.pack(anchor="e")

        self._instr = tk.Label(body, text="", font=st.FONTS["body"],
                                bg=st.COLORS["white"], fg=st.COLORS["text_medium"],
                                wraplength=380, justify="left")
        self._instr.pack(anchor="w", pady=(0,14))

        # Step 1
        self._s1 = tk.Frame(body, bg=st.COLORS["white"])
        tk.Label(self._s1, text="Registered Email", font=st.FONTS["body_bold"],
                 bg=st.COLORS["white"], fg=st.COLORS["text_medium"]).pack(anchor="w")
        self._email_var = tk.StringVar()
        self._email_ent = tk.Entry(self._s1, textvariable=self._email_var, **st.ENTRY)
        self._email_ent.pack(fill="x", ipady=7, pady=(4,0))
        self._send_btn = tk.Button(self._s1, text="Send OTP",
                                   command=self._send_otp, **st.BUTTON["primary"])
        self._send_btn.pack(fill="x", pady=(14,0))
        st.add_hover(self._send_btn, st.COLORS["primary"], st.COLORS["primary_dark"])

        # Step 2
        self._s2 = tk.Frame(body, bg=st.COLORS["white"])
        tk.Label(self._s2, text="One-Time Password (OTP)", font=st.FONTS["body_bold"],
                 bg=st.COLORS["white"], fg=st.COLORS["text_medium"]).pack(anchor="w")
        self._otp_var = tk.StringVar()
        tk.Entry(self._s2, textvariable=self._otp_var, **st.ENTRY).pack(
            fill="x", ipady=7, pady=(4,0))
        r2 = tk.Frame(self._s2, bg=st.COLORS["white"])
        r2.pack(fill="x", pady=(14,0))
        tk.Button(r2, text="Resend OTP", command=self._send_otp,
                  **st.BUTTON["secondary"]).pack(side="left")
        vb = tk.Button(r2, text="Verify OTP", command=self._verify_otp,
                       **st.BUTTON["primary"])
        vb.pack(side="right")
        st.add_hover(vb, st.COLORS["primary"], st.COLORS["primary_dark"])

        # Step 3
        self._s3 = tk.Frame(body, bg=st.COLORS["white"])
        tk.Label(self._s3, text="New Password", font=st.FONTS["body_bold"],
                 bg=st.COLORS["white"], fg=st.COLORS["text_medium"]).pack(anchor="w")
        self._np  = tk.StringVar()
        tk.Entry(self._s3, textvariable=self._np, show="•", **st.ENTRY).pack(
            fill="x", ipady=7, pady=(4,0))
        tk.Label(self._s3, text="Confirm New Password", font=st.FONTS["body_bold"],
                 bg=st.COLORS["white"], fg=st.COLORS["text_medium"]).pack(anchor="w", pady=(10,0))
        self._cnp = tk.StringVar()
        tk.Entry(self._s3, textvariable=self._cnp, show="•", **st.ENTRY).pack(
            fill="x", ipady=7, pady=(4,0))
        rb = tk.Button(self._s3, text="Reset Password",
                       command=self._do_reset, **st.BUTTON["primary"])
        rb.pack(fill="x", pady=(14,0))
        st.add_hover(rb, st.COLORS["primary"], st.COLORS["primary_dark"])

        self._msg_var = tk.StringVar()
        self._msg_lbl = tk.Label(body, textvariable=self._msg_var,
                                  font=st.FONTS["small"], bg=st.COLORS["white"],
                                  fg=st.COLORS["danger"], wraplength=380)
        self._msg_lbl.pack(pady=(12,0))
        tk.Button(body, text="← Cancel", command=self.destroy,
                  **st.BUTTON["link"]).pack(pady=(8,0))

    def _set_msg(self, text, error=True):
        self._msg_var.set(text)
        self._msg_lbl.config(fg=st.COLORS["danger"] if error else st.COLORS["success"])

    def _show_step(self, step):
        self._step_lbl.config(text=f"Step {step} of 3")
        self._msg_var.set("")
        instrs = {
            1: "Enter the email address linked to your account.",
            2: "Enter the 6-digit OTP sent to your email.",
            3: "Enter and confirm your new password.",
        }
        self._instr.config(text=instrs[step])
        for f in (self._s1, self._s2, self._s3):
            f.pack_forget()
        [self._s1, self._s2, self._s3][step-1].pack(fill="x")

    def _send_otp(self):
        self._msg_var.set("")
        email = self._email_var.get().strip().lower()
        if not email:
            self._set_msg("Please enter your email."); return
        if not db.get_user_by_email(email):
            self._set_msg("No account with that email."); return
        self._email = email
        self._set_msg("Sending OTP…", error=False)
        self._send_btn.config(state="disabled", text="Sending…")
        def after(ok, msg):
            self.after(0, lambda: self._after_send(ok, msg))
        smtp.send_otp_email(email, purpose="password reset", callback=after)

    def _after_send(self, ok, msg):
        self._send_btn.config(state="normal", text="Send OTP")
        if ok:
            self._set_msg(f"OTP sent to {self._email}.", error=False)
            self._show_step(2)
        else:
            self._set_msg(f"Failed: {msg}")

    def _verify_otp(self):
        self._msg_var.set("")
        otp = self._otp_var.get().strip()
        if not otp:
            self._set_msg("Enter the OTP."); return
        ok, msg = smtp.verify_otp(self._email, otp)
        if ok:
            self._set_msg("OTP verified!", error=False)
            self.after(600, lambda: self._show_step(3))
        else:
            self._set_msg(msg)

    def _do_reset(self):
        self._msg_var.set("")
        np = self._np.get(); cnp = self._cnp.get()
        if not np:        self._set_msg("Enter new password."); return
        if len(np) < 6:   self._set_msg("Password ≥ 6 chars."); return
        if np != cnp:     self._set_msg("Passwords don't match."); return
        ok, msg = db.update_password(self._email, np)
        if ok:
            messagebox.showinfo("Success",
                "Password reset! You can now log in.", parent=self)
            self.destroy()
        else:
            self._set_msg(msg)