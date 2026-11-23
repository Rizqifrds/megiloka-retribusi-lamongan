"""A trained intent router with read-only calendar and database retrieval."""
from datetime import date
import re

from models import Destination, Event, Promo
from ai.dates import MONTH_LOOKUP, format_date, parse_period, today_wib
from ai.intent_model import predict_intent
from utils.lamongan_calendar import POSTER_YEAR, poster_events

PROVENANCE = '\n\nSumber: data aplikasi MegiLoka. Jadwal/data awal belum diverifikasi ke penyelenggara; konfirmasi sebelum berkunjung.'
OFFICIAL_SOURCE = f'Kalender resmi Lamongan {POSTER_YEAR}'
OFFICIAL_CALENDAR_URL = '/calendar#poster-calendar-title'
HELP = ('Saya membantu informasi wisata Lamongan: jadwal dan detail event, lokasi destinasi, harga tiket, serta cara pemesanan. '
        'Coba “Event apa saja besok?”, “Kapan Festival Kupatan?”, atau “Berapa harga tiket Pantai Kutang?”.')
# Remove query grammar, but keep identifying words: unknown names must not match
# merely because they contain generic terms such as "Festival" or "Lamongan".
STOP = set('''apa apakah adakah saja ada yang akan untuk dan atau di ke dari pada dengan dalam masih saya tolong tampilkan tunjukkan daftar cari carikan lihat informasi informasikan info tentang ceritakan jelaskan ingin tahu mau bisa boleh ya dong itu ini tersebut wisata pariwisata destinasi tempat objek lokasi alamat lengkap letak letaknya daerah mana dimana terletak bagaimana kegiatan event acara agenda kalender jadwal festival akbar lamongan kapan tanggal pelaksanaan dilaksanakan dilangsungkan diselenggarakan diselenggarakannya berlangsung berlangsungnya diadakan penyelenggaraan mulai dimulai selesai berakhir sudah lewat belum detail rincian uraian deskripsi penjelasan tema isi berapa hari lagi pukul jam berapakah harganya harga tarif biaya ongkos masuk tiket karcis dewasa anak retribusi rupiah bayar terbaru promo diskon potongan saat sekarang kunjungan buka tutup dibuka beroperasi operasional sampai setiap hari minggu bulan tahun depan besok lusa kemarin akhir pekan weekend mendatang terdekat baru liburan pagi siang sore malam waktu selama esok tersedia tercatat'''.split()) | set(MONTH_LOOKUP)
ALIASES = {
    'wisata bahari lamongan': 'wbl', 'goa maharani': 'maharani', 'sundra': 'sunan drajat',
    'museum seni islam indonesia': 'indonesia islamic art museum',
    'pohon trinil': 'akar langit trinil', 'gunung mas mantup': 'istana gunung mas',
}
STOP.update(('pekan', 'resmi', 'kabupaten', 'budaya', 'kebudayaan', 'parkir', 'parkirnya'))


def tokens(text):
    msg = text.casefold()
    for alias, expanded in ALIASES.items():
        msg = re.sub(r'\b' + re.escape(alias) + r'\b', expanded, msg)
    return {t for t in re.findall(r'[a-z]+', msg) if t not in STOP and len(t) > 1}


def matches(message, records):
    query = tokens(message)
    if not query:
        return []
    scored = []
    for record in records:
        name = tokens(record.name)
        overlap = query & name
        # Require all identifying query words, avoiding unrelated partial matches.
        if overlap and len(overlap) / len(query) >= 0.75:
            scored.append(record)
    return scored


def source_event(event):
    return {'label': f'{event.name} — {format_date(event.event_date)}', 'url': '/calendar', 'type': 'event', 'id': event.id}


def source_destination(dest):
    return {'label': dest.name, 'url': f'/destinations/{dest.id}', 'type': 'destination', 'id': dest.id}


