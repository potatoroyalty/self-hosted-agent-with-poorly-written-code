# FILE: main.py

import argparse
import asyncio
from agent import WebAgent
import config

async def main():
    parser = argparse.ArgumentParser(description="Run the professional Web Agent.")
    # MODIFIED: Make objective not required to work with the interactive batch script
    parser.add_argument("--objective", type=str, help="The main goal for the agent to achieve. If not provided, the script will prompt for it.")
    parser.add_argument("--url", type=str, default=config.DEFAULT_URL, help="The optional starting URL for the agent.")
    parser.add_argument("--model", type=str, default=config.MAIN_MODEL, help="The main Ollama model for complex reasoning (e.g., 'llava:13b').")
    parser.add_argument("--supervisor-model", type=str, default=config.SUPERVISOR_MODEL, help="The Ollama model for high-level overview (e.g., 'llava:13b').")
    parser.add_argument("--fast-model", type=str, default=config.FAST_MODEL, help="A smaller, faster model for simple tasks like self-critique (e.g., 'llava:7b').")
    parser.add_argument("--vision-model", type=str, default=config.VISION_MODEL, help="The Ollama model for vision tasks (e.g., 'gemma:7b').")
    parser.add_argument("--max-steps", type=int, default=config.MAX_STEPS, help="The maximum number of steps the agent can take.")
    parser.add_argument("--low-memory", action="store_true", help="Use smaller models to reduce memory usage (main/supervisor: 7b, fast: phi3:mini). Overrides other model arguments.")
    args = parser.parse_args()

    # NEW: Prompt for objective if not provided
    if not args.objective:
        try:
            args.objective = input("Please enter the objective for the web agent: ")
            if not args.objective:
                print("[ERROR] Objective cannot be empty.")
                return
        except EOFError:
            print("\n[INFO] No objective provided. Exiting.")
            return

    # NEW: Default to low memory mode if not specified via flag
    if not args.low_memory:
        args.low_memory = config.LOW_MEMORY_MODE

    # Override models for low memory mode
    if args.low_memory:
        print("[INFO] Low memory mode enabled. Using smaller models.")
        args.model = config.LOW_MEMORY_MAIN_MODEL
        args.supervisor_model = config.LOW_MEMORY_SUPERVISOR_MODEL
        args.fast_model = config.LOW_MEMORY_FAST_MODEL
        args.vision_model = config.LOW_MEMORY_VISION_MODEL

    try:
        agent = WebAgent(objective=args.objective, start_url=args.url, model_name=args.model, supervisor_model_name=args.supervisor_model, fast_model_name=args.fast_model, vision_model_name=args.vision_model, max_steps=args.max_steps)
    except Exception as e:
        print(f"[FATAL] Failed to initialize the agent: {e}")
        return

    try:
        await agent.run()
    finally:
        # This block ensures that critique happens even if the run loop fails
        print("[INFO] Run loop finished. Proceeding to save and critique.")
        await agent.save_and_critique()
        # Ensure browser closes if it's still open, e.g., after an error
        await agent.browser.close()
        print("[INFO] Browser closed.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[INFO] User interrupted the program.")
