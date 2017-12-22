#!/usr/bin/env python
# -*- coding: utf-8 -*-
import codecs
import logging
import websocket
import json
import requests
import urllib
import os
import sys
import sqlite3
import time
import re

logging.basicConfig(filename='bot.log', level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

WELCOME_FILE='/path/to/WELCOME_MESSAGE.txt'

# Suppress InsecureRequestWarning
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

###VARIABLES THAT YOU NEED TO SET MANUALLY IF NOT ON HEROKU#####
# Handle each one seperately
try:
        TOKEN = os.environ['SLACK_TOKEN']
except:
        TOKEN = 'Manually set the API Token if youre not running through heroku or have not set vars in ENV'

try:
        UNFURL = os.environ['UNFURL_LINKS']
except:
        UNFURL = 'FALSE'

try:
        DEBUG_CHANNEL_ID = os.environ['DEBUG_CHANNEL_ID']
except:
        DEBUG_CHANNEL_ID = 'Manually set the Channel if youre not running through heroku or have not set vars in ENV'

try:
        DB_FILE = os.environ['DB_FILE']
except:
        DB_FILE = 'FALSE'

###############################################################

def unescape(s):
    s = s.replace("&lt;", "<")
    s = s.replace("&gt;", ">")
    # this has to be last:
    s = s.replace("&amp;", "&")
    return s

def welcome_message():
    try:
        message = os.environ['WELCOME-MESSAGE']
    except:
        with codecs.open(WELCOME_FILE,'r',encoding='utf8') as f:
            message = f.read()
    return message

def is_team_join(msg):
    return msg['type'] == "team_join"

def is_debug_channel_join(msg):
    if (msg['type'] == "member_joined_channel" and msg['channel'] == DEBUG_CHANNEL_ID):
        return True
    else:
        return False

def welcome_me(msg):
    if msg['type'] == 'message' and 'text' in msg.keys():
        if msg['text'] == '!welcome':
            return True
        else:
            return False
    else:
        return False

def is_message(msg):
    if msg['type'] == 'message':
        return True
    else:
        return False


def show_quote(msg):
    if msg['type'] == 'message' and msg['text'] == '!quote':
        return True
    else:
        return False

def add_quote(msg):
    if msg['type'] == 'message' and msg['text'] == '!add':
        return True
    else:
        return False

def parse_message(message):
    m = json.loads(message)
    #logging.debug(m)
    if is_team_join(m) or is_debug_channel_join(m) or welcome_me(m):
        user_id = m["user"]["id"] if is_team_join(m) else m["user"]
        getdata= {
                'token': TOKEN,
                'user': user_id
                }
        userdata = requests.get("https://slack.com/api/im.open", params=getdata)
        userdata = userdata.json()
        #logging.debug(userdata)
        dmchannel = userdata["channel"]["id"]
        data = {
                'token': TOKEN,
                'channel': dmchannel,
                'text': welcome_message(),
                'parse': 'full',
                'as_user': 'true',
        }
        if (UNFURL.lower() == "false"):
          data['unfurl_link']='false'
        #logging.debug(data)
        send_message = requests.post("https://slack.com/api/chat.postMessage", data=data)
        #logging.debug(send_message)
        logging.debug('HELLO SENT: ' + user_id)
    elif is_message(m) and 'text' in m.keys():
        ret = None
        #logging.debug(m)
        if m['text'][0] != '!':
            return
        try:
            cmd, args = m['text'].split(' ', 1)
        except ValueError:
            cmd = m['text']
            args = ''
        udata= {
                'token': TOKEN,
                'user': m['user']
                }
        userdata = requests.get("https://slack.com/api/users.info", params=udata)
        userdata = userdata.json()
        logging.debug(userdata)
        cdata= {
                'token': TOKEN,
                'channel': m['channel']
                }
        channeldata = requests.get("https://slack.com/api/channels.info", params=cdata)
        channeldata = channeldata.json()
        logging.debug(channeldata)
        f_args = [userdata['user']['profile']['display_name'], channeldata['channel']['name'], m['text']]
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
            logging.debug(send_message)

#Connects to Slacks and initiates socket handshake
def start_rtm():
    r = requests.get("https://slack.com/api/rtm.start?token="+TOKEN)
    r = r.json()
    #logging.debug(r)
    r = r["url"]
    return r

def on_message(ws, message):
    parse_message(message)

def on_error(ws, error):
    try:
		logger = logging.getLogger()
		logger.error("SOME ERROR HAS HAPPENED: " + error)
    except:
        print 'Interrupted'
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

        #logging.debug(out)
        if out and (len(out) >= 2):
            quote_id = out[0] # id
            quote_text = out[1] # quote

        quote_time = ''
        quote_user = ''
        if out and (len(out) == 4):
            quote_user = out[2] # user
            quote_time = out[3] # time
            quote_time = quote_time.replace('-', ':', 2)

        if quote_text:
            quote_text = unescape(quote_text)
            final_text = '[' + 'ID:' + str(quote_id) + ' by:' + quote_user + ' at:' + quote_time + '] ' + quote_text

        return final_text


    def addtodb(self, user, channel, msg):
        ret = None
        dba = db_api()
        db = sqlite3.connect(DB_FILE)
        dbc = db.cursor()
        quote = ' ' . join(msg.split(' ')[1:])
        query = '''INSERT INTO quotes_fts (QUOTE) VALUES (?)'''
        dbc.execute(query,(quote,))
        query = '''INSERT INTO quotes (QUOTE_DT, ADDED_BY, CHANNEL) VALUES (?, ?, ?)'''
        dbc.execute(query, (time.strftime('%H-%M-%S %d-%m-%Y'), user, channel))
        db.commit()
        db.close()

        #No intention of deleting, ever...
        query = '''SELECT MAX(rowid) FROM quotes'''
        max_q = dba.query_maxid(query)
        ret = 'Quote ' + str(max_q) + ' added!'
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

        db.close()


    def query_db(self, query, pattern = None):
        db = sqlite3.connect(DB_FILE)
        dbc = db.cursor()

        if pattern:
            dbc.execute(query, (pattern,))
        else:
            dbc.execute(query,)

        out = dbc.fetchone()
        db.close()
        return out


    def add_dbrow(self, query, quote, user = None, channel = None):
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
    ws = websocket.WebSocketApp(r, on_message = on_message, on_error = on_error, on_close = on_close, on_open = on_open)
    ws.run_forever()

