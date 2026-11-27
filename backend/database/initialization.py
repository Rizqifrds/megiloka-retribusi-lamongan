"""Initialize the catalog and register database administration commands."""

import click
from sqlalchemy.exc import IntegrityError

from database.migrations import upgrade_schema
from database.catalog import catalog_by_code, seed_booking_rates
from models import Destination, User, db


INITIAL_CATEGORIES = {
    'DEST-SND': 'Wisata Religi & Sejarah',
    'DEST-WDG': 'Wisata Alam & Edukasi',
    'DEST-MZG': 'Wisata Satwa & Geologi',
    'DEST-WBL': 'Taman Rekreasi Bahari',
    'DEST-KTG': 'Wisata Pesisir & Mangrove',
    'DEST-MSI-01': 'Museum Edukasi & Teknologi AR',
}


def initialize_database():
    upgrade_schema()
    if Destination.query.first() is not None:
        return

    catalog = catalog_by_code()
    for code, category in INITIAL_CATEGORIES.items():
        destination = Destination(category=category, **catalog[code])
        seed_booking_rates(destination)
        db.session.add(destination)
    db.session.commit()


def register_database_commands(app):
    @app.cli.command('init-db')
    def init_db_command():
        """Create or upgrade the configured database and initialize a new catalog."""
        initialize_database()
        click.echo('Database MegiLoka siap.')

    @app.cli.command('create-staff')
    @click.argument('username')
    @click.option('--name', required=True, help='Nama lengkap petugas.')
    @click.option('--role', type=click.Choice(['admin', 'cashier', 'gate_keeper']), default='admin', show_default=True)
    @click.option('--destination', help='Kode destinasi untuk kasir atau petugas gate.')
    def create_staff_command(username, name, role, destination):
        """Create a staff account with a privately entered password."""
        username, name = username.strip(), name.strip()
        if not 1 <= len(username) <= 50 or not 1 <= len(name) <= 100:
            raise click.ClickException('Periksa panjang username dan nama lengkap.')
        if role == 'admin' and destination:
            raise click.ClickException('Akun admin tidak memerlukan --destination.')
        if role != 'admin' and not destination:
            raise click.ClickException('Tentukan --destination untuk kasir atau petugas gate.')

        upgrade_schema()
        if User.query.filter_by(username=username).first() is not None:
            raise click.ClickException('Username sudah digunakan.')
        location = Destination.query.filter_by(code=destination).first() if destination else None
        if destination and location is None:
            raise click.ClickException('Kode destinasi tidak ditemukan.')
        password = click.prompt('Kata sandi', hide_input=True, confirmation_prompt=True)
        if len(password.strip()) < 12 or password.strip() != password:
            raise click.ClickException('Gunakan minimal 12 karakter tanpa spasi di awal atau akhir.')
        user = User(username=username, full_name=name, role=role, destination_id=location.id if location else None)
        user.set_password(password)
        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError as error:
            db.session.rollback()
            raise click.ClickException('Akun gagal disimpan. Periksa username dan destinasi.') from error
        click.echo(f'Akun {username} dibuat.')
