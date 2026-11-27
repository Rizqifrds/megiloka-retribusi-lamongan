# 📋 Daftar Fitur Sistem dan Teknologi MegiLoka

> **Sistem Integrasi Retribusi, E-Ticketing, dan Promosi Wisata Kabupaten Lamongan**  
> **Dinas Pariwisata dan Kebudayaan (Disparbud) Kabupaten Lamongan**  
> *Dokumen Resmi Spesifikasi Fitur, Arsitektur Teknologi, dan Hak Akses Pengguna (Role-Based Access Control / RBAC)*

---

## 📌 1. Ikhtisar Sistem & Peran Pengguna (User Roles)

Sistem **MegiLoka** (MegiLoka Lamongan - Megilan) merupakan platform tata kelola pariwisata terpadu yang memadukan promosi pariwisata daerah Pantura, e-ticketing bagi wisatawan, loket Point of Sale (POS) cepat di pintu masuk, validasi tiket ber-QR Code dengan tanda tangan kriptografi anti-fraud, hingga dashboard eksekutif pemantauan Pendapatan Asli Daerah (PAD).

Sistem menerapkan **Role-Based Access Control (RBAC)** ketat untuk 4 peran pengguna:

1. **Publik / Wisatawan (`Guest / Public`)** – Pengunjung umum yang mengakses portal promosi, melihat event daerah, bertanya ke AI Concierge (MegiBot), menyaring katalog wisata multi-tag, dan memesan e-ticket secara mandiri.
2. **Petugas Loket / Kasir (`cashier`)** – Petugas operasional di gerbang masuk fisik yang melayani pembelian tiket retribusi tunai/QRIS secara instan di tempat (Point of Sale).
3. **Petugas Gate Entrance (`gate_keeper`)** – Petugas pintu masuk yang memvalidasi keabsahan QR code e-ticket pengunjung menggunakan kamera scanner atau barcode scanner gun untuk mencegah kebocoran tiket dan tiket ganda.
4. **Administrator Disparbud (`admin`)** – Pejabat dan staf pengelola Dinas Pariwisata dan Kebudayaan yang memegang kendali penuh atas master data destinasi, tiket, hotel, event, serta pengawasan PAD dan ekspor laporan keuangan.

---

## 🛠️ 2. Tumpukan Teknologi yang Digunakan (Technology Stack)

Sistem MegiLoka dibangun menggunakan teknologi modern yang andal, aman, dan ringan dengan rincian sebagai berikut:

### A. Backend & Logika Server
* **Bahasa Pemrograman**: **Python 3.10+ / 3.14** – Bahasa tingkat tinggi untuk pemrosesan data, autentikasi, dan logika bisnis.
* **Web Framework**: **Flask 3.0+** – Microframework WSGI yang cepat, fleksibel, dan modular untuk menangani routing, templating, dan REST API.
* **Templating Engine**: **Jinja2 (Built-in Flask)** – Rendering halaman sisi server (*Server-Side Rendering / SSR*) dengan *template inheritance*, makro, filter string/angka, dan modular komponen.
* **Object-Relational Mapping (ORM)**: **Flask-SQLAlchemy 3.1+ (SQLAlchemy 2.0 Core)** – Abstraksi basis data relasional berbasis objek dengan deklarasi model terstruktur, relasi one-to-many, lazy loading, dan *cascade deletion*.
* **Konfigurasi Lingkungan**: **python-dotenv 1.0+** – Manajemen variabel lingkungan rahasia (`.env`) seperti database URI, secret key, dan port server.

### B. Basis Data (Database Engine)
* **Dual-Engine Support**:
  * **SQLite 3 (`megiloka.db`)**: Mesin basis data lokal tanpa konfigurasi (*zero-configuration*) untuk pengujian cepat, portabilitas, dan pengembangan offline.
  * **MySQL 8.0+ / MariaDB via `PyMySQL 1.1+`**: Mesin basis data relasional enterprise untuk *production environment* dengan integritas referensial dan dukungan *high concurrency*.
  * **Fallback Otomatis**: Jika koneksi MySQL tidak tersedia, server secara cerdas beralih ke database SQLite lokal tanpa menghentikan layanan.

