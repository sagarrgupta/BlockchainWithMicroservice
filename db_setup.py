# db_setup.py
import sqlite3
import os

def setup_database():
    """
    Create SQLite database with disaster management resource allocation data
    """
    # Ensure /data directory exists
    os.makedirs('/data', exist_ok=True)
    # Create database file
    db_path = '/data/disaster_resources.db'
    
    # Remove existing database if it exists
    if os.path.exists(db_path):
        os.remove(db_path)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create table for disaster resource allocation
    cursor.execute('''
        CREATE TABLE disaster_resources (
            city_id INTEGER PRIMARY KEY,
            city_name TEXT NOT NULL,
            resource_type TEXT NOT NULL,
            resources_allocated INTEGER NOT NULL,
            allocation_date TEXT NOT NULL,
            disaster_risk_level TEXT NOT NULL
        )
    ''')
    
    # Insert sample data - 10 cities with disaster management resources
    sample_data = [
        (1, 'New York', 'Emergency Vehicles', 300, '2024-01-15', 'High'),
        (2, 'Los Angeles', 'Medical Supplies', 200, '2024-01-20', 'Medium'),
        (3, 'Chicago', 'Food Packages', 200, '2024-02-01', 'Medium'),
        (4, 'Houston', 'Water Purification Units', 100, '2024-02-10', 'Low'),
        (5, 'Miami', 'Evacuation Buses', 400, '2024-01-25', 'Very High'),
        (6, 'San Francisco', 'Emergency Shelters', 300, '2024-02-05', 'High'),
        (7, 'Seattle', 'Communication Equipment', 200, '2024-01-30', 'Medium'),
        (8, 'Denver', 'Rescue Helicopters', 200, '2024-02-15', 'Medium'),
        (9, 'Phoenix', 'Fire Trucks', 300, '2024-01-18', 'High'),
        (10, 'Boston', 'Emergency Personnel', 200, '2024-02-08', 'Medium')
    ]
    
    cursor.executemany('''
        INSERT INTO disaster_resources 
        (city_id, city_name, resource_type, resources_allocated, allocation_date, disaster_risk_level)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', sample_data)
    
    conn.commit()
    conn.close()
    
    print(f"Database '{db_path}' created successfully with 10 sample records")
    print("Sample data includes disaster management resources for major cities")

if __name__ == '__main__':
    setup_database()