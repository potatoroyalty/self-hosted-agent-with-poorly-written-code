# FILE: browser_controller.py

import os
import base64
import io
from typing import List, Tuple, Dict, Optional, Any
from PIL import Image, ImageDraw, ImageFont
import config
from website_graph import WebsiteGraph
from recovery import ErrorRecovery
import asyncio
from queue import Queue, Empty, Full
from threading import Event

class BrowserController:
    """
    A controller for managing a remote browser via Socket.IO,
    handling page interactions, and annotating screenshots for an AI agent.
    """
    def __init__(self, run_folder: str, agent=None, website_graph: Optional[WebsiteGraph] = None, socketio=None, testing=False):
        self.run_folder = run_folder
        self.agent = agent
        self.socketio = socketio
        self.testing = testing
        self.recovery = ErrorRecovery(agent=self.agent) if self.agent else None
        self.website_graph = website_graph

        self.labeled_elements: Dict[int, Dict] = {}
        self.current_screenshot_bytes: Optional[bytes] = None
        self.current_url = "about:blank"

        # Ensure the run folder exists for saving screenshots
        os.makedirs(self.run_folder, exist_ok=True)

        # Event handlers for async communication with the bridge
        if self.socketio:
            self.socketio.on_event('observation_response', self._handle_observation_response, namespace='/bridge')
            self.socketio.on_event('action_response', self._handle_action_response, namespace='/bridge')

        # Request-response mechanism for browser actions
        self.response_queue = Queue(maxsize=1)
        self.pending_request_event = Event()


    def _handle_observation_response(self, data):
        print("[SOCKETS] Received observation response from bridge.")
        self.pending_request_event.data = data
        self.pending_request_event.set()

    def _handle_action_response(self, data):
        print(f"[SOCKETS] Received action response from bridge: {data}")
        self.pending_request_event.data = data
        self.pending_request_event.set()

    async def _wait_for_bridge_response(self, timeout=15):
        """Waits for a response from the bridge for a specific request."""
        if self.testing:
            print("[TESTING] Bypassing bridge wait and returning mock success.")
            return {'success': True}

        self.pending_request_event.clear()
        if self.pending_request_event.wait(timeout):
            return self.pending_request_event.data
        else:
            raise TimeoutError("Timed out waiting for response from the browser bridge.")


    async def start(self):
        """Starts the browser controller. No browser is launched here anymore."""
        print("[INFO] BrowserController started. Ready to connect to bridge.")
        # We need to wait until the UI and the bridge are ready.
        # For now, we assume they will be ready when needed.
        pass

    async def close(self):
        """Closes the browser controller."""
        print("[INFO] BrowserController closed.")
        pass

    async def goto_url(self, url: str):
        """Navigates the remote browser to the specified URL."""
        from_url = self.current_url

        print(f"[ACTION] Navigating to URL: {url}")
        self.socketio.emit('goto', {'url': url}, namespace='/bridge')

        # Navigation is a special case. We don't get a direct 'action_response'.
        # The page loads, the bridge re-injects, and we're ready for the next observation.
        # We will update the URL optimistically. A failed navigation will be caught
        # by the next observation.
        self.current_url = url if "://" in url else "http://" + url

        if self.socketio:
            print(f"[SOCKETS] Emitting 'browser_navigated' event to UI. URL: {self.current_url}")
            self.socketio.emit('browser_navigated', {'url': self.current_url})

        if self.website_graph:
            self.website_graph.add_page(from_url)
            self.website_graph.add_page(self.current_url, page_title="Title (Unknown)") # Title is not available anymore
            action = {"type": "goto", "url": url}
            self.website_graph.add_edge(from_url, self.current_url, action)

    async def observe_and_annotate(self, step: int) -> Tuple[str, List[Dict]]:
        """
        Captures a screenshot via the bridge, annotates it with labels on interactive elements,
        and returns the annotated image and the list of labeled elements.
        """
        print("[ACTION] Requesting observation from bridge...")
        self.socketio.emit('get_observation', {}, namespace='/bridge')
        
        try:
            response = await self._wait_for_bridge_response()
        except TimeoutError:
            print("[ERROR] Timed out waiting for observation from bridge.")
            return "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=", []

        if not response.get('success'):
            print(f"[ERROR] Bridge failed to get observation: {response.get('error')}")
            return "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=", []

        # Process the observation data
        screenshot_bytes = base64.b64decode(response['screenshot'])
        elements_to_label = response['elements']
        self.current_screenshot_bytes = screenshot_bytes
        self.labeled_elements = {el['label']: el for el in elements_to_label}

        # Annotate the screenshot
        img = Image.open(io.BytesIO(screenshot_bytes))
        draw = ImageDraw.Draw(img)
        font_size = 18
        font = ImageFont.load_default(size=font_size)

        for i, element_data in enumerate(elements_to_label):
            label = str(element_data['label'])
            box = element_data['box']

            # Draw bounding box
            draw.rectangle([box['x'], box['y'], box['x'] + box['width'], box['y'] + box['height']], outline="red", width=2)
            
            # Prepare and draw label
            bbox = draw.textbbox((0, 0), label, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            padding = 2
            label_x = box['x']
            label_y = box['y'] - text_height - (padding * 2)
            if label_y < 0:
                label_y = box['y'] + box['height']

            draw.rectangle(
                [label_x, label_y, label_x + text_width + (padding * 2), label_y + text_height + (padding * 2)],
                fill="red"
            )
            draw.text((label_x + padding, label_y + padding), label, fill="white", font=font)

        # Save and send annotated image
        annotated_buffer = io.BytesIO()
        img.save(annotated_buffer, format="PNG")
        annotated_image_bytes = annotated_buffer.getvalue()

        screenshot_path = os.path.join(self.run_folder, f"step_{step}_annotated.png")
        with open(screenshot_path, "wb") as f:
            f.write(annotated_image_bytes)

        if self.socketio:
            encoded_annotated_image = base64.b64encode(annotated_image_bytes).decode('utf-8')
            self.socketio.emit('agent_view_updated', {'image': encoded_annotated_image})

        # Return the original, un-annotated image for the AI model
        encoded_original_image = base64.b64encode(screenshot_bytes).decode('utf-8')

        # Return a list of dictionaries, not ElementHandles
        return encoded_original_image, list(self.labeled_elements.values())


    async def execute_action(self, action_json: dict) -> Tuple[bool, str]:
        """
        Executes a browser action by sending a command to the bridge.
        """
        action_type = action_json.get("action_type")
        details = action_json.get("details", {})
        element_label = details.get("element_label")

        if not action_type:
            return False, "Action failed: Missing 'action_type'."

        # Prepare command for the bridge
        command = {'action': action_type}
        if element_label is not None:
            command['label'] = int(element_label)
        if action_type == 'type':
            command['text'] = details.get('text', '')
        elif action_type == 'select':
            command['value'] = details.get('value', '')
        elif action_type == 'scroll':
            command['direction'] = details.get('direction', 'down')

        # Get element box for UI feedback
        box = None
        if element_label and int(element_label) in self.labeled_elements:
             box = self.labeled_elements[int(element_label)].get('box')

        if self.socketio and box:
            print(f"[SOCKETS] Emitting 'action_executed' event for {action_type} on element {element_label}")
            self.socketio.emit('action_executed', {'action': action_type, 'box': box})

        print(f"[ACTION] Executing '{action_type}' on element '{element_label}' via bridge.")
        self.socketio.emit(action_type, command, namespace='/bridge')

        try:
            response = await self._wait_for_bridge_response()
            if response.get('success'):
                return True, f"Action '{action_type}' on element {element_label} completed successfully."
            else:
                error_msg = response.get('error', 'Unknown error from bridge.')
                return False, f"Action '{action_type}' failed: {error_msg}"
        except TimeoutError:
            return False, f"Action '{action_type}' failed: Timed out waiting for response from bridge."
        except Exception as e:
            return False, f"Action '{action_type}' failed with exception: {e}"

    # --- Other methods that need to be refactored or removed ---
    # The methods below are largely placeholders or need to be adapted to the new model.
    # For now, many will return dummy data or indicate they are not implemented.

    async def get_page_content(self) -> tuple[bool, str]:
        """Not implemented in bridge model yet. Returns a placeholder."""
        return True, "Page content not available in this mode."

    async def get_element_details(self, label: int) -> tuple[bool, dict | str]:
        """Gets element details from the cached list."""
        if label in self.labeled_elements:
            return True, self.labeled_elements[label]
        else:
            return False, f"Invalid label {label}."

    async def find_elements_by_text(self, text_to_find: str) -> tuple[bool, str]:
        """Not implemented in bridge model yet. Returns a placeholder."""
        return True, f"Text search for '{text_to_find}' is not available in this mode."

    async def get_all_links(self) -> tuple[bool, list | str]:
        """Not implemented in bridge model yet. Returns a placeholder."""
        return True, "Link gathering is not available in this mode."