### C. Keamanan, Enkripsi & Kriptografi
* **Autentikasi & Password Hashing**: **Werkzeug Security (`generate_password_hash`, `check_password_hash`)** menggunakan metode derivasi kunci standar (PBKDF2 / scrypt).
* **Proteksi Akses Endpoint**: Custom Decorators Python (`@login_required`, `@role_required('admin', 'cashier', 'gate_keeper')`) untuk isolasi hak akses per sesi.
* **Tanda Tangan Digital Tiket (Anti-Fraud)**: **HMAC-SHA256 (Python `hmac` & `hashlib`)** – Setiap tiket menghasilkan tanda tangan digital yang di-encode ke dalam payload QR Code:
  $$\text{Payload} = \text{MGLK} \mid \text{TICKET\_CODE} \mid \text{DEST\_ID} \mid \text{VALID\_DATE} \mid \text{SEC\_HASH}$$
* **Pencegahan Tiket Ganda (*Anti-Replay / Anti-Reuse*)**: Status tiket transaksional (`valid` $\rightarrow$ `used`) dicatat dengan cap waktu (*timestamp*) dan identitas petugas scanner.

### D. QR Code & Pengolahan Gambar
* **Pustaka Pembuat QR**: **qrcode 7.4+** – Menghasilkan matriks QR Code secara dinamis berdasarkan data payload HMAC.
* **Manipulasi Citra**: **Pillow (PIL) 10.3+** – Konversi matriks QR Code ke format PNG dan encoding Base64 URI agar dapat dirender langsung di browser tanpa menyimpan file sampah di disk.

### E. Frontend & Antarmuka Pengguna (UI/UX)
* **CSS Framework**: **Bootstrap 5.3.2 (CDN)** – Sistem grid responsif (12-kolom), komponen UI (Cards, Badges, Modals, Toasts, Dropdowns, Collapse/Accordion).
* **Desain Kustom**: **Vanilla CSS3 (`static/css/style.css`)** – Mengusung tema identitas visual Kabupaten Lamongan:
  * Palet Warna: *Pantura Blue* (`#005B94`), *Megilan Teal* (`#00C9A7`), *Deep Navy* (`#0B1325`), dan aksen *Coral/Gold*.
  * Efek visual modern: *Glassmorphism*, *micro-interactions*, *pulse animation* pada status penting, dan tata letak *print-friendly* (`@media print`).
* **Ikonografi**: **FontAwesome 6.4.2 Free (CDN)** – Ikon vektor resolusi tinggi untuk seluruh navigasi, tombol aksi, dan penanda status.
* **Visualisasi Data Interaktif**: **Chart.js 4.x (CDN)** – Grafik analitik PAD (Bar Chart perbandingan pendapatan destinasi & Line Chart tren 7 hari terakhir).
* **JavaScript**: **Vanilla ES6+ (`static/js/main.js` & modul inline)** – Logika interaktif DOM, komunikasi API asinkron (*Fetch API*), audio synthesizer feedback, dan sinkronisasi filter query URL.
* **Audio Feedback Synthesizer**: **HTML5 Web Audio API** – Efek suara status pemindaian (*double beep* frekuensi 880Hz untuk sukses, *low buzz* frekuensi 220Hz untuk tiket ditolak/palsu).

### F. Kecerdasan Buatan & Basis Pengetahuan (AI Concierge)
* **Modul AI Cerdas**: `backend/ai/concierge.py` menjawab pertanyaan wisatawan. `backend/ai/content_publisher.py` memproses permintaan publikasi dari petugas.
* **Arsitektur Pemrosesan AI**:
  * *Keyword Matching & Intent Recognition*: Mengenali pertanyaan seputar tiket, kuliner khas (Soto, Nasi Boran, Wingko Babat), akomodasi, dan rute.
  * *Official Knowledge Base Integration*: Terintegrasi dengan **94 Agenda Kalender Event Resmi Bapperida Kabupaten Lamongan 2026** dan **32 Destinasi Wisata Pilihan (Kompas & TripAdvisor)**.
  * *Auto-Publisher Engine*: Otomasi penerbitan destinasi dan event baru ke database secara instan dalam rentang waktu besok (H-1), 1 bulan (H-30), hingga 1 tahun ke depan.

### G. Pelaporan & Ekspor Data
* **Format Ekspor**: **CSV (Comma-Separated Values) / Excel-Compatible** – Dibuat secara streaming menggunakan pustaka standar Python `csv` dan `io.StringIO` dengan encoding UTF-8 BOM untuk kompatibilitas penuh Microsoft Excel.

