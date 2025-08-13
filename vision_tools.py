import asyncio
from typing import Type, TYPE_CHECKING
from langchain.tools import BaseTool
from pydantic import Field, BaseModel
from ai_model import AIModel

if TYPE_CHECKING:
    from browser_controller import BrowserController

class FindElementWithVisionSchema(BaseModel):
    query: str = Field(description="A clear, natural language description of the element to find. For example, 'the search bar' or 'the button that says Log In'.")

class FindElementWithVisionTool(BaseTool):
    name: str = "find_element_with_vision"
    description: str = "Use this tool to find a single specific element on the page. It takes a natural language query and uses a combination of text-based filtering and visual analysis to locate the element. It returns the element's label, which can then be used by other tools like 'click' or 'type'."
    args_schema: Type[BaseModel] = FindElementWithVisionSchema
    browser: "BrowserController"
    ai_model: AIModel

    def _run(self, query: str):
        """Use the asynchronous version of the tool."""
        raise NotImplementedError("This tool does not support synchronous execution.")

    async def _arun(self, query: str):
        """
        Orchestrates the micro-vision loop:
        1. Get SnapDOM from the browser.
        2. Perform text-based filtering to find candidates.
        3. (Next Step) Get image tiles for candidates.
        4. (Next Step) Use the vision model to identify the best candidate.
        5. (Next Step) Return the label of the best candidate.
        """
        print(f"[Vision Tool] Finding element with query: '{query}'")

        # 1. Get SnapDOM from the browser
        snapdom = await self.browser.get_snapdom()
        if not snapdom or "labeledElements" not in snapdom:
            return "Could not retrieve page content for analysis. The page might be empty or failed to load."

        labeled_elements = snapdom["labeledElements"]

        # 2. Perform text-based filtering to find candidates
        # A simple scoring system to find the best candidates
        candidates = []
        for element in labeled_elements:
            score = 0
            text_to_check = (element.get("text", "") + " " + element.get("attributes", {}).get("aria-label", "")).lower()

            # Basic keyword matching
            if query.lower() in text_to_check:
                score += 2

            # Heuristics based on query terms
            if "button" in query.lower() and (element.get("tag") == "button" or element.get("role") == "button"):
                score += 1
            if "link" in query.lower() and (element.get("tag") == "a" or element.get("role") == "link"):
                score += 1
            if ("input" in query.lower() or "field" in query.lower() or "box" in query.lower()) and (element.get("tag") == "input" or element.get("tag") == "textarea"):
                score += 1

            if score > 0:
                # The 'index' from preprocessor.js corresponds to the label in browser_controller
                candidates.append({"label": element["index"], "score": score, "text": element.get("text", "")})

        if not candidates:
            return "No suitable elements found based on the text query. Try a different query or use full-page analysis."

        # Sort candidates by score in descending order
        candidates.sort(key=lambda x: x["score"], reverse=True)

        # Handle edge cases for candidate numbers
        if len(candidates) > 5:
            return f"Found too many ({len(candidates)}) potential candidates. Please provide a more specific query."

        top_candidates = candidates[:5]

        # 3. Get image tiles for candidates
        candidate_data = []
        for candidate in top_candidates:
            label = candidate["label"]
            screenshot = await self.browser.get_element_screenshot(label)
            if screenshot:
                candidate_data.append({
                    "label": label,
                    "text": candidate["text"],
                    "image": screenshot
                })

        if not candidate_data:
            return "Could not capture images for any of the candidate elements."

        # 4. Use the vision model to identify the best candidate
        prompt = f"""
Your goal is to identify the single correct UI element from a list of candidates that best matches the user's query.
User Query: "{query}"

Here are the candidates. Each has a label, its visible text, and an image of the element itself.
Review the images and select the one that is the best fit for the query.

**If multiple elements seem to match, prioritize the one that is most visually prominent or appears to be the main interactive element for the query's context.**

Respond with a single JSON object with a single key "label" containing the numeric label of the best element. Example: {{"label": 2}}

Candidates:
"""

        for c in candidate_data:
            prompt += f"- Label: {c['label']}, Text: \"{c['text']}\"\n"

        # Prepare multimodal message for LLaVA
        from langchain_core.messages import HumanMessage
        message_content = [{"type": "text", "text": prompt}]
        for c in candidate_data:
            message_content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{c['image']}"}})

        messages = [HumanMessage(content=message_content)]

        # Use the vision model for this targeted task
        response = await self.ai_model.vision_model.agenerate(messages=[messages])
        response_text = response.generations[0].message.content.strip()

        print(f"[Vision Tool] Model response: {response_text}")

        # 5. Parse the response and return the label
        import re
        import json
        try:
            # Use regex to find the JSON block
            json_match = re.search(r'\{.*?\}', response_text)
            if json_match:
                json_str = json_match.group(0)
                parsed_json = json.loads(json_str)
                final_label = parsed_json.get("label")
                if final_label:
                    print(f"[Vision Tool] Successfully identified element with label: {final_label}")
                    return f"Successfully found element with label {final_label}"

            # Fallback for non-JSON numeric response
            numeric_match = re.search(r'\d+', response_text)
            if numeric_match:
                final_label = numeric_match.group(0)
                print(f"[Vision Tool] Successfully identified element with label: {final_label}")
                return f"Successfully found element with label {final_label}"

            return f"Could not determine the correct element from the model's response: {response_text}"
        except (json.JSONDecodeError, KeyError) as e:
            return f"Error parsing model response: {e}. Raw response: {response_text}"

class AnalyzeVisualLayoutSchema(BaseModel):
    question: str = Field(description="A high-level question about the page's layout or structure. For example: 'Is the main content a feed of articles?', 'Is there a two-column layout?', or 'Where is the primary navigation bar located on the screen?'.")

class AnalyzeVisualLayoutTool(BaseTool):
    name: str = "analyze_visual_layout"
    description: str = "Use this tool to ask high-level questions about the page's structure and layout. It takes a natural language question and uses the vision model to answer it based on a screenshot of the current page. This is useful for understanding the overall layout, such as identifying navigation bars, main content areas, or the number of columns."
    args_schema: Type[BaseModel] = AnalyzeVisualLayoutSchema
    browser: "BrowserController"
    ai_model: AIModel

    def _run(self, question: str):
        """Use the asynchronous version of the tool."""
        raise NotImplementedError("This tool does not support synchronous execution.")

    async def _arun(self, question: str):
        """
        1. Get a screenshot of the current page.
        2. Use the vision model to answer the question about the layout.
        3. Return the model's answer.
        """
        print(f"[Vision Tool] Analyzing layout with question: '{question}'")

        # 1. Get a screenshot of the current page
        try:
            screenshot_b64 = await self.browser.capture_screenshot()
        except Exception as e:
            return f"Error capturing screenshot: {e}"

        if not screenshot_b64:
            return "Could not capture a screenshot of the page."

        # 2. Use the vision model to answer the question
        # This calls a new method on the AIModel that we will create in the next step.
        try:
            answer = await self.ai_model.analyze_layout(screenshot_b64, question)
            print(f"[Vision Tool] Model response: {answer}")
            return answer
        except Exception as e:
            return f"An error occurred while analyzing the layout: {e}"
