"""Tests for get_bot_channels (Slack API via WebClient)."""
from unittest.mock import patch, MagicMock

import bot


def test_get_bot_channels_success():
    resp = {
        "ok": True,
        "channels": [
            {"name": "general"},
            {"name": "random"},
        ],
        "response_metadata": {"next_cursor": ""},
    }
    with patch.object(bot, "web_client") as wc:
        wc.users_conversations.return_value = resp
        ret = bot.get_bot_channels()
    wc.users_conversations.assert_called_once()
    assert "general" in ret
    assert "random" in ret
    assert "#general" in ret
    assert "2" in ret


def test_get_bot_channels_pagination():
    """Test that multiple pages are requested when next_cursor is set."""
    call_count = 0

    def side_effect(**kwargs):
        nonlocal call_count
        call_count += 1
        cursor = kwargs.get("cursor", "")
        if cursor == "":
            return {
                "ok": True,
                "channels": [{"name": "first"}],
                "response_metadata": {"next_cursor": "page2"},
            }
        else:
            return {
                "ok": True,
                "channels": [{"name": "second"}],
                "response_metadata": {"next_cursor": ""},
            }

    with patch.object(bot, "web_client") as wc:
        wc.users_conversations.side_effect = side_effect
        ret = bot.get_bot_channels()
    assert call_count == 2
    assert "first" in ret and "second" in ret


def test_get_bot_channels_api_error():
    with patch.object(bot, "web_client") as wc:
        wc.users_conversations.return_value = {"ok": False, "error": "invalid_auth"}
        ret = bot.get_bot_channels()
    assert "invalid_auth" in ret or "Could not" in ret


def test_get_bot_channels_uses_webclient():
    """Regression: ensure WebClient.users_conversations is used."""
    with patch.object(bot, "web_client") as wc:
        wc.users_conversations.return_value = {"ok": True, "channels": [], "response_metadata": {"next_cursor": ""}}
        bot.get_bot_channels()
    wc.users_conversations.assert_called_once()
