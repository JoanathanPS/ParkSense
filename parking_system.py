import sqlite3
from datetime import datetime, timedelta
from typing import List, Optional, Tuple, Dict
import random
import os

from werkzeug.security import generate_password_hash

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
        self.seed_initial_data()
    
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
        
        # Create users table with login credentials and display name support
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username VARCHAR(100) UNIQUE NOT NULL,
                full_name VARCHAR(150) NOT NULL DEFAULT '',
                email VARCHAR(100) UNIQUE NOT NULL,
                phone VARCHAR(20),
                vehicle_number VARCHAR(20),
                wallet_balance DECIMAL(10,2) DEFAULT 0.00,
                password_hash VARCHAR(255) DEFAULT '',
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

        # Track wallet transactions such as top-ups for admin visibility
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS wallet_transactions (
                transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount DECIMAL(10,2) NOT NULL,
                transaction_type VARCHAR(20) NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
        
        # Ensure new columns exist when upgrading an old database
        self.cursor.execute('PRAGMA table_info(users)')
        user_columns = {column[1] for column in self.cursor.fetchall()}
        if 'full_name' not in user_columns:
            self.cursor.execute("ALTER TABLE users ADD COLUMN full_name VARCHAR(150) NOT NULL DEFAULT ''")
        if 'password_hash' not in user_columns:
            self.cursor.execute("ALTER TABLE users ADD COLUMN password_hash VARCHAR(255) NOT NULL DEFAULT ''")

        self.conn.commit()
        self.close()
        print("✓ Database initialized with optimized schema and indexes!")

    def seed_initial_data(self):
        """Populate the database with realistic parking slots and sample data"""
        self.connect()

        # Seed parking slots only if the count is low to avoid duplicates on restart
        self.cursor.execute('SELECT COUNT(*) FROM parking_slots')
        slot_count = self.cursor.fetchone()[0] or 0
        if slot_count < 1000:
            floors = range(1, 11)
            zones = ['A', 'B', 'C', 'D']
            slot_types = ['regular', 'electric', 'handicap', 'premium']
            for floor in floors:
                for zone in zones:
                    for number in range(1, 26):
                        slot_type = random.choice(slot_types)
                        base_price = 35 + (floor * 4)
                        price = base_price + (20 if slot_type == 'premium' else 0)
                        price -= 8 if slot_type == 'handicap' else 0
                        price += 10 if slot_type == 'electric' else 0
                        slot_number = f"{zone}{floor:02d}-{number:03d}"
                        self.cursor.execute('''
                            INSERT OR IGNORE INTO parking_slots (slot_number, floor_number, zone, slot_type, price_per_hour)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (slot_number, floor, f"Zone {zone}", slot_type, float(price)))

        # Ensure a default user exists so the demo has login credentials
        self.cursor.execute('SELECT COUNT(*) FROM users')
        user_count = self.cursor.fetchone()[0] or 0
        if user_count == 0:
            password_hash = generate_password_hash('user')
            self.cursor.execute('''
                INSERT OR IGNORE INTO users (username, full_name, email, phone, vehicle_number, wallet_balance, password_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                'user',
                'Primary Driver',
                'user@example.com',
                '9999999999',
                'KA01XX0001',
                0.0,
                password_hash
            ))

        self.conn.commit()
        self.close()
    
    # ===== MODULE 1: PARKING SLOT OPERATIONS =====
    
    def add_parking_slot(self, slot_number: str, floor_number: int, 
                        zone: str = None, slot_type: str = 'regular', 
                        price_per_hour: float = 50.00) -> bool:
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
    
    def register_user(self, login_id: str, full_name: str, email: str,
                     phone: str = None, vehicle_number: str = None,
                     password_hash: str = '', initial_balance: float = 0.00) -> Optional[int]:
        """Register a new user with wallet and login credentials"""
        try:
            self.connect()
            self.cursor.execute('''
                INSERT INTO users (username, full_name, email, phone, vehicle_number, wallet_balance, password_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (login_id, full_name, email, phone, vehicle_number, initial_balance, password_hash))
            self.conn.commit()
            user_id = self.cursor.lastrowid
            self.close()
            print(f"✓ User {full_name} ({login_id}) registered successfully!")
            return user_id
        except sqlite3.IntegrityError:
            print(f"✗ Error: Login {login_id} or email {email} already exists!")
            self.close()
            return None

    def get_user_credentials(self, login_id: str) -> Optional[Dict]:
        """Return login credentials for authentication"""
        self.connect()
        self.cursor.execute('''
            SELECT user_id, username, full_name, password_hash
            FROM users
            WHERE username = ?
        ''', (login_id,))
        row = self.cursor.fetchone()
        self.close()
        if not row or not row[3]:
            return None
        return {
            'user_id': row[0],
            'login_id': row[1],
            'full_name': row[2],
            'password_hash': row[3]
        }

    def delete_user(self, user_id: int) -> bool:
        """Delete a user and associated transactional data"""
        try:
            self.connect()
            self.conn.execute('BEGIN')

            # Release any active reservations for the user
            self.cursor.execute('''
                SELECT reservation_id, slot_id
                FROM reservations
                WHERE user_id = ? AND status = 'active'
            ''', (user_id,))
            for reservation_id, slot_id in self.cursor.fetchall():
                self.cursor.execute('UPDATE reservations SET status = "cancelled", end_time = ? WHERE reservation_id = ?',
                                    (datetime.now().isoformat(), reservation_id))
                self.cursor.execute('UPDATE parking_slots SET is_available = 1 WHERE slot_id = ?', (slot_id,))

            # Remove related records
            self.cursor.execute('DELETE FROM payments WHERE user_id = ?', (user_id,))
            self.cursor.execute('DELETE FROM wallet_transactions WHERE user_id = ?', (user_id,))
            self.cursor.execute('DELETE FROM reservations WHERE user_id = ?', (user_id,))
            self.cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))

            if self.cursor.rowcount == 0:
                self.conn.rollback()
                self.close()
                return False

            self.conn.commit()
            self.close()
            print(f"✓ User {user_id} deleted along with related records")
            return True
        except Exception as exc:
            print(f"✗ Error deleting user {user_id}: {exc}")
            if self.conn:
                self.conn.rollback()
            self.close()
            return False

    def clear_transactional_data(self) -> None:
        """Remove reservations, payments, and wallet transactions while keeping slots and users"""
        try:
            self.connect()
            self.conn.execute('BEGIN')
            self.cursor.execute('DELETE FROM payments')
            self.cursor.execute('DELETE FROM wallet_transactions')
            self.cursor.execute('DELETE FROM utilization_stats')
            self.cursor.execute('UPDATE parking_slots SET is_available = 1')
            self.cursor.execute('DELETE FROM reservations')
            self.conn.commit()
            print("✓ Transactional data cleared")
        except Exception as exc:
            print(f"✗ Error clearing transactional data: {exc}")
            if self.conn:
                self.conn.rollback()
        finally:
            self.close()

    def get_database_overview(self, limit: int = 10) -> Dict[str, Dict]:
        """Return a snapshot of database tables for the admin dashboard"""
        self.connect()
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = [row[0] for row in self.cursor.fetchall()]
        overview: Dict[str, Dict] = {}

        for table in tables:
            self.cursor.execute(f'PRAGMA table_info({table})')
            columns = [col[1] for col in self.cursor.fetchall()]
            self.cursor.execute(f'SELECT COUNT(*) FROM {table}')
            total_count = self.cursor.fetchone()[0] or 0
            self.cursor.execute(f'SELECT * FROM {table} ORDER BY ROWID DESC LIMIT ?', (limit,))
            rows = self.cursor.fetchall()
            overview[table] = {
                'columns': columns,
                'rows': rows,
                'count': total_count
            }

        self.close()
        return overview

    def add_wallet_balance(self, user_id: int, amount: float) -> bool:
        """Add balance to user wallet and record the transaction"""
        if amount <= 0:
            return False

        self.connect()
        self.cursor.execute('''
            UPDATE users
            SET wallet_balance = wallet_balance + ?
            WHERE user_id = ?
        ''', (amount, user_id))
        affected = self.cursor.rowcount

        if affected > 0:
            self.cursor.execute('''
                INSERT INTO wallet_transactions (user_id, amount, transaction_type, description)
                VALUES (?, ?, 'top_up', 'Manual balance addition')
            ''', (user_id, amount))

        self.conn.commit()
        self.close()

        if affected > 0:
            print(f"✓ Added ₹{amount:.2f} to user {user_id} wallet")
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
        # Release expired reservations before computing availability
        self.release_expired_reservations()

        self.connect()

        # Total and available slots
        self.cursor.execute('SELECT COUNT(*), SUM(CASE WHEN is_available = 1 THEN 1 ELSE 0 END) FROM parking_slots')
        total, available = self.cursor.fetchone()
        total = total or 0
        available = available or 0
        occupied = total - available if total else 0

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
        by_floor_rows = self.cursor.fetchall()

        # By zone
        self.cursor.execute('''
            SELECT zone,
                   COUNT(*) as total,
                   SUM(CASE WHEN is_available = 1 THEN 1 ELSE 0 END) as available
            FROM parking_slots
            WHERE zone IS NOT NULL
            GROUP BY zone
            ORDER BY zone
        ''')
        by_zone_rows = self.cursor.fetchall()

        self.close()

        by_floor = []
        for floor in by_floor_rows:
            total_floor = floor[1] or 0
            available_floor = floor[2] or 0
            occupied_floor = total_floor - available_floor
            rate = round((occupied_floor / total_floor * 100) if total_floor else 0, 2)
            by_floor.append({
                'floor': floor[0],
                'total': total_floor,
                'available': available_floor,
                'occupied': occupied_floor,
                'avg_price': float(floor[3] or 0),
                'occupancy_rate': rate
            })

        by_zone = []
        for zone in by_zone_rows:
            total_zone = zone[1] or 0
            available_zone = zone[2] or 0
            occupied_zone = total_zone - available_zone
            rate = round((occupied_zone / total_zone * 100) if total_zone else 0, 2)
            by_zone.append({
                'zone': zone[0],
                'total': total_zone,
                'available': available_zone,
                'occupied': occupied_zone,
                'occupancy_rate': rate
            })

        return {
            'total_slots': total,
            'available_slots': available,
            'occupied_slots': occupied,
            'occupancy_rate': round((occupied / total * 100) if total else 0, 2),
            'by_floor': by_floor,
            'by_zone': by_zone
        }
    
    # ===== MODULE 3: RESERVATION WORKFLOW =====
    
    def create_reservation_with_payment(self, user_id: int, slot_id: int,
                                       duration_hours: float,
                                       payment_method: str = 'wallet') -> Tuple[Optional[int], str]:
        """Create reservation with integrated payment workflow and proper transaction handling

        Returns a tuple of (reservation_id, message)
        """
        if duration_hours is None:
            return None, "Reservation duration is required."

        if duration_hours < 1 or duration_hours > 4:
            return None, "Reservation duration must be between 1 and 4 hours."

        self.connect()
        try:
            # Begin transaction
            self.conn.execute('BEGIN')

            # Ensure user does not have another active reservation
            self.cursor.execute('''
                SELECT reservation_id FROM reservations
                WHERE user_id = ? AND status = 'active'
            ''', (user_id,))
            if self.cursor.fetchone():
                self.conn.rollback()
                self.close()
                return None, "You already have an active reservation."

            # Ensure the user has not already booked a reservation today
            self.cursor.execute('''
                SELECT reservation_id FROM reservations
                WHERE user_id = ?
                  AND DATE(start_time) = DATE('now', 'localtime')
            ''', (user_id,))
            if self.cursor.fetchone():
                self.conn.rollback()
                self.close()
                return None, "You have already made a reservation today."

            # Check slot availability
            self.cursor.execute('SELECT is_available, price_per_hour FROM parking_slots WHERE slot_id = ?', (slot_id,))
            result = self.cursor.fetchone()

            if not result or not result[0]:
                print("✗ Error: Parking slot is not available!")
                self.conn.rollback()
                self.close()
                return None, "Parking slot is not available."
            
            price_per_hour = result[1]
            total_amount = price_per_hour * duration_hours
            
            # Check user wallet balance
            self.cursor.execute('SELECT wallet_balance FROM users WHERE user_id = ?', (user_id,))
            balance = self.cursor.fetchone()
            
            if not balance or balance[0] < total_amount:
                print(f"✗ Error: Insufficient wallet balance! Need ₹{total_amount:.2f}, have ₹{balance[0] if balance else 0:.2f}")
                self.conn.rollback()
                self.close()
                return None, "Insufficient wallet balance."
            
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
                return None, "Payment failed due to concurrent balance change."

            # Record wallet debit
            self.cursor.execute('''
                INSERT INTO wallet_transactions (user_id, amount, transaction_type, description)
                VALUES (?, ?, 'debit', 'Reservation payment')
            ''', (user_id, -total_amount))
            
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
            print(f"✓ Reservation {reservation_id} created! Amount: ₹{total_amount:.2f}, Duration: {duration_hours}h")
            print(f"✓ Payment processed: {transaction_id}")
            return reservation_id, "Reservation created successfully."
        except Exception as e:
            print(f"✗ Error creating reservation: {e}")
            if self.conn:
                self.conn.rollback()
            self.close()
            return None, "An unexpected error occurred while creating the reservation."
    
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

    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Return user information as a dictionary"""
        self.connect()
        self.cursor.execute('''
            SELECT user_id, username, full_name, email, phone, vehicle_number, wallet_balance, created_at
            FROM users WHERE user_id = ?
        ''', (user_id,))
        row = self.cursor.fetchone()
        self.close()
        if not row:
            return None
        return {
            'user_id': row[0],
            'login_id': row[1],
            'full_name': row[2],
            'email': row[3],
            'phone': row[4],
            'vehicle_number': row[5],
            'wallet_balance': float(row[6] or 0),
            'created_at': row[7]
        }

    def get_user_reservations(self, user_id: int, active_only: bool = False) -> List[Dict]:
        """Fetch reservations for a specific user"""
        self.connect()
        query = '''
            SELECT r.reservation_id, p.slot_number, r.start_time, r.duration_hours, r.status, r.end_time, r.total_amount
            FROM reservations r
            JOIN parking_slots p ON r.slot_id = p.slot_id
            WHERE r.user_id = ?
        '''
        params = [user_id]
        if active_only:
            query += " AND r.status = 'active'"
        query += ' ORDER BY r.start_time DESC'
        self.cursor.execute(query, params)
        rows = self.cursor.fetchall()
        self.close()

        reservations = []
        for row in rows:
            reservations.append({
                'reservation_id': row[0],
                'slot_number': row[1],
                'start_time': row[2],
                'duration_hours': float(row[3] or 0),
                'status': row[4],
                'end_time': row[5],
                'total_amount': float(row[6] or 0)
            })
        return reservations

    def get_active_reservations(self) -> List[Dict]:
        """Return a list of active reservations with user and slot details"""
        self.connect()
        self.cursor.execute('''
            SELECT r.reservation_id, u.full_name, p.slot_number, r.start_time, r.end_time, r.total_amount
            FROM reservations r
            JOIN users u ON r.user_id = u.user_id
            JOIN parking_slots p ON r.slot_id = p.slot_id
            WHERE r.status = 'active'
        ''')
        rows = self.cursor.fetchall()
        self.close()
        active = []
        for row in rows:
            active.append({
                'reservation_id': row[0],
                'full_name': row[1],
                'slot_number': row[2],
                'start_time': row[3],
                'end_time': row[4],
                'total_amount': float(row[5] or 0)
            })
        return active

    def get_reservation_details(self, reservation_id: int) -> Optional[Dict]:
        """Return reservation details for countdown timers"""
        self.connect()
        self.cursor.execute('''
            SELECT r.reservation_id, r.user_id, u.full_name, p.slot_number, r.start_time, r.end_time, r.total_amount, r.status
            FROM reservations r
            JOIN users u ON r.user_id = u.user_id
            JOIN parking_slots p ON r.slot_id = p.slot_id
            WHERE r.reservation_id = ?
        ''', (reservation_id,))
        row = self.cursor.fetchone()
        self.close()
        if not row:
            return None
        return {
            'reservation_id': row[0],
            'user_id': row[1],
            'full_name': row[2],
            'slot_number': row[3],
            'start_time': row[4],
            'end_time': row[5],
            'total_amount': float(row[6] or 0),
            'status': row[7]
        }

    def list_users(self) -> List[Dict]:
        """Return all users with wallet balance"""
        self.connect()
        self.cursor.execute('''
            SELECT user_id, username, full_name, email, phone, vehicle_number, wallet_balance, created_at
            FROM users
            ORDER BY created_at DESC
        ''')
        rows = self.cursor.fetchall()
        self.close()
        users = []
        for row in rows:
            users.append({
                'user_id': row[0],
                'login_id': row[1],
                'full_name': row[2],
                'email': row[3],
                'phone': row[4],
                'vehicle_number': row[5],
                'wallet_balance': float(row[6] or 0),
                'created_at': row[7]
            })
        return users

    def release_expired_reservations(self) -> int:
        """Mark reservations whose end time has passed as completed and free the slot"""
        self.connect()
        now = datetime.now().isoformat()
        self.cursor.execute('''
            SELECT reservation_id, slot_id FROM reservations
            WHERE status = 'active' AND end_time <= ?
        ''', (now,))
        expired = self.cursor.fetchall()

        released = 0
        for reservation_id, slot_id in expired:
            self.cursor.execute('''
                UPDATE reservations
                SET status = 'completed', end_time = ?
                WHERE reservation_id = ?
            ''', (now, reservation_id))
            self.cursor.execute('UPDATE parking_slots SET is_available = 1 WHERE slot_id = ?', (slot_id,))
            released += 1

        if released:
            self.conn.commit()
        self.close()
        return released

    def get_occupancy_by_floor(self) -> List[Dict]:
        """Return occupancy rate per floor"""
        self.connect()
        self.cursor.execute('''
            SELECT floor_number,
                   COUNT(*) AS total,
                   SUM(CASE WHEN is_available = 0 THEN 1 ELSE 0 END) AS occupied
            FROM parking_slots
            GROUP BY floor_number
            ORDER BY floor_number
        ''')
        rows = self.cursor.fetchall()
        self.close()
        floors = []
        for row in rows:
            total = row[1] or 0
            occupied = row[2] or 0
            rate = round((occupied / total * 100) if total else 0, 2)
            floors.append({
                'floor': row[0],
                'total': total,
                'occupied': occupied,
                'occupancy_rate': rate
            })
        return floors

    def get_occupancy_by_zone(self) -> List[Dict]:
        """Return occupancy rate per zone"""
        self.connect()
        self.cursor.execute('''
            SELECT zone,
                   COUNT(*) AS total,
                   SUM(CASE WHEN is_available = 0 THEN 1 ELSE 0 END) AS occupied
            FROM parking_slots
            WHERE zone IS NOT NULL
            GROUP BY zone
            ORDER BY zone
        ''')
        rows = self.cursor.fetchall()
        self.close()
        zones = []
        for row in rows:
            total = row[1] or 0
            occupied = row[2] or 0
            rate = round((occupied / total * 100) if total else 0, 2)
            zones.append({
                'zone': row[0],
                'total': total,
                'occupied': occupied,
                'occupancy_rate': rate
            })
        return zones

    def get_wallet_transactions(self, limit: int = 10) -> List[Dict]:
        """Return latest wallet transactions"""
        self.connect()
        self.cursor.execute('''
            SELECT wt.transaction_id, wt.user_id, u.full_name, wt.amount, wt.transaction_type, wt.created_at
            FROM wallet_transactions wt
            JOIN users u ON wt.user_id = u.user_id
            ORDER BY wt.created_at DESC
            LIMIT ?
        ''', (limit,))
        rows = self.cursor.fetchall()
        self.close()
        transactions = []
        for row in rows:
            transactions.append({
                'transaction_id': row[0],
                'user_id': row[1],
                'full_name': row[2],
                'amount': float(row[3] or 0),
                'transaction_type': row[4],
                'created_at': row[5]
            })
        return transactions
    
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


if __name__ == "__main__":
    # Allow running this module directly to perform a quick health check
    system = SmartParkingSystem()
    summary = system.get_availability_summary()
    print("Parking system initialized. Total slots:", summary['total_slots'])
