"""Conservative Indonesian date parsing. Inclusive periods, never invented dates."""
import calendar
from datetime import date, datetime, timedelta, timezone
import re

MONTHS = ('Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember')
MONTH_LOOKUP = {name.lower(): i for i, name in enumerate(MONTHS, 1)}
WIB = timezone(timedelta(hours=7), 'Asia/Jakarta')


def today_wib() -> date:
    return datetime.now(WIB).date()


def format_date(value: date) -> str:
    return f'{value.day} {MONTHS[value.month - 1]} {value.year}'


def parse_period(message: str, today: date):
    msg = message.casefold()
    iso = re.findall(r'\b(\d{4})-(\d{1,2})-(\d{1,2})\b', msg)
    named = re.findall(r'\b(\d{1,2})\s+(' + '|'.join(MONTH_LOOKUP) + r')(?:\s+(\d{4}))?\b', msg)
    numeric = re.findall(r'\b(\d{1,2})([/-])(\d{1,2})\2(\d{4})\b', msg)
    if re.search(r'\b\d{1,4}\.\d{1,2}\.\d{1,4}\b', msg):
        raise ValueError('Format tanggal belum didukung.')
    if len(iso) + len(named) + len(numeric) > 1:
        raise ValueError('Sebutkan satu tanggal atau satu rentang seperti bulan depan.')
    if iso or named or numeric:
        if iso:
            y, m, d = map(int, iso[0])
        elif named:
            d, m, y = named[0]
            d, m, y = int(d), MONTH_LOOKUP[m], int(y or today.year)
        else:
            d, _, m, y = numeric[0]
            d, m, y = int(d), int(m), int(y)
        target = date(y, m, d)
        return target, target, format_date(target)
    relative_day = re.search(r'\btanggal\s+(\d{1,2})\s+bulan\s+(ini|depan)\b', msg)
    if relative_day:
        month = today.month + (relative_day[2] == 'depan')
        year = today.year + (month == 13)
        month = 1 if month == 13 else month
        target = date(year, month, int(relative_day[1]))
        return target, target, format_date(target)
    for word, offset in [('hari ini', 0), ('besok', 1), ('lusa', 2), ('kemarin', -1)]:
        if re.search(r'\b' + word + r'\b', msg):
            target = today + timedelta(days=offset)
            return target, target, word
    if 'akhir pekan' in msg or 'weekend' in msg:
        start = today + timedelta(days=5-today.weekday())
        if 'depan' in msg:
            start += timedelta(days=7)
        return start, start + timedelta(days=1), 'akhir pekan'
    if 'minggu ini' in msg or 'minggu depan' in msg:
        start = today - timedelta(days=today.weekday())
        if 'minggu depan' in msg:
            start += timedelta(days=7)
        return start, start + timedelta(days=6), 'minggu depan' if 'minggu depan' in msg else 'minggu ini'
    if 'bulan ini' in msg or 'bulan depan' in msg:
        month = today.month + ('bulan depan' in msg)
        year = today.year
        if month == 13:
            year, month = year + 1, 1
        return date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1]), f'{MONTHS[month-1]} {year}'
    if 'tahun depan' in msg or 'tahun ini' in msg:
        year = today.year + ('tahun depan' in msg)
        return date(year, 1, 1), date(year, 12, 31), str(year)
    month_only = re.search(r'\b(' + '|'.join(MONTH_LOOKUP) + r')(?:\s+(\d{4}))?\b', msg)
    if month_only:
        month, year = MONTH_LOOKUP[month_only[1]], int(month_only[2] or today.year)
        return date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1]), f'{MONTHS[month-1]} {year}'
    interval = re.search(r'\b(\d+)\s+hari\s+(lagi|ke depan)\b', msg)
    if interval:
        days = int(interval[1])
        if days > 3660:
            raise ValueError('Rentang terlalu jauh.')
        end = today + timedelta(days=days)
        return (end if interval[2] == 'lagi' else today), end, interval[0]
    day_only = re.search(r'\btanggal\s+(\d{1,2})\b', msg)
    if day_only:
        target = date(today.year, today.month, int(day_only[1]))
        return target, target, format_date(target)
    # Reject recognizable unsupported date expressions rather than ignoring them.
    if re.search(r'\b(?:tanggal|bulan|tahun)\s+\d|\b\d+\s+(?:bulan|tahun)\s+lagi\b|\b\d{1,4}[./-]\d{1,2}[./-]\d{1,4}\b', msg):
        raise ValueError('Gunakan tanggal lengkap, misalnya 6 November 2026, atau bulan depan.')
    return None
