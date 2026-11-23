from datetime import date, timedelta
from app import app
from models import db, Destination, TicketType
from utils.ai_service import LAMONGAN_DESTINATION_TEMPLATES

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


if __name__ == '__main__':
    seed_references()
