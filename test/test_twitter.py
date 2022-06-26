"""Test"""
# pylint: disable=C

import logging
import unittest
from unittest.mock import NonCallableMagicMock

from twitter_discord_bot.twitter_api import (TwitterUserWrapper,
                                             get_twitter_user_timeline)

from .help import TWITTER_USER_SAMPLE

module_logger = logging.getLogger('twitter_discord_bot.twitter_api')
module_logger.setLevel(logging.CRITICAL)


class TestTwitterUser(unittest.TestCase):

    def test_init(self) -> None:

        api_mock = NonCallableMagicMock()
        api_mock_user_info = api_mock.get_user.return_value
        api_mock_user_info.name = TWITTER_USER_SAMPLE['name']
        api_mock_user_info.screen_name = TWITTER_USER_SAMPLE['screen_name']
        api_mock_user_info.id = TWITTER_USER_SAMPLE['id']
        api_mock_user_info.profile_image_url_https = TWITTER_USER_SAMPLE['profile_image_url']

        user = TwitterUserWrapper(
            api_mock,
            TWITTER_USER_SAMPLE['screen_name'],     # type: ignore
        )

        self.assertEqual(user.name, TWITTER_USER_SAMPLE['name'])
        self.assertEqual(user.screen_name, TWITTER_USER_SAMPLE['screen_name'])
        self.assertEqual(user.user_id, TWITTER_USER_SAMPLE['id'])
        self.assertEqual(user.profile_image_url, TWITTER_USER_SAMPLE['profile_image_url_orig'])

        api_mock.get_user.assert_called_once_with(screen_name=TWITTER_USER_SAMPLE['screen_name'])


class TestTwitterHelpingFuctions(unittest.TestCase):

    def test_get_twitter_user_timeline_no_last_id(self) -> None:
        api_mock = NonCallableMagicMock()
        user_mock = NonCallableMagicMock()
        since_id = -1

        statuses = get_twitter_user_timeline(api=api_mock, user=user_mock, since_id=since_id)

        self.assertEqual(statuses, api_mock.user_timeline.return_value)
        api_mock.user_timeline.assert_called_once_with(
            screen_name=user_mock.screen_name,
            tweet_mode='extended',
            trim_user=True,
            count=10,
            exclude_replies=True,
        )

    def test_get_twitter_user_timeline_has_last_id(self) -> None:
        api_mock = NonCallableMagicMock()
        user_mock = NonCallableMagicMock()
        since_id = 123456789

        statuses = get_twitter_user_timeline(
            api=api_mock,
            user=user_mock,
            since_id=since_id,
        )

        self.assertEqual(statuses, api_mock.user_timeline.return_value)
        api_mock.user_timeline.assert_called_once_with(
            screen_name=user_mock.screen_name,
            tweet_mode='extended',
            trim_user=True,
            since_id=since_id,
            exclude_replies=True,
        )
