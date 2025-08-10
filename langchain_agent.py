from typing import Type, List, Dict, Any
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from browser_controller import BrowserController
import asyncio

# Initialize BrowserController globally or pass it during agent initialization
# For now, we'll assume it's initialized elsewhere and passed to the tool's run method
# In a real LangChain agent, you'd likely pass this via the tool's constructor or a shared context.
# For this refactoring, we'll make the tools accept a BrowserController instance.

class BrowserTool(BaseTool):
    controller: BrowserController

    class Config:
        arbitrary_types_allowed = True

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
