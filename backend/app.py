import hmac
from hashlib import sha256
import os
import sys
import io
import re
import random
import secrets
import csv
from datetime import datetime, date, timedelta
from decimal import Decimal, InvalidOperation
from functools import wraps
from urllib.parse import urlsplit

# Ensure backend directory is in sys.path
BACKEND_DIR = os.path.abspath(os.path.dirname(__file__))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

PROJECT_ROOT = os.path.abspath(os.path.join(BACKEND_DIR, '..'))
FRONTEND_DIR = os.path.join(PROJECT_ROOT, 'frontend')

from flask import (
    Flask, abort, render_template, request, redirect, url_for, flash, session, jsonify, Response, send_from_directory
)
from sqlalchemy.exc import IntegrityError

from config import Config
from destination_catalog import catalog_by_code, seed_booking_rates, upgrade_visit_schema
from models import db, Destination, User, TicketType, Transaction, Ticket, PADReportRecap, Hotel, Promo, Event, VisitorAccount
from utils.qr_generator import create_ticket_qr_payload, verify_qr_payload, generate_qr_image_base64
from utils.holiday_feed import HolidayFeed
from utils.pad_reporting import pad_rows
from utils.ticket_pricing import (
    LOYALTY_PERCENT, PAYMENT_METHODS, available_promo_discount, next_loyalty_discount,
    paid_order_count, promo_discount, ticket_promo,
)
from utils.whatsapp_agenda import init_whatsapp
from utils.lamongan_calendar import POSTER_PAGE, POSTER_YEAR, poster_events, poster_months, upcoming_poster_events
from ai.dates import WIB, today_wib
from ai.concierge import answer_question
from ai.intent_model import ModelUnavailable
from visitor_auth import current_visitor, normalize_name, normalize_phone, verify_visitor_csrf, visitor_auth
from utils.ai_service import (
    LAMONGAN_EVENT_TEMPLATES, LAMONGAN_DESTINATION_TEMPLATES,
    resolve_date_target, detect_ai_intent
)

app = Flask(
    __name__,
    template_folder=os.path.join(FRONTEND_DIR, 'html'),
    static_folder=None
)
app.config.from_object(Config)

db.init_app(app)
app.register_blueprint(visitor_auth)
init_whatsapp(app)
instagram_settings = tuple(app.config[key] for key in (
    'INSTAGRAM_GRAPH_VERSION', 'INSTAGRAM_IG_USER_ID', 'INSTAGRAM_ACCESS_TOKEN',
))
holiday_feed = HolidayFeed(
    os.path.join(app.instance_path, 'holiday-feed.json'),
    app.config['HOLIDAY_PARTNER_URL'],
    instagram_settings if all(instagram_settings) else None,
)


@app.before_request
def start_holiday_feed():
    if not app.testing:
        holiday_feed.start()

# Static file routes for css and js directories
@app.route('/css/<path:filename>', endpoint='serve_css')
def serve_css(filename):
    return send_from_directory(os.path.join(FRONTEND_DIR, 'css'), filename)

@app.route('/js/<path:filename>', endpoint='serve_js')
def serve_js(filename):
    return send_from_directory(os.path.join(FRONTEND_DIR, 'js'), filename)

@app.route('/static/<path:filename>', endpoint='static')
def serve_static(filename):
    if filename.startswith('css/'):
        return send_from_directory(os.path.join(FRONTEND_DIR, 'css'), filename[4:])
    elif filename.startswith('js/'):
        return send_from_directory(os.path.join(FRONTEND_DIR, 'js'), filename[3:])
    return send_from_directory(FRONTEND_DIR, filename)

# Helper Decorators for RBAC
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Silakan login terlebih dahulu untuk mengakses halaman ini.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_role' not in session or session['user_role'] not in roles:
                flash('Anda tidak memiliki hak akses untuk halaman tersebut.', 'danger')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def generate_invoice_number():
    date_str = datetime.now().strftime('%Y%m%d')
    random_str = secrets.token_hex(12).upper()
    return f"INV-{date_str}-{random_str}"

def generate_ticket_code(dest_code):
    random_str = secrets.token_hex(12).upper()
    return f"MGLK-{dest_code}-{random_str}"

# Auto Database Seeder Helper
def seed_database():
    with app.app_context():
        upgrade_visit_schema()
        if Destination.query.count() == 0:
            catalog = catalog_by_code()
            categories = {
                'DEST-SND': 'Wisata Religi & Sejarah',
                'DEST-WDG': 'Wisata Alam & Edukasi',
                'DEST-MZG': 'Wisata Satwa & Geologi',
                'DEST-WBL': 'Taman Rekreasi Bahari',
                'DEST-KTG': 'Wisata Pesisir & Mangrove',
            }
            dest1, dest2, dest3, dest4, dest5 = [
                Destination(category=category, **catalog[code])
                for code, category in categories.items()
            ]
            db.session.add_all([dest1, dest2, dest3, dest4, dest5])
            seed_booking_rates(dest3)
            seed_booking_rates(dest4)
            db.session.flush()

            # Add Users
            admin_user = User(username='admin', full_name='Administrator Disparbud Lamongan', role='admin')
            admin_user.set_password('adminmegiloka')

            cashier1 = User(username='kasir_drajat', full_name='Budi Loket Sunan Drajat', role='cashier', destination_id=dest1.id)
            cashier1.set_password('kasirmegiloka')

            gate1 = User(username='gate_drajat', full_name='Siti Petugas Gate Drajat', role='gate_keeper', destination_id=dest1.id)
            gate1.set_password('gatemegiloka')

            db.session.add_all([admin_user, cashier1, gate1])
            db.session.commit()

            # Add Initial PAD Recap data for chart preview
            today = date.today()
            for i in range(7):
                past_date = today - timedelta(days=i)
                db.session.add_all([
                    PADReportRecap(destination_id=dest1.id, report_date=past_date, total_tickets_sold=random.randint(80, 150), total_revenue=random.randint(80, 150)*10000.0),
                    PADReportRecap(destination_id=dest2.id, report_date=past_date, total_tickets_sold=random.randint(50, 120), total_revenue=random.randint(50, 120)*15000.0),
                    PADReportRecap(destination_id=dest3.id, report_date=past_date, total_tickets_sold=random.randint(100, 250), total_revenue=random.randint(100, 250)*35000.0),
                    PADReportRecap(destination_id=dest4.id, report_date=past_date, total_tickets_sold=random.randint(200, 500), total_revenue=random.randint(200, 500)*75000.0),
                    PADReportRecap(destination_id=dest5.id, report_date=past_date, total_tickets_sold=random.randint(60, 110), total_revenue=random.randint(60, 110)*10000.0)
                ])
            db.session.commit()
            print("[INFO] MegiLoka database initialized.")


