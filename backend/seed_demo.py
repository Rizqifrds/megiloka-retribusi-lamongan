"""Load connected demonstration records with `python backend/seed_demo.py`."""

import argparse
import secrets
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import URL, create_engine, func, select

from ai.dates import today_wib
from app import app
from models import Destination, Event, Hotel, PADReportRecap, Promo, Ticket, TicketType, Transaction, User, db
from utils.qr_generator import create_ticket_qr_payload


def copy_sqlite(path):
    if not path.is_file():
        raise FileNotFoundError(path)
    tables = db.metadata.sorted_tables
    if any(db.session.scalar(select(func.count()).select_from(table)) for table in tables):
        raise ValueError('Impor SQLite memerlukan database tujuan kosong.')
    source = create_engine(URL.create('sqlite', database=str(path.resolve())))
    try:
        with source.connect() as connection:
            for table in tables:
                rows = [dict(row) for row in connection.execute(select(table)).mappings()]
                if rows:
                    db.session.execute(table.insert(), rows)
    finally:
        source.dispose()


def get_or_create(model, defaults, **keys):
    record = model.query.filter_by(**keys).first()
    if record is None:
        record = model(**keys, **defaults)
        db.session.add(record)
        db.session.flush()
    return record


def seed_demo():
    today = today_wib()
    description = 'Data contoh MegiLoka untuk pengujian.'
    photo = '/static/images/lamongan-wbl-hero.jpg'
    destination = get_or_create(Destination, {
        'name': '[DEMO] Taman Pesisir MegiLoka', 'category': 'Wisata Alam & Edukasi',
        'location': 'Lamongan (lokasi contoh)', 'base_price': 25000,
        'description': description, 'image_url': photo,
    }, code='DEMO-MEGILOKA')
    cashier = get_or_create(User, {
        'full_name': 'Kasir Demo', 'role': 'cashier', 'destination_id': destination.id,
        'password_hash': _demo_password_hash(),
    }, username='demo_kasir')
    ticket_type = get_or_create(TicketType, {
        'price': 25000, 'description': description,
    }, destination_id=destination.id, name='Tiket Reguler Demo')
    transaction = get_or_create(Transaction, {
        'destination_id': destination.id, 'cashier_id': cashier.id, 'visitor_name': 'Pengunjung Demo',
        'total_amount': ticket_type.price, 'payment_method': 'cash', 'payment_status': 'paid',
        'transaction_time': datetime.combine(today, datetime.now().time()),
    }, invoice_number='INV-DEMO-MEGILOKA-001')
    day = transaction.transaction_time.date()
    code = 'MGLK-DEMO-MEGILOKA-001'
    _, signature = create_ticket_qr_payload(code, destination.id, day.isoformat(), app.config['SECRET_KEY'])
    get_or_create(Ticket, {
        'transaction_id': transaction.id, 'ticket_type_id': ticket_type.id,
        'qr_hash': signature, 'valid_for_date': day,
    }, ticket_code=code)
    get_or_create(PADReportRecap, {
        'total_tickets_sold': 1, 'total_revenue': transaction.total_amount,
    }, destination_id=destination.id, report_date=day)
    hotel = get_or_create(Hotel, {
        'location': 'Lamongan (lokasi contoh)', 'description': description, 'image_url': photo,
    }, destination_id=destination.id, name='[DEMO] Penginapan Pesisir')
    get_or_create(Promo, {
        'hotel_id': hotel.id, 'discount_percent': 10, 'description': description,
        'valid_from': today, 'valid_until': today + timedelta(days=30),
    }, destination_id=destination.id, name='[DEMO] Promo Wisata Pesisir')
    get_or_create(Event, {
        'description': description, 'event_date': today + timedelta(days=7), 'image_url': photo,
    }, destination_id=destination.id, name='[DEMO] Festival Pesisir Lamongan')


def _demo_password_hash():
    user = User()
    user.set_password(secrets.token_urlsafe(24))
    return user.password_hash


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--copy-sqlite', type=Path, help='Salin data lama jika database tujuan masih kosong.')
    args = parser.parse_args()
    with app.app_context():
        db.create_all()
        if args.copy_sqlite:
            copy_sqlite(args.copy_sqlite)
        seed_demo()
        db.session.commit()
        for table in db.metadata.sorted_tables:
            count = db.session.scalar(select(func.count()).select_from(table))
            print(f'{table.name}: {count}')


if __name__ == '__main__':
    main()
