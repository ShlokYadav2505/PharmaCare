import tkinter as tk
from tkinter import messagebox
from datetime import datetime
import database as db
import styles as st

_inv_cls = _bill_cls = _rep_cls = _vend_cls = _purch_cls = _exp_cls = None

def _get_inv():
    global _inv_cls
    if not _inv_cls:
        from inventory import InventoryFrame; _inv_cls = InventoryFrame
    return _inv_cls

def _get_bill():
    global _bill_cls
    if not _bill_cls:
        from billing import BillingFrame; _bill_cls = BillingFrame
    return _bill_cls

def _get_rep():
    global _rep_cls
    if not _rep_cls:
        from reports import ReportsFrame; _rep_cls = ReportsFrame
    return _rep_cls

def _get_vend():
    global _vend_cls
    if not _vend_cls:
        from vendors import VendorsFrame; _vend_cls = VendorsFrame
    return _vend_cls

def _get_purch():
    global _purch_cls
    if not _purch_cls:
        from purchases import PurchasesFrame; _purch_cls = PurchasesFrame
    return _purch_cls

def _get_exp():
    global _exp_cls
    if not _exp_cls:
        from expenses import ExpensesFrame; _exp_cls = ExpensesFrame
    return _exp_cls


class DashboardApp(tk.Frame):
    NAV = [("🏠","Dashboard","home"),("💊","Inventory","inventory"),
           ("🏢","Vendors","vendors"),("📦","Purchases","purchases"),
           ("🧾","Billing","billing"),("💸","Expenses","expenses"),
           ("📊","Reports","reports")]

    def __init__(self, parent, username, on_logout_callback):
        super().__init__(parent, bg=st.COLORS["background"])
        self._username   = username
        self._on_logout  = on_logout_callback
        self._user_email = self._get_email(username)
        self._frames     = {}
        self._current    = ""
        self._nav_btns   = {}
        self._build_ui()
        self._switch("home")
        self._check_alerts()

    def _get_email(self, username):
        user = db.get_user_by_username(username)
        return user["email"] if user else ""

    def _build_ui(self):
        self.rowconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        sidebar = tk.Frame(self, bg=st.COLORS["sidebar_bg"], width=220)
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.grid_propagate(False)
        self._build_sidebar(sidebar)

        self._content = tk.Frame(self, bg=st.COLORS["background"])
        self._content.grid(row=0, column=1, sticky="nsew")
        self._content.rowconfigure(0, weight=1)
        self._content.columnconfigure(0, weight=1)

    def _build_sidebar(self, sb):
        # Logo
        lo = tk.Frame(sb, bg=st.COLORS["primary_dark"])
        lo.pack(fill="x")
        tk.Label(lo, text="✚", font=("Calibri",28,"bold"),
                 bg=st.COLORS["primary_dark"], fg=st.COLORS["accent"]).pack(pady=(20,0))
        tk.Label(lo, text="PharmaCare", font=st.FONTS["logo"],
                 bg=st.COLORS["primary_dark"], fg=st.COLORS["white"]).pack()
        tk.Label(lo, text="Pharmacy Management", font=("Calibri",9),
                 bg=st.COLORS["primary_dark"], fg=st.COLORS["sidebar_icon"]).pack(pady=(0,16))
        tk.Frame(sb, bg=st.COLORS["sidebar_hover"], height=1).pack(fill="x")

        # User info
        uf = tk.Frame(sb, bg=st.COLORS["sidebar_bg"])
        uf.pack(fill="x", pady=14, padx=16)
        tk.Label(uf, text="👤", font=("Calibri",22),
                 bg=st.COLORS["sidebar_hover"], fg=st.COLORS["white"],
                 width=3).pack(side="left", padx=(0,10))
        info = tk.Frame(uf, bg=st.COLORS["sidebar_bg"])
        info.pack(side="left")
        tk.Label(info, text=self._username, font=st.FONTS["body_bold"],
                 bg=st.COLORS["sidebar_bg"], fg=st.COLORS["white"],
                 anchor="w").pack(anchor="w")
        tk.Label(info, text="Pharmacist", font=st.FONTS["small"],
                 bg=st.COLORS["sidebar_bg"], fg=st.COLORS["sidebar_icon"],
                 anchor="w").pack(anchor="w")
        tk.Frame(sb, bg=st.COLORS["sidebar_hover"], height=1).pack(fill="x")
        tk.Frame(sb, bg=st.COLORS["sidebar_bg"], height=10).pack()

        # Nav items
        for icon, label, key in self.NAV:
            btn = tk.Button(sb, text=f"  {icon}   {label}",
                            font=st.FONTS["sidebar_item"],
                            bg=st.COLORS["sidebar_bg"], fg=st.COLORS["sidebar_text"],
                            relief="flat", bd=0, cursor="hand2",
                            padx=16, pady=13, anchor="w",
                            activebackground=st.COLORS["sidebar_active"],
                            activeforeground=st.COLORS["white"],
                            command=lambda k=key: self._switch(k))
            btn.pack(fill="x")
            st.add_hover(btn, st.COLORS["sidebar_bg"], st.COLORS["sidebar_hover"])
            self._nav_btns[key] = btn

        # Logout
        tk.Frame(sb, bg=st.COLORS["sidebar_bg"]).pack(fill="both", expand=True)
        tk.Frame(sb, bg=st.COLORS["sidebar_hover"], height=1).pack(fill="x")
        lb = tk.Button(sb, text="⎋  Logout", font=st.FONTS["sidebar_item"],
                       bg=st.COLORS["sidebar_bg"], fg=st.COLORS["sidebar_icon"],
                       relief="flat", bd=0, cursor="hand2", padx=20, pady=12,
                       anchor="w", activebackground=st.COLORS["danger"],
                       activeforeground=st.COLORS["white"],
                       command=self._logout)
        lb.pack(fill="x")
        st.add_hover(lb, st.COLORS["sidebar_bg"], st.COLORS["danger"],
                     st.COLORS["sidebar_icon"], st.COLORS["white"])

        self._clock = tk.StringVar()
        tk.Label(sb, textvariable=self._clock, font=("Calibri",9),
                 bg=st.COLORS["sidebar_bg"], fg=st.COLORS["sidebar_icon"]
                 ).pack(pady=(4,10))
        self._tick()

    def _tick(self):
        self._clock.set(datetime.now().strftime("%a, %d %b %Y  %H:%M"))
        self.after(30000, self._tick)

    def _highlight_nav(self, key):
        for k, b in self._nav_btns.items():
            b.config(bg=st.COLORS["sidebar_active"] if k==key else st.COLORS["sidebar_bg"])

    def _switch(self, key):
        if self._current == key and key in self._frames:
            f = self._frames[key]
            if hasattr(f, "refresh"): f.refresh()
            return
        if self._current and self._current in self._frames:
            self._frames[self._current].grid_remove()
        if key not in self._frames:
            self._frames[key] = self._make_frame(key)
        f = self._frames[key]
        f.grid(row=0, column=0, sticky="nsew")
        if hasattr(f, "refresh"): f.refresh()
        self._current = key
        self._highlight_nav(key)

    def _make_frame(self, key):
        if key == "home":      return HomeFrame(self._content, self._username, self._switch)
        if key == "inventory": return _get_inv()(self._content, user_email=self._user_email)
        if key == "vendors":   return _get_vend()(self._content)
        if key == "purchases": return _get_purch()(self._content)
        if key == "billing":   return _get_bill()(self._content, user_email=self._user_email)
        if key == "expenses":  return _get_exp()(self._content)
        if key == "reports":   return _get_rep()(self._content)

    def _check_alerts(self):
        if self._user_email:
            import smtp_handler as smtp
            ls = db.get_low_stock_medicines()
            if ls: smtp.send_low_stock_alert(self._user_email, ls)
            ex = db.get_expired_medicines()
            if ex: smtp.send_expired_medicine_alert(self._user_email, ex)
        self.after(21_600_000, self._check_alerts)

    def _logout(self):
        if messagebox.askyesno("Logout", "Are you sure you want to logout?",
                               parent=self.winfo_toplevel()):
            self._on_logout()


