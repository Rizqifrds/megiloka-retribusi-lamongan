import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import Config

Config.SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
from app import app
from models import Destination, PADReportRecap, Promo, User, db


class DatabaseSetupTests(unittest.TestCase):
    def setUp(self):
        self.runner = app.test_cli_runner()

    def tearDown(self):
        with app.app_context():
            db.drop_all()

    def test_init_is_repeatable_without_default_accounts_or_revenue(self):
        for _ in range(2):
            result = self.runner.invoke(args=['init-db'])
            self.assertEqual(result.exit_code, 0, result.output)
        with app.app_context():
            self.assertGreaterEqual(Destination.query.count(), 5)
            self.assertEqual(Destination.query.count(), len({item.code for item in Destination.query.all()}))
            self.assertEqual(User.query.count(), 0)
            self.assertEqual(PADReportRecap.query.count(), 0)
            self.assertTrue(Promo.__table__.c.hotel_id.nullable)

    def test_create_staff_hashes_password_and_rejects_duplicate_username(self):
        password = 'test-only-staff-password'
        command = ['create-staff', 'operator', '--name', 'Operator Uji']
        user_input = f'{password}\n{password}\n'
        first = self.runner.invoke(args=command, input=user_input)
        self.assertEqual(first.exit_code, 0, first.output)
        second = self.runner.invoke(args=command, input=user_input)
        self.assertNotEqual(second.exit_code, 0)
        with app.app_context():
            user = User.query.one()
            self.assertEqual(user.role, 'admin')
            self.assertNotEqual(user.password_hash, password)
            self.assertTrue(user.check_password(password))
