from typing import Type, List, Dict, Any
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from browser_controller import BrowserController
from working_memory import WorkingMemory
import asyncio
import threading
from queue import Queue

# Initialize BrowserController globally or pass it during agent initialization
# For now, we'll assume it's initialized elsewhere and passed to the tool's run method
# In a real LangChain agent, you'd likely pass this via the tool's constructor or a shared context.
# For this refactoring, we'll make the tools accept a BrowserController instance.

class BrowserTool(BaseTool):
    controller: BrowserController

    class Config:
        arbitrary_types_allowed = True

class MemoryTool(BaseTool):
    memory: WorkingMemory

    class Config:
        arbitrary_types_allowed = True

class MacroTool(BrowserTool):
    """Base class for macro tools."""
    pass

class GoToPageInput(BaseModel):
    url: str = Field(description="The URL to navigate to.")

class GoToPageTool(BrowserTool):
    name: str = "go_to_page"
    description: str = "Navigates the browser to a specified URL."
    args_schema: Type[BaseModel] = GoToPageInput

    def _run(self, url: str) -> str:
        return asyncio.run(self.controller.goto_url(url))

    async def _arun(self, url: str) -> str:
        await self.controller.goto_url(url)
        return f"Navigated to {url}"

class ClickElementInput(BaseModel):
    element_label: int = Field(description="The label of the element to click.")

class ClickElementTool(BrowserTool):
    name: str = "click_element"
    description: str = "Clicks an element identified by its label."
    args_schema: Type[BaseModel] = ClickElementInput

    def _run(self, element_label: int) -> str:
        success, message = asyncio.run(self.controller.execute_action({"action_type": "click", "details": {"element_label": element_label}}))
        return message

    async def _arun(self, element_label: int) -> str:
        success, message = await self.controller.execute_action({"action_type": "click", "details": {"element_label": element_label}})
        return message

class TypeTextInput(BaseModel):
    element_label: int = Field(description="The label of the element to type into.")
    text: str = Field(description="The text to type.")

class TypeTextTool(BrowserTool):
    name: str = "type_text"
    description: str = "Types text into an element identified by its label."
    args_schema: Type[BaseModel] = TypeTextInput

    def _run(self, element_label: int, text: str) -> str:
        success, message = asyncio.run(self.controller.execute_action({"action_type": "type", "details": {"element_label": element_label, "text": text}}))
        return message

    async def _arun(self, element_label: int, text: str) -> str:
        success, message = await self.controller.execute_action({"action_type": "type", "details": {"element_label": element_label, "text": text}})
        return message

class GetElementDetailsInput(BaseModel):
    label: int = Field(description="The label of the element to get details for.")

class GetElementDetailsTool(BrowserTool):
    name: str = "get_element_details"
    description: str = "Gets detailed information about a specific labeled element."
    args_schema: Type[BaseModel] = GetElementDetailsInput

    def _run(self, label: int) -> str:
        success, details = asyncio.run(self.controller.get_element_details(label))
        return str(details)

    async def _arun(self, label: int) -> str:
        success, details = await self.controller.get_element_details(label)
        return str(details)

class TakeScreenshotTool(BrowserTool):
    name: str = "take_screenshot"
    description: str = "Takes a screenshot of the current page and returns its base64 encoded data."

    def _run(self) -> str:
        encoded_image, _ = asyncio.run(self.controller.observe_and_annotate(step=0)) # Step can be managed externally
        return encoded_image

    async def _arun(self) -> str:
        encoded_image, _ = await self.controller.observe_and_annotate(step=0)
        return encoded_image

class ScrollPageInput(BaseModel):
    direction: str = Field(description="The direction to scroll (up or down).")

class ScrollPageTool(BrowserTool):
    name: str = "scroll_page"
    description: str = "Scrolls the page up or down."
    args_schema: Type[BaseModel] = ScrollPageInput

    def _run(self, direction: str) -> str:
        success, message = asyncio.run(self.controller.scroll_page(direction))
        return message

    async def _arun(self, direction: str) -> str:
        success, message = await self.controller.scroll_page(direction)
        return message