---

## 📊 3. Matriks Hak Akses Fitur (Permission Matrix)

| Modul / Fitur | Publik (Guest) | Kasir (`cashier`) | Gate Keeper (`gate_keeper`) | Admin Disparbud (`admin`) |
| :--- | :---: | :---: | :---: | :---: |
| **Katalog & Promosi Wisata** | ✅ | ✅ | ✅ | ✅ |
| **Navigasi Kelompok & Multi-Tag Filter** | ✅ | ✅ | ✅ | ✅ |
| **Kalender Event Pariwisata Daerah** | ✅ | ✅ | ✅ | ✅ |
| **Section Spotlight Agenda H-1 & H-30** | ✅ | ✅ | ✅ | ✅ |
| **Lonceng & Toast Notifikasi Wisatawan** | ✅ | ✅ | ✅ | ✅ |
| **AI CS Concierge & Auto-Publisher (MegiBot)** | ✅ | ✅ | ✅ | ✅ |
| **Pemesanan E-Ticket Mandiri** | ✅ | ✅ | ✅ | ✅ |
| **Lihat & Cetak E-Ticket (QR Code)** | ✅ (Milik Sendiri) | ✅ | ✅ | ✅ |
| **Login Petugas & Sesi Terproteksi** | ❌ | ✅ | ✅ | ✅ |
| **Point of Sale (POS) Retribusi Loket Cepat** | ❌ | ✅ | ❌ | ✅ |
| **Gate Entrance QR Validator (Scanner)** | ❌ | ✅ | ✅ | ✅ |
| **API Validasi Kriptografi HMAC QR Code** | ❌ | ✅ | ✅ | ✅ |
| **Dashboard Analytics & KPI PAD** | ❌ | ❌ | ❌ | ✅ |
| **AI Insights & Prediksi Tren PAD** | ❌ | ❌ | ❌ | ✅ |
| **Laporan & Rekapitulasi PAD Terpusat** | ❌ | ❌ | ❌ | ✅ |
| **Ekspor Laporan PAD (CSV/Excel)** | ❌ | ❌ | ❌ | ✅ |
| **CRUD Destinasi Wisata** | ❌ | ❌ | ❌ | ✅ |
| **CRUD Kategori & Tarif Tiket** | ❌ | ❌ | ❌ | ✅ |
| **CRUD Hotel & Promo Rekanan** | ❌ | ❌ | ❌ | ✅ |
| **CRUD Kalender Event Pariwisata** | ❌ | ❌ | ❌ | ✅ |

---

## 🔍 4. Rincian Fitur Lengkap Berdasarkan Role

---

### 🌐 4.1. Role: Publik / Wisatawan (Guest)
*Pengunjung umum tanpa kewajiban autentikasi akun.*

#### A. Eksplorasi & Promosi Wisata Pantura
* **Landing Page Interaktif (`/`)**:
  * Menampilkan etalase destinasi wisata unggulan di Kabupaten Lamongan.
  * **⚡ Section Spotlight Agenda & Destinasi Segera Hadir (H-1 & H-30)**:
    * Menampilkan kartu acara & destinasi baru yang berjarak **1 hari sebelum berlangsung (H-1 Besok!)** dengan badge merah beranimasi *urgent pulse*.
    * Menampilkan acara & destinasi yang berjarak **1 bulan sebelum berlangsung (H-30)** dengan badge biru/cyan.
    * Daftar agenda mendatang dalam rentang 1 bulan hingga 1 tahun ke depan.
    * Widget ringkasan total destinasi terdaftar, event kalender, dan promo akomodasi hotel rekanan.
* **🔔 Sistem Notifikasi Pengunjung (Guest Notification System)**:
  * **Lonceng Notifikasi di Navbar**: Dilengkapi badge counter merah yang menghitung jumlah agenda H-1 & H-30 yang aktif.
  * **Dropdown Notifikasi Wisatawan**: Menampilkan rincian agenda terdekat tanpa perlu login.
  * **Floating Toast Alert**: Banner pop-up interaktif di sudut layar yang memberitahu pengunjung tentang agenda yang akan berlangsung besok dan bulan depan.
  * **Pembaruan Real-Time**: Lonceng notifikasi ter-update secara otomatis saat AI menerbitkan agenda baru.
