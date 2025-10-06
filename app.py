from functools import wraps
from typing import Optional

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
from werkzeug.security import check_password_hash, generate_password_hash

from parking_system import SmartParkingSystem

app = Flask(__name__)
app.config['SECRET_KEY'] = 'smart-parking-secret-key'

parking = SmartParkingSystem()

ADMIN_CREDENTIALS = {'login_id': 'admin', 'password': 'admin'}


def success_response(data=None, message: str = "Success"):
    """Standardise successful API responses."""
    return jsonify({
        'success': True,
        'data': data or {},
        'message': message
    })


def error_response(message: str = "An error occurred", status_code: int = 400, data=None):
    """Standardise API error responses."""
    response = jsonify({
        'success': False,
        'data': data or {},
        'message': message
    })
    response.status_code = status_code
    return response


def is_logged_in() -> bool:
    return bool(session.get('logged_in'))


def is_admin() -> bool:
    return session.get('user_role') == 'admin'


def ensure_api_login(admin_only: bool = False):
    if not is_logged_in():
        return error_response('Authentication required', 401)
    if admin_only and not is_admin():
        return error_response('Admin access required', 403)
    return None


def get_active_user_id() -> Optional[int]:
    return session.get('active_user_id')


def set_active_user(user_id: Optional[int]):
    if user_id:
        session['active_user_id'] = user_id
    else:
        session.pop('active_user_id', None)


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not is_logged_in():
            if request.path.startswith('/api/'):
                return error_response('Authentication required', 401)
            next_url = request.path if request.method == 'GET' else url_for('index')
            return redirect(url_for('login', next=next_url))
        return view(*args, **kwargs)

    return wrapped_view


def admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not is_logged_in() or not is_admin():
            if request.path.startswith('/api/'):
                return error_response('Admin access required', 403)
            return redirect(url_for('login'))
        return view(*args, **kwargs)

    return wrapped_view


@app.before_request
def cleanup_expired_reservations():
    """Ensure expired reservations are marked complete on every request."""
    parking.release_expired_reservations()


