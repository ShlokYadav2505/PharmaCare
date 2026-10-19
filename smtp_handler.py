# smtp_handler.py - Email & OTP (edit SMTP_CONFIG before using email features)

import smtplib
import random
import string
import threading
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ── Edit these two values ────────────────────────────────────────────────────
SMTP_CONFIG = {
    "email":    "shlok.vyadav2508@gmail.com",       # Your Gmail address
    "password": "tola tpno ydtj eknj",     # 16-char Gmail App Password
    "server":   "smtp.gmail.com",
    "port":     587,
}

_otp_store = {}  # {email: {"otp": str, "expires": datetime}}


def generate_otp(length=6):
    return "".join(random.choices(string.digits, k=length))


def store_otp(email, otp, minutes=10):
    _otp_store[email.lower()] = {
        "otp": otp,
        "expires": datetime.now() + timedelta(minutes=minutes)
    }


def verify_otp(email, otp):
    key = email.lower()
    if key not in _otp_store:
        return False, "No OTP found. Request a new one."
    rec = _otp_store[key]
    if datetime.now() > rec["expires"]:
        del _otp_store[key]
        return False, "OTP expired. Request a new one."
    if rec["otp"] != otp.strip():
        return False, "Invalid OTP."
    del _otp_store[key]
    return True, "OTP verified."


def _send_raw(to, subject, html):
    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = SMTP_CONFIG["email"]
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(html, "html"))
        with smtplib.SMTP(SMTP_CONFIG["server"], SMTP_CONFIG["port"]) as s:
            s.ehlo()
            s.starttls()
            s.login(SMTP_CONFIG["email"], SMTP_CONFIG["password"])
            s.send_message(msg)
        return True, "Email sent."
    except smtplib.SMTPAuthenticationError:
        return False, "SMTP auth failed. Check credentials in smtp_handler.py."
    except Exception as e:
        return False, str(e)


def send_email_async(to, subject, html, callback=None):
    def worker():
        ok, msg = _send_raw(to, subject, html)
        if callback:
            callback(ok, msg)
    threading.Thread(target=worker, daemon=True).start()


def _wrap(body):
    return f"""<!DOCTYPE html><html><body style="font-family:Calibri,Arial,sans-serif;background:#E8F5E9;margin:0;padding:20px;">
    <div style="max-width:520px;margin:auto;background:#fff;border-radius:8px;overflow:hidden;">
      <div style="background:#1B5E20;padding:16px;text-align:center;">
        <h2 style="color:#fff;margin:0;">PharmaCare</h2>
      </div>
      <div style="padding:24px;">{body}</div>
      <div style="background:#F1F8E9;padding:10px;text-align:center;font-size:11px;color:#999;">
        Automated message – do not reply.
      </div>
    </div></body></html>"""


def send_otp_email(to_email, purpose="verification", callback=None):
    otp = generate_otp()
    store_otp(to_email, otp)
    body = f"""
      <h3 style="color:#2E7D32;">OTP for {purpose.title()}</h3>
      <p>Your One-Time Password:</p>
      <p style="font-size:32px;font-weight:bold;color:#2E7D32;letter-spacing:6px;text-align:center;">{otp}</p>
      <p style="color:#757575;font-size:13px;">Valid for 10 minutes. Do not share.</p>"""
    send_email_async(to_email, f"PharmaCare – OTP for {purpose.title()}", _wrap(body), callback)
    return otp


def send_low_stock_alert(to_email, medicines, callback=None):
    rows = "".join(
        f"<tr><td style='padding:8px;'>{dict(m)['name']}</td>"
        f"<td style='padding:8px;color:#E65100;font-weight:bold;'>{dict(m)['quantity']}</td>"
        f"<td style='padding:8px;'>{dict(m)['min_stock']}</td></tr>"
        for m in medicines)
    body = f"""
      <h3 style="color:#E65100;">Low Stock Alert</h3>
      <p>These medicines are at or below minimum stock:</p>
      <table style="width:100%;border-collapse:collapse;">
        <tr style="background:#E65100;color:#fff;"><th style="padding:8px;text-align:left;">Medicine</th>
          <th style="padding:8px;">Current</th><th style="padding:8px;">Min</th></tr>
        {rows}
      </table>"""
    send_email_async(to_email, "PharmaCare – Low Stock Alert", _wrap(body), callback)


def send_expired_medicine_alert(to_email, medicines, callback=None):
    rows = "".join(
        f"<tr><td style='padding:8px;'>{dict(m)['name']}</td>"
        f"<td style='padding:8px;color:#C62828;font-weight:bold;'>{dict(m)['expiry_date']}</td>"
        f"<td style='padding:8px;'>{dict(m)['quantity']}</td></tr>"
        for m in medicines)
    body = f"""
      <h3 style="color:#C62828;">Expired Medicine Alert</h3>
      <p>These medicines have expired:</p>
      <table style="width:100%;border-collapse:collapse;">
        <tr style="background:#C62828;color:#fff;"><th style="padding:8px;text-align:left;">Medicine</th>
          <th style="padding:8px;">Expiry</th><th style="padding:8px;">Stock</th></tr>
        {rows}
      </table>"""
    send_email_async(to_email, "PharmaCare – Expired Medicine Alert", _wrap(body), callback)


def send_welcome_email(to_email, username, callback=None):
    body = f"""
      <h3 style="color:#2E7D32;">Welcome, {username}!</h3>
      <p>Your PharmaCare account is ready. You can now manage inventory, billing, and reports.</p>"""
    send_email_async(to_email, "Welcome to PharmaCare!", _wrap(body), callback)


def send_bill_email(to_email, bill_no, customer, items, sub, disc, total, callback=None):
    """Email bill receipt to the logged-in pharmacy user."""
    rows = "".join(
        f"<tr><td style='padding:8px;'>{item['name']}</td>"
        f"<td style='padding:8px;text-align:center;'>{item['qty']}</td>"
        f"<td style='padding:8px;text-align:right;'>&#8377;{item['price']:.2f}</td>"
        f"<td style='padding:8px;text-align:right;'>&#8377;{item['total']:.2f}</td></tr>"
        for item in items)
    body = f"""
      <h3 style="color:#2E7D32;">Bill Receipt</h3>
      <p><strong>Bill No:</strong> {bill_no}<br>
         <strong>Customer:</strong> {customer}<br>
         <strong>Date:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
      <table style="width:100%;border-collapse:collapse;">
        <tr style="background:#2E7D32;color:#fff;">
          <th style="padding:8px;text-align:left;">Medicine</th>
          <th style="padding:8px;">Qty</th>
          <th style="padding:8px;">Price</th>
          <th style="padding:8px;">Total</th>
        </tr>
        {rows}
      </table>
      <p style="text-align:right;margin-top:12px;">
        Subtotal: &#8377;{sub:.2f}<br>
        Discount: &#8377;{disc:.2f}<br>
        <strong style="font-size:16px;">TOTAL: &#8377;{total:.2f}</strong>
      </p>"""
    send_email_async(to_email, f"PharmaCare – Bill {bill_no}", _wrap(body), callback)
