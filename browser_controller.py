# FILE: browser_controller.py

import os
import base64
import io
from typing import List, Tuple, Dict, Optional, Any
from playwright.async_api import async_playwright, Browser, Page, ElementHandle
from PIL import Image, ImageDraw, ImageFont
import config

class BrowserController:
    """
    A controller for managing a Playwright browser instance,
    handling page interactions, and annotating screenshots for an AI agent.
    """
    def __init__(self, run_folder: str, agent=None):
        self.browser: Browser | None = None
        self.page: Page | None = None
        self.playwright = None
        self.run_folder = run_folder
        self.agent = agent
        self.labeled_elements: List[ElementHandle] = []
        self.current_screenshot_bytes: Optional[bytes] = None
        self.preprocessor_script: Optional[str] = None
        # Ensure the run folder exists for saving screenshots
        os.makedirs(self.run_folder, exist_ok=True)

        # Load the preprocessor script
        try:
            with open(config.PREPROCESSOR_PATH, 'r', encoding='utf-8') as f:
                self.preprocessor_script = f.read()
        except FileNotFoundError:
            print(f"[WARN] Preprocessor script not found at {config.PREPROCESSOR_PATH}. SnapDOM generation will not be available.")

    async def start(self):
        """Starts the Playwright instance and launches a new browser."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=False)
        self.page = await self.browser.new_page()

    async def close(self):
        """Closes the browser and stops the Playwright instance."""
        if self.page:
            await self.page.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    def _get_page(self) -> Page:
        """
        Helper to get the page object, raising a RuntimeError if it's not initialized.
        This provides a single point of failure and a clear error message.
        """
        if not self.page:
            raise RuntimeError("Browser has not been started. Please call start() first.")
        return self.page

    async def goto_url(self, url: str):
        """Navigates the page to the specified URL."""
        page = self._get_page()
        await page.goto(url if "://" in url else "http://" + url)

    async def get_snapdom(self) -> Optional[Dict[str, Any]]:
        """
        Executes the preprocessor script on the current page to get a simplified,
        structured representation of the DOM.

        Returns:
            A dictionary representing the SnapDOM, or None if the script is not available.
        """
        page = self._get_page()
        if not self.preprocessor_script:
            print("[ERROR] Preprocessor script is not loaded. Cannot get SnapDOM.")
            return None

        try:
            snapdom = await page.evaluate(self.preprocessor_script)
            return snapdom
        except Exception as e:
            print(f"[ERROR] Failed to execute preprocessor script and get SnapDOM: {e}")
            return None

    async def observe_and_annotate(self, step: int) -> Tuple[str, List[ElementHandle]]:
        """
        Captures a screenshot, annotates it with labels on interactive elements,
        and returns the annotated image and the list of labeled elements.

        Args:
            step (int): The current step number, used for naming the screenshot file.

        Returns:
            A tuple containing:
            - The base64 encoded string of the original (un-annotated) screenshot.
            - A list of Playwright ElementHandle objects corresponding to the labeled elements.
        """
        page = self._get_page()
        screenshot_path = os.path.join(self.run_folder, f"step_{step}_annotated.png")
        
        # Expanded selector to include more interactive roles
        interactive_elements = await page.query_selector_all(
            "a, button, input, textarea, select, [role='button'], [role='link'], "
            "[role='tab'], [role='checkbox'], [role='menuitem'], [role='option'], [role='switch']"
        )
        
        # Take screenshot into a memory buffer first
        screenshot_bytes = await page.screenshot()
        self.current_screenshot_bytes = screenshot_bytes # Store for later use

        # Efficiently filter for visible elements with valid bounding boxes
        elements_to_label = []
        for element in interactive_elements:
            if await element.is_visible():
                box = await element.bounding_box()
                if box:
                    elements_to_label.append((element, box))

        # Annotate screenshot from memory
        img = Image.open(io.BytesIO(screenshot_bytes))
        draw = ImageDraw.Draw(img)
        font_size = 18
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except IOError:
            font = ImageFont.load_default(size=font_size)

        labeled_elements = []
        for i, (element, box) in enumerate(elements_to_label):
            label = str(i + 1)
            labeled_elements.append(element)

            # Draw the red bounding box around the element
            draw.rectangle([box['x'], box['y'], box['x'] + box['width'], box['y'] + box['height']], outline="red", width=2)
            
            # Calculate text size for a perfectly fitted background
            # The `textsize` method was removed in Pillow 10.0.0. The `textbbox`
            # method is the recommended replacement and is available in Pillow >= 8.0.0.
            # The use of `ImageFont.load_default(size=...)` elsewhere implies a
            # dependency on Pillow >= 9.2.0, so `textbbox` is guaranteed to exist.
            bbox = draw.textbbox((0, 0), label, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            # Position label above the element, but move it below if it would go off-screen
            padding = 2
            label_x = box['x']
            label_y = box['y'] - text_height - (padding * 2)
            if label_y < 0: # If label is off the top of the screen
                label_y = box['y'] + box['height']

            # Draw a perfectly sized background for the label
            draw.rectangle(
                [label_x, label_y, label_x + text_width + (padding * 2), label_y + text_height + (padding * 2)],
                fill="red"
            )
            draw.text((label_x + padding, label_y + padding), label, fill="white", font=font)

        # Save the final annotated image once for logging/review
        img.save(screenshot_path)

        # Encode the original, un-annotated image to base64 for the AI model
        encoded_image = base64.b64encode(screenshot_bytes).decode('utf-8')

        self.labeled_elements = labeled_elements
        return encoded_image, labeled_elements

    async def get_element_screenshot(self, label: int) -> Optional[str]:
        """
        Crops the last screenshot to a specific labeled element's bounding box.

        Args:
            label (int): The numeric label of the element.

        Returns:
            A base64 encoded string of the cropped image, or None if an error occurs.
        """
        if not self.current_screenshot_bytes:
            print("[ERROR] No screenshot available to crop.")
            return None

        try:
            element_index = int(label) - 1
        except (ValueError, TypeError):
            print(f"[ERROR] Invalid element label '{label}'. Must be a number.")
            return None

        if not (0 <= element_index < len(self.labeled_elements)):
            print(f"[ERROR] Invalid element label '{label}'. There are only {len(self.labeled_elements)} labeled elements.")
            return None

        element = self.labeled_elements[element_index]
        box = await element.bounding_box()

        if not box:
            print(f"[ERROR] Element {label} has no bounding box.")
            return None

        img = Image.open(io.BytesIO(self.current_screenshot_bytes))

        # Crop the image using the bounding box
        cropped_img = img.crop((box['x'], box['y'], box['x'] + box['width'], box['y'] + box['height']))

        # Encode the cropped image to base64
        buffer = io.BytesIO()
        cropped_img.save(buffer, format="PNG")
        encoded_image = base64.b64encode(buffer.getvalue()).decode('utf-8')

        return encoded_image

    async def execute_action(self, action_json: dict) -> Tuple[bool, str]:
        """
        Executes a browser action based on the JSON object provided by the AI.

        Args:
            action_json (dict): The action object from the AI.

        Returns:
            A tuple containing:
            - A boolean indicating if the action was successful.
            - A string summarizing the result of the action.
        """
        action_type = action_json.get("action_type")
        details = action_json.get("details", {})
        
        try:
            if action_type in ["click", "type", "select"]:
                element_label = details.get("element_label")
                if element_label is None:
                    return False, f"Action '{action_type}' failed: Missing 'element_label'."
                
                try:
                    element_index = int(element_label) - 1
                except (ValueError, TypeError):
                    return False, f"Action '{action_type}' failed: 'element_label' must be a number, but got '{element_label}'."

                if not (0 <= element_index < len(self.labeled_elements)):
                    return False, f"Action '{action_type}' failed: Invalid element_label '{element_label}'. There are only {len(self.labeled_elements)} labeled elements."
                
                element = self.labeled_elements[element_index]

                if action_type == "click":
                    await element.click(timeout=5000)
                    return True, f"Clicked element {element_label}."
                
                elif action_type == "type":
                    text_to_type = details.get("text")
                    if text_to_type is None:
                        return False, "Type action failed: Missing 'text'."
                    await element.fill(text_to_type, timeout=5000)
                    return True, f"Typed '{text_to_type}' into element {element_label}."

                elif action_type == "select":
                    value_to_select = details.get("value")
                    if value_to_select is None:
                        return False, "Select action failed: Missing 'value'."
                    await element.select_option(value_to_select, timeout=5000)
                    return True, f"Selected option '{value_to_select}' in element {element_label}."
                
            elif action_type == "scroll":
                page = self._get_page()
                direction = details.get("direction", "down")
                scroll_amount = "window.innerHeight" if direction == "down" else "-window.innerHeight"
                await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
                return True, f"Scrolled {direction}."

            else:
                return False, f"Unknown action type: '{action_type}'."

        except Exception as e:
            return False, f"Action '{action_type}' failed: {e}"

        # Ensure a return value on all code paths
        return False, "Action could not be completed due to an unknown error."

    async def get_page_content(self) -> tuple[bool, str]:
        """Get a cleaned summary of the page's text content."""
        try:
            page = self._get_page()
            content = await page.evaluate(r'''() => {
            const text = document.body.innerText;
            return text
                .replace(/\s+/g, ' ')
                .replace(/\n+/g, '\n')
                .trim();
        }''')
            return True, content
        except Exception as e:
            return False, f"Failed to get page content: {e}"

    async def get_element_details(self, label: int) -> tuple[bool, dict | str]:
        """Get detailed information about a specific labeled element."""
        try:
            if not (0 <= label - 1 < len(self.labeled_elements)):
                return False, f"Invalid label {label}. Available labels: 1-{len(self.labeled_elements)}"

            element = self.labeled_elements[label - 1]
            details = await element.evaluate('''(\n                el) => ({
                tag: el.tagName.toLowerCase(),
                text: el.innerText,
                attributes: Object.fromEntries(
                    Array.from(el.attributes).map(attr => [attr.name, attr.value])
                ),
                isVisible: el.offsetParent !== null,
                role: el.getAttribute('role'),
                ariaLabel: el.getAttribute('aria-label')
            })''')
            return True, details
        except Exception as e:
            return False, f"Failed to get element details: {e}"

    async def find_elements_by_text(self, text_to_find: str) -> tuple[bool, str]:
        """Find all elements containing the specified text."""
        try:
            matches = []
            
            # STEP 1: Let the loop run to completion to find ALL possible matches.
            # If labeled_elements is empty, this loop is just skipped, and 'matches' remains empty.
            for i, element in enumerate(self.labeled_elements):
                element_text = await element.evaluate('el => el.innerText')
                if text_to_find.lower() in element_text.lower():
                    matches.append(str(i + 1))
            
            # STEP 2: AFTER the loop is finished, check the results.
            # This logic is now outside the loop and will ALWAYS be executed.
            if matches:
                # This path is taken if one or more matches were found.
                return True, f"Found text '{text_to_find}' in elements: {', '.join(matches)}"
            else:
                # This path is taken if the loop finished and 'matches' is still empty.
                return True, f"Text '{text_to_find}' not found in any labeled element."
                
        except Exception as e:
            # This path is only taken if an error occurs inside the 'try' block.
            return False, f"Failed to search for text: {e}"

    async def get_all_links(self) -> tuple[bool, list | str]:
        """Get a list of all hyperlinks on the page."""
        try:
            page = self._get_page()
            links = await page.evaluate('''() => {
                return Array.from(document.querySelectorAll('a')).map(a => ({
                    text: a.innerText.trim(),
                    href: a.href,
                    label: a.getAttribute('aria-label') || ''
                })).filter(link => link.text || link.label);
            }''')
            return True, links
        except Exception as e:
            return False, f"Failed to get links: {e}"

    async def scroll_page(self, direction: str) -> tuple[bool, str]:
        """Scrolls the page up or down."""
        try:
            page = self._get_page()
            if direction not in ["up", "down"]:
                return False, f"Invalid scroll direction: {direction}"
            scroll_amount = "window.innerHeight" if direction == "down" else "-window.innerHeight"
            await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
            return True, f"Scrolled page {direction}."
        except Exception as e:
            return False, f"Failed to scroll: {e}"

    async def execute_tool(self, tool_command: Dict[str, Any]) -> tuple[bool, str | dict | list]:
        """Execute a tool command."""
        tool = tool_command.get('tool')
        params = tool_command.get('params', {})

        # Handle observation tools
        if tool == 'get_page_content':
            return await self.get_page_content()
        elif tool == 'get_element_details':
            label = params.get('label')
            if not isinstance(label, int):
                return False, f"Invalid label type: {type(label)}. Label must be an integer."
            return await self.get_element_details(label)
        elif tool == 'find_elements_by_text':
            return await self.find_elements_by_text(params.get('text_to_find', ''))
        elif tool == 'get_all_links':
            return await self.get_all_links()

        # Handle basic tools
        if tool == 'click':
            return await self.execute_action({"action_type": "click", "details": {"element_label": params['element']}})
        elif tool == 'type':
            return await self.execute_action({"action_type": "type", "details": {"element_label": params['element'], "text": params['text']}})
        elif tool == 'select':
            return await self.execute_action({"action_type": "select", "details": {"element_label": params['element'], "value": params['value']}})
        elif tool == 'scroll':
            return await self.scroll_page(params['direction'])

        # Handle composite tools
        elif tool == 'perform_google_search':
            query = params.get("query")
            if not query:
                return False, "Google search failed: Missing 'query' parameter."
            return await self._tool_perform_google_search(query)
        elif tool == 'finish':
            return True, f"Task complete: {params['reason']}"
        elif tool == 'pause':
            return True, f"Paused for user: {params['message']}"
        else:
            return False, f"Unknown tool: {tool}"

    # --- Composite Tool Implementation ---
    async def _tool_perform_google_search(self, query: str) -> tuple[bool, str]:
        """
        Executes the composite 'perform_google_search' action.
        This tool knows how to find the search box and search button on its own.
        """
        print(f"[ACTION ENGINE] Performing composite tool: Google Search for '{query}'")
        page = self._get_page()
        try:
            # Step 1: Find the search box and type the query
            search_box_selector = 'textarea[aria-label="Search"]'
            search_box = page.locator(search_box_selector)
            if not await search_box.is_visible(timeout=5000):
                raise Exception("Could not find the Google search box on the page.")
            print(f"  - Typing '{query}' into search box...")
            await search_box.fill(query)
            await page.wait_for_timeout(500)
            # Step 2: Find the search button and click it
            search_button_selector = 'input[aria-label="Google Search"]'
            search_button = page.locator(search_button_selector).first
            if not await search_button.is_visible(timeout=5000):
                raise Exception("Could not find the Google Search button on the page.")
            print("  - Clicking search button...")
            await search_button.click()
            # Step 3: Wait for the results page to load
            await page.wait_for_load_state('networkidle')
            return True, f"Successfully performed Google search for '{query}' and navigated to results."
        except Exception as e:
            error_message = f"Failed to perform Google search: {e}"
            print(f"  - Error: {error_message}")
            return False, error_message
