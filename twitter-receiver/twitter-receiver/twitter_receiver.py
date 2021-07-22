"""Helping functions that related to Twitter API"""

from __future__ import annotations

import logging
import re
import time
from configparser import ConfigParser
from dataclasses import asdict, dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

import tweepy
import zmq
from ruamel.yaml import YAML

from .configs import TWITTER_ACCOUNTS_PATH, LAST_FETECHED_TWEETS_PATH

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_MS = 2000
RESTART_INTERVAL_SEC = 5


@dataclass
class TwitterMessageRequest:
    """A message request received from ZeroMQ."""

    source_id: str
    source_type: str
    username: str
    avatar_url: str
    content: str = ''
    embeds: Optional[List[Dict[str, Any]]] = None

    class _HasVideoException(Exception):
        pass

    @classmethod
    def _get_medias_from_twitter_status(
            cls,
            status: tweepy.Status
    ) -> Optional[List[Dict[str, Dict[str, str]]]]:
        try:
            media_entities = status.extended_entities['media']
        except AttributeError:
            return None

        medias = []
        for media in media_entities:
            if media['type'] == 'video':
                raise cls._HasVideoException

            medias.append({'image': {'url': media['media_url_https']}})
        return medias

    @classmethod
    def generate_from_twitter_status(
            cls,
            user: TwitterUser,
            status: tweepy.Status
    ) -> TwitterMessageRequest:
        """Generate TwitterMessageRequest from a TwitterUser and a tweepy.Status"""

        # Whether the tweet is a retweet
        is_retweet = hasattr(status, 'retweeted_status')

        # Discord api does not accept videos in the embeds
        if not is_retweet:
            try:
                embeds = cls._get_medias_from_twitter_status(status=status)
            except cls._HasVideoException:
                has_video = True
            else:
                has_video = False

        if is_retweet or has_video:
            embeds = None
            content = f'http://twitter.com/{user.screen_name}/status/{status.id}'

        else:
            try:
                text = status.full_text
            except AttributeError:
                text = status.text

            contents: List[str] = []

            contents.append(f'<http://twitter.com/{user.screen_name}/status/{status.id}>')
            contents.append(text)

            content = '\n'.join(contents)

        message_request = cls(
            source_id=user.screen_name.lower(),
            source_type='twitter',
            username=user.name,
            avatar_url=user.profile_image_url,
            content=content,
            embeds=embeds,
        )

        return message_request

    def as_dict(self) -> Dict:
        """Wrapper of dataclasses.asdict()."""
        return asdict(self)


@dataclass(init=False)
class TwitterUser():
    """Contains the infomation of a Twitter user."""

    name: str
    screen_name: str
    user_id: int
    profile_image_url: str

    def __init__(
            self,
            name: str,
            screen_name: str,
            user_id: int,
            profile_image_url: str,
    ) -> None:
        self.name = name
        self.screen_name = screen_name
        self.user_id = user_id
        self.profile_image_url = re.sub(r'_normal(\..+)$', R'\1', profile_image_url)

    @classmethod
    def get_from_twitter_api(cls, api: tweepy.API, screen_name: str) -> 'TwitterUser':
        """Construct TwitterUser with tweepy.API."""

        user_info = api.get_user(screen_name)

        user = cls(
            name=user_info.name,
            screen_name=user_info.screen_name,
            user_id=user_info.id,
            profile_image_url=user_info.profile_image_url_https,
        )
        return user


def get_twitter_secrets(path: str) -> Tuple[str, str, str, str]:
    """Read Twitter secrets from the file."""
    config_parser = ConfigParser()

    with open(path) as secret_config_file:
        config_parser.read_file(secret_config_file)

    consumer_key = config_parser['Twitter']['ConsumerKey']
    consumer_secret = config_parser['Twitter']['ConsumerSecret']
    access_token = config_parser['Twitter']['AccessToken']
    access_token_secret = config_parser['Twitter']['AccessTokenSecret']

    return (consumer_key, consumer_secret, access_token, access_token_secret)


def get_twitter_users_infos(
        api: tweepy.API,
        twitter_accounts: List[str],
) -> Dict[str, TwitterUser]:
    """Get user objects from Twitter."""

    twitter_users_infos: Dict[str, TwitterUser] = {}

    for twitter_account in twitter_accounts:
        twitter_user = TwitterUser.get_from_twitter_api(api=api, screen_name=twitter_account)
        twitter_users_infos[twitter_account] = twitter_user

    return twitter_users_infos


