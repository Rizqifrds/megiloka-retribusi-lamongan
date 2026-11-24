"""Visitor sign-in, independent of staff accounts and ticket notifications."""
import hmac
import re
import secrets
import unicodedata
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from threading import Lock
from time import monotonic

from flask import Blueprint, abort, flash, g, redirect, render_template, request, session, url_for
from sqlalchemy.exc import IntegrityError

from models import VisitorAccount, db

visitor_auth = Blueprint('visitor_auth', __name__, url_prefix='/pengunjung')
attempts = {}
attempt_lock = Lock()


def normalize_name(value):
    return ' '.join(unicodedata.normalize('NFKC', value).split())


def normalize_phone(value):
    if len(value) > 35 or not re.fullmatch(r'[+0-9()\s-]+', value):
        return None
    phone = re.sub(r'[()\s-]', '', value)
    if phone.startswith('0'):
        phone = '+62' + phone[1:]
    elif phone.startswith('62'):
        phone = '+' + phone
    return phone if re.fullmatch(r'\+[1-9][0-9]{7,14}', phone) else None


def visitor_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def token_hash(value):
    return sha256(value.encode()).hexdigest()


def visitor_login_key(name):
    return token_hash(normalize_name(name).casefold())


@visitor_auth.before_app_request
def clear_request_visitor():
    g.pop('visitor_account', None)


def current_visitor():
    if 'visitor_account' not in g:
        token = session.get('visitor_token')
        g.visitor_account = VisitorAccount.query.filter(
            VisitorAccount.session_token_hash == token_hash(token),
            VisitorAccount.session_expires_at > visitor_now(),
        ).first() if isinstance(token, str) and len(token) <= 64 else None
    return g.visitor_account


def visitor_csrf():
    if 'visitor_csrf' not in session:
        session['visitor_csrf'] = secrets.token_urlsafe(24)
    return session['visitor_csrf']


def verify_visitor_csrf():
    expected = session.get('visitor_csrf')
    supplied = request.form.get('csrf_token', '')
    if not isinstance(expected, str) or not hmac.compare_digest(expected.encode(), supplied.encode()):
        abort(400)


def start_session(account):
    token = secrets.token_urlsafe(32)
    account.session_token_hash = token_hash(token)
    account.session_expires_at = visitor_now() + timedelta(hours=12)
    db.session.commit()
    session['visitor_token'] = token
    session.pop('visitor_csrf', None)


def login_attempt_allowed(name_key):
    now = monotonic()
    with attempt_lock:
        for key, (_, expiry) in list(attempts.items()):
            if expiry <= now:
                del attempts[key]
        count, expiry = attempts.get(name_key, (0, now + 600))
        if count >= 8:
            return False
        attempts[name_key] = (count + 1, expiry)
        return True


@visitor_auth.app_context_processor
def visitor_navigation():
    return {'signed_in_visitor': current_visitor(), 'visitor_csrf': visitor_csrf}


@visitor_auth.route('/login', methods=['GET', 'POST'], endpoint='login')
@visitor_auth.route('/daftar', methods=['GET', 'POST'], endpoint='register')
def access():
    registering = request.endpoint == 'visitor_auth.register'
    destination_id = request.args.get('destination_id', type=int)
    if destination_id is not None and destination_id > 0:
        onward = url_for('booking', destination_id=destination_id)
    else:
        onward = url_for('destinations')
    if current_visitor():
        return redirect(onward)
    needs_phone = False
    if request.method == 'POST':
        verify_visitor_csrf()
        phone = normalize_phone(request.form.get('phone', ''))
        password = request.form.get('password', '')
        name = normalize_name(request.form.get('full_name', ''))
        if not name or len(name) > 100 or not 8 <= len(password) <= 128:
            flash('Periksa nama lengkap dan kata sandi. Gunakan minimal 8 karakter.', 'danger')
        elif registering:
            if not any(character.isalpha() for character in name):
                flash('Masukkan nama lengkap yang akan digunakan saat memesan.', 'danger')
            elif not phone:
                flash('Masukkan nomor WhatsApp atau telepon yang valid.', 'danger')
            elif password != request.form.get('password_confirmation'):
                flash('Ulangi kata sandi yang sama.', 'danger')
            else:
                account = VisitorAccount(full_name=name, login_name_key=visitor_login_key(name), phone=phone)
                account.set_password(password)
                db.session.add(account)
                try:
                    start_session(account)
                except IntegrityError:
                    db.session.rollback()
                    flash('Nomor tersebut sudah terdaftar. Silakan masuk.', 'danger')
                else:
                    return redirect(onward)
        elif not login_attempt_allowed(visitor_login_key(name)):
            flash('Percobaan masuk terlalu banyak. Coba lagi dalam beberapa menit.', 'danger')
        else:
            key = visitor_login_key(name)
            matching = [account for account in VisitorAccount.query.filter_by(login_name_key=key)
                        if account.check_password(password)]
            needs_phone = len(matching) > 1
            if needs_phone:
                matching = [account for account in matching if account.phone == phone]
            if len(matching) == 1:
                account, = matching
                start_session(account)
                with attempt_lock:
                    attempts.pop(key, None)
                return redirect(onward)
            if needs_phone:
                flash('Ada lebih dari satu akun yang cocok. Masukkan nomor telepon akun untuk melanjutkan.', 'warning')
            else:
                flash('Nama lengkap atau kata sandi tidak cocok.', 'danger')
    return render_template('visitor_access.html', registering=registering, destination_id=destination_id,
                           needs_phone=needs_phone), {
        'Cache-Control': 'no-store',
    }


@visitor_auth.post('/keluar')
def logout():
    verify_visitor_csrf()
    token = session.pop('visitor_token', None)
    if token:
        VisitorAccount.query.filter_by(session_token_hash=token_hash(token)).update({
            'session_token_hash': None, 'session_expires_at': None,
        })
        db.session.commit()
    session.pop('visitor_csrf', None)
    return redirect(url_for('index'))
