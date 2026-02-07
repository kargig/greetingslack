#!/usr/bin/env python
# -*- coding: utf-8 -*-
import codecs
import logging
import json
import requests
import os
import sys
import sqlite3
import time
import re
import hashlib
from collections import Counter
from functools import lru_cache
from slack_sdk.socket_mode import SocketModeClient
from slack_sdk.web import WebClient
from slack_sdk.socket_mode.request import SocketModeRequest
from slack_sdk.socket_mode.response import SocketModeResponse

# Suppress InsecureRequestWarning
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

logging.basicConfig(filename='/backup/greetingslack/bot.log', level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(funcName)s() - %(levelname)s - %(message)s')

# ENV VARS
SLACK_APP_TOKEN = os.environ.get('SLACK_APP_TOKEN')  # xapp-...
SLACK_BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN')  # xoxb-...
TOKEN = SLACK_BOT_TOKEN  # For legacy code compatibility
UNFURL = os.environ.get('UNFURL_LINKS', 'FALSE')
DEBUG_CHANNEL_ID = os.environ.get('DEBUG_CHANNEL_ID','Manually set the Channel if youre not running through heroku or have not set vars in ENV')
DB_FILE = os.environ.get('DB_FILE','FALSE')
WELCOME_FILE = os.environ.get('WELCOME_FILE','/path/to/WELCOME_MESSAGE.txt')
DOWNLOAD_DIR = os.environ.get('DOWNLOAD_DIR','/tmp/')
COC_FILE = os.environ.get('COC_FILE','/path/to/COC_FILE.txt')

###############################################################


# Slack user mention in text: <@U01234ABCD> or profile link https://app.slack.com/team/U01234ABCD|name
SLACK_MENTION_RE = re.compile(r'<@(U[A-Z0-9]+)>')
SLACK_TEAM_LINK_RE = re.compile(r'app\.slack\.com/team/(U[A-Z0-9]+)')
# IRC-style / bracket username at start or anywhere: <ebal>, <kyriakos> (exclude <@, <http, <#)
BRACKET_NAME_RE = re.compile(r'<(?!@|https?://|#)([a-zA-Z0-9_]+)>')
SLACK_ID_RE = re.compile(r'^U[A-Z0-9]+$')


def FindURL(string):
    # findall() has been used
    # with valid conditions for urls in string
    url = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', string)
    return url


def unescape(s):
    s = s.replace("&lt;", "<")
    s = s.replace("&gt;", ">")
    # this has to be last:
    s = s.replace("&amp;", "&")
    return s


def welcome_message():
    try:
        message = os.environ['WELCOME_MESSAGE']
    except KeyError:
        with codecs.open(WELCOME_FILE, 'r', encoding='utf8') as f:
            message = f.read()
    return message


def coc_text():
    try:
        message = os.environ['COC_MESSAGE']
    except KeyError:
        with codecs.open(COC_FILE, 'r', encoding='utf8') as f:
            message = f.read()
    return message


def is_team_join(msg):
    return msg['type'] == "team_join"


def is_debug_channel_join(msg):
    return (msg['type'] == "member_joined_channel" and msg['channel'] == DEBUG_CHANNEL_ID)


def welcome_me(msg):
    if msg['type'] == 'message' and 'text' in msg.keys():
        return msg['text'] == '!welcome'
    else:
        return False


def coc_message(msg):
    if msg['type'] == 'message' and 'text' in msg.keys():
        return msg['text'] == '!coc'
    else:
        return False


def is_message(msg):
    return msg['type'] == 'message'


def show_quote(msg):
    return msg['type'] == 'message' and msg['text'] == '!quote'


def add_quote(msg):
    return msg['type'] == 'message' and msg['text'] == '!add'


def bot_called(msg):
    # logging.debug(msg)
    if is_message(msg) and 'text' in msg.keys():
        return msg['text'].startswith('!greetbot')
    else:
        return False


def parse_message(message):
    try:
        m = json.loads(message)
    except (ValueError, json.JSONDecodeError):
        return
    # logging.debug(m)

    if bot_called(m):
        channel_name = request_channel_name(channel_id=m['channel'])
        data = {
                'token': TOKEN,
                'channel': channel_name,
                'text': 'Channel cache: '+ str(request_channel_name.cache_info()) +
                  '\n Display name cache: ' + str(request_display_name.cache_info()),
                'parse': 'full',
                'as_user': 'true',
        }
        if (UNFURL.lower() == "false"):
            data['unfurl_link'] = 'false'
            # logging.debug(data)
        send_message = requests.post("https://slack.com/api/chat.postMessage", data=data)
        #logging.debug(request_channel_name.cache_info())
        #logging.debug(request_display_name.cache_info())


    if coc_message(m):
        channel_name = request_channel_name(channel_id=m['channel'])
        data = {
                'token': TOKEN,
                'channel': channel_name,
                'text': coc_text(),
                'parse': 'full',
                'as_user': 'true',
        }
        if (UNFURL.lower() == "false"):
            data['unfurl_link'] = 'false'
            # logging.debug(data)
        send_message = requests.post("https://slack.com/api/chat.postMessage", data=data, headers={"Authorization": "Bearer " + TOKEN})
    elif is_team_join(m) or is_debug_channel_join(m) or welcome_me(m):
        user_id = m["user"]["id"] if is_team_join(m) else m["user"]
        getdata = {
                'token': TOKEN,
                'users': user_id
                }
        getdata.pop('token')  # fails if present (for non legacy token)
        userdata = requests.get("https://slack.com/api/conversations.open", params=getdata, headers={"Authorization": "Bearer " + TOKEN})
        userdata = userdata.json()
        if not userdata.get('ok') or 'channel' not in userdata:
            logging.error("conversations.open failed: %s", userdata.get('error', 'unknown'))
            return
        dmchannel = userdata["channel"]["id"]
        data = {
                'token': TOKEN,
                'channel': dmchannel,
                'text': welcome_message(),
                'parse': 'full',
                'as_user': 'true',
        }
        if (UNFURL.lower() == "false"):
            data['unfurl_link'] = 'false'
            # logging.debug(data)
        send_message = requests.post("https://slack.com/api/chat.postMessage", data=data, headers={"Authorization": "Bearer " + TOKEN})
    elif is_message(m) and 'files' in m.keys() and m.get('files'):
        # just get the first file for now
        zefile = m['files'][0]['url_private']
        headers = {'Authorization': 'Bearer ' + TOKEN}
        filedata = requests.get(zefile, headers=headers)
        filename = m['files'][0]['name']
        timestamp = m['files'][0]['timestamp']
        id = m['files'][0]['id']
        hashname = hashlib.sha256(filename.encode("utf-8")+str(timestamp).encode("utf-8")+str(id).encode("utf-8")).hexdigest()
        savepath = DOWNLOAD_DIR + hashname
        with open(savepath, 'wb') as f:
            f.write(filedata.content)
        displayname = request_display_name(user_id=m['user'])
        channel_name = request_channel_name(channel_id=m['channel'])
        f_args = [displayname, channel_name, hashname, filename]
        quote_api().addfiletodb(*f_args)
    elif is_message(m) and 'text' in m.keys():
        ret = None
        if 'bot_id' in m.keys():
            return
        text = m.get('text') or ''
        if not text:
            return
        if text[0] != '!':
            # logging.debug(m)
            # u'blocks': [{u'elements': [{u'elements': [{u'url': u'http://koko.org', u'text': u'koko.org', u'type': u'link'}]
            if 'blocks' in m.keys():
                try:
                    link_block = m['blocks'][0]['elements'][0]['elements'][0]
                except (KeyError, IndexError, TypeError):
                    link_block = None
                if isinstance(link_block, dict) and 'url' in link_block:
                    urls = FindURL(link_block['url'])
                    if len(urls) > 0:
                        logging.debug("Found URL: " + link_block['url'])
                        displayname = request_display_name(user_id=m['user'])
                        channel_name = request_channel_name(channel_id=m['channel'])
                        # trim trailing '>' added by Slack in link formatting
                        final_URL = urls[0][:-1] if urls[0].endswith('>') else urls[0]
                        ret = quote_api().get_url(final_URL)
                        if ret:
                            ret = ret.replace('@', '')
                            data = {
                                    'token': TOKEN,
                                    'channel': m['channel'],
                                    'text': ret,
                                    'parse': 'full',
                                    'as_user': 'true',
                            }
                            send_message = requests.post("https://slack.com/api/chat.postMessage", data=data, headers={"Authorization": "Bearer " + TOKEN})
                            # logging.debug(send_message)
                            return
                        f_args = [displayname, channel_name, final_URL]
                        ret = quote_api().addurltodb(*f_args)
                    return
        elif text[0] == '!':
            try:
                cmd, args = text.split(' ', 1)
            except ValueError:
                cmd = text
                args = ''
            displayname = request_display_name(user_id=m['user'])
            channel_name = request_channel_name(channel_id=m['channel'])
            f_args = [displayname, channel_name, text]
            if cmd == '!quote':
                ret = quote_api().get_quote(*f_args)
            elif cmd == '!add':
                ret = quote_api().addtodb(*f_args)

            elif cmd == '!cache':
                ret = handle_cache_invokes(args)
            elif cmd == '!stats':
                ret = handle_stats_invokes(args)

            if ret:
                ret = ret.replace('@', '')
                data = {
                        'token': TOKEN,
                        'channel': m['channel'],
                        'text': ret,
                        'parse': 'full',
                        'as_user': 'true',
                }
                send_message = requests.post("https://slack.com/api/chat.postMessage", data=data, headers={"Authorization": "Bearer " + TOKEN})
                # logging.debug(send_message)


def handle_cache_invokes(args):
    if args == 'clear':
        request_display_name.cache_clear()
        request_channel_name.cache_clear()
        ret = "Display name and channel caches cleared."
    elif 'stats' in args:
        name_stats = str(request_display_name.cache_info())
        channel_stats = str(request_channel_name.cache_info())
        ret = "Display Name cache stats: {}\nChannel Name cache stats: {}".format(name_stats, channel_stats)
    else:
        ret = "Use `!cache stats` for statistics, or `!cache clear` for clearing LRU cache"
    return(ret)


def handle_stats_invokes(args):
    """Handle !stats quotes and !stats urls for leaderboards."""
    dba = db_api()
    limit = 10
    arg = args.strip().lower() if args else ''
    if arg == 'quotes':
        rows = dba.query_db_many(
            '''SELECT ADDED_BY, COUNT(*) AS cnt FROM quotes GROUP BY ADDED_BY ORDER BY cnt DESC LIMIT ?''',
            (limit,),
        )
        if not rows:
            return "No quotes in the database yet."
        lines = ["Top quote adders:"]
        for i, (user, cnt) in enumerate(rows, 1):
            lines.append("{}. {} — {}".format(i, user or '?', cnt))
        return '\n'.join(lines)
    elif arg == 'urls':
        rows = dba.query_db_many(
            '''SELECT ADDED_BY, COUNT(*) AS cnt FROM URLS GROUP BY ADDED_BY ORDER BY cnt DESC LIMIT ?''',
            (limit,),
        )
        if not rows:
            return "No URLs in the database yet."
        lines = ["Top URL adders:"]
        for i, (user, cnt) in enumerate(rows, 1):
            lines.append("{}. {} — {}".format(i, user or '?', cnt))
        return '\n'.join(lines)
    elif arg == 'mentions':
        # Most often mentioned: <@U...>, app.slack.com/team/U..., and <name> (bracket usernames)
        quote_rows = dba.query_db_many('''SELECT quote FROM quotes_fts''')
        raw_counts = Counter()
        for (quote_text,) in quote_rows:
            if quote_text:
                text = unescape(quote_text)
                raw_counts.update(SLACK_MENTION_RE.findall(text))
                raw_counts.update(SLACK_TEAM_LINK_RE.findall(text))
                raw_counts.update(BRACKET_NAME_RE.findall(text))
        if not raw_counts:
            return "No user mentions found in quotes yet."
        # Merge by canonical name: resolve Slack IDs to display name so <@U...> and <ebal> combine
        merged = Counter()
        for key, cnt in raw_counts.items():
            if SLACK_ID_RE.match(key):
                canonical = request_display_name(key) or key
            else:
                canonical = key
            merged[canonical] += cnt
        lines = ["Most mentioned users in quotes:"]
        for i, (name, cnt) in enumerate(merged.most_common(limit), 1):
            lines.append("{}. {} — {} mention{}".format(i, name, cnt, 's' if cnt != 1 else ''))
        return '\n'.join(lines)
    else:
        return "Use `!stats quotes` (top quote adders), `!stats urls` (top URL adders), or `!stats mentions` (most mentioned in quotes)."


@lru_cache(maxsize=256)
def request_display_name(user_id):
    try:
        udata = {
            'token': TOKEN,  # Include token first
            'user': user_id
        }
        udata.pop('token')  # Remove from params for non-legacy token
        userdata = requests.get(
            "https://slack.com/api/users.info",
            params=udata,
            headers={"Authorization": f"Bearer {TOKEN}"}  # Pass token in header
        )
        userdata.raise_for_status()  # Raise exception for bad status codes
        response = userdata.json()
        if not response.get('ok'):
            raise Exception(f"Slack API error: {response.get('error')}")
        return response['user']['profile']['display_name']
    except Exception as e:
        logging.error(f"Error fetching display name for user {user_id}: {str(e)}")
        return None


@lru_cache(maxsize=16)
def request_channel_name(channel_id):
    """
    channel_id: String with the slack channel id to request from slack api
    returns: string with either the slack name or the slack id
    """
    cdata = {
            'token': TOKEN,
            'channel': channel_id
            }
    cdata.pop('token')  # fails if present (for non legacy token)
    channeldata = requests.get("https://slack.com/api/conversations.info", params=cdata, headers={"Authorization": "Bearer " + TOKEN})
    channeldata = channeldata.json()
    try:
        channel_name = channeldata['channel']['name']
    except KeyError:
        channel_name = channel_id
    return(channel_name)

class quote_api:

    def __init__(self):
        """
        """

    def get_quote(self, user, channel, msg):
        toks = msg.split(' ')
        dba = db_api()
        final_text = None
        quote_text = None
        out = None
        if len(toks) < 2:
            query = '''SELECT id, quote,added_by,quote_dt FROM quotes,quotes_fts where quotes.rowid=quotes_fts.rowid ORDER BY RANDOM() LIMIT 1'''
            out = dba.query_db(query)
        else:
            idq = re.match('id:', toks[1])
            if idq:
                idx = toks[1].split(':', 1)
                if idx[1].isdigit():
                    query = '''SELECT id, quote, added_by, quote_dt FROM quotes,quotes_fts WHERE quotes.id=quotes_fts.rowid AND id == ?'''
                    pattern = idx[1]
                else:
                    query = None
            else:
                query = '''SELECT id, quote,added_by,quote_dt FROM quotes,quotes_fts WHERE quotes.id=quotes_fts.rowid AND quotes_fts MATCH ? ORDER BY RANDOM()'''
                pattern = '%s' % ' ' . join(toks[1:])

            if query:
                out = dba.query_db(query, pattern)

        # logging.debug(out)
        if out and (len(out) >= 2):
            quote_id = out[0]    # id
            quote_text = out[1]  # quote

        quote_time = ''
        quote_user = ''
        if out and (len(out) == 4):
            quote_user = out[2]  # user
            quote_time = out[3]  # time

        if quote_text:
            quote_text = unescape(quote_text)
            final_text = '[' + 'ID:' + str(quote_id) + ' by:' + quote_user + ' at:' + quote_time + '] ' + quote_text

        return final_text

    def get_url(self, url):
        dba = db_api()
        final_text = None
        out = None
        query = '''SELECT URL_DT,ADDED_BY,CHANNEL,URL,MENTION_COUNT FROM URLS WHERE URL == ?'''
        pattern = url
        if query:
            out = dba.query_db(query, pattern)
        if out:
            url_dt = out[0]       # timestamp
            url_user = out[1]     # username
            url_channel = out[2]  # channel
            # Increment mention count for this URL and get new count (handles missing column in old DBs)
            new_count = dba.increment_url_mention(url)
            if new_count is None:
                new_count = (out[4] + 1) if len(out) > 4 and out[4] is not None else 2
            final_text = ('[' + 'URL: ' + str(url) + ' posted first on: #' + url_channel + ' by: ' + url_user + ' at: ' + url_dt +
                         ' | mentioned ' + str(new_count) + ' times so far] ')
            # logging.debug(final_text)
            return final_text
        return False

    def addtodb(self, user, channel, msg):
        ret = None
        dba = db_api()
        db = sqlite3.connect(DB_FILE)
        dbc = db.cursor()
        quote = ' ' . join(msg.split(' ')[1:])
        query = '''INSERT INTO quotes_fts (QUOTE) VALUES (?)'''
        dbc.execute(query, (quote,))
        query = '''INSERT INTO quotes (QUOTE_DT, ADDED_BY, CHANNEL) VALUES (?, ?, ?)'''
        dbc.execute(query, (time.strftime('%Y-%m-%d %H:%M:%S'), user, channel))
        db.commit()
        db.close()

        # No intention of deleting, ever...
        query = '''SELECT MAX(rowid) FROM quotes'''
        max_q = dba.query_maxid(query)
        ret = 'Quote ' + str(max_q) + ' added!'
        return ret

    def addfiletodb(self, user, channel, hashname, orig_name):
        db = sqlite3.connect(DB_FILE)
        dbc = db.cursor()
        query = '''INSERT INTO FILES (FILE_DT, ADDED_BY, CHANNEL, HASH, ORIG_NAME) VALUES (?,?,?,?,?)'''
        dbc.execute(query, (time.strftime('%Y-%m-%d %H:%M:%S'), user, channel, hashname, orig_name))
        db.commit()
        db.close()
        return True

    def addurltodb(self, user, channel, url):
        ret = None
        dba = db_api()
        db = sqlite3.connect(DB_FILE)
        dbc = db.cursor()
        query = '''INSERT INTO URLS (URL_DT, ADDED_BY, CHANNEL, URL, MENTION_COUNT) VALUES (?,?,?,?,1)'''
        dbc.execute(query, (time.strftime('%Y-%m-%d %H:%M:%S'), user, channel, url))
        db.commit()
        db.close()

        # No intention of deleting, ever...
        query = '''SELECT MAX(rowid) FROM URLS'''
        max_q = dba.query_maxid(query)
        ret = 'URL ' + str(max_q) + ' added!'
        return ret


class db_api:

    def __init__(self):
        self.db_file = DB_FILE

    def init_db(self):
        """Initialize the database schema"""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.executescript("""
                CREATE VIRTUAL TABLE IF NOT EXISTS QUOTES_FTS USING fts5(
                    QUOTE
                );

                CREATE TABLE IF NOT EXISTS QUOTES (
                    ID INTEGER PRIMARY KEY,
                    QUOTE_DT DATETIME,
                    ADDED_BY TEXT,
                    CHANNEL TEXT
                );

                CREATE TABLE IF NOT EXISTS FILES (
                    ID INTEGER PRIMARY KEY,
                    FILE_DT DATETIME,
                    ADDED_BY TEXT,
                    CHANNEL TEXT,
                    HASH TEXT,
                    ORIG_NAME TEXT
                );

                CREATE TABLE IF NOT EXISTS URLS (
                    ID INTEGER PRIMARY KEY,
                    URL_DT DATETIME,
                    ADDED_BY TEXT,
                    CHANNEL TEXT,
                    URL TEXT,
                    MENTION_COUNT INTEGER DEFAULT 1
                );
            """)

    def query_db(self, query, pattern=None):
        """Execute a query and return results"""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                if pattern:
                    cursor.execute(query, (pattern,))
                else:
                    cursor.execute(query)
                return cursor.fetchone()
        except sqlite3.Error as e:
            logging.error(f"Database query error: {e}")
            return None

    def query_db_many(self, query, params=None):
        """Execute a query and return all rows. params is an optional tuple for ? placeholders."""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                if params is not None:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                return cursor.fetchall()
        except sqlite3.Error as e:
            logging.error(f"Database query error: {e}")
            return []

    def add_dbrow(self, query, quote, user=None, channel=None):
        """Add a row to the database"""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute(query, (quote, time.strftime('%H-%M-%S %d-%m-%Y'), user, channel))
                conn.commit()
        except sqlite3.Error as e:
            logging.error(f"Database insert error: {e}")

    def query_maxid(self, query):
        """Get the maximum ID from a query"""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                result = cursor.fetchone()
                return result[0] if result else None
        except sqlite3.Error as e:
            logging.error(f"Database maxid query error: {e}")
            return None

    def increment_url_mention(self, url):
        """Increment MENTION_COUNT for the given URL and return the new count."""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    '''UPDATE URLS SET MENTION_COUNT = COALESCE(MENTION_COUNT, 1) + 1 WHERE URL = ?''',
                    (url,)
                )
                conn.commit()
                cursor.execute('''SELECT MENTION_COUNT FROM URLS WHERE URL = ?''', (url,))
                row = cursor.fetchone()
                return row[0] if row else None
        except sqlite3.Error as e:
            logging.error(f"Database increment_url_mention error: {e}")
            return None


