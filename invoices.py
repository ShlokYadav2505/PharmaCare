"""Invoice history, detail views, and printing for PharmaCare."""
import os
import tempfile
import textwrap
import tkinter as tk
from html import escape
from tkinter import messagebox, ttk

import database as db
import styles as st


def _money(value):
    return f"₹{float(value or 0):,.2f}"


def _date(value):
    return value or "Not provided"


def _invoice_lines(invoice, kind):
    purchase = kind == "purchase"
    number = invoice.get("invoice_number", "")
    lines = [
        "PHARMACARE - PURCHASE INVOICE" if purchase else "PHARMACARE - SALES INVOICE",
        f"Invoice ID: {number}",
        f"Date: {invoice.get('purchase_date' if purchase else 'invoice_date', '')}",
    ]
    if purchase:
        lines.extend([
            f"Vendor: {invoice.get('vendor_name', '')} (ID: {invoice.get('vendor_id', '')})",
            f"Vendor contact: {invoice.get('vendor_contact') or '—'} | {invoice.get('vendor_phone') or '—'} | {invoice.get('vendor_email') or '—'}",
            f"Vendor address: {invoice.get('vendor_address') or '—'}",
            f"Pharmacy: {invoice.get('pharmacy_name') or 'PharmaCare'}",
            f"Pharmacist: {invoice.get('pharmacist_name') or '—'} | {invoice.get('pharmacist_email') or '—'}",
            f"Vendor invoice reference: {invoice.get('supplier_invoice_number') or '—'}",
        ])
    else:
        lines.extend([
            f"Pharmacy: {invoice.get('pharmacy_name') or 'PharmaCare'}",
            f"Pharmacist: {invoice.get('pharmacist_name') or '—'} | {invoice.get('pharmacist_email') or '—'}",
            f"Customer: {invoice.get('customer_name') or 'Walk-in Customer'}",
            f"Customer email: {invoice.get('customer_email') or '—'}",
            f"Customer address: {invoice.get('customer_address') or '—'}",
        ])

    lines.extend(["", "MEDICINE DETAILS"])
    for item in invoice.get("items", []):
        name = item.get("medicine_name") or item.get("invoice_medicine_name") or "Medicine"
        medicine_id = item.get("medicine_id", "—")
        batch = item.get("batch_number") or "—"
        mfg = _date(item.get("manufacture_date"))
        expiry = _date(item.get("expiry_date"))
        qty = int(item.get("quantity", 0) or 0)
        if purchase:
            unit_price = float(item.get("cost_price", 0) or 0)
            base = round(qty * unit_price, 2)
            tax = float(item.get("gst_amount", 0) or 0)
            lines.append(
                f"{name} | ID {medicine_id} | Batch {batch} | Mfg {mfg} | Exp {expiry}"
            )
            lines.append(
                f"  Qty {qty} x {_money(unit_price)} | Subtotal {_money(base)} | "
                f"GST {float(item.get('gst_rate', 0) or 0):g}% ({invoice.get('gst_mode', 'local')}) "
                f"{_money(tax)} | Line total {_money(base + tax)}"
            )
        else:
            unit_price = float(item.get("unit_price", 0) or 0)
            subtotal = round(qty * unit_price, 2)
            discount = float(item.get("discount_amount", 0) or 0)
            taxable = float(item.get("total_price", 0) or 0)
            tax = float(item.get("gst_amount", 0) or 0)
            lines.append(
                f"{name} | ID {medicine_id} | Batch {batch} | Mfg {mfg} | Exp {expiry}"
            )
            lines.append(
                f"  Qty {qty} x {_money(unit_price)} | Subtotal {_money(subtotal)} | "
                f"Discount {_money(discount)} | Taxable {_money(taxable)} | "
                f"GST {float(item.get('gst_rate', 0) or 0):g}% ({invoice.get('gst_mode', 'local')}) "
                f"{_money(tax)} | Line total {_money(taxable + tax)}"
            )

    lines.extend(["", "TAX AND TOTALS"])
    lines.append(f"Subtotal: {_money(invoice.get('subtotal'))}")
    if not purchase:
        lines.append(f"Discount: {_money(invoice.get('discount_amount'))}")
    lines.append(f"CGST: {_money(invoice.get('cgst_amount'))}")
    lines.append(f"SGST: {_money(invoice.get('sgst_amount'))}")
    lines.append(f"IGST: {_money(invoice.get('igst_amount'))}")
    lines.append(f"GST rate: {float(invoice.get('gst_rate', 0) or 0):g}% ({invoice.get('gst_mode', 'local')})")
    total = invoice.get("total_amount") if purchase else invoice.get("grand_total")
    lines.append(f"GRAND TOTAL: {_money(total)}")
    lines.append(f"Payment method: {invoice.get('payment_method') or '—'}")
    lines.append(f"Payment status: {invoice.get('payment_status') or '—'}")
    if purchase and invoice.get("notes"):
        lines.extend(["", f"Notes: {invoice['notes']}"])
    return lines


