"""Fetch public announcements and match their published dates to national holidays."""

import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from html import unescape
from pathlib import Path
from tempfile import NamedTemporaryFile
from threading import Event, Lock, Thread
from time import monotonic
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen

from ai.dates import MONTH_LOOKUP, WIB, format_date, today_wib

DISTRICT = 'https://disbudporapar.lamongankab.go.id'
WBL = 'https://wisatabaharilamongan.com'
INTERVAL = 300
LOG = logging.getLogger(__name__)
MONTH = '|'.join(MONTH_LOOKUP)
DAY = rf'(?P<day>\d{{1,2}})(?:\s+(?P<month>{MONTH})(?:\s+(?P<year>\d{{4}}))?)?'
DATES = re.compile(
    rf'\b{DAY}(?:\s*(?:[-–—]|sampai|hingga|s\s*[/\.]\s*d\.?)\s*'
    rf'(?P<end_day>\d{{1,2}})\s+(?P<end_month>{MONTH})\s+(?P<end_year>\d{{4}}))?(?!\w)',
    re.I,
)
DATE_LABEL = re.compile(
    r'^(?:[^\w\n]*)(?P<label>periode promo|promo berlaku|masa berlaku promo|'
    r'tanggal acara|tanggal pelaksanaan|jadwal acara|dilaksanakan pada|berlangsung pada|tanggal)'
    r'\s*[:\s]+(?:[A-Za-z]+,\s*)?',
    re.I,
)
UNCONFIRMED = re.compile(r'\b(?:dibatalkan|ditunda|tentatif|batal digelar|batal berlangsung)\b', re.I)


def _fetch(url):
    with urlopen(url, timeout=8) as response:
        body = response.read(2_000_001)
    if len(body) > 2_000_000:
        raise ValueError('Response exceeds limit')
    return body.decode('utf-8')


def _text(html):
    html = re.sub(r'<(script|style)\b[^>]*>.*?</\1\s*>', '', html, flags=re.I | re.S)
    html = re.sub(r'<br\b[^>]*>|</(?:p|div|li|h[1-6])\s*>', '\n', html, flags=re.I)
    return unescape(re.sub(r'<[^>]+>', '', html)).replace('\u2060', '')


def holiday_source(year):
    return f'https://www.setneg.go.id/baca/index/inilah_skb_3_menteri_libur_nasional_dan_cuti_bersama_{year}'


def parse_holidays(html, year):
    _, marker, text = _text(html).partition(f'daftar lengkap hari libur nasional {year}')
    section, end, _ = text.partition('cuti bersama')
    if not marker or not end:
        raise ValueError('National holiday list missing')
    holidays = {}
    pattern = rf'(\d{{1,2}})(?:\s*[-–]\s*(\d{{1,2}}))?\s+({MONTH})(?:\s+{year})?(?:\s+\([^)]*\))?\s*:\s*([^\n]+)'
    for first, last, month, name in re.findall(pattern, section, re.I):
        for day in range(int(first), int(last or first) + 1):
            key = date(year, MONTH_LOOKUP[month.lower()], day).isoformat()
            holidays[key] = name.strip().rstrip(';')
    if not 10 <= len(holidays) <= 30 or f'{year}-01-01' not in holidays:
        raise ValueError('Incomplete national holiday list')
    return holidays


def _iso_date(value):
    if not isinstance(value, str):
        raise ValueError('Explicit date required')
    if 'T' in value:
        moment = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return moment.astimezone(WIB).date() if moment.tzinfo else moment.date()
    return date.fromisoformat(value)


def _entry(kind, name, start, end, url):
    if name and start <= end:
        return {'kind': kind, 'name': name[:180], 'start': start.isoformat(),
                'end': end.isoformat(), 'url': url}
    return None


