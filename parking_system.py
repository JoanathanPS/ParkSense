import sqlite3
from datetime import datetime, timedelta
from typing import List, Optional, Tuple, Dict
import random
import os

class SmartParkingSystem:
    """
    Smart Parking Management System with three modules:
    1. Database Design & Real-Time Slot Updates
    2. Query Optimization & Slot Search
    3. Reservation Workflow, Payment & Predictive Analytics
    """
    
    def __init__(self, db_name: str = "parking_system.db"):
        self.db_name = db_name
        self.conn = None
        self.cursor = None
        self.initialize_database()
    
    def connect(self):
        """Establish database connection"""
        self.conn = sqlite3.connect(self.db_name)
        self.cursor = self.conn.cursor()
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
    
    def initialize_database(self):
        """MODULE 1: Create optimized database schema with indexes"""
        self.connect()
        
        # Create parking_slots table with optimized schema
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS parking_slots (
                slot_id INTEGER PRIMARY KEY AUTOINCREMENT,
                slot_number VARCHAR(10) UNIQUE NOT NULL,
                floor_number INTEGER NOT NULL,
                zone VARCHAR(50),
                slot_type VARCHAR(20) DEFAULT 'regular',
                is_available BOOLEAN DEFAULT 1,
                price_per_hour DECIMAL(10,2) DEFAULT 5.00,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create users table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username VARCHAR(100) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                phone VARCHAR(20),
                vehicle_number VARCHAR(20),
                wallet_balance DECIMAL(10,2) DEFAULT 0.00,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create reservations table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS reservations (
                reservation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                slot_id INTEGER NOT NULL,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP,
                duration_hours DECIMAL(5,2),
                total_amount DECIMAL(10,2),
                payment_status VARCHAR(20) DEFAULT 'pending',
                status VARCHAR(20) DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (slot_id) REFERENCES parking_slots(slot_id)
            )
        ''')
        
        # Create payments table for MODULE 3
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                reservation_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                amount DECIMAL(10,2) NOT NULL,
                payment_method VARCHAR(50),
                transaction_id VARCHAR(100),
                payment_status VARCHAR(20) DEFAULT 'completed',
                payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (reservation_id) REFERENCES reservations(reservation_id),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')
        
        # Create utilization_stats table for analytics
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS utilization_stats (
                stat_id INTEGER PRIMARY KEY AUTOINCREMENT,
                slot_id INTEGER NOT NULL,
                date DATE NOT NULL,
                hour INTEGER NOT NULL,
                occupancy_count INTEGER DEFAULT 0,
                revenue DECIMAL(10,2) DEFAULT 0.00,
                FOREIGN KEY (slot_id) REFERENCES parking_slots(slot_id),
                UNIQUE(slot_id, date, hour)
            )
        ''')
        
        # MODULE 2: Create indexes for query optimization
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_slots_availability ON parking_slots(is_available)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_slots_floor ON parking_slots(floor_number)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_slots_zone ON parking_slots(zone)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_slots_type ON parking_slots(slot_type)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_reservations_user ON reservations(user_id)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_reservations_slot ON reservations(slot_id)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_reservations_status ON reservations(status)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_payments_user ON payments(user_id)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_payments_reservation ON payments(reservation_id)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_stats_slot_date ON utilization_stats(slot_id, date)')
        
        self.conn.commit()
        self.close()
        print("✓ Database initialized with optimized schema and indexes!")
    
    # ===== MODULE 1: PARKING SLOT OPERATIONS =====
    
    def add_parking_slot(self, slot_number: str, floor_number: int, 
                        zone: str = None, slot_type: str = 'regular', 
                        price_per_hour: float = 5.00) -> bool:
        """Add a new parking slot with pricing"""
        try:
            self.connect()
            self.cursor.execute('''
                INSERT INTO parking_slots (slot_number, floor_number, zone, slot_type, price_per_hour)
                VALUES (?, ?, ?, ?, ?)
            ''', (slot_number, floor_number, zone, slot_type, price_per_hour))
            self.conn.commit()
            self.close()
            print(f"✓ Parking slot {slot_number} added successfully!")
            return True
        except sqlite3.IntegrityError:
            print(f"✗ Error: Slot {slot_number} already exists!")
            self.close()
            return False
    
    def update_slot_availability_realtime(self, slot_id: int, is_available: bool) -> bool:
        """Real-time slot availability update"""
        self.connect()
        self.cursor.execute('''
            UPDATE parking_slots 
            SET is_available = ? 
            WHERE slot_id = ?
        ''', (is_available, slot_id))
        self.conn.commit()
        affected = self.cursor.rowcount
        self.close()
        if affected > 0:
            status = "available" if is_available else "occupied"
            print(f"✓ Slot {slot_id} marked as {status}")
        return affected > 0
    
    # ===== MODULE 1: USER OPERATIONS =====
    
    def register_user(self, username: str, email: str, 
                     phone: str = None, vehicle_number: str = None,
                     initial_balance: float = 0.00) -> bool:
        """Register a new user with wallet"""
        try:
            self.connect()
            self.cursor.execute('''
                INSERT INTO users (username, email, phone, vehicle_number, wallet_balance)
                VALUES (?, ?, ?, ?, ?)
            ''', (username, email, phone, vehicle_number, initial_balance))
            self.conn.commit()
            self.close()
            print(f"✓ User {username} registered successfully!")
            return True
        except sqlite3.IntegrityError:
            print(f"✗ Error: User {username} or email {email} already exists!")
            self.close()
            return False
    
    def add_wallet_balance(self, user_id: int, amount: float) -> bool:
        """Add balance to user wallet"""
        self.connect()
        self.cursor.execute('''
            UPDATE users 
            SET wallet_balance = wallet_balance + ? 
            WHERE user_id = ?
        ''', (amount, user_id))
        self.conn.commit()
        affected = self.cursor.rowcount
        self.close()
        if affected > 0:
            print(f"✓ Added ${amount:.2f} to user {user_id} wallet")
        return affected > 0
    
    # ===== MODULE 2: QUERY OPTIMIZATION & SLOT SEARCH =====
    
    def search_available_slots_optimized(self, floor_number: int = None, 
                                        zone: str = None, slot_type: str = None,
                                        max_price: float = None) -> List[Tuple]:
        """Optimized search using indexes for fast retrieval"""
        self.connect()
        
        query = 'SELECT * FROM parking_slots WHERE is_available = 1'
        params = []
        
        if floor_number is not None:
            query += ' AND floor_number = ?'
            params.append(floor_number)
        
        if zone:
            query += ' AND zone = ?'
            params.append(zone)
        
        if slot_type:
            query += ' AND slot_type = ?'
            params.append(slot_type)
        
        if max_price is not None:
            query += ' AND price_per_hour <= ?'
            params.append(max_price)
        
        query += ' ORDER BY price_per_hour, floor_number, slot_number'
        
        self.cursor.execute(query, params)
        available_slots = self.cursor.fetchall()
        self.close()
        return available_slots
    
    def get_availability_summary(self) -> Dict:
        """Get comprehensive availability summary"""
        self.connect()
        
        # Total and available slots
        self.cursor.execute('SELECT COUNT(*), SUM(CASE WHEN is_available = 1 THEN 1 ELSE 0 END) FROM parking_slots')
        total, available = self.cursor.fetchone()
        occupied = total - available if total and available else 0
        
        # By floor with pricing
        self.cursor.execute('''
            SELECT floor_number, 
                   COUNT(*) as total,
                   SUM(CASE WHEN is_available = 1 THEN 1 ELSE 0 END) as available,
                   AVG(price_per_hour) as avg_price
            FROM parking_slots
            GROUP BY floor_number
            ORDER BY floor_number
        ''')
        by_floor = self.cursor.fetchall()
        
        # By zone
        self.cursor.execute('''
            SELECT zone, 
                   COUNT(*) as total,
                   SUM(CASE WHEN is_available = 1 THEN 1 ELSE 0 END) as available
            FROM parking_slots
            WHERE zone IS NOT NULL
            GROUP BY zone
        ''')
        by_zone = self.cursor.fetchall()
        
        self.close()
        
        return {
            'total_slots': total or 0,
            'available_slots': available or 0,
            'occupied_slots': occupied,
            'occupancy_rate': round((occupied / total * 100) if total and total > 0 else 0, 2),
            'by_floor': by_floor,
            'by_zone': by_zone
        }
    
    # ===== MODULE 3: RESERVATION WORKFLOW =====
    
    def create_reservation_with_payment(self, user_id: int, slot_id: int, 
                                       duration_hours: float,
                                       payment_method: str = 'wallet') -> Optional[int]:
        """Create reservation with integrated payment workflow and proper transaction handling"""
        self.connect()
        try:
            # Begin transaction
            self.conn.execute('BEGIN')
            
            # Check slot availability
            self.cursor.execute('SELECT is_available, price_per_hour FROM parking_slots WHERE slot_id = ?', (slot_id,))
            result = self.cursor.fetchone()
            
            if not result or not result[0]:
                print("✗ Error: Parking slot is not available!")
                self.conn.rollback()
                self.close()
                return None
            
            price_per_hour = result[1]
            total_amount = price_per_hour * duration_hours
            
            # Check user wallet balance
            self.cursor.execute('SELECT wallet_balance FROM users WHERE user_id = ?', (user_id,))
            balance = self.cursor.fetchone()
            
            if not balance or balance[0] < total_amount:
                print(f"✗ Error: Insufficient wallet balance! Need ${total_amount:.2f}, have ${balance[0] if balance else 0:.2f}")
                self.conn.rollback()
                self.close()
                return None
            
            # Create reservation
            start_time = datetime.now()
            end_time = start_time + timedelta(hours=duration_hours)
            
            self.cursor.execute('''
                INSERT INTO reservations (user_id, slot_id, start_time, end_time, duration_hours, total_amount, payment_status, status)
                VALUES (?, ?, ?, ?, ?, ?, 'completed', 'active')
            ''', (user_id, slot_id, start_time.isoformat(), end_time.isoformat(), duration_hours, total_amount))
            
            reservation_id = self.cursor.lastrowid
            
            # Process payment - deduct from wallet
            self.cursor.execute('''
                UPDATE users 
                SET wallet_balance = wallet_balance - ? 
                WHERE user_id = ? AND wallet_balance >= ?
            ''', (total_amount, user_id, total_amount))
            
            if self.cursor.rowcount == 0:
                print(f"✗ Error: Payment failed - concurrent balance change detected")
                self.conn.rollback()
                self.close()
                return None
            
            # Record payment
            transaction_id = f"TXN{datetime.now().strftime('%Y%m%d%H%M%S')}{reservation_id}"
            self.cursor.execute('''
                INSERT INTO payments (reservation_id, user_id, amount, payment_method, transaction_id, payment_status)
                VALUES (?, ?, ?, ?, ?, 'completed')
            ''', (reservation_id, user_id, total_amount, payment_method, transaction_id))
            
            # Update slot availability
            self.cursor.execute('UPDATE parking_slots SET is_available = 0 WHERE slot_id = ?', (slot_id,))
            
            # Record utilization stats with correct UPSERT
            current_date = datetime.now().date()
            current_hour = datetime.now().hour
            self.cursor.execute('''
                INSERT INTO utilization_stats (slot_id, date, hour, occupancy_count, revenue)
                VALUES (?, ?, ?, 1, ?)
                ON CONFLICT(slot_id, date, hour) DO UPDATE SET 
                    occupancy_count = occupancy_count + 1,
                    revenue = revenue + ?
            ''', (slot_id, current_date, current_hour, total_amount, total_amount))
            
            # Commit transaction
            self.conn.commit()
            self.close()
            print(f"✓ Reservation {reservation_id} created! Amount: ${total_amount:.2f}, Duration: {duration_hours}h")
            print(f"✓ Payment processed: {transaction_id}")
            return reservation_id
        except Exception as e:
            print(f"✗ Error creating reservation: {e}")
            if self.conn:
                self.conn.rollback()
            self.close()
            return None
    
    def end_reservation(self, reservation_id: int) -> bool:
        """End reservation and free up the slot"""
        try:
            self.connect()
            
            self.cursor.execute('SELECT slot_id FROM reservations WHERE reservation_id = ?', (reservation_id,))
            result = self.cursor.fetchone()
            
            if not result:
                print("✗ Error: Reservation not found!")
                self.close()
                return False
            
            slot_id = result[0]
            
            self.cursor.execute('''
                UPDATE reservations 
                SET status = 'completed', end_time = ?
                WHERE reservation_id = ?
            ''', (datetime.now().isoformat(), reservation_id))
            
            self.cursor.execute('UPDATE parking_slots SET is_available = 1 WHERE slot_id = ?', (slot_id,))
            
            self.conn.commit()
            self.close()
            print(f"✓ Reservation {reservation_id} ended and slot {slot_id} is now available!")
            return True
        except Exception as e:
            print(f"✗ Error ending reservation: {e}")
            self.close()
            return False
    
    # ===== MODULE 3: ANALYTICS & PREDICTIONS =====
    
    def get_utilization_stats(self, slot_id: int = None, date: str = None) -> List[Tuple]:
        """Get parking slot utilization statistics"""
        self.connect()
        
        query = 'SELECT * FROM utilization_stats WHERE 1=1'
        params = []
        
        if slot_id:
            query += ' AND slot_id = ?'
            params.append(slot_id)
        
        if date:
            query += ' AND date = ?'
            params.append(date)
        
        query += ' ORDER BY date DESC, hour DESC'
        
        self.cursor.execute(query, params)
        stats = self.cursor.fetchall()
        self.close()
        return stats
    
    def predict_peak_demand(self) -> Dict:
        """Predict peak demand hours based on historical data"""
        self.connect()
        
        # Get hourly occupancy patterns
        self.cursor.execute('''
            SELECT hour, AVG(occupancy_count) as avg_occupancy, SUM(revenue) as total_revenue
            FROM utilization_stats
            GROUP BY hour
            ORDER BY avg_occupancy DESC
        ''')
        hourly_stats = self.cursor.fetchall()
        
        # Get busiest zones
        self.cursor.execute('''
            SELECT p.zone, COUNT(r.reservation_id) as reservation_count, SUM(r.total_amount) as total_revenue
            FROM reservations r
            JOIN parking_slots p ON r.slot_id = p.slot_id
            WHERE p.zone IS NOT NULL
            GROUP BY p.zone
            ORDER BY reservation_count DESC
        ''')
        zone_stats = self.cursor.fetchall()
        
        # Get slot type preferences
        self.cursor.execute('''
            SELECT p.slot_type, COUNT(r.reservation_id) as reservation_count
            FROM reservations r
            JOIN parking_slots p ON r.slot_id = p.slot_id
            GROUP BY p.slot_type
            ORDER BY reservation_count DESC
        ''')
        type_stats = self.cursor.fetchall()
        
        self.close()
        
        peak_hours = [stat[0] for stat in hourly_stats[:3]] if hourly_stats else []
        
        return {
            'peak_hours': peak_hours,
            'hourly_patterns': hourly_stats,
            'busiest_zones': zone_stats,
            'slot_type_preferences': type_stats,
            'recommendation': f"Peak demand expected at hours: {', '.join(map(str, peak_hours))}" if peak_hours else "Insufficient data for prediction"
        }
    
    def get_revenue_report(self) -> Dict:
        """Generate revenue report"""
        self.connect()
        
        # Total revenue
        self.cursor.execute('SELECT SUM(amount) FROM payments WHERE payment_status = "completed"')
        total_revenue = self.cursor.fetchone()[0] or 0
        
        # Revenue by date
        self.cursor.execute('''
            SELECT DATE(payment_date) as date, SUM(amount) as daily_revenue
            FROM payments
            WHERE payment_status = "completed"
            GROUP BY DATE(payment_date)
            ORDER BY date DESC
            LIMIT 7
        ''')
        daily_revenue = self.cursor.fetchall()
        
        # Revenue by slot type
        self.cursor.execute('''
            SELECT p.slot_type, SUM(pay.amount) as revenue
            FROM payments pay
            JOIN reservations r ON pay.reservation_id = r.reservation_id
            JOIN parking_slots p ON r.slot_id = p.slot_id
            WHERE pay.payment_status = "completed"
            GROUP BY p.slot_type
        ''')
        revenue_by_type = self.cursor.fetchall()
        
        self.close()
        
        return {
            'total_revenue': total_revenue,
            'daily_revenue': daily_revenue,
            'revenue_by_slot_type': revenue_by_type
        }


