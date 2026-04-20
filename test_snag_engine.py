import unittest
from unittest.mock import MagicMock, patch
import os
import sys
import logging

# Mock oci before importing main
mock_oci = MagicMock()
sys.modules['oci'] = mock_oci

# Ensure main uses the mock
import main

class TestSnagEngine(unittest.TestCase):

    @patch('main.os.getenv')
    @patch('main.logging.info')
    @patch('main.time.sleep')
    def test_snag_engine_missing_env(self, mock_sleep, mock_logging, mock_getenv):
        mock_getenv.side_effect = lambda k, default=None: None if k == "OCI_AD" else "some_value"
        main.snag_engine()
        mock_logging.assert_any_call("OCI environment variables are incomplete. Snag engine inactive.")

    @patch('main.os.getenv')
    @patch('oci.core.ComputeClient')
    @patch('main.logging.info')
    def test_snag_engine_init_fail(self, mock_logging, mock_compute_client, mock_getenv):
        mock_getenv.return_value = "some_value"
        mock_compute_client.side_effect = Exception("Init failed")
        main.snag_engine()
        mock_logging.assert_any_call("Failed to init OCI client: Init failed")

    @patch('main.os.getenv')
    @patch('oci.core.ComputeClient')
    @patch('main.logging.info')
    @patch('main.time.sleep')
    @patch('urllib.request.urlopen')
    def test_snag_engine_success(self, mock_urlopen, mock_sleep, mock_logging, mock_compute_client, mock_getenv):
        mock_getenv.return_value = "some_value"
        mock_client_instance = mock_compute_client.return_value
        mock_client_instance.launch_instance.return_value = MagicMock()
        main.snag_engine()
        mock_logging.assert_any_call("✅ MISSION SUCCESS: Bunker Secured!")
        mock_urlopen.assert_called()

    @patch('main.os.getenv')
    @patch('oci.core.ComputeClient')
    @patch('main.logging.info')
    @patch('main.time.sleep')
    @patch('urllib.request.urlopen')
    def test_snag_engine_out_of_capacity(self, mock_urlopen, mock_sleep, mock_logging, mock_compute_client, mock_getenv):
        mock_getenv.return_value = "some_value"
        mock_client_instance = mock_compute_client.return_value
        
        class MockServiceError(Exception):
            def __init__(self, message):
                self.message = message
        
        import oci
        oci.exceptions.ServiceError = MockServiceError
        mock_client_instance.launch_instance.side_effect = [MockServiceError("Out of host capacity"), MagicMock()]

        main.snag_engine()
        
        mock_logging.assert_any_call("❌ Status: Hub Capacity Full. Retrying...")
        mock_logging.assert_any_call("✅ MISSION SUCCESS: Bunker Secured!")
        mock_urlopen.assert_called()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    unittest.main()
