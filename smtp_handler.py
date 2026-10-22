import smtplib, random, string, threading, os
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Configure email outside source code. Never commit Gmail app passwords.
# Windows PowerShell example:
#   $env:PHARMACARE_EMAIL="your-address@gmail.com"
#   $env:PHARMACARE_EMAIL_PASSWORD="your-new-gmail-app-password"
SMTP_CONFIG = {
    "email": os.getenv("PHARMACARE_EMAIL", ""),
    "password": os.getenv("PHARMACARE_EMAIL_PASSWORD", ""),
    "smtp_server": os.getenv("PHARMACARE_SMTP_SERVER", "smtp.gmail.com"),
    "smtp_port": int(os.getenv("PHARMACARE_SMTP_PORT", "587")),
}

# In-memory OTP store: { email: {"otp": str, "expires": datetime} }
_otp_store = {}


# ── OTP Helpers ───────────────────────────────────────────────────────────────

def store_otp(email, otp, expiry_minutes=10):
    """Save OTP with expiry time."""
    _otp_store[email.lower()] = {
        "otp":     otp,
        "expires": datetime.now() + timedelta(minutes=expiry_minutes)
    }


def verify_otp(email, otp):
    """
    Verify OTP for the given email.
    Returns (success: bool, message: str).
    """
    key = email.lower()
    if key not in _otp_store:
        return False, "No OTP found. Please request a new one."
    record = _otp_store[key]
    if datetime.now() > record["expires"]:
        del _otp_store[key]
        return False, "OTP has expired. Please request a new one."
    if record["otp"] != otp.strip():
        return False, "Invalid OTP. Please try again."
    del _otp_store[key]
    return True, "OTP verified successfully."


def clear_otp(email):
    """Remove a stored OTP manually."""
    _otp_store.pop(email.lower(), None)


def _send_raw(to_email, subject, html_body):
    """Send one HTML email. Returns (success, message)."""
    try:
        if not SMTP_CONFIG["email"] or not SMTP_CONFIG["password"]:
            return False, "Email is not configured. Set PHARMACARE_EMAIL and PHARMACARE_EMAIL_PASSWORD environment variables."
        msg = MIMEMultipart("alternative")
        msg["From"]    = SMTP_CONFIG["email"]
        msg["To"]      = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(SMTP_CONFIG["smtp_server"], SMTP_CONFIG["smtp_port"]) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_CONFIG["email"], SMTP_CONFIG["password"])
            server.send_message(msg)

        return True, "Email sent successfully."
    except smtplib.SMTPAuthenticationError:
        return False, "SMTP auth failed. Check your email/password in smtp_handler.py."
    except smtplib.SMTPConnectError:
        return False, "Cannot connect to SMTP server. Check your internet."
    except smtplib.SMTPException as e:
        return False, f"SMTP error: {e}"
    except Exception as e:
        return False, f"Failed to send email: {e}"


# ── Core Email Sender ─────────────────────────────────────────────────────────

def send_email_async(to_email, subject, html_body, callback=None):
    """Send email in a background thread so the UI doesn't freeze."""
    def _worker():
        ok, msg = _send_raw(to_email, subject, html_body)
        if callback:
            callback(ok, msg)
    threading.Thread(target=_worker, daemon=True).start()


def _wrap(content):
    """Wrap email content in the PharmaCare branded HTML layout."""
    return f"""<!DOCTYPE html>
    <html>
    <body style="margin:0;padding:0;background:#E8F5E9;
                 font-family:Calibri,Arial,sans-serif;">
      <div style="max-width:580px;margin:30px auto;border-radius:10px;
                  overflow:hidden;box-shadow:0 4px 16px rgba(0,0,0,0.12);">

        <!-- Header -->
        <div style="background:#1B5E20;padding:20px 0 10px;text-align:center;">
          <h1 style="color:#fff;margin:0;font-size:28px;letter-spacing:2px;">
            &#128138; PharmaCare
          </h1>
          <p style="color:#A5D6A7;margin:4px 0 0;font-size:12px;">
            Professional Pharmacy Management System
          </p>
        </div>

        <!-- Body -->
        <div style="background:#ffffff;padding:32px 36px;">
          {content}
        </div>

        <!-- Footer -->
        <div style="background:#F1F8E9;padding:16px;text-align:center;">
          <p style="color:#9E9E9E;font-size:11px;margin:0;">
            &copy; PharmaCare &nbsp;|&nbsp;
            This is an automated message – please do not reply.
          </p>
        </div>

      </div>
    </body>
    </html>"""


# ── Email Template Wrapper ────────────────────────────────────────────────────

