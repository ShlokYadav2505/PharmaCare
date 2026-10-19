import tkinter as tk
import database as db
import styles as st


class LoginFrame(tk.Frame):
    def __init__(self, parent, on_success_callback):
        super().__init__(parent, bg=st.COLORS["primary_dark"])
        self._on_success = on_success_callback
        self._build_ui()

    def _build_ui(self):
        self.pack_propagate(False)
        outer = tk.Frame(self, bg=st.COLORS["primary_dark"])
        outer.place(relx=0.5, rely=0.5, anchor="center")
        card = tk.Frame(outer, bg=st.COLORS["white"], relief="flat", bd=0)
        card.pack()
        left = tk.Frame(card, bg=st.COLORS["primary_dark"], width=260, height=520)
        left.pack(side="left")
        left.pack_propagate(False)
        self._build_left(left)
        right = tk.Frame(card, bg=st.COLORS["white"], width=400, height=520)
        right.pack(side="left")
        right.pack_propagate(False)
        self._build_right(right)

    def _build_left(self, p):
        tk.Label(p, text="✚", font=("Calibri", 60, "bold"),
                 bg=st.COLORS["primary_dark"], fg=st.COLORS["accent"]).place(relx=0.5, rely=0.35, anchor="center")
        tk.Label(p, text="PharmaCare", font=("Calibri", 20, "bold"),
                 bg=st.COLORS["primary_dark"], fg=st.COLORS["white"]).place(relx=0.5, rely=0.52, anchor="center")
        tk.Label(p, text="Pharmacy Management\nSystem", font=("Calibri", 10),
                 bg=st.COLORS["primary_dark"], fg=st.COLORS["sidebar_icon"],
                 justify="center").place(relx=0.5, rely=0.62, anchor="center")
        tk.Label(p, text="Login with your email", font=("Calibri", 9),
                 bg=st.COLORS["primary_dark"], fg=st.COLORS["secondary"]).place(relx=0.5, rely=0.93, anchor="center")

    def _build_right(self, p):
        tk.Label(p, text="Welcome Back!", font=("Calibri", 22, "bold"),
                 bg=st.COLORS["white"], fg=st.COLORS["text_dark"]).place(relx=0.5, rely=0.12, anchor="center")
        tk.Label(p, text="Sign in with your email", font=("Calibri", 11),
                 bg=st.COLORS["white"], fg=st.COLORS["text_light"]).place(relx=0.5, rely=0.21, anchor="center")
        tk.Label(p, text="Email", font=("Calibri", 11, "bold"),
                 bg=st.COLORS["white"], fg=st.COLORS["text_medium"]).place(x=40, y=140)
        self._email_var = tk.StringVar()
        self._email_entry = tk.Entry(p, textvariable=self._email_var, font=("Calibri", 12),
                                     relief="solid", bd=1, bg=st.COLORS["entry_bg"], fg=st.COLORS["text_dark"],
                                     highlightthickness=1, highlightbackground=st.COLORS["entry_border"],
                                     highlightcolor=st.COLORS["primary"])
        self._email_entry.place(x=40, y=162, width=320, height=36)
        self._email_entry.bind("<Return>", lambda e: self._pass_entry.focus())
        tk.Label(p, text="Password", font=("Calibri", 11, "bold"),
                 bg=st.COLORS["white"], fg=st.COLORS["text_medium"]).place(x=40, y=218)
        self._pass_var = tk.StringVar()
        self._pass_entry = tk.Entry(p, textvariable=self._pass_var, show="•", font=("Calibri", 12),
                                    relief="solid", bd=1, bg=st.COLORS["entry_bg"], fg=st.COLORS["text_dark"],
                                    highlightthickness=1, highlightbackground=st.COLORS["entry_border"],
                                    highlightcolor=st.COLORS["primary"])
        self._pass_entry.place(x=40, y=240, width=320, height=36)
        self._pass_entry.bind("<Return>", lambda e: self._do_login())
        self._show = tk.BooleanVar(value=False)
        tk.Checkbutton(p, text="Show password", variable=self._show, font=("Calibri", 9),
                       bg=st.COLORS["white"], fg=st.COLORS["text_light"],
                       activebackground=st.COLORS["white"], cursor="hand2",
                       command=lambda: self._pass_entry.config(show="" if self._show.get() else "•")).place(x=40, y=283)
        self._msg_var = tk.StringVar()
        self._msg_lbl = tk.Label(p, textvariable=self._msg_var, font=("Calibri", 10),
                                  bg=st.COLORS["white"], fg=st.COLORS["danger"], wraplength=320)
        self._msg_lbl.place(x=40, y=308, width=320)
        login_btn = tk.Button(p, text="Login", command=self._do_login, font=("Calibri", 12, "bold"),
                              bg=st.COLORS["primary"], fg=st.COLORS["white"], relief="flat", bd=0, cursor="hand2",
                              activebackground=st.COLORS["primary_dark"], activeforeground=st.COLORS["white"])
        login_btn.place(x=40, y=335, width=320, height=42)
        st.add_hover(login_btn, st.COLORS["primary"], st.COLORS["primary_dark"])
        tk.Frame(p, bg=st.COLORS["border"], height=1).place(x=40, y=392, width=320)
        tk.Label(p, text="No account?", font=("Calibri", 10),
                 bg=st.COLORS["white"], fg=st.COLORS["text_light"]).place(x=60, y=405)
        tk.Button(p, text="Sign Up", command=self._open_signup, font=("Calibri", 10),
                  bg=st.COLORS["white"], fg=st.COLORS["primary"], relief="flat", bd=0, cursor="hand2",
                  activebackground=st.COLORS["white"], activeforeground=st.COLORS["primary_dark"]).place(x=140, y=402)
        tk.Button(p, text="Forgot Password?", command=self._open_forgot, font=("Calibri", 10),
                  bg=st.COLORS["white"], fg=st.COLORS["primary"], relief="flat", bd=0, cursor="hand2",
                  activebackground=st.COLORS["white"], activeforeground=st.COLORS["primary_dark"]).place(x=210, y=402)
        self._email_entry.focus()

    def _set_msg(self, text, error=True):
        self._msg_var.set(text)
        self._msg_lbl.config(fg=st.COLORS["danger"] if error else st.COLORS["success"])

    def _do_login(self):
        em = self._email_var.get().strip()
        pw = self._pass_var.get()
        if not em:
            self._set_msg("Please enter your email."); return
        if "@" not in em:
            self._set_msg("Enter a valid email address."); return
        if not pw:
            self._set_msg("Please enter your password."); return
        ok, msg, email, role = db.validate_login(em, pw)
        if ok:
            self._set_msg("Login successful! Loading…", error=False)
            self.after(600, lambda: self._on_success(email, role))
        else:
            self._set_msg(msg)

    def _open_signup(self):
        from signup import SignupWindow
        SignupWindow(self.winfo_toplevel())

    def _open_forgot(self):
        from forgot_password import ForgotPasswordWindow
        ForgotPasswordWindow(self.winfo_toplevel())