# Docker
In case you need to run the bot from a docker container you may use the following commands.

## build
You can build the docker container using the following:
```sh
docker build -f Dockerfile.slim-buster -t greetingbot-slim . 
```
_(A prebuild image will be available in the future.)_

## run
In order to run the container you may use the `docker-run-example.sh` which look like the following:

```sh
export WORKDIR=/home/user/greetbot_dir

docker run --rm -it \
	--env-file $WORKDIR/envfile \
	-e TZ='EET' \
	-v $WORKDIR/bot.log:/backup/greetingslack/bot.log \
	-v $WORKDIR/greetingbot.sqlite3:/backup/greetingslack/greetingbot.sqlite3 \
	--name greetingbot \
    greetingbot-slim
```
_Note: You need to set your `WORKDIR` or alter the volumes accordingly_  
_Note: environment variables required by the bot need to be in the `envfile`, or set like the TZ_