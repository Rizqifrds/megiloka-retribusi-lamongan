"""Run all Python tests against an in-memory database, including legacy tests."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from config import Config

# SQLAlchemy binds its engine on app initialization, not when setUp runs.
# Keep the legacy tests' drop_all away from the real database.
Config.SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

if __name__ == '__main__':
    loader = unittest.TestLoader()
    suite = unittest.TestSuite([
        loader.discover(str(ROOT / 'tests'), pattern='test_*.py'),
        loader.discover(str(ROOT / 'scratch'), pattern='test_*.py'),
    ])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
