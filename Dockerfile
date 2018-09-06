FROM python:3.7.0
WORKDIR /usr/src/app
COPY secret.ini twitter_discord_bot Pipfile Pipfile.lock ./
RUN pip install --no-cache-dir pipenv
RUN pipenv install --system
CMD ["python", "twitter_discord_bot/twitter_discord_bot.py"]
