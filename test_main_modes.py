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
        chat_id = "-1001"
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

    def test_get_mode_respects_admin_assistant_toggle_in_admin_lounge(self):
        main.ADMIN_LOUNGE_ID = "-123"
        main.admin_assistant_chats.discard("-123")
        self.assertEqual(main.get_mode("-123"), "puppy")

        main.admin_assistant_chats.add("-123")
        self.assertEqual(main.get_mode("-123"), "admin_assistant")

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


if __name__ == "__main__":
    unittest.main()