* **🤖 Asisten Cerdas AI Customer Service (MegiBot) & Auto-Publisher**:
  * Widget interaktif floating chat di sudut kanan bawah layar.
  * Menjawab pertanyaan wisatawan seputar info tiket, rute, kuliner (Soto Lamongan, Tahu Campur, Nasi Boran), dan daya tarik wisata.
  * **Auto-Publisher Event & Destinasi**: AI dapat langsung mengeksekusi penambahan event dan lokasi baru ke database dalam rentang 1 hari (H-1), 1 bulan (H-30), hingga 1 tahun ke depan.
  * Terintegrasi dengan basis data **94 Kalender Event Resmi Bapperida Lamongan 2026** dan **32 Tempat Wisata Lamongan (Kompas & TripAdvisor)**.
* **Katalog Destinasi, Pengelompokan & Filter Multi-Tag Cerdas (`/destinations`)**:
  * **Sistem Navigasi Kelompok Wisata (Primary Group Tabs)**: Mengelompokkan 20+ kategori menjadi 5 kluster utama yang rapi dan tidak bertumpuk (*Bahari & Pesisir*, *Religi & Cagar Budaya*, *Alam & Konservasi*, *Taman Rekreasi & Keluarga*, *Edukasi & Museum*) lengkap dengan badge jumlah destinasi.
  * **Fitur Filter Multi-Tag (Bisa Memilih Lebih Dari 1 Tag)**: Wisatawan dapat memilih/mencentang beberapa tag sekaligus (misalnya kombinasi *Wisata Bahari* dan *Wisata Religi*) melalui drawer filter multi-select yang terorganisir per kelompok.
  * **Active Filter Chips & Reset Instan**: Menampilkan bar status tag yang sedang aktif dengan tombol hapus tag individual (`✕`), penghitung hasil pencarian yang cocok, serta tombol reset cepat.
  * **Pencarian Cerdas**: Pencarian real-time berdasarkan kata kunci nama destinasi, deskripsi, maupun lokasi kecamatan.
* **Halaman Detail Destinasi (`/destinations/<id>`)**:
  * Galeri foto resolusi tinggi dan deskripsi mendalam sejarah/fasilitas.
  * Informasi lokasi geografis dan rincian variasi harga tiket masuk.
  * Tombol aksi langsung menuju reservasi online.
* **Kalender Event Wisata Terpadu (`/calendar`)**:
  * Jadwal event festival budaya, seni, dan agenda daerah Lamongan sepanjang tahun.

#### B. Reservasi E-Ticketing Mandiri
* **Formulir E-Booking Tiket (`/booking/<dest_id>`)**:
  * Pemilihan tanggal kunjungan yang fleksibel.
  * Pemilihan variasi tipe tiket (Dewasa, Anak-anak, Tiket Terusan, dll) dalam satu transaksi.
  * Kalkulasi dinamis total biaya tiket di sisi formulir.
  * Pilihan metode pembayaran modern (QRIS, Transfer Bank, Tunai).
* **Penerbitan Invoice & E-Ticket Digital (`/tickets/<invoice_number>`)**:
  * Nomor faktur unik terstruktur otomatis (`INV-YYYYMMDD-XXXX`).
  * Generasi e-ticket ber-QR Code untuk setiap lembar tiket yang dipesan.
  * Halaman siap cetak (*print-friendly view*) atau disimpan sebagai tangkapan layar di ponsel pintar wisatawan.

---

### 🎫 4.2. Role: Petugas Loket / Kasir (`cashier`)
*Petugas operasional penjualan tiket di gerbang/loket masuk destinasi.*

#### A. Autentikasi & Identitas Loket
* **Login & Logout Aman (`/login`, `/logout`)**:
  * Sesi otomatis terhubung dengan destinasi penugasan petugas (`destination_id`).
  * Pembatasan hak akses halaman internal jika sesi berakhir.

