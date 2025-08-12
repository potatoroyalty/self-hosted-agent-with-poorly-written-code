# Project Context: Autonomous Web Agent

## Goal

The primary goal of this project is to create an autonomous web agent capable of achieving user-defined objectives by browsing the web. The agent should be able to understand complex goals, interact with web pages, and learn from its experiences to improve its performance over time.

## Architecture

The agent is built using a combination of Python libraries, including:

- **`playwright`**: For controlling the web browser and interacting with web pages.
- **`ollama`**: For running local large language models (LLMs) that power the agent's reasoning and decision-making abilities.
- **`langchain`**: The `langchain-core` package is used to define the structure of the tools available to the agent (using the `BaseTool` class), but the project does not use the LangChain agent execution framework.

The agent's architecture is modular, with different components responsible for specific tasks:

- **`main.py`**: The entry point of the application. It parses command-line arguments and starts the agent.
- **`agent.py`**: Contains the main `WebAgent` class, which runs the primary agent loop (observe, plan, act) and orchestrates the agent's lifecycle.
- **`langchain_agent.py`**: Defines the library of tools (e.g., `ClickElementTool`, `TypeTextTool`) that the agent can use. These tools are built on LangChain's `BaseTool` for a standardized structure.
- **`browser_controller.py`**: Manages the web browser instance using `playwright`.
- **`ai_model.py`**: Handles the interaction with the `ollama` LLMs.

## Key Features

- **Autonomous Browsing**: The agent can navigate websites, fill out forms, and click buttons to achieve its objectives.
- **Local LLMs**: The agent uses locally-run LLMs via `ollama`, ensuring privacy and control over the models.
- **Memory and Learning**: The agent maintains a memory of its past actions and uses a self-critique mechanism to learn from its mistakes and improve its performance.
- **Configurable Models**: The agent can be configured to use different LLMs for different tasks, allowing for a balance between performance and resource usage.
- **Dynamic Tools**: The agent can be extended with new tools that are loaded dynamically from a JSON configuration file.
