from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_socketio import SocketIO, emit
import user_db
import alerts_db
from datetime import timedelta
from flask import send_from_directory
import os
import shutil



app = Flask(__name__)
socketio = SocketIO(app)  # Initialize SocketIO with Flask

# Define the path for deleted files
DELETED_FILES_FOLDER = './deleted_files'
app.config['DELETED_FILES_FOLDER'] = DELETED_FILES_FOLDER

# Create the folder if it doesn't exist
os.makedirs(DELETED_FILES_FOLDER, exist_ok=True)


UPLOAD_FOLDER = './uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    
# Server configuration
MAIN_SERVER_HOST = '127.0.0.1'
MAIN_SERVER_PORT = 5000
ALERT_SERVER_HOST = '127.0.0.1'
ALERT_SERVER_PORT = 5003

# Flask secret key and session timeout
app.secret_key = 'your_secret_key'  # Replace with a secure key
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)

# Global list to keep track of connected users
connected_users = []

# Function to check if the file has a valid extension
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Function to send alert to the alert server and broadcast via SocketIO
def send_to_alert_server(alert_message):
    try:
        # Store the alert in the database
        alerts_db.add_weather_alert('Global', alert_message, session['username'])

        # Broadcast the alert to all connected clients using WebSocket (SocketIO)
        socketio.emit('new_alert', {'message': alert_message}, room=None)  # This is for older versions of Flask-SocketIO
        print(f"Sent alert to all connected users: {alert_message}")
    except Exception as e:
        print(f"Error sending alert: {e}")



# Function to search weather data from the database based on the city name
def search_weather_data(city):
    conn = user_db.connect_db()
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

# Function to update weather data
def update_weather_data(city, date, temperature, condition, alert_description=None):
    conn = user_db.connect_db()
    cursor = conn.cursor()

    # First, try to update the weather data for the specific city on a specific date
    cursor.execute('''
        UPDATE weather_data
        SET temperature = ?, condition = ?
        WHERE city = ? AND date = ? AND condition = ?
    ''', (temperature, condition, city, date, condition))

    # If no rows were updated (meaning the record didn't exist), insert a new one
    if cursor.rowcount == 0:
        cursor.execute('''
            INSERT INTO weather_data (city, date, temperature, condition)
            VALUES (?, ?, ?, ?)
        ''', (city, date, temperature, condition))

    conn.commit()

    # If an alert description is provided, add the alert to the alerts database
    if alert_description:
        username = session['username']  # Assuming username is available in the session
        alerts_db.add_weather_alert(city, alert_description, username)  # Store the alert in the database
        # Optionally, broadcast the alert to clients (this can be done via SocketIO, for example)
        send_to_alert_server(alert_description)  # This would call your function to broadcast

    conn.close()



# Route for the home page
@app.route('/')
def home():
    return render_template('index.html')

# Route for registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if user_db.register_user(username, password):
            return redirect(url_for('login'))
        else:
            return "Username already taken!", 400

    return render_template('register.html')

# Route for login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if user_db.verify_login(username, password):
            if username not in connected_users:
                connected_users.append(username)

            session['username'] = username
            session.permanent = True
            return redirect(url_for('dashboard'))
        else:
            return "Invalid login credentials", 400

    return render_template('login.html')

# User dashboard
@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']

    options = [
        {"name": "Search Weather", "link": "/select_city"},
        {"name": "Update Weather", "link": "/update_weather"},
        {"name": "View Alerts", "link": "/alerts"},
        {"name": "Exit", "link": "/logout"},
        {"name": "View All Connected Users", "link": "/view_clients"}
    ]
    return render_template('dashboard.html', options=options, connected_users=connected_users, username=username)

@app.route('/select_city', methods=['GET', 'POST'])
def select_city():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        selected_city = request.form['city']
        weather_info = search_weather_data(selected_city)

        if weather_info:
            seen = set()
            unique_weather_info = []
            for day in weather_info:
                if (day[0], day[1], day[2]) not in seen:
                    seen.add((day[0], day[1], day[2]))
                    unique_weather_info.append(day)

            return render_template('select_city.html',
                                   location=selected_city,
                                   weather_info=unique_weather_info,
                                   city=selected_city)

    return render_template('select_city.html')

@app.route('/update_weather/<city>/<date>', methods=['GET', 'POST'])
def update_weather(city, date):
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        temperature = request.form['temperature']
        condition = request.form['condition']
        alert = request.form.get('alert')  # Check if the alert checkbox is checked
        alert_description = request.form.get('alert_description', '')

        # Update weather data
        update_weather_data(city, date, temperature, condition)

        if alert and alert_description:  # If alert is checked and description is provided
            username = session['username']
            send_to_alert_server(alert_description)  # Save the alert and broadcast to clients

        weather_info = search_weather_data(city)

        weather_for_date = None
        for record in weather_info:
            if record[0] == date:
                weather_for_date = record
                break

        if weather_for_date:
            return render_template('update_weather.html', city=city, date=date, weather=weather_for_date,
                                   message="Weather data updated successfully!")

    weather_info = search_weather_data(city)
    weather_for_date = None
    for record in weather_info:
        if record[0] == date:
            weather_for_date = record
            break

    if weather_for_date:
        return render_template('update_weather.html', city=city, date=date, weather=weather_for_date)

    return "Weather data for this date not found", 404

