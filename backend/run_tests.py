"""Run the Python suite against an in-memory database."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from config import Config

# SQLAlchemy binds its engine on app initialization, not when setUp runs.
# Keep test setup and cleanup away from the local database.
Config.SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

if __name__ == '__main__':
    loader = unittest.TestLoader()
    suite = loader.discover(str(ROOT / 'tests'), pattern='test_*.py')
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
