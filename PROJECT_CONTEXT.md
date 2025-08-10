# Project Context: Autonomous Web Agent

## Goal

The primary goal of this project is to create an autonomous web agent capable of achieving user-defined objectives by browsing the web. The agent should be able to understand complex goals, interact with web pages, and learn from its experiences to improve its performance over time.

## Architecture

The agent is built using a combination of Python libraries, including:

- **`playwright`**: For controlling the web browser and interacting with web pages.
- **`ollama`**: For running local large language models (LLMs) that power the agent's reasoning and decision-making abilities.
- **`langchain`**: For creating and managing the agent, which is a ReAct-style agent.

The agent's architecture is modular, with different components responsible for specific tasks:

- **`main.py`**: The entry point of the application. It parses command-line arguments and starts the agent.
- **`agent.py`**: Contains the main `WebAgent` class that orchestrates the agent's lifecycle, including memory management and self-critique.
- **`langchain_agent.py`**: Defines the set of tools that the agent can use to interact with the web, such as navigating to pages, clicking elements, and typing text.
- **`browser_controller.py`**: Manages the web browser instance using `playwright`.
- **`ai_model.py`**: Handles the interaction with the `ollama` LLMs.

## Key Features

- **Autonomous Browsing**: The agent can navigate websites, fill out forms, and click buttons to achieve its objectives.
- **Local LLMs**: The agent uses locally-run LLMs via `ollama`, ensuring privacy and control over the models.
- **Memory and Learning**: The agent maintains a memory of its past actions and uses a self-critique mechanism to learn from its mistakes and improve its performance.
- **Configurable Models**: The agent can be configured to use different LLMs for different tasks, allowing for a balance between performance and resource usage.
- **Dynamic Tools**: The agent can be extended with new tools that are loaded dynamically from a JSON configuration file.
