#!/usr/bin/env python
# -*- coding: utf-8 -*-
import codecs
import logging
import websocket
import json
import requests
import os
import sys
import sqlite3
import time
import re
import hashlib
from functools import lru_cache

# Suppress InsecureRequestWarning
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

logging.basicConfig(filename='/backup/greetingslack/bot.log', level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(funcName)s() - %(levelname)s - %(message)s')


# VARIABLES THAT YOU NEED TO SET MANUALLY IF NOT ON HEROKU
# Handle each one seperately

TOKEN = os.environ.get('SLACK_TOKEN','Manually set the API Token if youre not running through heroku or have not set vars in ENV')
UNFURL = os.environ.get('UNFURL_LINKS', 'FALSE')
DEBUG_CHANNEL_ID = os.environ.get('DEBUG_CHANNEL_ID','Manually set the Channel if youre not running through heroku or have not set vars in ENV')
DB_FILE = os.environ.get('DB_FILE','FALSE')
WELCOME_FILE = os.environ.get('WELCOME_FILE','/path/to/WELCOME_MESSAGE.txt')
DOWNLOAD_DIR = os.environ.get('DOWNLOAD_DIR','/tmp/')
COC_FILE = os.environ.get('COC_FILE','/path/to/COC_FILE.txt')

###############################################################


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


def parse_message(message):
    try:
        m = json.loads(message)
    except:
        # logging.debug(message)
        return
    # logging.debug(m)
    if coc_message(m):
        channel_name = get_channel_name(m)
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
        send_message = requests.post("https://slack.com/api/chat.postMessage", data=data)
    elif is_team_join(m) or is_debug_channel_join(m) or welcome_me(m):
        user_id = m["user"]["id"] if is_team_join(m) else m["user"]
        getdata = {
                'token': TOKEN,
                'users': user_id
                }
        userdata = requests.get("https://slack.com/api/conversations.open", params=getdata)
        userdata = userdata.json()
        # logging.debug(userdata)
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
        send_message = requests.post("https://slack.com/api/chat.postMessage", data=data)
    elif is_message(m) and 'files' in m.keys():
        ret = None
        #logging.debug(m)
        # just get the first file for now
        zefile = m['files'][0]['url_private']
        headers = {'Authorization': 'Bearer ' + TOKEN}
        filedata = requests.get(zefile, headers=headers)
        filename = m['files'][0]['name']
        hashname = hashlib.sha256(filename.encode("utf-8")).hexdigest()
        savepath = DOWNLOAD_DIR + hashname
        with open(savepath, 'wb') as f:
            f.write(filedata.content)
        displayname = get_display_name(m)
        channel_name = get_channel_name(m)
        f_args = [displayname, channel_name, hashname, filename]
        quote_api().addfiletodb(*f_args)
    elif is_message(m) and 'text' in m.keys():
        ret = None
        if 'bot_id' in m.keys():
            return
        if m['text'][0] != '!':
            # logging.debug(m)
            # u'blocks': [{u'elements': [{u'elements': [{u'url': u'http://koko.org', u'text': u'koko.org', u'type': u'link'}]
            if 'blocks' in m.keys():
                if 'url' in m['blocks'][0]['elements'][0]['elements'][0].keys():
                    urls = FindURL(m['blocks'][0]['elements'][0]['elements'][0]['url'])
                    if len(urls) > 0:
                        # logging.debug(m['blocks']['elements']['elements']['url'])
                        logging.debug("Found URL: " + m['blocks'][0]['elements'][0]['elements'][0]['url'])
                        displayname = get_display_name(m)
                        channel_name = get_channel_name(m)
                        # trim last character from url which is a '>' added by slack
                        if urls[0][:-1] == '>':
                            final_URL = urls[0][:-1]
                        else:
                            final_URL = urls[0]
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
                            send_message = requests.post("https://slack.com/api/chat.postMessage", data=data)
                            # logging.debug(send_message)
                            return
                        f_args = [displayname, channel_name, final_URL]
                        ret = quote_api().addurltodb(*f_args)
                    return
        elif m['text'][0] == '!':
            try:
                cmd, args = m['text'].split(' ', 1)
            except ValueError:
                cmd = m['text']
                args = ''
            displayname = get_display_name(m)
            channel_name = get_channel_name(m)
            f_args = [displayname, channel_name, m['text']]
            if cmd == '!quote':
                ret = quote_api().get_quote(*f_args)
            elif cmd == '!add':
                ret = quote_api().addtodb(*f_args)

            if ret:
                ret = ret.replace('@', '')
                data = {
                        'token': TOKEN,
                        'channel': m['channel'],
                        'text': ret,
                        'parse': 'full',
                        'as_user': 'true',
                }
                send_message = requests.post("https://slack.com/api/chat.postMessage", data=data)
                # logging.debug(send_message)


def get_display_name(m):
    # logging.debug("GET_DISPLAY_NAME")
    return request_display_name(user_id=m['user'])


@lru_cache(maxsize=32)
def request_display_name(user_id):    
    udata = {
            'token': TOKEN,
            'user': user_id
            }
    userdata = requests.get("https://slack.com/api/users.info", params=udata)
    userdata = userdata.json()
    # logging.debug(userdata)
    return(userdata['user']['profile']['display_name'])


def get_channel_name(m):
    # logging.debug("GET_CHANNEL_NAME")
    return request_channel_name(channel_id=m['channel'])


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
    channeldata = requests.get("https://slack.com/api/conversations.info", params=cdata)
    channeldata = channeldata.json()
    try:
        channel_name = channeldata['channel']['name']
    except KeyError:
        channel_name = channel_id
    return(channel_name)


# Connects to Slacks and initiates socket handshake
def start_rtm():
    r = requests.get("https://slack.com/api/rtm.connect?token="+TOKEN)
    r = r.json()
    # logging.debug(r)
    r = r["url"]
    return r


def on_message(ws, message):
    parse_message(message)


def on_error(ws, error):
    try:
        logger = logging.getLogger()
        logger.error("SOME ERROR HAS HAPPENED: " + error)
    except:
        print('Interrupted')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)


