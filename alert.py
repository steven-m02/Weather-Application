import socket
import json
import threading
import alerts_db  # Import the alerts database functions
from app import socketio  # Import socketio from your Flask app

ALERT_SERVER_HOST = '127.0.0.1'
ALERT_SERVER_PORT = 5003
CONNECTED_CLIENTS = []  # List to store connected clients for broadcasting alerts

# Function to handle incoming client connections and send alerts
def handle_alert_client(client_socket):
    CONNECTED_CLIENTS.append(client_socket)
    print(f"Client connected for alerts. Total connected: {len(CONNECTED_CLIENTS)}")
    
    # Retrieve and send existing alerts to the client
    try:
        alerts = alerts_db.get_weather_alerts()  # Get all alerts from the database
        for alert in alerts:
            alert_data = {"type": "alert", "message": alert[1]}  # alert[1] is the message
            client_socket.send(json.dumps(alert_data).encode())  # Send existing alerts

        while True:
            data = client_socket.recv(1024).decode()
            if data:
                request = json.loads(data)
                if request['type'] == 'get_latest_alert':
                    alert = alerts_db.get_latest_alert()
                    if alert:
                        alert_data = {"type": "alert", "message": alert[1]}  # alert[1] is the message
                        client_socket.send(json.dumps(alert_data).encode())
                elif request['type'] == 'alert':
                    message = request.get('message', '')
                    # Broadcast the alert to all connected clients
                    broadcast_alert(message)
            else:
                break
    except Exception as e:
        print(f"Error handling alert client: {e}")
    finally:
        # Remove client when disconnected
        if client_socket in CONNECTED_CLIENTS:
            CONNECTED_CLIENTS.remove(client_socket)
        client_socket.close()
        print(f"Client disconnected. Total connected: {len(CONNECTED_CLIENTS)}")

# Function to broadcast an alert to all connected clients
def broadcast_alert(alert_message):
    print(f"Broadcasting alert: {alert_message}")
    for client_socket in CONNECTED_CLIENTS:
        try:
            alert_data = {"type": "alert", "message": alert_message}
            client_socket.send(json.dumps(alert_data).encode())
        except Exception as e:
            print(f"Error broadcasting alert: {e}")

# Start the alert server
def start_alert_server():
    alert_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    alert_server.bind((ALERT_SERVER_HOST, ALERT_SERVER_PORT))
    alert_server.listen(5)
    print(f"Alert server listening on {ALERT_SERVER_HOST}:{ALERT_SERVER_PORT}...")

    while True:
        client_socket, client_address = alert_server.accept()
        print(f"New connection from {client_address}")
        threading.Thread(target=handle_alert_client, args=(client_socket,)).start()

if __name__ == "__main__":
    start_alert_server()
