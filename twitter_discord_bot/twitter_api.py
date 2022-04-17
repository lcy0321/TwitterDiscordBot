"""Helping functions that related to Twitter API"""

from __future__ import annotations

import logging
import re
from typing import Dict, List

import tweepy
import tweepy.models

from .models import TwitterAccount

logger = logging.getLogger(__name__)    # pylint: disable=invalid-name


class TwitterUserWrapper():
    """
    Contains the infomation of a Twitter user

    Fetch the information from Twitter only when needed (lazy loading).
    """

    screen_name: str

    _api: tweepy.API
    _has_initalize: bool = False

    _name: str
    _user_id: int
    _profile_image_url: str

    def __init__(
            self,
            api: tweepy.API,
            screen_name: str
    ) -> None:
        self._api = api
        self.screen_name = screen_name

    @staticmethod
    def _contruct_for_testing(
        name: str,
        screen_name: str,
        user_id: int,
        profile_image_url: str,
    ) -> TwitterUserWrapper:
        """Initialize the objects directly by the given values, onlt for testing."""

        obj = TwitterUserWrapper(None, screen_name)
        obj._name = name
        obj._user_id = user_id
        obj._profile_image_url = profile_image_url

        obj._has_initalize = True

        return obj

    def _sync_with_twitter_api(self) -> None:
        """Fetch the information via Twitter API"""

        logger.debug(f'Fetching user info of {self.screen_name}...')
        user_info = self._api.get_user(screen_name=self.screen_name)

        self._name = user_info.name
        self._user_id = user_info.id
        self._profile_image_url = re.sub(
            r'_normal(\..+)$',
            R'\1',
            user_info.profile_image_url_https,
        )

        self._has_initalize = True

    def _init_if_needed(self) -> None:
        if not self._has_initalize:
            self._sync_with_twitter_api()

    @property
    def name(self) -> str:
        self._init_if_needed()
        return self._name

    @property
    def user_id(self) -> int:
        self._init_if_needed()
        return self._user_id

    @property
    def profile_image_url(self) -> str:
        self._init_if_needed()
        return self._profile_image_url


def get_twitter_users_infos(
        api: tweepy.API,
        twitter_accounts: List[TwitterAccount],
) -> Dict[str, TwitterUserWrapper]:
    """Get user objects from Twitter"""

    twitter_users_infos: Dict[str, TwitterUserWrapper] = {}

    for twitter_account in twitter_accounts:
        screen_name = twitter_account.twitter
        twitter_user = TwitterUserWrapper(api=api, screen_name=screen_name)
        twitter_users_infos[screen_name] = twitter_user

    return twitter_users_infos


def get_twitter_user_timeline(
        api: tweepy.API,
        user: TwitterUserWrapper,
        since_id: int = -1,
) -> List[tweepy.models.Status]:
    """Get statuses of the specific user from Twitter"""

    if since_id == -1:
        logger.info('Doesn\'t found the information of last ids, fetch lastest 10 tweets...')

        statuses = api.user_timeline(
            screen_name=user.screen_name,
            tweet_mode='extended',
            trim_user=True,
            count=10,
            exclude_replies=True,
        )
    else:
        logger.debug('Fetching tweets since id: %s', since_id)

        statuses = api.user_timeline(
            screen_name=user.screen_name,
            tweet_mode='extended',
            trim_user=True,
            since_id=since_id,
            exclude_replies=True,
        )

    return statuses


def get_auth_handler(
        consumer_key: str,
        consumer_secret: str,
        access_token: str,
        access_token_secret: str
) -> tweepy.OAuth1UserHandler:
    """Generate OAuthHandler with given tokens"""

    auth_handler = tweepy.OAuth1UserHandler(
        consumer_key=consumer_key,
        consumer_secret=consumer_secret
    )
    auth_handler.set_access_token(key=access_token, secret=access_token_secret)
    return auth_handler
