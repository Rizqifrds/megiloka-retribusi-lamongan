"""
MegiLoka Smart AI Concierge & Event/Destination Auto-Publisher
Sistem Cerdas Customer Service & Manajemen Event Wisata Lamongan
Referensi Resmi:
- Bapperida & Disbudporapar Kabupaten Lamongan (Kalender Event 2026)
- Kompas Travel (32 Tempat Wisata Lamongan) & TripAdvisor Attractions
"""

import re
import random
from datetime import date, datetime, timedelta

# =========================================================
# 1. TEMPLATE EVENT KALENDER WISATA LAMONGAN 2026 (BAPPERIDA)
# =========================================================
LAMONGAN_EVENT_TEMPLATES = [
    {
        "name": "Festival Kupatan Akbar Tanjung Kodok",
        "description": "Tradisi tahunan kupatan pesisir pasca-Idulfitri khas Pantura Lamongan yang menyajikan gunungan ketupat raksasa, kenduri rakyat, pawai perahu hias nelayan, dan pagelaran musik tradisional di tepi laut Paciran.",
        "category": "Budaya & Tradisi",
        "image_url": "https://images.unsplash.com/photo-1514525253161-7a46d19cd819?auto=format&fit=crop&w=800&q=80",
        "dest_code_hint": "DEST-WBL"
    },
    {
        "name": "Haul Akbar ke-516 Sunan Drajat",
        "description": "Peringatan haul agung Raden Qasim Sunan Drajat di kompleks makam bersejarah Paciran, diiringi pameran kaligrafi Islam, bedah sejarah Walisongo, khitanan massal, dan pasar rakyat kuliner halal.",
        "category": "Wisata Religi & Budaya",
        "image_url": "https://images.unsplash.com/photo-1548625361-185b9826f634?auto=format&fit=crop&w=800&q=80",
        "dest_code_hint": "DEST-SND"
    },
    {
        "name": "Kirab Budaya Hari Jadi Lamongan (HJL ke-457)",
        "description": "Pawai agung pusaka dan karnaval budaya peringatan Hari Jadi Lamongan mengelilingi pusat kota, dimeriahkan kereta kencana bupati, barisan bregodo prajurit kerajaan, dan tari-tarian kolosal khas Megilan.",
        "category": "Sejarah & Budaya Daerah",
        "image_url": "https://images.unsplash.com/photo-1533174072545-7a4b6ad7a6c3?auto=format&fit=crop&w=800&q=80",
        "dest_code_hint": None
    },
    {
        "name": "Gebyar Seni Tari Boran Kolosal Lamongan",
        "description": "Pertunjukan spektakuler Tari Boran massal di Alun-Alun Lamongan yang mengangkat kearifan lokal penjual Nasi Boran, dibawakan oleh ratusan penari mengenakan busana khas, caping, dan bakul bambu.",
        "category": "Seni & Pertunjukan",
        "image_url": "https://images.unsplash.com/photo-1469488865564-c2de10f69f96?auto=format&fit=crop&w=800&q=80",
        "dest_code_hint": None
    },
    {
        "name": "Lamongan Tempo Doeloe",
        "description": "Pesta nostalgia budaya dan bazar kuliner lawas tempo dulu khas Lamongan, menghadirkan stand bernuansa rumah joglo tempo dulu, mainan tradisional anak, serta pakaian adat Jawa Timuran.",
        "category": "Festival Rakyat & Kuliner",
        "image_url": "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?auto=format&fit=crop&w=800&q=80",
        "dest_code_hint": None
    },
    {
        "name": "Festival Pantura & Pesta Nelayan Brondong",
        "description": "Karnaval pesisir memukau di dermaga Pelabuhan Brondong dan jembatan kayu Pantai Kutang, peragaan kostum biota laut, parade obor malam, serta tradisi larung sesaji laut sebagai wujud syukur hasil tangkapan.",
        "category": "Bahari & Festival Nelayan",
        "image_url": "https://images.unsplash.com/photo-1519046904884-53103b34b206?auto=format&fit=crop&w=800&q=80",
        "dest_code_hint": "DEST-KTG"
    },
    {
        "name": "Festival Bandeng & Lele Megilan Nusantara",
        "description": "Pesta kuliner rakyat Kabupaten Lamongan merayakan sentra budidaya perikanan air tawar dan tambak, lomba kreasi memasak soto bumbu koya, lele krispi, serta pameran olahan ikan UMKM.",
        "category": "Kuliner & Ekonomi Kreatif",
        "image_url": "https://images.unsplash.com/photo-1544025162-d76694265947?auto=format&fit=crop&w=800&q=80",
        "dest_code_hint": None
    },
    {
        "name": "Festival Bonsai Nasional & Pameran Flora Megilan",
        "description": "Pameran dan kontes tanaman bonsai tingkat nasional yang dihadiri ribuan kolektor dari seluruh Indonesia di kawasan wisata Lamongan, menampilkan karya seni tanaman kerdil bernilai seni tinggi.",
        "category": "Pameran & Komunitas",
        "image_url": "https://images.unsplash.com/photo-1512428813834-c702c7702b78?auto=format&fit=crop&w=800&q=80",
        "dest_code_hint": "DEST-WDG"
    },
    {
        "name": "Gandrung Rajekwesi Beach Music Festival",
        "description": "Pentas musik akustik dan jazz senja di pinggir pantai karang Pantai Lorena Paciran, dimeriahkan musisi regional, kuliner es kelapa muda, dan panorama matahari terbenam yang syahdu.",
        "category": "Musik & Hiburan Pesisir",
        "image_url": "https://images.unsplash.com/photo-1470225620780-dba8ba36b745?auto=format&fit=crop&w=800&q=80",
        "dest_code_hint": "DEST-LRN"
    },
    {
        "name": "Pesta Layang-Layang Hias Pantura Paciran",
        "description": "Kompetisi layang-layang tradisional dan modern berukuran raksasa bentuk naga, burung garuda, dan perahu di pesisir utara Lamongan dengan atraksi manuver angin laut yang memukau.",
        "category": "Olahraga & Rekreasi Pantai",
        "image_url": "https://images.unsplash.com/photo-1508873696983-2df5293cb32f?auto=format&fit=crop&w=800&q=80",
        "dest_code_hint": "DEST-WBL"
    },
    {
        "name": "Tradisi Upacara Adat Mendak Sanggring Tlemang",
        "description": "Upacara adat sakral warisan leluhur di Desa Tlemang, Kecamatan Ngimbang, di mana seluruh juru masak masakan tradisional sanggring wajib merupakan kaum laki-laki yang telah disucikan.",
        "category": "Warisan Budaya & Tradisi Adat",
        "image_url": "https://images.unsplash.com/photo-1563245372-f21724e3856d?auto=format&fit=crop&w=800&q=80",
        "dest_code_hint": None
    }
]

