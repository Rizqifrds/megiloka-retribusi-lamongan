"""Add missing columns and constraints to existing MegiLoka databases."""

from sqlalchemy import inspect
from sqlalchemy.schema import CreateColumn

from models import Destination, Promo, TicketType, Transaction, VisitorAccount, db
from visitor_auth import visitor_login_key


VISIT_FIELDS = (
    'admission_status', 'admission_info', 'parking_info', 'source_url',
    'ticket_url', 'image_source_url',
)


def upgrade_schema():
    db.create_all()
    with db.engine.begin() as connection:
        inspector = inspect(connection)
        additions = (
            (Destination, VISIT_FIELDS),
            (TicketType, ('is_active', 'weekdays_mask')),
            (Transaction, ('paid_at', 'visitor_account_id', 'loyalty_discount', 'quantity_discount',
                           'promo_discount', 'promo_code', 'promo_offer', 'promo_expires_on')),
            (VisitorAccount, ('login_name_key',)),
            (Promo, ('destination_id',)),
        )
        references = {
            'visitor_account_id': 'visitor_accounts(id) ON DELETE SET NULL',
            'destination_id': 'destinations(id) ON DELETE CASCADE',
        }
        for model, fields in additions:
            table = model.__table__
            existing = {column['name'] for column in inspector.get_columns(table.name)}
            for field in fields:
                if field not in existing:
                    ddl = CreateColumn(table.c[field]).compile(dialect=connection.dialect)
                    if connection.dialect.name == 'sqlite' and field in references:
                        ddl = f'{ddl} REFERENCES {references[field]}'
                    connection.exec_driver_sql(f'ALTER TABLE {table.name} ADD COLUMN {ddl}')
        if connection.dialect.name in ('mysql', 'mariadb') and not any(
            fk['constrained_columns'] == ['visitor_account_id']
            for fk in inspector.get_foreign_keys('transactions')
        ):
            connection.exec_driver_sql(
                'ALTER TABLE transactions ADD CONSTRAINT fk_transaction_visitor '
                'FOREIGN KEY (visitor_account_id) REFERENCES visitor_accounts(id) ON DELETE SET NULL'
            )
        if connection.dialect.name in ('mysql', 'mariadb'):
            upgrade_mysql_promos(connection, inspector)
        accounts = VisitorAccount.__table__
        missing_keys = connection.execute(db.select(accounts.c.id, accounts.c.full_name).where(
            accounts.c.login_name_key.is_(None),
        )).all()
        for account_id, name in missing_keys:
            connection.execute(accounts.update().where(accounts.c.id == account_id).values(login_name_key=visitor_login_key(name)))
        for index in accounts.indexes:
            index.create(connection, checkfirst=True)


def upgrade_mysql_promos(connection, inspector):
    columns = {column['name']: column for column in inspector.get_columns('promos')}
    if not columns['hotel_id']['nullable']:
        hotel_type = columns['hotel_id']['type'].compile(dialect=connection.dialect)
        connection.exec_driver_sql(f'ALTER TABLE promos MODIFY COLUMN hotel_id {hotel_type} NULL')
    if not any(fk['constrained_columns'] == ['destination_id'] for fk in inspector.get_foreign_keys('promos')):
        connection.exec_driver_sql(
            'ALTER TABLE promos ADD CONSTRAINT fk_promo_destination '
            'FOREIGN KEY (destination_id) REFERENCES destinations(id) ON DELETE CASCADE'
        )