def admission_summary(dest):
    if dest.admission_status == 'free':
        return dest.admission_info or 'Kunjungan gratis. Tidak perlu tiket masuk.'
    if dest.admission_info:
        return dest.admission_info
    return 'Tarif masuk belum terverifikasi. Konfirmasi ke pengelola.'


def event_summary(event, today, detail=False):
    days = (event.event_date - today).days
    status = f'sudah lewat {abs(days)} hari' if days < 0 else 'hari ini' if days == 0 else 'besok (H-1)' if days == 1 else f'{days} hari lagi'
    # The event schema has no venue field. A linked destination is a reference,
    # not proof that its address is the exact venue of the event.
    location = f'Referensi destinasi: {event.destination.name}' if event.destination else 'Lokasi rinci belum tersedia'
    text = f'• **{event.name}** — {format_date(event.event_date)} ({status}).\n  {location}.'
    if detail:
        text += '\n  Jam mulai dan selesai belum tersedia dalam data aplikasi.'
        if event.description:
            text += '\n  ' + event.description
    return text


def official_event_answer(message, today, intent, official_events, period):
    named = matches(message, official_events)
    if named and period:
        named = [event for event in named if event.start and event.start <= period[1] and event.end >= period[0]]
    if named:
        events = named
    elif intent == 'event_schedule' and not tokens(message):
        start, end = period[:2] if period else (today, date.max)
        events = [event for event in official_events if event.start and event.start <= end and event.end >= start]
    else:
        return None
    if not events:
        return None
    events.sort(key=lambda event: event.start or date.max)
    lines = [f'Agenda dari {OFFICIAL_SOURCE}:']
    for event in events[:8]:
        date_note = '' if event.start else ' (tanggal pastinya belum tercantum)'
        lines.append(f'• **{event.name}** — {event.date_label}{date_note}')
    if len(events) > 8:
        lines.append(f'Menampilkan 8 dari {len(events)} agenda. Lihat Kalender Event untuk jadwal lengkap.')
    lines.append(f'\nSumber: {OFFICIAL_SOURCE}. Jam belum tercantum di poster. Jadwal bersifat tentatif.')
    return '\n'.join(lines), [{'label': OFFICIAL_SOURCE, 'url': OFFICIAL_CALENDAR_URL}]


def event_answer(message, today, intent, official_events):
    try:
        period = parse_period(message, today)
    except (ValueError, OverflowError):
        return 'Tanggal tidak valid atau belum didukung. Gunakan satu tanggal lengkap, misalnya 6 November 2026, atau “bulan depan”.', []
    official = official_event_answer(message, today, intent, official_events, period)
    if official:
        return official
    all_events = Event.query.order_by(Event.event_date.asc(), Event.id.asc()).all()
    selected = matches(message, all_events)
    destinations = Destination.query.filter_by(is_active=True).all()
    dest_matches = matches(message, destinations)
    identifying_words = tokens(message)
    if selected:
        if period:
            selected = [e for e in selected if period[0] <= e.event_date <= period[1]]
        if len(selected) > 1:
            choices = '\n'.join(f'• {e.name} — {format_date(e.event_date)}' for e in selected[:10])
            return 'Ada beberapa agenda yang cocok. Silakan pilih dengan menyebut nama dan tanggal lengkap:\n' + choices + PROVENANCE, [source_event(e) for e in selected[:10]]
        if not selected:
            return 'Belum ada event dengan nama dan tanggal tersebut dalam data aplikasi.' + PROVENANCE, []
        return event_summary(selected[0], today, detail=True) + PROVENANCE, [source_event(selected[0])]
    if identifying_words and not dest_matches:
        return 'Saya tidak menemukan nama event atau destinasi tersebut. Sebutkan nama yang tercantum di Kalender Event atau Destinasi Wisata.' + PROVENANCE, [{'label': 'Kalender Event MegiLoka', 'url': '/calendar'}]
    if intent == 'event_detail' and not dest_matches:
        return 'Event mana yang ingin Anda ketahui? Sebutkan nama acara, misalnya Festival Kupatan.', []
    events = all_events
    if dest_matches:
        ids = {d.id for d in dest_matches}
        events = [e for e in events if e.destination_id in ids]
    if period:
        events = [e for e in events if period[0] <= e.event_date <= period[1]]
        label = f'{format_date(period[0])} sampai {format_date(period[1])}' if period[0] != period[1] else format_date(period[0])
    else:
        events = [e for e in events if e.event_date >= today]
        label = f'mendatang, dihitung dari {format_date(today)} WIB'
    if not events:
        return f'Belum ada event tercatat untuk {label}. Ini berarti data belum tersedia, bukan kepastian tidak ada acara.' + PROVENANCE, []
    text = f'Agenda {label}:\n\n' + '\n\n'.join(event_summary(e, today) for e in events[:8])
    if len(events) > 8:
        text += f'\n\nMenampilkan 8 dari {len(events)} agenda. Persempit tanggal atau lihat Kalender Event.'
    text += '\n\nJam mulai event belum tersedia dalam data aplikasi.'
    return text + PROVENANCE, [source_event(e) for e in events[:8]]


