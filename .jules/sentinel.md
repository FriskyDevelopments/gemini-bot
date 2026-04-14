# Sentinel's Journal - Security Critical Learnings

## 2025-05-15 - GitHub Webhook Security & SSRF Prevention
**Vulnerability:** The GitHub webhook endpoint was open to the public without signature verification, and the bot made outbound requests to URLs provided in the webhook payload without validation.
**Learning:** Webhooks that trigger expensive operations (like LLM generation) or perform outbound requests based on payload data must be strictly authenticated and validated to prevent unauthorized usage and SSRF attacks.
**Prevention:** Always implement HMAC-SHA256 signature verification for GitHub webhooks and validate all outbound request destinations against a whitelist of trusted domains.
