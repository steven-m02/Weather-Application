import sqlite3

# Path to SQLite database file for alerts
DATABASE = 'weather_net.db'

# Connect to the SQLite database
def connect_db():
    conn = sqlite3.connect(DATABASE)
    return conn

# Create alerts table if it doesn't exist
def create_alerts_table():
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS alerts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        city TEXT NOT NULL,
                        alert_description TEXT NOT NULL,
                        username TEXT NOT NULL,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                      )''')

    conn.commit()
    conn.close()

# Add a weather alert to the database
def add_weather_alert(city, description, username):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO alerts (city, alert_description, username)
        VALUES (?, ?, ?)
    ''', (city, description, username))

    conn.commit()
    conn.close()

# Retrieve all weather alerts from the database
def get_weather_alerts():
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT city, alert_description, username, timestamp 
        FROM alerts
        ORDER BY timestamp DESC
    ''')
    alerts = cursor.fetchall()
    conn.close()

    return alerts

# Retrieve unsent alerts (if needed for future functionality like real-time updates)
def get_unsent_alerts():
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT city, alert_description, username, timestamp 
        FROM alerts
    ''')
    alerts = cursor.fetchall()
    conn.close()

    return alerts