# =========================================================
# 2. TEMPLATE DESTINASI WISATA (KOMPAS TRAVEL 32 TEMPAT & TRIPADVISOR)
# =========================================================
LAMONGAN_DESTINATION_TEMPLATES = [
    {
        "code_prefix": "NMR",
        "name": "Masjid Namira Lamongan",
        "category": "Wisata Religi & Arsitektur",
        "location": "Jalan Raya Mantup Km 5, Desa Jotosanur, Kec. Tikung, Kab. Lamongan",
        "base_price": 5000.0,
        "description": "Destinasi wisata religi megah dan viral di Lamongan yang terkenal dengan potongan kain Kiswah Ka'bah asli dari Masjidil Haram di dinding mihrab, kolam ikan luas, dan arsitektur modern ala Timur Tengah.",
        "image_url": "https://images.unsplash.com/photo-1564769625905-50e93615e769?auto=format&fit=crop&w=800&q=80",
        "ticket_name": "Infaq & Tiket Wisata Religi Masjid Namira"
    },
    {
        "code_prefix": "SCN",
        "name": "Sukodadi Carnival",
        "category": "Taman Hiburan & Rekreasi Keluarga",
        "location": "Jalan Raya Pantura No. 38, Kec. Sukodadi, Kab. Lamongan",
        "base_price": 30000.0,
        "description": "Taman rekreasi keluarga yang memadukan wahana karnaval modern dengan sirkus budaya, rumah hantu, bioskop VR, waterpark mini, dan pertunjukan lampu gemerlap malam hari.",
        "image_url": "https://images.unsplash.com/photo-1513889961551-628c1e5e2ee9?auto=format&fit=crop&w=800&q=80",
        "ticket_name": "Tiket Masuk Reguler Sukodadi Carnival"
    },
    {
        "code_prefix": "WGO",
        "name": "Wisata Edukasi Danau & Pesawat WEGO Lamongan",
        "category": "Wisata Edukasi & Outbound",
        "location": "Desa Deketagung, Kec. Sugio, Kab. Lamongan",
        "base_price": 25000.0,
        "description": "Destinasi wisata alam edukatif seluas 36 hektare dengan ikon pesawat terbang Boeing asli di tepi danau, jembatan Pulau Cinta, mini zoo satwa jinak, dan fasilitas perkemahan outbound.",
        "image_url": "https://images.unsplash.com/photo-1513836279014-a89f7a76ae86?auto=format&fit=crop&w=800&q=80",
        "ticket_name": "Tiket Terusan Edukasi WEGO"
    },
    {
        "code_prefix": "GMS",
        "name": "Wisata Alam Bukit Kapur Gunung Mas Mantup",
        "category": "Wisata Alam & Spot Foto",
        "location": "Desa Tugu, Kec. Mantup, Kab. Lamongan",
        "base_price": 10000.0,
        "description": "Kawasan bekas galian tambang kapur yang disulap menjadi destinasi wisata artistik dengan rumah kayu bergaya perpaduan arsitektur Jawa dan Tionghoa kuno di atas tebing kapur bernuansa emas.",
        "image_url": "https://images.unsplash.com/photo-1506744038136-46273834b3fb?auto=format&fit=crop&w=800&q=80",
        "ticket_name": "Tiket Masuk Gunung Mas Mantup"
    },
    {
        "code_prefix": "SDW",
        "name": "Desa Cagar Budaya Sendang Duwur",
        "category": "Wisata Sejarah & Cagar Budaya",
        "location": "Bukit Amitaba, Desa Sendangduwur, Kec. Paciran, Kab. Lamongan",
        "base_price": 10000.0,
        "description": "Situs cagar budaya nasional peninggalan abad ke-16 makam Raden Noer Rahman (Sunan Sendang Duwur) yang tersohor dengan gapura bersayap paduraksa perpaduan langka seni arsitektur Islam dan Hindu Majapahit.",
        "image_url": "https://images.unsplash.com/photo-1548625361-185b9826f634?auto=format&fit=crop&w=800&q=80",
        "ticket_name": "Tiket Masuk Cagar Budaya Sendang Duwur"
    },
    {
        "code_prefix": "KMN",
        "name": "Pantai Kemantren Gubuk Apung",
        "category": "Wisata Bahari & Santai",
        "location": "Desa Kemantren, Kec. Paciran, Kab. Lamongan",
        "base_price": 10000.0,
        "description": "Destinasi wisata pesisir pantai dengan deretan saung bambu apung unik beratap jerami di atas laut dangkal yang terhubung jembatan titian kayu, ideal untuk menikmati ombak tenang dan semilir angin pantai.",
        "image_url": "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=800&q=80",
        "ticket_name": "Tiket Masuk Pantai Kemantren"
    },
    {
        "code_prefix": "KLY",
        "name": "Pantai Putri Klayar Hidden Gem",
        "category": "Wisata Bahari & Camping",
        "location": "Dusun Klayar, Desa Sidokelar, Kec. Paciran, Kab. Lamongan",
        "base_price": 10000.0,
        "description": "Pantai pasir putih alami yang tenang dengan hamparan pepohonan mangrove rindang, air laut jernih, dan area berkemah pantai yang asri bebas dari hiruk pikuk keramaian kota.",
        "image_url": "https://images.unsplash.com/photo-1519046904884-53103b34b206?auto=format&fit=crop&w=800&q=80",
        "ticket_name": "Tiket Masuk Pantai Putri Klayar"
    },
    {
        "code_prefix": "SDG",
        "name": "Telaga Sadang Bukit Kapur Hijau",
        "category": "Wisata Geologi & Danau",
        "location": "Desa Tlogosadang, Kec. Paciran, Kab. Lamongan",
        "base_price": 10000.0,
        "description": "Danau air alami berwarna kehijauan toska yang terbentuk di antara formasi tebing kapur putih vertikal yang megah, menjadi latar foto estetik dan panorama alam menawan di Pantura.",
        "image_url": "https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?auto=format&fit=crop&w=800&q=80",
        "ticket_name": "Tiket Masuk Telaga Sadang"
    },
    {
        "code_prefix": "GRT",
        "name": "Wisata Sejarah Gunung Ratu",
        "category": "Wisata Alam & Legenda Sejarah",
        "location": "Desa Cancing, Kec. Ngimbang, Kab. Lamongan",
        "base_price": 10000.0,
        "description": "Puncak bukit bersejarah yang dipercaya sebagai tempat petilasan dan makam Dewi Andong Sari, ibunda Mahapatih Gajah Mada dari Kerajaan Majapahit, dengan panorama alam hutan pegunungan yang sejuk.",
        "image_url": "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&w=800&q=80",
        "ticket_name": "Tiket Masuk Gunung Ratu Ngimbang"
    },
    {
        "code_prefix": "VDW",
        "name": "Monumen Sejarah Van Der Wijck",
        "category": "Wisata Sejarah Kolonial",
        "location": "Kompleks Kantor Pelabuhan Nelayan Brondong, Kab. Lamongan",
        "base_price": 5000.0,
        "description": "Monumen mercusuar setinggi 15 meter peninggalan pemerintah Hindia Belanda untuk mengenang para nelayan Brondong yang berani menyelamatkan korban tragedi tenggelamnya Kapal Mewah Van Der Wijck tahun 1936.",
        "image_url": "https://images.unsplash.com/photo-1544551763-46a013bb70d5?auto=format&fit=crop&w=800&q=80",
        "ticket_name": "Tiket Kunjungan Monumen Van Der Wijck"
    },
    {
        "code_prefix": "MSI",
        "name": "Museum Seni Islam Indonesia",
        "category": "Museum Edukasi & Teknologi AR",
        "location": "Jalan Raya Daendels Paciran, Kompleks WBL, Kab. Lamongan",
        "base_price": 20000.0,
        "description": "Museum sejarah kebudayaan Islam pertama di Indonesia yang dilengkapi teknologi modern Augmented Reality (AR), memamerkan artefak peradaban Islam Nusantara, Timur Tengah, dan Dinasti Utsmaniyah.",
        "image_url": "https://images.unsplash.com/photo-1565043589221-1a6fd9ae45c7?auto=format&fit=crop&w=800&q=80",
        "ticket_name": "Tiket Masuk Museum Seni Islam"
    },
    {
        "code_prefix": "ALN",
        "name": "Alun-Alun & Taman Tematik Bianglala Lamongan",
        "category": "Taman Kota & Rekreasi Publik",
        "location": "Pusat Kota Lamongan, Jalan KH. Wahid Hasyim, Kab. Lamongan",
        "base_price": 5000.0,
        "description": "Ruang terbuka hijau megah di jantung kota Lamongan dengan ikon pesawat tempur TNI AU, bianglala raksasa, arena bermain ramah anak, dan pusat jajanan kuliner Nasi Boran malam hari.",
        "image_url": "https://images.unsplash.com/photo-1519331379826-f10be5486c6f?auto=format&fit=crop&w=800&q=80",
        "ticket_name": "Tiket Wahana Bianglala Alun-Alun"
    }
]

