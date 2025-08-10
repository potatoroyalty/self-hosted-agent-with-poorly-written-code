# AI Web Agent

This project is an AI-powered web agent that can navigate and interact with websites to achieve a specific objective. It uses local AI models through [Ollama](https://ollama.com/) to understand the content of a page, including visual elements, and decide on the next action to take.

## Features

*   **Autonomous Web Navigation**: The agent can browse websites, click elements, type text, and navigate to different pages to complete a given objective.
*   **Vision-Capable**: Utilizes vision-language models (like Gemma) to analyze screenshots of web pages, making it capable of understanding pages that are heavily reliant on JavaScript and dynamic content.
*   **Dynamic Macro Creation**: The agent can write its own Python scripts (macros) to automate repetitive tasks it encounters.
*   **Self-Critique and Learning**: After each run, the agent reflects on its performance and generates self-critiques to improve its decision-making in future runs.
*   **Local First**: Runs entirely on your local machine, ensuring privacy and control over your data. Requires a running Ollama instance.

## How It Works

The agent operates in a loop, taking the following steps:

1.  **Observe**: The agent takes a screenshot of the current web page.
2.  **Understand**: It uses a vision-language model to understand the content of the screenshot and describe the current state of the page.
3.  **Reason and Plan**: Based on the objective, the current page state, and its past actions, the agent reasons about the best course of action and creates a plan.
4.  **Act**: The agent executes an action, such as clicking a button, typing text, or navigating to a new page, using a set of predefined tools.

This process is orchestrated by several key components:

*   `main.py`: The entry point for running the agent. It handles command-line arguments and initializes the agent.
*   `agent.py`: The core of the agent, which manages the main loop, memory, and interaction between the AI models and the browser.
*   `ai_model.py`: Handles all communication with the Ollama AI models, including generating descriptions, plans, and actions.
*   `browser_controller.py`: Controls the Playwright browser, allowing the agent to interact with web pages.
*   `langchain_agent.py`: Defines the LangChain tools (e.g., `click`, `type`) that the agent can use to interact with the web.
*   `tools.py`: Defines the data schemas for the parameters of the tools.

## Setup

To get the agent running on your local machine, follow these steps.

### 1. Clone the Repository

First, you need to download the project files. You can do this by cloning the GitHub repository.

```bash
git clone <repository-url>
cd <repository-directory>
```

### 2. Install Dependencies

The project uses several Python libraries to function. You can install them using `pip` and the `requirements.txt` file. It is recommended to use a virtual environment.

```bash
python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
pip install -r requirements.txt
```

The first time you run the agent, Playwright will also install the necessary browser drivers.

### 3. Set Up Ollama

This agent requires [Ollama](https://ollama.com/) to be running on your machine. Ollama provides the AI models that the agent uses for its reasoning and vision capabilities.

1.  **Download and Install Ollama**: Follow the instructions on the [Ollama website](https://ollama.com/) to download and install it for your operating system.
2.  **Run Ollama**: Make sure the Ollama application is running before you start the agent.

### 4. Download AI Models

The agent will attempt to download the required AI models automatically if they are not already available locally. The default models are:

*   **Main/Supervisor Model**: `mixtral:latest`
*   **Fast Model**: `phi3`
*   **Vision Model**: `gemma:7b`

You can also pull them manually before running the agent for the first time:

```bash
ollama pull mixtral:latest
ollama pull phi3
ollama pull gemma:7b
```

For users with limited resources, the agent includes a `--low-memory` mode which is enabled by default. This mode uses smaller, more efficient models:

*   **Main/Supervisor Model**: `mistral:7b`
*   **Fast Model**: `phi3`
*   **Vision Model**: `gemma:2b`

You can configure the agent to use different models by passing command-line arguments (see the "Usage" section).

## Usage

To run the agent, use the `main.py` script. You need to provide an objective for the agent to achieve.

### Basic Usage

The most basic way to run the agent is to provide an objective. The agent will prompt you for the objective if you don't provide one.

```bash
python main.py --objective "Find the weather forecast for tomorrow in London"
```

If you run the script without any arguments, it will prompt you to enter the objective interactively:

```bash
python main.py
```

### Command-Line Arguments

You can customize the agent's behavior with the following command-line arguments:

*   `--objective`: (Optional) The main goal for the agent to achieve. If not provided, the script will prompt for it.
*   `--url`: The starting URL for the agent. Defaults to `https://www.google.com`.
*   `--model`: The main Ollama model for complex reasoning (e.g., `mixtral:latest`).
*   `--supervisor-model`: The Ollama model for high-level overview (e.g., `mixtral:latest`).
*   `--fast-model`: A smaller, faster model for simple tasks (e.g., `phi3`).
*   `--vision-model`: The Ollama model for vision tasks (e.g., `gemma:7b`).
*   `--max-steps`: The maximum number of steps the agent can take.
*   `--low-memory`: Use smaller, less resource-intensive models. This is enabled by default. Overrides other model arguments.

**Example with custom models and start URL:**

```bash
python main.py \
  --objective "Log in to my account on example.com" \
  --url "https://example.com/login" \
  --model "mixtral:8x7b" \
  --supervisor-model "mixtral:8x22b"
```

## Contributing

Contributions are welcome! If you would like to contribute to this project, please follow these steps.

### 1. Fork the Repository

Click the "Fork" button at the top right of the repository page on GitHub. This will create a copy of the repository in your own GitHub account.

### 2. Create a New Branch

Create a new branch in your forked repository to work on your changes. It's good practice to give your branch a descriptive name.

```bash
git checkout -b my-new-feature
```

### 3. Make Your Changes

Make your changes to the code. If you are adding a new feature, please also add any necessary tests.

### 4. Commit Your Changes

Once you are happy with your changes, commit them with a clear and concise commit message.

```bash
git add .
git commit -m "feat: Add my new feature"
```

### 5. Push to Your Branch

Push your changes to your forked repository on GitHub.

```bash
git push origin my-new-feature
```

### 6. Submit a Pull Request

Go to the original repository on GitHub and you should see a prompt to create a pull request from your new branch. Fill out the pull request template with a description of your changes and submit it for review.

## Updating Your Local Copy

To keep your local copy of the project up-to-date with the latest changes from the main repository, you can use the `git pull` command.

First, make sure you have configured a remote that points to the original repository. If you cloned the repository, this remote is usually named `origin`.

```bash
git pull origin main
```

This will fetch the latest changes from the `main` branch of the original repository and merge them into your local branch.
