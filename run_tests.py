import subprocess
import time
import asyncio
from agent import WebAgent
import config

async def main():
    # Start the test server
    server_process = subprocess.Popen(['python', 'test_environment/test_server.py'])
    time.sleep(2)  # Give the server a moment to start

    # Run the agent with a specific objective
    try:
        agent = WebAgent(
            objective="Log in to the website with username 'admin' and password 'password'",
            start_url="http://localhost:8000/login.html",
            model_name=config.LOW_MEMORY_MAIN_MODEL,
            supervisor_model_name=config.LOW_MEMORY_SUPERVISOR_MODEL,
            fast_model_name=config.LOW_MEMORY_FAST_MODEL
        )
        await agent.run()
    finally:
        # Stop the server
        server_process.terminate()
        server_process.wait()
        print("Test server stopped.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[INFO] User interrupted the program.")