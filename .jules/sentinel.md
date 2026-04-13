## 2025-04-13 - [Webhook Security & SSRF Protection]
**Vulnerability:** The GitHub webhook endpoint lacked signature verification, and the `perform_review` function was susceptible to SSRF by fetching arbitrary URLs from the payload.
**Learning:** Webhook endpoints that fetch external resources based on payload data are high-risk for SSRF and unauthorized action triggering if not protected by both signature verification and strict URL allowlisting.
**Prevention:** Always verify webhook signatures (e.g., HMAC-SHA256) and implement strict prefix validation for any URLs extracted from the payload before making outgoing requests.
