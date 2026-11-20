# Evaluasi awal AI MegiLoka

Tanggal pemeriksaan: 5 November 2026 (Asia/Jakarta).

## Bukti pemeriksaan

Beranda http://127.0.0.1:5000/ merespons HTTP 200. Pemeriksaan dilakukan melalui HTTP, endpoint chatbot, kode sumber, dan pembacaan database tanpa perubahan data. Pemeriksaan visual browser belum berhasil karena browser bawaan mengalami timeout dan jendela Chrome terdeteksi diminimalkan.

Chatbot saat ini memakai daftar kata kunci dan jawaban tetap di `backend/utils/ai_service.py`. Jalur jawaban percakapan tidak mengambil event atau tarif destinasi dari database. Tidak ada proses training model pada jalur ini.

| Pertanyaan uji melalui POST /api/ai/chat | Jawaban saat ini | Masalah |
| --- | --- | --- |
| Kapan Festival Kupatan Akbar Tanjung Kodok dilaksanakan? | Petunjuk membuat event/destinasi | Tidak memberikan tanggal |
| Event apa saja besok? | Informasi umum tentang 94 agenda | Tidak memfilter event besok |
| Jam berapa Haul Sunan Drajat dimulai? | Deskripsi makam dan tarif tiket | Salah mengenali maksud pertanyaan |
| Berapa harga tiket Pantai Kutang? | Petunjuk memesan tiket | Tidak memberikan harga |

Database yang dibaca berisi 29 baris event dan 21 destinasi aktif. Ini tidak mendukung klaim chatbot bahwa ia menguasai 94 agenda resmi dan 32+ destinasi. Klaim status resmi instansi juga perlu bukti sebelum digunakan pada proyek mahasiswa.

Model Event menyimpan tanggal, tetapi belum menyimpan jam mulai, jam selesai, sumber jadwal, status verifikasi, atau penanda data simulasi. `backend/seed_references.py` membuat tanggal relatif terhadap hari eksekusi, bahkan menggeser sebagian tanggal pada eksekusi berikutnya. Karena itu data tersebut belum dapat dianggap sebagai kalender resmi.

Contoh data aplikasi (bukan jadwal resmi terverifikasi):

- Festival Kupatan Akbar Tanjung Kodok tercatat 10 Oktober 2026; sudah lewat pada tanggal pemeriksaan.
- Ada dua event tercatat untuk 6 November 2026: Gandrung Rajekwesi Beach Music Festival Edisi 2026 dan Gebyar Seni Tari Boran Kolosal Lamongan Edisi 2026.
- Tarif dasar Pantai Kutang tercatat Rp10.000; tarif tiket per jenis dan promo tetap harus diperiksa ketika membuat jawaban harga.

## Masukan sebagai pembimbing

Fokus tema: asisten informasi wisata dan agenda Lamongan yang membantu calon pengunjung merencanakan kunjungan. Prioritaskan ketepatan data, keterlacakan sumber, dan kemampuan mengakui informasi yang belum tersedia.

1. Jawab kapan, di mana, berapa harga, dan cara pemesanan sesuai maksud pertanyaan. Gunakan data aplikasi untuk fakta yang berubah.
2. Pahami hari ini, besok, akhir pekan, bulan ini, bulan depan, tanggal tertentu, dan event terdekat dengan zona waktu Asia/Jakarta.
3. Pisahkan agenda yang sudah lewat dan mendatang. Jangan menggeser jadwal budaya agar selalu terlihat akan berlangsung.
4. Jika nama acara ambigu, minta pengguna memilih acara. Jika jam belum ada, katakan bahwa jam belum dicantumkan, tanpa mengarang.
5. Ganti tombol cepat pengunjung menjadi pertanyaan informasi. Pindahkan penerbitan agenda ke pengelola dengan pemeriksaan hak akses pada backend. Endpoint chatbot saat ini memiliki cabang penambahan data tanpa pemeriksaan role; hal ini ditemukan dari kode dan tidak diuji dengan membuat data.
6. Tandai data demonstrasi dan lengkapi sumber jadwal, waktu pembaruan, lokasi acara, penyelenggara, serta status konfirmasi.
7. Bedakan istilah pada laporan: pencocokan kata kunci, model klasifikasi intent terlatih, pengambilan fakta dari database, dan fine-tuning model bahasa adalah mekanisme yang berbeda.

## Pilihan implementasi untuk dibahas

Pilihan A: perbaiki pencarian dan aturan chatbot agar mengambil fakta langsung dari database. Lebih ringan, tetapi tidak memiliki training model statistik.

Pilihan B (rekomendasi jika tugas membutuhkan training): latih model klasifikasi maksud pertanyaan secara lokal menggunakan contoh bahasa Indonesia, kemudian ambil tanggal, lokasi, dan harga dari database. Model mempelajari maksud pertanyaan; jadwal tidak dihafalkan dalam bobot model. Tetap sediakan penanganan nama ambigu dan pertanyaan di luar cakupan.

Fine-tuning model bahasa besar bukan langkah pertama yang disarankan untuk masalah yang ditemukan: spesifikasi perangkat belum diperiksa, dan sumber masalah utama adalah akses fakta serta kualitas data.

## Kriteria evaluasi yang diusulkan

Sediakan kumpulan pertanyaan training dan pengujian yang terpisah; jangan melaporkan skor training sebagai akurasi pengujian. Uji variasi parafrasa, nama singkat destinasi, tanggal relatif, nama acara berulang, acara lampau, jadwal kosong, dan jam yang tidak tersedia. Sertakan pengujian bahwa pertanyaan pengunjung tidak menambah atau mengubah data. Laporkan jumlah kasus lulus, kasus gagal, dan keterbatasan secara terpisah dari metrik model.

Status: audit awal selesai; belum ada model yang dilatih, dependensi dipasang, kode aplikasi diubah, atau jadwal database dimodifikasi.
