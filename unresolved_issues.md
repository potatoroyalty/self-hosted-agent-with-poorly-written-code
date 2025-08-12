# Project Audit and Outstanding Issues

This document outlines a list of outstanding issues, unimplemented features, and areas for improvement identified during a codebase review. It is intended to be used by a future software agent to prioritize and address these items.

*Note: This is a technical document intended for developers. For a high-level summary of the project's current status, please see the "Current Status & Known Issues" section in the main [`README.md`](README.md).*

## 1. Unimplemented & "Headless" Features

This section details features that are present in the UI or code but lack a complete backend implementation.

---

### 1.1. Script Generation from User Recordings
- **File:** `renderer.js` (line 215), `run_ui.py` (line 120)
- **Description:** The UI has a "Record New Script" button that successfully captures user `click` and `input` events and sends them to the server. The server logs these events to the console but does not do anything further with them. The "Generate Script" button in the "Generator" view is intended to use these recordings, but it is non-functional and only shows an alert.
- **Suggested Action:** Implement the script generation logic. This would likely involve having an AI model process the `recorded_events` list from `run_ui.py` to produce a reusable script (e.g., a new macro tool).

---

### 1.2. Clarification UI Lacks Actions
- **Files:** `renderer.js` (line 69), `agent.py` (line 204)
- **Description:** The UI has a popup for asking the user for clarification. This UI is designed to show a list of potential actions for the user to choose from. However, the agent currently calls this tool with an empty `potential_actions` list, so the user is prompted for help but given no options.
- **Suggested Action:** Enhance the `get_tactical_action` method in the AI model to generate a list of alternative actions when its confidence is low. This list can then be passed to the `AskUserForClarificationTool`.

---

### 1.3. Placeholder UI Views and Tabs
- **File:** `index.html` (lines 94, 99, 104, 109, 137, 140)
- **Description:** The main UI has several navigation links ("Scripts", "Proxies", "Logs", "Settings") and sidebar tabs ("Inspector", "Task Queue") that lead to placeholder pages with no functionality.
- **Suggested Action:** Implement the UI and backend logic for each of these sections, one at a time. For example, the "Scripts" view could list, edit, and run saved macro scripts.

---

### 1.4. Non-Functional UI Controls
- **File:** `index.html` (lines 78-86, 126-129)
- **Description:** Several UI elements are present but have no event listeners attached to them. This includes the "Quick Toggles" in the left sidebar (Stealth Mode, Proxy Usage, etc.), the "Pause" and "Stop" buttons in the main browser view, and the "Select a script..." dropdown. The status bar in the footer is also static and does not reflect the application's true state.
- **Suggested Action:** Wire up these UI elements to the backend. For example, the "Pause" button should send a socket event to the agent to temporarily halt its execution. The toggles should modify the agent's configuration.

---

## 2. Items Needing Updates & Improvements

This section covers existing features that are functional but could be improved for robustness, security, or maintainability.

---

### 2.1. Brittle Google Search Selectors
- **File:** `browser_controller.py` (lines 351-358)
- **Description:** The `_tool_perform_google_search` method relies on hardcoded CSS selectors (`textarea[aria-label="Search"]`, `input[aria-label="Google Search"]`) to find elements on the Google search page. These are fragile and will break if Google changes its website's HTML structure.
- **Suggested Action:** Refactor this tool to use a more resilient method for finding elements. For example, use the vision model to visually identify the search box and button, or use a more general-purpose text-based search to find an element with a label like "Search".

---

### 2.2. Limited User Action Recording
- **File:** `bridge.js` (lines 102-103)
- **Description:** The script that records user actions (`bridge.js`) only listens for `click` and `input` events. It does not capture other common interactions like dropdown selections (`change` events), form submissions (`submit`), or key presses (`keydown`), limiting the scope of automations that can be learned.
- **Suggested Action:** Add event listeners for other relevant user interactions (`change`, `submit`, `keydown`, `scroll`, etc.) to the `recordEvent` function in `bridge.js`.

---

### 2.3. Simplified Script Execution Sandbox
- **File:** `langchain_agent.py` (line 218)
- **Description:** The `ExecuteScriptTool` runs scripts in a subprocess. A comment in the code itself notes: `# This is a simplified execution. For true sandboxing, consider Docker.` Running arbitrary scripts without proper sandboxing is a security risk.
- **Suggested Action:** Implement a more secure execution environment for user-provided or AI-generated scripts, potentially by using Docker containers as suggested in the code comment.

---

### 2.4. Basic HTML Sanitization
- **File:** `renderer.js` (line 33)
- **Description:** The live log updates are sanitized by replacing `<` and `>` characters. This prevents basic HTML injection but is not fully secure against more sophisticated cross-site scripting (XSS) attacks.
- **Suggested Action:** Replace the basic string replacement with a well-vetted third-party sanitization library (like `DOMPurify`) to provide more robust protection.

---

### 2.5. Ollama Mocking in Test Environments
- **File:** `ai_model.py` (line 155)
- **Description:** To prevent memory overload issues in resource-constrained test environments, the application now detects if it is running within a Python virtual environment (`sys.prefix != sys.base_prefix`). If it is, the expensive Ollama models are not loaded. Instead, they are replaced by mock objects that return placeholder responses.
- **Note:** This means that when running in a virtual environment, the AI's reasoning and vision capabilities will be disabled. This is intended for front-end development and testing where AI responses are not critical. For full functionality, run the application from a global Python environment where Ollama models can be loaded.

---

## 3. Potential Issues & Minor Bugs

This section lists miscellaneous findings that could be bugs or areas for minor improvement.

---

### 3.2. Incomplete Async Method Implementations
- **File:** `langchain_agent.py` (lines 255, 271, 321)
- **Description:** Several tools (e.g., `CreateMacroTool`, `NavigateToURLTool`) have synchronous `_run` methods that are not implemented and immediately raise an error. The `AskUserForClarificationTool`'s async `_arun` method simply calls its synchronous counterpart, with a comment noting it's a temporary solution.
- **Suggested Action:** Implement the synchronous `_run` methods for the tools that lack them, or ensure they are never called. Refactor the `AskUserForClarificationTool` to use a proper asynchronous pattern with `asyncio` events instead of blocking queues.
