## 2024-04-13 - [AI Response Polish]
**Learning:** In LLM-driven chat interfaces, the perceived performance is just as important as the actual response time. Adding a 'typing' indicator prevents the user from feeling like the bot is dead during API latency. Furthermore, LLMs often produce slightly malformed Markdown; a robust fallback to plain-text message delivery ensures the UX doesn't break when formatting fails.
**Action:** Always wrap AI message delivery in a try-except block when using Markdown, and trigger a 'typing' chat action immediately before the generation call.
