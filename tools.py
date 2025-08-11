from typing import TypedDict, Literal, Union

class ClickParams(TypedDict):
    element: int

class TypeParams(TypedDict):
    element: int
    text: str

class SelectParams(TypedDict):
    element: int
    value: str

class ScrollParams(TypedDict):
    direction: Literal['up', 'down']

class FinishParams(TypedDict):
    reason: str

class PauseForUserParams(TypedDict):
    instruction_to_user: str

class FindTextParams(TypedDict):
    text_to_find: str

class GoogleSearchParams(TypedDict):
    query: str

class UpsertInMemoryParams(TypedDict):
    key: str
    value: str

TOOL_SCHEMAS = {
    # Observation tools
    "get_page_content": {},  # No parameters needed
    "get_element_details": {"label": int},
    "find_elements_by_text": {"text_to_find": str},
    "get_all_links": {},  # No parameters needed
    # Basic tools
    "click": {"element": int},
    "type": {"element": int, "text": str},
    "select": {"element": int, "value": str},
    "scroll": {"direction": ["up", "down"]},
    # Memory tools
    "upsert_in_memory": {"key": str, "value": str},
    # Composite tools
    "perform_google_search": {"query": str},
    # Control tools
    "finish": {"reason": str},
    "pause_for_user": {"instruction_to_user": str}
}
