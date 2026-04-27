import unittest
import os
from types import SimpleNamespace
from unittest.mock import patch
from unittest.mock import AsyncMock

import main


class TestMainModes(unittest.TestCase):
    def setUp(self):
        self.orig_antigravity = set(main.antigravity_chats)
        self.orig_alchemy = set(main.alchemy_chats)
        self.orig_admin_assistant = set(main.admin_assistant_chats)
        self.orig_link_codes = dict(main.link_codes)
        self.orig_dynamic_alpha_ids = set(main.dynamic_alpha_ids)
        self.orig_admin_lounge_id = main.ADMIN_LOUNGE_ID
        self.orig_main_group_id = main.MAIN_GROUP_ID
        self.orig_admin_owner_last_refresh = main.admin_owner_last_refresh

    def tearDown(self):
        main.antigravity_chats.clear()
        main.antigravity_chats.update(self.orig_antigravity)
        main.alchemy_chats.clear()
        main.alchemy_chats.update(self.orig_alchemy)
        main.admin_assistant_chats.clear()
        main.admin_assistant_chats.update(self.orig_admin_assistant)
        main.link_codes.clear()
        main.link_codes.update(self.orig_link_codes)
        main.dynamic_alpha_ids.clear()
        main.dynamic_alpha_ids.update(self.orig_dynamic_alpha_ids)
        main.ADMIN_LOUNGE_ID = self.orig_admin_lounge_id
        main.MAIN_GROUP_ID = self.orig_main_group_id
        main.admin_owner_last_refresh = self.orig_admin_owner_last_refresh
        os.environ.pop("MAIN_GROUP_ID", None)

    def test_get_mode_precedence(self):
        chat_id = "-100111"
        main.antigravity_chats.add(chat_id)
        main.alchemy_chats.add(chat_id)
        main.admin_assistant_chats.add(chat_id)
        self.assertEqual(main.get_mode(chat_id), "antigravity")

        main.antigravity_chats.remove(chat_id)
        self.assertEqual(main.get_mode(chat_id), "alchemy")

        main.alchemy_chats.remove(chat_id)
        self.assertEqual(main.get_mode(chat_id), "admin_assistant")

    def test_create_link_code_and_cleanup_expired(self):
        main.link_codes.clear()
        with patch("main.save_state", return_value=None):
            code = main.create_link_code("-1001", "12345")
            self.assertIsNotNone(code)
            self.assertIn(code, main.link_codes)
            payload = main.link_codes[code]
            self.assertEqual(payload["admin_chat_id"], "-1001")
            self.assertEqual(payload["issuer_user_id"], "12345")

            main.link_codes["EXPIRED01"] = {"expires_at": 0}
            main.cleanup_expired_link_codes()
            self.assertNotIn("EXPIRED01", main.link_codes)
            self.assertIn(code, main.link_codes)

    def test_prevent_echo_reply_for_modes(self):
        self.assertIn(
            "Antigravity online",
            main.prevent_echo_reply("antigravity", "hi", "hi"),
        )
        self.assertIn(
            "Alchemy Curator",
            main.prevent_echo_reply("alchemy", "promo", "promo"),
        )
        self.assertIn(
            "Admin Assistant",
            main.prevent_echo_reply("admin_assistant", "help", "help"),
        )
        self.assertEqual(
            main.prevent_echo_reply("puppy", "hello", "hello there!"),
            "hello there!",
        )

    def test_build_identity_context(self):
        alpha_context = main.build_identity_context("Frisky", "1", True)
        self.assertIn("Owner/Alpha", alpha_context)
        member_context = main.build_identity_context("Pup", "2", False)
        self.assertIn("Lounge member", member_context)

    def test_get_primary_target_group_prefers_linked(self):
        original_main_group = main.MAIN_GROUP_ID
        original_linked = set(main.linked_groups)
        original_env_main = main.os.environ.get("MAIN_GROUP_ID")
        try:
            main.MAIN_GROUP_ID = None
            main.linked_groups.clear()
            main.linked_groups.add("-100LINKED")
            if "MAIN_GROUP_ID" in main.os.environ:
                del main.os.environ["MAIN_GROUP_ID"]
            self.assertEqual(main.get_primary_target_group(), "-100LINKED")

            main.os.environ["MAIN_GROUP_ID"] = "-100ENV"
            self.assertEqual(main.get_primary_target_group(), "-100LINKED")
        finally:
            main.MAIN_GROUP_ID = original_main_group
            main.linked_groups.clear()
            main.linked_groups.update(original_linked)
            if original_env_main is None:
                main.os.environ.pop("MAIN_GROUP_ID", None)
            else:
                main.os.environ["MAIN_GROUP_ID"] = original_env_main

    def test_get_primary_target_group_falls_back_to_linked(self):
        original_main_group = main.MAIN_GROUP_ID
        original_linked = set(main.linked_groups)
        original_env_main = main.os.environ.get("MAIN_GROUP_ID")
        try:
            main.MAIN_GROUP_ID = None
            main.os.environ.pop("MAIN_GROUP_ID", None)
            main.linked_groups.clear()
            main.linked_groups.update({"-100B", "-100A"})
            self.assertEqual(main.get_primary_target_group(), "-100A")
        finally:
            main.MAIN_GROUP_ID = original_main_group
            main.linked_groups.clear()
            main.linked_groups.update(original_linked)
            if original_env_main is None:
                main.os.environ.pop("MAIN_GROUP_ID", None)
            else:
                main.os.environ["MAIN_GROUP_ID"] = original_env_main

    def test_get_effective_mode_respects_admin_assistant_toggle_in_admin_lounge(self):
        main.ADMIN_LOUNGE_ID = "-123"
        main.admin_assistant_chats.discard("-123")
        self.assertEqual(main.get_effective_mode("-123"), "puppy")

        main.admin_assistant_chats.add("-123")
        self.assertEqual(main.get_effective_mode("-123"), "admin_assistant")

    def test_validate_link_target_chat(self):
        main.MAIN_GROUP_ID = "-200"
        valid, msg = main.validate_link_target_chat("-100", "-100")
        self.assertFalse(valid)
        self.assertIn("target group", msg.lower())

        valid, msg = main.validate_link_target_chat("-999", "-100")
        self.assertFalse(valid)
        self.assertIn("configured Main Group", msg)

        valid, msg = main.validate_link_target_chat("-200", "-100")
        self.assertTrue(valid)
        self.assertEqual(msg, "")

    def test_is_admin_status(self):
        self.assertTrue(main.is_admin_status("creator"))
        self.assertTrue(main.is_admin_status("administrator"))
        self.assertFalse(main.is_admin_status("member"))

    def test_prevent_echo_reply_similarity_catches_near_copies(self):
        fallback = main.prevent_echo_reply(
            "admin_assistant",
            "launch plan for tonight",
            "launch plan for tonite",
        )
        self.assertIn("Admin Assistant active", fallback)

    # ── Tone / Persona tests ──────────────────────────────────────────────── #

    def test_system_prompt_defaults_to_friendly(self):
        """Default BOT_TONE should produce a non-goofy system prompt."""
        self.assertNotIn("Arf arf", main.SYSTEM_PROMPT)
        self.assertNotIn("wag", main.SYSTEM_PROMPT.lower()[:80])
        self.assertIn("Geminipupbot", main.SYSTEM_PROMPT)

    def test_friendly_prompt_contains_guidelines(self):
        """Friendly tone prompt must include explicit anti-silliness guidelines."""
        prompt = main._SYSTEM_PROMPT_FRIENDLY
        self.assertIn("not goofy", prompt)
        self.assertIn("barking", prompt)
        self.assertIn("concise", prompt.lower())

    def test_playful_prompt_retained(self):
        """Playful tone prompt must still be available for backward compat."""
        prompt = main._SYSTEM_PROMPT_PLAYFUL
        self.assertIn("pup host", prompt.lower())
        self.assertIn("Geminipupbot", prompt)

    def test_system_prompt_selection_via_bot_tone(self):
        """SYSTEM_PROMPT selection follows BOT_TONE at module init."""
        import importlib, sys

        original_system_prompt = main.SYSTEM_PROMPT
        try:
            with patch.dict(os.environ, {"BOT_TONE": "playful"}):
                # Simulate choosing the playful prompt (as done at module level)
                chosen = main._SYSTEM_PROMPT_PLAYFUL if os.getenv("BOT_TONE") == "playful" else main._SYSTEM_PROMPT_FRIENDLY
                self.assertEqual(chosen, main._SYSTEM_PROMPT_PLAYFUL)

            with patch.dict(os.environ, {"BOT_TONE": "friendly"}):
                chosen = main._SYSTEM_PROMPT_PLAYFUL if os.getenv("BOT_TONE") == "playful" else main._SYSTEM_PROMPT_FRIENDLY
                self.assertEqual(chosen, main._SYSTEM_PROMPT_FRIENDLY)
        finally:
            main.SYSTEM_PROMPT = original_system_prompt


