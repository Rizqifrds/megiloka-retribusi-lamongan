# Panduan AI lokal MegiLoka

Implementasi 5 November 2026. Model sudah dilatih dan dipakai oleh `/api/ai/chat` pada aplikasi Flask.

## Yang dapat dijelaskan kepada dosen

Megi adalah chatbot domain pariwisata Lamongan dengan model klasifikasi intent terlatih. Modelnya bukan LLM generatif: ia mempelajari hubungan pola bahasa dengan maksud pertanyaan. Jawaban fakta diambil dari database aplikasi, lalu disusun dengan template agar tanggal dan harga tidak dikarang.

Alur: pertanyaan → TF-IDF kata dan karakter → regresi logistik → intent → penguraian tanggal/nama → query database → jawaban beserta tautan sumber. Model tetap berperan pada setiap pertanyaan percakapan; pemeriksaan perintah perubahan data dan otorisasi dilakukan terpisah sebelum inferensi.

Delapan kelas: `event_schedule`, `event_detail`, `destination_info`, `ticket_price`, `booking`, `greeting`, `opening_hours`, dan `out_of_scope`.

Data disusun manual sebagai contoh sintetis bahasa Indonesia untuk tugas kuliah, bukan percakapan pengguna nyata. Training berisi 256 pertanyaan (32 per kelas); data uji terpisah berisi 64 pertanyaan (8 per kelas). Tidak ada pertanyaan identik setelah normalisasi huruf/spasi di kedua bagian. Parafrasa dan kosakata masih dapat mirip: evaluasi kecil ini belum membuktikan kemampuan pada pengguna umum.

## Hasil training pertama

| Ukuran | Hasil |
| --- | --- |
| Pertanyaan training | 256 |
| Pertanyaan uji terpisah | 64 |
| Prediksi kelas benar | 59 / 64 |
| Akurasi klasifikasi | 92,1875% |
| Macro F1 | 0,9064 |
| Penolakan karena confidence/margin rendah | 1 / 64 |
| Akurasi runtime termasuk penolakan sebagai tidak benar | 92,1875% |

Nilai di atas adalah kemampuan klasifikasi pada dataset ini, bukan jaminan bahwa 92% semua jawaban pengguna akan benar. Ketepatan jawaban juga bergantung pada pengenalan nama, tanggal, dan isi database. Angka tersebut dihitung sebelum pemeriksaan integrasi dan tidak ditingkatkan dengan melatih ulang pada soal uji.

Lima kesalahan semuanya berasal dari kelas di luar cakupan. Contohnya pertanyaan tugas fisika dikenali sebagai sapaan, pertanyaan obat batuk sebagai booking, dan investasi emas minggu depan sebagai agenda. Lihat semua kesalahan, confidence, precision/recall per kelas, serta confusion matrix dalam `backend/ai/artifacts/evaluation.json`. Recall kelas `out_of_scope` baru 37,5%; ini batas penting untuk dipaparkan, bukan disembunyikan dengan angka akurasi total. Lapisan pencarian fakta tetap menolak nama yang tidak cocok dan tidak menjalankan perintah dari jawaban model.

Confidence adalah probabilitas prediksi classifier yang belum dikalibrasi, bukan persentase kepastian kebenaran jawaban. Ambang tetap 0,32 dan selisih dua kelas teratas 0,04; jika di bawahnya, Megi meminta pertanyaan diperjelas.

## Menjalankan dan melakukan training ulang

Jalankan dari PowerShell pada `C:\PENS\op`:

```powershell
.\venv\Scripts\python.exe -m pip install -r backend/requirements.txt
.\venv\Scripts\python.exe backend/train_ai.py
.\venv\Scripts\python.exe run.py
```

Jika ingin menyamai versi pustaka yang dipakai pada training awal, pasang `backend/requirements-ai-lock.txt` setelah requirements utama. Artefak joblib bergantung pada versi pustaka; setelah mengganti versi Python/scikit-learn, lakukan training ulang.

Buka `http://127.0.0.1:5000/`, muat ulang halaman dengan Ctrl+F5, lalu klik Tanya Megi. Server yang sudah berjalan dapat membaca model hasil training ulang pada permintaan berikutnya. Jika server berhenti ketika dependensi belum terpasang, jalankan ulang perintah `run.py` di atas.

Training ulang tidak mengubah tabel event, harga, maupun transaksi. Hasilnya:

- `backend/ai/artifacts/intent_model.joblib`: pipeline TF-IDF dan bobot model.
- `backend/ai/artifacts/evaluation.json`: metrik, versi, seed, hash dataset, dan prediksi setiap soal uji.

Hanya gunakan artefak joblib buatan proyek sendiri. Jangan memuat model unduhan tidak tepercaya, karena format joblib dapat mengeksekusi kode ketika dibaca.

## Menambah data pembelajaran

Edit `backend/ai/data/train.json`, tambahkan pertanyaan dengan format berikut, dan gunakan salah satu dari delapan label yang ada:

```json
{"text": "contoh pertanyaan bahasa Indonesia", "intent": "event_schedule"}
```

Untuk pengembangan berikutnya, kumpulkan parafrasa nyata tanpa data pribadi, variasi bahasa sehari-hari, salah ketik, dan contoh di luar tema. Perbanyak contoh negatif untuk kelas `out_of_scope`. Tambahkan kumpulan evaluasi baru yang belum pernah dipakai untuk menentukan perubahan model; setelah melihat kesalahan soal uji, jangan mengklaim soal itu masih merupakan evaluasi independen untuk versi yang disesuaikan dengannya.