class GetPageContentTool(BrowserTool):
    name: str = "get_page_content"
    description: str = "Gets the cleaned text content of the current page."

    def _run(self) -> str:
        success, content = asyncio.run(self.controller.get_page_content())
        return content

    async def _arun(self) -> str:
        success, content = await self.controller.get_page_content()
        return content

class FindElementsByTextInput(BaseModel):
    text_to_find: str = Field(description="The text to find within elements.")

class FindElementsByTextTool(BrowserTool):
    name: str = "find_elements_by_text"
    description: str = "Finds all elements containing the specified text."
    args_schema: Type[BaseModel] = FindElementsByTextInput

    def _run(self, text_to_find: str) -> str:
        success, message = asyncio.run(self.controller.find_elements_by_text(text_to_find))
        return message

    async def _arun(self, text_to_find: str) -> str:
        success, message = await self.controller.find_elements_by_text(text_to_find)
        return message

class GetAllLinksTool(BrowserTool):
    name: str = "get_all_links"
    description: str = "Gets a list of all hyperlinks on the page."

    def _run(self) -> str:
        success, links = asyncio.run(self.controller.get_all_links())
        return str(links)

    async def _arun(self, ) -> str:
        success, links = await self.controller.get_all_links()
        return str(links)

class PerformGoogleSearchInput(BaseModel):
    query: str = Field(description="The search query for Google.")

class PerformGoogleSearchTool(BrowserTool):
    name: str = "perform_google_search"
    description: str = "Performs a Google search and navigates to the results page."
    args_schema: Type[BaseModel] = PerformGoogleSearchInput

    def _run(self, query: str) -> str:
        success, message = asyncio.run(self.controller._tool_perform_google_search(query))
        return message

    async def _arun(self, query: str) -> str:
        success, message = await self.controller._tool_perform_google_search(query)
        return message

class WriteFileInput(BaseModel):
    file_path: str = Field(description="The absolute path to the file to write.")
    content: str = Field(description="The content to write to the file.")

class WriteFileTool(BaseTool):
    name: str = "write_file"
    description: str = "Writes content to a specified file."
    args_schema: Type[BaseModel] = WriteFileInput

    def _run(self, file_path: str, content: str) -> str:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"Successfully wrote to {file_path}"
        except Exception as e:
            return f"Error writing to file {file_path}: {e}"

    async def _arun(self, file_path: str, content: str) -> str:
        return self._run(file_path, content)

class ExecuteScriptInput(BaseModel):
    script_path: str = Field(description="The absolute path to the script to execute.")
    interpreter: str = Field(description="The interpreter to use (e.g., 'python', 'bash').")

class ExecuteScriptTool(BaseTool):
    name: str = "execute_script"
    description: str = "Executes a script using the specified interpreter."
    args_schema: Type[BaseModel] = ExecuteScriptInput

    def _run(self, script_path: str, interpreter: str) -> str:
        try:
            command = f"{interpreter} {script_path}"
            # This is a simplified execution. For true sandboxing, consider Docker.
            process = asyncio.run(asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            ))
            stdout, stderr = asyncio.run(process.communicate())
            
            output = f"""Stdout:
{stdout.decode()}"""
            if stderr:
                output += f"""
Stderr:
{stderr.decode()}"""
            if process.returncode != 0:
                output += f"""
Script exited with code {process.returncode}"""
            return output
        except Exception as e:
            return f"Error executing script {script_path}: {e}"

    async def _arun(self, script_path: str, interpreter: str) -> str:
        return self._run(script_path, interpreter)

class CreateMacroInput(BaseModel):
    objective: str = Field(description="The objective for the new macro. This should be a descriptive sentence, e.g., 'log in to the website'.")

class CreateMacroTool(BrowserTool):
    name: str = "create_macro"
    description: str = "Creates a new macro (a sequence of actions) to be used in the future. Use this when you identify a repetitive task."
    args_schema: Type[BaseModel] = CreateMacroInput

    def _run(self, objective: str) -> str:
        """Use the asynchronous version of the tool."""
        raise NotImplementedError("This tool does not support synchronous execution.")

    async def _arun(self, objective: str) -> str:
        if not self.controller.agent:
            return "Error: The agent is not available to create a macro."

        await self.controller.agent.create_macro(objective)
        return f"Successfully initiated the creation of a macro for the objective: '{objective}'. The new macro will be available for use in the next run."