def get_twitter_user_timeline(
        api: tweepy.API,
        user: TwitterUser,
        since_id: str = None,
) -> List[tweepy.Status]:
    """Get statuses of the specific user from Twitter."""

    if not since_id:
        logging.info(
            f'Doesn\'t found the information of last tweet of {user.screen_name}, '
            'fetch latest 10 tweets...'
        )

        statuses = api.user_timeline(
            user.user_id,
            tweet_mode='extended',
            trim_user=True,
            count=10
        )
    else:
        logging.debug('Fetching tweets since id: %s', since_id)

        statuses = api.user_timeline(
            user.user_id,
            tweet_mode='extended',
            rim_user=True,
            since_id=since_id
        )

    return statuses


def get_twitter_accounts(path: str) -> List[str]:
    with open(path) as twitter_accounts_file:
        return YAML().load(twitter_accounts_file)


def get_auth_handler(
        consumer_key: str,
        consumer_secret: str,
        access_token: str,
        access_token_secret: str
) -> tweepy.OAuthHandler:
    """Generate OAuthHandler with given tokens."""

    auth_handler = tweepy.OAuthHandler(
        consumer_key=consumer_key,
        consumer_secret=consumer_secret
    )
    auth_handler.set_access_token(key=access_token, secret=access_token_secret)
    return auth_handler


class ZMQReqClient:
    """A ZeroMQ REQ client wrapper that implements Lazy Pirate Pattern.

    Reference: https://zguide.zeromq.org/docs/chapter4/#Client-Side-Reliability-Lazy-Pirate-Pattern

    """

    def __init__(self, addr) -> None:
        self.addr = addr
        self.zmq_client = None

    def connect(self):
        """Initialize the ZeroMQ socket and connect to the server."""
        self.zmq_client = zmq.Context().socket(zmq.REQ)
        self.zmq_client.connect(self.addr)
        logger.info(f'Connected to {self.addr}')

    def close(self):
        """Close and cleanup the ZeroMQ socket."""
        self.zmq_client.close(linger=0)

    def _lazy_pirate_pattern_send(
        self,
        send_func: Callable[[], None],
    ):
        send_func()

        while True:
            if (self.zmq_client.poll(REQUEST_TIMEOUT_MS) & zmq.POLLIN) == 0:
                logging.warning('Failed to receive the ACK from the server. Retrying...')
                self.zmq_client.close(linger=0)
                time.sleep(RESTART_INTERVAL_SEC)

                # Re-send the message
                self.close()
                self.connect()
                send_func()
                continue

            self.zmq_client.recv()
            break

    def send_json(self, obj, flags=0, **kwargs):
        """Wrapper for zmq.Socket.send_json()."""

        def _send_func():
            self.zmq_client.send_json(
                obj=obj,
                flags=flags,
                **kwargs,
            )
        self._lazy_pirate_pattern_send(_send_func)


def read_last_fetched_tweets_from_file(path: str) -> Dict[str, str]:
    """Read the id of tweets that have fetched last time from the file."""

    try:
        with open(path) as last_tweets_file:
            last_fetched_tweets: Dict[str, str] = YAML().load(last_tweets_file)
    except OSError:
        return {}

    return {
        screen_name.casefold(): tweet_id
        for screen_name, tweet_id in last_fetched_tweets.items()
    }


def save_last_fetched_ids_to_file(path: str, last_fetched_tweets: Dict[str, str]) -> None:
    """Read the id of tweets that have fetched last time from the file"""

    with open(path, mode='w') as last_tweets_file:
        YAML().dump(
            {
                screen_name.casefold(): tweet_id
                for screen_name, tweet_id in last_fetched_tweets.items()
            },
            last_tweets_file
        )


def main():

    addr = 'tcp://127.0.0.1:5555'

    client = ZMQReqClient(addr)
    client.connect()

    twitter_tokens = get_twitter_secrets(path='./configs/twitter_secrets.ini')
    twitter_api = tweepy.API(auth_handler=get_auth_handler(*twitter_tokens))

    last_fetched_tweets = read_last_fetched_tweets_from_file(LAST_FETECHED_TWEETS_PATH)

    for twitter_account in get_twitter_accounts(TWITTER_ACCOUNTS_PATH):

        twitter_user = TwitterUser.get_from_twitter_api(
            api=twitter_api,
            screen_name=twitter_account,
        )

        logger.debug('Fetching timeline from %s...', twitter_user.screen_name)

        statuses = get_twitter_user_timeline(
            api=twitter_api,
            user=twitter_user,
            since_id=last_fetched_tweets.get(twitter_account.casefold())
        )

        logger.debug('Found %d new tweet(s).', len(statuses))

        for status in reversed(statuses):

            request = TwitterMessageRequest.generate_from_twitter_status(
                user=twitter_user,
                status=status,
            )

            logger.info(f'Sending tweet message {twitter_account}: {status.id_str} to ZeroMQ...')

            client.send_json(request.as_dict())

            last_fetched_tweets[twitter_account] = status.id_str

    save_last_fetched_ids_to_file(LAST_FETECHED_TWEETS_PATH, last_fetched_tweets)
