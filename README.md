# MegiLoka - Sistem Integrasi Retribusi & Promosi Wisata Pantura Lamongan

> **AI lokal terlatih (5 November 2026):** Tanya Megi kini memakai TF-IDF + regresi logistik untuk mengenali maksud pertanyaan, lalu membaca fakta wisata/event dari database. Training: `python backend/train_ai.py`. Pengujian aman: `python backend/run_tests.py`. Lihat [panduan training, hasil evaluasi, dan keterbatasan](docs/PANDUAN_AI_MEGI.md). Data awal kalender belum terverifikasi sebagai jadwal resmi; alur pembayaran masih simulasi.

![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue)
![Database](https://img.shields.io/badge/Database-MySQL_8.0-orange)
![Framework](https://img.shields.io/badge/Framework-Flask_SQLAlchemy-green)
![Status](https://img.shields.io/badge/Status-Production_Ready-brightgreen)

> **Instansi Fokus**: Dinas Pariwisata dan Kebudayaan Kabupaten Lamongan  
> **Filosofi Jargon**: Diserap dari jargon kebanggaan **"Megilan"** + **"Loka"** (Tempat/Destinasi Wisata).

---

## 📌 Deskripsi Sistem

**MegiLoka** adalah sistem informasi terpadu berbasis **Python** dan **MySQL** yang mencakup:
1. **E-Ticketing & Public Tourism Portal**: Reservasi tiket digital ber-QR Code untuk destinasi wisata daerah (Makam Sunan Drajat, Waduk Gondang, Maharani Zoo & Goa, Wisata Bahari Lamongan, Pantai Kutang, dll).
2. **POS (Point of Sale) Retribusi Loket**: Interface penerbitan tiket tunai/QRIS cepat bagi petugas pintu masuk.
3. **Gate Entrance QR Validator**: Pemindai keabsahan tiket menggunakan enkripsi **HMAC-SHA256** untuk mencegah tiket palsu dan kebocoran pemakaian berulang (*ticket re-use*).
4. **Dashboard Analytics & Rekapitutasi PAD**: Pelaporan Pendapatan Asli Daerah (PAD) terpusat secara real-time untuk pengawasan Dinas Pariwisata beserta ekspor laporan CSV/Excel.

---

## 🛠️ Tech Stack & Dependensi

* **Backend Logic**: Python 3.10+ & Flask Framework
* **ORM & Database Driver**: Flask-SQLAlchemy & PyMySQL
* **Database Target**: MySQL 8.0 / MariaDB (disertai SQLite fallback otomatis untuk pengujian instant)
* **QR Engine & Security**: Python `qrcode`, `Pillow`, `hmac`, `hashlib` (HMAC-SHA256)
* **Frontend UI**: HTML5, CSS3 Glassmorphism, Bootstrap 5, Chart.js, FontAwesome 6

---

## 📁 Struktur Direktori Proyek (Frontend & Backend)

```text
megiloka-retribusi-lamongan/
├── run.py                   # Script praktis untuk menjalankan aplikasi dari root
├── README.md
├── DAFTAR_FITUR_PER_ROLE.md
├── .gitignore
├── .env
├── .env.example
│
├── backend/                 # 📂 Core Backend (Python Flask, ORM & Database)
│   ├── app.py               # Aplikasi utama & API endpoints
│   ├── config.py            # Konfigurasi database & environment
│   ├── models.py            # Model SQLAlchemy ORM
│   ├── requirements.txt     # Dependensi Python
│   ├── megiloka.db          # Database SQLite lokal
│   ├── seed_references.py   # Seeder event & destinasi kalender 2026
│   ├── test_verification.py # Script pengujian otomatis
│   ├── database/
│   │   ├── schema.sql       # Script DDL MySQL 8.0
│   │   └── seed.sql         # Data awal destinasi & user demo
│   └── utils/
│       ├── __init__.py
│       ├── ai_service.py    # MegiBot AI Concierge & CS
│       └── qr_generator.py  # HMAC QR Generator & Validator
│
└── frontend/                # 📂 Core Frontend (HTML, CSS & JS)
    ├── css/
    │   └── style.css        # Theme CSS MegiLoka Glassmorphism
    ├── js/
    │   └── main.js          # Interaksi frontend, scanner sound, dll
    └── html/
        ├── base.html        # Layout utama & MegiBot AI Widget
        ├── index.html       # Beranda promosi wisata & spotlight event
        ├── destinations.html# Katalog & pencarian destinasi
        ├── destination_detail.html
        ├── booking.html     # Form reservasi e-ticket
        ├── ticket_view.html # Cetak e-ticket ber-QR Code
        ├── pos.html         # Point of Sale loket petugas
        ├── validator.html   # QR Scanner gerbang masuk
        ├── login.html       # Halaman login petugas/admin
        ├── calendar.html    # Kalender pariwisata 2026
        └── admin/
            ├── dashboard.html
            ├── pad_reports.html
            ├── destinations_crud.html
            └── hotels_crud.html
```

---

## 🚀 Panduan Installation & Setup Environment

### 1. Prasyarat System
- Python 3.10 atau versi lebih baru.
- MySQL Server 8.0 / MariaDB (atau SQLite bawaan).
- Git Client.

### 2. Setup Python Virtual Environment
```bash
# Clone repository
git clone https://github.com/username/megiloka-retribusi-lamongan.git
cd megiloka-retribusi-lamongan

# Buat virtual environment
python -m venv venv

# Aktifkan virtual environment (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Install dependency packages
pip install -r backend/requirements.txt
```

### 3. Konfigurasi Basis Data MySQL
1. Buka MySQL Client / phpMyAdmin / MySQL Workbench.
2. Buat database:
   ```sql
   CREATE DATABASE IF NOT EXISTS megiloka_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```
3. Salin file `.env.example` menjadi `.env` dan atur kredensial MySQL Anda:
   ```ini
   FLASK_ENV=development
   SECRET_KEY=megiloka_lamongan_megilan_secret_key_2026
   DB_TYPE=mysql
   DB_HOST=127.0.0.1
   DB_PORT=3306
   DB_USER=root
   DB_PASSWORD=password_mysql_anda
   DB_NAME=megiloka_db
   ```
4. Buat sembilan tabel dan tambahkan data contoh dari root proyek:
   ```powershell
   .\venv\Scripts\python.exe backend/seed_demo.py
   ```
   Untuk menyalin data lama saat database tujuan masih kosong, gunakan
   `backend/seed_demo.py --copy-sqlite backend/megiloka.db`. Menjalankan seeder demo
   berulang kali menggunakan kembali data contoh yang sudah ada.

   Pilih `DB_TYPE=sqlite` untuk menggunakan file lokal `backend/megiloka.db`.

### 4. Menjalankan Server Aplikasi
Anda dapat menjalankan server melalui salah satu opsi berikut:

**Opsi 1 (Melalui root project):**
```bash
python run.py
```

**Opsi 2 (Melalui folder backend):**
```bash
python backend/app.py
```
Akses sistem di browser melalui alamat: `http://127.0.0.1:5000`

### API promo dan event libur nasional

Isi `HOLIDAY_PARTNER_URL` di `.env` dengan URL HTTPS API pengelola. API
mengembalikan satu daftar JSON lengkap untuk periode yang dicakup. Parameter
ini opsional. Contoh respons (data ilustrasi):

```json
{
  "items": [
    {
      "id": "festival-akhir-tahun",
      "kind": "event",
      "title": "Festival Akhir Tahun",
      "starts_on": "2026-12-25",
      "ends_on": "2026-12-26",
      "status": "published",
      "url": "https://example.org/festival-akhir-tahun"
    }
  ]
}
```

Gunakan `event` atau `promo` untuk `kind` dan tanggal WIB berformat
`YYYY-MM-DD`. Pakai ID yang sama saat tanggal berubah. Untuk pembatalan,
kirim status `cancelled` atau `postponed`, atau keluarkan entri dari daftar
lengkap. Respons `{"items":[]}` berarti tidak ada pengumuman yang berlaku.

Server mengambil API setiap lima menit. Jika pengelola mendukung webhook,
isi `HOLIDAY_WEBHOOK_TOKEN` dengan token acak khusus integrasi dan mulai
ulang server. Setelah API pengelola memublikasikan perubahan, pengelola
mengirim `POST /api/agenda-libur/webhook` ke alamat HTTPS publik MegiLoka
dengan header `Authorization: Bearer <token>`. Respons `202` berarti
pembaruan masuk antrean. Jika menerima `429`, coba lagi setelah 10 detik.
MegiLoka mengambil rincian dari API pengelola dan mencocokkan tanggal
dengan jadwal libur nasional. Beranda terbuka meminta hasil terbaru
setiap 30 detik.

---

## 🔑 Akun Demo Petugas & Admin

| Role | Username | Password Default | Akses Fitur Utama |
| :--- | :--- | :--- | :--- |
| **Administrator Disparbud** | `admin` | `password123` | Full Access, Dashboard PAD, Master Data CRUD Destinasi |
| **Petugas Cashier Loket** | `kasir_drajat` | `password123` | POS Penjualan Tiket Masuk, Cetak E-Ticket Loket |
| **Petugas Gate Entrance** | `gate_drajat` | `password123` | Gate QR Scanner, Validasi HMAC Signature Tiket |

---

## 📤 Panduan Push Ke GitHub Repository Kelompok

```bash
# Inisialisasi Git dalam folder proyek
git init

# Tambahkan seluruh file proyek
git add .

# Buat commit pertama
git commit -m "feat: Initial commit MegiLoka E-Ticketing & PAD System Lamongan"

# Hubungkan dengan remote repository GitHub kelompok Anda
git remote add origin https://github.com/nama-kelompok/megiloka.git

# Ganti nama branch utama ke main dan push
git branch -M main
git push -u origin main
```

---

## 🛡️ Hak Cipta & Lisensi
Dikembangkan untuk **Dinas Pariwisata dan Kebudayaan Kabupaten Lamongan**.  
© 2026 Tim Pengembang MegiLoka.