#### B. Point of Sale (POS) Retribusi Tiket (`/pos`)
* **Interface Transaksi Cepat (Fast-Checkout)**:
  * Antarmuka yang dioptimalkan untuk pelayanan antrean wisatawan di loket fisik.
  * Otomatis memuat tarif dan jenis tiket berdasarkan objek wisata penugasan kasir (dengan opsi switch destinasi bagi peran berwenang).
  * Pemilihan jumlah tiket per kategori secara instan.
  * Input nama pembeli (opsional/default "Pengunjung Loket").
  * Pemilihan metode pembayaran instan (Tunai / QRIS).
* **Penerbitan Tiket Fisik / Struk QR**:
  * Pembuatan tiket instan dengan kode unik (`MGLK-[KODE]-XXXXXX`).
  * Enkripsi data tiket ke dalam QR Code menggunakan algoritma HMAC-SHA256.
  * Pengalihan instan ke halaman tiket cetak (`/tickets/<invoice>`) untuk langsung dicetak ke printer struk/loket.
* **Sinkronisasi Pendapatan Real-Time**:
  * Setiap transaksi loket otomatis memperbarui data rekapitulasi PAD harian (`pad_reports_recap`).

---

### 🛡️ 4.3. Role: Petugas Pintu Masuk / Gate Keeper (`gate_keeper`)
*Petugas pemeriksa keabsahan tiket di gerbang masuk fisik.*

#### A. Gate Entrance QR Validator (`/validator`)
* **Dual Scanner Mode**:
  * **Kamera / Webcam Scanner**: Pemindaian langsung menggunakan kamera smartphone atau webcam pos gerbang melalui pustaka pemindai HTML5.
  * **Manual / Barcode Gun Input**: Input manual kode tiket (`MGLK-...`) atau raw payload string untuk perangkat pemindai barcode eksternal.
* **Verifikasi Keamanan Kriptografi HMAC-SHA256 (`/api/validate-qr`)**:
  * Memvalidasi tanda tangan digital (*signature hash*) untuk mencegah manipulasi data tiket atau tiket palsu hasil rekayasa sendiri.
* **Pencegahan Tiket Ganda (*Anti Ticket Re-Use / Anti Fraud*)**:
  * Mendeteksi status tiket:
    * `VALID`: Tiket asli, belum dipakai, dan tanggal kunjungan sesuai $\rightarrow$ Sistem mengubah status menjadi `used`.
    * `ALREADY USED`: Tiket ditolak dengan rincian waktu pemindaian sebelumnya dan nama petugas yang melakukan scan.
    * `EXPIRED / CANCELLED`: Tiket ditolak karena kedaluwarsa atau dibatalkan.
    * `INVALID SIGNATURE / NOT FOUND`: Tiket terindikasi palsu atau tidak terdaftar di sistem.
* **Feedback Status & Audio Interaktif**:
  * Notifikasi visual berwarna (Hijau = Sukses Masuk, Merah = Ditolak/Palsu, Kuning = Pernah Dipakai).
  * Efek suara konfirmasi (*beep success* vs *buzzer error*) via Web Audio API untuk mempermudah operasional gerbang tanpa harus selalu menatap layar monitor.
* **Audit Trail / Riwayat Pemindaian Terkini**:
  * Menampilkan log 10 tiket terakhir yang dipindai di pos masuk lengkap dengan cap waktu (*timestamp*), nama pengunjung, dan nama jenis tiket.

---

### 🏛️ 4.4. Role: Administrator Disparbud (`admin`)
*Pejabat dan staf dinas yang memegang otoritas penuh atas sistem pariwisata.*

#### A. Full Operational Access
* Memiliki hak istimewa untuk membuka dan mengoperasikan modul Kasir POS (`/pos`) dan Gate Validator (`/validator`).

#### B. Dashboard Analytics & PAD Executive Metrics (`/admin/dashboard`)
* **Key Performance Indicators (KPI Cards)**:
  * Total Destinasi Wisata Aktif.
  * Total Akumulasi Transaksi Masuk.
  * Realisasi Pendapatan Retribusi Hari Ini (Rp).
  * Realisasi Pendapatan Retribusi Bulan Berjalan (Rp).
  * Total Realisasi Pendapatan PAD Kumulatif (Rp).
  * Total Volume Tiket Retribusi Terjual (Lembar).
* **Modul Prediksi & AI Insights PAD**:
  * Komparasi persentase pendapatan bulan berjalan terhadap bulan sebelumnya.
  * Deteksi dini lonjakan pendapatan (*surge alerts*) atau anomali penurunan PAD (*drop warning*) untuk rekomendasi tindak lanjut event/promosi.
