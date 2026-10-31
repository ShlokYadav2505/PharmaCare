# PharmaCare

IB Computer Science SL Internal Assessment — Pharmacy Management System.

## Database

PharmaCare uses SQLite through Python's built-in `sqlite3` module. The local `pharmacy.db` is created and migrated by `database.py` on startup. It is intentionally excluded from Git; each installation keeps its own user and pharmacy data. `database.py` is the source of truth for the schema and migrations.

**Before testing new code:** close PharmaCare and make a backup copy of `pharmacy.db`. Test changes against a copy first. Do not delete the original database.

## Run

1. Install Python 3.10 or newer.
2. Open a terminal in the project folder.
3. Run `python main.py`.

The UI uses Tkinter, which is included with many Python installations. The app and test suite use only the Python standard library. Run the automated tests with `python -m unittest discover -s tests -v`.

## Vendor workflow

1. Create a pharmacist account and verify the email OTP. Vendor registration is invite-only: set `PHARMACARE_VENDOR_INVITE_CODE` in the environment to enable Vendor signup, then share the code with the intended vendor.
2. Log in as the vendor and add medicine catalogue items with a unit, wholesale price, available quantity, and manufacturing date. Expiry is calculated as one year after manufacture.
3. Log out and sign in as a pharmacist.
4. Select an available catalogue item, enter an order quantity, and place the order. The system saves the order before attempting to send the email receipt.
5. Log back in as the vendor to confirm or reject a pending order, then mark a confirmed order as dispatched.
6. Dispatch records the purchase invoice and adds the supplied batch to pharmacy inventory. Purchase and sales invoices are available in Reports.

Use separate pharmacist and vendor accounts to demonstrate role-based access on one computer.

## Email configuration

Email uses environment variables; credentials should not be committed to the repository. In Windows PowerShell, set these for the current terminal session before launching the app:

```powershell
$env:PHARMACARE_EMAIL="your-address@gmail.com"
$env:PHARMACARE_EMAIL_PASSWORD="your-new-gmail-app-password"
python main.py
```

Optional settings: `PHARMACARE_SMTP_SERVER` (defaults to `smtp.gmail.com`), `PHARMACARE_SMTP_PORT` (defaults to `587`), and `PHARMACARE_VENDOR_INVITE_CODE` (unset by default, which disables public Vendor signup).

If email is not configured, account OTP verification and email receipts cannot be completed. Use a test email account and never commit an app password.

## Current implementation status

The vendor workflow is maintained on `feature/vendor-order-workflow`. Do not copy or commit a live `pharmacy.db`; test against a temporary database.
