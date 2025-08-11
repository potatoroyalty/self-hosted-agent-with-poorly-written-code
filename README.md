# AI Web Agent

This project is an AI-powered web agent that can navigate and interact with websites to achieve a specific objective. It uses local AI models through [Ollama](https://ollama.com/) to understand the content of a page, including visual elements, and decide on the next action to take.

## Features

*   **Autonomous Web Navigation**: The agent can browse websites, click elements, type text, and navigate to different pages to complete a given objective.
*   **Interactive Web UI**: A web-based interface for starting the agent, viewing logs in real-time, and providing input during a run.
*   **Vision-Capable**: Utilizes vision-language models to analyze screenshots of web pages, making it capable of understanding pages that are heavily reliant on JavaScript and dynamic content.
*   **Dynamic Macro Creation**: The agent can write its own Python scripts (macros) to automate repetitive tasks it encounters.
*   **Strategy Learning**: The agent learns and saves successful action sequences (strategies) to improve its performance on similar tasks in the future.
*   **Task-Aware AI Personas**: Dynamically generates "constitutions" or system prompts for the AI models to tailor their reasoning to the specific task at hand.
*   **Self-Critique and Learning**: After each run, the agent reflects on its performance and generates self-critiques to improve its decision-making in future runs.
*   **Local First**: Runs entirely on your local machine, ensuring privacy and control over your data. Requires a running Ollama instance.

## How It Works

The agent operates in a sophisticated loop, moving beyond simple "observe and act" cycles. It leverages a multi-layered architecture to reason, plan, and execute tasks.

### Architecture Overview

The agent's workflow can be broken down into these main phases:

1.  **Observe**: The agent captures a screenshot of the current web page and annotates it with labels for all interactive elements.
2.  **Strategize**: Using a "supervisor" AI model, the agent analyzes its objective, memory, and the current page to form a high-level strategic plan. This involves reflecting on its progress and updating its internal "world model."
3.  **Execute**: For each step in the strategic plan, the agent uses a "tactical" AI model to select the best tool and parameters (e.g., which element to click). It uses vision to match the plan step to the visual layout of the page.
4.  **Learn**: After each run, the agent performs a self-critique to identify areas for improvement. It also saves successful action sequences as "strategies" that can be reused later.

This entire process is supported by a set of core components that manage state, control the browser, and interact with the AI models.

### Core Components

*   `agent.py`: The central orchestrator. It manages the main loop, coordinates all other components, and executes the agent's lifecycle.
*   `run_ui.py`: A Flask and SocketIO-based web server that provides an interactive user interface for running the agent, viewing logs, and providing real-time feedback.
*   `ai_model.py`: Handles all communication with the Ollama AI models. It is responsible for generating strategic plans, selecting tactical actions, and performing self-critique. It uses "constitutions" to guide the AI's reasoning process.
*   `constitution.py`: Contains the templates for the system prompts (or "constitutions") that guide the AI models' behavior, ensuring they adhere to a specific role and format.
*   `browser_controller.py`: A wrapper around the Playwright library that provides a high-level API for controlling the web browser. It handles tasks like navigating to pages, taking screenshots, and interacting with elements.
*   `working_memory.py`: Manages the agent's short-term memory for a single run. It tracks the history of actions, observations, and reflections.
*   `vision_tools.py`: A set of tools that allow the agent to analyze visual information from screenshots, such as finding elements based on a visual description.
*   `website_graph.py`: Builds and maintains a graph representation of the websites the agent visits, mapping the connections between pages. This is saved in `website_graph.json`.
*   `strategy_manager.py`: Saves and retrieves successful sequences of actions (strategies) for specific tasks and websites. This allows the agent to learn from experience and is stored in `strategies.json`.
*   `config.py`: A centralized file for all major configuration options, such as which AI models to use and whether to run the browser in headless mode.

## Getting Started

Follow these steps to get the agent running on your local machine.

### 1. Prerequisites

This agent requires [Ollama](https://ollama.com/) to be running on your machine. Ollama provides the AI models that the agent uses for its reasoning and vision capabilities.

1.  **Download and Install Ollama**: Follow the instructions on the [Ollama website](https://ollama.com/) to download and install it for your operating system.
2.  **Run Ollama**: Make sure the Ollama application is running before you start the agent.

### 2. Installation

First, clone the repository to your local machine.

```bash
git clone <repository-url>
cd <repository-directory>
```

Next, install the required Python dependencies. It is recommended to use a virtual environment.

```bash
python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
pip install -r requirements.txt
```

The first time you run the agent, Playwright will also install the necessary browser drivers.

### 3. Download AI Models

The agent will attempt to download the required AI models automatically if they are not already available locally. The default models are configured for a low-memory footprint.

*   **Main/Supervisor Model**: `mistral:7b`
*   **Fast Model**: `phi3`
*   **Vision Model**: `gemma:2b`

You can also pull them manually before running the agent for the first time:

```bash
ollama pull mistral:7b
ollama pull phi3
ollama pull gemma:2b
```

You can configure the agent to use different, more powerful models by passing command-line arguments (see the "Usage" section).

## Usage

You can run the agent using either the command-line interface (CLI) or the web-based user interface (UI).

### Command-Line Interface (CLI)

To run the agent from the command line, use the `main.py` script. You must provide an objective for the agent to achieve.

```bash
python main.py --objective "Find the weather forecast for tomorrow in London"
```

If you run the script without the `--objective` argument, it will prompt you to enter one interactively.

**Command-Line Arguments:**

*   `--objective`: The main goal for the agent to achieve.
*   `--url`: The starting URL for the agent. Defaults to `https://www.google.com`.
*   `--model`: The main Ollama model for complex reasoning (e.g., `mixtral:latest`).
*   `--supervisor-model`: The Ollama model for high-level overview (e.g., `mixtral:latest`).
*   `--fast-model`: A smaller, faster model for simple tasks (e.g., `phi3`).
*   `--vision-model`: The Ollama model for vision tasks (e.g., `gemma:7b`).
*   `--max-steps`: The maximum number of steps the agent can take.
*   `--low-memory`: Use smaller, less resource-intensive models. This is enabled by default. Set to `false` to disable.

### Web Interface (UI)

For a more interactive experience, you can use the web-based UI.

**To launch the UI, run the following command:**

```bash
python run_ui.py
```

This will start a local web server and should automatically open the interface in your default web browser at `http://127.0.0.1:5000`.

**The web interface provides several features:**

*   **Start Agent**: Enter your objective in the input box and click "Start Agent" to begin a run.
*   **Real-Time Logs**: The agent's thoughts, actions, and observations are streamed to the page in real-time, allowing you to follow along with its progress.
*   **Clarification Requests**: If the agent is unsure how to proceed, it will pause and ask for your input through the UI. You can provide instructions to guide its next action.
*   **Screenshot Display**: The UI will display the latest screenshot the agent is analyzing, giving you a clear view of what the agent "sees".

## Configuration

The agent's behavior can be customized through the `config.py` file. This file contains settings for the AI models, browser behavior, and file paths.

While command-line arguments can override some of these settings for a single run, modifying `config.py` allows you to change the default behavior.

### Key Configuration Options

*   `LOW_MEMORY_MODE`: Set to `True` by default to use smaller, less resource-intensive models. Set this to `False` if you have a powerful machine and want to use larger models.
*   `HEADLESS_BROWSER`: Set to `True` to run the browser in the background without a visible GUI window. Set to `False` (the default) to watch the agent work in real-time.
*   `MAIN_MODEL`, `VISION_MODEL`, etc.: You can change the default Ollama models used by the agent here.

## Advanced Concepts

The agent includes several advanced features for learning and long-term task automation.

*   **Dynamic Macros**: The agent has the ability to write its own Python tools (macros) to automate repetitive sequences of actions. These macros are saved in the `macros/` directory and are loaded at runtime. This allows the agent to learn new skills tailored to specific websites or tasks.
*   **Strategy Manager**: The agent records successful strategies (sequences of actions for a given objective) in `strategies.json`. While not fully implemented for automatic reuse yet, this framework is designed to allow the agent to recall and apply past solutions to similar problems.
*   **Website Graph**: As the agent navigates, it builds a graph of the relationships between pages in `website_graph.json`. This helps the agent understand the structure of a site and navigate more efficiently in the future.
*   **Constitutions**: The agent's reasoning is guided by "constitutions," which are specialized system prompts that define a role and a set of rules for the AI models. The `SUPERVISOR_CONSTITUTION` even allows a higher-level AI to write a custom, task-specific constitution for the main agent, adapting its core behavior to the objective.

## Project Structure

Here is an overview of the key files and directories in this project:

*   `main.py`: The command-line entry point for the agent.
*   `run_ui.py`: The entry point for the web-based UI.
*   `agent.py`: The core file containing the main agent logic.
*   `config.py`: The central configuration file.
*   `runs/`: This directory is created automatically to store the output of each agent run. Each subfolder contains screenshots, a log of the agent's memory, and other artifacts.
*   `macros/`: This directory contains dynamically generated Python scripts (macros) that the agent creates to automate tasks.
*   `website_graph.json`: Stores the graph of visited web pages, helping the agent understand website structures.
*   `strategies.json`: Stores learned strategies for completing objectives on specific websites.
*   `dynamic_tools.json`: The configuration file that registers the dynamic macros with the agent.

## Contributing

Contributions are welcome! Please follow the standard fork-and-pull-request workflow.

1.  Fork the repository.
2.  Create a new branch (`git checkout -b my-new-feature`).
3.  Make your changes.
4.  Commit your changes (`git commit -m "feat: Add my new feature"`).
5.  Push to the branch (`git push origin my-new-feature`).
6.  Submit a pull request.

## License

This project is licensed under the terms of the LICENSE file.
