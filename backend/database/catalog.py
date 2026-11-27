"""Manage destination information and ticket rates from the Lamongan catalog."""
import json
from pathlib import Path

from models import Destination, TicketType, db

CATALOG_PATH = Path(__file__).resolve().with_name('destination_catalog.json')
BOOKING_RATES = {
    'DEST-WBL': (
        ('WBL (Senin–Kamis)', 75000, 0b0001111),
        ('WBL (Sabtu–Minggu)', 100000, 0b1100000),
    ),
    'DEST-MZG': (('Maharani Zoo & Goa (tarif acuan)', 30000, None),),
    'DEST-MSI-01': (
        ('Museum Islam Indonesia (Senin–Kamis)', 15000, 0b0001111),
        ('Museum Islam Indonesia (Jumat–Minggu)', 20000, 0b1110000),
    ),
}


def catalog_by_code():
    entries = json.loads(CATALOG_PATH.read_text(encoding='utf-8'))
    return {entry['code']: entry for entry in entries}


def seed_booking_rates(destination):
    if destination.admission_status != 'paid':
        return
    existing = {ticket.name for ticket in destination.ticket_types}
    for name, price, weekdays in BOOKING_RATES.get(destination.code, ()):
        if name not in existing:
            destination.ticket_types.append(TicketType(
                name=name, price=price, weekdays_mask=weekdays, is_active=True,
                description='Tarif acuan dari halaman produk. Dikonfirmasi petugas di loket.',
            ))
    destination.base_price = min((ticket.price for ticket in destination.available_tickets), default=0)


def apply_catalog():
    catalog = catalog_by_code()
    # Match stable codes used by the current data and the reference seeder.
    prefixes = ('DEST-LRN', 'DEST-TRN', 'DEST-BRM', 'DEST-MGR')
    updated = []
    for destination in Destination.query.order_by(Destination.id).with_for_update():
        entry = catalog.get(destination.code)
        if entry is None:
            prefix = destination.code.rsplit('-', 1)[0]
            if prefix in prefixes:
                entry = next(item for code, item in catalog.items() if code.startswith(prefix + '-'))
        if entry is None:
            continue
        for field, value in entry.items():
            if field != 'code':
                setattr(destination, field, value)
        destination.opening_date = None
        if destination.admission_status != 'paid':
            for ticket in destination.ticket_types:
                ticket.is_active = False
        seed_booking_rates(destination)
        if destination.admission_status != 'paid':
            destination.base_price = 0
        updated.append(destination.code)
    db.session.commit()
    return updated