# Knowledge base untuk tanya jawab seputar pariwisata Lamongan
FAQ_KNOWLEDGE = [
    {
        "keywords": ["tiket", "beli", "pesan", "reservasi", "harga", "cara booking"],
        "answer": "Untuk memesan tiket masuk wisata, Anda cukup klik menu **'Destinasi Wisata'**, pilih objek wisata yang ingin Anda kunjungi, tentukan tanggal kunjungan dan jumlah tiket, lalu selesaikan pembayaran via QRIS atau Transfer Bank. E-Ticket resmi ber-QR Code dengan enkripsi HMAC-SHA256 akan langsung terbit seketika!"
    },
    {
        "keywords": ["sunan drajat", "makam", "ziarah", "religi"],
        "answer": "Makam Sunan Drajat terletak di Kecamatan Paciran, Kab. Lamongan. Merupakan salah satu situs ziarah Walisongo utama dengan museum bersejarah peninggalan gamelan Singo Mengkok. Tiket dewasa Rp 10.000 dan tiket anak Rp 5.000."
    },
    {
        "keywords": ["wbl", "wisata bahari", "pantai", "wahana", "waterpark"],
        "answer": "Wisata Bahari Lamongan (WBL) adalah taman rekreasi pesisir ikonik di Paciran dengan puluhan wahana seru, kolam renang air tawar dan laut, rumah hantu, drop zone, serta bioskop 3D. Tiket terusan WBL seharga Rp 75.000."
    },
    {
        "keywords": ["namira", "masjid namira", "kiswah"],
        "answer": "Masjid Namira Lamongan berlokasi di Jl. Raya Mantup Km 5, Tikung. Daya tarik utamanya adalah potongan kain Kiswah Ka'bah asli dari Masjidil Haram Arab Saudi yang terpasang di mihrab masjid, serta suasana arsitektur modern yang teduh."
    },
    {
        "keywords": ["sukodadi", "carnival"],
        "answer": "Sukodadi Carnival berada di Jalan Raya Pantura Sukodadi. Menyuguhkan atraksi sirkus, aneka wahana karnaval keluarga, rumah hantu, dan spot foto malam hari dengan harga tiket mulai Rp 30.000."
    },
    {
        "keywords": ["wego", "pesawat"],
        "answer": "WEGO (Wisata Edukasi Gondang Outbound) berlokasi di Sugio, Lamongan. Memiliki pesawat Boeing asli di tepi danau, jembatan gantung Pulau Cinta, dan area camping outbound yang cocok untuk keluarga dan pelajar."
    },
    {
        "keywords": ["maharani", "goa", "zoo", "kebun binatang"],
        "answer": "Maharani Zoo & Goa memadukan keajaiban stalaktit/stalagmit alami jutaan tahun dengan kebun binatang modern berisi satwa eksotis dari 5 benua. Lokasinya berdampingan langsung dengan WBL di Paciran."
    },
    {
        "keywords": ["kutang", "pantai kutang", "mangrove", "sunset"],
        "answer": "Pantai Kutang di Desa Labuhan, Kec. Brondong terkenal dengan jembatan kayu estetik sepanjang ratusan meter melintasi hutan mangrove menuju laut lepas dengan pemandangan matahari terbenam (sunset) yang sangat memukau."
    },
    {
        "keywords": ["kuliner", "makan", "soto", "tahu campur", "boran", "wingko"],
        "answer": "Kuliner khas Lamongan yang wajib Anda nikmati antara lain: Soto Ayam Lamongan bertabur koya gurih, Tahu Campur Lamongan dengan petis istimewa, Nasi Boran khas kota, Bandeng Bakar Asap Pantura, dan Wingko Babat legendaris!"
    },
    {
        "keywords": ["kalender", "event", "acara", "agenda", "jadwal", "2026", "bapperida"],
        "answer": "Berdasarkan Kalender Event Kabupaten Lamongan 2026 resmi dari Bapperida & Disbudporapar, ada 94 agenda kegiatan sepanjang tahun! Agenda besarnya meliputi: Festival Kupatan Tanjung Kodok, Haul Akbar Sunan Drajat, Kirab Budaya Hari Jadi Lamongan (HJL ke-457), Gebyar Seni Tari Boran, Lamongan Tempo Doeloe, dan Festival Nelayan Pantura."
    }
]


