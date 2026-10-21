# styles.py - Simple shared colours, fonts and button styles for PharmaCare
# Kept plain for IB CS IA - easy to explain

COLORS = {
    "primary":         "#1B5E20",
    "primary_light":   "#2E7D32",
    "primary_dark":    "#1B5E20",
    "secondary":       "#E0E0E0",
    "light_green":     "#E8F5E9",
    "accent":          "#2E7D32",
    "background":      "#F0F0F0",
    "white":           "#FFFFFF",
    "card_bg":         "#FFFFFF",
    "entry_bg":        "#FFFFFF",
    "sidebar_bg":      "#1B5E20",
    "sidebar_hover":   "#2E7D32",
    "sidebar_active":  "#2E7D32",
    "sidebar_text":    "#FFFFFF",
    "sidebar_icon":    "#C8E6C9",
    "text_dark":       "#212121",
    "text_medium":     "#424242",
    "text_light":      "#757575",
    "text_white":      "#FFFFFF",
    "text_primary":    "#1B5E20",
    "danger":          "#C62828",
    "danger_light":    "#FFEBEE",
    "warning":         "#E65100",
    "success":         "#1B5E20",
    "table_header":    "#1B5E20",
    "table_header_fg": "#FFFFFF",
    "row_even":        "#F5F5F5",
    "row_odd":         "#FFFFFF",
    "row_select":      "#C8E6C9",
    "row_select_fg":   "#1B5E20",
    "border":          "#BDBDBD",
    "entry_border":    "#BDBDBD",
    "card_medicine":   "#1B5E20",
    "card_sales":      "#1B5E20",
    "card_low":        "#E65100",
    "card_expired":    "#C62828",
}

# All Arial - simple and consistent
FONTS = {
    "title":        ("Arial", 22, "bold"),
    "heading":      ("Arial", 16, "bold"),
    "subheading":   ("Arial", 13, "bold"),
    "body_large":   ("Arial", 12),
    "body":         ("Arial", 11),
    "body_bold":    ("Arial", 11, "bold"),
    "small":        ("Arial", 9),
    "small_bold":   ("Arial", 9, "bold"),
    "sidebar_item": ("Arial", 11),
    "card_number":  ("Arial", 20, "bold"),
    "card_label":   ("Arial", 10),
    "button":       ("Arial", 11, "bold"),
    "entry":        ("Arial", 11),
    "logo":         ("Arial", 16, "bold"),
    "tagline":      ("Arial", 9),
    "table_header": ("Arial", 10, "bold"),
    "table_body":   ("Arial", 10),
}

BUTTON = {
    "primary": {
        "bg": COLORS["primary"], "fg": COLORS["text_white"],
        "font": FONTS["button"], "relief": "raised", "cursor": "hand2",
        "padx": 14, "pady": 6, "bd": 1,
        "activebackground": COLORS["primary_light"],
        "activeforeground": COLORS["text_white"],
    },
    "secondary": {
        "bg": COLORS["secondary"], "fg": COLORS["text_dark"],
        "font": FONTS["button"], "relief": "raised", "cursor": "hand2",
        "padx": 12, "pady": 5, "bd": 1,
        "activebackground": "#BDBDBD",
        "activeforeground": COLORS["text_dark"],
    },
    "danger": {
        "bg": COLORS["danger"], "fg": COLORS["text_white"],
        "font": FONTS["button"], "relief": "raised", "cursor": "hand2",
        "padx": 14, "pady": 6, "bd": 1,
        "activebackground": "#B71C1C",
        "activeforeground": COLORS["text_white"],
    },
    "warning": {
        "bg": COLORS["warning"], "fg": COLORS["text_white"],
        "font": FONTS["button"], "relief": "raised", "cursor": "hand2",
        "padx": 14, "pady": 6, "bd": 1,
        "activebackground": "#BF360C",
        "activeforeground": COLORS["text_white"],
    },
    "sm_primary": {
        "bg": COLORS["primary"], "fg": COLORS["text_white"],
        "font": FONTS["small_bold"], "relief": "raised", "cursor": "hand2",
        "padx": 10, "pady": 4, "bd": 1,
        "activebackground": COLORS["primary_light"],
        "activeforeground": COLORS["text_white"],
    },
    "sm_danger": {
        "bg": COLORS["danger"], "fg": COLORS["text_white"],
        "font": FONTS["small_bold"], "relief": "raised", "cursor": "hand2",
        "padx": 10, "pady": 4, "bd": 1,
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
    "highlightthickness": 0,
    "insertbackground": COLORS["primary"],
}


def add_hover(widget, normal_bg, hover_bg, normal_fg=None, hover_fg=None):
    # Keep function so existing code does not break, but hover is optional/simple
    def on_enter(e):
        try:
            widget.config(bg=hover_bg)
            if hover_fg:
                widget.config(fg=hover_fg)
        except Exception:
            pass

    def on_leave(e):
        try:
            widget.config(bg=normal_bg)
            if normal_fg:
                widget.config(fg=normal_fg)
        except Exception:
            pass

    widget.bind("<Enter>", on_enter)
    widget.bind("<Leave>", on_leave)


def apply_treeview_style(style, tree_name="Custom.Treeview"):
    style.configure(
        tree_name,
        background=COLORS["row_odd"],
        foreground=COLORS["text_dark"],
        rowheight=26,
        fieldbackground=COLORS["row_odd"],
        font=FONTS["table_body"],
        borderwidth=1,
    )
    style.configure(
        f"{tree_name}.Heading",
        background=COLORS["table_header"],
        foreground=COLORS["table_header_fg"],
        font=FONTS["table_header"],
        relief="raised",
        padding=(6, 4),
    )
    style.map(
        tree_name,
        background=[("selected", COLORS["row_select"])],
        foreground=[("selected", COLORS["row_select_fg"])],
    )
    style.map(
        f"{tree_name}.Heading",
        background=[("active", COLORS["primary_light"])],
    )
    return tree_name
