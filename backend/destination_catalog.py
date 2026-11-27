"""Apply the Lamongan catalog to the configured database."""

if __name__ == '__main__':
    from app import app
    from database.catalog import apply_catalog
    from database.migrations import upgrade_schema

    with app.app_context():
        upgrade_schema()
        updated = apply_catalog()
        print(f'{len(updated)} destinasi diperbarui.')
