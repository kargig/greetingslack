"""Tests for helper functions and message/event predicates."""
import pytest

# Import after conftest has set env and patched logging
import bot


class TestFindURL:
    def test_finds_http(self):
        assert bot.FindURL("check http://example.com") == ["http://example.com"]

    def test_finds_https(self):
        assert bot.FindURL("https://slack.com/team/U123") == ["https://slack.com/team/U123"]

    def test_finds_multiple(self):
        urls = bot.FindURL("a https://a.com b http://b.com")
        assert "https://a.com" in urls
        assert "http://b.com" in urls

    def test_empty_string(self):
        assert bot.FindURL("") == []

    def test_no_url(self):
        assert bot.FindURL("no url here") == []


class TestUnescape:
    def test_lt_gt_amp(self):
        assert bot.unescape("&lt;tag&gt; a &amp; b") == "<tag> a & b"

    def test_amp_last(self):
        assert bot.unescape("&amp;") == "&"
        assert bot.unescape("&lt;&amp;&gt;") == "<&>"


class TestMessagePredicates:
    def test_is_team_join(self):
        assert bot.is_team_join({"type": "team_join"}) is True
        assert bot.is_team_join({"type": "message"}) is False

    def test_is_debug_channel_join(self):
        assert bot.is_debug_channel_join({"type": "member_joined_channel", "channel": bot.DEBUG_CHANNEL_ID}) is True
        assert bot.is_debug_channel_join({"type": "member_joined_channel", "channel": "COTHER"}) is False
        assert bot.is_debug_channel_join({"type": "message"}) is False

    def test_welcome_me(self):
        assert bot.welcome_me({"type": "message", "text": "!welcome"}) is True
        assert bot.welcome_me({"type": "message", "text": "!help"}) is False
        assert bot.welcome_me({"type": "message"}) is False
        assert bot.welcome_me({"type": "other"}) is False

    def test_coc_message(self):
        assert bot.coc_message({"type": "message", "text": "!coc"}) is True
        assert bot.coc_message({"type": "message", "text": "!quote"}) is False

    def test_is_message(self):
        assert bot.is_message({"type": "message"}) is True
        assert bot.is_message({"type": "team_join"}) is False

    def test_show_quote(self):
        assert bot.show_quote({"type": "message", "text": "!quote"}) is True
        assert bot.show_quote({"type": "message", "text": "!quote foo"}) is False

    def test_add_quote(self):
        assert bot.add_quote({"type": "message", "text": "!add"}) is True
        # add_quote predicate matches only exact "!add"; "!add something" is handled as a command in parse_message
        assert bot.add_quote({"type": "message", "text": "!add something"}) is False
        assert bot.add_quote({"type": "message", "text": "!help"}) is False


class TestWelcomeAndCoc:
    def test_welcome_message_from_env(self):
        assert bot.welcome_message() == "Welcome test"

    def test_coc_text_from_env(self):
        assert bot.coc_text() == "CoC test"
