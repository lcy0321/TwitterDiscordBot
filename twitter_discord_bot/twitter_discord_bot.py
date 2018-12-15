"""A bot that fetch tweets from Twitter and post to Discord"""
import logging
from configparser import ConfigParser
from threading import Event
from types import FrameType
from typing import Dict, List, Optional, Tuple

import tweepy

from .discord_api import DiscordPost
from .twitter_api import (TwitterUser, get_auth_handler,
                          get_twitter_user_timeline, get_twitter_users_infos)

# logging.getLogger('urllib3').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)    # pylint: disable=invalid-name
logger.setLevel(logging.INFO)
logging.basicConfig(format='%(asctime)s:%(levelname)-7s:%(message)s', datefmt='%Y-%m-%d %H:%M:%S')

receive_stop = Event()    # pylint: disable=invalid-name


def get_twitter_user_names(filename: str) -> List[str]:
    """Read Twitter user names that need to fetch from the file"""
    with open(filename) as user_name_file:
        return list(filter(None, [user_name.strip() for user_name in user_name_file]))


def get_secrets(filename: str) -> Tuple[Tuple[str, str, str, str], str]:
    """Read secrets from the file"""
    config_parser = ConfigParser()

    with open(filename) as secret_config_file:
        config_parser.read_file(secret_config_file)

    consumer_key = config_parser['Twitter']['ConsumerKey']
    consumer_secret = config_parser['Twitter']['ConsumerSecret']
    access_token = config_parser['Twitter']['AccessToken']
    access_token_secret = config_parser['Twitter']['AccessTokenSecret']

    webhook_url = config_parser['Discord']['BotWebHookUrl']

    return (consumer_key, consumer_secret, access_token, access_token_secret), webhook_url


def post_tweets_to_discord(
        user: TwitterUser, statuses: List[tweepy.Status], webhook_url: str
) -> None:
    """Post the statuses to the Discord channel with the webhook"""
    for status in reversed(statuses):
        post = DiscordPost.generate_from_twitter_status(user=user, status=status)
        response_code = post.save(webhook_url=webhook_url)

        if response_code in [200, 201, 204]:
            logger.info('Successfully post twitter id %d to the Discord channel.', status.id)
        else:
            logger.error(
                'Failed to post twitter id %d to the Discord channel. Code: %d',
                status.id, response_code
            )


def fetch_and_post(
        twitter_api: tweepy.API, discord_webhook_url: str,
        twitter_user_names: List[str], last_fetched_ids: Dict[str, int],
) -> Dict[str, int]:
    """
    Fetch tweets and post them to the Discord channel.
    Return the ids of the lastest tweets.
    """

    # Get user information
    logger.debug('Fetching user information...')
    twitter_users_infos = get_twitter_users_infos(
        api=twitter_api, twitter_user_names=twitter_user_names
    )

    latest_ids = last_fetched_ids.copy()

    # Fetching timeline
    for user in twitter_users_infos.values():
        logger.debug('Fetching timeline from %s...', user.screen_name)

        try:
            since_id = last_fetched_ids[user.screen_name]
        except KeyError:
            since_id = -1

        statuses = get_twitter_user_timeline(api=twitter_api, user=user, since_id=since_id)

        logger.debug('Found %d new tweet(s).', len(statuses))

        if statuses:
            post_tweets_to_discord(user=user, statuses=statuses, webhook_url=discord_webhook_url)
            latest_ids[user.screen_name] = statuses[0].id

    return latest_ids


def read_last_fetched_ids_from_file(filename: str) -> Dict[str, int]:
    """Read the id of tweets that have fetched last time from the file"""

    config_parser = ConfigParser()

    try:
        with open(filename) as last_id_file:
            config_parser.read_file(last_id_file)
    except OSError:
        return {}

    return {
        screen_name: int(tweet_id)
        for screen_name, tweet_id in config_parser.items(section='LastID')
    }


def save_last_fetched_ids_to_file(filename: str, last_fetched_ids: Dict[str, int]) -> None:
    """Read the id of tweets that have fetched last time from the file"""

    config_parser = ConfigParser()

    if not config_parser.has_section('LastID'):
        config_parser.add_section('LastID')

    for screen_name, last_id in last_fetched_ids.items():
        config_parser['LastID'][screen_name] = str(last_id)

    with open(filename, 'w') as last_id_file:
        config_parser.write(last_id_file)


def main() -> None:
    """main function"""

    def _quit(signo: int, _frame: Optional[FrameType]) -> None:
        print(f'Receive {Signals(signo).name}, quit.')
        receive_stop.set()

    from signal import signal, SIGTERM, SIGINT, Signals     # pylint: disable=no-name-in-module
    signal(SIGTERM, _quit)
    signal(SIGINT, _quit)

    user_name_filename = 'twitter_users.txt'
    secret_filename = 'secret.ini'
    last_fetched_ids_filename = 'last_id.ini'

    twitter_user_names = get_twitter_user_names(user_name_filename)
    twitter_tokens, discord_webhook_url = get_secrets(filename=secret_filename)
    api = tweepy.API(auth_handler=get_auth_handler(*twitter_tokens))

    # Get the last ids that have fecthed
    last_fetched_ids = read_last_fetched_ids_from_file(filename=last_fetched_ids_filename)

    logger.info('Start to fetch tweets.')

    while not receive_stop.is_set():
        try:
            last_fetched_ids = fetch_and_post(
                twitter_api=api,
                discord_webhook_url=discord_webhook_url,
                twitter_user_names=twitter_user_names,
                last_fetched_ids=last_fetched_ids,
            )
        except Exception as exception:
            logger.error('Failed to fetch tweets.')
            logger.error(str(exception))
            receive_stop.wait(600)
        else:
            save_last_fetched_ids_to_file(last_fetched_ids_filename, last_fetched_ids)
            receive_stop.wait(60)


if __name__ == '__main__':
    main()
