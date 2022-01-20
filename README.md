# Greetings Slackers

This simple script written in basic Python will allow you to hook into the real time API of Slack and perform a direct message greeting to every new joiner! It can also send a message about the Code of Conduct of your community, store and retrieve quotes as well as store URLs shared in the channels that the bot is invited to.

This is a fork of <https://github.com/orliesaurus/greetingslack>

## Requirements

Python 3.7+

## Installation

```bash
git clone <thisgitrepo>
cd <thisgitrepo>
virtualenv greetingslack
. greetingslack/bin/activate
pip3 install -r requirements.txt
python bot.py &
```

## Q&A

### Q1. How do you change the welcome message?

A1.
To change the welcome message, expose `WELCOME_MESSAGE` or WELCOME_FILE env
variable

### Q2. How to store a quote

A2.
Use `!add quote goes here`

### Q3. How to get a random quote

A3.
Use `!quote`

### Q4. How to get a quote containing a keyword (foobar)

A4.
Use `!quote foobar`

### Q5. How to get a specific quote id (123)

A5.
Use `!quote id:123`
