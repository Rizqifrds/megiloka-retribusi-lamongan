"""WhatsApp opt-in and H-1 delivery for the official Lamongan calendar."""
import hmac
import json
import re
from datetime import timedelta
from hashlib import sha256
from threading import Lock, Thread
from time import sleep
from urllib.error import URLError
from urllib.request import Request, urlopen

from flask import Blueprint, abort, current_app, render_template, request
from sqlalchemy.exc import IntegrityError

from ai.dates import today_wib
from models import WhatsAppAgendaDelivery, WhatsAppSubscription, db
from utils.lamongan_calendar import poster_events

whatsapp = Blueprint('whatsapp', __name__)
PHONE_PATTERN = re.compile(r'[1-9][0-9]{7,14}')
SUBSCRIPTION_COMMANDS = {'DAFTAR MEGILOKA': True, 'STOP MEGILOKA': False}


def configured(config):
    return bool(
        PHONE_PATTERN.fullmatch(config['WHATSAPP_NUMBER'])
        and re.fullmatch(r'[0-9]+', config['WHATSAPP_PHONE_ID'])
        and re.fullmatch(r'v[0-9]+\.[0-9]+', config['WHATSAPP_API_VERSION'])
        and all(config[key] for key in (
            'WHATSAPP_ACCESS_TOKEN', 'WHATSAPP_APP_SECRET', 'WHATSAPP_VERIFY_TOKEN', 'WHATSAPP_AGENDA_TEMPLATE',
        ))
    )


@whatsapp.get('/notifikasi-whatsapp')
def subscription():
    number = current_app.config['WHATSAPP_NUMBER'] if configured(current_app.config) else None
    return render_template('whatsapp_subscription.html', whatsapp_number=number)


@whatsapp.route('/webhooks/whatsapp', methods=['GET', 'POST'])
def webhook():
    config = current_app.config
    if not configured(config):
        abort(404)
    if request.method == 'GET':
        token = request.args.get('hub.verify_token', '')
        if request.args.get('hub.mode') != 'subscribe' or not hmac.compare_digest(
            token.encode(), config['WHATSAPP_VERIFY_TOKEN'].encode(),
        ):
            abort(403)
        return request.args.get('hub.challenge', '')

    body = request.get_data()
    signature = 'sha256=' + hmac.new(config['WHATSAPP_APP_SECRET'].encode(), body, sha256).hexdigest()
    if not hmac.compare_digest(signature.encode(), request.headers.get('X-Hub-Signature-256', '').encode()):
        abort(403)
    payload = request.get_json()
    if not isinstance(payload, dict) or payload.get('object') != 'whatsapp_business_account':
        return '', 204
    for entry in payload.get('entry', []):
        for change in entry.get('changes', []):
            value = change.get('value', {})
            if value.get('metadata', {}).get('phone_number_id') != config['WHATSAPP_PHONE_ID']:
                continue
            for message in value.get('messages', []):
                if message.get('type') != 'text':
                    continue
                command = message.get('text', {}).get('body', '').strip().upper()
                phone = message.get('from', '')
                timestamp = str(message.get('timestamp', ''))
                if command in SUBSCRIPTION_COMMANDS and PHONE_PATTERN.fullmatch(phone) and re.fullmatch(r'[0-9]{1,12}', timestamp):
                    set_subscription(phone, int(timestamp), SUBSCRIPTION_COMMANDS[command])
    return '', 204


def set_subscription(phone, timestamp, active):
    record = db.session.get(WhatsAppSubscription, phone, with_for_update=True)
    if record is None:
        db.session.add(WhatsAppSubscription(phone=phone, active=active, changed_at=timestamp))
        try:
            db.session.commit()
            return
        except IntegrityError:
            db.session.rollback()
            record = db.session.get(WhatsAppSubscription, phone, with_for_update=True)
    if timestamp > record.changed_at or (timestamp == record.changed_at and not active):
        record.active = active
        record.changed_at = timestamp
    db.session.commit()


def send_template(config, phone, event):
    payload = {
        'messaging_product': 'whatsapp', 'to': phone, 'type': 'template',
        'template': {
            'name': config['WHATSAPP_AGENDA_TEMPLATE'], 'language': {'code': 'id'},
            'components': [{
                'type': 'body',
                'parameters': [
                    {'type': 'text', 'text': event.name},
                    {'type': 'text', 'text': event.date_label},
                ],
            }],
        },
    }
    endpoint = f"https://graph.facebook.com/{config['WHATSAPP_API_VERSION']}/{config['WHATSAPP_PHONE_ID']}/messages"
    message = Request(endpoint, data=json.dumps(payload).encode(), headers={
        'Authorization': 'Bearer ' + config['WHATSAPP_ACCESS_TOKEN'], 'Content-Type': 'application/json',
    })
    with urlopen(message, timeout=10) as response:
        result = json.load(response)
    return bool(result.get('messages', [{}])[0].get('id'))


def dispatch_agenda(config, today):
    tomorrow = today + timedelta(days=1)
    events = [event for event in poster_events(today) if event.start == tomorrow]
    if not events:
        return
    phones = list(db.session.scalars(db.select(WhatsAppSubscription.phone).where(WhatsAppSubscription.active.is_(True))))
    for event in events:
        key = sha256(f'{event.start}|{event.end}|{event.name}'.encode()).hexdigest()
        for phone in phones:
            subscriber = db.session.get(WhatsAppSubscription, phone, with_for_update=True)
            if not subscriber or not subscriber.active or db.session.get(WhatsAppAgendaDelivery, (phone, key)):
                db.session.rollback()
                continue
            db.session.add(WhatsAppAgendaDelivery(phone=phone, event_key=key, status='sending'))
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                continue
            try:
                status = 'accepted' if send_template(config, phone, event) else 'unconfirmed'
            except (URLError, TimeoutError, ValueError, IndexError):
                # Avoid resending when it is unclear whether Meta accepted the request.
                status = 'unconfirmed'
                current_app.logger.warning('WhatsApp agenda delivery could not be confirmed.')
            delivery = db.session.get(WhatsAppAgendaDelivery, (phone, key))
            delivery.status = status
            db.session.commit()


def init_whatsapp(app):
    app.register_blueprint(whatsapp)
    lock = Lock()
    worker = None

    def run():
        with app.app_context():
            while True:
                try:
                    dispatch_agenda(app.config, today_wib())
                except Exception:
                    app.logger.exception('WhatsApp agenda worker failed.')
                finally:
                    db.session.remove()
                sleep(600)

    @app.before_request
    def start_worker():
        nonlocal worker
        if not app.testing and configured(app.config):
            with lock:
                if worker is None or not worker.is_alive():
                    worker = Thread(name='whatsapp-agenda', target=run, daemon=True)
                    worker.start()
