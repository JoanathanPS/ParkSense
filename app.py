from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    redirect,
    url_for,
    session,
    abort
)
from parking_system import SmartParkingSystem

app = Flask(__name__)
app.config['SECRET_KEY'] = 'smart-parking-secret-key'

parking = SmartParkingSystem()

USD_TO_INR_RATE = 83


def success_response(data=None, message="Success"):
    """Standardize successful API responses"""
    return jsonify({
        'success': True,
        'data': data or {},
        'message': message
    })


def error_response(message="An error occurred", status_code=400, data=None):
    """Standardize error API responses"""
    response = jsonify({
        'success': False,
        'data': data or {},
        'message': message
    })
    response.status_code = status_code
    return response


def convert_currency(balance_usd: float, preferred_currency: str = 'USD'):
    """Return balance in both USD and INR"""
    balance_usd = float(balance_usd or 0)
    balance_inr = round(balance_usd * USD_TO_INR_RATE, 2)
    return {
        'balance_usd': round(balance_usd, 2),
        'balance_inr': balance_inr,
        'display_balance': balance_inr if preferred_currency == 'INR' else round(balance_usd, 2)
    }


def get_preferred_currency(user_id: int) -> str:
    return session.get(f'currency_pref_{user_id}', 'USD')


def set_preferred_currency(user_id: int, currency: str):
    if currency not in {'USD', 'INR'}:
        return False
    session[f'currency_pref_{user_id}'] = currency
    return True


@app.before_request
def cleanup_expired_reservations():
    """Ensure expired reservations are released on each request"""
    parking.release_expired_reservations()


@app.route('/')
def index():
    """Main dashboard"""
    summary = parking.get_availability_summary()
    quick_links = [
        {'label': 'Reservations', 'url': url_for('reservations'), 'icon': 'bi-calendar-check'},
        {'label': 'Analytics', 'url': url_for('analytics'), 'icon': 'bi-graph-up'},
        {'label': 'Users', 'url': url_for('users'), 'icon': 'bi-people'},
        {'label': 'Admin', 'url': url_for('admin_dashboard'), 'icon': 'bi-speedometer'}
    ]
    return render_template('dashboard.html', summary=summary, quick_links=quick_links)


@app.route('/api/availability')
def api_availability():
    """API endpoint for live availability updates"""
    summary = parking.get_availability_summary()
    return success_response(summary, "Availability summary fetched successfully")


@app.route('/slots')
def slots():
    """View all parking slots"""
    all_slots = parking.search_available_slots_optimized()
    return render_template('slots.html', slots=all_slots)


@app.route('/api/slots')
def api_slots():
    """API endpoint for live slot updates"""
    floor = request.args.get('floor', type=int)
    zone = request.args.get('zone')
    slot_type = request.args.get('type')
    max_price = request.args.get('max_price', type=float)

    slots = parking.search_available_slots_optimized(floor, zone, slot_type, max_price)
    slots_data = [{
        'id': s[0],
        'number': s[1],
        'floor': s[2],
        'zone': s[3],
        'type': s[4],
        'available': bool(s[5]),
        'price': float(s[6])
    } for s in slots]

    return success_response({'slots': slots_data}, "Slots fetched successfully")


@app.route('/reservations')
def reservations():
    """View reservations"""
    return render_template('reservations.html')


@app.route('/api/reserve', methods=['POST'])
def api_reserve():
    """Create a new reservation"""
    data = request.get_json(silent=True) or {}
    user_id = data.get('user_id')
    slot_id = data.get('slot_id')
    duration = data.get('duration')

    if not all([user_id, slot_id, duration]):
        return error_response("user_id, slot_id and duration are required.", 400)

    try:
        duration = float(duration)
    except (TypeError, ValueError):
        return error_response('duration must be a number', 400)

    reservation_id, message = parking.create_reservation_with_payment(user_id, slot_id, duration)

    if reservation_id:
        return success_response({'reservation_id': reservation_id}, message)
    return error_response(message, 400)


@app.route('/api/end-reservation', methods=['POST'])
def api_end_reservation():
    """End a reservation"""
    data = request.get_json(silent=True) or {}
    reservation_id = data.get('reservation_id')

    if not reservation_id:
        return error_response("reservation_id is required", 400)

    success = parking.end_reservation(reservation_id)

    if success:
        return success_response({'reservation_id': reservation_id}, "Reservation ended successfully")
    else:
        return error_response('Failed to end reservation', 400)


