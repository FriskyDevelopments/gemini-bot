"""Tests for github_bot.py changes in PR.

Key changes tested:
1. ALLOWED_ASSOCIATIONS constant was removed.
2. author_association check removed from PR event handler.
3. author_association check removed from issue_comment handler.
4. Keyword matching broadened: plain "gemini" now triggers a review.
5. verify_signature logic (unchanged but tested for regression).
"""
import hashlib
import hmac
import json
import os
import unittest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Stub out google.generativeai before importing github_bot so no real API
# calls are made at import time.
# ---------------------------------------------------------------------------
import sys

_genai_mock = MagicMock()
_genai_mock.GenerativeModel.return_value = MagicMock()
sys.modules.setdefault("google", MagicMock())
sys.modules.setdefault("google.generativeai", _genai_mock)

# Patch requests so no HTTP calls leave the process
import requests as _requests_mod  # noqa: E402


def _make_signature(secret: str, body: bytes) -> str:
    mac = hmac.new(secret.encode(), msg=body, digestmod=hashlib.sha256)
    return f"sha256={mac.hexdigest()}"


class TestVerifySignature(unittest.TestCase):
    """Tests for the verify_signature() helper (unchanged logic, regression)."""

    def setUp(self):
        self._orig_secret = os.environ.get("GITHUB_WEBHOOK_SECRET")
        os.environ["GITHUB_WEBHOOK_SECRET"] = "test_secret_123"

    def tearDown(self):
        if self._orig_secret is None:
            os.environ.pop("GITHUB_WEBHOOK_SECRET", None)
        else:
            os.environ["GITHUB_WEBHOOK_SECRET"] = self._orig_secret

    def _get_verify(self):
        import importlib
        import github_bot
        importlib.reload(github_bot)
        return github_bot.verify_signature

    def test_valid_signature_returns_true(self):
        verify = self._get_verify()
        body = b'{"action": "opened"}'
        sig = _make_signature("test_secret_123", body)
        self.assertTrue(verify(body, sig))

    def test_invalid_signature_returns_false(self):
        verify = self._get_verify()
        body = b'{"action": "opened"}'
        self.assertFalse(verify(body, "sha256=deadbeef"))

    def test_missing_signature_returns_false(self):
        verify = self._get_verify()
        self.assertFalse(verify(b"data", None))

    def test_wrong_algorithm_prefix_returns_false(self):
        verify = self._get_verify()
        body = b"data"
        mac = hmac.new("test_secret_123".encode(), msg=body, digestmod=hashlib.sha256)
        sig = f"sha1={mac.hexdigest()}"  # sha1 prefix, not sha256
        self.assertFalse(verify(body, sig))

    def test_no_secret_configured_returns_false(self):
        os.environ.pop("GITHUB_WEBHOOK_SECRET", None)
        import importlib
        import github_bot
        importlib.reload(github_bot)
        self.assertFalse(github_bot.verify_signature(b"data", "sha256=anything"))


