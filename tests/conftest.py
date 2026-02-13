# Configure test environment before bot is imported (bot reads os.environ at import time).
import os
import sys
import tempfile
import logging

# Set env so bot module can be imported without missing vars or writing to real paths
def _setup_test_env():
    os.environ.setdefault("DB_FILE", os.path.join(tempfile.gettempdir(), "greetingslack_test.sqlite"))
    os.environ.setdefault("SLACK_BOT_TOKEN", "xoxb-test")
    os.environ.setdefault("SLACK_APP_TOKEN", "xapp-test")
    os.environ.setdefault("WELCOME_MESSAGE", "Welcome test")
    os.environ.setdefault("COC_MESSAGE", "CoC test")
    os.environ.setdefault("DEBUG_CHANNEL_ID", "C_TEST")


_setup_test_env()

# Prevent bot from calling basicConfig with a fixed path (avoids /backup/greetingslack/bot.log)
_original_basicConfig = logging.basicConfig
def _test_basicConfig(*args, **kwargs):
    kwargs.pop("filename", None)
    kwargs.setdefault("format", "%(levelname)s %(message)s")
    kwargs.setdefault("stream", sys.stderr)
    if "level" not in kwargs:
        kwargs["level"] = logging.DEBUG
    _original_basicConfig(*args, **kwargs)
logging.basicConfig = _test_basicConfig


def pytest_configure(config):
    """Ensure test env is set before any test collection imports bot."""
    _setup_test_env()


import pytest


@pytest.fixture
def fresh_db():
    """Provide a fresh temporary database; patch bot.DB_FILE and init schema."""
    import bot
    fd, path = tempfile.mkstemp(suffix=".sqlite")
    os.close(fd)
    old_db = bot.DB_FILE
    bot.DB_FILE = path
    try:
        bot.db_api().init_db()
        yield path
    finally:
        bot.DB_FILE = old_db
        try:
            os.unlink(path)
        except OSError:
            pass
