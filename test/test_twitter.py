"""Test"""
# pylint: disable=C

import unittest
from unittest.mock import MagicMock, NonCallableMagicMock, patch

from twitter_discord_bot.twitter_api import (TwitterUser, get_auth_handler,
                                             get_twitter_user_timeline)

from .help import TWITTER_USER_SAMPLE


class TestTwitterUser(unittest.TestCase):

    def test_init(self) -> None:
        user = TwitterUser(                                                     # type: ignore
            name=TWITTER_USER_SAMPLE['name'],
            screen_name=TWITTER_USER_SAMPLE['screen_name'],
            user_id=TWITTER_USER_SAMPLE['id'],
            profile_image_url=TWITTER_USER_SAMPLE['profile_image_url'],
        )
        self.assertEqual(user.name, TWITTER_USER_SAMPLE['name'])
        self.assertEqual(user.screen_name, TWITTER_USER_SAMPLE['screen_name'])
        self.assertEqual(user.user_id, TWITTER_USER_SAMPLE['id'])
        self.assertEqual(user.profile_image_url, TWITTER_USER_SAMPLE['profile_image_url_orig'])

    @patch.object(target=TwitterUser, attribute='__init__')
    def test_get_from_twitter_api(self, twitter_user_init_mock: MagicMock) -> None:

        api_mock = NonCallableMagicMock()
        api_mock_user_info = api_mock.get_user.return_value
        api_mock_user_info.name = TWITTER_USER_SAMPLE['name']
        api_mock_user_info.screen_name = TWITTER_USER_SAMPLE['screen_name']
        api_mock_user_info.id = TWITTER_USER_SAMPLE['id']
        api_mock_user_info.profile_image_url_https = TWITTER_USER_SAMPLE['profile_image_url']

        twitter_user_init_mock.return_value = None

        user = TwitterUser.get_from_twitter_api(                  # type: ignore
            api_mock, TWITTER_USER_SAMPLE['screen_name']
        )

        api_mock.get_user.assert_called_once_with(TWITTER_USER_SAMPLE['screen_name'])
        twitter_user_init_mock.assert_called_once_with(
            name=TWITTER_USER_SAMPLE['name'],
            screen_name=TWITTER_USER_SAMPLE['screen_name'],
            user_id=TWITTER_USER_SAMPLE['id'],
            profile_image_url=TWITTER_USER_SAMPLE['profile_image_url'],
        )
        self.assertIsInstance(user, TwitterUser)


class TestTwitterHelpingFuctions(unittest.TestCase):

    def test_get_twitter_user_timeline_no_last_id(self) -> None:
        api_mock = NonCallableMagicMock()
        user_mock = NonCallableMagicMock()
        since_id = -1

        statuses = get_twitter_user_timeline(api=api_mock, user=user_mock, since_id=since_id)

        self.assertEqual(statuses, api_mock.user_timeline.return_value)
        api_mock.user_timeline.assert_called_once_with(
            user_mock.user_id, tweet_mode='extended', trim_user=True, count=10
        )

    def test_get_twitter_user_timeline_has_last_id(self) -> None:
        api_mock = NonCallableMagicMock()
        user_mock = NonCallableMagicMock()
        since_id = 123456789

        statuses = get_twitter_user_timeline(api=api_mock, user=user_mock, since_id=since_id)

        self.assertEqual(statuses, api_mock.user_timeline.return_value)
        api_mock.user_timeline.assert_called_once_with(
            user_mock.user_id, tweet_mode='extended', trim_user=True, since_id=since_id
        )

    def test_get_auth_handler(self) -> None:
        test_tokens = {
            'consumer_key': 'abc',
            'consumer_secret': 'def',
            'access_token': 'ghi',
            'access_token_secret': 'jkl',
        }
        auth_handler = get_auth_handler(**test_tokens)
        self.assertIsNotNone(auth_handler.consumer_key)
        self.assertIsNotNone(auth_handler.consumer_secret)
        self.assertIsNotNone(auth_handler.access_token)
        self.assertIsNotNone(auth_handler.access_token_secret)