# ----------------------------
# OFFICIAL AGENDA NOTIFICATIONS
# ----------------------------

def get_upcoming_items():
    today = today_wib()
    cutoff = today + timedelta(days=30)
    read_ids = set(session.get('read_agenda_notifications', ()))
    items = []
    for event in poster_events(today):
        if not event.start or event.end < today or event.start > cutoff:
            continue
        days_left = (event.start - today).days
        timing = 'Sedang berlangsung' if days_left < 0 else 'Hari ini' if days_left == 0 else 'Besok' if days_left == 1 else f'{days_left} hari lagi'
        key = sha256(f'{event.name}|{event.start}|{event.end}'.encode()).hexdigest()[:20]
        items.append({
            'id': key,
            'type': 'event',
            'title': event.name,
            'date_str': event.date_label,
            'is_read': key in read_ids,
            'timing_desc': timing,
            'url': url_for('public_calendar', _anchor=event.anchor),
            'days_left': days_left,
        })
    return sorted(items, key=lambda item: item['days_left'])


@app.context_processor
def inject_global_data():
    notifications = get_upcoming_items()
    return {
        'guest_notifications': notifications,
        'total_notifications': sum(not item['is_read'] for item in notifications),
    }


# ----------------------------
# PUBLIC ROUTES (Promosi & E-Booking)
# ----------------------------

@app.route('/')
def index():
    today = today_wib()

    active_promo_dest_ids = db.session.query(db.func.coalesce(Promo.destination_id, Hotel.destination_id)).outerjoin(
        Hotel, Promo.hotel_id == Hotel.id
    ).filter(Promo.valid_from <= today, Promo.valid_until >= today)

    # Order popular destinations by ticket sales
    popular_dest_ids = [
        row[0] for row in db.session.query(
            Destination.id
        ).outerjoin(PADReportRecap, Destination.id == PADReportRecap.destination_id
        ).filter(
            Destination.is_active == True,
            Destination.id.in_(active_promo_dest_ids)
        ).group_by(Destination.id
        ).order_by(db.func.coalesce(db.func.sum(PADReportRecap.total_tickets_sold), 0).desc()
        ).all()
    ]

    featured_destinations = []
    for d_id in popular_dest_ids:
        d = Destination.query.get(d_id)
        if d and d.active_promo:
            featured_destinations.append(d)

    # Fallback if no promo destinations found
    if not featured_destinations:
        featured_destinations = Destination.query.filter_by(is_active=True).order_by(Destination.id).limit(5).all()
    namira = Destination.query.filter_by(code='DEST-NMR-01', is_active=True, admission_status='free').first()
    if namira and namira not in featured_destinations:
        featured_destinations.append(namira)

    total_dest = Destination.query.filter_by(is_active=True).count()

    return render_template(
        'index.html',
        destinations=featured_destinations,
        total_dest=total_dest,
        official_agenda=upcoming_poster_events(today),
        promo_feed=holiday_feed.promo_view(),
    )


@app.get('/agenda-libur/pembaruan')
def holiday_updates_partial():
    response = app.make_response(render_template('promo_feed.html', promo_feed=holiday_feed.promo_view()))
    response.cache_control.no_store = True
    return response


@app.post('/api/agenda-libur/webhook')
def holiday_partner_webhook():
    token = app.config['HOLIDAY_WEBHOOK_TOKEN']
    if not holiday_feed.partner_url or not token:
        return '', 404
    expected = f'Bearer {token}'.encode('utf-8')
    provided = request.headers.get('Authorization', '').encode('utf-8')
    if not hmac.compare_digest(provided, expected):
        return '', 401
    if not holiday_feed.request_partner_refresh():
        return jsonify(status='rate_limited'), 429, {'Retry-After': '10'}
    return jsonify(status='accepted'), 202


TAG_GROUPS = {
    'bahari': {
        'name': 'Bahari & Pesisir',
        'tags': [
            'Taman Rekreasi Bahari',
            'Wisata Bahari & Pesisir',
            'Wisata Pesisir & Mangrove',
            'Wisata Bahari & Santai',
            'Wisata Bahari & Camping'
        ]
    },
    'religi_sejarah': {
        'name': 'Religi & Cagar Budaya',
        'tags': [
            'Wisata Religi & Sejarah',
            'Wisata Religi & Arsitektur',
            'Wisata Religi & Kesehatan',
            'Wisata Sejarah & Cagar Budaya',
            'Wisata Sejarah Kolonial',
            'Wisata Alam & Legenda Sejarah'
        ]
    },
    'alam': {
        'name': 'Alam & Konservasi',
        'tags': [
            'Wisata Alam & Edukasi',
            'Wisata Alam & Spot Foto',
            'Wisata Satwa & Geologi',
            'Wisata Geologi & Danau',
            'Ekowisata & Lingkungan'
        ]
    },
    'rekreasi': {
        'name': 'Rekreasi Keluarga',
        'tags': [
            'Taman Hiburan & Rekreasi Keluarga',
            'Taman Kota & Rekreasi Publik'
        ]
    },
    'edukasi': {
        'name': 'Edukasi & Museum',
        'tags': [
            'Wisata Edukasi & Outbound',
            'Museum Edukasi & Teknologi AR'
        ]
    }
}

@app.route('/destinations')
def destinations():
    search_query = request.args.get('q', '').strip()
    groups = map(str.strip, request.args.getlist('group'))
    selected_group = next((group for group in groups if group in TAG_GROUPS), None)

    # Keep existing links that filter on individual categories.
    selected_tags = [
        tag.strip() for value in request.args.getlist('tags')
        for tag in value.split(',') if tag.strip()
    ]

    # Backward compatibility with single category
    legacy_cat = request.args.get('category', '').strip()
    if legacy_cat and legacy_cat not in selected_tags:
        selected_tags.append(legacy_cat)

    query = Destination.query.filter_by(is_active=True)
    if search_query:
        query = query.filter(
            Destination.name.ilike(f"%{search_query}%") |
            Destination.description.ilike(f"%{search_query}%") |
            Destination.location.ilike(f"%{search_query}%")
        )

    if selected_tags:
        selected_group = None
        query = query.filter(Destination.category.in_(selected_tags))
    elif selected_group:
        query = query.filter(Destination.category.in_(TAG_GROUPS[selected_group]['tags']))

    all_destinations = query.order_by(Destination.name.asc()).all()

    return render_template(
        'destinations.html',
        destinations=all_destinations,
        tag_groups=TAG_GROUPS,
        selected_group=selected_group,
        selected_tags=selected_tags,
        search_query=search_query
    )

