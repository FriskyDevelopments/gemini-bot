import unittest
import os
from types import SimpleNamespace
from unittest.mock import patch, MagicMock
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
        chat_id = "chat-1"
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


class TestGetPrimaryTargetGroup(unittest.TestCase):
    """Tests for the PR change: get_primary_target_group now prefers MAIN_GROUP_ID env var."""

    def setUp(self):
        self.orig_main_group_id = main.MAIN_GROUP_ID
        self.orig_linked_groups = set(main.linked_groups)
        main.linked_groups.clear()

    def tearDown(self):
        main.MAIN_GROUP_ID = self.orig_main_group_id
        main.linked_groups.clear()
        main.linked_groups.update(self.orig_linked_groups)
        os.environ.pop("MAIN_GROUP_ID", None)

    def test_env_var_takes_priority_over_linked_groups(self):
        """MAIN_GROUP_ID env var must be returned even when linked_groups is non-empty."""
        os.environ["MAIN_GROUP_ID"] = "-100111"
        main.linked_groups.add("-100999")
        result = main.get_primary_target_group()
        self.assertEqual(result, "-100111")

    def test_module_level_main_group_id_used_when_env_absent(self):
        """If env var is absent, the module-level MAIN_GROUP_ID is tried."""
        os.environ.pop("MAIN_GROUP_ID", None)
        main.MAIN_GROUP_ID = "-100222"
        result = main.get_primary_target_group()
        self.assertEqual(result, "-100222")

    def test_falls_back_to_linked_groups_when_main_group_id_unset(self):
        """When MAIN_GROUP_ID is not set at all, linked_groups is the fallback."""
        os.environ.pop("MAIN_GROUP_ID", None)
        main.MAIN_GROUP_ID = None
        main.linked_groups.add("-100333")
        main.linked_groups.add("-100100")
        result = main.get_primary_target_group()
        # Returns the lexicographically first (sorted)
        self.assertEqual(result, "-100100")

    def test_returns_none_when_nothing_configured(self):
        os.environ.pop("MAIN_GROUP_ID", None)
        main.MAIN_GROUP_ID = None
        result = main.get_primary_target_group()
        self.assertIsNone(result)

    def test_linked_groups_not_returned_when_main_group_id_env_set(self):
        """Regression: old code returned linked_groups first; new code must not."""
        os.environ["MAIN_GROUP_ID"] = "-999"
        main.linked_groups.add("-111")
        result = main.get_primary_target_group()
        self.assertNotEqual(result, "-111")


class TestBuildIdentityContextNoSanitization(unittest.TestCase):
    """The PR removed user_name sanitization from build_identity_context."""

    def test_special_chars_in_username_are_preserved(self):
        """After the PR, brackets and newlines in user_name are no longer stripped."""
        result = main.build_identity_context("[Admin]", "123", False)
        # The name must appear unmodified (brackets not stripped)
        self.assertIn("[Admin]", result)

    def test_newline_in_username_not_removed(self):
        result = main.build_identity_context("User\nName", "456", False)
        self.assertIn("User\nName", result)

    def test_long_name_not_truncated(self):
        """Old code truncated to 100 chars; new code does not."""
        long_name = "A" * 200
        result = main.build_identity_context(long_name, "789", True)
        self.assertIn(long_name, result)

    def test_alpha_role_label(self):
        result = main.build_identity_context("Frisky", "1", True)
        self.assertIn("Owner/Alpha", result)

    def test_member_role_label(self):
        result = main.build_identity_context("Pup", "2", False)
        self.assertIn("Lounge member", result)

    def test_format_includes_user_id(self):
        result = main.build_identity_context("Fido", "9999", False)
        self.assertIn("9999", result)


class TestSaveStateRemovedFields(unittest.TestCase):
    """The PR removed dashboard_chats, manual_alpha_ids, sleep_mode from save_state."""

    def test_dashboard_chats_not_a_module_attribute(self):
        self.assertFalse(
            hasattr(main, "dashboard_chats"),
            "dashboard_chats should have been removed from main in this PR",
        )

    def test_manual_alpha_ids_not_a_module_attribute(self):
        self.assertFalse(
            hasattr(main, "manual_alpha_ids"),
            "manual_alpha_ids should have been removed from main in this PR",
        )

    def test_sleep_mode_not_a_module_attribute(self):
        self.assertFalse(
            hasattr(main, "sleep_mode"),
            "sleep_mode should have been removed from main in this PR",
        )

    def test_conversation_histories_not_a_module_attribute(self):
        self.assertFalse(
            hasattr(main, "conversation_histories"),
            "conversation_histories should have been removed from main in this PR",
        )

    def test_save_state_does_not_reference_removed_fields(self):
        """save_state() must run without AttributeError despite removed fields."""
        with patch("main.db") as mock_db:
            mock_db.set_val = MagicMock()
            try:
                main.save_state()
            except AttributeError as e:
                self.fail(f"save_state() raised AttributeError: {e}")


