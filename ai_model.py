import ollama
import re
import json
import sys
from constitution import AGENT_CONSTITUTION, ACTION_CONSTITUTION, SUPERVISOR_CONSTITUTION
from typing import Any, List, Mapping, Optional

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.outputs import ChatResult, ChatGeneration, Generation
from pydantic import Field
from ollama import ResponseError, RequestError

class OllamaChatModel(BaseChatModel):
    model_name: str
    async_client: ollama.AsyncClient = Field(default_factory=ollama.AsyncClient)

    def __init__(self, model_name: str, **kwargs: Any):
        super().__init__(model_name=model_name, **kwargs)

    @property
    def _llm_type(self) -> str:
        return "ollama-chat"

    def _generate(self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        raise NotImplementedError("OllamaChatModel does not support synchronous calls.")

    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        ollama_messages = []
        for message in messages:
            if isinstance(message, HumanMessage):
                content = message.content
                images = []
                if isinstance(content, list):
                    # Handle multimodal content
                    text_content = ""
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "text":
                            text_content = item.get("text", "")
                        elif isinstance(item, dict) and item.get("type") == "image_url":
                            image_url = item.get("image_url", {}).get("url", "")
                            if image_url.startswith("data:image/"):
                                # Extract base64 part
                                images.append(image_url.split(",")[1])
                else:
                    text_content = content

                ollama_messages.append({"role": "user", "content": text_content, "images": images})
            elif isinstance(message, AIMessage):
                ollama_messages.append({"role": "assistant", "content": message.content})
            # Add other message types if needed
        try:
            response_content = ""
            async for chunk in await self.async_client.chat(
                model=self.model_name,
                messages=ollama_messages,
                stream=True,
                options=kwargs.get("options", {})
            ):
                content_chunk = chunk['message']['content']
                response_content += content_chunk
                if run_manager:
                    await run_manager.on_llm_new_token(content_chunk)

            return ChatResult(generations=[ChatGeneration(message=AIMessage(content=response_content))])
        except ResponseError as e:
            print(f"[ERROR] Ollama API Error: {e.error}")
            # Handle the error appropriately, maybe return a default response
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content=""))])
        except RequestError as e:
            print(f"[ERROR] Ollama Request Error: {e.error}")
            # Handle the error appropriately
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content=""))])
        except Exception as e:
            print(f"[ERROR] An unexpected error occurred: {e}")
            # Handle the error appropriately
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content=""))])


    @property
    def _identifying_params(self) -> Mapping[str, Any]:
        return {"model_name": self.model_name}

class MockOllamaChatModel(BaseChatModel):
    """A mock model to be used in test environments where Ollama is not available."""
    def _generate(self, messages: List[BaseMessage], stop: Optional[List[str]] = None, run_manager: Optional[CallbackManagerForLLMRun] = None, **kwargs: Any) -> ChatResult:
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content="Mocked response: Feature disabled in test environment."))])

    async def _agenerate(self, messages: List[BaseMessage], stop: Optional[List[str]] = None, run_manager: Optional[CallbackManagerForLLMRun] = None, **kwargs: Any) -> ChatResult:
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content="Mocked response: Feature disabled in test environment."))])

    @property
    def _llm_type(self) -> str:
        return "mock-ollama-chat"

    @property
    def _identifying_params(self) -> Mapping[str, Any]:
        return {"model_name": "mock"}

