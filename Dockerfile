FROM python:3.11

WORKDIR /usr/src/app
COPY Pipfile.lock ./

RUN pip install --no-cache-dir micropipenv
RUN micropipenv install

COPY twitter_discord_bot ./twitter_discord_bot
CMD ["python", "-m", "twitter_discord_bot"]