def resolve_date_target(range_type_str: str) -> tuple[date, int, str]:
    """
    Menghitung target tanggal berdasarkan range (besok, 1 bulan lagi, 1 tahun lagi)
    Return: (target_date, days_diff, label)
    """
    today = date.today()
    range_clean = (range_type_str or '').lower().strip()

    if any(k in range_clean for k in ['h-1', 'h1', 'besok', 'tomorrow', '1 hari', 'sehari']):
        target_date = today + timedelta(days=1)
        days_diff = 1
        label = "H-1 Hari (Besok!)"
    elif any(k in range_clean for k in ['1 bulan', 'bulan depan', 'sebulan', '30 hari', 'h-30', 'h30', 'month']):
        target_date = today + timedelta(days=30)
        days_diff = 30
        label = "1 Bulan Lagi (H-30 Hari)"
    elif any(k in range_clean for k in ['1 tahun', 'tahun depan', 'setahun', '365 hari', 'year']):
        target_date = today + timedelta(days=365)
        days_diff = 365
        label = "1 Tahun ke Depan (Agenda Mendatang)"
    elif any(k in range_clean for k in ['2 bulan', '60 hari']):
        target_date = today + timedelta(days=60)
        days_diff = 60
        label = "2 Bulan ke Depan"
    elif any(k in range_clean for k in ['6 bulan', 'setengah tahun']):
        target_date = today + timedelta(days=180)
        days_diff = 180
        label = "6 Bulan ke Depan"
    else:
        target_date = today + timedelta(days=30)
        days_diff = 30
        label = "1 Bulan ke Depan (H-30 Hari)"

    return target_date, days_diff, label


