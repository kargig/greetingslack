"""Tests for handle_event and parse_message."""
from unittest.mock import patch, MagicMock

import bot


class TestHandleEventCoc:
    def test_coc_sends_to_channel(self):
        with patch.object(bot, "send_message") as send:
            with patch.object(bot, "request_channel_name", return_value="general"):
                bot.handle_event({"type": "message", "text": "!coc", "channel": "C123"})
        send.assert_called_once()
        args = send.call_args[0]
        assert args[0] == "general"
        assert args[1] == bot.coc_text()


class TestHandleEventWelcome:
    def test_team_join_sends_welcome_dm(self):
        with patch.object(bot, "web_client") as wc:
            wc.conversations_open.return_value = {"ok": True, "channel": {"id": "D123"}}
            with patch.object(bot, "send_message") as send:
                bot.handle_event({"type": "team_join", "user": {"id": "U123"}})
        wc.conversations_open.assert_called_once_with(users="U123")
        send.assert_called_once_with("D123", bot.welcome_message())

    def test_welcome_me_sends_welcome_dm(self):
        with patch.object(bot, "web_client") as wc:
            wc.conversations_open.return_value = {"ok": True, "channel": {"id": "D456"}}
            with patch.object(bot, "send_message") as send:
                bot.handle_event({"type": "message", "text": "!welcome", "user": "U456", "channel": "C1"})
        wc.conversations_open.assert_called_once_with(users="U456")
        send.assert_called_once_with("D456", bot.welcome_message())


class TestHandleEventCommands:
    def test_help_sends_help_text(self, fresh_db):
        with patch.object(bot, "request_display_name", return_value="u"):
            with patch.object(bot, "request_channel_name", return_value="c"):
                with patch.object(bot, "send_message") as send:
                    bot.handle_event({"type": "message", "text": "!help", "channel": "C1", "user": "U1"})
        send.assert_called_once()
        assert send.call_args[0][1] == bot.get_help_text()

    def test_quote_sends_quote_or_nothing(self, fresh_db):
        with patch.object(bot, "request_display_name", return_value="u"):
            with patch.object(bot, "request_channel_name", return_value="c"):
                with patch.object(bot, "send_message") as send:
                    bot.handle_event({"type": "message", "text": "!quote", "channel": "C1", "user": "U1"})
        # No quote in DB -> get_quote returns None -> no send
        send.assert_not_called()

    def test_quote_with_data_sends(self, fresh_db):
        bot.quote_api().addtodb("alice", "general", "!add test quote")
        with patch.object(bot, "request_display_name", return_value="u"):
            with patch.object(bot, "request_channel_name", return_value="c"):
                with patch.object(bot, "send_message") as send:
                    bot.handle_event({"type": "message", "text": "!quote", "channel": "C1", "user": "U1"})
        send.assert_called_once()
        assert "test quote" in send.call_args[0][1]

    def test_add_sends_confirmation(self, fresh_db):
        with patch.object(bot, "request_display_name", return_value="alice"):
            with patch.object(bot, "request_channel_name", return_value="general"):
                with patch.object(bot, "send_message") as send:
                    bot.handle_event({"type": "message", "text": "!add new quote", "channel": "C1", "user": "U1"})
        send.assert_called_once()
        assert "Quote" in send.call_args[0][1] and "added" in send.call_args[0][1]

    def test_channels_calls_send(self):
        with patch("bot.requests.get") as m:
            m.return_value.json.return_value = {"ok": True, "channels": [{"name": "general"}], "response_metadata": {"next_cursor": ""}}
            with patch.object(bot, "request_display_name", return_value="u"):
                with patch.object(bot, "request_channel_name", return_value="c"):
                    with patch.object(bot, "send_message") as send:
                        bot.handle_event({"type": "message", "text": "!channels", "channel": "C1", "user": "U1"})
        send.assert_called_once()
        assert "general" in send.call_args[0][1]

    def test_bot_message_ignored(self, fresh_db):
        with patch.object(bot, "send_message") as send:
            bot.handle_event({"type": "message", "text": "!help", "channel": "C1", "user": "U1", "bot_id": "B1"})
        send.assert_not_called()


class TestParseMessage:
    def test_invalid_json_returns_none(self):
        assert bot.parse_message("not json") is None
        assert bot.parse_message("") is None

    def test_valid_message_coc(self):
        with patch.object(bot, "request_channel_name", return_value="general"):
            with patch("bot.requests.post") as post:
                bot.parse_message('{"type":"message","text":"!coc","channel":"C123"}')
        post.assert_called_once()
        call_args = post.call_args
        assert "chat.postMessage" in call_args[0][0]
        assert call_args[1]["data"]["text"] == bot.coc_text()