class TestIsAlphaUserNoManualAlphaIds(unittest.TestCase):
    """is_alpha_user no longer checks manual_alpha_ids (removed in this PR)."""

    def setUp(self):
        self.orig_core = set(main.CORE_ALPHA_IDS)
        self.orig_dynamic = set(main.dynamic_alpha_ids)

    def tearDown(self):
        main.CORE_ALPHA_IDS.clear() if isinstance(main.CORE_ALPHA_IDS, set) else None
        main.dynamic_alpha_ids.clear()
        main.dynamic_alpha_ids.update(self.orig_dynamic)

    def test_core_alpha_returns_true(self):
        import asyncio
        from types import SimpleNamespace
        context = SimpleNamespace(bot=SimpleNamespace(
            get_chat_administrators=AsyncMock(return_value=[])
        ))
        # ALPHA is always in CORE_ALPHA_IDS
        result = asyncio.get_event_loop().run_until_complete(
            main.is_alpha_user(context, main.ALPHA)
        )
        self.assertTrue(result)

    def test_unknown_user_returns_false(self):
        import asyncio
        from types import SimpleNamespace
        context = SimpleNamespace(bot=SimpleNamespace(
            get_chat_administrators=AsyncMock(return_value=[])
        ))
        with patch("main.save_state"):
            result = asyncio.get_event_loop().run_until_complete(
                main.is_alpha_user(context, "000000000")
            )
        self.assertFalse(result)


class TestWriteAuthorizedGroupsFallbackAppend(unittest.TestCase):
    """The PR changed fallback persistence from read-modify-write to append-only."""

    def setUp(self):
        import tempfile
        self.tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False)
        self.tmp.write("TELEGRAM_TOKEN=test\n")
        self.tmp.close()
        self.env_path = self.tmp.name
        self.orig_env_path = main.env_path

    def tearDown(self):
        main.env_path = self.orig_env_path
        os.unlink(self.env_path)
        os.environ.pop("AUTHORIZED_GROUPS", None)

    def test_fallback_appends_when_doppler_and_file_succeed(self):
        """When Doppler fails, the env file fallback must append the entry."""
        main.env_path = self.env_path

        # Force Doppler to fail by not having DOPPLER_PROJECT set
        os.environ.pop("DOPPLER_PROJECT", None)

        result = main._write_authorized_groups(["-100123"])

        with open(self.env_path) as f:
            content = f.read()

        self.assertTrue(result)
        self.assertIn("AUTHORIZED_GROUPS=-100123", content)

    def test_fallback_appends_rather_than_replacing(self):
        """Append mode means calling twice creates two entries (idempotency lost)."""
        main.env_path = self.env_path
        os.environ.pop("DOPPLER_PROJECT", None)

        main._write_authorized_groups(["-100aaa"])
        main._write_authorized_groups(["-100bbb"])

        with open(self.env_path) as f:
            content = f.read()

        # Both entries must appear (append, not replace)
        self.assertIn("AUTHORIZED_GROUPS=-100aaa", content)
        self.assertIn("AUTHORIZED_GROUPS=-100bbb", content)


class TestSystemPromptFixed(unittest.TestCase):
    """The PR removed BOT_TONE branching; SYSTEM_PROMPT is now a single constant."""

    def test_bot_tone_attribute_removed(self):
        """BOT_TONE-based prompt selection no longer exists."""
        self.assertFalse(
            hasattr(main, "_SYSTEM_PROMPT_FRIENDLY"),
            "_SYSTEM_PROMPT_FRIENDLY should have been removed",
        )
        self.assertFalse(
            hasattr(main, "_SYSTEM_PROMPT_PLAYFUL"),
            "_SYSTEM_PROMPT_PLAYFUL should have been removed",
        )

    def test_system_prompt_is_a_string(self):
        self.assertIsInstance(main.SYSTEM_PROMPT, str)
        self.assertGreater(len(main.SYSTEM_PROMPT), 0)

    def test_system_prompt_contains_pup_lounge(self):
        self.assertIn("Pup Lounge", main.SYSTEM_PROMPT)


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
