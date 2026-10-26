# Shared colours and styles for the PharmaCare application.

COLORS = {
    "primary": "#2E7D32",
    "primary_light": "#388E3C",
    "primary_dark": "#2E7D32",
    "secondary": "#E0E0E0",
    "light_green": "#E8F5E9",
    "accent": "#43A047",
    "background": "#F5F5F5",
    "white": "#FFFFFF",
    "card_bg": "#FFFFFF",
    "entry_bg": "#FFFFFF",
    "sidebar_bg": "#2E7D32",
    "sidebar_hover": "#388E3C",
    "sidebar_active": "#1B5E20",
    "sidebar_text": "#FFFFFF",
    "sidebar_icon": "#E8F5E9",
    "text_dark": "#212121",
    "text_medium": "#424242",
    "text_light": "#757575",
    "text_white": "#FFFFFF",
    "text_primary": "#2E7D32",
    "danger": "#C62828",
    "danger_light": "#FFEBEE",
    "warning": "#E65100",
    "success": "#2E7D32",
    "table_header": "#2E7D32",
    "table_header_fg": "#FFFFFF",
    "row_even": "#F5F5F5",
    "row_odd": "#FFFFFF",
    "row_select": "#C8E6C9",
    "row_select_fg": "#1B5E20",
    "border": "#D0D0D0",
    "entry_border": "#D0D0D0",
    "card_medicine": "#2E7D32",
    "card_sales": "#2E7D32",
    "card_low": "#E65100",
    "card_expired": "#C62828",
}

FONTS = {
    "title": ("Arial", 20, "bold"),
    "heading": ("Arial", 16, "bold"),
    "subheading": ("Arial", 12, "bold"),
    "body_large": ("Arial", 12),
    "body": ("Arial", 10),
    "body_bold": ("Arial", 10, "bold"),
    "small": ("Arial", 9),
    "small_bold": ("Arial", 9, "bold"),
    "sidebar_item": ("Arial", 10),
    "card_number": ("Arial", 18, "bold"),
    "card_label": ("Arial", 10),
    "button": ("Arial", 10, "bold"),
    "entry": ("Arial", 10),
    "logo": ("Arial", 16, "bold"),
    "tagline": ("Arial", 9),
    "table_header": ("Arial", 10, "bold"),
    "table_body": ("Arial", 10),
}

BUTTON = {
    # Keep the platform's native Tk button appearance throughout the app.
    "primary": {"relief": "raised", "padx": 8, "pady": 3},
    "secondary": {"relief": "raised", "padx": 8, "pady": 3},
    "danger": {"relief": "raised", "padx": 8, "pady": 3},
    "warning": {"relief": "raised", "padx": 8, "pady": 3},
    "sm_primary": {"relief": "raised", "padx": 6, "pady": 2},
    "sm_danger": {"relief": "raised", "padx": 6, "pady": 2},
    "link": {"relief": "raised", "padx": 6, "pady": 2},
}

ENTRY = {}


def add_hover(widget, normal_bg, hover_bg, normal_fg=None, hover_fg=None):
    # Retain the existing sidebar hover behavior; content buttons stay native.
    if normal_bg != COLORS["sidebar_bg"]:
        return

    def on_enter(event):
        widget.config(bg=hover_bg)
        if hover_fg:
            widget.config(fg=hover_fg)

    def on_leave(event):
        widget.config(bg=normal_bg)
        if normal_fg:
            widget.config(fg=normal_fg)

    widget.bind("<Enter>", on_enter)
    widget.bind("<Leave>", on_leave)


def apply_treeview_style(style, tree_name="Custom.Treeview"):
    return "Treeview"
