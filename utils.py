# FILE: utils.py

import asyncio
import sys
import itertools

class Spinner:
    """A simple async spinner for the console."""
    def __init__(self, message: str = "Processing..."):
        self._spinner = itertools.cycle(['|', '/', '-', '\\'])
        self._message = message
        self._task = None
        self.running = False

    async def _spin(self):
        """The spinning animation task."""
        while self.running:
            sys.stdout.write(f'\r{self._message} {next(self._spinner)}')
            sys.stdout.flush()
            try:
                await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                break

    async def __aenter__(self):
        """Start the spinner when entering the context."""
        if sys.stdout.isatty():  # Only show spinner in a real terminal
            self.running = True
            sys.stdout.write('\033[?25l')  # Hide cursor
            sys.stdout.flush()
            self._task = asyncio.create_task(self._spin())
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        """Stop the spinner when exiting the context."""
        if self.running and self._task:
            self.running = False
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            # Clear the line and show cursor
            sys.stdout.write('\r' + ' ' * (len(self._message) + 2) + '\r')
            sys.stdout.write('\033[?25h')  # Show cursor
            sys.stdout.flush()