@app.route('/destinations/<int:id>')
def destination_detail(id):
    destination = Destination.query.filter_by(id=id, is_active=True).first_or_404()
    return render_template('destination_detail.html', destination=destination)

@app.route('/booking/<int:destination_id>', methods=['GET', 'POST'])
def booking(destination_id):
    destination_query = Destination.query.filter_by(id=destination_id, is_active=True)
    if request.method == 'POST':
        destination_query = destination_query.with_for_update()
    destination = destination_query.first_or_404()
    ticket_types = destination.available_tickets
    if not ticket_types:
        return redirect(url_for('destination_detail', id=destination_id))

    visitor = current_visitor()
    if visitor is None:
        return redirect(url_for('visitor_auth.login', destination_id=destination_id))

    today = today_wib()
    if request.method == 'POST':
        verify_visitor_csrf()
        visitor_name = normalize_name(request.form.get('visitor_name', ''))
        visitor_phone = normalize_phone(request.form.get('visitor_phone', ''))
        payment_method = request.form.get('payment_method', 'cash')
        if visitor_name.casefold() != visitor.full_name.casefold() or visitor_phone != visitor.phone:
            flash('Nama lengkap dan nomor WhatsApp atau telepon harus sesuai dengan akun pengunjung.', 'danger')
            return redirect(url_for('booking', destination_id=destination_id))
        try:
            visit_date = date.fromisoformat(request.form.get('visit_date', ''))
            if visit_date < today or payment_method not in PAYMENT_METHODS:
                raise ValueError
            ticket_items = []
            for ticket_type in ticket_types:
                qty = int(request.form.get(f'qty_{ticket_type.id}', 0))
                if not 0 <= qty <= 50 or (qty and not ticket_type.offered_on(visit_date)):
                    raise ValueError
                if qty:
                    ticket_items.append((ticket_type, qty))
        except ValueError:
            flash('Periksa nama, tanggal kunjungan, dan pilihan tiket untuk tanggal tersebut.', 'danger')
            return redirect(url_for('booking', destination_id=destination_id))
        if not ticket_items:
            flash('Pilih minimal satu tiket untuk tanggal tersebut.', 'warning')
            return redirect(url_for('booking', destination_id=destination_id))

        subtotal = sum(ticket.price * qty for ticket, qty in ticket_items)
        offer = ticket_promo(destination.id, today, visit_date) if request.form.get('use_promo') else None
        if request.form.get('use_promo') and offer is None:
            flash('Promo tidak berlaku untuk tanggal kunjungan yang dipilih. Ubah tanggal atau lanjutkan tanpa promo.', 'warning')
            return redirect(url_for('booking', destination_id=destination_id))
        order = Transaction(
            invoice_number=f'INV-RSV-{secrets.token_hex(12).upper()}',
            destination_id=destination.id,
            visitor_account_id=visitor.id,
            visitor_name=visitor.full_name,
            visitor_phone=visitor.phone,
            total_amount=subtotal,
            payment_method=payment_method,
            payment_status='pending',
        )
        if offer:
            order.promo_code = f'REF-{secrets.token_hex(6).upper()}'
            order.promo_offer = promo_discount(offer, subtotal)
            order.promo_expires_on = offer.valid_until
        db.session.add(order)
        add_order_tickets(order, destination, visit_date, ticket_items)
        db.session.commit()
        return redirect(url_for('ticket_view', invoice_number=order.invoice_number))

    return render_template('booking.html', destination=destination, ticket_types=ticket_types,
                           payment_methods=PAYMENT_METHODS, ticket_offer=ticket_promo(destination.id, today),
                           paid_order_count=paid_order_count(visitor.id), loyalty_percent=LOYALTY_PERCENT,
                           default_date=(today + timedelta(days=1)).isoformat(),
                           earliest_date=today.isoformat())


def add_order_tickets(order, destination, visit_date, ticket_items):
    for ticket_type, qty in ticket_items:
        for _ in range(qty):
            code = generate_ticket_code(destination.code)
            payload, _ = create_ticket_qr_payload(code, destination.id, visit_date.isoformat(), app.config['SECRET_KEY'])
            db.session.add(Ticket(transaction=order, ticket_type=ticket_type, ticket_code=code,
                                  qr_hash=payload, status='valid', valid_for_date=visit_date))


def record_pad_sale(destination_id, report_date, ticket_count, amount):
    recap = PADReportRecap.query.filter_by(destination_id=destination_id, report_date=report_date).with_for_update().first()
    if recap is None:
        recap = PADReportRecap(destination_id=destination_id, report_date=report_date,
                               total_tickets_sold=0, total_revenue=0)
        db.session.add(recap)
    recap.total_tickets_sold += ticket_count
    recap.total_revenue += amount


@app.route('/tickets/<invoice_number>')
def ticket_view(invoice_number):
    transaction = Transaction.query.filter_by(invoice_number=invoice_number).first_or_404()
    tickets = sorted(transaction.tickets, key=lambda ticket: ticket.id) if transaction.payment_status == 'paid' else []

    # Generate Base64 QR Code images for inline display
    ticket_data_list = []
    for t in tickets:
        payload, _ = create_ticket_qr_payload(t.ticket_code, transaction.destination_id,
                                              t.valid_for_date.isoformat(), app.config['SECRET_KEY'])
        qr_b64 = generate_qr_image_base64(payload)
        ticket_data_list.append({
            'ticket': t,
            'qr_b64': qr_b64
        })

    response = app.make_response(render_template('ticket_view.html', transaction=transaction,
                                                 ticket_data_list=ticket_data_list, payment_methods=PAYMENT_METHODS))
    response.cache_control.no_store = True
    return response

# ----------------------------
# POS LOKET & GATE VALIDATION
# ----------------------------

