import subprocess
import time
import asyncio
from unittest.mock import MagicMock
from agent import WebAgent
import config

async def main():
    # Start the test server
    server_process = subprocess.Popen(['python', 'test_environment/test_server.py'])
    time.sleep(2)  # Give the server a moment to start

    # Create a mock SocketIO object
    mock_socketio = MagicMock()

    agent = None  # Ensure agent is defined in the outer scope
    try:
        # Initialize the agent with the mock socketio
        agent = WebAgent(
            objective="Log in to the website with username 'admin' and password 'password'",
            start_url="http://localhost:8000/login.html",
            socketio=mock_socketio,
            model_name=config.LOW_MEMORY_MAIN_MODEL,
            supervisor_model_name=config.LOW_MEMORY_SUPERVISOR_MODEL,
            fast_model_name=config.LOW_MEMORY_FAST_MODEL,
            testing=True
        )

        # The agent can't run without a real AI model.
        # For this test, we'll bypass the agent's main loop and directly
        # call the browser controller methods to ensure the new architecture works.

        print("[TEST] Starting browser controller...")
        await agent.browser.start()

        print(f"[TEST] Navigating to {agent.start_url}...")
        await agent.browser.goto_url(agent.start_url)

        # Now, instead of direct Playwright calls, we simulate the agent's behavior
        # by calling observe_and_annotate and execute_action.
        # This is a simplified test flow.

        # 1. Observe the page (this would be done by the agent)
        # In a real scenario, the bridge would respond. We need to mock this response.
        # For this basic test, we'll assume the observation happens and we get some elements.
        print("[TEST] Simulating an observation step...")
        agent.browser.labeled_elements = {
            1: {'selector': '#username'},
            2: {'selector': '#password'},
            3: {'selector': 'input[type="submit"]'}
        }

        # To make this test runnable without a live frontend, we need to mock the
        # response from the bridge. We'll bypass the waiting part of execute_action
        # and just check if the right emit call is made.

        # We will directly check the calls on our mock_socketio object.
        # This test verifies that the controller sends the right commands.

        print("[TEST] Executing 'type' action for username...")
        await agent.browser.execute_action({
            "action_type": "type",
            "details": {"element_label": 1, "text": "admin"}
        })
        mock_socketio.emit.assert_any_call('type', {'action': 'type', 'label': 1, 'text': 'admin'}, namespace='/bridge')

        print("[TEST] Executing 'type' action for password...")
        await agent.browser.execute_action({
            "action_type": "type",
            "details": {"element_label": 2, "text": "password"}
        })
        mock_socketio.emit.assert_any_call('type', {'action': 'type', 'label': 2, 'text': 'password'}, namespace='/bridge')

        print("[TEST] Executing 'click' action for submit button...")
        await agent.browser.execute_action({
            "action_type": "click",
            "details": {"element_label": 3}
        })
        mock_socketio.emit.assert_any_call('click', {'action': 'click', 'label': 3}, namespace='/bridge')

        print("\n[SUCCESS] All test steps executed and socket emits were called as expected.")

    except Exception as e:
        print(f"\n[ERROR] An error occurred during the test: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Stop the server
        server_process.terminate()
        server_process.wait()
        print("Test server stopped.")
        if agent and agent.browser:
            await agent.browser.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[INFO] User interrupted the program.")