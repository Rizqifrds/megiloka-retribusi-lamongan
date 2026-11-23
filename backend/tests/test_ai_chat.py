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
from models import db, Destination, Event, Hotel, PADReportRecap, TicketType, Promo, Ticket, Transaction, User


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
        d = Destination(code='TEST-KTG', name='Pantai Kutang', category='Bahari', location='Labuhan, Brondong', description='Pantai untuk pengujian.', base_price=10000, is_active=True, admission_status='paid')
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

    def test_guest_notifications_are_official_and_read_per_session(self):
        db.session.add(Event(name='[DEMO] Acara Lama', event_date=date(2026, 11, 26)))
        db.session.commit()
        with patch('app.today_wib', return_value=date(2026, 11, 23)):
            items = self.client.get('/api/guest/notifications').get_json()
            self.assertEqual(items['total'], 2)
            notice = items['notifications'][0]
            self.assertIn('Lohgung', notice['title'])
            response = self.client.post(f"/notifications/read/{notice['id']}")
            self.assertEqual(response.location, notice['url'])
            self.assertIn(b'Lohgung', self.client.get(response.location).data)
            self.assertEqual(self.client.get('/api/guest/notifications').get_json()['total'], 1)
            self.client.post(f"/notifications/read/{notice['id']}")
            self.assertEqual(self.client.get('/api/guest/notifications').get_json()['total'], 1)
            self.assertEqual(app.test_client().get('/api/guest/notifications').get_json()['total'], 2)

    def test_admin_can_delete_event_hotel_and_direct_or_hotel_promos(self):
        dest = Destination.query.one()
        hotel = Hotel(name='Hotel Uji', location='Paciran', destination=dest)
        dates = dict(valid_from=date(2026, 11, 1), valid_until=date(2026, 11, 30))
        hotel_promo = Promo(name='Promo Hotel Uji', hotel=hotel, **dates)
        direct_promo = Promo(name='Promo Destinasi Uji', destination=dest, **dates)
        db.session.add_all([hotel_promo, direct_promo])
        db.session.commit()
        promo_id, hotel_id, event_id = direct_promo.id, hotel.id, Event.query.first().id
        with self.client.session_transaction() as sess:
            sess.update(user_id=1, user_role='admin')
        self.assertIn(b'Promo Destinasi Uji', self.client.get('/admin/hotels').data)
        for collection, record_id in [('events', event_id), ('promos', promo_id), ('hotels', hotel_id)]:
            self.assertEqual(self.client.post(f'/admin/{collection}/delete/{record_id}').status_code, 302)
        db.session.expire_all()
        self.assertIsNone(db.session.get(Event, event_id))
        self.assertIsNone(db.session.get(Hotel, hotel_id))
        self.assertEqual(Promo.query.count(), 0)

    def test_delete_destination_removes_unused_data_and_archives_history(self):
        dest = Destination.query.one()
        unused = Destination(code='UNUSED', name='Destinasi Uji', location='Lamongan')
        hotel = Hotel(name='Hotel Uji', location='Lamongan', destination=unused)
        db.session.add_all([Promo(name='Promo Uji', hotel=hotel, valid_from=date(2026, 11, 1),
                                  valid_until=date(2026, 11, 30)),
                            PADReportRecap(destination=dest, report_date=date(2026, 11, 1))])
        db.session.commit()
        dest_id, unused_id = dest.id, unused.id
        with self.client.session_transaction() as sess:
            sess.update(user_id=1, user_role='admin')
        for record_id in (unused_id, dest_id):
            self.assertEqual(self.client.post(f'/admin/destinations/delete/{record_id}').status_code, 302)
        db.session.expire_all()
        self.assertIsNone(db.session.get(Destination, unused_id))
        self.assertEqual(Hotel.query.count(), 0)
        self.assertEqual(Promo.query.count(), 0)
        self.assertFalse(db.session.get(Destination, dest_id).is_active)
        self.assertEqual(PADReportRecap.query.count(), 1)
        self.assertEqual(self.client.get(f'/booking/{dest_id}').status_code, 404)

    def test_official_calendar_questions_find_multiday_event(self):
        db.session.add(Event(name='[DEMO] Agenda Uji', event_date=date(2026, 11, 24)))
        db.session.commit()
        with patch('ai.concierge.today_wib', return_value=date(2026, 11, 23)):
            for question in ('Event apa saja besok?', 'Besok ada kegiatan apa?', 'Agenda minggu ini',
                             'Agenda resmi esok', 'Acara pekan ini', 'Adakah agenda budaya esok hari?',
                             'Acara tanggal 26 November 2026', 'Petik Laut Lohgung',
                             'Jam berapa Petik Laut Lohgung?'):
                with self.subTest(question=question):
                    response = self.client.post('/api/ai/chat', json={'message': question})
                    self.assertEqual(response.status_code, 200)
                    result = response.get_json()
                    self.assertIn('petik laut lohgung', result['reply'].lower())
                    self.assertIn('24–27 November 2026', result['reply'])
                    self.assertIn('Kalender resmi Lamongan', result['reply'])
                    self.assertEqual(result['sources'][0]['url'], '/calendar#poster-calendar-title')
                    self.assertNotIn('Agenda Uji', result['reply'])

    def test_official_calendar_excludes_other_dates_and_undated_entries(self):
        from ai.concierge import answer_question
        today = date(2026, 11, 23)
        reply = answer_question('Event apa saja besok?', today=today)['reply']
        self.assertNotIn('Festival Wingko Babat', reply)
        reply = answer_question('Jadwal acara bulan depan', today=today)['reply']
        self.assertIn('Malam Tahun Baruan Megilan', reply)
        self.assertNotIn('Lohgung', reply)

    def test_named_poster_event_without_day_discloses_missing_date(self):
        reply = self.answer('Kapan Festival Wingko Babat?')['reply']
        self.assertIn('November 2026', reply)
        self.assertIn('tanggal pastinya belum tercantum', reply.lower())

    def test_past_named_event_is_not_moved(self):
        result = self.answer('Kapan Festival Kupatan Akbar Tanjung Kodok dilaksanakan?')
        self.assertIn('10 Oktober 2026', result['reply'])
        self.assertIn('sudah lewat', result['reply'])

    @patch('ai.concierge.poster_events', return_value=())
    def test_missing_time_and_duplicate_names(self, _poster_events):
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

    def test_free_destination_is_information_only_even_with_legacy_ticket(self):
        dest = Destination.query.one()
        dest.admission_status = 'free'
        db.session.commit()
        detail = self.client.get(f'/destinations/{dest.id}').get_data(as_text=True)
        self.assertIn('Gratis', detail)
        self.assertNotIn('Pesan E-Ticket', detail)
        sale = self.client.post(f'/booking/{dest.id}', data={'qty_1': '1'})
        self.assertEqual(sale.location, f'/destinations/{dest.id}')
        self.assertIn('gratis', self.answer('Berapa harga tiket Pantai Kutang?')['reply'].lower())

    def test_namira_is_featured_without_a_ticket_button(self):
        db.session.add(Destination(code='DEST-NMR-01', name='Masjid Namira Lamongan', location='Jotosanur', admission_status='free'))
        db.session.commit()
        html = self.client.get('/').get_data(as_text=True)
        self.assertIn('Masjid Namira Lamongan', html)
        self.assertIn('Gratis', html)

    def test_reservation_counts_toward_pad_once_cashier_confirms(self):
        dest = Destination.query.one()
        ticket_type = TicketType.query.filter_by(name='Dewasa').one()
        with patch('app.today_wib', return_value=date(2026, 11, 23)):
            result = self.client.post(f'/booking/{dest.id}', data={
                'visitor_name': 'Pengunjung Uji', 'visit_date': '2026-11-23', f'qty_{ticket_type.id}': '2',
            })
            self.assertIn('/tickets/', result.location)
            order = Transaction.query.one()
            self.assertEqual(order.payment_status, 'pending')
            self.assertEqual(PADReportRecap.query.count(), 0)
            self.assertNotIn('ticket-qr-container', self.client.get(result.location).get_data(as_text=True))
            path = f'/pos/reservations/{order.invoice_number}/confirm'
            self.assertEqual(self.client.post(path).status_code, 302)
            self.assertEqual(Transaction.query.one().payment_status, 'pending')
            with self.client.session_transaction() as sess:
                sess.update(user_id=1, user_role='admin', reservation_csrf='test-token')
            for _ in range(2):
                self.assertEqual(self.client.post(path, data={'csrf_token': 'test-token'}).status_code, 302)
            self.assertEqual(Transaction.query.one().payment_status, 'paid')
            self.assertEqual(Ticket.query.count(), 2)
            self.assertEqual(PADReportRecap.query.one().total_revenue, 24000)
            self.assertEqual(PADReportRecap.query.one().total_tickets_sold, 2)
            self.assertIn('ticket-qr-container', self.client.get(result.location).get_data(as_text=True))

    def test_retired_ticket_remains_in_database_but_is_not_offered(self):
        dest = Destination.query.one()
        old = TicketType.query.filter_by(name='Dewasa').one()
        old.is_active = False
        db.session.commit()
        detail = self.client.get(f'/destinations/{dest.id}').get_data(as_text=True)
        self.assertNotIn('12.000', detail)
        self.assertNotIn('12.000', self.answer('Berapa harga tiket Pantai Kutang?')['reply'])
        self.assertIsNotNone(db.session.get(TicketType, old.id))

    def test_parking_uses_destination_note(self):
        dest = Destination.query.one()
        dest.parking_info = 'Tarif parkir motor tercatat Rp2.000.'
        db.session.commit()
        result = self.answer('Berapa biaya parkir Pantai Kutang?')
        self.assertIn('motor tercatat Rp2.000', result['reply'])

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

    @patch('ai.concierge.poster_events', return_value=())
    def test_indonesian_grammar_is_not_treated_as_unknown_event_name(self, _poster_events):
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