@app.route('/pos', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'cashier')
def pos():
    destinations = Destination.query.filter_by(is_active=True, admission_status='paid').filter(
        Destination.ticket_types.any(TicketType.is_active.is_(True) & (TicketType.price > 0))
    ).all()
    selected_dest_id = request.args.get('dest_id', type=int)
    
    if not selected_dest_id and session.get('user_destination_id'):
        selected_dest_id = session['user_destination_id']
    elif not selected_dest_id and destinations:
        selected_dest_id = destinations[0].id

    selected_dest = next((dest for dest in destinations if dest.id == selected_dest_id), None)
    today = today_wib()
    ticket_types = [ticket for ticket in selected_dest.available_tickets if ticket.offered_on(today)] if selected_dest else []

    if request.method == 'POST':
        visitor_name = request.form.get('visitor_name', '').strip() or 'Pengunjung Loket'
        visitor_phone = request.form.get('visitor_phone', '').strip() or None
        payment_method = request.form.get('payment_method', 'cash')
        dest_id = request.form.get('destination_id', type=int)
        dest = Destination.query.filter_by(id=dest_id, is_active=True).with_for_update().first_or_404()
        tt_list = [ticket for ticket in dest.available_tickets if ticket.offered_on(today)]
        try:
            if len(visitor_name) > 100 or len(visitor_phone or '') > 30 or payment_method not in PAYMENT_METHODS:
                raise ValueError
            ticket_items = []
            for ticket_type in tt_list:
                qty = int(request.form.get(f'qty_{ticket_type.id}', 0))
                if not 0 <= qty <= 100:
                    raise ValueError
                if qty:
                    ticket_items.append((ticket_type, qty))
        except ValueError:
            flash('Periksa nama, kontak, metode pembayaran, dan jumlah tiket.', 'warning')
            return redirect(url_for('pos', dest_id=dest_id))
        if not ticket_items:
            flash('Pilih minimal satu tiket loket yang tersedia.', 'warning')
            return redirect(url_for('pos', dest_id=dest_id))

        invoice_num = generate_invoice_number()
        trans = Transaction(
            invoice_number=invoice_num, destination_id=dest_id, cashier_id=session['user_id'],
            visitor_name=visitor_name, visitor_phone=visitor_phone,
            total_amount=sum(ticket.price * qty for ticket, qty in ticket_items),
            payment_method=payment_method, payment_status='paid',
            paid_at=datetime.now(WIB).replace(tzinfo=None),
        )
        db.session.add(trans)
        add_order_tickets(trans, dest, today, ticket_items)
        record_pad_sale(dest.id, today, sum(qty for _, qty in ticket_items), trans.total_amount)
        db.session.commit()
        flash(f'Tiket loket diterbitkan. Nomor transaksi: {invoice_num}', 'success')
        return redirect(url_for('ticket_view', invoice_number=invoice_num))

    invoice = request.args.get('invoice', '').strip().upper()
    pending = Transaction.query.filter_by(payment_status='pending')
    if session['user_role'] == 'cashier':
        pending = pending.filter_by(destination_id=session.get('user_destination_id'))
    reservation = pending.filter_by(invoice_number=invoice).first() if invoice else None
    pending_reservations = pending.filter(Transaction.tickets.any(Ticket.valid_for_date >= today)).order_by(
        Transaction.transaction_time.desc(), Transaction.id.desc(),
    ).limit(10).all()
    if reservation and 'reservation_csrf' not in session:
        session['reservation_csrf'] = secrets.token_urlsafe(24)
    loyalty = next_loyalty_discount(reservation.visitor_account_id, reservation.total_amount) if reservation else Decimal(0)
    promo = available_promo_discount(reservation, today, loyalty) if reservation else Decimal(0)
    return render_template('pos.html', destinations=destinations, selected_dest=selected_dest, ticket_types=ticket_types,
                           invoice=invoice, reservation=reservation, pending_reservations=pending_reservations,
                           payment_methods=PAYMENT_METHODS, loyalty_quote=loyalty, promo_quote=promo)


@app.post('/pos/reservations/<invoice_number>/confirm')
@login_required
@role_required('admin', 'cashier')
def confirm_reservation(invoice_number):
    staff = db.session.get(User, session['user_id'])
    if staff is None or staff.role not in ('admin', 'cashier'):
        abort(403)
    expected = session.get('reservation_csrf')
    provided = request.form.get('csrf_token', '')
    if not expected or not hmac.compare_digest(expected.encode(), provided.encode()):
        abort(403)
    query = Transaction.query.filter_by(invoice_number=invoice_number)
    if staff.role == 'cashier':
        query = query.filter_by(destination_id=staff.destination_id)
    row = query.with_entities(Transaction.destination_id, Transaction.visitor_account_id).first_or_404()
    dest = Destination.query.filter_by(id=row.destination_id).with_for_update().first_or_404()
    if row.visitor_account_id:
        db.session.get(VisitorAccount, row.visitor_account_id, with_for_update=True)
    order = query.with_for_update().first_or_404()
    if order.payment_status == 'paid':
        return redirect(url_for('ticket_view', invoice_number=order.invoice_number))
    today = today_wib()
    if (
        order.payment_status != 'pending' or not dest.is_active or not order.tickets
        or any(ticket.valid_for_date < today or ticket.status != 'valid' for ticket in order.tickets)
    ):
        flash('Pesanan ini sudah tidak dapat dibayar.', 'warning')
        return redirect(url_for('pos', invoice=invoice_number))

    loyalty = next_loyalty_discount(order.visitor_account_id, order.total_amount, lock=True)
    code = request.form.get('promo_code', '').strip().upper()
    promo = available_promo_discount(order, today, loyalty) if code else Decimal(0)
    if code and (code != order.promo_code or not promo):
        flash('Kode referral tidak cocok dengan reservasi ini atau masa berlakunya sudah habis.', 'warning')
        return redirect(url_for('pos', invoice=invoice_number))
    try:
        correct_quote = Decimal(request.form.get('loyalty_quote', '0')) == loyalty
        if code:
            correct_quote = correct_quote and Decimal(request.form.get('promo_quote', '0')) == promo
    except InvalidOperation:
        correct_quote = False
    if not correct_quote:
        flash('Potongan berubah. Periksa kembali jumlah yang harus dibayar sebelum konfirmasi.', 'warning')
        return redirect(url_for('pos', invoice=invoice_number))

    order.loyalty_discount = loyalty
    order.promo_discount = promo
    order.total_amount -= loyalty + promo
    order.payment_status = 'paid'
    order.cashier_id = staff.id
    order.paid_at = datetime.combine(today, datetime.now(WIB).time())
    record_pad_sale(dest.id, today, len(order.tickets), order.total_amount)
    db.session.commit()
    flash('Pembayaran diterima dan tercatat di PAD.', 'success')
    return redirect(url_for('ticket_view', invoice_number=order.invoice_number))


@app.route('/validator')
@login_required
@role_required('admin', 'gate_keeper', 'cashier')
def validator():
    destinations = Destination.query.filter_by(is_active=True).all()
    recent_scans = Ticket.query.filter(Ticket.scanned_at.isnot(None)).order_by(Ticket.scanned_at.desc()).limit(10).all()
    return render_template('validator.html', destinations=destinations, recent_scans=recent_scans)