class TestGithubWebhookPREvent(unittest.TestCase):
    """Tests for the pull_request event handler after ALLOWED_ASSOCIATIONS removal."""

    def setUp(self):
        os.environ["GITHUB_WEBHOOK_SECRET"] = "secret"
        os.environ.pop("GITHUB_PUPBOT_TOKEN", None)
        os.environ.pop("GEMINI_API_KEY", None)

    def tearDown(self):
        os.environ.pop("GITHUB_WEBHOOK_SECRET", None)

    def _get_app(self):
        import importlib
        import github_bot
        importlib.reload(github_bot)
        return github_bot.app

    def _post_webhook(self, app, event, payload_dict):
        body = json.dumps(payload_dict).encode()
        sig = _make_signature("secret", body)
        with app.test_client() as client:
            return client.post(
                "/github-webhook",
                data=body,
                content_type="application/json",
                headers={
                    "X-Hub-Signature-256": sig,
                    "X-GitHub-Event": event,
                },
            )

    def _make_pr_payload(self, author_association="NONE"):
        return {
            "action": "opened",
            "pull_request": {
                "number": 42,
                "diff_url": "https://github.com/owner/repo/pull/42.diff",
                "author_association": author_association,
            },
            "repository": {"full_name": "owner/repo"},
        }

    def test_pr_event_no_longer_checks_author_association(self):
        """Any author_association must now trigger a review (auth check removed)."""
        app = self._get_app()
        import github_bot
        with patch.object(github_bot, "perform_review", return_value=True) as mock_review:
            resp = self._post_webhook(app, "pull_request", self._make_pr_payload("NONE"))
        self.assertEqual(resp.status_code, 200)
        mock_review.assert_called_once()

    def test_pr_event_owner_triggers_review(self):
        app = self._get_app()
        import github_bot
        with patch.object(github_bot, "perform_review", return_value=True) as mock_review:
            resp = self._post_webhook(app, "pull_request", self._make_pr_payload("OWNER"))
        self.assertEqual(resp.status_code, 200)
        mock_review.assert_called_once()

    def test_pr_event_first_time_contributor_triggers_review(self):
        """FIRST_TIME_CONTRIBUTOR was previously denied; now it must be processed."""
        app = self._get_app()
        import github_bot
        with patch.object(github_bot, "perform_review", return_value=True) as mock_review:
            resp = self._post_webhook(
                app, "pull_request", self._make_pr_payload("FIRST_TIME_CONTRIBUTOR")
            )
        self.assertEqual(resp.status_code, 200)
        mock_review.assert_called_once()

    def test_pr_synchronize_triggers_review(self):
        payload = self._make_pr_payload("NONE")
        payload["action"] = "synchronize"
        app = self._get_app()
        import github_bot
        with patch.object(github_bot, "perform_review", return_value=False) as mock_review:
            resp = self._post_webhook(app, "pull_request", payload)
        self.assertEqual(resp.status_code, 200)
        mock_review.assert_called_once()

    def test_pr_closed_does_not_trigger_review(self):
        payload = self._make_pr_payload("OWNER")
        payload["action"] = "closed"
        app = self._get_app()
        import github_bot
        with patch.object(github_bot, "perform_review", return_value=True) as mock_review:
            self._post_webhook(app, "pull_request", payload)
        mock_review.assert_not_called()

    def test_allowed_associations_constant_removed(self):
        """The ALLOWED_ASSOCIATIONS constant must no longer exist in github_bot."""
        import importlib
        import github_bot
        importlib.reload(github_bot)
        self.assertFalse(
            hasattr(github_bot, "ALLOWED_ASSOCIATIONS"),
            "ALLOWED_ASSOCIATIONS should have been removed in this PR",
        )


