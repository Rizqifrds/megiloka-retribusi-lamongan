from app import app
from destination_catalog import catalog_by_code, upgrade_visit_schema
from models import db, Destination
from utils.ai_service import LAMONGAN_DESTINATION_TEMPLATES


def seed_references():
    with app.app_context():
        upgrade_visit_schema()
        catalog = catalog_by_code()
        known_prefixes = {destination.code.rsplit('-', 1)[0]
                          for destination in Destination.query.all()}
        for template in LAMONGAN_DESTINATION_TEMPLATES:
            prefix = f"DEST-{template['code_prefix']}"
            if prefix in known_prefixes:
                continue
            entry = next((item for code, item in catalog.items() if code.startswith(prefix + '-')), None)
            if entry:
                db.session.add(Destination(category=template['category'], **entry))
        db.session.commit()


if __name__ == '__main__':
    seed_references()
