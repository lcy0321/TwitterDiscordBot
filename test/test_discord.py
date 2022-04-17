"""Test"""
# pylint: disable=C

import typing
import unittest
from unittest.mock import MagicMock, NonCallableMagicMock, patch

from twitter_discord_bot.discord_api import DiscordPost

from .help import (DISCORD_WEBHOOK_SAMPLE, TWITTER_STATUS_SAMPLE, TWITTER_STATUS_SAMPLE_2,
                   TWITTER_USER_SAMPLE, TWITTER_USER_SAMPLE_2, get_user_mock)


class TestDiscordPost(unittest.TestCase):

    def test_generate_from_twitter_status_with_full_text_and_media(self) -> None:

        user_mock = get_user_mock()

        status_mock = NonCallableMagicMock(
            spec=['id', 'text', 'text', 'full_text', 'extended_entities']
        )
        status_mock.id = TWITTER_STATUS_SAMPLE['id']
        status_mock.text = TWITTER_STATUS_SAMPLE['text']
        status_mock.full_text = TWITTER_STATUS_SAMPLE['full_text']
        status_mock.extended_entities = {
            'media': [
                {
                    'type': 'photo',
                    'media_url_https': TWITTER_STATUS_SAMPLE['media_url_https'],
                },
            ]
        }

        post = DiscordPost.generate_from_twitter_status(user=user_mock, status=status_mock)

        self.assertIsInstance(post, DiscordPost)
        self.assertEqual(post.username, TWITTER_USER_SAMPLE['name'])
        self.assertEqual(post.avatar_url, TWITTER_USER_SAMPLE['profile_image_url_orig'])
        self.assertEqual(
            post.content,
            (f'<http://twitter.com/{TWITTER_USER_SAMPLE["screen_name"]}/status/'
             f'{TWITTER_STATUS_SAMPLE["id"]}>\n'
             f'{TWITTER_STATUS_SAMPLE["full_text"]}')
        )
        self.assertEqual(post.embeds, [{
            'image': {
                'url': TWITTER_STATUS_SAMPLE['media_url_https'],
            }
        }])

    def test_generate_from_twitter_status_without_full_text_and_media(self) -> None:

        user_mock = get_user_mock()

        status_mock = NonCallableMagicMock(spec=['id', 'text'])
        status_mock.id = TWITTER_STATUS_SAMPLE['id']
        status_mock.text = TWITTER_STATUS_SAMPLE['text']

        post = DiscordPost.generate_from_twitter_status(user=user_mock, status=status_mock)

        self.assertIsInstance(post, DiscordPost)
        self.assertEqual(post.username, TWITTER_USER_SAMPLE['name'])
        self.assertEqual(post.avatar_url, TWITTER_USER_SAMPLE['profile_image_url_orig'])
        self.assertEqual(
            post.content,
            (f'<http://twitter.com/{TWITTER_USER_SAMPLE["screen_name"]}/status/'
             f'{TWITTER_STATUS_SAMPLE["id"]}>\n'
             f'{TWITTER_STATUS_SAMPLE["text"]}')
        )
        self.assertIsNone(post.embeds)

    def test_generate_from_twitter_status_retweet(self) -> None:

        user_mock = get_user_mock()

        original_status_mock = NonCallableMagicMock(spec=['id', 'text', 'user'])
        original_status_mock.id = TWITTER_STATUS_SAMPLE_2['id']
        original_status_mock.text = TWITTER_STATUS_SAMPLE_2['text']
        original_status_mock.user.screen_name = TWITTER_USER_SAMPLE_2['screen_name']

        status_mock = NonCallableMagicMock(spec=['id', 'text', 'retweeted_status'])
        status_mock.id = TWITTER_STATUS_SAMPLE['id']
        status_mock.text = TWITTER_STATUS_SAMPLE['text']
        status_mock.retweeted_status = original_status_mock

        post = DiscordPost.generate_from_twitter_status(user=user_mock, status=status_mock)

        self.assertIsInstance(post, DiscordPost)
        self.assertEqual(post.username, TWITTER_USER_SAMPLE['name'])
        self.assertEqual(post.avatar_url, TWITTER_USER_SAMPLE['profile_image_url_orig'])
        self.assertEqual(
            post.content,
            (
                f'RT: http://twitter.com/_/status/{TWITTER_STATUS_SAMPLE_2["id"]}\n'
                f'http://twitter.com/{TWITTER_USER_SAMPLE["screen_name"]}/status/'
                f'{TWITTER_STATUS_SAMPLE["id"]}'
            )
        )
        self.assertIsNone(post.embeds)

    def test_generate_from_twitter_status_has_video(self) -> None:

        user_mock = get_user_mock()

        status_mock = NonCallableMagicMock(
            spec=['id', 'text', 'text', 'full_text', 'extended_entities']
        )
        status_mock.id = TWITTER_STATUS_SAMPLE['id']
        status_mock.text = TWITTER_STATUS_SAMPLE['text']
        status_mock.full_text = TWITTER_STATUS_SAMPLE['full_text']
        status_mock.extended_entities = {
            'media': [
                {
                    'type': 'video',
                    'media_url_https': TWITTER_STATUS_SAMPLE['media_url_https'],
                },
            ]
        }

        post = DiscordPost.generate_from_twitter_status(user=user_mock, status=status_mock)

        self.assertIsInstance(post, DiscordPost)
        self.assertEqual(post.username, TWITTER_USER_SAMPLE['name'])
        self.assertEqual(post.avatar_url, TWITTER_USER_SAMPLE['profile_image_url_orig'])
        self.assertEqual(
            post.content,
            (f'http://twitter.com/{TWITTER_USER_SAMPLE["screen_name"]}/status/'
             f'{TWITTER_STATUS_SAMPLE["id"]}')
        )
        self.assertIsNone(post.embeds)

    @typing.no_type_check
    @patch('twitter_discord_bot.discord_api.sleep')
    @patch('requests.post')
    def test_save_with_embeds(self, requests_post_mock: MagicMock, sleep_mock: MagicMock) -> None:

        post = DiscordPost(
            username=TWITTER_USER_SAMPLE['name'],
            avatar_url=TWITTER_USER_SAMPLE['profile_image_url_orig'],
            content=TWITTER_STATUS_SAMPLE['full_text'],
            embeds=[{
                'image': {
                    'url': TWITTER_STATUS_SAMPLE['media_url_https'],
                }
            }],
        )
        expected_payload = {
            'username': TWITTER_USER_SAMPLE['name'],
            'avatar_url': TWITTER_USER_SAMPLE['profile_image_url_orig'],
            'content': TWITTER_STATUS_SAMPLE['full_text'],
            'embeds': [{
                'image': {
                    'url': TWITTER_STATUS_SAMPLE['media_url_https'],
                }
            }],
        }
        sleep_sec = 3.0
        requests_post_mock.return_value.status_code = 200

        result = post.save(webhook_url=DISCORD_WEBHOOK_SAMPLE, sleep_seconds=sleep_sec)

        requests_post_mock.assert_called_once_with(DISCORD_WEBHOOK_SAMPLE, json=expected_payload)
        sleep_mock.assert_called_once_with(sleep_sec)
        self.assertEqual(result, 200)

    @typing.no_type_check
    @patch('twitter_discord_bot.discord_api.sleep')
    @patch('requests.post')
    def test_save_without_embeds(
        self, requests_post_mock: MagicMock, sleep_mock: MagicMock
    ) -> None:

        post = DiscordPost(
            username=TWITTER_USER_SAMPLE['name'],
            avatar_url=TWITTER_USER_SAMPLE['profile_image_url_orig'],
            content=TWITTER_STATUS_SAMPLE['full_text'],
        )
        expected_payload = {
            'username': TWITTER_USER_SAMPLE['name'],
            'avatar_url': TWITTER_USER_SAMPLE['profile_image_url_orig'],
            'content': TWITTER_STATUS_SAMPLE['full_text'],
        }
        sleep_sec = 3.0
        requests_post_mock.return_value.status_code = 200

        result = post.save(webhook_url=DISCORD_WEBHOOK_SAMPLE, sleep_seconds=sleep_sec)

        requests_post_mock.assert_called_once_with(DISCORD_WEBHOOK_SAMPLE, json=expected_payload)
        sleep_mock.assert_called_once_with(sleep_sec)
        self.assertEqual(result, 200)
