import sys
from datetime import date, timedelta
from app import app
from models import db, Destination, Event, TicketType
from utils.ai_service import LAMONGAN_EVENT_TEMPLATES, LAMONGAN_DESTINATION_TEMPLATES

def seed_references():
    with app.app_context():
        today = date.today()
        print(f"Current Date: {today}")
        
        # 1. Add Destinations from templates if not present
        added_dest_count = 0
        for i, t in enumerate(LAMONGAN_DESTINATION_TEMPLATES):
            existing = Destination.query.filter_by(name=t['name']).first()
            if not existing:
                if i % 3 == 0:
                    op_date = today + timedelta(days=28) # ~1 month (H-28)
                elif i % 3 == 1:
                    op_date = today + timedelta(days=180) # ~6 months
                else:
                    op_date = today + timedelta(days=330) # ~1 year
                
                dest = Destination(
                    code=f"DEST-{t['code_prefix']}-01",
                    name=t['name'],
                    category=t['category'],
                    location=t['location'],
                    base_price=t['base_price'],
                    description=t['description'],
                    image_url=t['image_url'],
                    opening_date=op_date,
                    is_active=True
                )
                db.session.add(dest)
                db.session.flush()
                
                tt = TicketType(
                    destination_id=dest.id,
                    name=t['ticket_name'],
                    price=t['base_price'],
                    description=f"Retribusi masuk resmi {dest.name}"
                )
                db.session.add(tt)
                added_dest_count += 1
                print(f"[OK] Added Destination: {dest.name} | Opening Date: {op_date}")

        db.session.commit()
        print(f"Total new destinations added: {added_dest_count}")

        # 2. Add / Update Events from Kalender 2026 templates
        event_schedules = [
            1,   # H-1 (BESOK!)
            20,  # H-20 (1 BULAN LAGI)
            30,  # H-30 (1 BULAN LAGI)
            60,  # 2 bulan
            90,  # 3 bulan
            120, # 4 bulan
            180, # 6 bulan
            240, # 8 bulan
            300, # 10 bulan
            360, # 1 tahun
            365  # 1 tahun
        ]

        added_ev_count = 0
        for idx, et in enumerate(LAMONGAN_EVENT_TEMPLATES):
            days_ahead = event_schedules[idx % len(event_schedules)]
            ev_date = today + timedelta(days=days_ahead)
            existing_ev = Event.query.filter_by(name=et['name']).first()
            if not existing_ev:
                dest_hint = None
                if et.get('dest_code_hint'):
                    dest_hint = Destination.query.filter_by(code=et['dest_code_hint']).first()
                    
                new_ev = Event(
                    destination_id=dest_hint.id if dest_hint else None,
                    name=et['name'],
                    description=et['description'],
                    event_date=ev_date,
                    image_url=et['image_url']
                )
                db.session.add(new_ev)
                added_ev_count += 1
                print(f"[OK] Added Event: {new_ev.name} | Date: {ev_date} (Days left: {days_ahead})")
            else:
                # Update date if needed to ensure H-1 and H-30 representation
                if idx == 0:
                    existing_ev.event_date = today + timedelta(days=1)
                elif idx == 1:
                    existing_ev.event_date = today + timedelta(days=25)
                db.session.add(existing_ev)
                print(f"[UPDATE] Updated Event date: {existing_ev.name} -> {existing_ev.event_date}")

        db.session.commit()
        print(f"Total new events added: {added_ev_count}")
        print("Database successfully synchronized with Bapperida & Kompas references!")

if __name__ == '__main__':
    seed_references()