@app.route('/analytics')
def analytics():
    """View analytics and predictions"""
    predictions = parking.predict_peak_demand()
    revenue = parking.get_revenue_report()
    return render_template('analytics.html', predictions=predictions, revenue=revenue)


@app.route('/api/analytics')
def api_analytics():
    """API endpoint for live analytics updates"""
    predictions = parking.predict_peak_demand()
    revenue = parking.get_revenue_report()

    return success_response({'predictions': predictions, 'revenue': revenue}, "Analytics generated successfully")


@app.route('/users')
def users():
    """Manage users"""
    return render_template('users.html')


@app.route('/api/add-balance', methods=['POST'])
def api_add_balance():
    """Add balance to user wallet"""
    data = request.get_json(silent=True) or {}
    user_id = data.get('user_id')
    amount = data.get('amount')

    if not all([user_id, amount]):
        return error_response('user_id and amount are required', 400)

    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return error_response('amount must be a positive number', 400)

    success = parking.add_wallet_balance(user_id, amount)

    if success:
        user = parking.get_user_by_id(user_id)
        return success_response({'user': user}, "Balance added successfully")
    else:
        return error_response('Failed to add balance', 400)


@app.route('/profile/<int:user_id>', methods=['GET', 'POST'])
def profile(user_id: int):
    """Display user profile with wallet summary"""
    user = parking.get_user_by_id(user_id)
    if not user:
        abort(404, description="User not found")

    if request.method == 'POST':
        currency = request.form.get('preferred_currency')
        if set_preferred_currency(user_id, currency):
            return redirect(url_for('profile', user_id=user_id))

    preferred_currency = get_preferred_currency(user_id)
    balances = convert_currency(user['wallet_balance'], preferred_currency)
    reservations = parking.get_user_reservations(user_id)

    return render_template(
        'profile.html',
        user=user,
        preferred_currency=preferred_currency,
        balances=balances,
        reservations=reservations
    )


@app.route('/api/user/<int:user_id>')
def api_user(user_id: int):
    """Return user profile and reservation information"""
    user = parking.get_user_by_id(user_id)
    if not user:
        return error_response("User not found", 404)

    preferred_currency = get_preferred_currency(user_id)
    balances = convert_currency(user['wallet_balance'], preferred_currency)
    reservations = [
        {
            'slot_number': r['slot_number'],
            'start': r['start_time'],
            'duration': r['duration_hours'],
            'status': r['status']
        }
        for r in parking.get_user_reservations(user_id)
    ]

    data = {
        'user_id': user['user_id'],
        'name': user['username'],
        'balance_usd': balances['balance_usd'],
        'balance_inr': balances['balance_inr'],
        'preferred_currency': preferred_currency,
        'reservations': reservations
    }
    return success_response(data, "User profile fetched successfully")


@app.route('/profile/<int:user_id>/currency', methods=['POST'])
def update_currency(user_id: int):
    """Toggle preferred currency for a user"""
    data = request.get_json(silent=True) or {}
    currency = data.get('preferred_currency') or request.form.get('preferred_currency')

    if not currency:
        return error_response('preferred_currency is required', 400)

    if set_preferred_currency(user_id, currency.upper()):
        return success_response({'preferred_currency': currency.upper()}, 'Currency preference updated')

    return error_response('Invalid currency option', 400)


@app.route('/admin')
def admin_dashboard():
    """Admin dashboard with revenue and occupancy insights"""
    revenue = parking.get_revenue_report()
    active_reservations = parking.get_active_reservations()
    summary = parking.get_availability_summary()
    occupancy_by_floor = parking.get_occupancy_by_floor()
    occupancy_by_zone = parking.get_occupancy_by_zone()
    wallet_transactions = parking.get_wallet_transactions()

    return render_template(
        'admin.html',
        revenue=revenue,
        active_reservations=active_reservations,
        summary=summary,
        occupancy_by_floor=occupancy_by_floor,
        occupancy_by_zone=occupancy_by_zone,
        wallet_transactions=wallet_transactions
    )


@app.errorhandler(404)
def not_found(error):
    message = getattr(error, 'description', 'Resource not found')
    if request.path.startswith('/api/'):
        return error_response(message, 404)
    return render_template('errors/404.html', message=message), 404


@app.errorhandler(500)
def server_error(error):
    message = 'An internal server error occurred.'
    if request.path.startswith('/api/'):
        return error_response(message, 500)
    return render_template('errors/500.html', message=message), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