def send_otp_email(to_email, purpose="verification", callback=None):
    """Generate, store, and send an OTP email. Returns the OTP string."""
    otp = generate_otp()
    store_otp(to_email, otp)

    content = f"""
      <h2 style="color:#2E7D32;margin-top:0;">OTP {purpose.title()}</h2>
      <p style="color:#424242;">
        Your One-Time Password for <strong>{purpose}</strong> is:
      </p>
      <div style="text-align:center;background:#E8F5E9;border-radius:8px;
                  padding:24px;margin:20px 0;">
        <span style="font-size:40px;font-weight:bold;color:#2E7D32;
                     letter-spacing:10px;font-family:Courier New,monospace;">
          {otp}
        </span>
      </div>
      <p style="color:#757575;font-size:13px;">
        Valid for <strong>10 minutes</strong>.
        Do not share this OTP with anyone.
      </p>
    """
    send_email_async(
        to_email,
        f"PharmaCare – OTP for {purpose.title()}",
        _wrap(content),
        callback
    )
    return otp


# ── Public Email Functions ────────────────────────────────────────────────────

def send_low_stock_alert(to_email, medicines, callback=None):
    """Send a low-stock alert email listing all affected medicines."""
    rows = "".join(
        f"""<tr style="background:{'#F9FBF9' if i % 2 == 0 else '#ffffff'};">
              <td style="padding:10px 14px;">{dict(m)['name']}</td>
              <td style="padding:10px 14px;color:#E65100;font-weight:bold;">
                {dict(m)['quantity']}
              </td>
              <td style="padding:10px 14px;">{dict(m)['min_stock']}</td>
            </tr>"""
        for i, m in enumerate(medicines)
    )
    content = f"""
      <h2 style="color:#E65100;margin-top:0;">&#9888; Low Stock Alert</h2>
      <p style="color:#424242;">
        The following medicines are at or below their minimum stock level.
        Please reorder immediately.
      </p>
      <table style="width:100%;border-collapse:collapse;margin:16px 0;">
        <thead>
          <tr style="background:#E65100;color:#ffffff;">
            <th style="padding:12px 14px;text-align:left;">Medicine</th>
            <th style="padding:12px 14px;text-align:left;">Current Stock</th>
            <th style="padding:12px 14px;text-align:left;">Min Stock</th>
          </tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
    """
    send_email_async(
        to_email,
        "PharmaCare – Low Stock Alert",
        _wrap(content),
        callback
    )


def send_expired_medicine_alert(to_email, medicines, callback=None):
    """Send an expired-medicine alert email."""
    rows = "".join(
        f"""<tr style="background:{'#F9FBF9' if i % 2 == 0 else '#ffffff'};">
              <td style="padding:10px 14px;">{dict(m)['name']}</td>
              <td style="padding:10px 14px;color:#C62828;font-weight:bold;">
                {dict(m)['expiry_date']}
              </td>
              <td style="padding:10px 14px;">{dict(m)['quantity']}</td>
            </tr>"""
        for i, m in enumerate(medicines)
    )
    content = f"""
      <h2 style="color:#C62828;margin-top:0;">&#128680; Expired Medicine Alert</h2>
      <p style="color:#424242;">
        The following medicines have <strong>expired</strong> and must be
        removed from inventory immediately.
      </p>
      <table style="width:100%;border-collapse:collapse;margin:16px 0;">
        <thead>
          <tr style="background:#C62828;color:#ffffff;">
            <th style="padding:12px 14px;text-align:left;">Medicine</th>
            <th style="padding:12px 14px;text-align:left;">Expiry Date</th>
            <th style="padding:12px 14px;text-align:left;">Stock</th>
          </tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
    """
    send_email_async(
        to_email,
        "PharmaCare – Expired Medicine Alert",
        _wrap(content),
        callback
    )


def send_welcome_email(to_email, username, callback=None):
    """Send a welcome email after successful account creation."""
    content = f"""
      <h2 style="color:#2E7D32;margin-top:0;">Welcome to PharmaCare, {username}!</h2>
      <p style="color:#424242;">
        Your account has been created successfully.
        You can now log in and start managing your pharmacy.
      </p>
      <ul style="color:#424242;line-height:1.8;">
        <li>Track medicines and stock levels in real time</li>
        <li>Generate professional bills with receipts</li>
        <li>View detailed sales and inventory reports</li>
        <li>Get automatic low-stock &amp; expiry alerts by email</li>
      </ul>
      <p style="color:#757575;font-size:13px;margin-top:20px;">
        If you did not create this account, please contact support.
      </p>
    """
    send_email_async(
        to_email,
        "Welcome to PharmaCare!",
        _wrap(content),
        callback
    )


def generate_otp(length=6):
    """Generate a random 6-digit OTP."""
    return "".join(random.choices(string.digits, k=length))