def detect_ai_intent(user_msg: str) -> dict:
    """
    Menganalisis pesan pengguna dan mengidentifikasi apakah berniat:
    - Menambahkan event
    - Menambahkan destinasi wisata baru
    - Pertanyaan umum (FAQ CS)
    """
    msg = user_msg.lower().strip()

    if re.search(r'\b(?:tambah(?:kan)?|buat(?:kan)?|terbitkan|jadwalkan)\b.*\b(?:destinasi|wisata|lokasi)\b', msg):
        range_key = '1month'
        if any(r in msg for r in ['besok', 'h-1', 'h1', '1 hari']):
            range_key = 'h1'
        elif any(r in msg for r in ['1 tahun', 'tahun depan', 'setahun', '1 year']):
            range_key = '1year'
        elif any(r in msg for r in ['1 bulan', 'bulan depan', '30 hari']):
            range_key = '1month'
        return {"intent": "add_destination", "range": range_key}

    if re.search(r'\b(?:tambah(?:kan)?|buat(?:kan)?|terbitkan|jadwalkan)\b.*\b(?:event|acara|agenda|festival|kegiatan)\b', msg):
        range_key = '1month'
        if any(r in msg for r in ['besok', 'h-1', 'h1', '1 hari']):
            range_key = 'h1'
        elif any(r in msg for r in ['1 tahun', 'tahun depan', 'setahun']):
            range_key = '1year'
        elif any(r in msg for r in ['1 bulan', 'bulan depan', '30 hari']):
            range_key = '1month'
        return {"intent": "add_event", "range": range_key}

    return {"intent": "chat"}


