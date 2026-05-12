# Fenrir Go-Live Environment Checklist

> **Do not expose secrets.** All values listed here must be set as environment variables
> (Doppler, Railway / Render / Heroku config vars, or a `.env` file that is `.gitignore`d).
> Never commit secrets to the repository.

---

## 1. Telegram Bot

| Variable | Required | Notes |
|---|---|---|
| `TELEGRAM_TOKEN` | ✅ Yes | Bot token from `@BotFather`. Bot will refuse to start without it (`TOKEN` is read at module load). |

**Validation:** `main.py` line 34 — `TOKEN = os.getenv("TELEGRAM_TOKEN")`. If `None`, `ApplicationBuilder().token(None)` raises immediately.

---

## 2. Fenrir Payment Mode

| Variable | Required | Notes |
|---|---|---|
| `FENRIR_PRIMARY_PAYMENT` | ✅ Yes | Set to `stars` to activate Telegram Stars flow. Any other value (or unset) defaults to legacy behavior. |
| `FENRIR_STARS_PRICE` | ✅ Yes (if `stars`) | Integer — number of Telegram Stars to charge per transaction. Example: `FENRIR_STARS_PRICE=50`. |

> ⚠️ **Code gap:** As of this checklist, `main.py` does **not** yet read `FENRIR_PRIMARY_PAYMENT` or
> `FENRIR_STARS_PRICE`. The Stars payment handlers (`pre_checkout_query`, `successful_payment`,
> `send_invoice`) and the env-var reads must be implemented before go-live.
> Setting these vars without the handler code has no effect.

---

## 3. Stripe (only if Stripe remains enabled)

| Variable | Required | Notes |
|---|---|---|
| `STRIPE_SECRET_KEY` | Conditional | Live secret key (`sk_live_…`). Required if Stripe checkout is active. |
| `STRIPE_WEBHOOK_SECRET` | Conditional | Signing secret for Stripe webhook events (`whsec_…`). Required to verify incoming Stripe callbacks. |
| `FENRIR_PUBLIC_BASE_URL` | Conditional | The public HTTPS URL of this deployment (e.g. `https://fenrir.example.com`). Used to build Stripe `success_url`, `cancel_url`, and the Stripe webhook endpoint path. |

> ⚠️ **Code gap:** `main.py` currently has **no** Stripe imports or payment route handlers.
> `requirements.txt` does not include `stripe`. If Stripe is kept, add `stripe` to
> `requirements.txt` and implement the checkout/webhook routes before enabling live keys.

---

## 4. Webhook vs. Polling

| Variable | Mode | Notes |
|---|---|---|
| `WEBHOOK_URL` unset | Polling | Bot calls `app.run_polling()`. Good for local dev; not suitable for production (open port required). |
| `WEBHOOK_URL=https://…` | Webhook | Bot calls `app.run_webhook(listen="0.0.0.0", port=$PORT, webhook_url=$WEBHOOK_URL/$TOKEN)`. Required for cloud platforms (Railway, Render, Heroku, GCP, etc.). |
| `PORT` | Both | Defaults to `8080`. Set to the port your platform exposes (e.g. `PORT=8080`). |

**Rules:**
- Only **one** instance may run at a time. A second instance in polling mode causes a `Conflict` error (caught in `main.py`).
- `WEBHOOK_URL` must be a reachable public HTTPS URL. Telegram requires TLS.
- If `FENRIR_PUBLIC_BASE_URL` is set for Stripe, it should match `WEBHOOK_URL` (same host).

---

## 5. Database / State File

| Item | Detail |
|---|---|
| **Engine** | SQLite via `db.py` — file: `pupbot.db` in the working directory (`/app/pupbot.db` in Docker). |
| **On first boot** | `db.init_db()` creates the `kv_store` table automatically if missing. No manual migration needed. |
| **Persistence** | On ephemeral platforms (Heroku, Railway) the file is **lost on restart** unless mounted to a persistent volume. Mount `/app/pupbot.db` (or the full `/app` directory) to a persistent disk. |
| **Backup** | Copy `pupbot.db` before any deployment that changes the schema. |

