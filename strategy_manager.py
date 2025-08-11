import json
import os
from typing import List, Dict, Any
from urllib.parse import urlparse
from langchain.callbacks.base import AsyncCallbackHandler
from langchain.schema import AgentAction
from typing import Dict, Any, List, UUID


class StrategyCallbackHandler(AsyncCallbackHandler):
    """Callback handler to record agent actions."""
    def __init__(self):
        self.actions: List[Dict[str, Any]] = []
        print("[INFO] StrategyCallbackHandler initialized.")

    async def on_agent_action(
        self, action: AgentAction, *, run_id: UUID, parent_run_id: UUID | None = None, **kwargs: Any
    ) -> None:
        """Record the action taken by the agent."""
        print(f"[CALLBACK] Agent action: {action.tool} with input {action.tool_input}")
        # We want to ignore the 'create_macro' tool in our strategy
        if action.tool == "create_macro":
            return

        self.actions.append({"tool_name": action.tool, "tool_input": action.tool_input})

    def clear_actions(self):
        """Clear the recorded actions."""
        self.actions = []

class StrategyManager:
    def __init__(self, strategy_file_path: str):
        self.strategy_file_path = strategy_file_path
        self.strategies = self._load_strategies()

    def _load_strategies(self) -> Dict[str, Any]:
        if os.path.exists(self.strategy_file_path):
            with open(self.strategy_file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _save_strategies(self):
        with open(self.strategy_file_path, 'w', encoding='utf-8') as f:
            json.dump(self.strategies, f, indent=4)

    def get_domain(self, url: str) -> str:
        """Extracts the domain from a URL."""
        try:
            return urlparse(url).netloc
        except Exception:
            return ""

    def find_strategy(self, domain: str, objective: str) -> List[Dict[str, Any]]:
        """Finds a strategy for a given domain and objective."""
        if domain in self.strategies and objective in self.strategies[domain]:
            return self.strategies[domain][objective]
        return None

    def save_strategy(self, domain: str, objective: str, actions: List[Dict[str, Any]]):
        """Saves a new strategy."""
        if not actions:
            return

        if domain not in self.strategies:
            self.strategies[domain] = {}

        # Do not overwrite existing strategies for now. This can be changed later.
        if objective not in self.strategies[domain]:
            self.strategies[domain][objective] = actions
            self._save_strategies()
            print(f"[INFO] New strategy saved for domain '{domain}' and objective '{objective}'.")
        else:
            print(f"[INFO] Strategy for domain '{domain}' and objective '{objective}' already exists. Not overwriting.")
