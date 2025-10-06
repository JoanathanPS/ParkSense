from flask import Flask, render_template, request, jsonify, redirect, url_for
from parking_system import SmartParkingSystem
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'smart-parking-secret-key'

parking = SmartParkingSystem()

@app.route('/')
def index():
    """Main dashboard"""
    summary = parking.get_availability_summary()
    return render_template('dashboard.html', summary=summary)

@app.route('/api/availability')
def api_availability():
    """API endpoint for live availability updates"""
    summary = parking.get_availability_summary()
    return jsonify(summary)

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
    
    return jsonify(slots_data)

@app.route('/reservations')
def reservations():
    """View reservations"""
    return render_template('reservations.html')

@app.route('/api/reserve', methods=['POST'])
def api_reserve():
    """Create a new reservation"""
    data = request.json
    user_id = data.get('user_id', 1)
    slot_id = data.get('slot_id')
    duration = data.get('duration', 1.0)
    
    reservation_id = parking.create_reservation_with_payment(user_id, slot_id, duration)
    
    if reservation_id:
        return jsonify({'success': True, 'reservation_id': reservation_id})
    else:
        return jsonify({'success': False, 'error': 'Failed to create reservation'}), 400

@app.route('/api/end-reservation', methods=['POST'])
def api_end_reservation():
    """End a reservation"""
    data = request.json
    reservation_id = data.get('reservation_id')
    
    success = parking.end_reservation(reservation_id)
    
    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Failed to end reservation'}), 400

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
    
    return jsonify({
        'predictions': predictions,
        'revenue': revenue
    })

@app.route('/users')
def users():
    """Manage users"""
    return render_template('users.html')

@app.route('/api/add-balance', methods=['POST'])
def api_add_balance():
    """Add balance to user wallet"""
    data = request.json
    user_id = data.get('user_id')
    amount = data.get('amount', 0)
    
    success = parking.add_wallet_balance(user_id, amount)
    
    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Failed to add balance'}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