def on_close(ws):
    logging.info('Connection Closed')


def on_open(ws):
    logging.info("Connection Started - Auto Greeting new joiners to the network")


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
            quote_time = quote_time.replace('-', ':', 2)

        if quote_text:
            quote_text = unescape(quote_text)
            final_text = '[' + 'ID:' + str(quote_id) + ' by:' + quote_user + ' at:' + quote_time + '] ' + quote_text

        return final_text

    def get_url(self, url):
        dba = db_api()
        final_text = None
        out = None
        query = '''SELECT URL_DT,ADDED_BY,CHANNEL,URL FROM URLS WHERE URL == ?'''
        pattern = url
        if query:
            out = dba.query_db(query, pattern)
        if out:
            url_dt = out[0]       # timestamp
            url_user = out[1]     # username
            url_channel = out[2]  # channel
            url_dt = url_dt.replace('-', ':', 2)
            final_text = '[' + 'URL: ' + str(url) + ' posted first on: #' + url_channel + ' by: ' + url_user + ' at: ' + url_dt + '] '
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
        dbc.execute(query, (time.strftime('%H-%M-%S %d-%m-%Y'), user, channel))
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
        dbc.execute(query, (time.strftime('%H-%M-%S %d-%m-%Y'), user, channel, hashname, orig_name))
        db.commit()
        db.close()
        return True

    def addurltodb(self, user, channel, url):
        ret = None
        dba = db_api()
        db = sqlite3.connect(DB_FILE)
        dbc = db.cursor()
        query = '''INSERT INTO URLS (URL_DT, ADDED_BY, CHANNEL, URL) VALUES (?,?,?,?)'''
        dbc.execute(query, (time.strftime('%H-%M-%S %d-%m-%Y'), user, channel, url))
        db.commit()
        db.close()

        # No intention of deleting, ever...
        query = '''SELECT MAX(rowid) FROM URLS'''
        max_q = dba.query_maxid(query)
        ret = 'URL ' + str(max_q) + ' added!'
        return ret


class db_api:

    def __init__(self):
        """
        """

    def init_db(self):
        db = sqlite3.connect(DB_FILE)
        dbc = db.cursor()
        dbc.execute('''CREATE VIRTUAL TABLE IF NOT EXISTS QUOTES_FTS USING fts5(
                                                    QUOTE
                                                    )''')

        dbc.execute('''CREATE TABLE IF NOT EXISTS QUOTES (ID INTEGER PRIMARY KEY,
                                                    QUOTE_DT DATETIME,
                                                    ADDED_BY TEXT,
                                                    CHANNEL TEXT
                                                    )''')

        dbc.execute('''CREATE TABLE IF NOT EXISTS FILES (ID INTEGER PRIMARY KEY,
                                                    FILE_DT DATETIME,
                                                    ADDED_BY TEXT,
                                                    CHANNEL TEXT,
                                                    HASH TEXT,
                                                    ORIG_NAME TEXT
                                                    )''')
        dbc.execute('''CREATE TABLE IF NOT EXISTS URLS (ID INTEGER PRIMARY KEY,
                                                    URL_DT DATETIME,
                                                    ADDED_BY TEXT,
                                                    CHANNEL TEXT,
                                                    URL TEXT
                                                    )''')

        db.close()

    def query_db(self, query, pattern=None):
        db = sqlite3.connect(DB_FILE)
        dbc = db.cursor()

        if pattern:
            dbc.execute(query, (pattern,))
        else:
            dbc.execute(query,)

        out = dbc.fetchone()
        db.close()
        return out

    def add_dbrow(self, query, quote, user=None, channel=None):
        db = sqlite3.connect(DB_FILE)
        dbc = db.cursor()
        dbc.execute(query, (quote, time.strftime('%H-%M-%S %d-%m-%Y'), user, channel))
        db.commit()
        db.close()

    def query_maxid(self, query):
        db = sqlite3.connect(DB_FILE)
        dbc = db.cursor()
        dbc.execute(query,)
        max_q = dbc.fetchone()
        db.close()
        return max_q[0]


if __name__ == "__main__":
    db_api().init_db()
    r = start_rtm()
    ws = websocket.WebSocketApp(r, on_message=on_message, on_error=on_error, on_close=on_close, on_open=on_open)
    ws.run_forever()
