-- =========================================================
-- MegiLoka Seed Data (Lamongan Tourist Destinations & Users)
-- Dinas Pariwisata dan Kebudayaan Kabupaten Lamongan
-- =========================================================

USE `megiloka_db`;

-- Password Default: 'password123' (Hash pbkdf2:sha256/werkzeug hash format)
-- Admin: admin / password123
-- Cashier: kasir_drajat / password123
-- Gate Keeper: gate_drajat / password123

-- 1. Insert Destinations
INSERT INTO `destinations` (`id`, `code`, `name`, `category`, `location`, `base_price`, `description`, `image_url`, `is_active`) VALUES
(1, 'DEST-SND', 'Makam Sunan Drajat', 'Wisata Religi & Sejarah', 'Kecamatan Paciran, Kab. Lamongan', 10000.00, 'Situs ziarah dan museum bersejarah Sunan Drajat, salah satu Walisongo penyebar agama Islam di Pantura Jawa.', 'https://images.unsplash.com/photo-1548625361-185b9826f634?auto=format&fit=crop&w=800&q=80', 1),
(2, 'DEST-WDG', 'Waduk Gondang', 'Wisata Alam & Edukasi', 'Kecamatan Sugio, Kab. Lamongan', 15000.00, 'Waduk buatan seluas 6.600 Ha yang indah dengan perahu wisata, taman bermain, dan pemandangan perbukitan hijau.', 'https://images.unsplash.com/photo-1506744038136-46273834b3fb?auto=format&fit=crop&w=800&q=80', 1),
(3, 'DEST-MZG', 'Maharani Zoo & Goa', 'Wisata Satwa & Geologi', 'Kecamatan Paciran, Kab. Lamongan', 35000.00, 'Kombinasi keindahan goa stalaktit/stalagmit alami dengan kebun binatang modern koleksi satwa terlengkap.', 'https://images.unsplash.com/photo-1534567153574-2b12153a87f0?auto=format&fit=crop&w=800&q=80', 1),
(4, 'DEST-WBL', 'Wisata Bahari Lamongan (WBL)', 'Taman Rekreasi Bahari', 'Kecamatan Paciran, Kab. Lamongan', 75000.00, 'Taman hiburan pesisir Pantura populer dengan puluhan wahana permainan modern, waterpark, dan wahana ekstrem.', 'https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=800&q=80', 1),
(5, 'DEST-KTG', 'Pantai Kutang', 'Wisata Pesisir & Mangrove', 'Desa Labuhan, Kec. Brondong, Kab. Lamongan', 10000.00, 'Destinasi wisata pantai ikonik dengan jembatan kayu melintasi hutan mangrove dan pemandangan matahari terbenam.', 'https://images.unsplash.com/photo-1519046904884-53103b34b206?auto=format&fit=crop&w=800&q=80', 1);

-- 2. Insert Users
INSERT INTO `users` (`id`, `username`, `password_hash`, `full_name`, `role`, `destination_id`) VALUES
(1, 'admin', 'scrypt:32768:8:1$uH2S5N7Y9xK1wP0L$2ef083c0ff569a941efdb0eef2a87eddbbb9d86b86ab6f8e77cbbca499bd142fa955bdad50d4eb0ec1d4ffbcbb7fcf6dbff6b14ea9ddb53c7a2efb3bf27498c0', 'Administrator Disparbud Lamongan', 'admin', NULL),
(2, 'kasir_drajat', 'scrypt:32768:8:1$uH2S5N7Y9xK1wP0L$2ef083c0ff569a941efdb0eef2a87eddbbb9d86b86ab6f8e77cbbca499bd142fa955bdad50d4eb0ec1d4ffbcbb7fcf6dbff6b14ea9ddb53c7a2efb3bf27498c0', 'Budi Loket Sunan Drajat', 'cashier', 1),
(3, 'gate_drajat', 'scrypt:32768:8:1$uH2S5N7Y9xK1wP0L$2ef083c0ff569a941efdb0eef2a87eddbbb9d86b86ab6f8e77cbbca499bd142fa955bdad50d4eb0ec1d4ffbcbb7fcf6dbff6b14ea9ddb53c7a2efb3bf27498c0', 'Siti Petugas Gate Drajat', 'gate_keeper', 1),
(4, 'kasir_gondang', 'scrypt:32768:8:1$uH2S5N7Y9xK1wP0L$2ef083c0ff569a941efdb0eef2a87eddbbb9d86b86ab6f8e77cbbca499bd142fa955bdad50d4eb0ec1d4ffbcbb7fcf6dbff6b14ea9ddb53c7a2efb3bf27498c0', 'Ahmad Kasir Gondang', 'cashier', 2);

