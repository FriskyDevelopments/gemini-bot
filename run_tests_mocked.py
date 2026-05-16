import sys
from unittest.mock import MagicMock

# Mock missing dependencies
for module in ['requests', 'telegram', 'telegram.ext', 'telegram.error', 'google', 'google.generativeai', 'oci', 'tweepy', 'supabase']:
    sys.modules[module] = MagicMock()

# Specifically for python-telegram-bot submodules
import telegram
telegram.__path__ = []
sys.modules['telegram.error'] = MagicMock()
sys.modules['telegram.ext'] = MagicMock()

import unittest
from test_main_modes import TestMainModes

if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMainModes)
    unittest.TextTestRunner().run(suite)
