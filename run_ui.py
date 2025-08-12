from flask import Flask, send_from_directory, jsonify
from flask_socketio import SocketIO, emit
import os
import asyncio
from main import run_agent_task
import threading
import sys
from io import StringIO
import webbrowser
from threading import Timer
from queue import Queue
import config

# Virtual environment check
# if sys.prefix == sys.base_prefix:
#     print("[ERROR] This script is not running in a virtual environment.")
#     print("Please activate the virtual environment created by 'setup.bat' before running this script.")
#     # Use input() to pause execution in a command window
#     input("Press Enter to exit...")
#     sys.exit(1)

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
agent_paused = threading.Event()
agent_stopped = threading.Event()
agent_status = "Idle"
clarification_request_queue = Queue()
clarification_response_queue = Queue()

# --- Recording State ---
is_recording = False
recorded_events = []

def run_agent_in_background(objective, req_q, res_q, paused_event, stopped_event):
    """Runs the agent task in a separate thread."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        # Pass the queues and events to the agent task
        loop.run_until_complete(run_agent_task(
            objective,
            clarification_request_queue=req_q,
            clarification_response_queue=res_q,
            paused_event=paused_event,
            stopped_event=stopped_event
        ))
    except Exception as e:
        print(f"Agent task failed with exception: {e}")
    finally:
        print("Agent task finished or stopped. Notifying client.")
        # Ensure the client is notified that the agent has stopped.
        if not stopped_event.is_set():
            socketio.emit('agent_finished', {'status': 'completed'})
        loop.close()

# --- Flask Routes ---
@app.route('/')
def index():
    return send_from_directory(project_root, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(project_root, path)

@app.route('/get_settings')
def get_settings():
    """Route to provide the current settings to the frontend."""
    return jsonify(config.get_config())

# --- SocketIO Event Handlers ---
def get_scripts():
    """Scans the 'scripts' directory for .js files."""
    scripts_dir = os.path.join(project_root, 'scripts')
    if not os.path.exists(scripts_dir):
        return []
    return [f for f in os.listdir(scripts_dir) if f.endswith('.js')]

@socketio.on('connect')
def handle_connect():
    print('Client connected')
    emit('response', {'data': 'Connected to server!'})
    scripts = get_scripts()
    emit('script_list', {'scripts': scripts})

@socketio.on('run_script')
def handle_run_script(json_data):
    """Handles a request to run a script."""
    script_name = json_data.get('script')
    if not script_name:
        emit('error', {'message': 'Script name is required.'})
        return

    scripts_dir = os.path.join(project_root, 'scripts')
    script_path = os.path.join(scripts_dir, script_name)

    if not os.path.exists(script_path):
        emit('error', {'message': f"Script '{script_name}' not found."})
        return

    try:
        with open(script_path, 'r') as f:
            script_content = f.read()

        # For now, we'll treat the script content as the objective.
        # A more advanced implementation would execute the script's JS.
        print(f"Running script '{script_name}' as an objective.")
        handle_start_agent({'objective': script_content})

    except Exception as e:
        error_msg = f"Failed to read or run script '{script_name}': {e}"
        print(f"[ERROR] {error_msg}")
        emit('error', {'message': error_msg})

@socketio.on('start_agent')
def handle_start_agent(json_data):
    global agent_thread, agent_paused, agent_stopped, agent_status, clarification_request_queue, clarification_response_queue
    objective = json_data.get('objective')
    if not objective:
        emit('error', {'message': 'Objective is required.'})
        return

    if agent_thread and agent_thread.is_alive():
        emit('error', {'message': 'Agent is already running.'})
        return

    print(f"Received start request for objective: {objective}")
    emit('response', {'data': f'Starting agent with objective: {objective}'})

    # Reset events and queues
    agent_paused.clear()
    agent_stopped.clear()
    agent_status = "Running"
    while not clarification_request_queue.empty():
        clarification_request_queue.get()
    while not clarification_response_queue.empty():
        clarification_response_queue.get()

    # Start the agent in a new thread
    agent_thread = threading.Thread(
        target=run_agent_in_background,
        args=(objective, clarification_request_queue, clarification_response_queue, agent_paused, agent_stopped)
    )
    agent_thread.start()

@socketio.on('pause_agent')
def handle_pause_agent():
    global agent_paused, agent_status
    if agent_paused.is_set():
        agent_paused.clear()
        agent_status = "Running"
        print("Agent resumed.")
        emit('response', {'data': 'Agent resumed.'})
    else:
        agent_paused.set()
        agent_status = "Paused"
        print("Agent paused.")
        emit('response', {'data': 'Agent paused.'})

@socketio.on('stop_agent')
def handle_stop_agent():
    global agent_stopped, agent_thread, agent_status
    if agent_thread and agent_thread.is_alive():
        agent_stopped.set()
        # Wait for the thread to finish
        agent_thread.join()
        agent_status = "Idle"
        print("Agent stopped.")
        emit('response', {'data': 'Agent stopped.'})
        socketio.emit('agent_finished', {'status': 'stopped'})

@socketio.on('clarification_response')
def handle_clarification_response(json_data):
    """Handles the user's response to a clarification request."""
    print(f"Received clarification response: {json_data}")
    clarification_response_queue.put(json_data)