def rupiah(value):
    return 'Rp' + f'{value:,.0f}'.replace(',', '.')


def destination_answer(message, today, intent):
    destinations = Destination.query.filter_by(is_active=True).order_by(Destination.name).all()
    selected = matches(message, destinations)
    if len(selected) > 1:
        return 'Ada beberapa destinasi yang cocok. Silakan pilih nama lengkap:\n' + '\n'.join('• ' + d.name for d in selected[:10]), [source_destination(d) for d in selected[:10]]
    if not selected:
        if intent == 'destination_info' and not tokens(message):
            selected = destinations[:8]
            return 'Destinasi yang tercatat di MegiLoka:\n' + '\n'.join(f'• {d.name} — {d.location}' for d in selected) + '\nLihat katalog untuk daftar lengkap atau sebutkan nama destinasi.' + PROVENANCE, [source_destination(d) for d in selected]
        return 'Sebutkan nama destinasi yang tercantum di MegiLoka, misalnya Pantai Kutang atau WBL. Saya tidak menemukan kecocokan yang cukup jelas.', [{'label': 'Destinasi Wisata', 'url': '/destinations'}]
    d = selected[0]
    sources = [source_destination(d)]
    if intent == 'parking':
        return f'Parkir **{d.name}**: {d.parking_info or "Tarif parkir belum terverifikasi."}', sources
    if intent == 'opening_hours':
        return f'Jam buka/tutup dan hari operasional **{d.name}** belum tersedia dalam data aplikasi. Konfirmasi ke pengelola sebelum berkunjung.' + PROVENANCE, sources
    if intent == 'ticket_price':
        text = f'Harga tiket **{d.name}** pada data aplikasi:\n'
        if d.available_tickets:
            text += '\n'.join(f'• {t.name}: **{rupiah(t.price)}** per tiket' for t in d.available_tickets)
        else:
            text += admission_summary(d)
        promos = Promo.query.filter(Promo.destination_id == d.id, Promo.valid_from <= today, Promo.valid_until >= today).all() if d.admission_status == 'paid' else []
        if promos:
            text += '\n\nPromo destinasi yang tercatat:\n' + '\n'.join(f'• {p.name}, berlaku sampai {format_date(p.valid_until)}.' for p in promos)
            text += '\nKonfirmasi syarat promo ke pengelola. Harga di atas mengikuti jenis tiket pada formulir pemesanan; diskon belum otomatis diterapkan oleh alur booking saat ini.'
        text += '\nTarif dapat berubah; periksa kembali sebelum memesan.'
        if d.available_tickets:
            sources.append({'label': 'Lihat pilihan tiket', 'url': f'/booking/{d.id}'})
        return text + PROVENANCE, sources
    text = f'**{d.name}**\nAlamat: {d.location}\nKategori: {d.category}'
    if d.description:
        text += '\n' + d.description
    text += f'\nInformasi masuk: {admission_summary(d)}'
    text += f'\nParkir: {d.parking_info or "Tarif belum terverifikasi."}'
    if d.opening_date and d.opening_date > today:
        text += f'\nTanggal pembukaan yang tercatat: {format_date(d.opening_date)}; konfirmasi status pembukaan ke pengelola.'
    return text + PROVENANCE, sources


