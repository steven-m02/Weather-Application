import sqlite3
from passlib.hash import pbkdf2_sha256
import logging

# Path to SQLite database file
DATABASE = 'weather_net.db'

# Connect to the SQLite database
def connect_db():
    conn = sqlite3.connect(DATABASE)
    return conn

# Create tables if they don't exist
def create_tables():
    conn = connect_db()
    cursor = conn.cursor()

    # Create users table with username and hashed password
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT NOT NULL UNIQUE,
                        password TEXT NOT NULL
                      )''')
    
    # Create weather data table for storing forecast (with city, date, temperature, and condition)
    cursor.execute('''CREATE TABLE IF NOT EXISTS weather_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        city TEXT NOT NULL,
                        date TEXT NOT NULL,
                        temperature INTEGER NOT NULL,
                        condition TEXT NOT NULL,
                        UNIQUE(city, date, condition)  -- Ensuring no duplicates for city, date, and condition
                      )''')
    
     # Create files table for storing uploaded file metadata
    cursor.execute('''CREATE TABLE IF NOT EXISTS files (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        filename TEXT NOT NULL,
                        uploader TEXT NOT NULL,
                        upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                      )''')
    
    conn.commit()
    conn.close()

# Register a new user
def register_user(username, password):
    if not username or not password:
        print("Username and password cannot be empty.")
        return False

    conn = connect_db()
    cursor = conn.cursor()
    try:
        # Use pbkdf2_sha256 for hashing the password
        hashed_password = pbkdf2_sha256.hash(password)

        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        print("Username already taken!")
        return False
    except Exception as e:
        print(f"An error occurred: {e}")
        return False
    finally:
        conn.close()

# Verify user login
def verify_login(username, password):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("SELECT password FROM users WHERE username=?", (username,))
    user = cursor.fetchone()
    conn.close()

    if user and pbkdf2_sha256.verify(password, user[0]):  # Verify with pbkdf2_sha256
        return True
    return False

# Store weather data for 7-day forecast into the database
def store_weather_data(city, forecast_data):
    conn = connect_db()
    cursor = conn.cursor()

    for date, temperature, condition in forecast_data:
        # Check if the weather data already exists for the specific city and date
        cursor.execute('''
            SELECT COUNT(*) FROM weather_data
            WHERE city = ? AND date = ? AND condition = ?
        ''', (city, date, condition))
        
        if cursor.fetchone()[0] == 0:  # No existing entry for this city and date
            cursor.execute('''
                INSERT INTO weather_data (city, date, temperature, condition) 
                VALUES (?, ?, ?, ?)
            ''', (city, date, temperature, condition))
    
    conn.commit()
    conn.close()

# Retrieve weather data based on city for a 7-day forecast
def search_weather_data(city):
    conn = connect_db()
    cursor = conn.cursor()

    # Retrieve weather information for a specific city ordered by date
    cursor.execute('''
        SELECT date, temperature, condition 
        FROM weather_data 
        WHERE city = ?
        ORDER BY date
    ''', (city,))
    
    weather_info = cursor.fetchall()
    conn.close()

    return weather_info

# Create file metadata table
def create_files_table():
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS files (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        filename TEXT NOT NULL,
                        uploader TEXT NOT NULL,
                        upload_time DATETIME DEFAULT CURRENT_TIMESTAMP
                      )''')

    conn.commit()
    conn.close()

# Save file metadata in the database
def save_file_metadata(filename, uploader):
    conn = connect_db()
    cursor = conn.cursor()

    # Insert file metadata into the database
    cursor.execute('''
        INSERT INTO files (filename, uploader)
        VALUES (?, ?)
    ''', (filename, uploader))

    conn.commit()
    conn.close()





# Retrieve all uploaded files
def get_uploaded_files():
    conn = connect_db()
    cursor = conn.cursor()

    # Fetch the filenames and uploader info from the files table
    cursor.execute('''
        SELECT filename, uploader
        FROM files
    ''')
    
    files = cursor.fetchall()
    conn.close()

    # Ensure files are returned as a list of dictionaries
    return [{'filename': file[0], 'uploader': file[1]} for file in files]


def delete_file_metadata(filename):
    conn = connect_db()
    cursor = conn.cursor()

    try:
        # Delete the file's metadata based on the filename
        cursor.execute('''
            DELETE FROM files WHERE filename = ?
        ''', (filename,))
        conn.commit()
    except Exception as e:
        print(f"Error deleting file metadata: {e}")
    finally:
        conn.close()




# Pre-populate the weather data for Montreal, Toronto, and Vancouver (for testing purposes)
def prepopulate_weather_data():
    weather_data = {
        'Montreal': [
            ('2024-11-01', 5, 'Sunny'),
            ('2024-11-02', 6, 'Partly Cloudy'),
            ('2024-11-03', 4, 'Rainy'),
            ('2024-11-04', 3, 'Snowy'),
            ('2024-11-05', 7, 'Cloudy'),
            ('2024-11-06', 8, 'Windy'),
            ('2024-11-07', 5, 'Foggy')
        ],
        'Toronto': [
            ('2024-11-01', 10, 'Sunny'),
            ('2024-11-02', 12, 'Partly Cloudy'),
            ('2024-11-03', 8, 'Rainy'),
            ('2024-11-04', 9, 'Snowy'),
            ('2024-11-05', 13, 'Cloudy'),
            ('2024-11-06', 14, 'Windy'),
            ('2024-11-07', 11, 'Foggy')
        ],
        'Vancouver': [
            ('2024-11-01', 11, 'Sunny'),
            ('2024-11-02', 13, 'Partly Cloudy'),
            ('2024-11-03', 9, 'Rainy'),
            ('2024-11-04', 7, 'Snowy'),
            ('2024-11-05', 15, 'Cloudy'),
            ('2024-11-06', 16, 'Windy'),
            ('2024-11-07', 13, 'Foggy')
        ]
    }

    for city, forecast in weather_data.items():
        store_weather_data(city, forecast)
