"""Tests for db_api: init_db, query_*, execute_and_commit, increment_url_mention."""
import pytest

import bot


class TestDbApiInitAndQuery:
    def test_init_db_and_query(self, fresh_db):
        dba = bot.db_api()
        row = dba.query_db("SELECT 1")
        assert row == (1,)

    def test_query_db_with_pattern(self, fresh_db):
        dba = bot.db_api()
        dba.execute_and_commit([
            ("INSERT INTO quotes_fts (QUOTE) VALUES (?)", ("hello",)),
            ("INSERT INTO quotes (QUOTE_DT, ADDED_BY, CHANNEL) VALUES (?, ?, ?)", ("2020-01-01 00:00:00", "u", "c")),
        ])
        out = dba.query_db("SELECT quote FROM quotes_fts WHERE quotes_fts MATCH ?", "hello")
        assert out is not None
        assert "hello" in out[0]

    def test_query_db_many(self, fresh_db):
        dba = bot.db_api()
        dba.execute_and_commit([
            ("INSERT INTO URLS (URL_DT, ADDED_BY, CHANNEL, URL, MENTION_COUNT) VALUES (?,?,?,?,1)", ("2020-01-01", "u", "c", "http://x.com")),
        ])
        rows = dba.query_db_many("SELECT ADDED_BY, URL FROM URLS", None)
        assert len(rows) == 1
        assert rows[0][0] == "u"
        assert rows[0][1] == "http://x.com"

    def test_query_maxid(self, fresh_db):
        dba = bot.db_api()
        assert dba.query_maxid("SELECT MAX(rowid) FROM quotes") is None
        dba.execute_and_commit([
            ("INSERT INTO quotes_fts (QUOTE) VALUES (?)", ("q",)),
            ("INSERT INTO quotes (QUOTE_DT, ADDED_BY, CHANNEL) VALUES (?, ?, ?)", ("2020-01-01 00:00:00", "u", "c")),
        ])
        max_id = dba.query_maxid("SELECT MAX(rowid) FROM quotes")
        assert max_id == 1

    def test_execute_and_commit_multiple(self, fresh_db):
        dba = bot.db_api()
        dba.execute_and_commit([
            ("INSERT INTO FILES (FILE_DT, ADDED_BY, CHANNEL, HASH, ORIG_NAME) VALUES (?,?,?,?,?)", ("2020-01-01 00:00:00", "u", "c", "abc", "file.txt")),
        ])
        row = dba.query_db("SELECT ORIG_NAME FROM FILES WHERE HASH = ?", "abc")
        assert row == ("file.txt",)

    def test_increment_url_mention(self, fresh_db):
        dba = bot.db_api()
        dba.execute_and_commit([
            ("INSERT INTO URLS (URL_DT, ADDED_BY, CHANNEL, URL, MENTION_COUNT) VALUES (?,?,?,?,1)", ("2020-01-01", "u", "c", "http://y.com")),
        ])
        c = dba.increment_url_mention("http://y.com")
        assert c == 2
        c = dba.increment_url_mention("http://y.com")
        assert c == 3
        # unknown URL returns None
        assert dba.increment_url_mention("http://unknown.com") is None
