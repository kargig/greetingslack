"""Tests for get_help_text, handle_cache_invokes, handle_stats_invokes."""
import pytest
from unittest.mock import patch

import bot


class TestGetHelpText:
    def test_contains_commands(self):
        text = bot.get_help_text()
        assert "!help" in text
        assert "!quote" in text
        assert "!add" in text
        assert "!coc" in text
        assert "!welcome" in text
        assert "!cache" in text
        assert "!stats" in text
        assert "!channels" in text


class TestHandleCacheInvokes:
    def test_cache_stats(self):
        ret = bot.handle_cache_invokes("stats")
        assert "cache" in ret.lower()
        assert "Display" in ret or "Channel" in ret

    def test_cache_clear(self):
        ret = bot.handle_cache_invokes("clear")
        assert "cleared" in ret.lower()

    def test_cache_unknown(self):
        ret = bot.handle_cache_invokes("")
        assert "!cache stats" in ret or "!cache clear" in ret


class TestHandleStatsInvokes:
    def test_stats_quotes_empty(self, fresh_db):
        ret = bot.handle_stats_invokes("quotes")
        assert "No quotes" in ret

    def test_stats_quotes_with_data(self, fresh_db):
        bot.quote_api().addtodb("alice", "general", "!add one")
        bot.quote_api().addtodb("alice", "general", "!add two")
        ret = bot.handle_stats_invokes("quotes")
        assert "alice" in ret
        assert "2" in ret

    def test_stats_urls_empty(self, fresh_db):
        ret = bot.handle_stats_invokes("urls")
        assert "No URLs" in ret

    def test_stats_urls_with_data(self, fresh_db):
        bot.quote_api().addurltodb("bob", "random", "https://b.com")
        ret = bot.handle_stats_invokes("urls")
        assert "bob" in ret

    def test_stats_mentions_empty(self, fresh_db):
        ret = bot.handle_stats_invokes("mentions")
        assert "No user mentions" in ret

    def test_stats_mentions_with_quote(self, fresh_db):
        bot.quote_api().addtodb("u", "c", "!add hello <@U123> world")
        with patch.object(bot, "request_display_name", return_value="alice"):
            ret = bot.handle_stats_invokes("mentions")
        assert "alice" in ret or "U123" in ret

    def test_stats_unknown(self, fresh_db):
        ret = bot.handle_stats_invokes("")
        assert "!stats quotes" in ret or "quotes" in ret.lower()
