from flask import Flask, send_from_directory
from flask_socketio import SocketIO, emit
import os
import asyncio
from main import run_agent_task
import threading
import sys
from io import StringIO

app = Flask(__name__)
# MODIFIED: Allow for larger messages if screenshots are sent
socketio = SocketIO(app, max_http_buffer_size=10 * 1024 * 1024)

# Get the absolute path to the directory where this script is located
# This is necessary to correctly locate the static files
project_root = os.path.dirname(os.path.abspath(__file__))

# In-memory log capture
log_stream = StringIO()
sys.stdout = log_stream
sys.stderr = log_stream

# --- Agent Task Management ---
agent_thread = None
agent_task = None

def run_agent_in_background(objective):
    """Runs the agent task in a separate thread."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_agent_task(objective))
    loop.close()

# --- Flask Routes ---
@app.route('/')
def index():
    return send_from_directory(project_root, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(project_root, path)

# --- SocketIO Event Handlers ---
@socketio.on('connect')
def handle_connect():
    print('Client connected')
    emit('response', {'data': 'Connected to server!'})

@socketio.on('start_agent')
def handle_start_agent(json_data):
    global agent_thread
    objective = json_data.get('objective')
    if not objective:
        emit('error', {'message': 'Objective is required.'})
        return

    if agent_thread and agent_thread.is_alive():
        emit('error', {'message': 'Agent is already running.'})
        return

    print(f"Received start request for objective: {objective}")
    emit('response', {'data': f'Starting agent with objective: {objective}'})

    # Start the agent in a new thread
    agent_thread = threading.Thread(target=run_agent_in_background, args=(objective,))
    agent_thread.start()

def stream_logs():
    """Periodically sends new log content to the client."""
    last_position = 0
    while True:
        log_stream.seek(last_position)
        new_logs = log_stream.read()
        if new_logs:
            socketio.emit('log_update', {'data': new_logs})
            last_position = log_stream.tell()
        socketio.sleep(1) # Non-blocking sleep

if __name__ == "__main__":
    # Start the log streaming background task
    socketio.start_background_task(stream_logs)

    print("Starting web server with SocketIO...")
    # Using host='0.0.0.0' makes the server accessible from the local network
    # allow_unsafe_werkzeug is required for running in this threaded mode
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)
