# PharmaCare

IB Computer Science SL Internal Assessment — Pharmacy Management System.

## Database

PharmaCare currently uses SQLite through Python's built-in `sqlite3` module. The database is `pharmacy.db`, located beside the application files. The vendor workflow adds tables to this database when the app starts; it does not require MySQL.

**Before testing new code:** close PharmaCare and make a backup copy of `pharmacy.db`. Test changes against a copy first. Do not delete the original database.

## Run

1. Install Python 3.
2. Open a terminal in the project folder.
3. Run `python main.py`.

The UI uses Tkinter, which is included with many Python installations.

## Vendor workflow

1. Create an account and select **Vendor**. Enter the business name, then verify the email OTP.
2. Log in as the vendor and add medicine catalogue items with a unit, wholesale price, available quantity, and expiry date.
3. Log out and sign in as a pharmacist.
4. Select an available catalogue item, enter an order quantity, and place the order. The system saves the order before attempting to send the email receipt.
5. Log back in as the vendor to confirm or reject a pending order, then mark a confirmed order as dispatched.
6. Log in as the pharmacist and receive a dispatched order. Only receipt adds the supplied stock to the pharmacy inventory and creates batch/purchase records.

Use separate pharmacist and vendor accounts to demonstrate role-based access on one computer.

## Email configuration

Email uses environment variables; credentials should not be committed to the repository. In Windows PowerShell, set these for the current terminal session before launching the app:

```powershell
$env:PHARMACARE_EMAIL="your-address@gmail.com"
$env:PHARMACARE_EMAIL_PASSWORD="your-new-gmail-app-password"
python main.py
```

Optional settings: `PHARMACARE_SMTP_SERVER` (defaults to `smtp.gmail.com`) and `PHARMACARE_SMTP_PORT` (defaults to `587`).

If email is not configured, account OTP verification and email receipts cannot be completed. Use a test email account and never commit an app password.

## Current implementation status

The vendor workflow is under development on `feature/vendor-order-workflow`. Validate it with a copied database and test both account roles before merging it into `main`.
