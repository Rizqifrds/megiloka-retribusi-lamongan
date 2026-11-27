import json
import sys
import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services import agenda_feed as holiday_feed


class HolidayFeedTests(unittest.TestCase):
    def test_instagram_wbl_imports_explicit_dates_from_caption(self):
        posts = [
            {'caption': 'Promo WBL\nPeriode promo: 20–30 November 2026',
             'permalink': 'https://www.instagram.com/p/promo1/'},
            {'caption': 'Festival WBL\nTanggal acara: 25 November 2026',
             'permalink': 'https://www.instagram.com/p/event1/'},
            {'caption': 'Promo tanpa tanggal',
             'permalink': 'https://www.instagram.com/p/poster1/'},
        ]
        response = {'business_discovery': {
            'username': 'wisatabaharilamonganpark', 'media': {'data': posts},
        }}
        with patch.object(holiday_feed, '_fetch', return_value=json.dumps(response)) as fetch:
            items = holiday_feed._instagram_items('v27.0', '123', 'test-token')
        request = fetch.call_args.args[0]
        self.assertNotIn('test-token', request.full_url)
        self.assertEqual(request.get_header('Authorization'), 'Bearer test-token')
        self.assertEqual([(row['kind'], row['start']) for row in items],
                         [('Promo', '2026-11-20'), ('Event', '2026-11-25')])

    def test_homepage_feed_uses_promo_dates_without_a_holiday_calendar(self):
        import app as application

        today = date(2026, 11, 20)
        url = 'https://example.org/promo'
        entries = [
            holiday_feed._entry('Promo', 'Promo hari biasa', date(2026, 11, 19), today, url),
            holiday_feed._entry('Promo', 'Promo minggu depan', date(2026, 11, 23), date(2026, 11, 24), url),
            holiday_feed._entry('Promo', 'Promo lama', date(2026, 11, 17), date(2026, 11, 19), url),
            holiday_feed._entry('Event', 'Agenda wisata', today, today, url),
        ]
        with TemporaryDirectory() as directory:
            feed = holiday_feed.HolidayFeed(Path(directory) / 'feed.json')
            feed._refresh({'wbl': lambda: entries})
            result = feed.promo_view(today)
            self.assertEqual([(item['name'], item['active']) for item in result['items']],
                             [('Promo hari biasa', True), ('Promo minggu depan', False)])
            with patch.object(application.holiday_feed, 'promo_view', return_value=result), \
                 patch.object(application, 'get_upcoming_items', return_value=[]), \
                 patch.dict(application.app.config, TESTING=True):
                html = application.app.test_client().get('/agenda-libur/pembaruan').get_data(as_text=True)
            self.assertIn('Promo hari biasa', html)
            self.assertIn('Segera berlaku', html)
            self.assertNotIn('Agenda wisata', html)
            self.assertNotIn('Libur nasional', html)

    def test_partner_refresh_and_webhook(self):
        import app as application

        url = 'https://example.org/calendar.json'
        row = {'id': 'year-end', 'kind': 'event', 'title': 'Festival Mitra',
               'starts_on': '2026-12-25', 'ends_on': '2026-12-25',
               'status': 'published', 'url': 'https://example.org/festival'}
        today = date(2026, 12, 24)
        with TemporaryDirectory() as directory:
            feed = holiday_feed.HolidayFeed(Path(directory) / 'feed.json', partner_url=url)
            with patch.object(application, 'holiday_feed', feed), \
                 patch.dict(application.app.config, TESTING=True, HOLIDAY_WEBHOOK_TOKEN='test-token'), \
                 patch.object(feed, 'start'):
                client = application.app.test_client()
                route = '/api/agenda-libur/webhook'
                self.assertEqual(client.post(route).status_code, 401)
                headers = {'Authorization': 'Bearer test-token'}
                self.assertEqual(client.post(route, headers=headers).status_code, 202)
                self.assertTrue(feed.partner_pending.is_set())
                self.assertEqual(client.post(route, headers=headers).status_code, 429)

            def load_partner():
                return holiday_feed._partner_items(feed.partner_url)

            feed._refresh({'2026': lambda: {'2026-12-25': 'Natal'}})
            with patch.object(holiday_feed, '_fetch', side_effect=lambda request: json.dumps({'items': [row]})):
                feed._refresh({'partner': load_partner})
                self.assertEqual([item['name'] for item in feed.view(today)['matches']], ['Festival Mitra'])
                row.update(starts_on='2026-12-27', ends_on='2026-12-27')
                feed._refresh({'partner': load_partner})
                self.assertEqual(feed.view(today)['matches'], [])
                row.update(starts_on='2026-12-25', ends_on='2026-12-25', status='cancelled')
                feed._refresh({'partner': load_partner})
                self.assertEqual(feed.view(today)['matches'], [])

    def test_refresh_publishes_dated_matches_and_removes_cancelled_or_expired_items(self):
        url = holiday_feed.DISTRICT + '/posting/123'
        html = '<p>Periode promo: 24 – 26 Desember 2026</p>'
        promo = holiday_feed.parse_announcements(html, 'Promo akhir tahun', url, 'Promo')
        self.assertEqual(promo[0]['start'], '2026-12-24')
        event = {'@type': 'Festival', 'name': 'Festival Natal', 'startDate': '2026-12-25'}
        dated_event = f'<script type="application/ld+json">{json.dumps(event)}</script>'
        confirmed = holiday_feed.parse_announcements(dated_event, 'Festival Natal', url, 'Event')
        event['eventStatus'] = 'https://schema.org/EventCancelled'
        cancelled = f'<script type="application/ld+json">{json.dumps(event)}</script>'
        cancelled += '<p>Tanggal acara: 25 Desember 2026</p>'
        self.assertEqual(holiday_feed.parse_announcements(cancelled, 'Festival Natal', url, 'Event'), [])
        self.assertEqual(holiday_feed.parse_announcements('<p>25 Desember 2026</p>', 'Poster', url, 'Promo'), [])

        today = date(2026, 12, 24)
        with TemporaryDirectory() as directory:
            cache_path = Path(directory) / 'holiday-feed.json'
            feed = holiday_feed.HolidayFeed(cache_path)
            holiday_data = {'2026-12-25': 'Natal'}
            articles = {'Event': confirmed, 'Promo': promo}
            with patch.object(holiday_feed, '_fetch', side_effect=lambda url: (
                     json.dumps({'modified': holiday_feed.POSTER_TRANSCRIBED_VERSION})
                     if url == holiday_feed.POSTER_API else 'published HTML'
                 )), \
                 patch.object(holiday_feed, 'parse_holidays', return_value=holiday_data), \
                 patch.object(holiday_feed, '_district_items',
                              side_effect=lambda path, category: (articles[category], True)), \
                 patch.object(holiday_feed, '_wbl_items', return_value=[]):
                feed.sync(today)
                restored = holiday_feed.HolidayFeed(cache_path)
                self.assertEqual({item['kind'] for item in restored.view(today)['matches']}, {'Promo', 'Event'})
                self.assertEqual(restored.view(date(2026, 12, 27))['matches'], [])
                articles['Event'] = []
                feed.sync(today)
                self.assertEqual([item['kind'] for item in feed.view(today)['matches']], ['Promo'])