---

## 6. Supporting Environment Variables (already wired in code)

These are read by `main.py` today and must be set for full functionality:

| Variable | Purpose |
|---|---|
| `ALPHA_USER_ID` | Primary admin Telegram user ID (default: `8091939499`) |
| `EXTRA_ALPHA_IDS` | Comma-separated additional admin IDs |
| `ADMIN_LOUNGE_ID` | Telegram chat ID of the admin group |
| `MAIN_GROUP_ID` | Telegram chat ID of the main community group |
| `AUTHORIZED_GROUPS` | Comma-separated chat IDs the bot responds in |
| `ANTIGRAVITY_BYPASS_PASSWORD` | Password for the antigravity bypass flow (default: `ghost` — change for production) |
| `GROQ_API_KEY` | Groq LLM API key (used for AI replies) |
| `GEMINI_API_KEY` | Google Gemini API key |
| `GITHUB_PUPBOT_TOKEN` | GitHub PAT for ticket/PR creation |
| `SUPABASE_URL` / `SUPABASE_KEY` | Supabase backend (optional feature) |
| `BOT_TONE` | Bot personality: `friendly` (default), `professional`, etc. |
| `LINK_CODE_TTL_SECONDS` | Invite link TTL (default: `900`) |

---

## 7. Smoke-Test Commands

Run these after deploying to verify the bot is live:

```bash
# 1. Confirm the bot responds on Telegram
# Send /start to the bot in a private chat — expect a welcome message.

# 2. Check Telegram webhook status (replace TOKEN)
curl "https://api.telegram.org/bot${TELEGRAM_TOKEN}/getWebhookInfo" | python3 -m json.tool

# Expected: "url" matches your WEBHOOK_URL, "pending_update_count" is low, no "last_error_message".

# 3. Confirm polling mode (if not using webhook)
# Watch logs for: "🐕‍🦺 LOCAL/WORKER MODE: Monitoring for Frisky and Spammers... Arf!"

# 4. Database writability check
python3 -c "import db; db.init_db(); db.set_val('smoke_test','ok'); print(db.get_val('smoke_test'))"
# Expected output: ok

# 5. Verify Stars price env var is readable (once handler is implemented)
python3 -c "import os; print('FENRIR_STARS_PRICE:', os.getenv('FENRIR_STARS_PRICE', 'NOT SET'))"

# 6. Stripe webhook endpoint reachability (if Stripe enabled)
# curl -X POST https://<FENRIR_PUBLIC_BASE_URL>/stripe/webhook
# Expected: 400 (missing signature) — confirms the route exists and is reachable.
```

---

## 8. Deployment Blockers (Must Fix Before Go-Live)

| # | Blocker | Severity |
|---|---|---|
| 1 | `FENRIR_PRIMARY_PAYMENT` and `FENRIR_STARS_PRICE` are **not read anywhere in `main.py`**. Stars payment handlers (`send_invoice`, `pre_checkout_query`, `successful_payment`) must be implemented. | 🔴 Critical |
| 2 | `stripe` is **not in `requirements.txt`**. If Stripe is kept, install it and add webhook verification logic. | 🔴 Critical (if Stripe used) |
| 3 | `pupbot.db` is **lost on restart** on ephemeral platforms. Mount a persistent volume at `/app/pupbot.db` before live traffic. | 🔴 Critical |
| 4 | `ANTIGRAVITY_BYPASS_PASSWORD` defaults to `ghost`. Must be overridden with a strong secret before production. | 🟠 High |
| 5 | `WEBHOOK_URL` must be set for cloud deployments. Without it, `run_polling()` is used and will conflict if multiple dynos/containers start. | 🟠 High |
| 6 | Dockerfile `CMD` runs only `main.py` (Telegram bot). `github_bot.py` (Procfile `web:`) is not started. Decide: Docker-only or Procfile-based deployment? | 🟡 Medium |
