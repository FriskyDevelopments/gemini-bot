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

## 2026-04-18 - [Persona-Aware Menus & Accessibility Redundancy]
**Learning:** For bots with distinct personas, context-aware help menus improve immersion and command discoverability. Additionally, always sending text alongside AI voice messages is a critical accessibility requirement.
**Action:** Implement conditional help menus based on active persona state and ensure text fallbacks/companions for all media-based responses.

## 2026-05-10 - [Non-Destructive Navigation]
**Learning:** In multi-step interactive flows (like bug reporting or feedback), "Cancel" buttons are necessary but can be frustrating if the user only wants to correct a minor mistake.
**Action:** Implement "⬅️ Back" buttons in nested sub-menus to allow users to return to the previous state without destroying their session progress.

## 2026-05-15 - [Ephemeral UI Dismissibility]
**Learning:** Ephemeral menus, such as help guides or status reports, can quickly clutter a Telegram chat's history. Providing a way to "clean up" the bot's presence after an interaction is a high-value micro-UX touch.
**Action:** Implement a 'Close' button that calls `query.delete_message()` for all major menus and status alerts.

## 2026-05-15 - [Proactive Input Guidance]
**Learning:** Technical constraints (like character limits for GitHub issues) are often invisible to users until a failure occurs. Communicating these limits *at the point of entry* reduces frustration and prevents data loss.
**Action:** Always include character limit hints (e.g., "max 500 characters") in conversational prompts and provide immediate feedback if the limit is exceeded.