def _holiday_answer(message, today, holiday_view):
    query = message.casefold()
    if not re.search(r'\b(?:tanggal merah|libur nasional)\b', query):
        return None
    kinds = set()
    if re.search(r'\b(?:event|acara|agenda|festival)\b', query):
        kinds.add('Event')
    if re.search(r'\b(?:promo|diskon)\b', query):
        kinds.add('Promo')
    if not kinds:
        return None
    try:
        period = parse_period(message, today)
        feed = holiday_view(today, period)
        matches = [item for item in feed['matches'] if item['kind'] in kinds]
        if matches:
            reply = '\n'.join(f"{item['kind']}: **{item['name']}** · {item['date']} ({item['holiday']})"
                              for item in matches[:5])
        elif feed['sources_ready'] and feed['holidays']:
            reply = 'Belum ada pengumuman resmi yang sesuai dengan pertanyaan itu untuk libur nasional.'
        elif feed['sources_ready'] and period:
            reply = 'Saya belum menemukan tanggal libur nasional dalam rentang itu pada jadwal yang sudah diperiksa.'
        else:
            reply = 'Pemeriksaan jadwal dari sumber resmi belum lengkap. Lihat pembaruan di beranda.'
    except ValueError as exc:
        reply = str(exc)
    return {'intent': 'holiday_updates', 'confidence': 1.0, 'reply': reply,
            'sources': [{'label': 'Promo Wisata di beranda', 'url': '/#agenda-libur'}],
            'as_of': today.isoformat(), 'timezone': 'Asia/Jakarta'}


def answer_question(message: str, today=None, holiday_view=None) -> dict:
    today = today or today_wib()
    if holiday_view:
        holiday_answer = _holiday_answer(message, today, holiday_view)
        if holiday_answer:
            return holiday_answer
    prediction = predict_intent(message)
    intent = prediction['intent']
    if re.search(r'\bparkir(?:nya)?\b', message.casefold()):
        intent = 'parking'
        prediction = {**prediction, 'intent': intent, 'confidence': 1.0}
    official_events = []
    if intent in ('event_schedule', 'event_detail', 'opening_hours', 'out_of_scope', 'uncertain'):
        official_events = list(poster_events(today))
        query = tokens(message)
        if intent not in ('event_schedule', 'event_detail') and query and any(query == tokens(event.name) for event in official_events):
            intent = 'event_detail'
            prediction = {**prediction, 'intent': intent, 'confidence': 1.0}
    if intent in ('event_schedule', 'event_detail'):
        reply, sources = event_answer(message, today, intent, official_events)
    elif intent in ('destination_info', 'ticket_price', 'opening_hours', 'parking'):
        reply, sources = destination_answer(message, today, intent)
    elif intent == 'booking':
        reply = ('Buka Destinasi Wisata dan pilih tempat dengan tombol Pesan Tiket. Isi nama, pilih tanggal kunjungan dan jumlah tiket, lalu buat reservasi. '
                 'Tunjukkan nomor reservasi saat bayar tunai di loket. Tiket QR tersedia setelah petugas mengonfirmasi pembayaran.')
        sources = [{'label': 'Pilih destinasi untuk memesan', 'url': '/destinations'}]
    elif intent == 'greeting':
        reply, sources = 'Halo! Saya Megi, asisten lokal proyek MegiLoka. ' + HELP, []
    else:
        reply, sources = 'Saya belum memahami pertanyaan itu dengan cukup yakin. ' + HELP, []
    return {**prediction, 'reply': reply, 'sources': sources, 'as_of': today.isoformat(), 'timezone': 'Asia/Jakarta'}
