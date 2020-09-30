FROM python:3.8.6

WORKDIR /usr/src/app
COPY Pipfile Pipfile.lock ./
COPY twitter_discord_bot ./twitter_discord_bot

RUN pip install --no-cache-dir pipenv
RUN pipenv install --system

CMD ["python", "-m", "twitter_discord_bot"]