@app.route('/api/validate-qr', methods=['POST'])
@login_required
@role_required('admin', 'gate_keeper', 'cashier')
def api_validate_qr():
    data = request.get_json(silent=True)
    qr_payload = data.get('qr_payload') if isinstance(data, dict) else None

    if not isinstance(qr_payload, str) or not qr_payload.strip() or len(qr_payload) > 512:
        return jsonify(success=False, message='Masukkan QR atau kode tiket yang tercetak.'), 400
    qr_payload = qr_payload.strip()
    if qr_payload.upper().startswith('INV-'):
        return jsonify(success=False, message='Gunakan nomor reservasi untuk pembayaran di POS. Untuk masuk, pindai QR atau masukkan kode MGLK- pada tiap tiket.',
                       status_code='RESERVATION_CODE')
    if '|' not in qr_payload:
        qr_payload = qr_payload.upper()

    is_valid, t_code, dest_id, valid_date_str, err_msg = verify_qr_payload(qr_payload, app.config['SECRET_KEY'])

    if not is_valid:
        return jsonify({'success': False, 'message': err_msg, 'status_code': 'INVALID_SIGNATURE'}), 200

    ticket = Ticket.query.filter_by(ticket_code=t_code).first()

    if not ticket:
        return jsonify({'success': False, 'message': f'Kode Tiket {t_code} tidak ditemukan dalam database.', 'status_code': 'NOT_FOUND'}), 200

    if dest_id is not None and (dest_id != str(ticket.transaction.destination_id) or valid_date_str != ticket.valid_for_date.isoformat()):
        return jsonify(success=False, message='Data QR berbeda dari tiket yang tercatat.', status_code='INVALID_TICKET')
    if ticket.transaction.payment_status != 'paid':
        return jsonify(success=False, message='Pembayaran reservasi belum dikonfirmasi.', status_code='UNPAID'), 200

    if ticket.status == 'used':
        scanned_time = ticket.scanned_at.strftime('%d-%m-%Y %H:%M:%S') if ticket.scanned_at else 'Sebelumnya'
        return jsonify({
            'success': False,
            'message': f'TIKET SUDAH DIGUNAKAN! (Telah di-scan pada {scanned_time})',
            'status_code': 'ALREADY_USED',
            'ticket': {
                'code': ticket.ticket_code,
                'visitor': ticket.transaction.visitor_name,
                'destination': ticket.transaction.destination.name,
                'type': ticket.ticket_type.name,
                'scanned_at': scanned_time
            }
        }), 200

    if ticket.status in ['expired', 'cancelled']:
        return jsonify({'success': False, 'message': f'Tiket ini sudah tidak berlaku (Status: {ticket.status.upper()}).', 'status_code': 'EXPIRED'}), 200
    if ticket.valid_for_date != today_wib():
        return jsonify(success=False, message=f'Tiket berlaku pada {ticket.valid_for_date:%d/%m/%Y}.',
                       status_code='VISIT_DATE'), 200

    scanned_at = datetime.now()
    updated = Ticket.query.filter_by(id=ticket.id, status='valid').update({
        'status': 'used', 'scanned_at': scanned_at, 'scanned_by_user_id': session['user_id'],
    }, synchronize_session=False)
    if not updated:
        db.session.rollback()
        return jsonify(success=False, message='Tiket sudah dipindai atau statusnya berubah.',
                       status_code='ALREADY_USED'), 200
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'TIKET VALID! Akses masuk disetujui.',
        'status_code': 'SUCCESS',
        'ticket': {
            'code': ticket.ticket_code,
            'visitor': ticket.transaction.visitor_name,
            'destination': ticket.transaction.destination.name,
            'type': ticket.ticket_type.name,
            'price': float(ticket.ticket_type.price),
            'valid_for_date': str(ticket.valid_for_date),
            'scanned_at': ticket.scanned_at.strftime('%d-%m-%Y %H:%M:%S')
        }
    }), 200

# ----------------------------
# ADMIN & PAD REPORTING DASHBOARD
# ----------------------------

@app.route('/admin/dashboard')
@login_required
@role_required('admin')
def admin_dashboard():
    today = today_wib()
    rows = pad_rows()
    month_start = today.replace(day=1)
    last_7_days = [today - timedelta(days=i) for i in range(6, -1, -1)]
    revenue_by_day = {}
    revenue_by_destination = {}
    for row in rows:
        day = row.report_date
        revenue_by_day[day] = revenue_by_day.get(day, 0) + row.total_revenue
        name = row.destination_name
        revenue_by_destination[name] = revenue_by_destination.get(name, 0) + row.total_revenue

    recent_transactions = Transaction.query.order_by(Transaction.transaction_time.desc(), Transaction.id.desc()).limit(8).all()
    pending_count = Transaction.query.filter_by(payment_status='pending').count()
    return render_template(
        'admin/dashboard.html',
        today_revenue=revenue_by_day.get(today, 0),
        total_revenue=sum(revenue_by_day.values()),
        this_month_revenue=sum(revenue for day, revenue in revenue_by_day.items() if month_start <= day <= today),
        total_tickets_sold=sum(row.total_tickets_sold for row in rows),
        chart_labels=list(revenue_by_destination),
        chart_revenue_data=[float(amount) for amount in revenue_by_destination.values()],
        trend_labels=[day.strftime('%d %b') for day in last_7_days],
        trend_revenue=[float(revenue_by_day.get(day, 0)) for day in last_7_days],
        recent_transactions=recent_transactions,
        pending_count=pending_count,
    )


def pad_filters():
    try:
        start = request.args.get('start_date', '').strip()
        end = request.args.get('end_date', '').strip()
        return date.fromisoformat(start) if start else None, date.fromisoformat(end) if end else None
    except ValueError:
        abort(400, 'Gunakan tanggal dalam format YYYY-MM-DD.')


@app.route('/admin/pad-reports')
@login_required
@role_required('admin')
def pad_reports():
    start, end = pad_filters()
    dest_id = request.args.get('dest_id', type=int)
    recaps = pad_rows(start, end, dest_id)
    current_year = today_wib().year
    yearly_breakdown = {}
    for row in pad_rows(date(current_year, 1, 1), date(current_year, 12, 31), dest_id):
        monthly = yearly_breakdown.setdefault(row.destination_name, [0] * 12)
        monthly[row.report_date.month - 1] += float(row.total_revenue)

    return render_template(
        'admin/pad_reports.html',
        recaps=recaps,
        destinations=Destination.query.all(),
        start_date=start.isoformat() if start else '',
        end_date=end.isoformat() if end else '',
        selected_dest_id=dest_id,
        total_tickets=sum(row.total_tickets_sold for row in recaps),
        total_pad_revenue=sum(row.total_revenue for row in recaps),
        yearly_breakdown=yearly_breakdown,
        current_year=current_year,
    )


