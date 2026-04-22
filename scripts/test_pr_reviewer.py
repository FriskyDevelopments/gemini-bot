import sys
import unittest
from unittest.mock import MagicMock, patch
import os

# Mock dependencies before importing
# Capture originals for cleanup
_orig_requests = sys.modules.get('requests')
_orig_github = sys.modules.get('github')
sys.modules['requests'] = MagicMock()
sys.modules['github'] = MagicMock()

from scripts.pr_reviewer import (
    _env_required,
    _build_filtered_diff,
    _groq_review,
    main,
    MAX_DIFF_CHARS
)

def tearDownModule():
    """Restore sys.modules to prevent test pollution."""
    if _orig_requests is None:
        sys.modules.pop('requests', None)
    else:
        sys.modules['requests'] = _orig_requests

    if _orig_github is None:
        sys.modules.pop('github', None)
    else:
        sys.modules['github'] = _orig_github

class TestPRReviewer(unittest.TestCase):

    def setUp(self):
        # Reset modules and environment for clean tests
        self.patcher = patch.dict(os.environ, {}, clear=True)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def test_env_required_success(self):
        os.environ['TEST_ENV_VAR'] = 'test_value'
        self.assertEqual(_env_required('TEST_ENV_VAR'), 'test_value')

    @patch('sys.exit')
    @patch('sys.stderr', new_callable=MagicMock)
    def test_env_required_missing(self, mock_stderr, mock_exit):
        _env_required('MISSING_ENV_VAR')
        mock_exit.assert_called_once_with(1)
        # We don't check exact print output since MagicMock covers it, but we could check the write call if needed

    def test_build_filtered_diff(self):
        mock_pull = MagicMock()

        file_valid = MagicMock()
        file_valid.filename = "test.py"
        file_valid.patch = "diff --git a/test.py"

        file_invalid_ext = MagicMock()
        file_invalid_ext.filename = "test.txt"
        file_invalid_ext.patch = "diff --git a/test.txt"

        file_no_patch = MagicMock()
        file_no_patch.filename = "test2.ts"
        file_no_patch.patch = None

        mock_pull.get_files.return_value = [file_valid, file_invalid_ext, file_no_patch]

        result = _build_filtered_diff(mock_pull)
        self.assertIn("### test.py", result)
        self.assertIn("diff --git a/test.py", result)
        self.assertNotIn("test.txt", result)
        self.assertNotIn("test2.ts", result)

    @patch('scripts.pr_reviewer.requests.post')
    def test_groq_review_no_key(self, mock_post):
        self.assertIsNone(_groq_review("some diff", "main"))
        mock_post.assert_not_called()

    @patch('scripts.pr_reviewer.requests.post')
    def test_groq_review_success(self, mock_post):
        os.environ['GROQ_API_KEY'] = 'fake_key'

        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "  Looks good!  "
                    }
                }
            ]
        }
        mock_post.return_value = mock_response

        result = _groq_review("some diff", "main")
        self.assertEqual(result, "Looks good!")

    @patch('scripts.pr_reviewer.requests.post')
    def test_groq_review_failed_request(self, mock_post):
        os.environ['GROQ_API_KEY'] = 'fake_key'

        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.raise_for_status.side_effect = Exception("HTTP Error")
        mock_post.return_value = mock_response

        with self.assertRaises(Exception):
            _groq_review("some diff", "main")

    @patch('scripts.pr_reviewer.requests.post')
    def test_groq_review_unexpected_shape(self, mock_post):
        os.environ['GROQ_API_KEY'] = 'fake_key'

        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {"invalid": "shape"}
        mock_post.return_value = mock_response

        with self.assertRaises(RuntimeError):
            _groq_review("some diff", "main")

    @patch('scripts.pr_reviewer.Github')
    @patch('scripts.pr_reviewer._groq_review')
    @patch('scripts.pr_reviewer._build_filtered_diff')
    def test_main_no_diff(self, mock_build_diff, mock_groq_review, mock_github_class):
        os.environ['GITHUB_TOKEN'] = 'token'
        os.environ['GITHUB_REPOSITORY'] = 'repo'
        os.environ['PR_NUMBER'] = '1'

        mock_build_diff.return_value = ""

        mock_pr = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_pr
        mock_g = MagicMock()
        mock_g.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_g

        main()

        mock_pr.create_issue_comment.assert_called_once()
        self.assertIn("No `.py`, `.ts`, or `.tsx` file changes", mock_pr.create_issue_comment.call_args[0][0])
        mock_groq_review.assert_not_called()

    @patch('scripts.pr_reviewer.Github')
    @patch('scripts.pr_reviewer._groq_review')
    @patch('scripts.pr_reviewer._build_filtered_diff')
    def test_main_with_diff_truncated(self, mock_build_diff, mock_groq_review, mock_github_class):
        os.environ['GITHUB_TOKEN'] = 'token'
        os.environ['GITHUB_REPOSITORY'] = 'repo'
        os.environ['PR_NUMBER'] = '1'

        long_diff = "a" * (MAX_DIFF_CHARS + 100)
        mock_build_diff.return_value = long_diff
        mock_groq_review.return_value = "Review findings"

        mock_pr = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_pr
        mock_g = MagicMock()
        mock_g.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_g

        main()

        mock_groq_review.assert_called_once()
        called_diff = mock_groq_review.call_args[0][0]
        # Exact truncation check
        expected_truncated = long_diff[:MAX_DIFF_CHARS]
        self.assertTrue(called_diff.startswith(expected_truncated))
        self.assertIn("Diff truncated for review", called_diff)

        mock_pr.create_issue_comment.assert_called_once()
        self.assertIn("Review findings", mock_pr.create_issue_comment.call_args[0][0])

if __name__ == '__main__':
    unittest.main()