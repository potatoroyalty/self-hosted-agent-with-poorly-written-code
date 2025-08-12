# Note for Future Agents

## About This Project

This project is an **autonomous AI web agent**. Its purpose is to navigate and interact with websites to achieve user-defined objectives. It operates by taking screenshots of web pages, using a vision-language model to understand the content, and then deciding on the next action to take (e.g., clicking, typing).

The agent runs entirely on the user's local machine and relies on **Ollama** to run the large language models (LLMs) that power its reasoning and decision-making abilities.

## Your Role as a Coding Agent

It is important to distinguish between the agent you are currently operating as (a software development agent) and the local AI agent that this project is building.

*   **You (the Coding Agent):** Your role is to write, debug, and modify the code for this project. You are working *on* the codebase.
*   **The Local Agent:** This is the application being built. It is an autonomous agent that runs on a user's machine to browse the web.

Your purpose is to build and improve the features of the local agent.

## Testing and Verification

The full test suite and application functionality depend on a properly configured and running Ollama instance. As a coding agent, you do not have access to this environment.

**Action Required:**

To have your changes tested and verified, you must push them to a branch on GitHub. The user will then run the application and tests from that branch.

1.  Complete your code changes.
2.  Request a code review using the `request_code_review` tool.
3.  Address any feedback from the review.
4.  Submit your changes using the `submit` tool. This will create a new branch on GitHub for the user to test.

Do not attempt to run the application or tests yourself.