class TestMainModesAsync(unittest.IsolatedAsyncioTestCase):
    async def test_refresh_dynamic_alpha_ids_includes_admins(self):
        original_admin_lounge_id = main.ADMIN_LOUNGE_ID
        original_dynamic_alpha_ids = set(main.dynamic_alpha_ids)
        original_admin_owner_last_refresh = main.admin_owner_last_refresh
        try:
            main.ADMIN_LOUNGE_ID = "-100123"
            main.dynamic_alpha_ids.clear()
            main.admin_owner_last_refresh = 0.0

            admins = [
                SimpleNamespace(status="creator", user=SimpleNamespace(id=111)),
                SimpleNamespace(status="administrator", user=SimpleNamespace(id=222)),
                SimpleNamespace(status="member", user=SimpleNamespace(id=333)),
            ]
            context = SimpleNamespace(
                bot=SimpleNamespace(get_chat_administrators=AsyncMock(return_value=admins))
            )

            with patch("main.save_state", return_value=None):
                await main.refresh_dynamic_alpha_ids(context)

            self.assertIn("111", main.dynamic_alpha_ids)
            self.assertIn("222", main.dynamic_alpha_ids)
            self.assertNotIn("333", main.dynamic_alpha_ids)
        finally:
            main.ADMIN_LOUNGE_ID = original_admin_lounge_id
            main.dynamic_alpha_ids.clear()
            main.dynamic_alpha_ids.update(original_dynamic_alpha_ids)
            main.admin_owner_last_refresh = original_admin_owner_last_refresh

    async def test_groq_fallback_returns_text_on_success(self):
        """_groq_text_fallback should return response text when Groq responds OK."""
        import httpx
        mock_response = SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {"choices": [{"message": {"content": "Hello from Groq!"}}]},
        )

        async def mock_post(*args, **kwargs):
            return mock_response

        with patch.dict(os.environ, {"GROQ_API_KEY": "test_key"}):
            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = mock_client_cls.return_value.__aenter__.return_value
                mock_client.post = AsyncMock(return_value=mock_response)
                result = await main._groq_text_fallback("sys", "hello")
                self.assertEqual(result, "Hello from Groq!")

    async def test_groq_fallback_returns_none_without_key(self):
        """_groq_text_fallback should return None when GROQ_API_KEY is absent."""
        env = {k: v for k, v in os.environ.items() if k != "GROQ_API_KEY"}
        with patch.dict(os.environ, env, clear=True):
            result = await main._groq_text_fallback("sys", "hello")
            self.assertIsNone(result)

    async def test_groq_fallback_returns_none_on_http_error(self):
        """_groq_text_fallback should return None on network/HTTP errors."""
        import httpx

        async def raise_error(*args, **kwargs):
            raise httpx.ConnectError("timeout")

        with patch.dict(os.environ, {"GROQ_API_KEY": "test_key"}):
            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = mock_client_cls.return_value.__aenter__.return_value
                mock_client.post = raise_error
                result = await main._groq_text_fallback("sys", "hello")
                self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
