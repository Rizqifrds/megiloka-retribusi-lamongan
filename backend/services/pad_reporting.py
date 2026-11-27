"""PAD figures derived from recorded payments, grouped by destination and WIB date."""
from models import Destination, Ticket, Transaction, db


def pad_rows(start=None, end=None, destination_id=None):
    ticket_counts = db.select(
        Ticket.transaction_id,
        db.func.count(Ticket.id).label('ticket_count'),
    ).group_by(Ticket.transaction_id).subquery()
    payment_time = db.func.coalesce(Transaction.paid_at, Transaction.transaction_time)
    report_day = db.func.date(payment_time, type_=db.Date)
    query = db.select(
        report_day.label('report_date'),
        Destination.code.label('destination_code'),
        Destination.name.label('destination_name'),
        db.func.sum(ticket_counts.c.ticket_count).label('total_tickets_sold'),
        db.func.sum(Transaction.total_amount).label('total_revenue'),
    ).select_from(Transaction).join(Destination).join(
        ticket_counts, ticket_counts.c.transaction_id == Transaction.id,
    ).where(
        Transaction.payment_status == 'paid',
        ~Transaction.invoice_number.startswith('INV-DEMO-'),
    )
    if start:
        query = query.where(report_day >= start)
    if end:
        query = query.where(report_day <= end)
    if destination_id:
        query = query.where(Transaction.destination_id == destination_id)
    return db.session.execute(query.group_by(report_day, Destination.code, Destination.name).order_by(
        report_day.desc(), Destination.name.asc(),
    )).all()
