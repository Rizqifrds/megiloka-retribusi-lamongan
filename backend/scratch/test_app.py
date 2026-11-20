import unittest
import sys
import os

# Add root project dir to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db, seed_database
from models import Destination, TicketType, User, Transaction, Ticket, PADReportRecap
from utils.qr_generator import create_ticket_qr_payload, verify_qr_payload

class MegiLokaTestCase(unittest.TestCase):

    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SECRET_KEY'] = 'test_secret_key'
        self.client = app.test_client()
        with app.app_context():
            db.create_all()
            seed_database()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def test_database_seeding(self):
        with app.app_context():
            dest_count = Destination.query.count()
            self.assertGreaterEqual(dest_count, 5)
            user = User.query.filter_by(username='admin').first()
            self.assertIsNotNone(user)
            self.assertTrue(user.check_password('password123'))

    def test_qr_generation_and_validation(self):
        secret_key = 'test_secret_key'
        payload, sec_hash = create_ticket_qr_payload('MGLK-TEST-123', 1, '2026-09-02', secret_key)
        self.assertTrue(payload.startswith('MGLK|MGLK-TEST-123|1|2026-09-02|'))

        # Verify payload signature
        is_valid, t_code, dest_id, valid_date_str, err_msg = verify_qr_payload(payload, secret_key)
        self.assertTrue(is_valid)
        self.assertEqual(t_code, 'MGLK-TEST-123')
        self.assertIsNone(err_msg)

        # Test corrupted hash
        corrupted_payload = payload[:-4] + '0000'
        is_valid, _, _, _, err_msg = verify_qr_payload(corrupted_payload, secret_key)
        self.assertFalse(is_valid)
        self.assertIn('tidak cocok', err_msg)

    def test_public_routes(self):
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'MegiLoka', res.data)

        res = self.client.get('/destinations')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Katalog Wisata', res.data)

    def test_booking_flow(self):
        with app.app_context():
            dest = Destination.query.first()
            tt = TicketType.query.filter_by(destination_id=dest.id).first()
            
            data = {
                'visitor_name': 'Budi Santoso',
                'visitor_phone': '08123456789',
                'visit_date': '2026-09-05',
                'payment_method': 'qris',
                f'qty_{tt.id}': 2
            }
            res = self.client.post(f'/booking/{dest.id}', data=data, follow_redirects=True)
            self.assertEqual(res.status_code, 200)
            self.assertIn(b'E-Ticket Resmi MegiLoka', res.data)

            trans = Transaction.query.filter_by(visitor_name='Budi Santoso').first()
            self.assertIsNotNone(trans)
            tickets = Ticket.query.filter_by(transaction_id=trans.id).all()
            self.assertEqual(len(tickets), 2)

if __name__ == '__main__':
    unittest.main()
