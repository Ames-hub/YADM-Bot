# Installation
This bot has two components, the WebUI, and the bot program itself.

To install the bot alone, see "Installing the bot"<br>
To install the WebUI alone, see "Installing the WebUI"<br>
To install both, see the section "Installing Both."

## Installing the bot
There are two easy-ish ways to install the bot.
The recommended method is using Docker, which is the one that will be outlined here.

The second method is copying the repository, and running it on an actual machine and not in a container. This is simple enough, I won't describe how to do it here. Just google any video for "How to run python program."

### Docker
1. Clone the repository with 
```
git clone https://github.com/Ames-hub/YADM-bot
```
2. Download python3.13-bookworm image for docker with:
```
docker pull python:3.13-bookworm
```
3. Create a docker network named "nodeus-network", using the command: 
```
docker network create nodeus-network
```
4. Create a docker container named "nodeus-bot" with python3.13-bookworm image, which is connected to the network "nodeus-network" with the restart-policy set to "--unless-stopped", with -v being set to nodeus-bot-data/app. Have it run /app/bot.py on start.
```
docker run -d \
  --name nodeus-bot \
  --network nodeus-network \
  --restart unless-stopped \
  -v nodeus-bot-data:/app \
  python:3.13-bookworm \
  python /app/bot.py
```
5. Copy the cloned repo files to this docker container, in the "/app" directory.
```
docker cp ./YADM-bot/. nodeus-bot:/app
```
6. Go to `discord.com/developers/applications`, find your bot, and get the bot token.
7. In the "installation page" set it to guild install with no user install, and enable the scope "bot" and "application commands." Then for permissions, and pick "Administrator." In the "Bot" tab, go to "Privileged Gateway Intents" and enable "Server Member Intent" and "Message Content Intent"
8. Open a terminal, and run a command in the docker container. The command is:
```
cd app
pip install -r requirements.txt
```

If you want to install the WebUI too, you will want to follow the steps in "Installing the WebUI" from here on out.

## Installing the WebUI
1. Clone the repository with 
```
git clone https://github.com/Ames-hub/YADM-bot
```
2. Download python3.13-bookworm image for docker with:
```
docker pull python:3.13-bookworm
```
3. If you have not already done this in installing the bot, create a docker network named "nodeus-network", using the command: 
```
docker network create nodeus-network
```
4. Create a docker container named "nodeus-webui" with python3.13-bookworm image, which is connected to the network "nodeus-network" with the restart-policy set to "--unless-stopped", with -v being set to nodeus-webui-data/app. Have it run /app/webui.py on start.
```
docker run -d \
  --name nodeus-webui \
  --network nodeus-network \
  --restart unless-stopped \
  -v nodeus-webui-data:/app \
  -p 8040:8040 \
  python:3.13-bookworm \
  python /app/webui.py
```
5. Copy the cloned repo files to this docker container, in the "/app" directory.
```
docker cp ./YADM-bot/. nodeus-webui:/app
```
6. Open a terminal, and run a command in the docker container. The command is:
```
cd app
pip install -r requirements.txt
```

From here, you will want to follow the steps in "Installing both" to wire the WebUI up to the Bot. 

## Installing Both
In this section, we'll be hooking up the two docker containers for the WebUI and the Bot. 

1. First step is to create a docker container for Postgres, using the name "nodeus-pg", the network we made earlier "nodeus-network", with its restart policy set to "unless-stopped" and with some PG Login details.<br><br>
Be sure to replace "ENTER_A_PASSWORD_HERE" with your own custom password, and note it down somewhere.
```
docker run -d \
  --name nodeus-pg \
  --network nodeus-network \
  --restart unless-stopped \
  -e POSTGRES_USER=nodeus \
  -e POSTGRES_PASSWORD=ENTER_A_PASSWORD_HERE \
  -e POSTGRES_DB=nodeus \
  -v nodeus-pg-data:/var/lib/postgresql/data \
  postgres:latest
```
2. Verify that the Postgres container is running, if it is not, figure out why and get it running. (If Postgres is too problematic, you can always try other databases. Postgres is just the one I recommend.)
3. Open a terminal, and run a command in the docker container named "nodeus-bot". The command is:
```
cd app
python bot.py --setup-db
```
4. Enter the details that the prompt asks you for. Eg, host would be "nodeus-network", the port "8040". The DB Name and DB Username would be "Nodeus"
5. Then run this command in the same window:
```
python bot.py --enable-webui-cmds
```
6. Provide the host name for your webui (that is, your servers IP and Port. So, 'http://192.168.1.123:8040' for example.)
7. In the same terminal (or another, doesn't matter.) run a command in the docker container named "nodeus-webui". The command is:
```
cd app
python webui.py --setup-db
```
8. Enter the details that the prompt asks you for. Eg, host would be "nodeus-network", the port "8040". The DB Name and DB Username would be "Nodeus"

Once you've confirmed that both docker containers are reading and writing to the database, the full project will have been successfully configured.