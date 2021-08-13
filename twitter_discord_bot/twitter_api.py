"""Helping functions that related to Twitter API"""

import logging
import re
from dataclasses import dataclass
from typing import Dict, List

import tweepy

from .models import TwitterAccount


@dataclass(init=False)
class TwitterUser():
    """Contains the infomation of a Twitter user"""

    name: str
    screen_name: str
    user_id: int
    profile_image_url: str

    def __init__(
            self, name: str, screen_name: str, user_id: int, profile_image_url: str,
    ) -> None:
        self.name = name
        self.screen_name = screen_name
        self.user_id = user_id
        self.profile_image_url = re.sub(r'_normal(\..+)$', R'\1', profile_image_url)

    @staticmethod
    def get_from_twitter_api(api: tweepy.API, screen_name: str) -> 'TwitterUser':
        """Construct TwitterUser with tweepy.API"""

        user_info = api.get_user(screen_name)

        user = TwitterUser(
            name=user_info.name, screen_name=user_info.screen_name,
            user_id=user_info.id, profile_image_url=user_info.profile_image_url_https,
        )
        return user


def get_twitter_users_infos(
        api: tweepy.API,
        twitter_accounts: List[TwitterAccount],
) -> Dict[str, TwitterUser]:
    """Get user objects from Twitter"""

    twitter_users_infos: Dict[str, TwitterUser] = {}

    for twitter_account in twitter_accounts:
        screen_name = twitter_account.twitter
        twitter_user = TwitterUser.get_from_twitter_api(api=api, screen_name=screen_name)
        twitter_users_infos[screen_name] = twitter_user

    return twitter_users_infos


def get_twitter_user_timeline(
        api: tweepy.API, user: TwitterUser, since_id: int = -1,
) -> List[tweepy.Status]:
    """Get statuses of the specific user from Twitter"""

    if since_id == -1:
        logging.info('Doesn\'t found the information of last ids, fetch lastest 10 tweets...')

        statuses = api.user_timeline(
            user.user_id,
            tweet_mode='extended',
            trim_user=True,
            count=10,
            exclude_replies=True,
        )
    else:
        logging.debug('Fetching tweets since id: %s', since_id)

        statuses = api.user_timeline(
            user.user_id,
            tweet_mode='extended',
            trim_user=True,
            since_id=since_id,
            exclude_replies=True,
        )

    return statuses


def get_auth_handler(
        consumer_key: str, consumer_secret: str, access_token: str, access_token_secret: str
) -> tweepy.OAuthHandler:
    """Generate OAuthHandler with given tokens"""

    auth_handler = tweepy.OAuthHandler(
        consumer_key=consumer_key, consumer_secret=consumer_secret
    )
    auth_handler.set_access_token(key=access_token, secret=access_token_secret)
    return auth_handler
