COLORS = {
    "primary":         "#2E7D32",
    "primary_light":   "#43A047",
    "primary_dark":    "#1B5E20",
    "secondary":       "#81C784",
    "light_green":     "#E8F5E9",
    "accent":          "#00C853",
    "background":      "#F1F8E9",
    "white":           "#FFFFFF",
    "card_bg":         "#FFFFFF",
    "entry_bg":        "#FAFAFA",
    "sidebar_bg":      "#1B5E20",
    "sidebar_hover":   "#2E7D32",
    "sidebar_active":  "#43A047",
    "sidebar_text":    "#FFFFFF",
    "sidebar_icon":    "#A5D6A7",
    "text_dark":       "#1A1A2E",
    "text_medium":     "#424242",
    "text_light":      "#757575",
    "text_white":      "#FFFFFF",
    "text_primary":    "#2E7D32",
    "danger":          "#C62828",
    "danger_light":    "#FFEBEE",
    "warning":         "#E65100",
    "success":         "#1B5E20",
    "table_header":    "#2E7D32",
    "table_header_fg": "#FFFFFF",
    "row_even":        "#F9FBF9",
    "row_odd":         "#FFFFFF",
    "row_select":      "#C8E6C9",
    "row_select_fg":   "#1B5E20",
    "border":          "#E0E0E0",
    "entry_border":    "#C8E6C9",
    "card_medicine":   "#1565C0",
    "card_sales":      "#2E7D32",
    "card_low":        "#E65100",
    "card_expired":    "#C62828",
}

FONTS = {
    "title":        ("Calibri", 30, "bold"),
    "heading":      ("Calibri", 22, "bold"),
    "subheading":   ("Calibri", 16, "bold"),
    "body_large":   ("Calibri", 14),
    "body":         ("Calibri", 12),
    "body_bold":    ("Calibri", 12, "bold"),
    "small":        ("Calibri", 10),
    "small_bold":   ("Calibri", 10, "bold"),
    "sidebar_item": ("Calibri", 12),
    "card_number":  ("Calibri", 34, "bold"),
    "card_label":   ("Calibri", 11),
    "button":       ("Calibri", 12, "bold"),
    "entry":        ("Calibri", 12),
    "logo":         ("Calibri", 22, "bold"),
    "tagline":      ("Calibri", 10),
    "table_header": ("Calibri", 11, "bold"),
    "table_body":   ("Calibri", 11),
}

BUTTON = {
    "primary": {
        "bg": COLORS["primary"], "fg": COLORS["text_white"],
        "font": FONTS["button"], "relief": "flat", "cursor": "hand2",
        "padx": 24, "pady": 10, "bd": 0,
        "activebackground": COLORS["primary_dark"],
        "activeforeground": COLORS["text_white"],
    },
    "secondary": {
        "bg": COLORS["white"], "fg": COLORS["primary"],
        "font": FONTS["button"], "relief": "solid", "cursor": "hand2",
        "padx": 22, "pady": 9, "bd": 1,
        "activebackground": COLORS["light_green"],
        "activeforeground": COLORS["primary"],
    },
    "danger": {
        "bg": COLORS["danger"], "fg": COLORS["text_white"],
        "font": FONTS["button"], "relief": "flat", "cursor": "hand2",
        "padx": 24, "pady": 10, "bd": 0,
        "activebackground": "#B71C1C",
        "activeforeground": COLORS["text_white"],
    },
    "warning": {
        "bg": COLORS["warning"], "fg": COLORS["text_white"],
        "font": FONTS["button"], "relief": "flat", "cursor": "hand2",
        "padx": 24, "pady": 10, "bd": 0,
        "activebackground": "#BF360C",
        "activeforeground": COLORS["text_white"],
    },
    "sm_primary": {
        "bg": COLORS["primary"], "fg": COLORS["text_white"],
        "font": FONTS["small_bold"], "relief": "flat", "cursor": "hand2",
        "padx": 14, "pady": 6, "bd": 0,
        "activebackground": COLORS["primary_dark"],
        "activeforeground": COLORS["text_white"],
    },
    "sm_danger": {
        "bg": COLORS["danger"], "fg": COLORS["text_white"],
        "font": FONTS["small_bold"], "relief": "flat", "cursor": "hand2",
        "padx": 14, "pady": 6, "bd": 0,
        "activebackground": "#B71C1C",
        "activeforeground": COLORS["text_white"],
    },
    "link": {
        "bg": COLORS["white"], "fg": COLORS["primary"],
        "font": FONTS["small"], "relief": "flat", "cursor": "hand2",
        "padx": 0, "pady": 0, "bd": 0,
        "activebackground": COLORS["white"],
        "activeforeground": COLORS["primary_dark"],
    },
}

ENTRY = {
    "font": FONTS["entry"],
    "bg": COLORS["entry_bg"],
    "fg": COLORS["text_dark"],
    "relief": "solid", "bd": 1,
    "highlightthickness": 1,
    "highlightbackground": COLORS["entry_border"],
    "highlightcolor": COLORS["primary"],
    "insertbackground": COLORS["primary"],
}


def add_hover(widget, normal_bg, hover_bg, normal_fg=None, hover_fg=None):
    def on_enter(e):
        widget.config(bg=hover_bg)
        if hover_fg:
            widget.config(fg=hover_fg)
    def on_leave(e):
        widget.config(bg=normal_bg)
        if normal_fg:
            widget.config(fg=normal_fg)
    widget.bind("<Enter>", on_enter)
    widget.bind("<Leave>", on_leave)


def apply_treeview_style(style, tree_name="Custom.Treeview"):
    style.configure(tree_name,
        background=COLORS["row_odd"], foreground=COLORS["text_dark"],
        rowheight=30, fieldbackground=COLORS["row_odd"],
        font=FONTS["table_body"], borderwidth=0)
    style.configure(f"{tree_name}.Heading",
        background=COLORS["table_header"],
        foreground=COLORS["table_header_fg"],
        font=FONTS["table_header"], relief="flat", padding=(8, 6))
    style.map(tree_name,
        background=[("selected", COLORS["row_select"])],
        foreground=[("selected", COLORS["row_select_fg"])])
    style.map(f"{tree_name}.Heading",
        background=[("active", COLORS["primary_light"])])
    return tree_name