@app.route('/admin/export-pad-csv')
@login_required
@role_required('admin')
def export_pad_csv():
    start, end = pad_filters()
    recaps = pad_rows(start, end, request.args.get('dest_id', type=int))
    output = [['Tanggal Pembayaran', 'Kode Destinasi', 'Nama Objek Wisata', 'Total Tiket Terjual', 'Total Pendapatan (PAD Rp)']]
    for row in recaps:
        output.append([
            row.report_date.isoformat(), row.destination_code, row.destination_name,
            row.total_tickets_sold, row.total_revenue,
        ])

    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerows(output)

    return Response(
        si.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename=Rekap_PAD_MegiLoka_{datetime.now().strftime('%Y%m%d')}.csv"}
    )

# ----------------------------
# MASTER DATA DESTINASI (CRUD)
# ----------------------------

@app.route('/admin/destinations')
@login_required
@role_required('admin')
def destinations_crud():
    destinations = Destination.query.order_by(Destination.id.desc()).all()
    return render_template('admin/destinations_crud.html', destinations=destinations)

def apply_visit_fields(dest):
    status = request.form.get('admission_status', 'unknown')
    if status not in ('unknown', 'free', 'paid'):
        raise ValueError('Pilih status tiket masuk yang valid.')
    for field in ('source_url', 'ticket_url', 'image_source_url', 'image_url'):
        value = request.form.get(field, '').strip()
        parsed = urlsplit(value)
        local_photo = field == 'image_url' and value.startswith('/static/images/')
        limit = 255 if field == 'image_url' else 500
        if value and (len(value) > limit or (not local_photo and (parsed.scheme not in ('http', 'https') or not parsed.hostname))):
            raise ValueError('Gunakan URL sumber, foto, dan tiket yang valid.')
        setattr(dest, field, value or None)
    dest.admission_status = status
    dest.admission_info = request.form.get('admission_info', '').strip() or None
    dest.parking_info = request.form.get('parking_info', '').strip() or None
    if status != 'paid':
        dest.ticket_url = None
        for ticket in dest.ticket_types:
            ticket.is_active = False
        dest.base_price = 0


@app.route('/admin/destinations/create', methods=['POST'])
@login_required
@role_required('admin')
def destination_create():
    name = request.form.get('name', '').strip()
    code = request.form.get('code', '').strip().upper()
    category = request.form.get('category', 'Wisata Alam').strip()
    location = request.form.get('location', '').strip()
    description = request.form.get('description', '').strip()

    if not name or not code or not location:
        flash('Nama, Kode, dan Lokasi destinasi wajib diisi.', 'danger')
        return redirect(url_for('destinations_crud'))

    if Destination.query.filter_by(code=code).first():
        flash(f'Kode Destinasi {code} sudah digunakan.', 'danger')
        return redirect(url_for('destinations_crud'))

    dest = Destination(
        code=code,
        name=name,
        category=category,
        location=location,
        description=description,
        is_active=True
    )
    try:
        apply_visit_fields(dest)
    except ValueError as error:
        flash(str(error), 'danger')
        return redirect(url_for('destinations_crud'))
    db.session.add(dest)
    db.session.commit()

    flash(f'Destinasi wisata {name} berhasil ditambahkan!', 'success')
    return redirect(url_for('destinations_crud'))

@app.route('/admin/destinations/edit/<int:id>', methods=['POST'])
@login_required
@role_required('admin')
def destination_edit(id):
    dest = Destination.query.filter_by(id=id).with_for_update().first_or_404()
    try:
        apply_visit_fields(dest)
    except ValueError as error:
        db.session.rollback()
        flash(str(error), 'danger')
        return redirect(url_for('destinations_crud'))
    dest.name = request.form.get('name', dest.name).strip()
    dest.category = request.form.get('category', dest.category).strip()
    dest.location = request.form.get('location', dest.location).strip()
    dest.description = request.form.get('description', dest.description).strip()
    dest.is_active = True if request.form.get('is_active') == 'on' else False

    db.session.commit()
    flash(f'Data destinasi {dest.name} berhasil diperbarui.', 'success')
    return redirect(url_for('destinations_crud'))

@app.route('/admin/destinations/delete/<int:id>', methods=['POST'])
@login_required
@role_required('admin')
def destination_delete(id):
    dest = Destination.query.filter_by(id=id).with_for_update().first_or_404()
    if (Transaction.query.filter_by(destination_id=id).first()
            or PADReportRecap.query.filter_by(destination_id=id).first()):
        dest.is_active = False
        db.session.commit()
        flash(f'Destinasi {dest.name} dinonaktifkan. Riwayat transaksi dan PAD tetap tersimpan.', 'info')
        return redirect(url_for('destinations_crud'))
    return delete_admin_record(dest, 'Destinasi', 'destinations_crud')


def delete_admin_record(record, label, return_to):
    name = record.name
    db.session.delete(record)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        app.logger.exception('Could not delete %s', type(record).__name__)
        flash(f'{label} masih terkait dengan data lain atau telah berubah. Muat ulang dan coba lagi.', 'danger')
    else:
        flash(f'{label} {name} telah dihapus.', 'success')
    return redirect(url_for(return_to))

@app.route('/admin/ticket-types/create', methods=['POST'])
@login_required
@role_required('admin')
def ticket_type_create():
    dest_id = request.form.get('destination_id', type=int)
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    try:
        price = Decimal(request.form.get('price', ''))
    except InvalidOperation:
        price = Decimal(0)
    if not name or not price.is_finite() or not 1 <= price < 10_000_000_000:
        flash('Nama dan harga tiket harus diisi dengan benar.', 'danger')
        return redirect(url_for('destinations_crud'))

    dest = Destination.query.filter_by(id=dest_id).with_for_update().first_or_404()
    if dest.admission_status != 'paid' or not dest.is_active:
        flash('Tarif loket hanya dapat ditambahkan untuk destinasi aktif dan berbayar.', 'warning')
        return redirect(url_for('destinations_crud'))
    db.session.add(TicketType(destination=dest, name=name, price=price, description=description))
    db.session.flush()
    dest.base_price = min(ticket.price for ticket in dest.available_tickets)
    db.session.commit()
    flash(f'Jenis tiket {name} berhasil ditambahkan!', 'success')
    return redirect(url_for('destinations_crud'))


@app.post('/admin/ticket-types/retire/<int:id>')
@login_required
@role_required('admin')
def ticket_type_retire(id):
    dest = Destination.query.join(TicketType).filter(TicketType.id == id).with_for_update().first_or_404()
    ticket = db.get_or_404(TicketType, id)
    ticket.is_active = False
    dest.base_price = min((item.price for item in dest.available_tickets), default=0)
    db.session.commit()
    flash('Tarif loket dinonaktifkan. Riwayat tiket tetap tersimpan.', 'success')
    return redirect(url_for('destinations_crud'))