def _schema_nodes(value):
    if isinstance(value, list):
        for item in value:
            yield from _schema_nodes(item)
    elif isinstance(value, dict):
        yield value
        for key in ('@graph', 'mainEntity', 'offers', 'itemListElement', 'item'):
            yield from _schema_nodes(value.get(key))


def parse_announcements(html, title, url, category):
    text = _text(html)
    if UNCONFIRMED.search(title + ' ' + text):
        return []
    entries = []
    structured_schedule = False
    for block in re.findall(r"""<script\b[^>]*\btype=["']application/ld\+json["'][^>]*>(.*?)</script>""",
                            html, re.I | re.S):
        try:
            data = json.loads(block)
        except ValueError:
            continue
        for node in _schema_nodes(data):
            types = node.get('@type', [])
            types = types if isinstance(types, list) else [types]
            names = {item.rsplit('/', 1)[-1] for item in types if isinstance(item, str)}
            name = node.get('name')
            if not isinstance(name, str) or UNCONFIRMED.search(name):
                continue
            try:
                if names & {'Event', 'Festival', 'MusicEvent', 'SportsEvent', 'ExhibitionEvent'}:
                    structured_schedule = True
                    status = node.get('eventStatus', 'EventScheduled')
                    if not isinstance(status, str) or status.rsplit('/', 1)[-1] not in {
                        'EventScheduled', 'EventRescheduled'
                    }:
                        continue
                    start = _iso_date(node.get('startDate'))
                    end = _iso_date(node.get('endDate') or node.get('startDate'))
                    entries.append(_entry('Event', _text(name).strip(), start, end, url))
                elif 'Offer' in names:
                    structured_schedule = True
                    start = _iso_date(node.get('validFrom'))
                    end = _iso_date(node.get('validThrough'))
                    entries.append(_entry('Promo', _text(name).strip(), start, end, url))
            except ValueError:
                continue
    if structured_schedule:
        return [entry for entry in entries if entry]

    if not title:
        return []
    for line in text.splitlines():
        label = DATE_LABEL.match(line.strip())
        if not label:
            continue
        promo = 'promo' in label['label'].lower()
        if not promo and category != 'Event':
            continue
        match = DATES.match(line.strip()[label.end():].lstrip())
        if not match or not (match['end_year'] or match['year']) or (promo and not match['end_day']):
            continue
        # Require a complete date phrase. An unsupported or truncated range must not become a one-day event.
        if line.strip()[label.end():].lstrip()[match.end():].strip(' .;,'):
            continue
        try:
            month = MONTH_LOOKUP[(match['month'] or match['end_month']).lower()]
            end_month = MONTH_LOOKUP[match['end_month'].lower()] if match['end_month'] else month
            end_year = int(match['end_year'] or match['year'])
            year = int(match['year']) if match['year'] else end_year - (month > end_month)
            start = date(year, month, int(match['day']))
            end = date(end_year, end_month, int(match['end_day'] or match['day']))
        except (ValueError, AttributeError):
            continue
        entry = _entry('Promo' if promo else 'Event', title, start, end, url)
        if entry:
            entries.append(entry)
    return entries


def _district_article(url, category):
    html = _fetch(url)
    title = re.search(r'<h1\b[^>]*\bid="judul-artikel"[^>]*>(.*?)</h1>', html, re.S)
    body = re.search(r'<div class="card-text">(.*?)</body>', html, re.S)
    if not title or not body:
        raise ValueError('Article format changed')
    scripts = ''.join(re.findall(r'<script\b[^>]*application/ld\+json[^>]*>.*?</script>', html, re.S))
    return parse_announcements(scripts + body[1], ' '.join(_text(title[1]).split()), url, category)


