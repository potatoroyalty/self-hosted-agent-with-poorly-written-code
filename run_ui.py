from flask import Flask, send_from_directory, jsonify
from flask_socketio import SocketIO, emit
import os
import json
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

# --- AI Model ---
# We initialize the AIModel here to be accessible by the script generator.
# This avoids re-initializing the model on every request.
# In a production scenario, you might use a more sophisticated dependency injection pattern.
try:
    from ai_model import AIModel
    ai_model_instance = AIModel()
except Exception as e:
    print(f"[FATAL ERROR] Could not initialize AIModel: {e}")
    print("The script generation feature will be disabled.")
    ai_model_instance = None


def run_agent_in_background(objective, req_q, res_q, paused_event, stopped_event, socketio_instance):
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
            stopped_event=stopped_event,
            socketio=socketio_instance
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

@app.route('/get_log_content/<log_type>')
def get_log_content(log_type):
    """Route to provide the content of a specific log file."""
    if log_type == 'critique':
        log_file = config.CRITIQUE_FILE
    elif log_type == 'memory':
        log_file = config.MEMORY_FILE
    else:
        return jsonify({"error": "Invalid log type"}), 400

    try:
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            return jsonify({"content": content})
        else:
            return jsonify({"content": f"{log_file} not found."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get_scripts')
def get_scripts_route():
    """Route to provide the list of scripts."""
    scripts = get_scripts()
    return jsonify({"scripts": scripts})


@app.route('/get_proxies')
def get_proxies_route():
    """Route to provide the list of proxies."""
    try:
        proxies_file = os.path.join(project_root, 'proxies.json')
        if os.path.exists(proxies_file):
            with open(proxies_file, 'r', encoding='utf-8') as f:
                proxies = json.load(f)
            return jsonify({"proxies": proxies})
        else:
            return jsonify({"proxies": []})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@socketio.on('save_proxies')
def handle_save_proxies(json_data):
    """Handles a request to save the proxy list."""
    proxies = json_data.get('proxies')
    if proxies is None:
        emit('proxies_saved', {'success': False, 'error': 'No proxy data provided.'})
        return

    try:
        proxies_file = os.path.join(project_root, 'proxies.json')
        with open(proxies_file, 'w', encoding='utf-8') as f:
            json.dump(proxies, f, indent=4)
        print("Proxies saved successfully.")
        emit('proxies_saved', {'success': True})
    except Exception as e:
        print(f"Error saving proxies: {e}")
        emit('proxies_saved', {'success': False, 'error': str(e)})


@socketio.on('clear_log')
def handle_clear_log(json_data):
    """Handles a request to clear a log file."""
    log_type = json_data.get('log_type')
    if not log_type:
        emit('log_cleared', {'success': False, 'error': 'Log type not provided.'})
        return

    if log_type == 'critique':
        log_file = config.CRITIQUE_FILE
    elif log_type == 'memory':
        log_file = config.MEMORY_FILE
    else:
        emit('log_cleared', {'success': False, 'error': 'Invalid log type.'})
        return

    try:
        if os.path.exists(log_file):
            with open(log_file, 'w') as f:
                f.write('') # Overwrite with empty content
            print(f"Cleared log file: {log_file}")
            emit('log_cleared', {'success': True, 'log_type': log_type})
        else:
            # If the file doesn't exist, it's already "clear"
            emit('log_cleared', {'success': True, 'log_type': log_type})
    except Exception as e:
        print(f"Error clearing log '{log_file}': {e}")
        emit('log_cleared', {'success': False, 'error': str(e)})


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
        args=(objective, clarification_request_queue, clarification_response_queue, agent_paused, agent_stopped, socketio)
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

@socketio.on('generate_script')
def handle_generate_script(json_data):
    """Handles a request to generate a script from a recording."""
    global recorded_events, ai_model_instance
    script_name = json_data.get('script_name')
    objective = json_data.get('objective')

    if not script_name or not objective:
        emit('script_generated', {'success': False, 'error': 'Script name and objective are required.'})
        return

    if not recorded_events:
        emit('script_generated', {'success': False, 'error': 'No recorded actions to generate a script from.'})
        return

    if not ai_model_instance:
        emit('script_generated', {'success': False, 'error': 'AI Model is not available.'})
        return

    print(f"Generating script '{script_name}' for objective: {objective}")

    try:
        # This needs to be run in an async context
        async def generate():
            # Sanitize to create a valid class name
            class_name = f"{script_name.replace('_', ' ').title().replace(' ', '')}MacroTool"
            tool_name = script_name

            # We need the tool definitions for the prompt
            # This is a simplification; in a real app, you'd have a more robust way to get this
            from langchain_agent import GoToPageTool, ClickElementTool, TypeTextTool
            tool_definitions = "\n".join([f"- {tool.name}: {tool.description}" for tool in [GoToPageTool, ClickElementTool, TypeTextTool]])

            return await ai_model_instance.generate_script_from_recording(
                recorded_events,
                objective,
                tool_name,
                class_name,
                tool_definitions
            )

        script_content = asyncio.run(generate())

        if not script_content:
            emit('script_generated', {'success': False, 'error': 'AI failed to generate script content.'})
            return

        # Save the script
        scripts_dir = os.path.join(project_root, 'scripts')
        if not os.path.exists(scripts_dir):
            os.makedirs(scripts_dir)

        # Sanitize script_name to be a valid filename
        safe_script_name = "".join(c for c in script_name if c.isalnum() or c in ('_', '-')).rstrip()
        file_path = os.path.join(scripts_dir, f"{safe_script_name}.py")

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(script_content)

        print(f"Script saved to {file_path}")

        emit('script_generated', {
            'success': True,
            'script_name': script_name,
            'script_content': script_content
        })

    except Exception as e:
        error_msg = f"Failed to generate script: {e}"
        print(f"[ERROR] {error_msg}")
        emit('script_generated', {'success': False, 'error': str(e)})


@socketio.on('request_script_list')
def handle_request_script_list():
    """Handles a request to get the list of scripts."""
    print("[INFO] Client requested script list refresh.")
    scripts = get_scripts()
    emit('script_list', {'scripts': scripts})


@socketio.on('delete_script')
def handle_delete_script(json_data):
    """Handles a request to delete a script."""
    script_name = json_data.get('script_name')
    if not script_name:
        emit('script_deleted', {'success': False, 'error': 'Script name not provided.'})
        return

    try:
        scripts_dir = os.path.join(project_root, 'scripts')
        # Basic security check to prevent directory traversal
        if '..' in script_name or not script_name.endswith(('.js', '.py')):
             emit('script_deleted', {'success': False, 'error': 'Invalid script name.'})
             return

        script_path = os.path.join(scripts_dir, script_name)

        if os.path.exists(script_path):
            os.remove(script_path)
            print(f"Deleted script: {script_name}")
            emit('script_deleted', {'success': True, 'script_name': script_name})
        else:
            emit('script_deleted', {'success': False, 'error': 'Script not found.'})
    except Exception as e:
        print(f"Error deleting script '{script_name}': {e}")
        emit('script_deleted', {'success': False, 'error': str(e)})


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
        elif event_type == 'CHANGE':
            log_message = f"CHANGE on element '{selector}' to '{value}'"
        elif event_type == 'SUBMIT':
            log_message = f"SUBMIT form '{selector}'"
        elif event_type == 'KEYDOWN':
            key = data.get('key', 'N/A')
            log_message = f"KEYDOWN '{key}' in element '{selector}'"
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
            'ip': config.get_setting('PROXY_ADDRESS') if config.get_setting('USE_PROXY') else '127.0.0.1',
            'user_agent': config.get_setting('USER_AGENT'),
            'speed': f"{config.get_setting('WAIT_BETWEEN_ACTIONS')}s delay",
            'stealth': 'ON' if config.get_setting('STEALTH_MODE') else 'OFF'
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
