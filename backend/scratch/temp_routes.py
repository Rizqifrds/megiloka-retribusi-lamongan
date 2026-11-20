# ----------------------------
# HOTELS & PROMOS CRUD
# ----------------------------

@app.route('/admin/hotels')
@login_required
@role_required('admin')
def hotels_crud():
    hotels = Hotel.query.order_by(Hotel.id.desc()).all()
    destinations = Destination.query.all()
    return render_template('admin/hotels_crud.html', hotels=hotels, destinations=destinations)

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
    hotel_id = request.form.get('hotel_id')
    name = request.form.get('name')
    discount_percent = request.form.get('discount_percent')
    valid_from = request.form.get('valid_from')
    valid_until = request.form.get('valid_until')
    
    p = Promo(hotel_id=hotel_id, name=name, discount_percent=discount_percent, valid_from=valid_from, valid_until=valid_until)
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

@app.route('/admin/events/create', methods=['POST'])
@login_required
@role_required('admin')
def event_create():
    name = request.form.get('name')
    dest_id = request.form.get('destination_id')
    event_date = request.form.get('event_date')
    desc = request.form.get('description')
    
    if not dest_id:
        dest_id = None
        
    e = Event(name=name, destination_id=dest_id, event_date=event_date, description=desc)
    db.session.add(e)
    db.session.commit()
    flash('Event berhasil ditambahkan.', 'success')
    return redirect(url_for('events_crud'))

@app.route('/calendar')
def public_calendar():
    events = Event.query.order_by(Event.event_date.asc()).all()
    return render_template('calendar.html', events=events)
