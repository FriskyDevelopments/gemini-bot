import unittest
from unittest.mock import patch

import github_bot


class TestSecurity(unittest.TestCase):
    def test_verify_signature_rejects_when_secret_missing_and_unsigned_not_allowed(self):
        with patch.object(github_bot, "GITHUB_WEBHOOK_SECRET", None), patch.object(
            github_bot, "ALLOW_MISSING_WEBHOOK_SECRET", False
        ):
            self.assertFalse(github_bot.verify_signature(b"{}", "sha256=abc"))

    def test_verify_signature_allows_when_dev_flag_enabled(self):
        with patch.object(github_bot, "GITHUB_WEBHOOK_SECRET", None), patch.object(
            github_bot, "ALLOW_MISSING_WEBHOOK_SECRET", True
        ):
            self.assertTrue(github_bot.verify_signature(b"{}", None))

    def test_webhook_invalid_json_returns_400(self):
        client = github_bot.app.test_client()
        with patch.object(github_bot, "verify_signature", return_value=True):
            resp = client.post(
                "/github-webhook",
                data="not-json",
                content_type="application/json",
                headers={"X-GitHub-Event": "pull_request"},
            )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_json(), {"error": "Invalid JSON payload"})

    def test_perform_review_sets_timeouts_for_http_calls(self):
        class _DiffResponse:
            status_code = 200
            text = "diff --git a/a b/b"

        class _AiResponse:
            text = "Looks good"

        class _PostResponse:
            status_code = 201
            text = ""

        with patch.object(github_bot, "GITHUB_TOKEN", "token"), patch(
            "github_bot.requests.get", return_value=_DiffResponse()
        ) as mock_get, patch("github_bot.requests.post", return_value=_PostResponse()) as mock_post, patch.object(
            github_bot, "model"
        ) as mock_model:
            mock_model.generate_content.return_value = _AiResponse()
            ok = github_bot.perform_review(1, "owner/repo")

        self.assertTrue(ok)
        self.assertEqual(mock_get.call_args.kwargs["timeout"], github_bot.HTTP_TIMEOUT)
        self.assertEqual(mock_post.call_args.kwargs["timeout"], github_bot.HTTP_TIMEOUT)


if __name__ == "__main__":
    unittest.main()
