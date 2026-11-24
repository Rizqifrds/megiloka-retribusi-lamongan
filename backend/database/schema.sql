-- =========================================================
-- MegiLoka Database Schema (MySQL 8.0 / MariaDB Compatible)
-- Sistem Integrasi Retribusi & Promosi Wisata Kab. Lamongan
-- Dinas Pariwisata dan Kebudayaan Kabupaten Lamongan
-- =========================================================

CREATE DATABASE IF NOT EXISTS `megiloka_db` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `megiloka_db`;

-- Drop tables if exists (Order handles Foreign Keys)
DROP TABLE IF EXISTS `promos`;
DROP TABLE IF EXISTS `hotels`;
DROP TABLE IF EXISTS `events`;
DROP TABLE IF EXISTS `pad_reports_recap`;
DROP TABLE IF EXISTS `tickets`;
DROP TABLE IF EXISTS `transactions`;
DROP TABLE IF EXISTS `visitor_accounts`;
DROP TABLE IF EXISTS `ticket_types`;
DROP TABLE IF EXISTS `users`;
DROP TABLE IF EXISTS `destinations`;

-- 1. Master Data Destinasi Wisata
CREATE TABLE `destinations` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `code` VARCHAR(20) NOT NULL UNIQUE,
    `name` VARCHAR(150) NOT NULL,
    `category` VARCHAR(50) NOT NULL DEFAULT 'Alam & Budaya',
    `location` VARCHAR(255) NOT NULL,
    `base_price` DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    `description` TEXT,
    `image_url` VARCHAR(255),
    `image_source_url` VARCHAR(500),
    `admission_status` VARCHAR(12) NOT NULL DEFAULT 'unknown',
    `admission_info` TEXT,
    `parking_info` TEXT,
    `source_url` VARCHAR(500),
    `ticket_url` VARCHAR(500),
    `opening_date` DATE NULL,
    `is_active` TINYINT(1) NOT NULL DEFAULT 1,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. Master Data Pengguna & Hak Akses (RBAC)
CREATE TABLE `users` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `username` VARCHAR(50) NOT NULL UNIQUE,
    `password_hash` VARCHAR(255) NOT NULL,
    `full_name` VARCHAR(100) NOT NULL,
    `role` ENUM('admin', 'cashier', 'gate_keeper') NOT NULL DEFAULT 'cashier',
    `destination_id` INT NULL,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`destination_id`) REFERENCES `destinations`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. Master Data Jenis Tiket & Retribusi per Destinasi
CREATE TABLE `ticket_types` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `destination_id` INT NOT NULL,
    `name` VARCHAR(100) NOT NULL,
    `price` DECIMAL(12, 2) NOT NULL,
    `description` VARCHAR(255),
    `is_active` BOOLEAN NOT NULL DEFAULT FALSE,
    `weekdays_mask` INT,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`destination_id`) REFERENCES `destinations`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. Log Transaksi Pembelian Tiket
CREATE TABLE `visitor_accounts` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `full_name` VARCHAR(100) NOT NULL,
    `login_name_key` VARCHAR(64),
    `phone` VARCHAR(16) NOT NULL UNIQUE,
    `password_hash` VARCHAR(255) NOT NULL,
    `session_token_hash` VARCHAR(64) UNIQUE,
    `session_expires_at` DATETIME,
    INDEX `ix_visitor_accounts_login_name_key` (`login_name_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `transactions` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `invoice_number` VARCHAR(50) NOT NULL UNIQUE,
    `destination_id` INT NOT NULL,
    `cashier_id` INT NULL,
    `visitor_account_id` INT NULL,
    `visitor_name` VARCHAR(100) NOT NULL,
    `visitor_phone` VARCHAR(30),
    `total_amount` DECIMAL(12, 2) NOT NULL,
    `payment_method` ENUM('cash', 'qris', 'transfer') NOT NULL DEFAULT 'cash',
    `payment_status` ENUM('paid', 'pending', 'cancelled') NOT NULL DEFAULT 'paid',
    `transaction_time` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `paid_at` DATETIME,
    FOREIGN KEY (`destination_id`) REFERENCES `destinations`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`cashier_id`) REFERENCES `users`(`id`) ON DELETE SET NULL,
    FOREIGN KEY (`visitor_account_id`) REFERENCES `visitor_accounts`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5. Tabel Detail Tiket QR & Verification Status
CREATE TABLE `tickets` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `transaction_id` INT NOT NULL,
    `ticket_type_id` INT NOT NULL,
    `ticket_code` VARCHAR(60) NOT NULL UNIQUE,
    `qr_hash` TEXT NOT NULL,
    `status` ENUM('valid', 'used', 'expired', 'cancelled') NOT NULL DEFAULT 'valid',
    `valid_for_date` DATE NOT NULL,
    `scanned_at` DATETIME NULL,
    `scanned_by_user_id` INT NULL,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`transaction_id`) REFERENCES `transactions`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`ticket_type_id`) REFERENCES `ticket_types`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`scanned_by_user_id`) REFERENCES `users`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 6. Tabel Rekapitulasi Pendapatan Asli Daerah (PAD)
CREATE TABLE `pad_reports_recap` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `destination_id` INT NOT NULL,
    `report_date` DATE NOT NULL,
    `total_tickets_sold` INT NOT NULL DEFAULT 0,
    `total_revenue` DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY `dest_date_unique` (`destination_id`, `report_date`),
    FOREIGN KEY (`destination_id`) REFERENCES `destinations`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 7. Master Data Kalender Event
CREATE TABLE `events` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `destination_id` INT NULL,
    `name` VARCHAR(150) NOT NULL,
    `description` TEXT,
    `event_date` DATE NOT NULL,
    `image_url` VARCHAR(255),
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`destination_id`) REFERENCES `destinations`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 8. Master Data Hotel
CREATE TABLE `hotels` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `destination_id` INT NOT NULL,
    `name` VARCHAR(150) NOT NULL,
    `location` VARCHAR(255) NOT NULL,
    `description` TEXT,
    `image_url` VARCHAR(255),
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`destination_id`) REFERENCES `destinations`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 9. Master Data Promo Hotel
CREATE TABLE `promos` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `hotel_id` INT NOT NULL,
    `name` VARCHAR(150) NOT NULL,
    `discount_percent` DECIMAL(5, 2),
    `discount_amount` DECIMAL(12, 2),
    `description` TEXT,
    `valid_from` DATE NOT NULL,
    `valid_until` DATE NOT NULL,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`hotel_id`) REFERENCES `hotels`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Indexing untuk optimasi query pelaporan PAD & scan tiket
CREATE INDEX idx_tickets_code ON `tickets`(`ticket_code`);
CREATE INDEX idx_tickets_status ON `tickets`(`status`);
CREATE INDEX idx_trans_date ON `transactions`(`transaction_time`);
CREATE INDEX idx_pad_date ON `pad_reports_recap`(`report_date`);


-- WhatsApp consent and per-event notification delivery state.
CREATE TABLE IF NOT EXISTS `whatsapp_subscriptions` (
    `phone` VARCHAR(15) PRIMARY KEY,
    `active` BOOLEAN NOT NULL,
    `changed_at` BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS `whatsapp_agenda_deliveries` (
    `phone` VARCHAR(15) NOT NULL,
    `event_key` VARCHAR(64) NOT NULL,
    `status` VARCHAR(16) NOT NULL,
    `created_at` DATETIME NOT NULL,
    PRIMARY KEY (`phone`, `event_key`),
    FOREIGN KEY (`phone`) REFERENCES `whatsapp_subscriptions`(`phone`) ON DELETE CASCADE
);
