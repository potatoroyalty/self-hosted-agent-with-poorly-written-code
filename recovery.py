import re
from vision_tools import FindElementWithVisionTool

class ErrorRecovery:
    """
    A framework for proactively recovering from action failures.
    """
    def __init__(self, agent):
        self.agent = agent

    async def recover_from_click_failure(self, element_label: int) -> tuple[bool, str]:
        """
        Attempts to recover from a failed click action.

        This method is invoked when a click action does not produce the expected result
        (e.g., a URL change). It tries to find the element again using vision and
        re-attempts the click.

        Args:
            element_label: The label of the element that was originally clicked.

        Returns:
            A tuple containing a boolean indicating success and a message.
        """
        print(f"[RECOVERY] Attempting to recover from failed click on element {element_label}.")

        # 1. Get details of the failed element to create a search query
        success, details = await self.agent.browser.get_element_details(element_label)
        if not success or not isinstance(details, dict):
            return False, f"Recovery failed: Could not get details for element {element_label}."

        # Construct a descriptive query for the vision model
        element_description = details.get('text', '') or details.get('ariaLabel', '') or details.get('name', '')
        if not element_description:
            element_description = f"the {details.get('tag', 'element')}"

        query = f"the interactive element labeled '{element_description}'"
        print(f"[RECOVERY] Using vision to find element with query: {query}")

        # 2. Find the FindElementWithVisionTool instance from the agent's tools
        vision_tool = next((tool for tool in self.agent.tools if isinstance(tool, FindElementWithVisionTool)), None)

        if not vision_tool:
            return False, "Recovery failed: FindElementWithVisionTool not found."

        # 3. Use the vision tool to find the element again.
        # The tool itself calls observe_and_annotate, so we get a fresh view of the page.
        vision_result = await vision_tool._arun(query=query)

        print(f"[RECOVERY] Vision tool result: {vision_result}")

        # 4. Parse the result to get the new element label
        match = re.search(r'label (\d+)', vision_result)
        if not match:
            return False, f"Recovery failed: Vision tool did not find a matching element. ({vision_result})"

        new_element_label = int(match.group(1))
        print(f"[RECOVERY] Found new element label: {new_element_label}. Re-attempting click.")

        # 5. Get the new element handle from the browser controller's labeled elements
        if not (0 <= new_element_label - 1 < len(self.agent.browser.labeled_elements)):
             return False, f"Recovery failed: Vision tool returned an invalid label {new_element_label}."

        new_element = self.agent.browser.labeled_elements[new_element_label - 1]

        # 6. Perform the click on the new element
        page = self.agent.browser._get_page()
        from_url = page.url
        await new_element.click(timeout=5000)
        try:
            await page.wait_for_load_state('networkidle', timeout=5000)
        except Exception:
            # Ignore timeout errors on recovery, as the page might be slow or SPA-like
            pass
        to_url = page.url

        # 7. Check if the recovery click was successful by looking for a URL change
        if from_url != to_url:
            return True, f"Successfully recovered and clicked element {new_element_label}, navigating to {to_url}."
        else:
            # Even if the URL didn't change, the click might have triggered a dynamic update (e.g., opening a modal).
            # We'll consider this a success for now, as the next observation will see the new state.
            return True, f"Recovery click on element {new_element_label} was executed, but the URL did not change."
