import sys
from unittest.mock import MagicMock

# Mock missing dependencies
for module in ['requests', 'telegram', 'telegram.ext', 'telegram.error', 'google', 'google.generativeai', 'oci', 'tweepy', 'supabase']:
    sys.modules[module] = MagicMock()

httpx_mock = MagicMock()
httpx_mock.ConnectError = type("ConnectError", (Exception,), {})
sys.modules['httpx'] = httpx_mock

# Specifically for python-telegram-bot submodules
import telegram
telegram.__path__ = []
sys.modules['telegram.error'] = MagicMock()
sys.modules['telegram.ext'] = MagicMock()

import unittest
from test_main_modes import TestMainModes, TestMainModesAsync

if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestMainModes))
    suite.addTests(loader.loadTestsFromTestCase(TestMainModesAsync))
    unittest.TextTestRunner().run(suite)
