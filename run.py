import os
import sys

# Add backend directory to sys.path
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
BACKEND_DIR = os.path.join(BASE_DIR, 'backend')
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app import app, holiday_feed, seed_database

if __name__ == '__main__':
    seed_database()
    if os.getenv('WERKZEUG_RUN_MAIN') == 'true':
        holiday_feed.start()
    host = os.getenv('HOST', '127.0.0.1')
    port = int(os.getenv('PORT', 5000))
    print("=======================================================")
    print(" MegiLoka - E-Ticketing & PAD System Kab. Lamongan ")
    print(f" Server Running on: http://{host}:{port} ")
    print("=======================================================")
    app.run(host=host, port=port, debug=True)
