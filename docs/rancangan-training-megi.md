# Rancangan training lokal Megi

Usulan untuk persetujuan mahasiswa, 5 November 2026.

Tujuan: memenuhi persyaratan model yang benar-benar dilatih dan membuat asisten wisata Lamongan menjawab pertanyaan agenda serta informasi kunjungan secara tepat.

## Pendekatan

Usulan: model klasifikasi intent berbasis TF-IDF dan regresi logistik yang dilatih lokal dari dataset pertanyaan bahasa Indonesia. Model mendeteksi maksud; layanan aplikasi mengambil fakta dari database dan menyusun jawaban. Ini merupakan pilihan teknis yang diusulkan, bukan keputusan yang sudah disetujui pengguna.

Alternatif aturan kata kunci saja tidak memenuhi persyaratan training. Fine-tuning model bahasa besar memerlukan evaluasi perangkat dan dataset yang lebih besar; tidak diperlukan untuk cakupan pertanyaan yang ditemukan. Usulan model ringan memakai aplikasi Flask yang sudah ada.

## Cakupan

- Dataset berlabel untuk maksud jadwal event, detail event, lokasi destinasi, harga tiket, cara pemesanan, sapaan, dan pertanyaan di luar cakupan. Jumlah contoh serta label akhir ditentukan saat implementasi berdasarkan kebutuhan evaluasi.
- Skrip training yang dapat dijalankan ulang, artefak model lokal, dan laporan evaluasi menggunakan data uji terpisah. Contoh pengujian tidak disalin ke dataset training.
- Penanganan tanggal relatif Asia/Jakarta: hari ini, besok, akhir pekan, bulan ini, bulan depan; tanggal tertentu; dan event mendatang.
- Pencarian nama acara dan destinasi dari database. Jika nama tidak jelas atau punya beberapa kecocokan, minta klarifikasi.
- Jawaban jam mulai yang belum tersedia harus menyatakan belum tersedia. Tanggal database ditampilkan sebagai data aplikasi, tanpa klaim kalender resmi terverifikasi.
- Tarif diambil dari data destinasi/jenis tiket dan mempertimbangkan informasi promo yang memang tersedia.
- Tombol cepat untuk pengunjung berupa pertanyaan, bukan penerbitan data. Aksi perubahan data pada endpoint hanya boleh untuk admin yang terautentikasi; pengunjung tidak dapat membuat event melalui chat.
- Dokumentasi cara training, menjalankan aplikasi, keterbatasan, dan contoh presentasi.

## Batasan

Tidak mengubah tanggal event yang sudah ada menjadi tanggal resmi, tidak mengarang jam operasional atau jam mulai, dan tidak menghapus event berulang tanpa keputusan pemilik data. Data awal tetap perlu verifikasi penyelenggara. Peningkatan yang diusulkan tidak mencakup perombakan desain seluruh website atau pelatihan model bahasa generatif.

## Verifikasi

Uji maksud pada pertanyaan yang tidak masuk training, ketepatan jawaban terhadap database, rentang tanggal di batas bulan/tahun, acara lampau, jadwal kosong, nama ambigu, dan ketiadaan jam. Uji endpoint dengan database pengujian agar pertanyaan publik tidak mengubah data. Laporkan hasil nyata dan kegagalan; jangan menjanjikan angka akurasi sebelum training selesai.

## Hasil yang akan diserahkan

Model terlatih, dataset training dan pengujian, skrip training, integrasi chatbot lokal, hasil evaluasi, serta panduan mahasiswa. Seluruh proses inferensi dan training dijalankan lokal; tidak menggunakan API AI berbayar.
