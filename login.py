# login.py - Simple login screen

import tkinter as tk
from tkinter import messagebox
import database as db
import styles as st


class LoginFrame(tk.Frame):
    def __init__(self, parent, on_success_callback):
        super().__init__(parent, bg=st.COLORS["background"])
        self._on_success = on_success_callback
        self._build_ui()

    def _build_ui(self):
        box = tk.Frame(self, bg=st.COLORS["white"], relief="solid", bd=1)
        box.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(
            box, text="PharmaCare",
            font=st.FONTS["title"],
            bg=st.COLORS["white"], fg=st.COLORS["primary"]
        ).pack(pady=(24, 4), padx=40)

        tk.Label(
            box, text="Pharmacy Management System",
            font=st.FONTS["small"],
            bg=st.COLORS["white"], fg=st.COLORS["text_light"]
        ).pack(pady=(0, 16))

        tk.Label(
            box, text="Email Address", font=st.FONTS["body_bold"],
            bg=st.COLORS["white"], fg=st.COLORS["text_dark"],
            anchor="w"
        ).pack(fill="x", padx=40)
        self._email_var = tk.StringVar()
        self._email_entry = tk.Entry(box, textvariable=self._email_var, **st.ENTRY)
        self._email_entry.pack(fill="x", padx=40, ipady=5, pady=(2, 10))
        self._email_entry.bind("<Return>", lambda e: self._pass_entry.focus())

        tk.Label(
            box, text="Password", font=st.FONTS["body_bold"],
            bg=st.COLORS["white"], fg=st.COLORS["text_dark"],
            anchor="w"
        ).pack(fill="x", padx=40)
        self._pass_var = tk.StringVar()
        self._pass_entry = tk.Entry(
            box, textvariable=self._pass_var, show="*", **st.ENTRY
        )
        self._pass_entry.pack(fill="x", padx=40, ipady=5, pady=(2, 6))
        self._pass_entry.bind("<Return>", lambda e: self._do_login())

        self._show = tk.BooleanVar(value=False)
        tk.Checkbutton(
            box, text="Show password", variable=self._show,
            font=st.FONTS["small"], bg=st.COLORS["white"],
            fg=st.COLORS["text_medium"],
            activebackground=st.COLORS["white"],
            command=lambda: self._pass_entry.config(
                show="" if self._show.get() else "*"
            )
        ).pack(anchor="w", padx=40, pady=(0, 8))

        self._msg_var = tk.StringVar()
        tk.Label(
            box, textvariable=self._msg_var, font=st.FONTS["small"],
            bg=st.COLORS["white"], fg=st.COLORS["danger"]
        ).pack(padx=40)

        tk.Button(
            box, text="Login", command=self._do_login, **st.BUTTON["primary"]
        ).pack(fill="x", padx=40, pady=(8, 12))

        links = tk.Frame(box, bg=st.COLORS["white"])
        links.pack(pady=(0, 20))
        tk.Button(
            links, text="Create Account", command=self._open_signup,
            **st.BUTTON["link"]
        ).pack(side="left", padx=8)
        tk.Button(
            links, text="Forgot Password", command=self._open_forgot,
            **st.BUTTON["link"]
        ).pack(side="left", padx=8)

        self._email_entry.focus()

    def _set_msg(self, text, error=True):
        self._msg_var.set(text)

    def _do_login(self):
        email = self._email_var.get().strip()
        pw = self._pass_var.get()
        if not email:
            self._set_msg("Please enter your email address.")
            return
        if not pw:
            self._set_msg("Please enter your password.")
            return
        ok, msg, uname = db.validate_login(email, pw)
        if ok:
            self._set_msg("")
            self._on_success(uname)
        else:
            self._set_msg(msg)

    def _open_signup(self):
        from signup import SignupWindow
        SignupWindow(self.winfo_toplevel())

    def _open_forgot(self):
        from forgot_password import ForgotPasswordWindow
        ForgotPasswordWindow(self.winfo_toplevel())