* **Visualisasi Grafik Interaktif (Chart.js)**:
  * *Bar Chart*: Distribusi pendapatan dan volume tiket antar destinasi wisata (menganalisis destinasi penyumbang PAD tertinggi).
  * *Line Chart*: Tren fluktuasi pendapatan retribusi harian dalam 7 hari terakhir.
* **Tabel Aktivitas Transaksi Terbaru**:
  * Log 8 transaksi paling mutakhir yang masuk ke sistem secara real-time.

#### C. Laporan & Rekapitulasi PAD Terpusat (`/admin/pad-reports`)
* **Filter Multi-Kriteria**:
  * Filter berdasarkan rentang tanggal awal (*start date*) dan akhir (*end date*).
  * Filter spesifik per destinasi wisata.
* **Ringkasan Finansial Dinamis**:
  * Akumulasi total tiket dan total nilai PAD otomatis dihitung ulang sesuai filter yang dipilih.
* **Matriks Sebaran Pendapatan Bulanan (Yearly Breakdown)**:
  * Rekapitulasi kontribusi setiap destinasi per bulan dari Januari hingga Desember pada tahun berjalan.
* **Ekspor Data Laporan (`/admin/export-pad-csv`)**:
  * Unduh rekapitulasi data PAD ke dalam berkas **CSV/Excel** untuk kebutuhan arsip resmi, audit BPK, dan pelaporan keuangan pemda.

#### D. Manajemen Master Data Destinasi & Tiket (`/admin/destinations`)
* **CRUD Objek Wisata**:
  * Tambah destinasi baru (Kode Unik, Nama, Kategori, Lokasi, Tarif Dasar, Deskripsi, URL Foto).
  * Pembuatan tiket reguler otomatis saat destinasi baru ditambahkan.
  * Edit informasi dan toggle status aktif/non-aktif destinasi.
  * Hapus data destinasi beserta relasi dependensinya.
* **CRUD Jenis & Tarif Tiket Retribusi**:
  * Menambah varian kategori tiket per destinasi (misal: Tiket Dewasa, Anak, Rombongan, Tiket Terusan Wahana) lengkap dengan harga dan deskripsinya.

#### E. Manajemen Promo & Hotel Rekanan (`/admin/hotels`)
* **Master Data Hotel Rekanan**:
  * Pendaftaran akomodasi/hotel di sekitar destinasi wisata Pantura Lamongan.
* **Manajemen Promo & Diskon Hotel**:
  * Pembuatan kupon/diskon hotel rekanan dengan periode tanggal berlaku (*valid from* hingga *valid until*).

#### F. Manajemen Agenda Event Wisata (`/admin/events`)
* **Penjadwalan Event Budaya & Pariwisata**:
  * Tambah agenda event (Festival, Pameran Seni, Haul/Ziarah Akbar, Pesta Pantai) terhubung dengan destinasi terkait dan tanggal pelaksanaannya.

---

## 🔒 5. Arsitektur Keamanan & Proteksi Transaksi

1. **Autentikasi & Password Hashing**:
   * Password dienkripsi menggunakan hashing standar industri Werkzeug (`generate_password_hash` & `check_password_hash`).
2. **Dekorator Role-Based Access Control (RBAC)**:
   * Proteksi level endpoint menggunakan `@login_required` dan `@role_required('admin', ...)`.
   * Akses tidak sah akan diarahkan ke halaman login atau beranda dengan pesan peringatan kilat (*flash message*).
3. **HMAC-SHA256 Ticket Payload Protection**:
   * Format payload tiket: `MGLK|{TICKET_CODE}|{DESTINATION_ID}|{VALID_DATE}|{SEC_HASH}`.
   * `SEC_HASH` dihitung menggunakan kunci rahasia server (`SECRET_KEY`), menjamin tiket tidak dapat direkayasa secara offline.
4. **Dual Engine Database Support**:
   * Kompatibel penuh dengan **MySQL 8.0 / MariaDB** untuk deployment server produksi, dan fallback otomatis ke **SQLite** untuk pengujian lokal instan.

---

## 6. Akun petugas

Buat akun admin, kasir, atau gate keeper dengan perintah `create-staff`. Lihat [panduan setup](../README.md#akun-petugas).
