from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class Destination(db.Model):
    __tablename__ = 'destinations'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(50), nullable=False, default='Alam & Budaya')
    location = db.Column(db.String(255), nullable=False)
    base_price = db.Column(db.Numeric(12, 2), nullable=False, default=0.00)
    description = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(255), nullable=True)
    opening_date = db.Column(db.Date, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships
    ticket_types = db.relationship('TicketType', backref='destination', lazy=True, cascade="all, delete-orphan")
    users = db.relationship('User', backref='destination', lazy=True)
    transactions = db.relationship('Transaction', backref='destination', lazy=True)
    pad_recaps = db.relationship('PADReportRecap', backref='destination', lazy=True)
    hotels = db.relationship('Hotel', backref='destination', lazy=True, cascade='all, delete-orphan')
    events = db.relationship('Event', backref='destination', lazy=True)
    promos = db.relationship('Promo', backref='destination', lazy=True, cascade="all, delete-orphan")

    @property
    def active_promo(self):
        from ai.dates import today_wib
        today = today_wib()
        # Look for direct promos on destination first
        for p in self.promos:
            if p.valid_from <= today <= p.valid_until:
                return p
        # Look for promos on associated hotels
        for h in self.hotels:
            for p in h.promos:
                if p.valid_from <= today <= p.valid_until:
                    return p
        return None

    @property
    def discounted_price(self):
        promo = self.active_promo
        base = float(self.base_price)
        if promo:
            if promo.discount_percent:
                return round(base * (1.0 - float(promo.discount_percent) / 100.0))
            elif promo.discount_amount:
                return max(0, round(base - float(promo.discount_amount)))
        return base

    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'category': self.category,
            'location': self.location,
            'base_price': float(self.base_price),
            'description': self.description,
            'image_url': self.image_url,
            'opening_date': str(self.opening_date) if self.opening_date else None,
            'is_active': self.is_active
        }

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.Enum('admin', 'cashier', 'gate_keeper', name='user_roles'), nullable=False, default='cashier')
    destination_id = db.Column(db.Integer, db.ForeignKey('destinations.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class TicketType(db.Model):
    __tablename__ = 'ticket_types'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    destination_id = db.Column(db.Integer, db.ForeignKey('destinations.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Numeric(12, 2), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    destination_id = db.Column(db.Integer, db.ForeignKey('destinations.id', ondelete='CASCADE'), nullable=False)
    cashier_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    visitor_name = db.Column(db.String(100), nullable=False)
    visitor_phone = db.Column(db.String(30), nullable=True)
    total_amount = db.Column(db.Numeric(12, 2), nullable=False)
    payment_method = db.Column(db.Enum('cash', 'qris', 'transfer', name='payment_methods'), nullable=False, default='cash')
    payment_status = db.Column(db.Enum('paid', 'pending', 'cancelled', name='payment_statuses'), nullable=False, default='paid')
    transaction_time = db.Column(db.DateTime, default=datetime.now)

    # Relationships
    tickets = db.relationship('Ticket', backref='transaction', lazy=True, cascade="all, delete-orphan")
    cashier = db.relationship('User', foreign_keys=[cashier_id])

class Ticket(db.Model):
    __tablename__ = 'tickets'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transactions.id', ondelete='CASCADE'), nullable=False)
    ticket_type_id = db.Column(db.Integer, db.ForeignKey('ticket_types.id', ondelete='CASCADE'), nullable=False)
    ticket_code = db.Column(db.String(60), unique=True, nullable=False)
    qr_hash = db.Column(db.Text, nullable=False)
    status = db.Column(db.Enum('valid', 'used', 'expired', 'cancelled', name='ticket_statuses'), nullable=False, default='valid')
    valid_for_date = db.Column(db.Date, nullable=False)
    scanned_at = db.Column(db.DateTime, nullable=True)
    scanned_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    ticket_type = db.relationship('TicketType')
    scanned_by = db.relationship('User', foreign_keys=[scanned_by_user_id])

class PADReportRecap(db.Model):
    __tablename__ = 'pad_reports_recap'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    destination_id = db.Column(db.Integer, db.ForeignKey('destinations.id', ondelete='CASCADE'), nullable=False)
    report_date = db.Column(db.Date, nullable=False)
    total_tickets_sold = db.Column(db.Integer, nullable=False, default=0)
    total_revenue = db.Column(db.Numeric(15, 2), nullable=False, default=0.00)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('destination_id', 'report_date', name='dest_date_unique'),
    )

class Hotel(db.Model):
    __tablename__ = 'hotels'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    destination_id = db.Column(db.Integer, db.ForeignKey('destinations.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    location = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

    # Relationships
    promos = db.relationship('Promo', backref='hotel', lazy=True, cascade="all, delete-orphan")

class Promo(db.Model):
    __tablename__ = 'promos'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    hotel_id = db.Column(db.Integer, db.ForeignKey('hotels.id', ondelete='CASCADE'), nullable=True)
    destination_id = db.Column(db.Integer, db.ForeignKey('destinations.id', ondelete='CASCADE'), nullable=True)
    name = db.Column(db.String(150), nullable=False)
    discount_percent = db.Column(db.Numeric(5, 2), nullable=True)
    discount_amount = db.Column(db.Numeric(12, 2), nullable=True)
    description = db.Column(db.Text, nullable=True)
    valid_from = db.Column(db.Date, nullable=False)
    valid_until = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

class Event(db.Model):
    __tablename__ = 'events'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    destination_id = db.Column(db.Integer, db.ForeignKey('destinations.id', ondelete='CASCADE'), nullable=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    event_date = db.Column(db.Date, nullable=False)
    image_url = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