@app.context_processor
def inject_template_context():
    user = None
    user_id = get_active_user_id()
    if user_id:
        user = parking.get_user_by_id(user_id)
        if not user:
            set_active_user(None)
    return {
        'active_user': user,
        'is_admin': is_admin(),
        'is_logged_in': is_logged_in()
    }


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle admin and user authentication."""
    if is_logged_in():
        return redirect(url_for('index'))

    errors = []
    next_url = request.args.get('next') or url_for('index')

    if request.method == 'POST':
        login_id = request.form.get('login_id', '').strip()
        password = request.form.get('password', '')
        next_url = request.form.get('next') or url_for('index')

        if login_id == ADMIN_CREDENTIALS['login_id'] and password == ADMIN_CREDENTIALS['password']:
            session.clear()
            session['logged_in'] = True
            session['user_role'] = 'admin'
            set_active_user(None)
            return redirect(next_url if next_url else url_for('admin_dashboard'))

        credentials = parking.get_user_credentials(login_id)
        if credentials and check_password_hash(credentials['password_hash'], password):
            session.clear()
            session['logged_in'] = True
            session['user_role'] = 'user'
            set_active_user(credentials['user_id'])
            return redirect(next_url)

        errors.append('Invalid login or password.')

    return render_template('login.html', errors=errors, next_url=next_url)


@app.route('/logout')
def logout():
    """Clear the current session."""
    session.clear()
    return redirect(url_for('login'))


@app.route('/')
@login_required
def index():
    """Main dashboard."""
    summary = parking.get_availability_summary()
    quick_links = [
        {'label': 'Reservations', 'url': url_for('reservations'), 'icon': 'bi-calendar-check'},
        {'label': 'Parking Slots', 'url': url_for('slots'), 'icon': 'bi-grid'},
        {'label': 'Analytics', 'url': url_for('analytics'), 'icon': 'bi-graph-up'},
        {'label': 'Payment Showcase', 'url': url_for('payment_showcase'), 'icon': 'bi-credit-card'}
    ]
    if is_admin():
        quick_links.append({'label': 'Manage Users', 'url': url_for('manage_users'), 'icon': 'bi-people'})
        quick_links.append({'label': 'Admin Dashboard', 'url': url_for('admin_dashboard'), 'icon': 'bi-speedometer'})
        quick_links.append({'label': 'Database View', 'url': url_for('admin_database'), 'icon': 'bi-hdd-network'})
    return render_template('dashboard.html', summary=summary, quick_links=quick_links)


@app.route('/slots')
@login_required
def slots():
    """Display all available parking slots."""
    all_slots = parking.search_available_slots_optimized()
    return render_template('slots.html', slots=all_slots)


@app.route('/api/availability')
@login_required
def api_availability():
    summary = parking.get_availability_summary()
    return success_response(summary, 'Availability summary fetched successfully')


@app.route('/api/slots')
@login_required
def api_slots():
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

    return success_response({'slots': slots_data}, 'Slots fetched successfully')


@app.route('/reservations')
@login_required
def reservations():
    """View reservations for the active user."""
    user_id = get_active_user_id()
    if not user_id:
        abort(403, description='Select a user to view reservations.')
    user = parking.get_user_by_id(user_id)
    if not user:
        abort(404, description='User not found')
    reservations_data = parking.get_user_reservations(user_id)
    active_reservation = next((r for r in reservations_data if r['status'] == 'active'), None)
    return render_template(
        'reservations.html',
        user=user,
        reservations=reservations_data,
        active_reservation=active_reservation
    )


@app.route('/api/reserve', methods=['POST'])
@login_required
def api_reserve():
    data = request.get_json(silent=True) or {}
    user_id = data.get('user_id') or get_active_user_id()
    slot_id = data.get('slot_id')
    duration = data.get('duration')

    if user_id is None or slot_id is None or duration is None:
        return error_response('user_id, slot_id and duration are required.', 400)

    try:
        user_id = int(user_id)
        slot_id = int(slot_id)
    except (TypeError, ValueError):
        return error_response('user_id and slot_id must be valid integers', 400)

    if not is_admin() and user_id != get_active_user_id():
        return error_response('You can only reserve for your own account.', 403)

    try:
        duration = float(duration)
    except (TypeError, ValueError):
        return error_response('duration must be a number', 400)

    reservation_id, message = parking.create_reservation_with_payment(user_id, slot_id, duration)
    if reservation_id:
        reservation = parking.get_reservation_details(reservation_id)
        return success_response({'reservation_id': reservation_id, 'reservation': reservation}, message)
    return error_response(message, 400)


@app.route('/api/end-reservation', methods=['POST'])
@login_required
def api_end_reservation():
    data = request.get_json(silent=True) or {}
    reservation_id = data.get('reservation_id')

    if not reservation_id:
        return error_response('reservation_id is required', 400)

    try:
        reservation_id = int(reservation_id)
    except (TypeError, ValueError):
        return error_response('reservation_id must be an integer', 400)

    reservation = parking.get_reservation_details(reservation_id)
    if not reservation:
        return error_response('Reservation not found', 404)

    if not is_admin() and reservation['user_id'] != get_active_user_id():
        return error_response('You can only manage your own reservations.', 403)

    success = parking.end_reservation(reservation_id)
    if success:
        return success_response({'reservation_id': reservation_id}, 'Reservation ended successfully')
    return error_response('Failed to end reservation', 400)


@app.route('/analytics')
@login_required
def analytics():
    predictions = parking.predict_peak_demand()
    revenue = parking.get_revenue_report()
    return render_template('analytics.html', predictions=predictions, revenue=revenue)


@app.route('/api/analytics')
@login_required
def api_analytics():
    predictions = parking.predict_peak_demand()
    revenue = parking.get_revenue_report()
    return success_response({'predictions': predictions, 'revenue': revenue}, 'Analytics generated successfully')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Register a new user account."""
    errors = []
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        login_id = request.form.get('login_id', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        vehicle = request.form.get('vehicle_number', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        balance = request.form.get('initial_balance', type=float) or 0.0

        if not full_name:
            errors.append('Full name is required.')
        if not login_id:
            errors.append('Login ID is required.')
        if not email:
            errors.append('Email is required.')
        if not password:
            errors.append('Password is required.')
        if password and password != confirm_password:
            errors.append('Passwords do not match.')

        if not errors:
            password_hash = generate_password_hash(password)
            user_id = parking.register_user(login_id, full_name, email, phone, vehicle, password_hash, balance)
            if user_id:
                session.clear()
                session['logged_in'] = True
                session['user_role'] = 'user'
                set_active_user(user_id)
                return redirect(url_for('profile', user_id=user_id))
            errors.append('An account with this login or email already exists.')

    return render_template('register.html', errors=errors)


@app.route('/users')
@login_required
def users():
    """Redirect users based on their role."""
    if is_admin():
        return redirect(url_for('manage_users'))
    active_id = get_active_user_id()
    if active_id:
        return redirect(url_for('profile', user_id=active_id))
    abort(403, description='No active user selected.')


@app.route('/profile/<int:user_id>')
@login_required
def profile(user_id: int):
    user = parking.get_user_by_id(user_id)
    if not user:
        abort(404, description='User not found')

    if not is_admin() and user_id != get_active_user_id():
        abort(403, description='You can only view your own profile.')

    if not is_admin():
        set_active_user(user_id)

    reservations_history = parking.get_user_reservations(user_id)
    return render_template('profile.html', user=user, reservations=reservations_history)


@app.route('/payment-demo')
@login_required
def payment_showcase():
    """Static payment showcase page."""
    user_id = get_active_user_id()
    user = parking.get_user_by_id(user_id) if user_id else None
    return render_template('payment_showcase.html', user=user)


@app.route('/admin')
@admin_required
def admin_dashboard():
    revenue = parking.get_revenue_report()
    active_reservations = parking.get_active_reservations()
    summary = parking.get_availability_summary()
    occupancy_by_floor = parking.get_occupancy_by_floor()
    occupancy_by_zone = parking.get_occupancy_by_zone()
    wallet_transactions = parking.get_wallet_transactions()
    users = parking.list_users()

    return render_template(
        'admin.html',
        revenue=revenue,
        active_reservations=active_reservations,
        summary=summary,
        occupancy_by_floor=occupancy_by_floor,
        occupancy_by_zone=occupancy_by_zone,
        wallet_transactions=wallet_transactions,
        users=users
    )


@app.route('/admin/users', methods=['GET', 'POST'])
@admin_required
def manage_users():
    errors = []
    success_message = None

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        login_id = request.form.get('login_id', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        vehicle = request.form.get('vehicle_number', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        balance = request.form.get('initial_balance', type=float) or 0.0

        if not full_name:
            errors.append('Full name is required.')
        if not login_id:
            errors.append('Login ID is required.')
        if not email:
            errors.append('Email is required.')
        if not password:
            errors.append('Password is required.')
        if password and password != confirm_password:
            errors.append('Passwords do not match.')

        if not errors:
            password_hash = generate_password_hash(password)
            user_id = parking.register_user(login_id, full_name, email, phone, vehicle, password_hash, balance)
            if user_id:
                success_message = f'User {full_name} created successfully.'
            else:
                errors.append('Unable to create user. Login ID or email already exists.')

    users = parking.list_users()
    return render_template('manage_users.html', users=users, errors=errors, success_message=success_message)


@app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id: int):
    deleted = parking.delete_user(user_id)
    if deleted and get_active_user_id() == user_id:
        set_active_user(None)
    return redirect(url_for('manage_users'))


@app.route('/admin/database', methods=['GET'])
@admin_required
def admin_database():
    overview = parking.get_database_overview()
    summary = parking.get_availability_summary()
    return render_template('admin_database.html', overview=overview, summary=summary)


@app.route('/admin/database/reset', methods=['POST'])
@admin_required
def admin_reset_database():
    parking.clear_transactional_data()
    return redirect(url_for('admin_database'))


@app.route('/switch-user', methods=['POST'])
@admin_required
def switch_user():
    data = request.get_json(silent=True) or request.form
    user_id = data.get('user_id')
    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        return error_response('A valid user_id is required', 400)

    user = parking.get_user_by_id(user_id)
    if not user:
        return error_response('User not found', 404)

    set_active_user(user_id)
    return success_response({'user': user}, 'Active user updated successfully')


@app.route('/api/add-balance', methods=['POST'])
@admin_required
def api_add_balance():
    data = request.get_json(silent=True) or {}
    user_id = data.get('user_id')
    amount = data.get('amount')

    if not all([user_id, amount]):
        return error_response('user_id and amount are required', 400)

    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return error_response('amount must be a positive number', 400)

    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        return error_response('user_id must be an integer', 400)

    success = parking.add_wallet_balance(user_id, amount)
    if success:
        user = parking.get_user_by_id(user_id)
        return success_response({'user': user}, 'Balance added successfully in INR')
    return error_response('Failed to add balance', 400)


@app.route('/api/users')
@admin_required
def api_users():
    users = parking.list_users()
    return success_response({'users': users}, 'Users fetched successfully')


@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@admin_required
def api_delete_user(user_id: int):
    deleted = parking.delete_user(user_id)
    if deleted:
        if get_active_user_id() == user_id:
            set_active_user(None)
        return success_response({'user_id': user_id}, 'User deleted successfully')
    return error_response('Unable to delete user', 400)


@app.route('/api/user/<int:user_id>')
@login_required
def api_user(user_id: int):
    user = parking.get_user_by_id(user_id)
    if not user:
        return error_response('User not found', 404)

    if not is_admin() and user_id != get_active_user_id():
        return error_response('Access denied', 403)

    reservations = parking.get_user_reservations(user_id)
    data = {
        'user_id': user['user_id'],
        'login_id': user['login_id'],
        'full_name': user['full_name'],
        'email': user['email'],
        'wallet_balance': user['wallet_balance'],
        'reservations': reservations
    }
    return success_response(data, 'User profile fetched successfully')


@app.route('/api/user/<int:user_id>/reservations')
@login_required
def api_user_reservations(user_id: int):
    if not is_admin() and user_id != get_active_user_id():
        return error_response('Access denied', 403)
    reservations = parking.get_user_reservations(user_id)
    return success_response({'reservations': reservations}, 'Reservations fetched successfully')


@app.route('/api/reservations/<int:reservation_id>')
@login_required
def api_reservation_details(reservation_id: int):
    reservation = parking.get_reservation_details(reservation_id)
    if not reservation:
        return error_response('Reservation not found', 404)
    if not is_admin() and reservation['user_id'] != get_active_user_id():
        return error_response('Access denied', 403)
    return success_response({'reservation': reservation}, 'Reservation details fetched successfully')


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
