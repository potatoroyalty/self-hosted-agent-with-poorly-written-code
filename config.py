# -- Agent Configuration --
DEFAULT_URL = "https://www.google.com"
MAX_STEPS = 15
MEMORY_FILE = "memory_log.txt"
CRITIQUE_FILE = "critique_log.txt"
PREPROCESSOR_PATH = "preprocessor.js"
DYNAMIC_TOOLS_PATH = "dynamic_tools.json"
GRAPH_FILE_PATH = "website_graph.json"

# -- Model Configuration --
# Main model for complex reasoning (text-based)
MAIN_MODEL = "mixtral:latest"
# Supervisor model for high-level overview (text-based)
SUPERVISOR_MODEL = "mixtral:latest"
# Fast model for simple tasks like validation and critique (text-based)
FAST_MODEL = "phi3"
# Vision model for analyzing screenshots
VISION_MODEL = "gemma:7b"

# -- Low Memory Mode Configuration --
# Set to True to use smaller models to reduce memory usage
LOW_MEMORY_MODE = True
# Models to use in low memory mode
LOW_MEMORY_MAIN_MODEL = "mistral:7b"
LOW_MEMORY_SUPERVISOR_MODEL = "mistral:7b"
LOW_MEMORY_FAST_MODEL = "phi3"
LOW_MEMORY_VISION_MODEL = "gemma:2b"
