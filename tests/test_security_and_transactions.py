import hashlib
import tempfile
import unittest
from datetime import date
from pathlib import Path

import database as db
import smtp_handler as smtp
import vendor_system as vendors


class PharmaCareSecurityAndTransactionTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.original_db_path = db.DB_PATH
        db.DB_PATH = str(Path(self.temp_dir.name) / "pharmacy_test.db")
        self.addCleanup(setattr, db, "DB_PATH", self.original_db_path)
        db.initialize_database()
        vendors.initialize_vendor_system()

    @staticmethod
    def _create_user(username, email, password="StrongPassword123"):
        ok, message = db.create_user(username, email, password)
        if not ok:
            raise AssertionError(message)
        return db.get_user_by_email(email)["id"]

    def test_password_hash_is_salted_and_verifiable(self):
        first = db.hash_password("StrongPassword123")
        second = db.hash_password("StrongPassword123")
        self.assertNotEqual(first, second)
        self.assertTrue(db.verify_password(first, "StrongPassword123"))
        self.assertFalse(db.verify_password(first, "incorrect"))

    def test_login_upgrades_legacy_hash_and_uses_generic_error(self):
        user_id = self._create_user("legacy-user", "legacy@example.com")
        legacy_hash = hashlib.sha256(b"StrongPassword123").hexdigest()
        conn = db.get_connection()
        conn.execute("UPDATE users SET password=? WHERE id=?", (legacy_hash, user_id))
        conn.commit()
        conn.close()

        ok, _, username = db.validate_login("legacy@example.com", "StrongPassword123")
        self.assertTrue(ok)
        self.assertEqual(username, "legacy-user")
        upgraded = db.get_user_by_email("legacy@example.com")["password"]
        self.assertTrue(upgraded.startswith("pbkdf2_sha256$"))
        self.assertTrue(db.verify_password(upgraded, "StrongPassword123"))

        wrong = db.validate_login("legacy@example.com", "wrong-password")[1]
        unknown = db.validate_login("missing@example.com", "wrong-password")[1]
        self.assertEqual(wrong, "Invalid email or password.")
        self.assertEqual(unknown, wrong)

    def test_otp_has_a_five_attempt_limit(self):
        generated = smtp.generate_otp()
        self.assertEqual(len(generated), 6)
        self.assertTrue(generated.isdigit())
        smtp.clear_otp("person@example.com")
        smtp.store_otp("person@example.com", "123456")
        for _ in range(smtp.MAX_OTP_ATTEMPTS - 1):
            ok, _ = smtp.verify_otp("person@example.com", "000000")
            self.assertFalse(ok)
        ok, message = smtp.verify_otp("person@example.com", "000000")
        self.assertFalse(ok)
        self.assertIn("Too many", message)
        self.assertIn("No OTP found", smtp.verify_otp("person@example.com", "123456")[1])

    def test_missing_user_role_fails_closed(self):
        self.assertIsNone(vendors.get_user_role("not-a-user"))

    def test_vendor_registration_rolls_back_role_update(self):
        user_id = self._create_user("new-pharmacist", "new@example.com")
        conn = db.get_connection()
        conn.execute("""
            CREATE TRIGGER reject_vendor_profile BEFORE INSERT ON vendor_accounts
            BEGIN SELECT RAISE(ABORT, 'test rollback'); END
        """)
        conn.commit()
        conn.close()

        ok, _ = vendors.register_vendor_account(user_id, "Example Supplier")
        self.assertFalse(ok)
        self.assertEqual(vendors.get_user_role("new-pharmacist"), "pharmacist")

    def test_sales_invoice_uses_fefo_and_fixed_gst(self):
        user_id = self._create_user("pharmacist", "pharmacist@example.com")
        ok, message = db.add_medicine("Ibuprofen", 0, 10.0, "2030-01-01", 2)
        self.assertTrue(ok, message)
        medicine_id = db.get_all_medicines()[0]["id"]
        conn = db.get_connection()
        conn.executemany(
            """INSERT INTO batches
               (medicine_id,batch_number,quantity,cost_price,expiry_date,manufacture_date)
               VALUES (?,?,?,?,?,?)""",
            [
                (medicine_id, "EARLY", 2, 4.0, "2027-01-01", "2026-01-01"),
                (medicine_id, "LATE", 4, 5.0, "2028-01-01", "2026-01-01"),
            ],
        )
        db._sync_medicine_quantity(conn, medicine_id)
        conn.commit()
        conn.close()

        ok, message = db.record_bill(
            "SALE-TEST-1", "customer@example.com",
            [{"medicine_id": medicine_id, "name": "Ibuprofen", "qty": 4, "price": 10.0}],
            discount=2.0, user_id=user_id, customer_name="Test Customer",
        )
        self.assertTrue(ok, message)
        invoice = db.get_sales_invoice("SALE-TEST-1")
        self.assertEqual(invoice["gst_rate"], 12.0)
        self.assertEqual(invoice["gst_mode"], "local")
        self.assertAlmostEqual(invoice["grand_total"], 42.56)
        self.assertAlmostEqual(invoice["cgst_amount"] + invoice["sgst_amount"], 4.56)

        conn = db.get_connection()
        stock = conn.execute(
            "SELECT batch_number, quantity FROM batches WHERE medicine_id=? ORDER BY expiry_date",
            (medicine_id,),
        ).fetchall()
        conn.close()
        self.assertEqual(
            [(row["batch_number"], row["quantity"]) for row in stock],
            [("EARLY", 0), ("LATE", 2)],
        )

    def test_vendor_dispatch_creates_one_year_batch_and_purchase(self):
        pharmacist_id = self._create_user("pharmacist", "pharmacist@example.com")
        vendor_user_id = self._create_user("supplier", "supplier@example.com")
        ok, message = vendors.register_vendor_account(
            vendor_user_id, "Example Supplier", "Supplier Contact", "1234567890", "Address"
        )
        self.assertTrue(ok, message)
        vendor_id = vendors.get_vendor_for_user(vendor_user_id)["id"]
        manufacture_date = date.today().isoformat()
        expiry_date = vendors.expiry_one_year_after(manufacture_date)

        ok, message = vendors.add_catalog_item(
            vendor_id, "Paracetamol", "box", "25", "10", manufacture_date
        )
        self.assertTrue(ok, message)
        catalog_id = vendors.get_catalog(vendor_id)[0]["id"]
        ok, order_id = vendors.create_order(pharmacist_id, vendor_id, catalog_id, 3)
        self.assertTrue(ok)

        original_notify = vendors.send_pharmacist_dispatch_notification
        vendors.send_pharmacist_dispatch_notification = lambda _order_id: None
        self.addCleanup(setattr, vendors, "send_pharmacist_dispatch_notification", original_notify)
        self.assertTrue(vendors.transition_order(order_id, "confirm", "vendor", vendor_user_id)[0])
        self.assertTrue(vendors.transition_order(order_id, "dispatch", "vendor", vendor_user_id)[0])

        conn = db.get_connection()
        batch = conn.execute(
            "SELECT quantity, manufacture_date, expiry_date FROM batches"
        ).fetchone()
        purchase = conn.execute(
            "SELECT invoice_number, subtotal FROM purchases"
        ).fetchone()
        medicine = conn.execute("SELECT quantity FROM medicines").fetchone()
        conn.close()
        self.assertEqual(batch["quantity"], medicine["quantity"])
        self.assertEqual(batch["quantity"], 3)
        self.assertEqual(batch["manufacture_date"], manufacture_date)
        self.assertEqual(batch["expiry_date"], expiry_date)
        self.assertTrue(purchase["invoice_number"].startswith("PUR-PORTAL-"))
        self.assertAlmostEqual(purchase["subtotal"], 75.0)


if __name__ == "__main__":
    unittest.main()
