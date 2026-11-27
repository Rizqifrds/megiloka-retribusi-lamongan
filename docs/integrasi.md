# Integrasi MegiLoka

## API promo dan agenda mitra

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
MegiLoka mengambil rincian dari API pengelola. Bagian Promo Wisata memakai
periode promo untuk menampilkan pengumuman yang masih atau akan berlaku.
Beranda terbuka meminta hasil terbaru setiap 30 detik.

## Instagram Wisata Bahari Lamongan

Sumber yang dipantau adalah `@wisatabaharilamonganpark`. Untuk mengaktifkan
Business Discovery, buat aplikasi Meta memakai Instagram API with Facebook
Login dan hubungkan akun Instagram profesional proyek ke Halaman Facebook.
Isi konfigurasi berikut di file `.env` server, lalu mulai ulang aplikasi.

- `INSTAGRAM_GRAPH_VERSION`: versi Graph API yang digunakan aplikasi Meta.
- `INSTAGRAM_IG_USER_ID`: ID akun Instagram profesional yang mengotorisasi aplikasi.
- `INSTAGRAM_ACCESS_TOKEN`: token dari Meta dengan izin untuk Business Discovery.

Sinkronisasi mengambil hingga 25 kiriman terkini setiap lima menit. Format
caption seperti `Periode promo: 20–30 November 2026` dan
`Tanggal acara: 25 November 2026` dapat dipublikasikan otomatis beserta
tautan kirimannya. Tanggal dalam gambar tidak diproses.

---

## Notifikasi agenda melalui WhatsApp

Isi pengaturan `WHATSAPP_*` dari `.env.example` di file `.env` server.
`WHATSAPP_NUMBER` adalah nomor bisnis internasional tanpa tanda tambah.
`WHATSAPP_PHONE_ID` adalah Phone Number ID dari Meta. Gunakan versi Graph API
yang diaktifkan proyek, access token WhatsApp, App Secret, dan verify token
yang dibuat khusus untuk webhook.

Daftarkan URL HTTPS publik `/webhooks/whatsapp` di Meta dan pilih field
`messages`. Gunakan template berbahasa Indonesia yang disetujui Meta. Isi
template memerlukan dua parameter badan pesan dalam urutan nama agenda
dan tanggal. Nama template diisi di `WHATSAPP_AGENDA_TEMPLATE`.

Tautan dari lonceng membuka chat untuk mengirim `DAFTAR MEGILOKA` atau
`STOP MEGILOKA`. Pesan yang ditandatangani Meta mengaktifkan atau menghentikan
langganan untuk nomor pengirim. Server mengecek agenda H-1 setiap 10 menit
setelah menerima permintaan pertama. Status `accepted` menandai permintaan
diterima Meta, dan `unconfirmed` menandai hasil yang belum dapat dikonfirmasi.
