# Palette's Journal 🎨

## 2026-04-14 - [Immediate Visual Feedback]
**Learning:** In Telegram, long-running AI operations can make the bot feel unresponsive. Calling `context.bot.send_chat_action(action='typing')` before the API call provides immediate visual feedback that the bot is "working".
**Action:** Always trigger a 'typing' or appropriate chat action before starting an async AI generation task.

## 2026-04-14 - [Resilient Content Formatting]
**Learning:** LLMs occasionally generate malformed Markdown that causes Telegram's `send_message` to fail when `parse_mode='Markdown'` is used.
**Action:** Use a `try-except` block when sending Markdown content, falling back to plain text (no `parse_mode`) if formatting fails.

## 2026-04-14 - [Standardizing Command Entry]
**Learning:** Users instinctively type `/start` when first interacting with a bot. If this isn't handled, it can be a frustrating first experience.
**Action:** Map `/start` to the main help or menu command to improve onboarding.

## 2026-04-14 - [Explicit Flow Control]
**Learning:** Multi-step interactive flows (like bug ticketing) can feel like a "trap" if there isn't an obvious way to exit.
**Action:** Always include a "Cancel" button or clear command instructions (e.g., "Type /cancel") in interactive menus.
