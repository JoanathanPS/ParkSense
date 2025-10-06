import sqlite3
from datetime import datetime
from typing import List, Optional, Tuple

class SmartParkingSystem:
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
        """Create database tables for parking slots, users, and reservations"""
        self.connect()
        
        # Create parking_slots table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS parking_slots (
                slot_id INTEGER PRIMARY KEY AUTOINCREMENT,
                slot_number VARCHAR(10) UNIQUE NOT NULL,
                floor_number INTEGER NOT NULL,
                zone VARCHAR(50),
                slot_type VARCHAR(20) DEFAULT 'regular',
                is_available BOOLEAN DEFAULT 1,
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
                status VARCHAR(20) DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (slot_id) REFERENCES parking_slots(slot_id)
            )
        ''')
        
        self.conn.commit()
        self.close()
        print("Database initialized successfully!")
    
    # ===== PARKING SLOT OPERATIONS =====
    
    def add_parking_slot(self, slot_number: str, floor_number: int, 
                        zone: str = None, slot_type: str = 'regular') -> bool:
        """Add a new parking slot"""
        try:
            self.connect()
            self.cursor.execute('''
                INSERT INTO parking_slots (slot_number, floor_number, zone, slot_type)
                VALUES (?, ?, ?, ?)
            ''', (slot_number, floor_number, zone, slot_type))
            self.conn.commit()
            self.close()
            print(f"Parking slot {slot_number} added successfully!")
            return True
        except sqlite3.IntegrityError:
            print(f"Error: Slot {slot_number} already exists!")
            self.close()
            return False
    
    def get_all_slots(self) -> List[Tuple]:
        """Get all parking slots"""
        self.connect()
        self.cursor.execute('SELECT * FROM parking_slots')
        slots = self.cursor.fetchall()
        self.close()
        return slots
    
    def update_slot_availability(self, slot_id: int, is_available: bool) -> bool:
        """Update parking slot availability"""
        self.connect()
        self.cursor.execute('''
            UPDATE parking_slots 
            SET is_available = ? 
            WHERE slot_id = ?
        ''', (is_available, slot_id))
        self.conn.commit()
        affected = self.cursor.rowcount
        self.close()
        return affected > 0
    
    # ===== USER OPERATIONS =====
    
    def register_user(self, username: str, email: str, 
                     phone: str = None, vehicle_number: str = None) -> bool:
        """Register a new user"""
        try:
            self.connect()
            self.cursor.execute('''
                INSERT INTO users (username, email, phone, vehicle_number)
                VALUES (?, ?, ?, ?)
            ''', (username, email, phone, vehicle_number))
            self.conn.commit()
            self.close()
            print(f"User {username} registered successfully!")
            return True
        except sqlite3.IntegrityError:
            print(f"Error: User {username} or email {email} already exists!")
            self.close()
            return False
    
    def get_user(self, user_id: int) -> Optional[Tuple]:
        """Get user by ID"""
        self.connect()
        self.cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user = self.cursor.fetchone()
        self.close()
        return user
    
    def get_all_users(self) -> List[Tuple]:
        """Get all users"""
        self.connect()
        self.cursor.execute('SELECT * FROM users')
        users = self.cursor.fetchall()
        self.close()
        return users
    
    # ===== RESERVATION OPERATIONS =====
    
    def create_reservation(self, user_id: int, slot_id: int, 
                          start_time: str, end_time: str = None) -> bool:
        """Create a new reservation"""
        try:
            self.connect()
            
            # Check if slot is available
            self.cursor.execute('''
                SELECT is_available FROM parking_slots WHERE slot_id = ?
            ''', (slot_id,))
            result = self.cursor.fetchone()
            
            if not result or not result[0]:
                print("Error: Parking slot is not available!")
                self.close()
                return False
            
            # Create reservation
            self.cursor.execute('''
                INSERT INTO reservations (user_id, slot_id, start_time, end_time)
                VALUES (?, ?, ?, ?)
            ''', (user_id, slot_id, start_time, end_time))
            
            # Mark slot as unavailable
            self.cursor.execute('''
                UPDATE parking_slots SET is_available = 0 WHERE slot_id = ?
            ''', (slot_id,))
            
            self.conn.commit()
            self.close()
            print(f"Reservation created successfully for slot ID {slot_id}!")
            return True
        except Exception as e:
            print(f"Error creating reservation: {e}")
            self.close()
            return False
    
    def end_reservation(self, reservation_id: int) -> bool:
        """End a reservation and free up the slot"""
        try:
            self.connect()
            
            # Get slot_id from reservation
            self.cursor.execute('''
                SELECT slot_id FROM reservations WHERE reservation_id = ?
            ''', (reservation_id,))
            result = self.cursor.fetchone()
            
            if not result:
                print("Error: Reservation not found!")
                self.close()
                return False
            
            slot_id = result[0]
            
            # Update reservation status
            self.cursor.execute('''
                UPDATE reservations 
                SET status = 'completed', end_time = ?
                WHERE reservation_id = ?
            ''', (datetime.now().isoformat(), reservation_id))
            
            # Mark slot as available
            self.cursor.execute('''
                UPDATE parking_slots SET is_available = 1 WHERE slot_id = ?
            ''', (slot_id,))
            
            self.conn.commit()
            self.close()
            print(f"Reservation {reservation_id} ended successfully!")
            return True
        except Exception as e:
            print(f"Error ending reservation: {e}")
            self.close()
            return False
    
    def get_user_reservations(self, user_id: int) -> List[Tuple]:
        """Get all reservations for a user"""
        self.connect()
        self.cursor.execute('''
            SELECT r.*, p.slot_number, p.floor_number, p.zone
            FROM reservations r
            JOIN parking_slots p ON r.slot_id = p.slot_id
            WHERE r.user_id = ?
            ORDER BY r.created_at DESC
        ''', (user_id,))
        reservations = self.cursor.fetchall()
        self.close()
        return reservations
    
    # ===== REAL-TIME AVAILABILITY =====
    
    def get_available_slots(self, floor_number: int = None, 
                           zone: str = None, slot_type: str = None) -> List[Tuple]:
        """Fetch real-time available parking slots with optional filters"""
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
        
        query += ' ORDER BY floor_number, slot_number'
        
        self.cursor.execute(query, params)
        available_slots = self.cursor.fetchall()
        self.close()
        return available_slots
    
    def get_availability_summary(self) -> dict:
        """Get summary of parking availability"""
        self.connect()
        
        # Total slots
        self.cursor.execute('SELECT COUNT(*) FROM parking_slots')
        total = self.cursor.fetchone()[0]
        
        # Available slots
        self.cursor.execute('SELECT COUNT(*) FROM parking_slots WHERE is_available = 1')
        available = self.cursor.fetchone()[0]
        
        # Occupied slots
        occupied = total - available
        
        # By floor
        self.cursor.execute('''
            SELECT floor_number, 
                   COUNT(*) as total,
                   SUM(CASE WHEN is_available = 1 THEN 1 ELSE 0 END) as available
            FROM parking_slots
            GROUP BY floor_number
            ORDER BY floor_number
        ''')
        by_floor = self.cursor.fetchall()
        
        self.close()
        
        return {
            'total_slots': total,
            'available_slots': available,
            'occupied_slots': occupied,
            'occupancy_rate': round((occupied / total * 100) if total > 0 else 0, 2),
            'by_floor': by_floor
        }


def main():
    """Demo/Test interface for the Smart Parking System"""
    print("=" * 60)
    print("SMART PARKING MANAGEMENT SYSTEM - MODULE 1")
    print("=" * 60)
    
    # Initialize system
    parking = SmartParkingSystem()
    
    print("\n1. CREATING PARKING SLOTS...")
    print("-" * 60)
    # Add parking slots
    parking.add_parking_slot("A-101", 1, "Zone A", "regular")
    parking.add_parking_slot("A-102", 1, "Zone A", "regular")
    parking.add_parking_slot("A-103", 1, "Zone A", "handicap")
    parking.add_parking_slot("B-201", 2, "Zone B", "regular")
    parking.add_parking_slot("B-202", 2, "Zone B", "vip")
    parking.add_parking_slot("C-301", 3, "Zone C", "regular")
    
    print("\n2. REGISTERING USERS...")
    print("-" * 60)
    # Register users
    parking.register_user("john_doe", "john@example.com", "1234567890", "ABC-1234")
    parking.register_user("jane_smith", "jane@example.com", "0987654321", "XYZ-5678")
    
    print("\n3. CREATING RESERVATIONS...")
    print("-" * 60)
    # Create reservations
    parking.create_reservation(1, 1, datetime.now().isoformat())
    parking.create_reservation(2, 4, datetime.now().isoformat())
    
    print("\n4. REAL-TIME AVAILABLE PARKING SLOTS:")
    print("-" * 60)
    available = parking.get_available_slots()
    if available:
        print(f"{'ID':<5} {'Slot Number':<12} {'Floor':<7} {'Zone':<12} {'Type':<12} {'Available':<10}")
        print("-" * 60)
        for slot in available:
            print(f"{slot[0]:<5} {slot[1]:<12} {slot[2]:<7} {slot[3] or 'N/A':<12} {slot[4]:<12} {'Yes' if slot[5] else 'No':<10}")
    else:
        print("No available slots!")
    
    print("\n5. AVAILABLE SLOTS ON FLOOR 1:")
    print("-" * 60)
    floor1_slots = parking.get_available_slots(floor_number=1)
    if floor1_slots:
        for slot in floor1_slots:
            print(f"Slot: {slot[1]}, Zone: {slot[3]}, Type: {slot[4]}")
    else:
        print("No available slots on Floor 1!")
    
    print("\n6. PARKING AVAILABILITY SUMMARY:")
    print("-" * 60)
    summary = parking.get_availability_summary()
    print(f"Total Slots: {summary['total_slots']}")
    print(f"Available Slots: {summary['available_slots']}")
    print(f"Occupied Slots: {summary['occupied_slots']}")
    print(f"Occupancy Rate: {summary['occupancy_rate']}%")
    print("\nBy Floor:")
    for floor in summary['by_floor']:
        print(f"  Floor {floor[0]}: {floor[2]}/{floor[1]} available")
    
    print("\n7. USER RESERVATIONS (User ID: 1):")
    print("-" * 60)
    reservations = parking.get_user_reservations(1)
    if reservations:
        for res in reservations:
            print(f"Reservation ID: {res[0]}, Slot: {res[7]}, Floor: {res[8]}, Status: {res[5]}")
    else:
        print("No reservations found!")
    
    print("\n" + "=" * 60)
    print("DEMO COMPLETED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    main()