def _district_items(path, category):
    urls = dict.fromkeys(
        urljoin(DISTRICT, link)
        for link in re.findall(r'href="((?:' + re.escape(DISTRICT) + r')?/posting/\d+)"', _fetch(DISTRICT + path))
    )
    if not urls:
        raise ValueError('No article links found')
    entries = []
    failed = 0
    with ThreadPoolExecutor(max_workers=4) as pool:
        jobs = {url: pool.submit(_district_article, url, category) for url in list(urls)[:10]}
        for url, job in jobs.items():
            try:
                entries.extend(job.result())
            except (OSError, ValueError) as exc:
                failed += 1
                LOG.warning('Unable to read %s: %s', url, exc)
    if failed == len(jobs):
        raise ValueError('No articles could be read')
    return entries, failed == 0


def _wbl_items():
    api = WBL + '/wp-json/wp/v2'
    posts = json.loads(_fetch(api + '/posts?per_page=12&_fields=link,title,content'))
    promo = json.loads(_fetch(api + '/pages/3311?_fields=link,content'))
    if not isinstance(posts, list) or not isinstance(promo, dict):
        raise ValueError('Unexpected WordPress response')
    entries = []
    for post in [promo, *posts]:
        url = post['link']
        if urlsplit(url).scheme != 'https' or urlsplit(url).netloc != urlsplit(WBL).netloc:
            continue
        title = _text(post.get('title', {}).get('rendered', '')).strip()
        entries.extend(parse_announcements(post['content']['rendered'], title, url, 'Event' if post is not promo else 'Promo'))
    return entries


def _partner_items(url):
    if not _https_url(url):
        raise ValueError('Partner endpoint must be an HTTPS URL')
    data = json.loads(_fetch(Request(url, headers={'Accept': 'application/json'})))
    if not isinstance(data, dict) or not isinstance(data.get('items'), list):
        raise ValueError('Partner response requires an items list')
    entries = []
    seen = set()
    for row in data['items']:
        if not isinstance(row, dict):
            raise ValueError('Invalid partner item')
        identifier = row.get('id')
        if not isinstance(identifier, str) or not identifier.strip() or identifier in seen:
            raise ValueError('Partner item ID must be unique')
        seen.add(identifier)
        if row.get('status') in ('cancelled', 'postponed'):
            continue
        kind = {'event': 'Event', 'promo': 'Promo'}.get(row['kind'])
        name = row['title']
        if row.get('status') != 'published' or not kind or not isinstance(name, str) or not _https_url(row['url']):
            raise ValueError('Invalid partner announcement')
        start = date.fromisoformat(row['starts_on'])
        end = date.fromisoformat(row['ends_on'])
        entry = _entry(kind, name.strip(), start, end, row['url'])
        if not entry:
            raise ValueError('Partner announcement requires a name and valid dates')
        entries.append(entry)
    return entries


def _https_url(value):
    if not isinstance(value, str) or any(char.isspace() for char in value):
        return False
    url = urlsplit(value)
    return url.scheme == 'https' and bool(url.hostname) and url.username is None and url.password is None


