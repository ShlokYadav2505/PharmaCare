-- ============================================================
-- PharmaCare – run ENTIRE script in MySQL (recreates procedures)
-- Per-user data: medicines & transactions scoped by user_id
-- Includes Admin User Management (role: admin / user)
-- ============================================================

CREATE DATABASE IF NOT EXISTS pharmacy;
USE pharmacy;

CREATE TABLE IF NOT EXISTS users (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    username   VARCHAR(50)  UNIQUE NOT NULL,
    email      VARCHAR(100) UNIQUE NOT NULL,
    password   VARCHAR(64)  NOT NULL,
    role       VARCHAR(20)  NOT NULL DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- If upgrading existing DB without role column, run once:
-- ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'user';

-- Master catalog of standard medicines (for searchable dropdown)
CREATE TABLE IF NOT EXISTS medicine_catalog (
    id       INT AUTO_INCREMENT PRIMARY KEY,
    name     VARCHAR(100) UNIQUE NOT NULL,
    category VARCHAR(50) DEFAULT 'General'
);

CREATE TABLE IF NOT EXISTS medicines (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT NOT NULL DEFAULT 0,
    name        VARCHAR(100) NOT NULL,
    quantity    INT NOT NULL DEFAULT 0,
    price       DECIMAL(10,2) NOT NULL DEFAULT 0,
    expiry_date DATE NOT NULL,
    min_stock   INT NOT NULL DEFAULT 10,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS transactions (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    user_id          INT NOT NULL DEFAULT 0,
    bill_number      VARCHAR(50)  NOT NULL,
    medicine_id      INT NOT NULL,
    medicine_name    VARCHAR(100) NOT NULL,
    quantity         INT NOT NULL,
    unit_price       DECIMAL(10,2) NOT NULL,
    total_price      DECIMAL(10,2) NOT NULL,
    customer_name    VARCHAR(100) DEFAULT 'Walk-in Customer',
    transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (medicine_id) REFERENCES medicines(id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

DROP PROCEDURE IF EXISTS sp_create_user;
DROP PROCEDURE IF EXISTS sp_get_user_by_username;
DROP PROCEDURE IF EXISTS sp_get_user_by_email;
DROP PROCEDURE IF EXISTS sp_update_password;
DROP PROCEDURE IF EXISTS sp_get_all_users;
DROP PROCEDURE IF EXISTS sp_update_user;
DROP PROCEDURE IF EXISTS sp_delete_user;
DROP PROCEDURE IF EXISTS sp_get_catalog;
DROP PROCEDURE IF EXISTS sp_search_catalog;
DROP PROCEDURE IF EXISTS sp_add_medicine;
DROP PROCEDURE IF EXISTS sp_get_all_medicines;
DROP PROCEDURE IF EXISTS sp_get_medicine_by_id;
DROP PROCEDURE IF EXISTS sp_search_medicines;
DROP PROCEDURE IF EXISTS sp_update_medicine;
DROP PROCEDURE IF EXISTS sp_delete_medicine;
DROP PROCEDURE IF EXISTS sp_reduce_quantity;
DROP PROCEDURE IF EXISTS sp_get_low_stock;
DROP PROCEDURE IF EXISTS sp_get_expired;
DROP PROCEDURE IF EXISTS sp_add_transaction;
DROP PROCEDURE IF EXISTS sp_get_all_transactions;
DROP PROCEDURE IF EXISTS sp_get_transactions_by_date;
DROP PROCEDURE IF EXISTS sp_dashboard_stats;

DELIMITER //

CREATE PROCEDURE sp_create_user(
    IN p_username VARCHAR(50),
    IN p_email    VARCHAR(100),
    IN p_password VARCHAR(64)
)
BEGIN
    INSERT INTO users (username, email, password, role)
    VALUES (p_username, p_email, p_password, 'user');
END //

CREATE PROCEDURE sp_get_user_by_username(IN p_username VARCHAR(50))
BEGIN
    SELECT * FROM users WHERE username = p_username;
END //

CREATE PROCEDURE sp_get_user_by_email(IN p_email VARCHAR(100))
BEGIN
    SELECT * FROM users WHERE email = p_email;
END //

CREATE PROCEDURE sp_update_password(
    IN p_email    VARCHAR(100),
    IN p_password VARCHAR(64)
)
BEGIN
    UPDATE users SET password = p_password WHERE email = p_email;
END //

CREATE PROCEDURE sp_get_all_users()
BEGIN
    SELECT id, username, email, role, created_at
    FROM users
    ORDER BY username;
END //

CREATE PROCEDURE sp_update_user(
    IN p_id       INT,
    IN p_username VARCHAR(50),
    IN p_email    VARCHAR(100),
    IN p_role     VARCHAR(20)
)
BEGIN
    UPDATE users
    SET username = p_username,
        email    = p_email,
        role     = p_role
    WHERE id = p_id;
END //

CREATE PROCEDURE sp_delete_user(IN p_id INT)
BEGIN
    DELETE FROM users WHERE id = p_id;
END //

-- ── Medicine Catalog (master list for searchable dropdown) ───────────────────

CREATE PROCEDURE sp_get_catalog()
BEGIN
    SELECT id, name, category FROM medicine_catalog ORDER BY name;
END //

CREATE PROCEDURE sp_search_catalog(IN p_query VARCHAR(100))
BEGIN
    SELECT id, name, category FROM medicine_catalog
    WHERE name LIKE CONCAT('%', p_query, '%')
    ORDER BY name
    LIMIT 50;
END //

CREATE PROCEDURE sp_add_medicine(
    IN p_user_id  INT,
    IN p_name     VARCHAR(100),
    IN p_qty      INT,
    IN p_price    DECIMAL(10,2),
    IN p_expiry   DATE,
    IN p_min_stock INT
)
BEGIN
    INSERT INTO medicines (user_id, name, quantity, price, expiry_date, min_stock)
    VALUES (p_user_id, p_name, p_qty, p_price, p_expiry, p_min_stock);
END //

CREATE PROCEDURE sp_get_all_medicines(IN p_user_id INT)
BEGIN
    SELECT * FROM medicines WHERE user_id = p_user_id ORDER BY name;
END //

CREATE PROCEDURE sp_get_medicine_by_id(IN p_id INT, IN p_user_id INT)
BEGIN
    SELECT * FROM medicines WHERE id = p_id AND user_id = p_user_id;
END //

CREATE PROCEDURE sp_search_medicines(IN p_user_id INT, IN p_query VARCHAR(100))
BEGIN
    SELECT * FROM medicines
    WHERE user_id = p_user_id AND name LIKE CONCAT('%', p_query, '%')
    ORDER BY name;
END //

CREATE PROCEDURE sp_update_medicine(
    IN p_user_id  INT,
    IN p_id       INT,
    IN p_name     VARCHAR(100),
    IN p_qty      INT,
    IN p_price    DECIMAL(10,2),
    IN p_expiry   DATE,
    IN p_min_stock INT
)
BEGIN
    UPDATE medicines
    SET name = p_name, quantity = p_qty, price = p_price,
        expiry_date = p_expiry, min_stock = p_min_stock
    WHERE id = p_id AND user_id = p_user_id;
END //

CREATE PROCEDURE sp_delete_medicine(IN p_user_id INT, IN p_id INT)
BEGIN
    DELETE FROM medicines WHERE id = p_id AND user_id = p_user_id;
END //

CREATE PROCEDURE sp_reduce_quantity(IN p_user_id INT, IN p_id INT, IN p_amount INT)
BEGIN
    UPDATE medicines
    SET quantity = quantity - p_amount
    WHERE id = p_id AND user_id = p_user_id AND quantity >= p_amount;
END //

CREATE PROCEDURE sp_get_low_stock(IN p_user_id INT)
BEGIN
    SELECT * FROM medicines
    WHERE user_id = p_user_id AND quantity <= min_stock
    ORDER BY quantity;
END //

CREATE PROCEDURE sp_get_expired(IN p_user_id INT)
BEGIN
    SELECT * FROM medicines
    WHERE user_id = p_user_id AND expiry_date <= CURDATE()
    ORDER BY expiry_date;
END //

CREATE PROCEDURE sp_add_transaction(
    IN p_user_id  INT,
    IN p_bill     VARCHAR(50),
    IN p_med_id   INT,
    IN p_med_name VARCHAR(100),
    IN p_qty      INT,
    IN p_unit     DECIMAL(10,2),
    IN p_total    DECIMAL(10,2),
    IN p_customer VARCHAR(100)
)
BEGIN
    INSERT INTO transactions
        (user_id, bill_number, medicine_id, medicine_name, quantity,
         unit_price, total_price, customer_name)
    VALUES
        (p_user_id, p_bill, p_med_id, p_med_name, p_qty, p_unit, p_total, p_customer);
END //

CREATE PROCEDURE sp_get_all_transactions(IN p_user_id INT)
BEGIN
    SELECT * FROM transactions WHERE user_id = p_user_id
    ORDER BY transaction_date DESC;
END //

CREATE PROCEDURE sp_get_transactions_by_date(
    IN p_user_id INT,
    IN p_start DATE,
    IN p_end   DATE
)
BEGIN
    SELECT * FROM transactions
    WHERE user_id = p_user_id
      AND DATE(transaction_date) BETWEEN p_start AND p_end
    ORDER BY transaction_date DESC;
END //

CREATE PROCEDURE sp_dashboard_stats(IN p_user_id INT)
BEGIN
    SELECT
        (SELECT COUNT(*) FROM medicines WHERE user_id = p_user_id) AS total_medicines,
        (SELECT COALESCE(SUM(total_price), 0) FROM transactions WHERE user_id = p_user_id) AS total_sales,
        (SELECT COUNT(*) FROM medicines WHERE user_id = p_user_id AND quantity <= min_stock) AS low_stock_count,
        (SELECT COUNT(*) FROM medicines WHERE user_id = p_user_id AND expiry_date <= CURDATE()) AS expired_count,
        (SELECT COUNT(*) FROM transactions WHERE user_id = p_user_id) AS total_transactions;
END //

DELIMITER ;

-- ── Seed standard medicines into catalog (ignore duplicates) ─────────────────
INSERT IGNORE INTO medicine_catalog (name, category) VALUES
('Paracetamol 500mg', 'Analgesic'),
('Paracetamol 650mg', 'Analgesic'),
('Ibuprofen 400mg', 'Analgesic'),
('Aspirin 75mg', 'Analgesic'),
('Diclofenac 50mg', 'Analgesic'),
('Amoxicillin 250mg', 'Antibiotic'),
('Amoxicillin 500mg', 'Antibiotic'),
('Azithromycin 500mg', 'Antibiotic'),
('Ciprofloxacin 500mg', 'Antibiotic'),
('Metronidazole 400mg', 'Antibiotic'),
('Cefixime 200mg', 'Antibiotic'),
('Doxycycline 100mg', 'Antibiotic'),
('Cetirizine 10mg', 'Antihistamine'),
('Levocetirizine 5mg', 'Antihistamine'),
('Loratadine 10mg', 'Antihistamine'),
('Chlorpheniramine 4mg', 'Antihistamine'),
('Omeprazole 20mg', 'Antacid'),
('Pantoprazole 40mg', 'Antacid'),
('Ranitidine 150mg', 'Antacid'),
('Domperidone 10mg', 'Antiemetic'),
('Ondansetron 4mg', 'Antiemetic'),
('Metformin 500mg', 'Antidiabetic'),
('Glimepiride 1mg', 'Antidiabetic'),
('Glimepiride 2mg', 'Antidiabetic'),
('Amlodipine 5mg', 'Antihypertensive'),
('Atenolol 50mg', 'Antihypertensive'),
('Telmisartan 40mg', 'Antihypertensive'),
('Losartan 50mg', 'Antihypertensive'),
('Atorvastatin 10mg', 'Lipid Lowering'),
('Rosuvastatin 10mg', 'Lipid Lowering'),
('Salbutamol Inhaler', 'Respiratory'),
('Montelukast 10mg', 'Respiratory'),
('Dextromethorphan Syrup', 'Cough & Cold'),
('Ambroxol Syrup', 'Cough & Cold'),
('Phenylephrine Tablet', 'Cough & Cold'),
('ORS Powder', 'Rehydration'),
('Vitamin C 500mg', 'Vitamin'),
('Vitamin B Complex', 'Vitamin'),
('Calcium + Vitamin D3', 'Vitamin'),
('Iron Folic Acid', 'Vitamin'),
('Multivitamin Tablet', 'Vitamin'),
('Betadine Ointment', 'Topical'),
('Clotrimazole Cream', 'Topical'),
('Hydrocortisone Cream', 'Topical'),
('Povidone Iodine Solution', 'Antiseptic'),
('Hydrogen Peroxide', 'Antiseptic'),
('Dettol Antiseptic', 'Antiseptic'),
('Bandage Roll', 'First Aid'),
('Cotton Roll', 'First Aid'),
('Surgical Spirit', 'First Aid'),
('Crocin Advance', 'Analgesic'),
('Dolo 650', 'Analgesic'),
('Combiflam', 'Analgesic'),
('Vicks Vaporub', 'Cough & Cold'),
('Digene Tablet', 'Antacid'),
('Gelusil', 'Antacid'),
('Electral Powder', 'Rehydration'),
('Zincovit', 'Vitamin'),
('Shelcal 500', 'Vitamin'),
('Augmentin 625', 'Antibiotic'),
('Monocef O 200', 'Antibiotic'),
('Allegra 120', 'Antihistamine'),
('Montair LC', 'Respiratory'),
('Ascoril LS Syrup', 'Cough & Cold'),
('Benadryl Syrup', 'Cough & Cold');