# Route for viewing alerts
@app.route('/alerts', methods=['GET'])
def alerts():
    if 'username' not in session:
        return redirect(url_for('login'))

    try:
        # Retrieve all alerts from the alerts_db
        alerts = alerts_db.get_weather_alerts()  # Make sure this function returns all alerts
        return render_template('weather_alerts.html', alerts=alerts)
    except Exception as e:
        return f"Error loading alerts: {e}", 500



@app.route('/view_clients')
def view_clients():
    if 'username' not in session:
        return redirect(url_for('login'))

    print(f"Connected users at view_clients: {connected_users}")
    return render_template('view_clients.html', connected_users=connected_users)

# Route for logging out (Exit)
@app.route('/logout')
def logout():
    username = session.get('username')
    if username and username in connected_users:
        connected_users.remove(username)

    session.pop('username', None)  # Clear the session
    return redirect(url_for('login'))

# Socket event for broadcasting alert message to all connected clients
@socketio.on('new_alert')
def handle_alert(alert_data):
    message = alert_data['message']
    print(f"New alert received: {message}")
    emit('new_alert', {'message': message}, broadcast=True)
    
@socketio.on('test_alert')
def test_alert(data):
    print("Received test alert: ", data)
    socketio.emit('new_alert', {'message': 'This is a test alert'}, room=None)
    
@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part', 'error')
            return redirect(request.url)

        file = request.files['file']
        if file.filename == '':
            flash('No selected file', 'error')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)

            # Save the file metadata in the database
            user_db.save_file_metadata(file.filename, session['username'])

            # Notify all connected clients about the new file
            socketio.emit('new_file_uploaded', {'filename': file.filename, 'uploader': session['username']}, to='all')


            flash('File uploaded successfully!', 'success')
            return redirect(url_for('files'))  # Redirect to the files page to see the uploaded files

    return render_template('upload.html')



@app.route('/files', methods=['GET'])
def files():
    if 'username' not in session:
        return redirect(url_for('login'))

    files = user_db.get_uploaded_files()
    return render_template('files.html', files=files)

@app.route('/files/download/<filename>')
def download_file(filename):
    if 'username' not in session:
        return redirect(url_for('login'))

    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

# Socket event to notify all clients when a new file is uploaded
@socketio.on('new_file_uploaded')
def handle_new_file(data):
    print(f"New file uploaded: {data['filename']} by {data['uploader']}")
    emit('new_file_uploaded', {'filename': data['filename'], 'uploader': data['uploader']}, broadcast=True)
    
@app.route('/view_files', methods=['GET'])
def view_files():
    if 'username' not in session:
        return redirect(url_for('login'))

    # Fetch all uploaded files metadata from the database
    files = user_db.get_uploaded_files()

    # Debug: Print files to console
    print("Files fetched: ", files)

    return render_template('view_files.html', files=files)



@app.route('/files/delete/<filename>', methods=['POST'])
def delete_file(filename):
    if 'username' not in session:
        return redirect(url_for('login'))

    # Construct the file path in the original folder
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    deleted_file_path = os.path.join(app.config['DELETED_FILES_FOLDER'], filename)

    try:
        # Check if the file exists before moving it
        if os.path.exists(file_path):
            # Move the file to the deleted files folder
            shutil.move(file_path, deleted_file_path)

            # Optionally, delete the file metadata from the database
            user_db.delete_file_metadata(filename)

            # Flash success message
            flash(f"File '{filename}' moved to the deleted files folder.", "success")
        else:
            flash(f"File '{filename}' does not exist.", "error")
    except Exception as e:
        print(f"Error deleting file: {e}")
        flash(f"Error deleting file '{filename}': {str(e)}", "error")

    # Reload the updated list of files
    files = user_db.get_uploaded_files()  # Assuming this function retrieves the updated list of files

    # Redirect back to the files page after deletion
    return render_template('view_files.html', files=files)


import os

# Route to view deleted files
@app.route('/view_deleted_files')
def view_deleted_files():
    if 'username' not in session:
        return redirect(url_for('login'))

    # Get the list of deleted files from the deleted files folder
    deleted_files = os.listdir(app.config['DELETED_FILES_FOLDER'])

    return render_template('view_deleted_files.html', deleted_files=deleted_files)


@app.route('/deleted_files/download/<filename>')
def download_deleted_file(filename):
    if 'username' not in session:
        return redirect(url_for('login'))

    file_path = os.path.join(DELETED_FILES_FOLDER, filename)

    if os.path.exists(file_path):
        return send_from_directory(DELETED_FILES_FOLDER, filename, as_attachment=True)
    else:
        flash(f"File '{filename}' not found in deleted files.", "error")
        return redirect(url_for('view_deleted_files'))




if __name__ == '__main__':
    user_db.create_tables()
    alerts_db.create_alerts_table()  # Create the alerts table
    user_db.prepopulate_weather_data()
    socketio.run(app, debug=True)  # Start the app with socketio support