class NavigateToURLInput(BaseModel):
    url: str = Field(description="The destination URL to navigate to.")

class NavigateToURLTool(BrowserTool):
    name: str = "navigate_to_url"
    description: str = "Navigates to a URL using the most efficient path known. Use this to go to a page that you have likely visited before."
    args_schema: Type[BaseModel] = NavigateToURLInput

    def _run(self, url: str) -> str:
        """Use the asynchronous version of the tool."""
        raise NotImplementedError("This tool does not support synchronous execution.")

    async def _arun(self, url: str) -> str:
        if not self.controller.website_graph:
            return "Error: Website graph is not available."

        current_url = self.controller.page.url
        path = self.controller.website_graph.find_path(current_url, url)

        if not path:
            return f"No known path from {current_url} to {url}. Consider using go_to_page instead."

        print(f"[INFO] Found path to {url}. Executing sequence of {len(path)} actions.")
        for i, action in enumerate(path):
            print(f"  - Action {i+1}/{len(path)}: {action}")
            if action["type"] == "goto":
                await self.controller.goto_url(action["url"])
            elif action["type"] == "click":
                await self.controller.execute_action({
                    "action_type": "click",
                    "details": {"element_label": action["element_label"]}
                })
            await asyncio.sleep(1) # Small delay to allow page to settle

        return f"Successfully navigated to {url} by following a known path."


class AskUserForClarificationInput(BaseModel):
    world_model: str = Field(description="A summary of the agent's understanding of the current state.")
    potential_actions: List[str] = Field(description="A list of potential actions the agent is considering.")

class AskUserForClarificationTool(BaseTool):
    name: str = "ask_user_for_clarification"
    description: str = "Asks the user for clarification when the agent is stuck or has low confidence. Presents the user with the current world model and a list of potential actions to choose from."
    args_schema: Type[BaseModel] = AskUserForClarificationInput
    clarification_request_queue: Queue
    clarification_response_queue: Queue

    def _run(self, world_model: str, potential_actions: List[str]) -> str:
        """Asks the user for clarification and waits for their response."""
        try:
            # Unique identifier for this request
            request_id = threading.get_ident()

            # Package the request
            request = {
                "request_id": request_id,
                "world_model": world_model,
                "potential_actions": potential_actions
            }

            # Send the request to the UI thread
            self.clarification_request_queue.put(request)

            # Wait for the response from the UI thread
            # This will block the agent's execution until the user responds
            response = self.clarification_response_queue.get() # This assumes a 1:1 request/response flow

            if response.get("request_id") != request_id:
                # This is a fallback for a more complex scenario, for now we assume 1:1
                return "Error: Received response for a different request."

            selected_action = response.get("selected_action")

            if selected_action:
                return f"User selected the following action: {selected_action}"
            else:
                return "User did not select an action."

        except Exception as e:
            return f"An error occurred while asking for clarification: {e}"

    async def _arun(self, world_model: str, potential_actions: List[str]) -> str:
        # For now, we'll just use the synchronous implementation
        # In a more advanced setup, we could use asyncio events
        return self._run(world_model, potential_actions)

class UpsertInMemoryInput(BaseModel):
    key: str = Field(description="The key to add or update in the working memory.")
    value: str = Field(description="The value to associate with the key.")

class UpsertInMemoryTool(MemoryTool):
    name: str = "upsert_in_memory"
    description: str = "Adds or updates a key-value pair in the agent's working memory. Use this to remember information that you might need later in the task."
    args_schema: Type[BaseModel] = UpsertInMemoryInput

    def _run(self, key: str, value: str) -> str:
        self.memory.upsert(key, value)
        return f"Successfully upserted value for key '{key}' in working memory."

    async def _arun(self, key: str, value: str) -> str:
        self.memory.upsert(key, value)
        return f"Successfully upserted value for key '{key}' in working memory."

