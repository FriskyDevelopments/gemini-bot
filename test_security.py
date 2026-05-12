import unittest
import hmac
import hashlib
import json
import os
from github_bot import app

class TestSecurity(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        os.environ['GITHUB_WEBHOOK_SECRET'] = 'test_secret'
        # Re-initialize the secret in the app context
        import github_bot
        github_bot.GITHUB_WEBHOOK_SECRET = 'test_secret'

    def test_webhook_no_signature(self):
        response = self.app.post('/github-webhook', data=json.dumps({'action': 'opened'}), content_type='application/json')
        self.assertEqual(response.status_code, 403)

    def test_webhook_invalid_signature(self):
        headers = {'X-Hub-Signature-256': 'sha256=invalid'}
        response = self.app.post('/github-webhook', data=json.dumps({'action': 'opened'}), headers=headers, content_type='application/json')
        self.assertEqual(response.status_code, 403)

    def test_webhook_valid_signature(self):
        payload = json.dumps({'action': 'opened', 'pull_request': {'diff_url': 'https://github.com/foo/bar/diff', 'number': 1}, 'repository': {'full_name': 'foo/bar'}})
        signature = 'sha256=' + hmac.new(b'test_secret', msg=payload.encode('utf-8'), digestmod=hashlib.sha256).hexdigest()
        headers = {'X-Hub-Signature-256': signature, 'X-GitHub-Event': 'pull_request'}

        # We need to mock perform_review to avoid external calls
        import github_bot
        original_perform_review = github_bot.perform_review
        github_bot.perform_review = lambda *args, **kwargs: True

        try:
            response = self.app.post('/github-webhook', data=payload, headers=headers, content_type='application/json')
            self.assertEqual(response.status_code, 200)
        finally:
            github_bot.perform_review = original_perform_review

    def test_perform_review_ssrf_protection(self):
        from github_bot import perform_review
        # Should fail for non-github URLs
        self.assertFalse(perform_review(1, 'https://malicious.com', 'foo/bar'))
        # Should fail for internal IPs
        self.assertFalse(perform_review(1, 'http://127.0.0.1', 'foo/bar'))

        import requests
        from unittest.mock import patch
        with patch('requests.get') as mocked_get:
            mocked_get.return_value.status_code = 200
            mocked_get.return_value.text = "diff content"
            with patch('github_bot.model.generate_content') as mocked_genai:
                mocked_genai.return_value.text = "review"
                # This should reach requests.get
                perform_review(1, 'https://github.com/foo/bar', 'foo/bar')
                self.assertTrue(mocked_get.called)

    def test_perform_review_repo_validation(self):
        from github_bot import perform_review
        # Invalid repo names
        self.assertFalse(perform_review(1, 'https://github.com/foo/bar', 'invalid_repo'))
        self.assertFalse(perform_review(1, 'https://github.com/foo/bar', 'foo/bar/baz'))
        self.assertFalse(perform_review(1, 'https://github.com/foo/bar', '../../etc/passwd'))

    def test_webhook_manual_review_authorization(self):
        import github_bot
        from unittest.mock import patch

        # Payload for manual review trigger
        payload_dict = {
            'action': 'created',
            'issue': {'number': 1, 'pull_request': {'url': 'https://api.github.com/repos/foo/bar/pulls/1'}},
            'comment': {'body': '@pupbot review', 'author_association': 'NONE'},
            'repository': {'full_name': 'foo/bar'}
        }

        def send_payload(p):
            p_json = json.dumps(p)
            sig = 'sha256=' + hmac.new(b'test_secret', msg=p_json.encode('utf-8'), digestmod=hashlib.sha256).hexdigest()
            headers = {'X-Hub-Signature-256': sig, 'X-GitHub-Event': 'issue_comment'}
            return self.app.post('/github-webhook', data=p_json, headers=headers, content_type='application/json')

        with patch('github_bot.perform_review') as mocked_review:
            # 1. Unauthorized user (NONE)
            resp = send_payload(payload_dict)
            self.assertEqual(resp.status_code, 200)
            data = json.loads(resp.data)
            self.assertEqual(data['status'], 'denied')
            self.assertFalse(mocked_review.called)

            # 2. Authorized user (MEMBER)
            payload_dict['comment']['author_association'] = 'MEMBER'
            resp = send_payload(payload_dict)
            self.assertEqual(resp.status_code, 200)
            data = json.loads(resp.data)
            self.assertEqual(data['status'], 'ok')
            self.assertTrue(mocked_review.called)

if __name__ == '__main__':
    unittest.main()