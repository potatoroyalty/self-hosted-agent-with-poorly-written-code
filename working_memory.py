import json

class WorkingMemory:
    def __init__(self):
        self.memory = {}
        self.history = []

    def upsert(self, key: str, value: any):
        self.memory[key] = value

    def get(self, key: str) -> any:
        return self.memory.get(key)

    def add_reflection(self, reflection: str):
        self.history.append({"type": "reflection", "content": reflection})
        self.upsert("last_reflection", reflection)

    def add_world_model(self, world_model: str):
        self.history.append({"type": "world_model", "content": world_model})
        self.upsert("world_model", world_model)

    def add_plan(self, plan: list):
        self.history.append({"type": "plan", "content": plan})
        self.upsert("current_plan", plan)

    def add_action_result(self, tool_name: str, params: dict, result: str):
        self.history.append({
            "type": "action_result",
            "tool": tool_name,
            "params": params,
            "result": result
        })
        self.upsert("last_action_result", {
            "tool": tool_name,
            "params": params,
            "result": result
        })

    def get_history(self) -> str:
        return json.dumps(self.history, indent=4)

    def to_json(self) -> str:
        return json.dumps(self.memory, indent=4)

    def __str__(self) -> str:
        return self.to_json()