class HomeFrame(tk.Frame):
    def __init__(self, parent, username, navigate):
        super().__init__(parent, bg=st.COLORS["background"])
        self._username = username
        self._navigate = navigate
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        self.columnconfigure(0, weight=1)

        # Banner
        banner = tk.Frame(self, bg=st.COLORS["primary_dark"])
        banner.grid(row=0, column=0, sticky="ew", padx=20, pady=(20,0))
        lb = tk.Frame(banner, bg=st.COLORS["primary_dark"])
        lb.pack(side="left", fill="y", padx=24, pady=16)
        hour = datetime.now().hour
        greet = "Good Morning" if hour<12 else "Good Afternoon" if hour<17 else "Good Evening"
        tk.Label(lb, text=f"{greet}, {self._username}!",
                 font=st.FONTS["heading"], bg=st.COLORS["primary_dark"],
                 fg=st.COLORS["white"]).pack(anchor="w")
        tk.Label(lb, text=datetime.now().strftime("Today is %A, %d %B %Y"),
                 font=st.FONTS["body"], bg=st.COLORS["primary_dark"],
                 fg=st.COLORS["sidebar_icon"]).pack(anchor="w")
        tk.Label(banner, text="✚", font=("Calibri",48),
                 bg=st.COLORS["primary_dark"], fg=st.COLORS["accent"]).pack(side="right", padx=24)

        # KPI cards
        cr = tk.Frame(self, bg=st.COLORS["background"])
        cr.grid(row=1, column=0, sticky="ew", padx=20, pady=16)
        for i in range(4): cr.columnconfigure(i, weight=1)

        self._card_vals = {}
        cards = [("💊","Total Medicines","total_medicines",st.COLORS["card_medicine"],"inventory"),
                 ("💰","Total Sales (₹)","total_sales",    st.COLORS["card_sales"],   "reports"),
                 ("⚡","Low Stock",      "low_stock_count", st.COLORS["card_low"],     "inventory"),
                 ("⚠","Expired",        "expired_count",   st.COLORS["card_expired"], "inventory")]
        for col, (icon, lbl, key, colour, nav) in enumerate(cards):
            val_lbl = self._make_card(cr, icon, lbl, colour, nav)
            self._card_vals[key] = val_lbl
            val_lbl.master.grid(row=0, column=col, padx=8, sticky="nsew")

        # Financial summary row
        fin = tk.Frame(self, bg=st.COLORS["background"])
        fin.grid(row=2, column=0, sticky="ew", padx=20, pady=(0,8))
        for i in range(5):
            fin.columnconfigure(i, weight=1)
        fin_cards = [
            ("📈","Revenue","fin_revenue", st.COLORS["card_sales"], "reports"),
            ("📉","COGS","fin_cogs", st.COLORS["card_low"], "reports"),
            ("💹","Gross Profit","fin_gross", st.COLORS["primary"], "reports"),
            ("💸","Expenses","fin_exp", st.COLORS["warning"], "expenses"),
            ("✅","Net Profit","fin_net", st.COLORS["primary_dark"], "reports"),
        ]
        for col, (icon, lbl, key, colour, nav) in enumerate(fin_cards):
            val_lbl = self._make_card(fin, icon, lbl, colour, nav)
            self._card_vals[key] = val_lbl
            val_lbl.master.grid(row=0, column=col, padx=6, sticky="nsew")

        # Expiring soon note
        self._exp_soon_var = tk.StringVar()
        tk.Label(self, textvariable=self._exp_soon_var, font=st.FONTS["body"],
                 bg=st.COLORS["background"], fg=st.COLORS["warning"],
                 anchor="w").grid(row=3, column=0, sticky="ew", padx=24, pady=(0,4))

        # Quick actions
        tk.Label(self, text="Quick Actions", font=st.FONTS["subheading"],
                 bg=st.COLORS["background"], fg=st.COLORS["text_dark"]
                 ).grid(row=4, column=0, sticky="w", padx=24, pady=(0,8))
        qa = tk.Frame(self, bg=st.COLORS["background"])
        qa.grid(row=5, column=0, sticky="ew", padx=20, pady=(0,16))
        for text, nav, style in [("+ Add Medicine","inventory",st.BUTTON["primary"]),
                                  ("📦 Add Stock","purchases",st.BUTTON["primary"]),
                                  ("🧾 New Bill",  "billing",  st.BUTTON["primary"]),
                                  ("📊 Reports",   "reports",  st.BUTTON["secondary"])]:
            b = tk.Button(qa, text=text, command=lambda n=nav: self._navigate(n), **style)
            b.pack(side="left", padx=(0,12))
            if style == st.BUTTON["primary"]:
                st.add_hover(b, st.COLORS["primary"], st.COLORS["primary_dark"])

        # Recent transactions
        tk.Label(self, text="Recent Transactions", font=st.FONTS["subheading"],
                 bg=st.COLORS["background"], fg=st.COLORS["text_dark"]
                 ).grid(row=6, column=0, sticky="w", padx=24, pady=(0,6))
        tf = tk.Frame(self, bg=st.COLORS["white"],
                      highlightbackground=st.COLORS["border"], highlightthickness=1)
        tf.grid(row=7, column=0, sticky="nsew", padx=20, pady=(0,20))
        self.rowconfigure(7, weight=1)
        tf.columnconfigure(0, weight=1); tf.rowconfigure(0, weight=1)

        from tkinter import ttk
        sty = ttk.Style()
        st.apply_treeview_style(sty, "Home.Treeview")
        cols = ("bill","date","customer","medicine","qty","total")
        self._tree = ttk.Treeview(tf, columns=cols, show="headings",
                                   style="Home.Treeview", selectmode="browse", height=8)
        for col, hd, w, anchor in [("bill","Bill No",120,"center"),
                                    ("date","Date",130,"center"),
                                    ("customer","Customer",140,"w"),
                                    ("medicine","Medicine",180,"w"),
                                    ("qty","Qty",60,"center"),
                                    ("total","Total (₹)",100,"center")]:
            self._tree.heading(col, text=hd)
            self._tree.column(col, width=w, anchor=anchor)
        vsb = ttk.Scrollbar(tf, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        self._tree.tag_configure("alt", background=st.COLORS["row_even"])

    def _make_card(self, parent, icon, label, colour, nav):
        card = tk.Frame(parent, bg=st.COLORS["white"],
                        highlightbackground=colour, highlightthickness=2, cursor="hand2")
        card.bind("<Button-1>", lambda e, n=nav: self._navigate(n))
        tk.Frame(card, bg=colour, height=5).pack(fill="x")
        inner = tk.Frame(card, bg=st.COLORS["white"])
        inner.pack(padx=16, pady=12, fill="both")
        tk.Label(inner, text=icon, font=("Calibri",26),
                 bg=st.COLORS["white"], fg=colour).pack(anchor="w")
        val = tk.Label(inner, text="—", font=st.FONTS["card_number"],
                       bg=st.COLORS["white"], fg=colour)
        val.pack(anchor="w")
        tk.Label(inner, text=label, font=st.FONTS["card_label"],
                 bg=st.COLORS["white"], fg=st.COLORS["text_light"]).pack(anchor="w")
        st.add_hover(card, st.COLORS["white"], st.COLORS["light_green"])
        for w in (card, inner):
            w.bind("<Button-1>", lambda e, n=nav: self._navigate(n))
        return val

    def refresh(self):
        stats = db.get_dashboard_stats()
        self._card_vals["total_medicines"].config(text=str(stats["total_medicines"]))
        self._card_vals["total_sales"].config(text=f"{stats['total_sales']:,.2f}")
        self._card_vals["low_stock_count"].config(text=str(stats["low_stock_count"]))
        self._card_vals["expired_count"].config(text=str(stats["expired_count"]))
        # financial (all-time for dashboard cards)
        from datetime import timedelta
        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=3650)).strftime("%Y-%m-%d")
        fin = db.get_financial_summary(start, end)
        self._card_vals["fin_revenue"].config(text=f"{fin['revenue']:,.0f}")
        self._card_vals["fin_cogs"].config(text=f"{fin['cogs']:,.0f}")
        self._card_vals["fin_gross"].config(text=f"{fin['gross_profit']:,.0f}")
        self._card_vals["fin_exp"].config(text=f"{fin['expenses']:,.0f}")
        self._card_vals["fin_net"].config(text=f"{fin['net_profit']:,.0f}")
        n = stats.get("expiring_soon", 0)
        self._exp_soon_var.set(
            f"⚡ {n} batch(es) expiring within 30 days" if n else "No batches expiring soon"
        )
        for r in self._tree.get_children():
            self._tree.delete(r)
        for i, t in enumerate(db.get_all_transactions()[:20]):
            self._tree.insert("","end", tags=("alt" if i%2==0 else "",),
                values=(t["bill_number"],t["transaction_date"][:16],
                        t["customer_name"],t["medicine_name"],
                        t["quantity"],f"₹{t['total_price']:.2f}"))