import json
import os
import sys

# --- Default Configuration ---

DEFAULT_SETTINGS = {
    # Agent Configuration
    "START_URL": "https://www.google.com",
    "MAX_STEPS": 25,
    "MAX_RETRIES": 3,
    "WAIT_BETWEEN_ACTIONS": 1.0,

    # Model Configuration
    "MAIN_MODEL": "mixtral:latest",
    "SUPERVISOR_MODEL": "mixtral:latest",
    "FAST_MODEL": "phi3",
    "VISION_MODEL": "gemma:7b",
    "TEMPERATURE": 0.7,
    "TOP_P": 1.0,

    # Low Memory Mode
    "LOW_MEMORY_MODE": True,
    "LOW_MEMORY_MAIN_MODEL": "mistral:7b",
    "LOW_MEMORY_SUPERVISOR_MODEL": "mistral:7b",
    "LOW_MEMORY_FAST_MODEL": "phi3",
    "LOW_MEMORY_VISION_MODEL": "gemma:2b",

    # Browser Configuration
    "HEADLESS_BROWSER": False,
    "BROWSER_TYPE": "chromium",
    "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "VIEWPORT_WIDTH": 1280,
    "VIEWPORT_HEIGHT": 720,
    "SCREENSHOT_FULL_PAGE": True,
    "LOAD_IMAGES": True,
    "ENABLE_JAVASCRIPT": True,

    # Security & Privacy
    "STEALTH_MODE": True,
    "USE_PROXY": False,
    "PROXY_ADDRESS": "",
    "CLEAR_COOKIES_ON_START": True,
    "CLEAR_LOCAL_STORAGE_ON_START": True,
    "INCOGNITO_MODE": False,

    # Logging & Debugging
    "LOG_LEVEL": "INFO",
    "LOG_TO_FILE": True,
    "LOG_FILE": "agent_log.txt",
    "LOG_MEMORY": True,
    "MEMORY_FILE": "memory_log.txt",
    "LOG_CRITIQUE": True,
    "CRITIQUE_FILE": "critique_log.txt",
    "SAVE_SCREENSHOTS": True,
    "SCREENSHOT_DIR": "runs/screenshots",

    # Advanced Features
    "ENABLE_MACROS": True,
    "ENABLE_STRATEGY_LEARNING": True,
    "ENABLE_WEBSITE_GRAPH": True,

    # File Paths
    "PREPROCESSOR_PATH": "preprocessor.js",
    "DYNAMIC_TOOLS_PATH": "dynamic_tools.json",
    "GRAPH_FILE_PATH": "website_graph.json",
    "STRATEGY_FILE_PATH": "strategies.json"
}

# --- Configuration Loading ---

SETTINGS_FILE = "settings.json"

def get_config():
    """
    Loads settings from a JSON file, merging them with defaults.
    """
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r') as f:
            try:
                user_settings = json.load(f)
            except json.JSONDecodeError:
                user_settings = {}
    else:
        user_settings = {}

    # Merge user settings with defaults, giving priority to user settings
    config = DEFAULT_SETTINGS.copy()
    config.update(user_settings)

    # Ensure all default keys are present
    for key, value in DEFAULT_SETTINGS.items():
        if key not in config:
            config[key] = value

    return config

def save_config(new_settings):
    """
    Saves the provided settings to the JSON file.
    """
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(new_settings, f, indent=4)

    # After saving, update the current configuration in the module
    update_globals(new_settings)

def update_globals(config):
    """
    Updates the global variables in this module with the given config.
    """
    g = globals()
    for key, value in config.items():
        g[key] = value

# --- Initial Load ---

# Load the configuration and expose it as module-level variables
config = get_config()
update_globals(config)

# For any code that needs to dynamically update settings
def update_setting(key, value):
    """
    Updates a single setting and saves the configuration.
    """
    current_config = get_config()
    if key in current_config:
        current_config[key] = value
        save_config(current_config)
    else:
        # This could be an error or a feature, depending on desired strictness
        print(f"Warning: Attempted to update non-existent setting '{key}'")
