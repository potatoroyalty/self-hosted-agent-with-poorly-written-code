# -- Agent Configuration --
DEFAULT_URL = "https://www.google.com"
MAX_STEPS = 15
MEMORY_FILE = "memory_log.txt"
CRITIQUE_FILE = "critique_log.txt"
PREPROCESSOR_PATH = "preprocessor.js"
DYNAMIC_TOOLS_PATH = "dynamic_tools.json"

# -- Model Configuration --
# Main model for complex reasoning
MAIN_MODEL = "llava:13b"
# Supervisor model for high-level overview
SUPERVISOR_MODEL = "mixtral:latest"
# Fast model for simple tasks like self-critique
FAST_MODEL = "llava:7b"

# -- Low Memory Mode Configuration --
# Set to True to use smaller models to reduce memory usage
LOW_MEMORY_MODE = True
# Models to use in low memory mode
LOW_MEMORY_MAIN_MODEL = "llava:7b"
LOW_MEMORY_SUPERVISOR_MODEL = "llava:7b"
LOW_MEMORY_FAST_MODEL = "phi3:mini"
