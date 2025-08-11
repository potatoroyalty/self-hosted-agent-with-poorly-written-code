# Note for Future Agents

## About This Project

This project is an **autonomous AI web agent**. Its purpose is to navigate and interact with websites to achieve user-defined objectives. It operates by taking screenshots of web pages, using a vision-language model to understand the content, and then deciding on the next action to take (e.g., clicking, typing).

The agent runs entirely on the user's local machine and relies on **Ollama** to run the large language models (LLMs) that power its reasoning and decision-making abilities.

## Your Role as a Coding Agent

It is important to distinguish between the agent you are currently operating as (a software development agent) and the local AI agent that this project is building.

*   **You (the Coding Agent):** Your role is to write, debug, and modify the code for this project. You are working *on* the codebase.
*   **The Local Agent:** This is the application being built. It is an autonomous agent that runs on a user's machine to browse the web.

Your purpose is to build and improve the features of the local agent.

## Testing Limitation

The full test suite and application functionality depend on a properly configured and running Ollama instance. As an AI agent, you are unable to set up and run this local environment.

**Action Required:**

Do not attempt to run tests or the application. Leave the testing and execution of the application to the user who has the required local setup. Focus on code-related tasks that do not require running the application, such as code analysis, refactoring, and documentation.
