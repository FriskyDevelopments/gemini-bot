# Sentinel's Journal - Security Critical Learnings

## 2025-05-15 - GitHub Webhook Security & SSRF Prevention
**Vulnerability:** The GitHub webhook endpoint was open to the public without signature verification, and the bot made outbound requests to URLs provided in the webhook payload without validation.
**Learning:** Webhooks that trigger expensive operations (like LLM generation) or perform outbound requests based on payload data must be strictly authenticated and validated to prevent unauthorized usage and SSRF attacks.
**Prevention:** Always implement HMAC-SHA256 signature verification for GitHub webhooks and validate all outbound request destinations against a whitelist of trusted domains.

## 2025-05-22 - Secrets Migration & Contextual Validation
**Vulnerability:** Hardcoded admin IDs and bypass passwords in `main.py` were migrated to environment variables.
**Learning:** Migration of secrets must be paired with careful validation of how those variables are used in external tools (e.g., Doppler CLI) and ensuring sanitization doesn't break functional requirements (e.g., repo names containing dots).
**Prevention:** Always verify CLI flag meanings before renaming variables (e.g., `-p` for project name vs passphrase) and ensure input sanitization for security (path traversal) respects valid character sets for the target service (GitHub repos allow dots).