def main():
    """Comprehensive demo showcasing all three modules"""
    print("=" * 80)
    print(" " * 20 + "SMART PARKING MANAGEMENT SYSTEM")
    print(" " * 15 + "Complete System with 3 Integrated Modules")
    print("=" * 80)
    
    parking = SmartParkingSystem()
    
    print("\n" + "=" * 80)
    print("MODULE 1: DATABASE DESIGN & REAL-TIME SLOT UPDATES")
    print("=" * 80)
    
    print("\n1.1 Creating Parking Slots with Dynamic Pricing...")
    print("-" * 80)
    parking.add_parking_slot("A-101", 1, "Zone A", "regular", 5.00)
    parking.add_parking_slot("A-102", 1, "Zone A", "regular", 5.00)
    parking.add_parking_slot("A-103", 1, "Zone A", "handicap", 3.00)
    parking.add_parking_slot("A-104", 1, "Zone A", "regular", 5.00)
    parking.add_parking_slot("B-201", 2, "Zone B", "regular", 6.00)
    parking.add_parking_slot("B-202", 2, "Zone B", "vip", 10.00)
    parking.add_parking_slot("B-203", 2, "Zone B", "regular", 6.00)
    parking.add_parking_slot("C-301", 3, "Zone C", "regular", 7.00)
    parking.add_parking_slot("C-302", 3, "Zone C", "electric", 8.00)
    parking.add_parking_slot("C-303", 3, "Zone C", "regular", 7.00)
    
    print("\n1.2 Registering Users with Wallet...")
    print("-" * 80)
    parking.register_user("john_doe", "john@example.com", "1234567890", "ABC-1234", 100.00)
    parking.register_user("jane_smith", "jane@example.com", "0987654321", "XYZ-5678", 150.00)
    parking.register_user("bob_wilson", "bob@example.com", "5555555555", "DEF-9999", 75.00)
    
    print("\n" + "=" * 80)
    print("MODULE 2: QUERY OPTIMIZATION & SLOT SEARCH")
    print("=" * 80)
    
    print("\n2.1 Optimized Search - All Available Slots:")
    print("-" * 80)
    available = parking.search_available_slots_optimized()
    if available:
        print(f"{'ID':<5} {'Slot':<10} {'Floor':<7} {'Zone':<10} {'Type':<12} {'Price/hr':<10}")
        print("-" * 80)
        for slot in available:
            print(f"{slot[0]:<5} {slot[1]:<10} {slot[2]:<7} {slot[3] or 'N/A':<10} {slot[4]:<12} ${slot[6]:<9.2f}")
    
    print("\n2.2 Optimized Search - Zone A Only:")
    print("-" * 80)
    zone_a = parking.search_available_slots_optimized(zone="Zone A")
    for slot in zone_a:
        print(f"  Slot {slot[1]}: {slot[4]} - ${slot[6]:.2f}/hour")
    
    print("\n2.3 Optimized Search - Budget Slots (≤$6/hour):")
    print("-" * 80)
    budget = parking.search_available_slots_optimized(max_price=6.00)
    for slot in budget:
        print(f"  Slot {slot[1]}: Floor {slot[2]}, {slot[4]} - ${slot[6]:.2f}/hour")
    
    print("\n2.4 Availability Summary:")
    print("-" * 80)
    summary = parking.get_availability_summary()
    print(f"Total Slots: {summary['total_slots']}")
    print(f"Available: {summary['available_slots']}")
    print(f"Occupied: {summary['occupied_slots']}")
    print(f"Occupancy Rate: {summary['occupancy_rate']}%")
    print("\nBy Floor:")
    for floor in summary['by_floor']:
        print(f"  Floor {floor[0]}: {int(floor[2]) if floor[2] else 0}/{floor[1]} available (Avg: ${floor[3]:.2f}/hr)")
    print("\nBy Zone:")
    for zone in summary['by_zone']:
        print(f"  {zone[0]}: {int(zone[2]) if zone[2] else 0}/{zone[1]} available")
    
    print("\n" + "=" * 80)
    print("MODULE 3: RESERVATION WORKFLOW, PAYMENT & PREDICTIVE ANALYTICS")
    print("=" * 80)
    
    print("\n3.1 Creating Reservations with Integrated Payment...")
    print("-" * 80)
    res1 = parking.create_reservation_with_payment(1, 1, 2.0, "wallet")
    res2 = parking.create_reservation_with_payment(2, 5, 3.0, "wallet")
    res3 = parking.create_reservation_with_payment(3, 8, 1.5, "wallet")
    res4 = parking.create_reservation_with_payment(1, 2, 4.0, "wallet")
    
    print("\n3.2 Real-Time Availability After Reservations:")
    print("-" * 80)
    updated_summary = parking.get_availability_summary()
    print(f"Available Slots: {updated_summary['available_slots']}/{updated_summary['total_slots']}")
    print(f"Current Occupancy Rate: {updated_summary['occupancy_rate']}%")
    
    print("\n3.3 Revenue Report:")
    print("-" * 80)
    revenue = parking.get_revenue_report()
    print(f"Total Revenue: ${revenue['total_revenue']:.2f}")
    print("\nRevenue by Slot Type:")
    for rev in revenue['revenue_by_slot_type']:
        print(f"  {rev[0]}: ${rev[1]:.2f}")
    
    print("\n3.4 Predictive Analytics - Peak Demand Prediction:")
    print("-" * 80)
    predictions = parking.predict_peak_demand()
    print(f"Peak Hours: {predictions['peak_hours']}")
    print(f"Recommendation: {predictions['recommendation']}")
    if predictions['busiest_zones']:
        print("\nBusiest Zones:")
        for zone in predictions['busiest_zones']:
            print(f"  {zone[0]}: {zone[1]} reservations, ${zone[2]:.2f} revenue")
    if predictions['slot_type_preferences']:
        print("\nSlot Type Preferences:")
        for pref in predictions['slot_type_preferences']:
            print(f"  {pref[0]}: {pref[1]} reservations")
    
    print("\n3.5 Ending a Reservation...")
    print("-" * 80)
    if res1:
        parking.end_reservation(res1)
    
    print("\n" + "=" * 80)
    print(" " * 25 + "SYSTEM DEMO COMPLETED!")
    print(" " * 15 + "All 3 Modules Successfully Demonstrated")
    print("=" * 80)
    print("\nModule Summary:")
    print("  ✓ Module 1: Database with optimized schema and real-time updates")
    print("  ✓ Module 2: Indexed queries for fast slot search and retrieval")
    print("  ✓ Module 3: Reservation workflow, payment processing, and analytics")
    print("=" * 80)


if __name__ == "__main__":
    main()
