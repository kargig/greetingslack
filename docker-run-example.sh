#!/usr/bin/env bash
# This file is just an example (works with bash/zsh), 
# please change accordingly to meet your requirements and shell preference

# This helps keeping files outside of your repo when testing 
export WORKDIR=/home/user/greetbot_storage

# touch required files (otherwise docker will create them as directories)
touch $WORKDIR/bot.log
touch $WORKDIR/greetingbot.sqlite3

# -v for any volume mount (only files used below)
# Check the envfile.example to see what --env-file is needed for 
# or use other environment variable passing alternatives
docker run -d --rm -it \
	--env-file $WORKDIR/envfile \
	-e TZ='Europe/Athens' \
	-v $WORKDIR/bot.log:/backup/greetingslack/bot.log \
	-v $WORKDIR/greetingbot.sqlite3:/backup/greetingslack/greetingbot.sqlite3 \
	--name greetingbot \
    greetingbot-slim