class AIModel:
    def __init__(self, main_model_name='mixtral:latest', supervisor_model_name='mixtral:latest', fast_model_name='phi3', vision_model_name='gemma:7b', scripter_model_name=None):
        self.main_model_name = main_model_name
        self.fast_model_name = fast_model_name
        self.supervisor_model_name = supervisor_model_name
        self.vision_model_name = vision_model_name
        self.scripter_model_name = scripter_model_name if scripter_model_name else supervisor_model_name
        
        self.agent_constitution = AGENT_CONSTITUTION
        self.action_constitution = ACTION_CONSTITUTION

        # If not in a virtual environment, proceed with the full setup.
        self.main_model = OllamaChatModel(model_name=self.main_model_name)
        self.fast_model = OllamaChatModel(model_name=self.fast_model_name)
        self.supervisor_model = OllamaChatModel(model_name=self.supervisor_model_name)
        self.vision_model = OllamaChatModel(model_name=self.vision_model_name)
        self.scripter_model = OllamaChatModel(model_name=self.scripter_model_name)

        try:
            print("[INFO] Performing full Ollama model check...")
            # Check if the model exists locally
            response = ollama.list()
            # Safely access the 'models' key, defaulting to an empty list if not found.
            models_list = response.get('models', [])
            # Safely get model names using .get() and filter out any None results
            # to prevent errors from malformed API responses.
            local_models = [m.get('name') for m in models_list if isinstance(m, dict)]
            local_models = [name for name in local_models if name]
            required_models = [self.main_model_name, self.supervisor_model_name, self.fast_model_name, self.vision_model_name, self.scripter_model_name]
            for model in required_models:
                 if model not in local_models:
                    print(f"[INFO] Model '{model}' not found locally. Attempting to pull it now...")
                    try:
                        # This will display a progress bar in the console
                        ollama.pull(model)
                        print(f"[SUCCESS] Model '{model}' pulled successfully.")
                    except ResponseError as e:
                        print(f"[ERROR] Ollama API Error while pulling model '{model}': {e.error}")
                        raise
                    except RequestError as e:
                        print(f"[ERROR] Ollama Request Error while pulling model '{model}': {e.error}")
                        raise
                    except Exception as pull_error:
                        print(f"[ERROR] Failed to pull model '{model}'.")
                        print(f"Please ensure Ollama is running and you have an internet connection.")
                        print(f"You can also try pulling it manually: 'ollama pull {model}'")
                        raise ValueError(f"Required model '{model}' could not be pulled.") from pull_error
        except ResponseError as e:
            print(f"[ERROR] Ollama API Error: {e.error}")
            print("[INFO] Please ensure the Ollama application is running and accessible.")
            raise
        except RequestError as e:
            print(f"[ERROR] Ollama Request Error: {e.error}")
            print("[INFO] Please ensure the Ollama application is running and accessible.")
            raise
        except Exception as e:
            print(f"[ERROR] Failed to connect to Ollama or list models: {e}")
            print("[INFO] Please ensure the Ollama application is running and accessible.")
            raise

    async def generate_and_set_dynamic_constitutions(self, objective: str):
        """
        Uses the supervisor model to generate and set dynamic constitutions based on the objective.
        """
        prompt = f"""
        {SUPERVISOR_CONSTITUTION}

        # User's Objective
        "{objective}"
        """
        print("[INFO] Generating dynamic constitution...")
        messages = [HumanMessage(content=prompt)]

        try:
            response = await self.supervisor_model.agenerate(messages=[messages])
            response_text = response.generations[0][0].message.content

            json_match = re.search(r"```json\s*({{.*?}})\s*```|({{.*}})", response_text, re.DOTALL)
            if not json_match:
                raise ValueError("No valid JSON block found in the supervisor's response.")

            json_str = json_match.group(1) or json_match.group(2)
            constitutions = json.loads(json_str.strip())

            if "agent_constitution" in constitutions and "action_constitution" in constitutions:
                self.agent_constitution = constitutions["agent_constitution"]
                self.action_constitution = constitutions["action_constitution"]
                print("[INFO] Dynamic constitutions generated and set successfully.")
            else:
                raise ValueError("Generated constitution is missing required keys.")

        except Exception as e:
            print(f"[ERROR] Failed to generate dynamic constitutions: {e}. Falling back to default.")
            # Fallback to default constitutions
            self.agent_constitution = AGENT_CONSTITUTION
            self.action_constitution = ACTION_CONSTITUTION


    async def get_contextual_overview(self, encoded_image: str) -> str:
        """
        Given a screenshot (no labels), return a one-sentence summary of the page's main state.
        This focuses on identifying the most prominent feature, like a pop-up.
        """
        prompt = (
            "Based on this screenshot, provide a concise, one-sentence summary of the page's main state. "
            "Focus only on the most prominent visual element. For example, if there is a pop-up, "
            "describe the pop-up, not the page behind it. Do not speculate on actions. Just describe what you see."
        )
        print("[CONTEXTUAL OVERVIEW]")
        
        messages = [
            HumanMessage(
                content=[
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}"}},
                ]
            )
        ]
        response = await self.vision_model.agenerate(messages=[messages])
        return response.generations[0][0].message.content.strip()

    async def analyze_layout(self, encoded_image: str, question: str) -> str:
        """
        Given a screenshot and a question about the layout, return a textual answer.
        """
        prompt = (
            f"You are a visual analyst. Based on the provided screenshot, answer the following question about the page's layout and structure.\n\n"
            f"Question: \"{question}\"\n\n"
            f"Provide a direct and concise answer."
        )
        print(f"[LAYOUT ANALYSIS] Question: {question}")

        messages = [
            HumanMessage(
                content=[
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}"}},
                ]
            )
        ]
        response = await self.vision_model.agenerate(messages=[messages])
        return response.generations[0][0].message.content.strip()

    async def get_page_description(self, encoded_image, labeled_elements):
        element_texts = []
        for i, element in enumerate(labeled_elements):
            try:
                text = await element.inner_text()
                clean_text = ' '.join(text.strip().split())
                if clean_text:
                    element_texts.append(f'Label {i+1}: "{clean_text}"')
            except Exception:
                continue

        elements_list_str = "\n".join(element_texts)

        prompt = f"""
Based on the screenshot, what is the page's main state (e.g., "cookie pop-up", "login form")?
Also, list the text from the most important labeled elements below that a user would interact with.

Labeled elements provided:
{elements_list_str}
        """
        print("[PAGE DESCRIPTION]")
        messages = [
            HumanMessage(
                content=[
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}"}},
                ]
            )
        ]
        response = await self.vision_model.agenerate(messages=[messages])
        return response.generations[0][0].message.content.strip()


    async def validate_action(self, objective: str, page_summary: str, proposed_action_json: dict) -> bool:
        """
        Uses a fast model to perform a "sanity check" on the proposed action.
        """
        prompt = f"""
        You are a logical validator. Your answer must be a single word: either 'true' or 'false'.
        - Main Objective: "{objective}"
        - Current page summary: "{page_summary}"
        - Proposed Action: {json.dumps(proposed_action_json)}

        Based on the objective and the page summary, is the proposed action a logical next step?
        """
        messages = [
            HumanMessage(content=prompt)
        ]
        response = await self.fast_model.agenerate(messages=[messages])
        decision = response.generations[0][0].message.content.strip().lower()
        print(f"[VALIDATION] AI proposed action: {json.dumps(proposed_action_json)}. Validator response: {decision}")
        return "true" in decision

    async def get_self_critique(self, session_log):
        prompt = f"""
        You are a Self-Correction AI. You will be given the log of a web agent's session.
        Your job is to identify the single biggest mistake the agent made.
        The session log is a JSON object that contains a history of reflections, world models, plans, and action results.
        The 'action_result' contains the tool that was used, the parameters, and the result, which may include an error.

        First, analyze the log to find the most significant error or inefficiency.

        Second, determine if the error was due to the agent's flawed reasoning or a limitation of the available tools.
        
        - If the error is due to the agent's reasoning, formulate a single, concise, one-sentence directive for the *agent*.
          Example:
          - Mistake: The agent tried to type into an element that wasn't a text box.
          - Directive: Always use the `find_text` tool to confirm an element is a text input field before typing into it.

        - If the error is due to a tool's limitation (e.g., a tool consistently fails or is not suitable for a specific task), formulate a single, concise, one-sentence directive for the *developer*. This directive should start with "Directive for developer:".
          Example:
          - Mistake: The `click_element` tool repeatedly failed on a dynamic JavaScript button.
          - Directive for developer: The click_element tool is ineffective on dynamic buttons. Consider creating a new javascript_click tool that executes a click via a JS script.

        Here is the session log:
        <session_log>
        {session_log}
        </session_log>
        
        Based on the log, what is the single most important directive for the agent's next run or for the developer?
        """
        messages = [
            HumanMessage(content=prompt)
        ]
        response = await self.fast_model.agenerate(messages=[messages])
        return response.generations[0][0].message.content.strip()

    async def get_strategic_plan(self, objective, history, page_description, self_critique):
        """First step of the cognitive cycle - generates high-level plan based on structured page data."""
        prompt = f"""
        {self.agent_constitution}

        # Main Objective
        Your overall objective is: "{objective}".
        
        # Critical Self-Critique from Last Run
        A previous version of yourself made a mistake. Here is a critical instruction: "{self_critique}".

        # Factual Description of the Current Screen (from preprocessor)
        {page_description}

        # History of Past Steps
        <history>{history}</history>

        # Your Task
        Follow your cognitive cycle. Respond with a single JSON object containing "reflection", "world_model", and "plan".
        """
        
        messages = [
            HumanMessage(content=prompt)
        ]
        text_model = self.main_model # if "llava" not in self.main_model_name else self.fast_model
        
        response = await text_model.agenerate(messages=[messages])
        response_text = response.generations[0][0].message.content

        try:
            json_match = re.search(r"```json\s*({{.*?}})\s*```|({{.*}})", response_text, re.DOTALL)
            if not json_match:
                raise ValueError("No valid JSON block found in the AI's response for the plan.")
            json_str = json_match.group(1) or json_match.group(2)
            return json.loads(json_str.strip())
        except Exception as e:
            print(f"[ERROR] Failed to parse strategic plan: {e}")
            return {
                "reflection": "Error parsing the strategic plan.",
                "world_model": "Failed to generate valid plan. Need to retry.",
                "plan": ["Re-evaluate the page"],
            }

    async def get_tactical_action(self, plan, encoded_image, page_description):
        """Second step of the cognitive cycle - generates specific action based on plan."""
        prompt = f"""
        {self.action_constitution}

        # High-Level Plan
        {json.dumps(plan, indent=2)}

        # Current Screen Description (for context)
        {page_description}

        # Your Task
        Generate a single, executable JSON action object for the FIRST step of the plan.
        If your confidence_score for the primary action is below 0.7, you MUST also include a 'potential_actions' key, which is a list of up to 3 other distinct and reasonable actions you could take.
        """

        messages = [
            HumanMessage(
                content=[
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}"}},
                ]
            )
        ]
        response = await self.vision_model.agenerate(messages=[messages])
        response_text = response.generations[0][0].message.content

        try:
            json_match = re.search(r"```json\s*({{.*?}})\s*```|({{.*}})", response_text, re.DOTALL)
            if not json_match:
                raise ValueError("No valid JSON action found")
            json_str = json_match.group(1) or json_match.group(2)
            action_json = json.loads(json_str.strip())

            # Ensure potential_actions is a list if it exists, otherwise default to empty list
            if 'potential_actions' in action_json and not isinstance(action_json['potential_actions'], list):
                action_json['potential_actions'] = []

            return action_json

        except Exception as e:
            print(f"[ERROR] Failed to parse tactical action: {e}")
            return {
                "tool": "pause_for_user",
                "params": {"instruction_to_user": "Failed to generate valid action. Will retry."},
                "confidence_score": 0.0,
                "thought": "I encountered an error while trying to parse the tactical action from my own response.",
                "potential_actions": []
            }

    async def generate_macro_script(self, objective: str, tool_definitions: str, tool_name: str, class_name: str) -> str:
        """
        Generates a Python script for a macro tool based on an objective.
        """
        prompt = f"""
You are a script-generating AI. Your task is to create a Python script that defines a new LangChain tool for accomplishing a specific objective. The tool should be a class that inherits from `MacroTool`.

The script should contain a sequence of calls to the basic tools available to the agent.

Here are the available basic tools:
{tool_definitions}

Objective: {objective}

The class name for the tool must be `{class_name}`.
The tool name (the `name` attribute of the class) must be `{tool_name}`.

You must respond with only the Python script, enclosed in ```python ... ```.
Do not include any other text or explanations.
The script should define a class that inherits from `MacroTool` and implements the `_arun` method.
The `_arun` method should be a coroutine (async def).

Generated Python script:
"""
        messages = [
            HumanMessage(content=prompt)
        ]
        response = await self.scripter_model.agenerate(messages=[messages])
        response_text = response.generations[0][0].message.content.strip()

        # Extract the python script from the response
        match = re.search(r"```python\s*(.*?)\s*```", response_text, re.DOTALL)
        if match:
            return match.group(1)
        else:
            # Fallback to returning the whole response, but try to clean it
            if response_text.startswith("```python"):
                response_text = response_text[len("```python"):]
            if response_text.endswith("```"):
                response_text = response_text[:-len("```")]
            return response_text

    async def generate_script_from_recording(self, recorded_events: list, objective: str, tool_name: str, class_name: str, tool_definitions: str) -> str:
        """
        Generates a Python script for a macro tool based on a user's recording and objective.
        """
        # Convert recorded events to a more readable format for the prompt
        formatted_events = "\n".join([f"- {event['type'].upper()} on element '{event['selector']}'" + (f" with value '{event['value']}'" if 'value' in event and event['value'] else "") for event in recorded_events])

        prompt = f"""
You are a script-generating AI. Your task is to create a Python script that defines a new LangChain tool. This new tool will automate a task based on a provided recording of user actions and a high-level objective.

The user performed the following actions:
<recording>
{formatted_events}
</recording>

The user's objective for this script is: "{objective}"

Based on the recording and the objective, generate a Python script that creates a new tool class named `{class_name}` which inherits from `MacroTool`. The tool's `name` attribute must be `{tool_name}`.

The script should contain a sequence of calls to the basic tools available to the agent. Here are the available tools:
{tool_definitions}

Important Rules:
1.  Analyze the user's recorded actions and generalize them. Do not simply copy the selectors one-to-one, as they might be brittle. Instead, use tools like `find_elements_by_text` when appropriate to make the script more robust.
2.  The generated script must only contain the Python code for the tool, enclosed in ```python ... ```.
3.  The class must implement the `_arun` method as a coroutine (async def).

Generated Python script:
"""
        messages = [
            HumanMessage(content=prompt)
        ]
        response = await self.scripter_model.agenerate(messages=[messages])
        response_text = response.generations[0][0].message.content.strip()

        # Extract the python script from the response
        match = re.search(r"```python\s*(.*?)\s*```", response_text, re.DOTALL)
        if match:
            return match.group(1)
        else:
            if response_text.startswith("```python"):
                response_text = response_text[len("```python"):]
            if response_text.endswith("```"):
                response_text = response_text[:-len("```")]
            return response_text