def invoice_email_html(invoice):
    """Build a detailed customer receipt email for a saved sales invoice."""
    rows = []
    for item in invoice.get("items", []):
        name = escape(item.get("invoice_medicine_name") or item.get("medicine_name") or "Medicine")
        qty = int(item.get("quantity", 0) or 0)
        amount = float(item.get("total_price", 0) or 0)
        tax = float(item.get("gst_amount", 0) or 0)
        rows.append(
            "<tr>"
            f"<td>{name}<br>Batch: {escape(item.get('batch_number') or '—')} | "
            f"Mfg: {escape(item.get('manufacture_date') or 'Not provided')} | "
            f"Exp: {escape(item.get('expiry_date') or 'Not provided')}</td>"
            f"<td>{qty}</td><td>{_money(item.get('unit_price'))}</td>"
            f"<td>{_money(item.get('discount_amount'))}</td>"
            f"<td>{_money(tax)}</td><td>{_money(amount + tax)}</td></tr>"
        )
    return (
        f"<h2>PharmaCare Sales Invoice</h2><p><b>Invoice:</b> {escape(invoice['invoice_number'])}</p>"
        f"<p><b>Date:</b> {escape(invoice.get('invoice_date', ''))} | "
        f"<b>Customer:</b> {escape(invoice.get('customer_name') or 'Walk-in Customer')}</p>"
        "<table border='1' cellpadding='6' cellspacing='0' style='border-collapse:collapse'>"
        "<tr><th>Medicine / Batch</th><th>Qty</th><th>Unit Price</th><th>Discount</th><th>GST</th><th>Total</th></tr>"
        + "".join(rows) + "</table>"
        f"<p>Subtotal: {_money(invoice.get('subtotal'))}<br>"
        f"Discount: {_money(invoice.get('discount_amount'))}<br>"
        f"CGST: {_money(invoice.get('cgst_amount'))}<br>"
        f"SGST: {_money(invoice.get('sgst_amount'))}<br>"
        f"IGST: {_money(invoice.get('igst_amount'))}<br>"
        f"<b>Grand Total: {_money(invoice.get('grand_total'))}</b><br>"
        f"Payment: {escape(invoice.get('payment_method') or '—')} / "
        f"{escape(invoice.get('payment_status') or '—')}</p>"
    )


def _pdf_safe(text):
    text = str(text).replace("₹", "INR ").replace("—", "-").replace("–", "-")
    return text.encode("latin-1", "replace").decode("latin-1")