@socketio.on('update_config')
def handle_update_config(json_data):
    """Handles configuration updates from the UI toggles."""
    key = json_data.get('key')
    value = json_data.get('value')
    if key:
        print(f"[CONFIG] Updated '{key}' to '{value}'")
        config.update_setting(key, value)
        emit('response', {'data': f"Configuration '{key}' updated to '{value}'."})

# --- Recording Event Handlers ---
@socketio.on('start_recording')
def handle_start_recording():
    global is_recording, recorded_events
    is_recording = True
    recorded_events = []
    print("[INFO] Started recording user actions.")
    # Notify the bridge to start recording
    socketio.emit('start_recording_bridge', namespace='/bridge')
    emit('response', {'data': 'Recording started.'})

@socketio.on('stop_recording')
def handle_stop_recording():
    global is_recording
    is_recording = False
    print("[INFO] Stopped recording user actions.")
    # Notify the bridge to stop recording
    socketio.emit('stop_recording_bridge', namespace='/bridge')
    # For now, just print the recorded events to the console.
    print(f"Recorded events: {recorded_events}")
    emit('response', {'data': f'Recording stopped. {len(recorded_events)} events captured.'})

@socketio.on('record_action', namespace='/bridge')
def handle_record_action(data):
    """Handles an action event sent from the injected bridge script."""
    if is_recording:
        recorded_events.append(data)

        # Format the event into a user-friendly string for the live log
        event_type = data.get('type', 'unknown').upper()
        selector = data.get('selector', 'N/A')
        value = data.get('value', '')

        if event_type == 'CLICK':
            log_message = f"CLICK on element '{selector}'"
        elif event_type == 'INPUT':
            log_message = f"INPUT text '{value}' into element '{selector}'"
        else:
            log_message = f"Captured {event_type} on {selector}"

        # Also print to the server console for debugging
        print(f"[REC] {log_message}")

        # Emit the formatted message to the UI's live log
        socketio.emit('log_update', {'data': f"[USER ACTION] {log_message}"})

def stream_clarification_requests():
    """Periodically checks for clarification requests from the agent and sends them to the UI."""
    while True:
        if not clarification_request_queue.empty():
            request = clarification_request_queue.get()
            socketio.emit('clarification_request', request)
            print(f"Sent clarification request to client: {request}")
        socketio.sleep(1) # Non-blocking sleep

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

def stream_status():
    """Periodically sends status updates to the client."""
    global agent_status
    while True:
        if not (agent_thread and agent_thread.is_alive()):
            agent_status = "Idle"

        status_data = {
            'status': agent_status,
            'ip': '127.0.0.1', # Placeholder
            'user_agent': 'Default', # Placeholder
            'speed': 'Normal', # Placeholder
            'stealth': 'ON' # Placeholder
        }
        socketio.emit('status_update', status_data)
        socketio.sleep(2) # Update status every 2 seconds

def open_browser():
    """Opens the default web browser to the application's URL."""
    webbrowser.open_new("http://127.0.0.1:5000")

if __name__ == "__main__":
    # Start the background tasks
    socketio.start_background_task(stream_logs)
    socketio.start_background_task(stream_clarification_requests)
    socketio.start_background_task(stream_status)

    print("Starting web server with SocketIO...")
    # Open the web browser 1 second after starting the server
    Timer(1, open_browser).start()

    # Using host='0.0.0.0' makes the server accessible from the local network
    # allow_unsafe_werkzeug is required for running in this threaded mode
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)