class HolidayFeed:
    def __init__(self, cache_path, partner_url=''):
        self.path = Path(cache_path)
        self.partner_url = partner_url
        self.lock = Lock()
        self.worker = None
        self.partner_pending = Event()
        self.last_partner_signal = None
        try:
            self.snapshot = json.loads(self.path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            self.snapshot = {}

    def start(self):
        with self.lock:
            if self.worker is None:
                self.worker = Thread(target=self._run, name='holiday-feed', daemon=True)
                self.worker.start()

    def _run(self):
        next_sync = monotonic()
        while True:
            self.partner_pending.wait(max(0, next_sync - monotonic()))
            self.partner_pending.clear()
            try:
                if monotonic() >= next_sync:
                    self.sync()
                    next_sync = monotonic() + INTERVAL
                elif self.partner_url:
                    self._refresh({'partner': lambda: _partner_items(self.partner_url)})
            except Exception:
                LOG.exception('Holiday feed refresh failed')
                next_sync = monotonic() + INTERVAL

    def request_partner_refresh(self):
        with self.lock:
            now = monotonic()
            if self.last_partner_signal is not None and now - self.last_partner_signal < 10:
                return False
            self.last_partner_signal = now
            self.partner_pending.set()
        self.start()
        return True

    def sync(self, today=None):
        today = today or today_wib()
        years = {today.year, (today + timedelta(days=365)).year}
        sources = {
            'agenda': lambda: _district_items('/kategori/agenda', 'Event'),
            'pengumuman': lambda: _district_items('/kategori/Pengumuman', 'Promo'),
            'wbl': _wbl_items,
        }
        sources.update({
            str(year): lambda year=year: parse_holidays(_fetch(holiday_source(year)), year)
            for year in years
        })
        if self.partner_url:
            sources['partner'] = lambda: _partner_items(self.partner_url)
        self._refresh(sources)

    def _refresh(self, sources):
        snapshot = self.snapshot.copy()
        with ThreadPoolExecutor(max_workers=len(sources)) as pool:
            jobs = {key: pool.submit(load) for key, load in sources.items()}
            for key, job in jobs.items():
                try:
                    result = job.result()
                    data, complete = result if isinstance(result, tuple) else (result, True)
                    snapshot[key] = {'data': data, 'complete': complete, 'checked': datetime.now(WIB).isoformat()}
                except Exception as exc:
                    LOG.warning('Holiday feed source %s unavailable (%s)', key, type(exc).__name__)

        # Publish one consistent snapshot even when a source is temporarily unavailable.
        self.snapshot = snapshot
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(mode='w', encoding='utf-8', dir=self.path.parent, delete=False) as file:
            temp = Path(file.name)
            json.dump(snapshot, file, ensure_ascii=False)
        try:
            temp.replace(self.path)
        finally:
            temp.unlink(missing_ok=True)

    def view(self, today=None, period=None):
        today = today or today_wib()
        horizon = (today + timedelta(days=365)).isoformat()
        now = datetime.now(WIB)
        snapshot = self.snapshot
        holidays = {}
        reviewed_years = set()
        for key, source in snapshot.items():
            if key.isdecimal():
                holidays.update(source['data'])
                if now - datetime.fromisoformat(source['checked']) <= timedelta(days=7):
                    reviewed_years.add(int(key))
        lower = max(today.isoformat(), period[0].isoformat()) if period else today.isoformat()
        upper = min(horizon, period[1].isoformat()) if period else horizon
        days = sorted(day for day in holidays if lower <= day <= upper)
        matches = {}
        fresh_sources = []
        keys = ('agenda', 'pengumuman', 'wbl')
        if self.partner_url:
            keys = ('partner', *keys)
        for key in keys:
            source = snapshot.get(key)
            if not source:
                continue
            age = now - datetime.fromisoformat(source['checked'])
            if age <= timedelta(minutes=15) and source.get('complete', True):
                fresh_sources.append(source['checked'])
            if age > timedelta(hours=24):
                continue
            for item in source['data']:
                days_covered = [day for day in days if item['start'] <= day <= item['end']]
                if not days_covered:
                    continue
                day = days_covered[0]
                identity = (item['kind'], ' '.join(re.findall(r'\w+', item['name'].casefold())),
                            item['start'], item['end'])
                matches.setdefault(identity, {**item, 'day': day, 'date': format_date(date.fromisoformat(day)),
                                              'holiday': holidays[day]})
        return {
            'holidays': [{'name': holidays[day], 'date': format_date(date.fromisoformat(day)),
                          'url': holiday_source(int(day[:4]))} for day in days[:3]],
            'matches': sorted(matches.values(), key=lambda item: (item['day'], item['name']))[:12],
            'sources_ready': len(fresh_sources) == len(keys) and {int(lower[:4]), int(upper[:4])} <= reviewed_years,
            'checked': datetime.fromisoformat(min(fresh_sources)).strftime('%d/%m/%Y %H:%M WIB')
            if fresh_sources else None,
        }
