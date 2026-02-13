"""Tests for get_bot_channels (Slack API)."""
from unittest.mock import patch, MagicMock

import bot


def test_get_bot_channels_success():
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "ok": True,
        "channels": [
            {"name": "general"},
            {"name": "random"},
        ],
        "response_metadata": {"next_cursor": ""},
    }
    with patch("bot.requests.get", return_value=mock_response):
        ret = bot.get_bot_channels()
    assert "general" in ret
    assert "random" in ret
    assert "#general" in ret
    assert "2" in ret


def test_get_bot_channels_pagination():
    """Test that multiple pages are requested when next_cursor is set."""
    call_count = 0
    def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        cursor = kwargs.get("params", {}).get("cursor", "")
        mock = MagicMock()
        if cursor == "":
            mock.json.return_value = {
                "ok": True,
                "channels": [{"name": "first"}],
                "response_metadata": {"next_cursor": "page2"},
            }
        else:
            mock.json.return_value = {
                "ok": True,
                "channels": [{"name": "second"}],
                "response_metadata": {"next_cursor": ""},
            }
        return mock
    with patch("bot.requests.get", side_effect=side_effect):
        ret = bot.get_bot_channels()
    assert call_count == 2
    assert "first" in ret and "second" in ret


def test_get_bot_channels_api_error():
    mock_response = MagicMock()
    mock_response.json.return_value = {"ok": False, "error": "invalid_auth"}
    with patch("bot.requests.get", return_value=mock_response):
        ret = bot.get_bot_channels()
    assert "invalid_auth" in ret or "Could not" in ret


def test_get_bot_channels_uses_slack_com_host():
    """Regression: endpoint must be slack.com, not api.slack.com."""
    with patch("bot.requests.get") as m:
        m.return_value.json.return_value = {"ok": True, "channels": [], "response_metadata": {"next_cursor": ""}}
        bot.get_bot_channels()
    call_url = m.call_args[0][0]
    assert call_url == "https://slack.com/api/users.conversations", "Wrong API host (fix 1.1)"
