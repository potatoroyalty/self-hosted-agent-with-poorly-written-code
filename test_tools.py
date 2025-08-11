import subprocess
import time
import asyncio
import unittest
from unittest.mock import patch, MagicMock, AsyncMock
from agent import WebAgent, AIModel, BrowserController
from vision_tools import AnalyzeVisualLayoutTool
import config

class TestVisionTools(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server_process = subprocess.Popen(['python', 'test_environment/test_server.py'])
        time.sleep(2)

    @classmethod
    def tearDownClass(cls):
        cls.server_process.terminate()
        cls.server_process.wait()

    @patch('agent.BrowserController')
    @patch('agent.AIModel')
    def test_analyze_visual_layout(self, MockAIModel, MockBrowserController):
        # Create a mock instance of AIModel that passes Pydantic validation
        mock_ai_instance = MagicMock(spec=AIModel)
        mock_ai_instance.analyze_layout = AsyncMock(return_value="This is a test response from the mock AI.")

        # Add the model attributes that WebAgent expects
        mock_ai_instance.main_model = MagicMock()
        mock_ai_instance.fast_model = MagicMock()
        mock_ai_instance.supervisor_model = MagicMock()
        mock_ai_instance.vision_model = MagicMock()
        mock_ai_instance.scripter_model = MagicMock()

        MockAIModel.return_value = mock_ai_instance

        # Create a mock instance of BrowserController
        mock_browser_instance = MagicMock(spec=BrowserController)
        mock_browser_instance.get_screenshot_as_base64 = AsyncMock(return_value="fake_screenshot_data")
        MockBrowserController.return_value = mock_browser_instance

        async def run_test():
            # Initialize WebAgent - it will use the mocked classes
            agent = WebAgent(
                objective="Test visual layout analysis",
                start_url="http://localhost:8000/login.html",
            )
            # The agent's browser and ai_model will be the mocked instances
            self.assertIsInstance(agent.ai_model, MagicMock)
            self.assertIsInstance(agent.browser, MagicMock)

            # Initialize the tool with the mocked components
            tool = AnalyzeVisualLayoutTool(browser=agent.browser, ai_model=agent.ai_model)

            question = "Is this a login form?"
            result = await tool._arun(question=question)

            print(f"Tool Result: {result}")

            # Assertions
            self.assertEqual(result, "This is a test response from the mock AI.")
            # Verify that the underlying methods were called
            agent.browser.get_screenshot_as_base64.assert_called_once()
            agent.ai_model.analyze_layout.assert_called_once_with("fake_screenshot_data", question)

        asyncio.run(run_test())

if __name__ == "__main__":
    unittest.main()
