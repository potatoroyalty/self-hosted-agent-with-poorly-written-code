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
            self.socketio.on_event('page_content_response', self._handle_page_content_response, namespace='/bridge')
            self.socketio.on_event('found_elements_response', self._handle_found_elements_response, namespace='/bridge')

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

    def _handle_page_content_response(self, data):
        print("[SOCKETS] Received page_content response from bridge.")
        self.pending_request_event.data = data
        self.pending_request_event.set()

    def _handle_found_elements_response(self, data):
        print("[SOCKETS] Received found_elements response from bridge.")
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


    async def propagate_settings_to_bridge(self):
        """Sends the current dynamic settings to the browser bridge."""
        if self.socketio:
            settings = {
                'load_images': config.get_setting('LOAD_IMAGES'),
                'enable_javascript': config.get_setting('ENABLE_JAVASCRIPT'),
                # Note: Stealth and Proxy are context-level and cannot be changed on the fly.
                # We send them for informational purposes or for future bridge-side logic.
                'stealth_mode': config.get_setting('STEALTH_MODE'),
                'use_proxy': config.get_setting('USE_PROXY')
            }
            # This is too noisy to log on every step
            # print(f"[SETTINGS] Propagating settings to bridge: {settings}")
            self.socketio.emit('update_bridge_settings', settings, namespace='/bridge')

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

    def user_did_navigate(self, new_url: str):
        """
        Updates the controller's state when the user navigates the browser manually.
        This method should not trigger any browser actions, only update internal state.
        """
        from_url = self.current_url
        self.current_url = new_url
        print(f"[STATE] URL updated by user action: from '{from_url}' to '{self.current_url}'")

        if self.website_graph:
            self.website_graph.add_page(from_url)
            self.website_graph.add_page(self.current_url, page_title="Title (Unknown)")
            action = {"type": "user_navigation"}
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
                if action_type == 'click' and self.recovery and element_label is not None:
                    print(f"[INFO] Click action failed. Attempting recovery for element {element_label}.")
                    recovery_success, recovery_message = await self.recovery.recover_from_click_failure(
                        element_label=int(element_label)
                    )
                    if recovery_success:
                        return True, f"Recovered from failed click: {recovery_message}"
                    else:
                        return False, f"Click action failed and recovery also failed: {recovery_message}"
                return False, f"Action '{action_type}' failed: {error_msg}"
        except TimeoutError:
            if action_type == 'click' and self.recovery and element_label is not None:
                print(f"[INFO] Click action timed out. Attempting recovery for element {element_label}.")
                recovery_success, recovery_message = await self.recovery.recover_from_click_failure(
                    element_label=int(element_label)
                )
                if recovery_success:
                    return True, f"Recovered from timed out click: {recovery_message}"
                else:
                    return False, f"Click action timed out and recovery also failed: {recovery_message}"
            return False, f"Action '{action_type}' failed: Timed out waiting for response from bridge."
        except Exception as e:
            return False, f"Action '{action_type}' failed with exception: {e}"

    # --- Other methods that need to be refactored or removed ---
    # The methods below are largely placeholders or need to be adapted to the new model.
    # For now, many will return dummy data or indicate they are not implemented.

    async def get_page_content(self) -> tuple[bool, str]:
        """Gets the full text content of the current page via the bridge."""
        print("[ACTION] Requesting page content from bridge...")
        self.socketio.emit('get_page_content', {}, namespace='/bridge')

        try:
            response = await self._wait_for_bridge_response()
            if response.get('success'):
                return True, response.get('text', '')
            else:
                error_msg = response.get('error', 'Failed to get page content.')
                return False, f"Could not get page content: {error_msg}"
        except TimeoutError:
            return False, "Timed out waiting for page content from bridge."

    async def get_element_details(self, label: int) -> tuple[bool, dict | str]:
        """Gets element details from the cached list."""
        if label in self.labeled_elements:
            return True, self.labeled_elements[label]
        else:
            return False, f"Invalid label {label}."

    async def find_elements_by_text(self, text_to_find: str) -> tuple[bool, list | str]:
        """Finds elements by text content via the bridge and returns their labels."""
        print(f"[ACTION] Requesting to find elements by text from bridge for: '{text_to_find}'")
        self.socketio.emit('find_elements_by_text', {'text': text_to_find}, namespace='/bridge')

        try:
            response = await self._wait_for_bridge_response()
            if response.get('success'):
                return True, response.get('labels', [])
            else:
                error_msg = response.get('error', 'Failed to find elements by text.')
                return False, f"Could not find elements by text: {error_msg}"
        except TimeoutError:
            return False, "Timed out waiting for elements from bridge."

    async def get_all_links(self) -> tuple[bool, list | str]:
        """
        Gets a list of all hyperlink URLs from the current page.
        """
        print("[ACTION] Getting all links from the page.")
        try:
            # We don't need a new screenshot, just the element data.
            # The `observe_and_annotate` method is the current way to get this data.
            _, elements = await self.observe_and_annotate(step=-2) # Use a different dummy step

            links = []
            for element in elements:
                # The bridge now sends the tag and href for each element.
                if element.get('tag') == 'a' and element.get('href'):
                    links.append(element.get('href'))

            # Remove duplicates
            unique_links = sorted(list(set(links)))

            return True, unique_links
        except Exception as e:
            print(f"[ERROR] An unexpected error occurred while getting all links: {e}")
            return False, f"An unexpected error occurred while getting all links: {e}"

    async def _tool_perform_google_search(self, query: str) -> Tuple[bool, str]:
        """
        Performs a Google search by navigating to the homepage, finding the
        search elements, and executing the search. This is a special tool
        implementation that is not meant to be called directly by the AI model.
        """
        print(f"[ACTION] Performing Google search for: '{query}'")
        try:
            # 1. Navigate to Google
            await self.goto_url("https://www.google.com")
            # Let's add a small delay to ensure the page loads and the bridge is ready.
            await asyncio.sleep(2)

            # 2. Observe the page to get labeled elements
            # We pass a dummy step number since this is an internal tool action.
            _, elements = await self.observe_and_annotate(step=-1)

            # 3. Find the search box and search button from the elements
            search_box_label = None
            search_button_label = None

            for element in elements:
                # More robust search box finding
                if element.get("tag") in ["textarea", "input"] and element.get("name") == "q":
                    search_box_label = element.get("label")

                # More robust search button finding
                aria_label = element.get("aria_label", "").lower()
                text_content = element.get("text", "").lower() # Assuming bridge could send text content
                value_attr = element.get("value", "").lower()

                if element.get("tag") in ["button", "input"] and (
                    "google search" in aria_label or
                    "google search" in text_content or
                    "google search" in value_attr
                ):
                    # Prioritize visible buttons over hidden inputs if possible
                    if not search_button_label or element.get("tag") == "button":
                         search_button_label = element.get("label")

            if not search_box_label:
                return False, "Could not find the search input box on the page. (Looking for input with name='q')"
            if not search_button_label:
                # As a fallback, try to find a submit button if the main search fails.
                for element in elements:
                    if element.get("tag") == "input" and element.get("type") == "submit":
                        search_button_label = element.get("label")
                        break
                if not search_button_label:
                    return False, "Could not find the Google Search button on the page."

            # 4. Type the query into the search box
            success, message = await self.execute_action({
                "action_type": "type",
                "details": {"element_label": search_box_label, "text": query}
            })
            if not success:
                return False, f"Failed to type into search box: {message}"

            await asyncio.sleep(1) # Small delay between actions

            # 5. Click the search button
            success, message = await self.execute_action({
                "action_type": "click",
                "details": {"element_label": search_button_label}
            })
            if not success:
                return False, f"Failed to click search button: {message}"

            return True, f"Successfully performed Google search for '{query}'."

        except Exception as e:
            print(f"[ERROR] An unexpected error occurred during Google search: {e}")
            return False, f"An unexpected error occurred during Google search: {e}"