def generate_cs_reply(user_msg: str) -> str:
    """
    Menghasilkan respon customer service ramah khas Jawa Timuran / Megilan
    """
    msg = user_msg.lower().strip()

    for item in FAQ_KNOWLEDGE:
        if any(kw in msg for kw in item["keywords"]):
            return f"👋 **Halo dulur Megilan!**\n\n{item['answer']}\n\nAda lagi yang bisa Megi bantu seputar agenda wisata, tiket, atau destinasi di Kabupaten Lamongan?"

    if any(s in msg for s in ['halo', 'hai', 'pagi', 'siang', 'sore', 'malam', 'assalamualaikum', 'megibot', 'megi', 'tanya megi']):
        return (
            "👋 **Halo! Selamat datang di Layanan AI Customer Service MegiLoka Lamongan (Tanya Megi)!**\n\n"
            "Saya **Megi**, asisten cerdas resmi Dinas Pariwisata dan Kebudayaan Kab. Lamongan. Saya menguasai data 32+ destinasi wisata dan 94 agenda resmi Kalender Event Lamongan 2026 dari Bapperida!\n\n"
            "Saya bisa membantu Anda:\n"
            "1. 💬 Menjawab pertanyaan seputar info destinasi wisata, tiket, dan rute perjalanan.\n"
            "2. ⚡ **Menerbitkan Event Baru secara instan** (untuk besok H-1, 1 bulan lagi, atau 1 tahun ke depan).\n"
            "3. 🏖️ **Menerbitkan Destinasi Wisata Baru** yang langsung tayang di Beranda MegiLoka & memicu notifikasi pengunjung (guest)!\n\n"
            "Silakan pilih aksi cepat di atas atau tanyakan hal yang ingin Anda ketahui!"
        )

    return (
        "Terima kasih atas pesan Anda! Sebagai AI Concierge MegiLoka Lamongan, saya siap membantu Anda menjelajahi keindahan bumi Megilan.\n\n"
        "Anda dapat meminta saya menerbitkan event atau lokasi wisata baru secara langsung, misalnya:\n"
        "- *'Tambahkan event besok (H-1)'*\n"
        "- *'Tambahkan event festival untuk 1 bulan ke depan'*\n"
        "- *'Tambahkan destinasi wisata baru yang buka 1 bulan lagi'*\n"
        "- *'Tambahkan destinasi baru untuk tahun depan'*\n\n"
        "Setiap item yang berjarak 1 hari atau 1 bulan sebelum berlangsung akan **langsung otomatis muncul di Beranda dan membunyikan notifikasi untuk wisatawan (guest)**! 🚀"
    )
