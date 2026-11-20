from datetime import date
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import Config
# Set before importing app/db; never point these tests at the user's database.
Config.SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
from app import app
from models import db, Destination, Event, TicketType, Promo, User


class DateTests(unittest.TestCase):
    def test_day_with_relative_month_never_broadens_to_whole_month(self):
        from ai.dates import parse_period
        self.assertEqual(parse_period('tanggal 6 bulan depan', date(2026, 11, 5))[:2], (date(2026, 12, 6), date(2026, 12, 6)))
        self.assertEqual(parse_period('tanggal 6 bulan depan', date(2026, 12, 31))[:2], (date(2027, 1, 6), date(2027, 1, 6)))
        with self.assertRaises(ValueError):
            parse_period('tanggal 31 bulan ini', date(2026, 11, 5))

    def test_numeric_indonesian_date_or_unsupported_format_is_not_ignored(self):
        from ai.dates import parse_period
        today = date(2026, 11, 5)
        self.assertEqual(parse_period('Event 6-11-2026', today)[:2], (date(2026, 11, 6), date(2026, 11, 6)))
        with self.assertRaises(ValueError):
            parse_period('Event 6.11.2026', today)

    def test_periods_and_month_boundaries(self):
        from ai.dates import parse_period
        today = date(2026, 11, 5)
        for text, start, end in [
            ('event besok', date(2026, 11, 6), date(2026, 11, 6)),
            ('akhir pekan ini', date(2026, 11, 7), date(2026, 11, 8)),
            ('bulan ini', date(2026, 11, 1), date(2026, 11, 30)),
            ('bulan depan', date(2026, 12, 1), date(2026, 12, 31)),
            ('tanggal 6 November 2026', date(2026, 11, 6), date(2026, 11, 6)),
            ('pada 2027-01-02', date(2027, 1, 2), date(2027, 1, 2)),
            ('event Januari 2027', date(2027, 1, 1), date(2027, 1, 31)),
        ]:
            with self.subTest(text=text):
                self.assertEqual(parse_period(text, today)[:2], (start, end))
        self.assertEqual(parse_period('bulan depan', date(2026, 12, 31))[:2], (date(2027, 1, 1), date(2027, 1, 31)))
        self.assertEqual(parse_period('bulan depan', date(2028, 1, 31))[1], date(2028, 2, 29))
        with self.assertRaises(ValueError):
            parse_period('event 31 Februari 2026', today)


class ChatTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config.update(TESTING=True, SECRET_KEY='test-only')

    def setUp(self):
        self.context = app.app_context()
        self.context.push()
        db.create_all()
        d = Destination(code='TEST-KTG', name='Pantai Kutang', category='Bahari', location='Labuhan, Brondong', description='Pantai untuk pengujian.', base_price=10000, is_active=True)
        db.session.add(d)
        db.session.flush()
        db.session.add_all([
            TicketType(destination_id=d.id, name='Dewasa', price=12000),
            TicketType(destination_id=d.id, name='Anak', price=6000),
            Event(name='Festival Kupatan Akbar Tanjung Kodok', event_date=date(2026, 10, 10)),
            Event(name='Festival Pantura', destination_id=d.id, event_date=date(2026, 11, 6)),
            Event(name='Haul Sunan Drajat', event_date=date(2026, 11, 8)),
            Event(name='Haul Sunan Drajat', event_date=date(2027, 11, 8)),
            User(username='test-admin', password_hash='unused', full_name='Admin', role='admin'),
        ])
        db.session.commit()
        self.client = app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def answer(self, text):
        from ai.concierge import answer_question
        return answer_question(text, today=date(2026, 11, 5))

    def test_tomorrow_uses_database_and_does_not_write(self):
        before = Event.query.count()
        result = self.answer('Event apa saja besok?')
        self.assertIn('Festival Pantura', result['reply'])
        self.assertIn('6 November 2026', result['reply'])
        self.assertNotIn('Haul Sunan', result['reply'])
        self.assertEqual(result['sources'][0]['url'], '/calendar')
        self.assertEqual(Event.query.count(), before)

    def test_past_named_event_is_not_moved(self):
        result = self.answer('Kapan Festival Kupatan Akbar Tanjung Kodok dilaksanakan?')
        self.assertIn('10 Oktober 2026', result['reply'])
        self.assertIn('sudah lewat', result['reply'])

    def test_missing_time_and_duplicate_names(self):
        result = self.answer('Jam berapa Haul Sunan Drajat dimulai?')
        self.assertIn('pilih', result['reply'].lower())
        result = self.answer('Jam berapa Haul Sunan Drajat pada 8 November 2026?')
        self.assertIn('belum tersedia', result['reply'].lower())
        self.assertNotIn('08:00', result['reply'])

    def test_ticket_prices_are_from_ticket_types_not_faq(self):
        result = self.answer('Berapa harga tiket Pantai Kutang?')
        self.assertIn('12.000', result['reply'])
        self.assertIn('6.000', result['reply'])
        ticket = TicketType.query.filter_by(name='Dewasa').one()
        ticket.price = 17000
        db.session.commit()
        self.assertIn('17.000', self.answer('Berapa harga tiket Pantai Kutang?')['reply'])

    def test_promo_does_not_invent_booking_discount(self):
        d = Destination.query.one()
        db.session.add(Promo(name='Promo Uji', destination_id=d.id, discount_percent=10, valid_from=date(2026, 1, 1), valid_until=date(2026, 12, 31)))
        db.session.commit()
        text = self.answer('Berapa harga tiket Pantai Kutang?')['reply']
        self.assertIn('Promo Uji', text)
        self.assertIn('12.000', text)
        self.assertIn('konfirmasi', text.lower())

    def test_unknown_entity_does_not_return_unrelated_schedule(self):
        text = self.answer('Kapan Festival Naga Pelangi dilaksanakan?')['reply']
        self.assertIn('tidak menemukan', text.lower())
        self.assertNotIn('Festival Pantura', text)

    def test_no_events_and_invalid_date(self):
        self.assertIn('belum ada', self.answer('Event hari ini apa?')['reply'].lower())
        self.assertIn('tanggal tidak valid', self.answer('Event 31 Februari 2026 apa?')['reply'].lower())

    def test_relative_day_and_numeric_date_service_respect_constraints(self):
        self.assertIn('tanggal tidak valid', self.answer('Event tanggal 31 bulan ini apa?')['reply'].lower())
        text = self.answer('Event 6-11-2026 apa saja?')['reply']
        self.assertIn('Festival Pantura', text)
        self.assertNotIn('Haul Sunan Drajat', text)
        self.assertIn('belum ada', self.answer('Event tanggal 6 bulan depan apa?')['reply'].lower())

    def test_indonesian_grammar_is_not_treated_as_unknown_event_name(self):
        text = self.answer('Event apa saja dalam 7 hari ke depan?')['reply']
        self.assertIn('Festival Pantura', text)
        self.assertIn('Haul Sunan Drajat', text)
        self.assertIn('Kupatan', self.answer('Apakah Festival Kupatan masih ada?')['reply'])
        self.assertIn('tidak menemukan', self.answer('Kapan Festival Naga Pelangi dilaksanakan?')['reply'].lower())

    def test_location_and_no_invented_opening_hours(self):
        self.assertIn('Labuhan, Brondong', self.answer('Di mana Pantai Kutang?')['reply'])
        self.assertIn('belum tersedia', self.answer('Jam buka Pantai Kutang?')['reply'].lower())

    def test_wbl_abbreviation_does_not_match_other_bahari_destinations(self):
        db.session.add_all([
            Destination(code='TEST-WBL', name='Wisata Bahari Lamongan (WBL)', category='Rekreasi', location='Paciran WBL', description='WBL', base_price=75000),
            Destination(code='TEST-LRN', name='Wisata Bahari Pantai Lorena', category='Bahari', location='Paciran Lorena', description='Lorena', base_price=10000),
        ])
        db.session.commit()
        for text in ['Di mana lokasi WBL?', 'Di mana Wisata Bahari Lamongan?']:
            with self.subTest(text=text):
                reply = self.answer(text)['reply']
                self.assertIn('Paciran WBL', reply)
                self.assertNotIn('Lorena', reply)

    def test_out_of_scope(self):
        self.assertIn('wisata', self.answer('Tolong kerjakan integral kalkulus saya')['reply'].lower())
        self.assertNotIn('Festival Pantura', self.answer('Tolong kerjakan integral kalkulus saya')['reply'])

    def test_public_mutations_are_forbidden(self):
        before = (Event.query.count(), Destination.query.count())
        for payload in [
            {'action': 'add_event', 'range': 'h1'},
            {'action': 'add_destination', 'range': '1month'},
            {'message': 'tambah event besok'},
            {'message': 'tambahkan destinasi baru'},
        ]:
            with self.subTest(payload=payload):
                self.assertEqual(self.client.post('/api/ai/chat', json=payload).status_code, 403)
        self.assertEqual((Event.query.count(), Destination.query.count()), before)

    def test_fake_or_nonadmin_session_cannot_publish(self):
        for values in [{'user_role': 'admin'}, {'user_id': 999, 'user_role': 'admin'}, {'user_id': 1, 'user_role': 'cashier'}]:
            with self.client.session_transaction() as sess:
                sess.clear()
                sess.update(values)
            self.assertEqual(self.client.post('/api/ai/chat', json={'action': 'add_event'}).status_code, 403)

    def test_bad_input_and_unknown_action(self):
        for payload in [[], None, {'message': 12}, {'message': 'x'*2001}, {'action': 'erase'}, {'message': ''}]:
            with self.subTest(payload=payload):
                self.assertEqual(self.client.post('/api/ai/chat', json=payload).status_code, 400)

    def test_endpoint_serves_model_metadata(self):
        result = self.client.post('/api/ai/chat', json={'message': 'Berapa harga tiket Pantai Kutang?'}).get_json()
        self.assertEqual(result['intent'], 'ticket_price')
        self.assertEqual(result['model'], 'tfidf-logistic-regression')
        self.assertTrue(result['sources'])

    def test_model_unavailable_has_actionable_response(self):
        from ai.intent_model import ModelUnavailable
        with patch('ai.concierge.predict_intent', side_effect=ModelUnavailable('missing')):
            with self.assertLogs(app.logger, level='ERROR'):
                response = self.client.post('/api/ai/chat', json={'message': 'halo'})
        self.assertEqual(response.status_code, 503)
        self.assertIn('training', response.get_json()['reply'].lower())

    def test_visitor_shortcuts_are_questions_not_creations(self):
        html = self.client.get('/').get_data(as_text=True)
        self.assertIn('askMegi(', html)
        self.assertNotIn("triggerAiAction('add_event'", html)
        self.assertNotIn('Asisten AI Resmi', html)


if __name__ == '__main__':
    unittest.main()
