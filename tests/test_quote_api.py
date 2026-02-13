"""Tests for quote_api: addtodb, get_quote, addurltodb, get_url, addfiletodb."""
import pytest

import bot


class TestQuoteApiQuotes:
    def test_addtodb_returns_id(self, fresh_db):
        q = bot.quote_api()
        ret = q.addtodb("alice", "general", "!add first quote")
        assert ret == "Quote 1 added!"
        ret = q.addtodb("bob", "random", "!add second quote")
        assert ret == "Quote 2 added!"

    def test_get_quote_random_empty(self, fresh_db):
        q = bot.quote_api()
        out = q.get_quote("u", "c", "!quote")
        assert out is None

    def test_get_quote_random_after_add(self, fresh_db):
        q = bot.quote_api()
        q.addtodb("alice", "general", "!add hello world")
        out = q.get_quote("u", "c", "!quote")
        assert out is not None
        assert "hello world" in out
        assert "alice" in out
        assert "ID:1" in out

    def test_get_quote_by_id(self, fresh_db):
        q = bot.quote_api()
        q.addtodb("alice", "general", "!add unique by id")
        out = q.get_quote("u", "c", "!quote id:1")
        assert out is not None
        assert "unique by id" in out

    def test_get_quote_search(self, fresh_db):
        q = bot.quote_api()
        q.addtodb("alice", "general", "!add banana split")
        q.addtodb("bob", "general", "!add apple pie")
        out = q.get_quote("u", "c", "!quote banana")
        assert out is not None
        assert "banana" in out.lower()


class TestQuoteApiUrls:
    def test_addurltodb_returns_id(self, fresh_db):
        q = bot.quote_api()
        ret = q.addurltodb("alice", "general", "https://example.com/page")
        assert ret == "URL 1 added!"

    def test_get_url_new_returns_false(self, fresh_db):
        q = bot.quote_api()
        out = q.get_url("https://new-url.com")
        assert out is False

    def test_get_url_after_add_returns_info(self, fresh_db):
        q = bot.quote_api()
        q.addurltodb("alice", "general", "https://repeated.com")
        out = q.get_url("https://repeated.com")
        assert out is not None
        assert "alice" in out
        assert "general" in out
        assert "repeated.com" in out
        assert "1" in out or "times" in out

    def test_get_url_increments_mention_count(self, fresh_db):
        q = bot.quote_api()
        q.addurltodb("alice", "general", "https://count-test.com")
        q.get_url("https://count-test.com")
        out = q.get_url("https://count-test.com")
        assert "3" in out or "times" in out


class TestQuoteApiFiles:
    def test_addfiletodb(self, fresh_db):
        q = bot.quote_api()
        ret = q.addfiletodb("alice", "general", "hash123", "doc.pdf")
        assert ret is True
        dba = bot.db_api()
        row = dba.query_db("SELECT ADDED_BY, ORIG_NAME FROM FILES WHERE HASH = ?", "hash123")
        assert row == ("alice", "doc.pdf")
