import unittest
from unittest.mock import patch

import main


class TestMainModes(unittest.TestCase):
    def setUp(self):
        self.orig_antigravity = set(main.antigravity_chats)
        self.orig_alchemy = set(main.alchemy_chats)
        self.orig_admin_assistant = set(main.admin_assistant_chats)
        self.orig_link_codes = dict(main.link_codes)

    def tearDown(self):
        main.antigravity_chats.clear()
        main.antigravity_chats.update(self.orig_antigravity)
        main.alchemy_chats.clear()
        main.alchemy_chats.update(self.orig_alchemy)
        main.admin_assistant_chats.clear()
        main.admin_assistant_chats.update(self.orig_admin_assistant)
        main.link_codes.clear()
        main.link_codes.update(self.orig_link_codes)

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


if __name__ == "__main__":
    unittest.main()