Jangan memasukkan tanggal event atau harga sebagai jawaban tetap dalam dataset. Jadwal dan harga diperbarui melalui data pengelola; model belajar maksud pertanyaan, bukan menghafalkan kalender.

## Contoh demonstrasi

1. “Event apa saja besok?” — daftar event pada tanggal besok menurut waktu Asia/Jakarta.
2. “Event apa saja bulan depan?” — filter satu bulan kalender, termasuk pergantian tahun.
3. “Ada acara akhir pekan ini?” — filter Sabtu–Minggu pada minggu tersebut.
4. “Kapan Festival Kupatan Akbar Tanjung Kodok dilaksanakan?” — meminta nama/tanggal lebih spesifik jika ada beberapa edisi.
5. “Jam berapa Haul Sunan Drajat pada 8 November 2026?” — menyatakan jam belum tersedia, tidak mengarangnya.
6. “Berapa harga tiket Pantai Kutang?” — menampilkan jenis tiket dan tarif database saat ini.
7. “Di mana lokasi WBL?” — menampilkan alamat dari data destinasi.
8. “Bagaimana cara memesan tiket?” — panduan alur pemesanan dan penjelasan status simulasi pembayaran.

Pertanyaan lanjutan harus menyebut ulang nama/tanggal, misalnya “Haul Sunan Drajat tanggal 8 November 2026”. Versi ini belum menyimpan konteks percakapan; pesan “yang kedua” saja belum dapat dipahami. Nama yang tidak ditemukan atau ambigu memerlukan klarifikasi.

## Menjalankan pengujian

```powershell
.\venv\Scripts\python.exe backend/run_tests.py
node backend/tests/test_chat_ui.cjs
.\venv\Scripts\python.exe -m pip check
```

Runner Python mengatur SQLite in-memory sebelum aplikasi diimpor, kemudian menjalankan pengujian AI dan pengujian aplikasi lama. Ini penting karena tes lama memiliki `drop_all`; jangan menjalankan tes lama langsung dengan database website. Tes JavaScript menguji escaping pesan dan pembatasan tautan sumber tanpa mengoperasikan browser.

Hasil implementasi ini: 27 pengujian Python lulus (23 baru dan 4 pengujian aplikasi lama), pengujian render JavaScript lulus, pemeriksaan sintaks JavaScript lulus, serta `pip check` tidak menemukan konflik dependensi. Pemeriksaan HTTP website aktif mencakup 13 kasus dan tautan sumbernya, seluruhnya berhasil; sidik data event/destinasi/jenis tiket sebelum dan sesudah sama. Bukti tersimpan di `docs/hasil-uji-http-megi.json`. Tampilan visual browser belum berhasil diverifikasi; hasil ini berasal dari HTTP, template, dan pengujian JavaScript.

## Batas informasi dan saran pembimbing

- Kalender awal menggunakan data simulasi tanggal relatif, belum kalender resmi. Proses ini tidak mengganti tanggal atau menghapus duplikat. Verifikasi ke penyelenggara dan tambahkan sumber, tanggal pembaruan, status konfirmasi, jam mulai/selesai, serta lokasi acara yang sebenarnya pada pengembangan selanjutnya.
- Database saat ini belum menyimpan jam operasional destinasi atau jam event. Megi menyatakan belum tersedia. Destinasi yang ditautkan ke acara disebut referensi destinasi, bukan dianggap bukti lokasi persis acara.
- Tombol pengunjung kini berupa pertanyaan. Endpoint menolak penambahan event/destinasi oleh guest, kasir, dan pengguna dengan sesi admin tanpa akun admin valid. Pengelola tetap memakai menu Kelola Kalender Event/Kelola Destinasi.
- Cabang penerbitan simulasi yang lama dipertahankan untuk admin; ia belum merupakan editor jadwal resmi. Gunakan formulir pengelolaan untuk data yang terverifikasi. Ini berbeda dari kemampuan model memahami pertanyaan.
- Harga jawaban mengikuti jenis tiket yang digunakan formulir booking. Promo destinasi yang berlaku ditampilkan sebagai informasi dengan permintaan konfirmasi; alur booking sekarang belum mengurangi harga berdasarkan promo. Promo hotel tidak diasumsikan otomatis menjadi diskon tiket wisata.
- Pembayaran pada proyek langsung ditandai paid oleh kode lama tanpa verifikasi payment gateway. Megi menyebutnya simulasi; memperbaiki integrasi pembayaran berada di luar pekerjaan training ini.
- Domain di luar wisata, rute perjalanan terperinci, percakapan multilangkah, dan nama dengan salah ketik berat masih terbatas. Model ringan ini tidak setara chatbot umum.
- Seluruh training dan inferensi AI berjalan lokal. Tampilan website masih menggunakan aset CDN yang sudah ada (Bootstrap/FontAwesome/Chart.js/gambar), sehingga tampilan lengkap tidak dijanjikan sepenuhnya offline.

## File penting

| File | Fungsi |
| --- | --- |
| `backend/train_ai.py` | Membuat dan mengevaluasi model |
| `backend/ai/intent_model.py` | Memuat artefak dan memprediksi intent |
| `backend/ai/dates.py` | Interpretasi tanggal dan zona waktu |
| `backend/ai/concierge.py` | Pencarian fakta serta penyusunan jawaban |
| `backend/ai/data/train.json` | Contoh latihan berlabel |
| `backend/ai/data/test.json` | Soal evaluasi terpisah |
| `backend/tests/` | Regresi API, tanggal, model, dan render pesan |
| `docs/backups/sebelum-training-megi-20261105.zip` | Salinan lima file aplikasi sebelum perubahan |

Referensi algoritma: [TF-IDF scikit-learn](https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html) dan [LogisticRegression scikit-learn](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html).
