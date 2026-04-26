# Sentinel's Journal - Security Critical Learnings

## 2025-05-15 - GitHub Webhook Security & SSRF Prevention
**Vulnerability:** The GitHub webhook endpoint was open to the public without signature verification, and the bot made outbound requests to URLs provided in the webhook payload without validation.
**Learning:** Webhooks that trigger expensive operations (like LLM generation) or perform outbound requests based on payload data must be strictly authenticated and validated to prevent unauthorized usage and SSRF attacks.
**Prevention:** Always implement HMAC-SHA256 signature verification for GitHub webhooks and validate all outbound request destinations against a whitelist of trusted domains.

## 2025-05-22 - Secrets Migration & Contextual Validation
**Vulnerability:** Hardcoded admin IDs and bypass passwords in `main.py` were migrated to environment variables.
**Learning:** Migration of secrets must be paired with careful validation of how those variables are used in external tools (e.g., Doppler CLI) and ensuring sanitization doesn't break functional requirements (e.g., repo names containing dots).
**Prevention:** Always verify CLI flag meanings before renaming variables (e.g., `-p` for project name vs passphrase) and ensure input sanitization for security (path traversal) respects valid character sets for the target service (GitHub repos allow dots).

## 2025-05-30 - SSRF Validation & Precise Auth Logic
**Vulnerability:** SSRF protection using `.startswith()` was vulnerable to hostname manipulation, and a bypass password check used `in` instead of exact equality.
**Learning:** String prefix checks for URLs can be bypassed with clever hostname/subdomain construction. Likewise, using substring matches for passwords allows accidental or intentional leakage.
**Prevention:** Use `urllib.parse.urlparse` to strictly validate schemes and hostnames for outbound requests. Always use exact equality (`==`) for password or token comparisons.

## 2025-06-05 - Information Leakage & Resource Exhaustion
**Vulnerability:** Raw exception details and unvalidated user input lengths were exposed in Telegram responses and processed without timeouts.
**Learning:** Exposing raw exceptions (`str(e)`) in bot responses can leak internal state, file paths, or API structures. Lack of timeouts on `httpx`/`requests` calls allows third-party latency to hang the bot process.
**Prevention:** Always use generic error messages for end-users while logging the actual exception internally. Implement strict timeouts (e.g., 10s) for all external network requests and enforce length limits on user-provided text to prevent resource exhaustion.

## 2025-06-12 - User-Facing Tracebacks & Weak Bypass Auth
**Vulnerability:** User-facing error messages included full stack traces via `traceback.format_exc()`, and the 'antigravity' bypass used a hardcoded, case-insensitive substring match for a password.
**Learning:** Providing stack traces to end-users facilitates reconnaissance by exposing internal file structures and logic flows. Using `in` for password comparisons allows for significant entropy reduction and accidental bypasses.
**Prevention:** Strictly separate internal logging from user-facing responses. Use `logging.error(..., exc_info=True)` for developers and generic "Internal error" messages for users. Use exact string equality (`==`) and environment-managed secrets for all authentication bypasses.

## 2025-06-19 - Broad Keyword Triggers & Missing Authorization
**Vulnerability:** Sensitive cross-platform operations (like promo blasts) were triggered by broad substring matches ("promo" in text_lower) without verifying the user's privileged status (is_alpha).
**Learning:** Using keyword matching instead of strict command prefixes (/) for high-impact actions allows for accidental triggers and bypasses intended authorization boundaries if those checks are assumed from context (e.g., chat ID) rather than user identity.
**Prevention:** Always use strict command prefix matching for sensitive operations and explicitly verify user authorization (is_alpha) regardless of the chat context.
