import os
import json
import re
from datetime import datetime
import importlib.util
from unittest.mock import MagicMock
from ai_model import AIModel
from browser_controller import BrowserController
from website_graph import WebsiteGraph
from working_memory import WorkingMemory
from strategy_manager import StrategyManager, StrategyCallbackHandler
from langchain_agent import (
    BrowserTool, MacroTool, MemoryTool,
    GoToPageTool, ClickElementTool, TypeTextTool, GetElementDetailsTool,
    TakeScreenshotTool, ScrollPageTool, GetPageContentTool, FindElementsByTextTool,
    GetAllLinksTool, PerformGoogleSearchTool, WriteFileTool, ExecuteScriptTool,
    CreateMacroTool, NavigateToURLTool, UpsertInMemoryTool, AskUserForClarificationTool,
    FinishTool
)
from vision_tools import FindElementWithVisionTool, AnalyzeVisualLayoutTool
import config

# Pydantic's model_rebuild() is used to resolve forward references
# in type hints. This is necessary because FindElementWithVisionTool
# and AnalyzeVisualLayoutTool have a forward reference to BrowserController.
# By calling model_rebuild() after all relevant classes are imported,
# we ensure that Pydantic can correctly link the classes together.
FindElementWithVisionTool.model_rebuild()
AnalyzeVisualLayoutTool.model_rebuild()

