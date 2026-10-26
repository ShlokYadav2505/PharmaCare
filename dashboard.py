import tkinter as tk
from tkinter import messagebox
from datetime import datetime
import database as db
import styles as st

_inv_cls = _bill_cls = _rep_cls = _vend_cls = _exp_cls = None

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

def _get_exp():
    global _exp_cls
    if not _exp_cls:
        from expenses import ExpensesFrame; _exp_cls = ExpensesFrame
    return _exp_cls

class DashboardApp(tk.Frame):
    NAV = [("🏠","Dashboard","home"),("💊","Inventory","inventory"),
           ("🏢","Vendors","vendors"),
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
        # App title
        tk.Label(
            sb, text="PharmaCare", font=st.FONTS["logo"],
            bg=st.COLORS["sidebar_bg"], fg=st.COLORS["white"]
        ).pack(fill="x", padx=16, pady=(20, 4), anchor="w")

        tk.Label(
            sb, text="Pharmacy Management System",
            font=st.FONTS["small"], bg=st.COLORS["sidebar_bg"],
            fg=st.COLORS["sidebar_icon"]
        ).pack(fill="x", padx=16, pady=(0, 16), anchor="w")

        tk.Label(
            sb, text=self._username, font=st.FONTS["body_bold"],
            bg=st.COLORS["sidebar_bg"], fg=st.COLORS["white"]
        ).pack(fill="x", padx=16, pady=(0, 12), anchor="w")

        # Main sections
        for icon, label, key in self.NAV:
            btn = tk.Button(
                sb, text=label, font=st.FONTS["sidebar_item"],
                bg=st.COLORS["sidebar_bg"], fg=st.COLORS["sidebar_text"],
                relief="flat", bd=0, cursor="hand2", padx=16, pady=10,
                anchor="w", activebackground=st.COLORS["sidebar_active"],
                activeforeground=st.COLORS["white"],
                command=lambda k=key: self._switch(k)
            )
            btn.pack(fill="x")
            st.add_hover(btn, st.COLORS["sidebar_bg"], st.COLORS["sidebar_hover"])
            self._nav_btns[key] = btn

        # Keep logout at the bottom
        tk.Frame(sb, bg=st.COLORS["sidebar_bg"]).pack(fill="both", expand=True)
        logout = tk.Button(
            sb, text="Logout", font=st.FONTS["sidebar_item"],
            bg=st.COLORS["sidebar_bg"], fg=st.COLORS["sidebar_text"],
            relief="flat", bd=0, cursor="hand2", padx=16, pady=10,
            anchor="w", command=self._logout
        )
        logout.pack(fill="x", pady=(0, 8))
        st.add_hover(logout, st.COLORS["sidebar_bg"], st.COLORS["danger"])

        self._clock = tk.StringVar()
        tk.Label(
            sb, textvariable=self._clock, font=st.FONTS["small"],
            bg=st.COLORS["sidebar_bg"], fg=st.COLORS["sidebar_icon"]
        ).pack(pady=(0, 10))
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
        if key == "vendors":   return _get_vend()(self._content, username=self._username)
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
        self.rowconfigure(4, weight=1)

        # Page heading
        heading = tk.Frame(self, bg=st.COLORS["background"])
        heading.grid(row=0, column=0, sticky="ew", padx=20, pady=(18, 10))

        tk.Label(
            heading, text="Dashboard", font=st.FONTS["title"],
            bg=st.COLORS["background"], fg=st.COLORS["text_dark"]
        ).pack(anchor="w")

        tk.Label(
            heading, text=datetime.now().strftime("%A, %d %B %Y"),
            font=st.FONTS["body"], bg=st.COLORS["background"],
            fg=st.COLORS["text_light"]
        ).pack(anchor="w", pady=(3, 0))

        # Summary values
        summary = tk.Frame(self, bg=st.COLORS["background"])
        summary.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 10))
        for col in range(3):
            summary.columnconfigure(col, weight=1)

        self._card_vals = {}
        cards = [
            ("Total Medicines", "total_medicines", st.COLORS["primary"], "inventory"),
            ("Total Sales (₹)", "total_sales", st.COLORS["primary"], "reports"),
            ("Low Stock", "low_stock_count", st.COLORS["warning"], "inventory"),
            ("Expired Medicines", "expired_count", st.COLORS["danger"], "inventory"),
            ("Revenue", "fin_revenue", st.COLORS["primary"], "reports"),
            ("Cost of Goods Sold", "fin_cogs", st.COLORS["primary"], "reports"),
            ("Gross Profit", "fin_gross", st.COLORS["primary"], "reports"),
            ("Operating Expenses", "fin_exp", st.COLORS["warning"], "expenses"),
            ("Net Operating Profit", "fin_net", st.COLORS["primary"], "reports"),
        ]

        for i, (label, key, colour, nav) in enumerate(cards):
            value_label = self._make_card(summary, label, colour, nav)
            value_label.master.grid(
                row=i // 3, column=i % 3, padx=5, pady=5, sticky="nsew"
            )
            self._card_vals[key] = value_label

        # Expiry warning
        self._exp_soon_var = tk.StringVar()
        tk.Label(
            self, textvariable=self._exp_soon_var, font=st.FONTS["body"],
            bg=st.COLORS["background"], fg=st.COLORS["warning"], anchor="w"
        ).grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 8))

        # Shortcuts
        actions = tk.Frame(self, bg=st.COLORS["background"])
        actions.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 10))
        tk.Label(
            actions, text="Quick Actions", font=st.FONTS["subheading"],
            bg=st.COLORS["background"], fg=st.COLORS["text_dark"]
        ).pack(side="left", padx=(0, 12))

        for label, nav in [
            ("Add Medicine", "inventory"),
            ("New Bill", "billing"),
            ("Reports", "reports"),
        ]:
            tk.Button(
                actions, text=label, command=lambda k=nav: self._navigate(k),
                **st.BUTTON["primary"]
            ).pack(side="left", padx=4)

        # Recent transactions
        tk.Label(
            self, text="Recent Transactions", font=st.FONTS["subheading"],
            bg=st.COLORS["background"], fg=st.COLORS["text_dark"]
        ).grid(row=4, column=0, sticky="w", padx=20, pady=(4, 6))

        table_frame = tk.Frame(self, bg=st.COLORS["white"])
        table_frame.grid(row=5, column=0, sticky="nsew", padx=20, pady=(0, 16))
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)
        self.rowconfigure(5, weight=1)

        from tkinter import ttk
        tree_style = ttk.Style()
        st.apply_treeview_style(tree_style, "Home.Treeview")

        columns = ("bill", "date", "customer", "medicine", "qty", "total")
        self._tree = ttk.Treeview(
            table_frame, columns=columns, show="headings",
            style="Home.Treeview", selectmode="browse", height=6
        )

        headings = [
            ("bill", "Bill No", 100, "center"),
            ("date", "Date", 140, "center"),
            ("customer", "Customer", 140, "w"),
            ("medicine", "Medicine", 180, "w"),
            ("qty", "Qty", 60, "center"),
            ("total", "Total (₹)", 100, "center"),
        ]
        for col, title, width, anchor in headings:
            self._tree.heading(col, text=title)
            self._tree.column(col, width=width, anchor=anchor)

        scrollbar = ttk.Scrollbar(
            table_frame, orient="vertical", command=self._tree.yview
        )
        self._tree.configure(yscrollcommand=scrollbar.set)
        self._tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        self._tree.tag_configure("alt", background=st.COLORS["row_even"])

    def _make_card(self, parent, label, colour, nav):
        card = tk.Frame(
            parent, bg=st.COLORS["white"],
            highlightbackground=st.COLORS["border"], highlightthickness=1
        )

        tk.Label(
            card, text=label, font=st.FONTS["body_bold"],
            bg=st.COLORS["white"], fg=st.COLORS["text_medium"]
        ).pack(anchor="w", padx=10, pady=(8, 2))

        value = tk.Label(
            card, text="—", font=st.FONTS["card_number"],
            bg=st.COLORS["white"], fg=colour
        )
        value.pack(anchor="w", padx=10, pady=(0, 8))

        for widget in (card, *card.winfo_children()):
            widget.bind("<Button-1>", lambda event, key=nav: self._navigate(key))

        return value

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
