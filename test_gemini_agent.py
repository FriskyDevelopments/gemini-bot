"""Tests for gemini_agent.py changes in PR.

The PR changed run_cmd:
  - Before: subprocess.check_output(shlex.split(cmd), shell=False, ...)
            except Exception: return "Error: Command execution failed."
  - After:  subprocess.check_output(cmd, shell=True, ...)
            except Exception as e: return f"Error: {str(e)}"

Tests verify:
1. Successful commands return stdout.
2. Failing commands return "Error: <exception details>" (not the old generic message).
3. The command is passed as a string with shell=True.
"""
import subprocess
import unittest
from unittest.mock import MagicMock, patch


# We patch genai.configure and genai.GenerativeModel at module-load time so
# that importing gemini_agent does not require a real API key.
_genai_patch = patch.dict(
    "sys.modules",
    {
        "google": MagicMock(),
        "google.generativeai": MagicMock(),
    },
)


def setUpModule():
    _genai_patch.start()


def tearDownModule():
    _genai_patch.stop()


class TestRunCmd(unittest.TestCase):
    def _get_run_cmd(self):
        """Import run_cmd fresh after patching."""
        import importlib
        import gemini_agent
        importlib.reload(gemini_agent)
        return gemini_agent.run_cmd

    def test_successful_command_returns_output(self):
        run_cmd = self._get_run_cmd()
        with patch("subprocess.check_output", return_value="hello world\n") as mock_co:
            result = run_cmd("echo hello world")
        self.assertEqual(result, "hello world\n")
        mock_co.assert_called_once()

    def test_successful_command_passes_shell_true(self):
        """The PR changed shell=False → shell=True; verify the call site."""
        run_cmd = self._get_run_cmd()
        with patch("subprocess.check_output", return_value="ok") as mock_co:
            run_cmd("ls -la")
        _, kwargs = mock_co.call_args
        self.assertTrue(kwargs.get("shell"), "shell=True must be set after the PR change")

    def test_successful_command_passes_cmd_as_string_not_list(self):
        """After the PR, cmd is passed directly (not split by shlex)."""
        run_cmd = self._get_run_cmd()
        with patch("subprocess.check_output", return_value="ok") as mock_co:
            run_cmd("find . -maxdepth 2")
        args, _ = mock_co.call_args
        # First positional arg must be the raw string, not a list
        self.assertIsInstance(args[0], str, "cmd should be passed as a string with shell=True")

    def test_exception_returns_error_string_with_details(self):
        """After the PR: returns f'Error: {str(e)}', not the old generic message."""
        run_cmd = self._get_run_cmd()
        exc = subprocess.CalledProcessError(1, "bad_cmd", output="oops")
        with patch("subprocess.check_output", side_effect=exc):
            result = run_cmd("bad_cmd")
        self.assertTrue(result.startswith("Error: "), f"Expected 'Error: ...' prefix, got: {result!r}")
        # Must NOT be the old generic message
        self.assertNotEqual(result, "Error: Command execution failed.")

    def test_exception_message_is_included_in_output(self):
        """The exception string representation must appear in the return value."""
        run_cmd = self._get_run_cmd()
        exc = RuntimeError("Something went wrong with cmd")
        with patch("subprocess.check_output", side_effect=exc):
            result = run_cmd("any_cmd")
        self.assertIn("Something went wrong with cmd", result)

    def test_generic_exception_also_handled(self):
        """Any Exception subclass is caught and returned as error string."""
        run_cmd = self._get_run_cmd()
        with patch("subprocess.check_output", side_effect=OSError("file not found")):
            result = run_cmd("nonexistent_binary")
        self.assertTrue(result.startswith("Error: "))
        self.assertIn("file not found", result)

    def test_text_mode_is_requested(self):
        """text=True must be set so output is a str not bytes."""
        run_cmd = self._get_run_cmd()
        with patch("subprocess.check_output", return_value="output") as mock_co:
            run_cmd("cmd")
        _, kwargs = mock_co.call_args
        self.assertTrue(kwargs.get("text"), "text=True must be set")

    def test_stderr_redirected_to_stdout(self):
        """stderr=subprocess.STDOUT must be set to capture error output."""
        run_cmd = self._get_run_cmd()
        with patch("subprocess.check_output", return_value="output") as mock_co:
            run_cmd("cmd")
        _, kwargs = mock_co.call_args
        self.assertEqual(kwargs.get("stderr"), subprocess.STDOUT)


if __name__ == "__main__":
    unittest.main()