class WebAgent:
    def __init__(self, objective, start_url, model_name=config.MAIN_MODEL, supervisor_model_name=config.SUPERVISOR_MODEL, fast_model_name=config.FAST_MODEL, vision_model_name=config.VISION_MODEL, memory_file=config.MEMORY_FILE, critique_file=config.CRITIQUE_FILE, max_steps=config.MAX_STEPS, clarification_request_queue=None, clarification_response_queue=None, paused_event=None, stopped_event=None, socketio=None, testing=False):
        self.objective = objective
        self.start_url = start_url
        self.clarification_request_queue = clarification_request_queue
        self.clarification_response_queue = clarification_response_queue
        self.paused_event = paused_event
        self.stopped_event = stopped_event
        self.socketio = socketio
        self.testing = testing
        self.memory_file = memory_file
        self.critique_file = critique_file
        self.memory = []
        self.working_memory = WorkingMemory()
        self.max_steps = max_steps
        self.self_critique = "No critiques from previous runs."
        self.last_action_result = "No action has been taken yet."
        
        self.run_folder = f"runs/{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"

        self.website_graph = WebsiteGraph(graph_file_path=config.GRAPH_FILE_PATH)
        self.strategy_manager = StrategyManager(config.STRATEGY_FILE_PATH)
        self.strategy_callback_handler = StrategyCallbackHandler()
        if self.testing:
            print("[INFO] Testing mode enabled. Using mock AI model.")
            self.ai_model = MagicMock()
        else:
            self.ai_model = AIModel(main_model_name=model_name, supervisor_model_name=supervisor_model_name, fast_model_name=fast_model_name, vision_model_name=vision_model_name)
        self.browser = BrowserController(run_folder=self.run_folder, agent=self, website_graph=self.website_graph, socketio=self.socketio, testing=self.testing)

        # Added robust encoding and error handling
        if os.path.exists(self.memory_file):
            print(f"[INFO] Loading long-term memory from {self.memory_file}")
            with open(self.memory_file, 'r', encoding='utf-8', errors='ignore') as f:
                self.memory = f.read().splitlines()
        
        # Added robust encoding and error handling
        if os.path.exists(self.critique_file):
            print(f"[INFO] Loading self-critique from {self.critique_file}")
            with open(self.critique_file, 'r', encoding='utf-8', errors='ignore') as f:
                self.self_critique = f.read().strip()

        # Initialize LangChain tools
        self.tools = [
            GoToPageTool(controller=self.browser),
            NavigateToURLTool(controller=self.browser),
            ClickElementTool(controller=self.browser),
            TypeTextTool(controller=self.browser),
            GetElementDetailsTool(controller=self.browser),
            TakeScreenshotTool(controller=self.browser),
            ScrollPageTool(controller=self.browser),
            GetPageContentTool(controller=self.browser),
            FindElementsByTextTool(controller=self.browser),
            GetAllLinksTool(controller=self.browser),
            PerformGoogleSearchTool(controller=self.browser),
            WriteFileTool(),
            ExecuteScriptTool(),
            CreateMacroTool(controller=self.browser),
            UpsertInMemoryTool(memory=self.working_memory),
            FinishTool()
        ]

        if not self.testing:
            self.tools.extend([
                FindElementWithVisionTool(browser=self.browser, ai_model=self.ai_model),
                AnalyzeVisualLayoutTool(browser=self.browser, ai_model=self.ai_model),
            ])

        if self.clarification_request_queue and self.clarification_response_queue:
            self.tools.append(AskUserForClarificationTool(
                clarification_request_queue=self.clarification_request_queue,
                clarification_response_queue=self.clarification_response_queue
            ))

        # Load dynamic tools
        self.load_dynamic_tools()

    def get_tool_definitions(self):
        return "\n".join([f"- {tool.name}: {tool.description}" for tool in self.tools])

    async def create_macro(self, objective: str):
        # Sanitize objective to create a valid file/class name
        sanitized_objective = re.sub(r'\s+', '_', objective)
        sanitized_objective = re.sub(r'\W+', '', sanitized_objective).lower()
        tool_name = f"{sanitized_objective}_macro"
        class_name = f"{sanitized_objective.replace('_', ' ').title().replace(' ', '')}MacroTool"

        macros_dir = "macros"
        if not os.path.exists(macros_dir):
            os.makedirs(macros_dir)

        module_path = os.path.join(macros_dir, f"{tool_name}.py")

        tool_definitions = self.get_tool_definitions()
        script_content = await self.ai_model.generate_macro_script(objective, tool_definitions, tool_name, class_name)

        if script_content:
            # The generated script needs access to the base classes and tools
            script_header = "from langchain_agent import MacroTool, GoToPageTool, ClickElementTool, TypeTextTool, GetElementDetailsTool, TakeScreenshotTool, ScrollPageTool, GetPageContentTool, FindElementsByTextTool, GetAllLinksTool, PerformGoogleSearchTool, WriteFileTool, ExecuteScriptTool\n"
            script_content = script_header + script_content

            with open(module_path, 'w', encoding='utf-8') as f:
                f.write(script_content)
            print(f"[INFO] Created new macro script: {module_path}")

            dynamic_tools_path = config.DYNAMIC_TOOLS_PATH
            if os.path.exists(dynamic_tools_path):
                with open(dynamic_tools_path, 'r', encoding='utf-8') as f:
                    tools_config = json.load(f)
            else:
                tools_config = []

            # Remove existing tool with the same name if any
            tools_config = [t for t in tools_config if t['name'] != tool_name]

            tools_config.append({
                "name": tool_name,
                "module_path": module_path,
                "class_name": class_name
            })

            with open(dynamic_tools_path, 'w', encoding='utf-8') as f:
                json.dump(tools_config, f, indent=4)

            print(f"[INFO] Updated dynamic tools config with new macro: {tool_name}")

            # Reload dynamic tools
            self.load_dynamic_tools()
        else:
            print("[ERROR] Failed to generate macro script.")

    def load_dynamic_tools(self):
        dynamic_tools_path = config.DYNAMIC_TOOLS_PATH
        if os.path.exists(dynamic_tools_path):
            with open(dynamic_tools_path, 'r', encoding='utf-8') as f:
                dynamic_tools_config = json.load(f)

            for tool_config in dynamic_tools_config:
                tool_name = tool_config["name"]
                module_path = tool_config["module_path"]
                class_name = tool_config["class_name"]

                try:
                    spec = importlib.util.spec_from_file_location(tool_name, module_path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    ToolClass = getattr(module, class_name)
                    
                    # If the tool requires a browser controller, pass it
                    if issubclass(ToolClass, BrowserTool):
                        self.tools.append(ToolClass(controller=self.browser))
                    else:
                        self.tools.append(ToolClass())
                    print(f"[INFO] Dynamically loaded tool: {tool_name}")
                except Exception as e:
                    print(f"[ERROR] Failed to load dynamic tool {tool_name}: {e}")

    async def run(self):
        await self.browser.start()

        # Check for special 'run_macro' objective
        if self.objective.startswith("run_macro:"):
            tool_name = self.objective.split(":")[1]
            tool_to_execute = next((t for t in self.tools if t.name == tool_name), None)
            if tool_to_execute:
                print(f"[INFO] Directly executing macro: {tool_name}")
                # Macros might need to navigate to a starting URL
                await self.browser.goto_url(self.start_url)
                # The 'arun' method of a MacroTool is expected to be a coroutine
                await tool_to_execute.arun()
                print(f"[INFO] Macro {tool_name} finished execution.")
            else:
                print(f"[ERROR] Macro tool '{tool_name}' not found.")
            return # End the run after executing the macro

        await self.ai_model.generate_and_set_dynamic_constitutions(self.objective)
        await self.browser.goto_url(self.start_url)

        # Try to execute a saved strategy if one exists
        domain = self.strategy_manager.get_domain(self.start_url)
        strategy = self.strategy_manager.find_strategy(domain, self.objective)

        if strategy:
            print(f"[INFO] Found a strategy for domain '{domain}' and objective '{self.objective}'. Executing...")
            # Ensure we start from the correct URL, as some strategies might assume it.
            await self.browser.goto_url(self.start_url)

            for action in strategy:
                if self.stopped_event and self.stopped_event.is_set():
                    print("[INFO] Stop event received during strategy execution. Halting.")
                    break

                tool_name = action.get("tool_name")
                tool_input = action.get("tool_input")

                tool_to_execute = next((t for t in self.tools if t.name == tool_name), None)
                if tool_to_execute:
                    try:
                        print(f"[STRATEGY] Executing action: {tool_name} with input {tool_input}")
                        # We need to pass the arguments correctly to the tool's 'arun' method
                        result = await tool_to_execute.arun(**tool_input)
                        print(f"[STRATEGY] Action finished with result: {result}")
                    except Exception as e:
                        print(f"[ERROR] Error executing action from strategy: {e}")
                        # If an action fails, we stop the strategy execution.
                        break
                else:
                    print(f"[ERROR] Tool '{tool_name}' from strategy not found.")
                    break

            print("[INFO] Strategy execution finished.")
            # The run is considered complete after executing a successful strategy.
            return

        # Clear any recorded actions from a previous run
        self.strategy_callback_handler.clear_actions()

        # Main loop
        for i in range(self.max_steps):
            if self.stopped_event and self.stopped_event.is_set():
                print("[INFO] Stop event received. Halting agent.")
                break

            if self.paused_event and self.paused_event.is_set():
                print("[INFO] Pause event received. Waiting...")
                while self.paused_event.is_set():
                    await asyncio.sleep(1) # Check every second
                print("[INFO] Agent resumed.")

            print(f"--- Step {i+1}/{self.max_steps} ---")

            # Propagate dynamic settings to the browser bridge on each step
            await self.browser.propagate_settings_to_bridge()

            # 1. Observe the page
            encoded_image, page_description = await self.browser.observe_and_annotate(step=i)

            # 2. Get strategic plan
            strategic_plan = await self.ai_model.get_strategic_plan(
                self.objective,
                history=self.working_memory.get_history(),
                page_description=page_description,
                self_critique=self.self_critique
            )
            self.working_memory.add_reflection(strategic_plan.get("reflection", ""))
            self.working_memory.add_world_model(strategic_plan.get("world_model", ""))
            self.working_memory.add_plan(strategic_plan.get("plan", []))

            plan = strategic_plan.get("plan", [])
            if not plan:
                print("[INFO] Plan is empty. Finishing run.")
                break

            # 3. Execute tactical actions
            for step in plan:
                # Get tactical action
                action_json = await self.ai_model.get_tactical_action(
                    plan=[step],
                    encoded_image=encoded_image,
                    page_description=page_description
                )

                thought = action_json.get("thought", "")
                confidence_score = action_json.get("confidence_score", 0.0)
                tool_name = action_json.get("tool")
                params = action_json.get("params", {})
                potential_actions = action_json.get("potential_actions", [])

                print(f"[ACTION] Tool: {tool_name}, Params: {params}, Confidence: {confidence_score}, Thought: {thought}")

                is_valid = await self.ai_model.validate_action(self.objective, page_description, action_json)
                if not is_valid:
                    print(f"[VALIDATION] Action '{tool_name}' deemed invalid by the fast model. Skipping.")
                    self.last_action_result = "Action was deemed invalid by the validator."
                    self.working_memory.add_action_result(tool_name, params, self.last_action_result)
                    continue

                # Adaptive Risk-Taking
                if confidence_score < 0.6:
                    print(f"[WARN] Low confidence score ({confidence_score}). Asking user for clarification.")
                    clarification_tool = next((t for t in self.tools if t.name == "ask_user_for_clarification"), None)
                    if clarification_tool:
                        world_model_summary = self.working_memory.get_world_model()
                        user_instruction = await clarification_tool.arun(
                            world_model=f"My objective is: {self.objective}\n\nMy current understanding of the situation is:\n{world_model_summary}\n\nI was about to take the action '{tool_name}' with parameters {params} but my confidence is low. My thought process was: '{thought}'. What should I do instead?",
                            potential_actions=potential_actions
                        )
                        # The user response will be handled in the next loop iteration
                        self.last_action_result = f"User provided new instruction: {user_instruction}"
                        self.working_memory.add_action_result(tool_name, params, self.last_action_result)
                        continue # Skip to next iteration
                    else:
                        print("[ERROR] AskUserForClarificationTool not found. Cannot ask for help.")
                        self.last_action_result = "Error: Low confidence and clarification tool is not available."
                        break # Exit plan execution

                elif confidence_score < 0.9:
                    print(f"[WARN] Medium confidence score ({confidence_score}). Proceeding with caution.")

                # Execute action
                tool_to_execute = next((t for t in self.tools if t.name == tool_name), None)
                if tool_to_execute:
                    try:
                        result = await tool_to_execute.arun(**params)
                        self.last_action_result = result
                        print(f"[INFO] Action '{tool_name}' executed successfully. Result: {result}")
                    except Exception as e:
                        error_message = f"An unexpected error occurred during tool execution: {e}"
                        print(f"[ERROR] {error_message}")
                        self.last_action_result = error_message
                else:
                    self.last_action_result = f"Error: Tool '{tool_name}' not found."
                    print(f"[ERROR] {self.last_action_result}")

                self.working_memory.add_action_result(tool_name, params, self.last_action_result)

                # If the action was to finish, break the outer loop
                if tool_name == "finish":
                    print("[INFO] 'finish' action called. Ending run.")
                    return

        print("\n[INFO] Agent run has finished.")

    async def save_and_critique(self):
        session_log_path = os.path.join(self.run_folder, "session_log.txt")
        with open(session_log_path, 'w', encoding='utf-8', errors='ignore') as f:
            print(f"[INFO] Saving session log to {session_log_path}")
            f.write(self.working_memory.to_json())
        
        self.website_graph.save_graph()


        # Save the strategy if the run was successful
        # For now, we consider a run successful if it completes without an error.
        # A more robust check could be added here later.
        actions = self.strategy_callback_handler.actions
        if actions:
            domain = self.strategy_manager.get_domain(self.start_url)
            self.strategy_manager.save_strategy(domain, self.objective, actions)

        critique = await self.ai_model.get_self_critique(self.working_memory.get_history())

        # Log the critique
        developer_suggestions_file = "developer_suggestions.log"
        if critique.startswith("Directive for developer:"):
            with open(developer_suggestions_file, 'a', encoding='utf-8') as f:
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {critique}\n")
            print(f"[INFO] Developer suggestion logged to {developer_suggestions_file}")
        else:
            with open(self.critique_file, 'w', encoding='utf-8', errors='ignore') as f:
                f.write(critique)
            print(f"[INFO] Agent critique logged to {self.critique_file}")