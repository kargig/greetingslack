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

###############################################################

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
    if msg['type'] == 'message' and msg['text'] == '!welcome':
        return True
    else:
        return False

def parse_join(message):
    m = json.loads(message)
    if is_team_join(m) or is_debug_channel_join(m) or welcome_me(m):
        user_id = m["user"]["id"] if is_team_join(m) else m["user"]
        logging.debug(m)
        getdata= {
                'token': TOKEN,
                'user': user_id
                }
        userdata = requests.get("https://slack.com/api/im.open", params=getdata)
        userdata = userdata.json()
        logging.debug(userdata)
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
        logging.debug(data)
        send_message = requests.post("https://slack.com/api/chat.postMessage", data=data)
        logging.debug(send_message)
        logging.debug('HELLO SENT: ' + user_id)


#Connects to Slacks and initiates socket handshake
def start_rtm():
    r = requests.get("https://slack.com/api/rtm.start?token="+TOKEN)
    r = r.json()
    logging.debug(r)
    r = r["url"]
    return r

def on_message(ws, message):
    parse_join(message)

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


if __name__ == "__main__":
    r = start_rtm()
    ws = websocket.WebSocketApp(r, on_message = on_message, on_error = on_error, on_close = on_close, on_open = on_open)
    ws.run_forever()