# ----------------------------
# HOTELS & PROMOS CRUD
# ----------------------------

@app.route('/admin/hotels')
@login_required
@role_required('admin')
def hotels_crud():
    hotels = Hotel.query.order_by(Hotel.id.desc()).all()
    destinations = Destination.query.filter_by(is_active=True).all()
    direct_promos = Promo.query.filter_by(hotel_id=None).order_by(Promo.valid_until.desc()).all()
    return render_template('admin/hotels_crud.html', hotels=hotels, destinations=destinations, direct_promos=direct_promos)


@app.post('/admin/hotels/delete/<int:id>')
@login_required
@role_required('admin')
def hotel_delete(id):
    return delete_admin_record(db.get_or_404(Hotel, id), 'Hotel', 'hotels_crud')


@app.post('/admin/promos/delete/<int:id>')
@login_required
@role_required('admin')
def promo_delete(id):
    return delete_admin_record(db.get_or_404(Promo, id), 'Promo', 'hotels_crud')

@app.route('/admin/hotels/create', methods=['POST'])
@login_required
@role_required('admin')
def hotel_create():
    name = request.form.get('name')
    location = request.form.get('location')
    dest_id = request.form.get('destination_id')
    desc = request.form.get('description')
    
    h = Hotel(name=name, location=location, destination_id=dest_id, description=desc)
    db.session.add(h)
    db.session.commit()
    flash('Hotel berhasil ditambahkan.', 'success')
    return redirect(url_for('hotels_crud'))

@app.route('/admin/promos/create', methods=['POST'])
@login_required
@role_required('admin')
def promo_create():
    hotel_id = request.form.get('hotel_id', type=int)
    destination_id = request.form.get('destination_id', type=int)
    name = request.form.get('name', '').strip()
    try:
        percent = Decimal(request.form.get('discount_percent', ''))
        valid_from = date.fromisoformat(request.form.get('valid_from', ''))
        valid_until = date.fromisoformat(request.form.get('valid_until', ''))
        if (bool(hotel_id) == bool(destination_id) or not 1 <= len(name) <= 150
                or not percent.is_finite() or not Decimal('0.01') <= percent <= 100 or valid_until < valid_from):
            raise ValueError
    except (ValueError, InvalidOperation):
        flash('Periksa destinasi atau hotel, nama, diskon, dan tanggal berlaku promo.', 'warning')
        return redirect(url_for('hotels_crud'))
    if hotel_id:
        db.get_or_404(Hotel, hotel_id)
    else:
        Destination.query.filter_by(id=destination_id, is_active=True, admission_status='paid').first_or_404()

    p = Promo(hotel_id=hotel_id, destination_id=destination_id, name=name,
              discount_percent=percent, valid_from=valid_from, valid_until=valid_until)
    db.session.add(p)
    db.session.commit()
    flash('Promo berhasil ditambahkan.', 'success')
    return redirect(url_for('hotels_crud'))

# ----------------------------
# EVENTS CALENDAR
# ----------------------------

@app.route('/admin/events')
@login_required
@role_required('admin')
def events_crud():
    events = Event.query.order_by(Event.event_date.desc()).all()
    destinations = Destination.query.all()
    return render_template('admin/events_crud.html', events=events, destinations=destinations)


@app.post('/admin/events/delete/<int:id>')
@login_required
@role_required('admin')
def event_delete(id):
    return delete_admin_record(db.get_or_404(Event, id), 'Event', 'events_crud')

@app.route('/admin/events/create', methods=['POST'])
@login_required
@role_required('admin')
def event_create():
    name = request.form.get('name')
    dest_id = request.form.get('destination_id')
    event_date_str = request.form.get('event_date')
    desc = request.form.get('description')
    
    event_date = datetime.strptime(event_date_str, '%Y-%m-%d').date() if event_date_str else None
    
    if not dest_id:
        dest_id = None
        
    e = Event(name=name, destination_id=dest_id, event_date=event_date, description=desc)
    db.session.add(e)
    db.session.commit()
    flash('Event berhasil ditambahkan.', 'success')
    return redirect(url_for('events_crud'))

@app.route('/calendar')
def public_calendar():
    today = today_wib()
    return render_template(
        'calendar.html', instagram_events=holiday_feed.instagram_events(today),
        poster_months=poster_months(today), poster_year=POSTER_YEAR, poster_source=POSTER_PAGE,
        poster_page_updated=holiday_feed.poster_page_updated(),
        district_events=holiday_feed.district_events(today),
    )

# ----------------------------
# AUTHENTICATION
# ----------------------------