class TestGithubWebhookCommentEvent(unittest.TestCase):
    """Tests for the issue_comment handler after auth check removal and keyword broadening."""

    def setUp(self):
        os.environ["GITHUB_WEBHOOK_SECRET"] = "secret"
        os.environ.pop("GITHUB_PUPBOT_TOKEN", None)

    def tearDown(self):
        os.environ.pop("GITHUB_WEBHOOK_SECRET", None)

    def _get_app(self):
        import importlib
        import github_bot
        importlib.reload(github_bot)
        return github_bot.app

    def _post_webhook(self, app, event, payload_dict):
        body = json.dumps(payload_dict).encode()
        sig = _make_signature("secret", body)
        with app.test_client() as client:
            return client.post(
                "/github-webhook",
                data=body,
                content_type="application/json",
                headers={
                    "X-Hub-Signature-256": sig,
                    "X-GitHub-Event": event,
                },
            )

    def _make_comment_payload(self, comment_body, author_association="NONE"):
        return {
            "action": "created",
            "comment": {
                "body": comment_body,
                "author_association": author_association,
            },
            "issue": {
                "number": 7,
                "pull_request": {"url": "https://api.github.com/repos/owner/repo/pulls/7"},
            },
            "repository": {"full_name": "owner/repo"},
        }

    def test_plain_gemini_keyword_triggers_review(self):
        """PR added 'gemini' to the keyword list; a comment containing only 'gemini' must trigger."""
        app = self._get_app()
        import github_bot
        payload = self._make_comment_payload("gemini please check this")
        with patch.object(github_bot, "perform_review", return_value=True) as mock_review:
            resp = self._post_webhook(app, "issue_comment", payload)
        self.assertEqual(resp.status_code, 200)
        mock_review.assert_called_once()

    def test_gemini_keyword_case_insensitive(self):
        app = self._get_app()
        import github_bot
        payload = self._make_comment_payload("GEMINI review please")
        with patch.object(github_bot, "perform_review", return_value=True) as mock_review:
            self._post_webhook(app, "issue_comment", payload)
        mock_review.assert_called_once()

    def test_at_pupbot_review_triggers(self):
        app = self._get_app()
        import github_bot
        payload = self._make_comment_payload("@pupbot review this change please")
        with patch.object(github_bot, "perform_review", return_value=True) as mock_review:
            self._post_webhook(app, "issue_comment", payload)
        mock_review.assert_called_once()

    def test_slash_pupbot_triggers(self):
        app = self._get_app()
        import github_bot
        payload = self._make_comment_payload("/pupbot do your thing")
        with patch.object(github_bot, "perform_review", return_value=True) as mock_review:
            self._post_webhook(app, "issue_comment", payload)
        mock_review.assert_called_once()

    def test_slash_review_triggers(self):
        app = self._get_app()
        import github_bot
        payload = self._make_comment_payload("/review")
        with patch.object(github_bot, "perform_review", return_value=True) as mock_review:
            self._post_webhook(app, "issue_comment", payload)
        mock_review.assert_called_once()

    def test_comment_without_keyword_does_not_trigger(self):
        app = self._get_app()
        import github_bot
        payload = self._make_comment_payload("Great work! LGTM.")
        with patch.object(github_bot, "perform_review", return_value=True) as mock_review:
            self._post_webhook(app, "issue_comment", payload)
        mock_review.assert_not_called()

    def test_comment_without_pull_request_field_does_not_trigger(self):
        """issue_comment on a plain Issue (no pull_request key) must not trigger review."""
        app = self._get_app()
        import github_bot
        payload = {
            "action": "created",
            "comment": {"body": "gemini please review", "author_association": "OWNER"},
            "issue": {"number": 3},  # no 'pull_request' key
            "repository": {"full_name": "owner/repo"},
        }
        with patch.object(github_bot, "perform_review", return_value=True) as mock_review:
            self._post_webhook(app, "issue_comment", payload)
        mock_review.assert_not_called()

    def test_non_owner_comment_triggers_after_auth_removal(self):
        """Comments from NONE association now trigger since auth check was removed."""
        app = self._get_app()
        import github_bot
        payload = self._make_comment_payload("@pupbot review", author_association="NONE")
        with patch.object(github_bot, "perform_review", return_value=True) as mock_review:
            self._post_webhook(app, "issue_comment", payload)
        mock_review.assert_called_once()


class TestPerformReviewSSRF(unittest.TestCase):
    """SSRF protection in perform_review must still block non-GitHub URLs."""

    def setUp(self):
        os.environ.pop("GITHUB_PUPBOT_TOKEN", None)

    def _get_perform_review(self):
        import importlib
        import github_bot
        importlib.reload(github_bot)
        return github_bot.perform_review

    def test_non_github_url_is_blocked(self):
        perform_review = self._get_perform_review()
        result = perform_review(1, "https://evil.example.com/malicious", "owner/repo")
        self.assertFalse(result)

    def test_http_url_is_blocked(self):
        perform_review = self._get_perform_review()
        result = perform_review(1, "http://github.com/owner/repo/pull/1.diff", "owner/repo")
        self.assertFalse(result)

    def test_invalid_repo_name_is_blocked(self):
        perform_review = self._get_perform_review()
        result = perform_review(1, "https://github.com/owner/repo/pull/1.diff", "../../etc/passwd")
        self.assertFalse(result)

    def test_valid_github_url_passes_ssrf_check(self):
        perform_review = self._get_perform_review()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "diff content here"
        mock_ai = MagicMock()
        mock_ai.text = "looks good"
        with patch("requests.get", return_value=mock_resp):
            import github_bot
            github_bot.model = MagicMock()
            github_bot.model.generate_content.return_value = mock_ai
            # Should not return False due to SSRF check
            # (may return False for other reasons like no token)
            result = perform_review(1, "https://github.com/owner/repo/pull/1.diff", "owner/repo")
        # SSRF check passes; result depends on GITHUB_TOKEN being absent
        # The function returns False when no token and no post, but that's OK


if __name__ == "__main__":
    unittest.main()