-- 3. Insert Ticket Types
INSERT INTO `ticket_types` (`id`, `destination_id`, `name`, `price`, `description`) VALUES
(1, 1, 'Tiket Perorangan Dewasa', 10000.00, 'Retribusi pengunjung dewasa Makam Sunan Drajat'),
(2, 1, 'Tiket Perorangan Anak-Anak', 5000.00, 'Retribusi anak usia 3-10 tahun'),
(3, 1, 'Retribusi Parkir Bus / Rombongan', 25000.00, 'Retribusi kendaraan bus pariwisata'),
(4, 2, 'Tiket Pengunjung Dewasa', 15000.00, 'Retribusi masuk kawasan Waduk Gondang'),
(5, 2, 'Tiket Pengunjung Anak', 8000.00, 'Retribusi anak usia 3-10 tahun'),
(6, 3, 'Tiket Reguler Zoo & Goa', 35000.00, 'Tiket masuk Maharani Zoo & Goa'),
(7, 4, 'Tiket Terusan WBL', 75000.00, 'Tiket terusan seluruh wahana utama WBL'),
(8, 5, 'Tiket Masuk Pantai Kutang', 10000.00, 'Retribusi perorangan masuk jembatan mangrove');

-- 4. Sample Transactions
INSERT INTO `transactions` (`id`, `invoice_number`, `destination_id`, `cashier_id`, `visitor_name`, `visitor_phone`, `total_amount`, `payment_method`, `payment_status`, `transaction_time`) VALUES
(1, 'INV-20260901-001', 1, 2, 'Rahmat Hidayat', '081234567890', 25000.00, 'qris', 'paid', '2026-09-01 09:15:00'),
(2, 'INV-20260901-002', 2, 4, 'Dewi Lestari', '082198765432', 30000.00, 'cash', 'paid', '2026-09-01 10:30:00'),
(3, 'INV-20260902-001', 1, 2, 'Suryo Utomo', '085711223344', 45000.00, 'cash', 'paid', '2026-09-02 08:45:00');

-- 5. Sample Tickets
INSERT INTO `tickets` (`id`, `transaction_id`, `ticket_type_id`, `ticket_code`, `qr_hash`, `status`, `valid_for_date`, `scanned_at`, `scanned_by_user_id`, `created_at`) VALUES
(1, 1, 1, 'MGLK-SND-001', 'MGLK|MGLK-SND-001|1|2026-09-01|3a8f9c12b', 'used', '2026-09-01', '2026-09-01 09:30:00', 3, '2026-09-01 09:15:00'),
(2, 1, 1, 'MGLK-SND-002', 'MGLK|MGLK-SND-002|1|2026-09-01|5d7e1f48a', 'used', '2026-09-01', '2026-09-01 09:31:00', 3, '2026-09-01 09:15:00'),
(3, 1, 2, 'MGLK-SND-003', 'MGLK|MGLK-SND-003|1|2026-09-01|7c2a4b89e', 'valid', '2026-09-01', NULL, NULL, '2026-09-01 09:15:00'),
(4, 2, 4, 'MGLK-WDG-001', 'MGLK|MGLK-WDG-001|2|2026-09-01|9e1d5a32c', 'used', '2026-09-01', '2026-09-01 10:45:00', NULL, '2026-09-01 10:30:00'),
(5, 3, 1, 'MGLK-SND-004', 'MGLK|MGLK-SND-004|1|2026-09-02|1f4b8c92d', 'valid', '2026-09-02', NULL, NULL, '2026-09-02 08:45:00');

-- 6. Sample PAD Reports Recap
INSERT INTO `pad_reports_recap` (`destination_id`, `report_date`, `total_tickets_sold`, `total_revenue`) VALUES
(1, '2026-09-01', 120, 1450000.00),
(2, '2026-09-01', 85, 1275000.00),
(3, '2026-09-01', 210, 7350000.00),
(4, '2026-09-01', 350, 26250000.00),
(5, '2026-09-01', 95, 950000.00),
(1, '2026-09-02', 140, 1680000.00),
(2, '2026-09-02', 90, 1350000.00),
(3, '2026-09-02', 180, 6300000.00),
(4, '2026-09-02', 410, 30750000.00),
(5, '2026-09-02', 110, 1100000.00);