def staff_home(role):
    return {'admin': 'admin_dashboard', 'gate_keeper': 'validator'}.get(role, 'pos')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user_id'):
        return redirect(url_for(staff_home(session.get('user_role'))))
    if current_visitor():
        return redirect(url_for('visitor_auth.orders'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['full_name'] = user.full_name
            session['user_role'] = user.role
            session['user_destination_id'] = user.destination_id

            flash(f'Selamat datang kembali, {user.full_name}!', 'success')
            return redirect(url_for(staff_home(user.role)))

        flash('Username atau Password salah.', 'danger')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Anda telah keluar dari akun.', 'info')
    return redirect(url_for('index'))

# ----------------------------
# AI CONCIERGE & CS AUTO-PUBLISHER API
# ----------------------------

@app.route('/api/guest/notifications')
def api_guest_notifications():
    items = get_upcoming_items()
    return jsonify(success=True, total=sum(not item['is_read'] for item in items), notifications=items)


@app.post('/notifications/read/<notification_id>')
def read_guest_notification(notification_id):
    items = get_upcoming_items()
    selected = next((item for item in items if item['id'] == notification_id), None)
    if selected is None:
        return redirect(url_for('public_calendar', _anchor='poster-calendar-title'), code=303)
    session['read_agenda_notifications'] = [item['id'] for item in items if item['is_read'] or item is selected]
    return redirect(selected['url'], code=303)


@app.route('/api/ai/chat', methods=['POST'])
def api_ai_chat():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(success=False, reply='Kirim objek JSON dengan pertanyaan teks.'), 400
    if any(not isinstance(data.get(key, ''), str) for key in ('message', 'action', 'range')):
        return jsonify(success=False, reply='Pertanyaan, aksi, dan rentang harus berupa teks.'), 400
    user_msg = data.get('message', '').strip()
    action = data.get('action', '').strip()
    range_type = data.get('range', '1month').strip()
    if len(user_msg) > 2000 or action not in ('', 'chat', 'add_event', 'add_destination'):
        return jsonify(success=False, reply='Pertanyaan maksimal 2000 karakter dan aksi harus dikenal.'), 400

    if not user_msg and not action:
        return jsonify({
            'success': False,
            'reply': 'Silakan ketik pertanyaan tentang wisata atau jadwal event Lamongan.'
        }), 400

    if action in ('', 'chat'):
        detected = detect_ai_intent(user_msg)
        if detected['intent'] in ['add_event', 'add_destination']:
            action = detected['intent']
            range_type = detected.get('range', range_type)

    if action in ('add_event', 'add_destination'):
        user_id = session.get('user_id')
        user = db.session.get(User, user_id) if isinstance(user_id, int) else None
        if not user or user.role != 'admin' or session.get('user_role') != 'admin':
            return jsonify(success=False, reply='Penambahan data hanya untuk administrator. Pengunjung dapat menanyakan jadwal, lokasi, dan harga tiket.'), 403
    elif not user_msg:
        return jsonify(success=False, reply='Silakan ketik pertanyaan Anda.'), 400

    today = date.today()

    # ACTION 1: ADD EVENT
    if action == 'add_event':
        target_date, days_diff, date_label = resolve_date_target(range_type)

        available_templates = [t for t in LAMONGAN_EVENT_TEMPLATES if not Event.query.filter_by(name=t['name']).first()]
        if not available_templates:
            template = random.choice(LAMONGAN_EVENT_TEMPLATES)
            event_name = f"{template['name']} Edisi {target_date.year}"
        else:
            template = available_templates[0]
            event_name = template['name']

        # Custom name override
        name_match = re.search(r'["\'](.*?)["\']', user_msg)
        if name_match:
            event_name = name_match.group(1).strip()

        dest_obj = None
        if template.get('dest_code_hint'):
            dest_obj = Destination.query.filter_by(code=template['dest_code_hint']).first()

        new_event = Event(
            destination_id=dest_obj.id if dest_obj else None,
            name=event_name,
            description=template['description'],
            event_date=target_date,
            image_url=template['image_url']
        )
        db.session.add(new_event)
        db.session.commit()

        timing_status = "H-1 Hari (Besok!)" if days_diff <= 1 else f"H-{days_diff} (1 Bulan ke Depan)" if days_diff <= 30 else f"Agenda {days_diff} Hari ke Depan"

        reply_msg = (
            f"🎉 **Berhasil Menambahkan Event Pariwisata Lamongan!**\n\n"
            f"📌 **Nama Event**: {new_event.name}\n"
            f"📅 **Tanggal Pelaksanaan**: {new_event.event_date.strftime('%d %B %Y')} ({timing_status})\n"
            f"📍 **Lokasi**: {dest_obj.name if dest_obj else 'Kabupaten Lamongan'}\n"
            f"📝 **Deskripsi**: {new_event.description}\n\n"
        )
        reply_msg += 'Event tersimpan di Kelola Kalender Event sebagai agenda internal.'

        return jsonify({
            'success': True,
            'action_executed': 'add_event',
            'reply': reply_msg,
            'item': {
                'id': new_event.id,
                'type': 'event',
                'name': new_event.name,
                'date': str(new_event.event_date),
                'days_left': days_diff,
                'is_spotlight': False,
                'badge': 'H-1 (BESOK!)' if days_diff <= 1 else f'H-{days_diff} (1 BULAN LAGI)' if days_diff <= 30 else f'{days_diff} HARI'
            }
        })

    # ACTION 2: ADD DESTINATION
    elif action == 'add_destination':
        target_date, days_diff, date_label = resolve_date_target(range_type)

        available_templates = [t for t in LAMONGAN_DESTINATION_TEMPLATES if not Destination.query.filter_by(name=t['name']).first()]
        if not available_templates:
            template = random.choice(LAMONGAN_DESTINATION_TEMPLATES)
            dest_name = f"{template['name']} #{random.randint(2, 99)}"
        else:
            template = available_templates[0]
            dest_name = template['name']

        # Custom name override
        name_match = re.search(r'["\'](.*?)["\']', user_msg)
        if name_match:
            dest_name = name_match.group(1).strip()

        dest_code = f"DEST-{template['code_prefix']}-{random.randint(100, 999)}"

        new_dest = Destination(
            code=dest_code,
            name=dest_name,
            category=template['category'],
            location=template['location'],
            description=template['description'],
            opening_date=target_date,
            is_active=False
        )
        db.session.add(new_dest)
        db.session.flush()

        db.session.commit()

        timing_status = "H-1 Hari (Besok Grand Opening!)" if days_diff <= 1 else f"Buka dalam {days_diff} Hari (1 Bulan Lagi)" if days_diff <= 30 else f"Grand Opening {days_diff} Hari ke Depan"

        reply_msg = (
            f"🏖️ **Draf Destinasi Wisata Lamongan tersimpan!**\n\n"
            f"🏷️ **Nama Wisata**: {new_dest.name} (Kode: `{new_dest.code}`)\n"
            f"📅 **Tanggal Pembukaan / Grand Opening**: {new_dest.opening_date.strftime('%d %B %Y')} ({timing_status})\n"
            f"📍 **Lokasi**: {new_dest.location}\n"
            f"📝 **Deskripsi**: {new_dest.description}\n\n"
        )
        reply_msg += 'Destinasi tersimpan di Kelola Destinasi.'

        return jsonify({
            'success': True,
            'action_executed': 'add_destination',
            'reply': reply_msg,
            'item': {
                'id': new_dest.id,
                'type': 'destination',
                'name': new_dest.name,
                'code': new_dest.code,
                'opening_date': str(new_dest.opening_date),
                'days_left': days_diff,
                'is_spotlight': False,
                'badge': 'H-1 (BESOK!)' if days_diff <= 1 else f'H-{days_diff} (1 BULAN LAGI)' if days_diff <= 30 else f'{days_diff} HARI'
            }
        })

    # DEFAULT: Conversational Customer Service Assistant
    try:
        result = answer_question(user_msg, holiday_view=holiday_feed.view)
    except ModelUnavailable:
        app.logger.exception('Megi local model unavailable')
        return jsonify(success=False, reply='Model Megi belum tersedia. Pengelola perlu menjalankan training: python backend/train_ai.py.'), 503
    return jsonify(success=True, action_executed='chat', **result)

if __name__ == '__main__':
    seed_database()
    host = os.getenv('HOST', '127.0.0.1')
    port = int(os.getenv('PORT', 5000))
    print("=======================================================")
    print(" MegiLoka - E-Ticketing & PAD System Kab. Lamongan ")
    print(f" Server Running on: http://{host}:{port} ")
    print("=======================================================")
    app.run(host=host, port=port, debug=True)
