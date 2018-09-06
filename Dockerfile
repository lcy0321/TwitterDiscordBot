FROM python:3.7.0
WORKDIR /usr/src/app
COPY *.ini Pipfile Pipfile.lock ./
COPY twitter_discord_bot ./twitter_discord_bot
RUN pip install --no-cache-dir pipenv
RUN pipenv install --system
CMD ["python", "twitter_discord_bot/twitter_discord_bot.py"]
