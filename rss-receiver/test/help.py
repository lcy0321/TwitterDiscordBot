"""Helping functions and data for tests"""
from typing import Any
from unittest.mock import NonCallableMagicMock

from twitter_discord_bot.twitter_discord_bot import TwitterUser

TWITTER_USER_SAMPLE = {
    'name': 'name',
    'screen_name': 'screen_name',
    'id': 10000,
    'profile_image_url': 'https://pbs.twimg.com/profile_images/123456/asf5464_normal.jpg',
    'profile_image_url_orig': 'https://pbs.twimg.com/profile_images/123456/asf5464.jpg',
}

TWITTER_STATUS_SAMPLE = {
    'id': 12345,
    'text': 'text',
    'full_text': 'full_text',
    'media_url_https': 'https://pbs.twimg.com/profile_images/123456/asf5464_normal.jpg',
}

TWITTER_USER_NAMES_SAMPLE = [
    'foo',
    'bar',
    'test',
]

DISCORD_WEBHOOK_SAMPLE = 'https://webhook.discord.local'


def _get_user_mock(screen_name: Any = TWITTER_USER_SAMPLE['screen_name']) -> NonCallableMagicMock:
    user_mock = NonCallableMagicMock(spec=TwitterUser)
    user_mock.name = TWITTER_USER_SAMPLE['name']
    user_mock.screen_name = screen_name
    user_mock.user_id = TWITTER_USER_SAMPLE['id']
    user_mock.profile_image_url = TWITTER_USER_SAMPLE['profile_image_url_orig']
    return user_mock