# --- Socket Mode Event Handlers ---
web_client = WebClient(token=SLACK_BOT_TOKEN)

# Helper to send a message
def send_message(channel, text):
    web_client.chat_postMessage(channel=channel, text=text, unfurl_links=(UNFURL.lower() == 'true'))

def handle_event(event):
    # Reuse the logic from parse_message, but adapt to the new event structure
    m = event
    if bot_called(m):
        channel_name = request_channel_name(channel_id=m['channel'])
        text = 'Channel cache: '+ str(request_channel_name.cache_info()) + \
               '\n Display name cache: ' + str(request_display_name.cache_info())
        send_message(channel_name, text)
    elif coc_message(m):
        channel_name = request_channel_name(channel_id=m['channel'])
        send_message(channel_name, coc_text())
    elif is_team_join(m) or is_debug_channel_join(m) or welcome_me(m):
        user_id = m["user"]["id"] if is_team_join(m) else m["user"]
        try:
            resp = web_client.conversations_open(users=user_id)
            if not resp.get("ok") or "channel" not in resp:
                logging.error("conversations_open failed: %s", resp.get("error", "unknown"))
            else:
                dmchannel = resp["channel"]["id"]
                send_message(dmchannel, welcome_message())
        except (KeyError, TypeError, AttributeError) as e:
            logging.error("conversations_open response error: %s", e)
    elif is_message(m) and 'files' in m.keys() and m.get('files'):
        zefile = m['files'][0]['url_private']
        headers = {'Authorization': 'Bearer ' + TOKEN}
        filedata = requests.get(zefile, headers=headers)
        filename = m['files'][0]['name']
        timestamp = m['files'][0]['timestamp']
        id = m['files'][0]['id']
        hashname = hashlib.sha256(filename.encode("utf-8")+str(timestamp).encode("utf-8")+str(id).encode("utf-8")).hexdigest()
        savepath = DOWNLOAD_DIR + hashname
        with open(savepath, 'wb') as f:
            f.write(filedata.content)
        displayname = request_display_name(user_id=m['user'])
        channel_name = request_channel_name(channel_id=m['channel'])
        f_args = [displayname, channel_name, hashname, filename]
        quote_api().addfiletodb(*f_args)
    elif is_message(m) and 'text' in m.keys():
        ret = None
        if 'bot_id' in m.keys():
            return
        text = m.get('text') or ''
        if not text:
            return
        if text[0] != '!':
            if 'blocks' in m.keys():
                try:
                    link_block = m['blocks'][0]['elements'][0]['elements'][0]
                except (KeyError, IndexError, TypeError):
                    link_block = None
                if isinstance(link_block, dict) and 'url' in link_block:
                    urls = FindURL(link_block['url'])
                    if len(urls) > 0:
                        displayname = request_display_name(user_id=m['user'])
                        channel_name = request_channel_name(channel_id=m['channel'])
                        # trim trailing '>' added by Slack in link formatting
                        final_URL = urls[0][:-1] if urls[0].endswith('>') else urls[0]
                        ret = quote_api().get_url(final_URL)
                        if ret:
                            ret = ret.replace('@', '')
                            send_message(m['channel'], ret)
                            return
                        f_args = [displayname, channel_name, final_URL]
                        ret = quote_api().addurltodb(*f_args)
                    return
        elif text[0] == '!':
            try:
                cmd, args = text.split(' ', 1)
            except ValueError:
                cmd = text
                args = ''
            displayname = request_display_name(user_id=m['user'])
            channel_name = request_channel_name(channel_id=m['channel'])
            f_args = [displayname, channel_name, text]
            if cmd == '!quote':
                ret = quote_api().get_quote(*f_args)
            elif cmd == '!add':
                ret = quote_api().addtodb(*f_args)
            elif cmd == '!cache':
                ret = handle_cache_invokes(args)
            elif cmd == '!stats':
                ret = handle_stats_invokes(args)
            if ret:
                ret = ret.replace('@', '')
                send_message(m['channel'], ret)

# Main Socket Mode event handler

def process(client: SocketModeClient, req: SocketModeRequest):
    if req.type == "events_api":
        event = req.payload["event"]
        # Acknowledge immediately so Slack does not retry (avoids duplicate replies)
        client.send_socket_mode_response(SocketModeResponse(envelope_id=req.envelope_id))
        if event.get('type') in ["message", "team_join", "member_joined_channel"]:
            handle_event(event)

if __name__ == "__main__":
    # Check for required tokens
    if not SLACK_APP_TOKEN or not SLACK_BOT_TOKEN:
        print("SLACK_APP_TOKEN and SLACK_BOT_TOKEN must be set in the environment.")
        sys.exit(1)
    db_api().init_db()
    socket_mode_client = SocketModeClient(
        app_token=SLACK_APP_TOKEN,
        web_client=web_client
    )
    socket_mode_client.socket_mode_request_listeners.append(process)
    socket_mode_client.connect()
    import time; time.sleep(999999)
