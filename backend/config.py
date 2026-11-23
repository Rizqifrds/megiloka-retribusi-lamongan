import os
from dotenv import load_dotenv
from sqlalchemy.engine import URL

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, '..'))
FRONTEND_DIR = os.path.join(PROJECT_ROOT, 'frontend')

# Load environment variables from .env file (backend or root)
load_dotenv(os.path.join(BASE_DIR, '.env'))
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'megiloka_lamongan_megilan_secret_key_2026')
    HOLIDAY_PARTNER_URL = os.getenv('HOLIDAY_PARTNER_URL', '').strip()
    HOLIDAY_WEBHOOK_TOKEN = os.getenv('HOLIDAY_WEBHOOK_TOKEN', '')
    INSTAGRAM_GRAPH_VERSION = os.getenv('INSTAGRAM_GRAPH_VERSION', '').strip()
    INSTAGRAM_IG_USER_ID = os.getenv('INSTAGRAM_IG_USER_ID', '').strip()
    INSTAGRAM_ACCESS_TOKEN = os.getenv('INSTAGRAM_ACCESS_TOKEN', '').strip()
    WHATSAPP_NUMBER = os.getenv('WHATSAPP_NUMBER', '').strip()
    WHATSAPP_PHONE_ID = os.getenv('WHATSAPP_PHONE_ID', '').strip()
    WHATSAPP_API_VERSION = os.getenv('WHATSAPP_API_VERSION', '').strip()
    WHATSAPP_ACCESS_TOKEN = os.getenv('WHATSAPP_ACCESS_TOKEN', '').strip()
    WHATSAPP_APP_SECRET = os.getenv('WHATSAPP_APP_SECRET', '').strip()
    WHATSAPP_VERIFY_TOKEN = os.getenv('WHATSAPP_VERIFY_TOKEN', '').strip()
    WHATSAPP_AGENDA_TEMPLATE = os.getenv('WHATSAPP_AGENDA_TEMPLATE', '').strip()
    
    DB_TYPE = os.getenv('DB_TYPE', 'sqlite').lower()
    DB_HOST = os.getenv('DB_HOST', '127.0.0.1')
    DB_PORT = os.getenv('DB_PORT', '3306')
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_NAME = os.getenv('DB_NAME', 'megiloka_db')

    if DB_TYPE == 'mysql':
        SQLALCHEMY_DATABASE_URI = URL.create(
            'mysql+pymysql', username=DB_USER, password=DB_PASSWORD, host=DB_HOST,
            port=int(DB_PORT), database=DB_NAME, query={'charset': 'utf8mb4'}
        )
        SQLALCHEMY_ENGINE_OPTIONS = {'pool_pre_ping': True, 'pool_recycle': 1800}
    else:
        # SQLite fallback for instant zero-dependency execution
        db_path = os.path.join(BASE_DIR, 'megiloka.db')
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}"

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    QR_CODE_DIR = os.path.join(FRONTEND_DIR, 'qrcodes')
