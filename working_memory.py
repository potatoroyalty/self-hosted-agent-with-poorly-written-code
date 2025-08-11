import json

class WorkingMemory:
    def __init__(self):
        self.memory = {}

    def upsert(self, key: str, value: any):
        self.memory[key] = value

    def get(self, key: str) -> any:
        return self.memory.get(key)

    def to_json(self) -> str:
        return json.dumps(self.memory, indent=4)

    def __str__(self) -> str:
        return self.to_json()
