import unittest
import os
import html
from types import SimpleNamespace
from unittest.mock import patch, AsyncMock, MagicMock
import main

class TestSecurityHardening(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Save original states
        self.orig_antigravity = set(main.antigravity_chats)
        self.orig_ticket_states = dict(main.ticket_states)
        self.orig_ticket_data = dict(main.ticket_data)
        self.orig_invitations = dict(main.invitations)
        self.orig_banned_words = set(main.BANNED_WORDS)
        self.orig_alpha_user_id = main.ALPHA

        main.BANNED_WORDS = {"spamword"}
        main.invitations = {"12345": "InviterName"}
        main.ALPHA = "999"

    def tearDown(self):
        # Restore original states
        main.antigravity_chats = self.orig_antigravity
        main.ticket_states = self.orig_ticket_states
        main.ticket_data = self.orig_ticket_data
        main.invitations = self.orig_invitations
        main.BANNED_WORDS = self.orig_banned_words
        main.ALPHA = self.orig_alpha_user_id

    async def test_spam_detection_logic(self):
        # Setup mock update and context
        mock_msg = AsyncMock()
        mock_msg.text = "This contains a spamword"
        mock_msg.caption = None
        mock_msg.from_user.id = 12345
        mock_msg.from_user.username = "spammer"

        update = MagicMock()
        update.message = mock_msg
        update.effective_message = mock_msg
        update.effective_user = mock_msg.from_user
        update.effective_chat.id = 67890

        context = MagicMock()
        context.bot.send_message = AsyncMock()

        # Mock is_alpha_user to return False
        with patch('main.is_alpha_user', return_value=AsyncMock(return_value=False)):
            await main.lounge_host(update, context)

        # Verify spam report was sent with HTML escaping
        context.bot.send_message.assert_called()
        args, kwargs = context.bot.send_message.call_args
        report_text = kwargs.get('text', '')
        self.assertIn("SPAMMER DETECTED", report_text)
        self.assertIn("InviterName", report_text)
        self.assertEqual(kwargs.get('parse_mode'), "HTML")
        mock_msg.delete.assert_called_once()

    async def test_antigravity_bypass_group_rejection(self):
        user_id = "555"
        main.ticket_states[user_id] = "antigravity_bypass"
        main.ticket_data[user_id] = {"target_chat_id": "group_123"}

        mock_msg = AsyncMock()
        mock_msg.text = "secretpassword"
        mock_msg.chat.type = "supergroup"
        mock_msg.from_user.id = int(user_id)

        update = MagicMock()
        update.message = mock_msg
        update.effective_message = mock_msg
        update.effective_user = mock_msg.from_user
        update.effective_chat.id = 111

        context = MagicMock()
        context.bot.send_message = AsyncMock()

        await main.lounge_host(update, context)

        # Verify message was deleted and warning sent
        mock_msg.delete.assert_called_once()
        context.bot.send_message.assert_called_with(
            chat_id="111",
            text="⛔ <b>Security Alert:</b> Never enter bypass passwords in communal chats. Password entry must be done in Private DM.",
            parse_mode="HTML"
        )
        # State should still be active for DM attempt
        self.assertEqual(main.ticket_states[user_id], "antigravity_bypass")

    async def test_antigravity_bypass_dm_success(self):
        user_id = "555"
        main.ticket_states[user_id] = "antigravity_bypass"
        main.ticket_data[user_id] = {"target_chat_id": "group_123"}
        main.ANTIGRAVITY_BYPASS_PASSWORD = "secretpassword"

        mock_msg = AsyncMock()
        mock_msg.text = "secretpassword"
        mock_msg.chat.type = "private"
        mock_msg.from_user.id = int(user_id)

        update = MagicMock()
        update.message = mock_msg
        update.effective_message = mock_msg
        update.effective_user = mock_msg.from_user
        update.effective_chat.id = user_id

        context = MagicMock()
        context.bot.send_message = AsyncMock()

        with patch('main.save_state'):
            await main.lounge_host(update, context)

        # Verify activation in target group
        self.assertIn("group_123", main.antigravity_chats)
        self.assertNotIn(user_id, main.ticket_states)
        self.assertNotIn(user_id, main.ticket_data)

        # Check messages sent to both DM and target group
        calls = [call.kwargs.get('chat_id') for call in context.bot.send_message.call_args_list]
        self.assertIn("group_123", calls)
        self.assertIn(user_id, calls)

if __name__ == "__main__":
    unittest.main()
