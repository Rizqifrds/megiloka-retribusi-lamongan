"""Discounts and payment methods for ticket reservations."""
from decimal import Decimal, ROUND_HALF_UP

from models import Promo, Transaction

LOYALTY_STEP = 5
LOYALTY_PERCENT = 10
PAYMENT_METHODS = {'cash': 'Tunai di loket', 'qris': 'QRIS', 'transfer': 'Transfer bank'}


def rounded_discount(amount, percent):
    return (amount * Decimal(percent) / 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP)


def paid_order_count(visitor_id, lock=False):
    if visitor_id is None:
        return 0
    query = Transaction.query.filter_by(visitor_account_id=visitor_id, payment_status='paid')
    if lock:
        # A locking read sees payments committed while this cashier waited for the visitor row.
        return len(query.with_entities(Transaction.id).with_for_update().all())
    return query.count()


def next_loyalty_discount(visitor_id, amount, lock=False):
    if visitor_id is not None and (paid_order_count(visitor_id, lock) + 1) % LOYALTY_STEP == 0:
        return rounded_discount(amount, LOYALTY_PERCENT)
    return Decimal(0)


def ticket_promo(destination_id, today, visit_date=None):
    return Promo.query.filter_by(destination_id=destination_id, hotel_id=None).filter(
        Promo.valid_from <= today,
        Promo.valid_until >= (visit_date or today),
        (Promo.discount_percent > 0) | (Promo.discount_amount > 0),
    ).order_by(Promo.valid_until.asc(), Promo.id.asc()).first()


def promo_discount(promo, amount):
    discount = rounded_discount(amount, promo.discount_percent) if promo.discount_percent else promo.discount_amount
    return max(Decimal(0), min(amount, discount or Decimal(0)))


def available_promo_discount(order, today, loyalty):
    if order.promo_code and order.promo_expires_on and today <= order.promo_expires_on:
        return min(order.promo_offer or Decimal(0), order.total_amount - loyalty)
    return Decimal(0)
