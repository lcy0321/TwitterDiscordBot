"""A bot that fetch tweets from Twitter and post to Discord"""
import logging
from configparser import ConfigParser
from signal import SIGINT, SIGTERM, Signals, signal
from threading import Event
from types import FrameType
from typing import Dict, List, Mapping, Optional, Tuple

import tweepy
from ruamel.yaml import YAML

from .configs import (DISCORD_WEBHOOKS_PATH, LAST_FETECHED_POSTS_PATH,
                      TWITTER_ACCOUNTS_PATH, TWITTER_SECRETS_PATH)
from .discord_api import DiscordPost
from .models import TwitterAccount
from .twitter_api import (TwitterUserWrapper, get_auth_handler,
                          get_twitter_user_timeline, get_twitter_users_infos)

# logging.getLogger('urllib3').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)    # pylint: disable=invalid-name
logger.setLevel(logging.DEBUG)
logging.basicConfig(format='%(asctime)s:%(levelname)-7s:%(message)s', datefmt='%Y-%m-%d %H:%M:%S')


def get_twitter_accounts(path: str) -> List[TwitterAccount]:
    """Read Twitter user names that need to fetch from the file"""
    yaml = YAML()
    with open(path) as twitter_accounts_flle:
        twitter_account_dicts = yaml.load(twitter_accounts_flle)

    return [
        TwitterAccount(**twitter_account_dict)
        for twitter_account_dict in twitter_account_dicts
    ]


def get_twitter_secrets(path: str) -> Tuple[str, str, str, str]:
    """Read Twitter secrets from the file"""
    config_parser = ConfigParser()

    with open(path) as secret_config_file:
        config_parser.read_file(secret_config_file)

    consumer_key = config_parser['Twitter']['ConsumerKey']
    consumer_secret = config_parser['Twitter']['ConsumerSecret']
    access_token = config_parser['Twitter']['AccessToken']
    access_token_secret = config_parser['Twitter']['AccessTokenSecret']

    return (consumer_key, consumer_secret, access_token, access_token_secret)


def get_discord_webhooks(path: str) -> Dict[str, str]:
    """Read Discord webhook urls from the file"""
    config_parser = ConfigParser()

    with open(path) as webhooks_file:
        config_parser.read_file(webhooks_file)

    return dict(config_parser['Webhooks'])


def post_tweets_to_discord(
        user: TwitterUserWrapper,
        statuses: List[tweepy.models.Status],
        webhook_url: str,
) -> None:
    """Post the statuses to the Discord channel with the webhook"""
    for status in reversed(statuses):
        post = DiscordPost.generate_from_twitter_status(user=user, status=status)
        response_code = post.save(webhook_url=webhook_url)

        if response_code in [200, 201, 204]:
            logger.info(
                'Successfully post twitter id %d from %s to the Discord channel.',
                status.id,
                user.screen_name,
            )
        else:
            logger.error(
                'Failed to post twitter id %d from %s to the Discord channel. Code: %d',
                status.id,
                user.screen_name,
                response_code,
            )


def fetch_and_post(
        twitter_api: tweepy.API,
        twitter_accounts: List[TwitterAccount],
        discord_webhooks: Mapping[str, str],
        last_fetched_posts: Dict[str, int],
) -> Dict[str, int]:
    """
    Fetch tweets and post them to the Discord channel.
    Return the ids of the lastest tweets.
    """

    # Get user information
    logger.debug('Fetching user information...')
    twitter_users_infos = get_twitter_users_infos(
        api=twitter_api,
        twitter_accounts=twitter_accounts,
    )

    latest_posts = last_fetched_posts.copy()

    # Fetching timeline
    for twitter_account in twitter_accounts:

        if not twitter_account.discord_channels:
            logger.warning(
                f'{twitter_account.twitter} does\'t need to post to any Discord channel, ignore.',
            )
            continue

        twitter_name = twitter_account.twitter
        twitter_user = twitter_users_infos[twitter_name]

        logger.debug('Fetching timeline from %s...', twitter_name)

        try:
            since_id = last_fetched_posts[twitter_name.casefold()]
        except KeyError:
            since_id = -1

        statuses = get_twitter_user_timeline(
            api=twitter_api,
            user=twitter_user,
            since_id=since_id,
        )

        logger.debug('Found %d new tweet(s).', len(statuses))

        if statuses:
            for discord_channel in twitter_account.discord_channels:
                post_tweets_to_discord(
                    user=twitter_user,
                    statuses=statuses,
                    webhook_url=discord_webhooks[discord_channel],
                )
            latest_posts[twitter_name.casefold()] = statuses[0].id

    return latest_posts


def read_last_fetched_ids_from_file(filename: str) -> Dict[str, int]:
    """Read the id of tweets that have fetched last time from the file"""

    config_parser = ConfigParser()

    try:
        with open(filename) as last_id_file:
            config_parser.read_file(last_id_file)
    except OSError:
        return {}

    return {
        screen_name.casefold(): int(tweet_id)
        for screen_name, tweet_id in config_parser.items(section='LastID')
    }


def save_last_fetched_ids_to_file(filename: str, last_fetched_ids: Dict[str, int]) -> None:
    """Read the id of tweets that have fetched last time from the file"""

    config_parser = ConfigParser()

    if not config_parser.has_section('LastID'):
        config_parser.add_section('LastID')

    for screen_name, last_id in last_fetched_ids.items():
        config_parser['LastID'][screen_name.casefold()] = str(last_id)

    with open(filename, 'w') as last_id_file:
        config_parser.write(last_id_file)


def main() -> None:
    """main function"""

    receive_stop = Event()

    def _quit(signo: int, _frame: Optional[FrameType]) -> None:
        print(f'Receive {Signals(signo).name}, quit.')
        receive_stop.set()

    signal(SIGTERM, _quit)
    signal(SIGINT, _quit)

    twitter_accounts = get_twitter_accounts(path=TWITTER_ACCOUNTS_PATH)
    twitter_tokens = get_twitter_secrets(path=TWITTER_SECRETS_PATH)
    discord_webhooks = get_discord_webhooks(path=DISCORD_WEBHOOKS_PATH)
    api = tweepy.API(auth=get_auth_handler(*twitter_tokens))

    # Get the last ids that have fecthed
    last_fetched_posts = read_last_fetched_ids_from_file(filename=LAST_FETECHED_POSTS_PATH)

    logger.info('Start to fetch tweets.')

    while not receive_stop.is_set():
        try:
            last_fetched_posts = fetch_and_post(
                twitter_api=api,
                twitter_accounts=twitter_accounts,
                last_fetched_posts=last_fetched_posts,
                discord_webhooks=discord_webhooks,
            )
        except Exception:
            logger.exception('Failed to fetch tweets.')
            receive_stop.wait(600)
        else:
            save_last_fetched_ids_to_file(LAST_FETECHED_POSTS_PATH, last_fetched_posts)
            receive_stop.wait(30)


if __name__ == '__main__':
    main()