def _pdf_escape(text):
    return _pdf_safe(text).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _write_print_document(invoice, path, kind):
    """Create the temporary print document used by the Print action."""
    wrapped = []
    for line in _invoice_lines(invoice, kind):
        wrapped.extend(textwrap.wrap(_pdf_safe(line), width=92) or [""])
    page_lines = [wrapped[i:i + 52] for i in range(0, len(wrapped), 52)] or [[]]

    objects = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }
    page_refs = []
    for index, lines in enumerate(page_lines):
        page_id = 4 + index * 2
        content_id = page_id + 1
        page_refs.append(f"{page_id} 0 R")
        commands = []
        y = 800
        for line in lines:
            commands.append(
                f"BT /F1 9 Tf 42 {y} Td ({_pdf_escape(line)}) Tj ET"
            )
            y -= 14
        stream = "\n".join(commands).encode("latin-1")
        objects[page_id] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>"
        ).encode("ascii")
        objects[content_id] = (
            f"<< /Length {len(stream)} >>\nstream\n".encode("ascii")
            + stream + b"\nendstream"
        )
    objects[2] = (
        f"<< /Type /Pages /Kids [{' '.join(page_refs)}] /Count {len(page_refs)} >>"
    ).encode("ascii")

    output = bytearray(b"%PDF-1.4\n%PharmaCare\n")
    offsets = [0] * (max(objects) + 1)
    for object_id in sorted(objects):
        offsets[object_id] = len(output)
        output.extend(f"{object_id} 0 obj\n".encode("ascii"))
        output.extend(objects[object_id])
        output.extend(b"\nendobj\n")
    xref_offset = len(output)
    output.extend(f"xref\n0 {len(offsets)}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.extend(
        f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    with open(path, "wb") as pdf:
        pdf.write(output)
    return path


class InvoiceDetailWindow(tk.Toplevel):
    def __init__(self, parent, invoice, kind):
        super().__init__(parent)
        self.invoice = invoice
        self.kind = kind
        self.title(f"Invoice {invoice.get('invoice_number', '')}")
        self.geometry("1050x650")
        self.minsize(820, 500)
        self.configure(bg=st.COLORS["background"])
        self._build()

    def _build(self):
        tk.Label(
            self, text=("Vendor Purchase Invoice" if self.kind == "purchase" else "Pharmacist Sales Invoice"),
            font=st.FONTS["heading"], bg=st.COLORS["background"],
            fg=st.COLORS["text_dark"]
        ).pack(anchor="w", padx=18, pady=(14, 4))
        details = tk.Text(self, height=8, wrap="word", font=st.FONTS["body"],
                          bg=st.COLORS["white"], relief="solid", bd=1)
        details.pack(fill="x", padx=18, pady=(4, 10))
        detail_lines = _invoice_lines(self.invoice, self.kind)
        details.insert("1.0", "\n".join(detail_lines[:8]))
        details.config(state="disabled")

        cols = (("medicine", "Medicine", 180), ("id", "ID", 55),
                ("batch", "Batch", 110), ("mfg", "Mfg Date", 95),
                ("expiry", "Expiry", 95), ("qty", "Qty", 55),
                ("unit", "Unit Price", 90), ("subtotal", "Subtotal", 95),
                ("discount", "Discount", 85), ("gst", "GST rate / amount", 130),
                ("total", "Line Total", 100))
        frame = tk.Frame(self, bg=st.COLORS["white"])
        frame.pack(fill="both", expand=True, padx=18, pady=(0, 10))
        tree = ttk.Treeview(frame, columns=[col[0] for col in cols], show="headings")
        for key, heading, width in cols:
            tree.heading(key, text=heading)
            tree.column(key, width=width, anchor="center", stretch=key == "medicine")
        for item in self.invoice.get("items", []):
            purchase = self.kind == "purchase"
            qty = int(item.get("quantity", 0) or 0)
            unit = float(item.get("cost_price" if purchase else "unit_price", 0) or 0)
            subtotal = round(qty * unit, 2)
            discount = 0.0 if purchase else float(item.get("discount_amount", 0) or 0)
            gst = float(item.get("gst_amount", 0) or 0)
            taxable = subtotal if purchase else float(item.get("total_price", 0) or 0)
            tree.insert("", "end", values=(
                item.get("medicine_name") or item.get("invoice_medicine_name") or "Medicine",
                item.get("medicine_id", "—"), item.get("batch_number") or "—",
                _date(item.get("manufacture_date")), _date(item.get("expiry_date")),
                qty, _money(unit), _money(subtotal), _money(discount),
                f"{float(item.get('gst_rate', 0) or 0):g}% / {_money(gst)}",
                _money(taxable + gst)
            ))
        yscroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        xscroll = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        total = self.invoice.get("total_amount") if self.kind == "purchase" else self.invoice.get("grand_total")
        discount = 0.0 if self.kind == "purchase" else self.invoice.get("discount_amount", 0)
        summary = (
            f"Subtotal: {_money(self.invoice.get('subtotal'))}    "
            f"Discount: {_money(discount)}    "
            f"CGST: {_money(self.invoice.get('cgst_amount'))}    "
            f"SGST: {_money(self.invoice.get('sgst_amount'))}    "
            f"IGST: {_money(self.invoice.get('igst_amount'))}\n"
            f"Grand Total: {_money(total)}    "
            f"Payment: {self.invoice.get('payment_method') or '—'} / "
            f"{self.invoice.get('payment_status') or '—'}"
        )
        tk.Label(self, text=summary, font=st.FONTS["body_bold"],
                 bg=st.COLORS["white"], fg=st.COLORS["text_dark"],
                 anchor="w", justify="left", wraplength=1000).pack(
            fill="x", padx=18, pady=(0, 10))

        actions = tk.Frame(self, bg=st.COLORS["background"])
        actions.pack(fill="x", padx=18, pady=(0, 14))
        tk.Button(actions, text="Print", command=self._print,
                  **st.BUTTON["primary"]).pack(side="left")
        tk.Button(actions, text="Close", command=self.destroy,
                  **st.BUTTON["secondary"]).pack(side="right")

    def _print(self):
        path = None
        try:
            fd, path = tempfile.mkstemp(prefix="pharmacare_invoice_", suffix=".pdf")
            os.close(fd)
            _write_print_document(self.invoice, path, self.kind)
            if os.name == "nt":
                os.startfile(path, "print")
            else:
                raise OSError("Printing invoices is supported from the Windows app.")
        except OSError as exc:
            messagebox.showerror("Print failed", str(exc), parent=self)


class InvoiceHistoryWindow(tk.Toplevel):
    def __init__(self, parent, kind):
        super().__init__(parent)
        self.kind = kind
        self.title("Purchase Invoice History" if kind == "purchase" else "Sales Invoice History")
        self.geometry("850x500")
        self.configure(bg=st.COLORS["background"])
        self._build()
        self.refresh()

    def _build(self):
        tk.Label(
            self, text=self.title(), font=st.FONTS["heading"],
            bg=st.COLORS["background"], fg=st.COLORS["text_dark"]
        ).pack(anchor="w", padx=18, pady=14)
        frame = tk.Frame(self, bg=st.COLORS["white"])
        frame.pack(fill="both", expand=True, padx=18, pady=(0, 10))
        self.tree = ttk.Treeview(frame, columns=("number", "date", "party", "total", "status"),
                                 show="headings", selectmode="browse")
        for key, label, width in (
            ("number", "Invoice ID", 230), ("date", "Date", 125),
            ("party", "Vendor / Customer", 200), ("total", "Grand Total", 130),
            ("status", "Payment Status", 130),
        ):
            self.tree.heading(key, text=label)
            self.tree.column(key, width=width, anchor="w" if key in ("number", "party") else "center")
        self.tree.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.tree.bind("<Double-1>", lambda _event: self._view())
        buttons = tk.Frame(self, bg=st.COLORS["background"])
        buttons.pack(fill="x", padx=18, pady=(0, 14))
        tk.Button(buttons, text="View selected", command=self._view,
                  **st.BUTTON["primary"]).pack(side="left")
        tk.Button(buttons, text="Close", command=self.destroy,
                  **st.BUTTON["secondary"]).pack(side="right")

    def refresh(self):
        for child in self.tree.get_children():
            self.tree.delete(child)
        rows = db.get_purchase_invoices() if self.kind == "purchase" else db.get_sales_invoices()
        for row in rows:
            if self.kind == "purchase":
                key, party, total = row["id"], row["vendor_name"], row["total_amount"]
            else:
                key, party, total = row["invoice_number"], row["customer_name"], row["grand_total"]
            self.tree.insert("", "end", iid=str(key), values=(
                row["invoice_number"],
                row["purchase_date"] if self.kind == "purchase" else row["invoice_date"],
                party, _money(total), row["payment_status"]
            ))

    def _view(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Select invoice", "Select an invoice to view.", parent=self)
            return
        key = selection[0]
        invoice = (db.get_purchase_invoice(int(key)) if self.kind == "purchase"
                   else db.get_sales_invoice(key))
        if not invoice:
            messagebox.showerror("Invoice unavailable", "The selected invoice could not be loaded.", parent=self)
            return
        InvoiceDetailWindow(self, invoice, self.kind)


def open_invoice(parent, kind, identifier):
    invoice = (db.get_purchase_invoice(int(identifier)) if kind == "purchase"
               else db.get_sales_invoice(identifier))
    if not invoice:
        messagebox.showerror("Invoice unavailable", "The selected invoice could not be loaded.", parent=parent)
        return
    return InvoiceDetailWindow(parent, invoice, kind)


def open_invoice_history(parent, kind):
    return InvoiceHistoryWindow(parent, kind)
