"""Test"""
# pylint: disable=C

import logging
import unittest
from typing import Any
from unittest.mock import (ANY, MagicMock, NonCallableMagicMock, mock_open,
                           patch)

from tweepy import OAuthHandler
from twitter_discord_bot.twitter_discord_bot import (DiscordPost, TwitterUser,
                                                     fetch_and_post,
                                                     get_secrets,
                                                     get_twitter_user_names,
                                                     get_twitter_user_timeline,
                                                     get_twitter_users_infos,
                                                     main,
                                                     post_tweets_to_discord,
                                                     read_last_fetched_ids_from_file,
                                                     save_last_fetched_ids_to_file)

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

module_logger = logging.getLogger('twitter_discord_bot.twitter_discord_bot')
module_logger.setLevel(logging.CRITICAL)


def _get_user_mock(screen_name: Any = TWITTER_USER_SAMPLE['screen_name']) -> NonCallableMagicMock:
    user_mock = NonCallableMagicMock(spec=TwitterUser)
    user_mock.name = TWITTER_USER_SAMPLE['name']
    user_mock.screen_name = screen_name
    user_mock.user_id = TWITTER_USER_SAMPLE['id']
    user_mock.profile_image_url = TWITTER_USER_SAMPLE['profile_image_url_orig']
    return user_mock


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


class TestDiscordPost(unittest.TestCase):

    def test_generate_from_twitter_status_with_full_text_and_media(self) -> None:

        user_mock = _get_user_mock()

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

        user_mock = _get_user_mock()

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

        user_mock = _get_user_mock()

        status_mock = NonCallableMagicMock(spec=['id', 'text', 'retweeted_status'])
        status_mock.id = TWITTER_STATUS_SAMPLE['id']
        status_mock.text = TWITTER_STATUS_SAMPLE['text']
        status_mock.retweeted_status = status_mock

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

    def test_generate_from_twitter_status_has_video(self) -> None:

        user_mock = _get_user_mock()

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

    @patch('twitter_discord_bot.twitter_discord_bot.sleep')
    @patch('requests.post')
    def test_save_with_embeds(self, requests_post_mock: MagicMock, sleep_mock: MagicMock) -> None:

        post = DiscordPost(                                             # type: ignore
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

    @patch('twitter_discord_bot.twitter_discord_bot.sleep')
    @patch('requests.post')
    def test_save_without_embeds(
        self, requests_post_mock: MagicMock, sleep_mock: MagicMock
    ) -> None:

        post = DiscordPost(                                             # type: ignore
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


class TestHelpFunctions(unittest.TestCase):
    @patch('twitter_discord_bot.twitter_discord_bot.open', new_callable=mock_open)
    def test_get_twitter_user_names(self, open_mock: MagicMock) -> None:
        usernames_filename = 'usernames.ini'

        user_names = get_twitter_user_names(usernames_filename)

        open_mock.assert_called_once_with(usernames_filename)
        self.assertTrue(all([isinstance(user_names, str) for user_name in user_names]))

    @patch('twitter_discord_bot.twitter_discord_bot.ConfigParser', new=MagicMock())
    @patch('twitter_discord_bot.twitter_discord_bot.open', new_callable=mock_open)
    def test_get_secrets(self, open_mock: MagicMock) -> None:
        secret_filename = 'iamsecret.ini'

        auth_handler, _ = get_secrets(secret_filename)

        open_mock.assert_called_once_with(secret_filename)
        self.assertIsInstance(auth_handler, OAuthHandler)

    @patch.object(TwitterUser, 'get_from_twitter_api')
    def test_get_twitter_users_infos(self, get_from_twitter_api_mock: MagicMock) -> None:
        api_mock = NonCallableMagicMock()
        twitter_user_mock = NonCallableMagicMock(spec=['user_id'])

        get_from_twitter_api_mock.return_value = twitter_user_mock

        user_infos = get_twitter_users_infos(
            api=api_mock, twitter_user_names=TWITTER_USER_NAMES_SAMPLE
        )

        self.assertEqual(get_from_twitter_api_mock.call_args_list, [
            ({'api': api_mock, 'screen_name': user_name_sample},)
            for user_name_sample in TWITTER_USER_NAMES_SAMPLE
        ])
        self.assertIsInstance(user_infos, dict)

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

    @patch.object(DiscordPost, 'generate_from_twitter_status')
    def test_post_tweets_to_discord(self, generate_from_twitter_status_mock: MagicMock) -> None:
        user_mock = NonCallableMagicMock()
        webhook_url = DISCORD_WEBHOOK_SAMPLE
        status_number = 10
        status_mocks = [NonCallableMagicMock() for _ in range(status_number)]
        generate_from_twitter_status_mock.return_value.save.side_effect = [
            200, 201, 204, 304, 400, 401, 403, 404, 405, 429
        ]

        post_tweets_to_discord(user=user_mock, statuses=status_mocks, webhook_url=webhook_url)

        self.assertEqual(
            generate_from_twitter_status_mock.call_args_list,
            [({'user': user_mock, 'status': status},) for status in reversed(status_mocks)]
        )
        self.assertEqual(
            generate_from_twitter_status_mock.return_value.save.call_count,
            status_number
        )

    @patch('twitter_discord_bot.twitter_discord_bot.post_tweets_to_discord')
    @patch('twitter_discord_bot.twitter_discord_bot.get_twitter_user_timeline')
    @patch('twitter_discord_bot.twitter_discord_bot.get_twitter_users_infos')
    def test_fetch_and_post(
            self,
            get_twitter_users_infos_mock: MagicMock,
            get_twitter_user_timeline_mock: MagicMock,
            post_tweets_to_discord_mock: MagicMock,
    ) -> None:
        twitter_users_info_samples = {
            100: _get_user_mock(screen_name='A'),
            200: _get_user_mock(screen_name='B'),
            300: _get_user_mock(screen_name='C'),
        }
        last_fetched_ids_samples = {
            'A': 1000,
            'B': 2000,
        }
        api_mock = NonCallableMagicMock()
        get_twitter_users_infos_mock.return_value = twitter_users_info_samples
        get_twitter_user_timeline_mock.return_value = NonCallableMagicMock()

        last_fetched_ids = fetch_and_post(
            twitter_api=api_mock,
            discord_webhook_url=DISCORD_WEBHOOK_SAMPLE,
            twitter_user_names=TWITTER_USER_NAMES_SAMPLE,
            last_fetched_ids=last_fetched_ids_samples,
        )

        self.assertEqual(
            get_twitter_user_timeline_mock.call_args_list,
            [
                ({'api': api_mock, 'user': twitter_users_info_sample, 'since_id': last_fetched_id},)
                for twitter_users_info_sample, last_fetched_id in zip(
                    twitter_users_info_samples.values(),
                    {**last_fetched_ids_samples, 'C': -1}.values()
                )
            ]
        )
        self.assertEqual(
            post_tweets_to_discord_mock.call_args_list,
            [
                ({'user': twitter_users_info_sample,
                  'statuses': get_twitter_user_timeline_mock.return_value,
                  'webhook_url': DISCORD_WEBHOOK_SAMPLE},)
                for twitter_users_info_sample in twitter_users_info_samples.values()
            ]
        )

        self.assertIsInstance(last_fetched_ids, dict)

    @patch('twitter_discord_bot.twitter_discord_bot.open', new=mock_open())
    @patch('twitter_discord_bot.twitter_discord_bot.ConfigParser', new=MagicMock())
    def test_read_last_fetched_ids_from_file(self) -> None:
        last_id_filename = 'last_id_test.ini'

        last_ids = read_last_fetched_ids_from_file(filename=last_id_filename)

        self.assertIsInstance(last_ids, dict)

    @patch('twitter_discord_bot.twitter_discord_bot.open', new=MagicMock(side_effect=OSError))
    @patch('twitter_discord_bot.twitter_discord_bot.ConfigParser')
    def test_read_last_fetched_ids_from_file_not_exists(
            self, config_parser_mock: MagicMock
    ) -> None:
        last_id_filename = 'last_id_test.ini'

        last_ids = read_last_fetched_ids_from_file(filename=last_id_filename)

        config_parser_mock.return_value.read_file.assert_not_called()
        self.assertEqual(last_ids, {})

    @patch('twitter_discord_bot.twitter_discord_bot.open', new_callable=mock_open)
    @patch('twitter_discord_bot.twitter_discord_bot.ConfigParser')
    def test_save_last_fetched_ids_to_file(
            self, config_parser_mock: MagicMock, open_mock: MagicMock
    ) -> None:
        last_id_filename = 'last_id_test.ini'
        last_fetched_ids_mock = {
            'screen_name1': 100,
            'screen_name2': 200,
            'screen_name3': 300,
        }

        config_parser_mock.return_value.has_section.return_value = True

        save_last_fetched_ids_to_file(
            filename=last_id_filename, last_fetched_ids=last_fetched_ids_mock
        )

        config_parser_mock.return_value.write.assert_called_once_with(open_mock.return_value)

    @patch('twitter_discord_bot.twitter_discord_bot.open', new_callable=mock_open)
    @patch('twitter_discord_bot.twitter_discord_bot.ConfigParser')
    def test_save_last_fetched_ids_to_file_not_exists(
            self, config_parser_mock: MagicMock, open_mock: MagicMock
    ) -> None:
        last_id_filename = 'last_id_test.ini'
        last_fetched_ids = {
            'screen_name1': 100,
            'screen_name2': 200,
            'screen_name3': 300,
        }

        config_parser_mock.return_value.has_section.return_value = False

        save_last_fetched_ids_to_file(
            filename=last_id_filename, last_fetched_ids=last_fetched_ids
        )

        config_parser_mock.return_value.add_section.assert_called_once_with('LastID')
        self.assertEqual(
            config_parser_mock.return_value.__getitem__.return_value.__setitem__.call_args_list,
            [((screen_name, str(last_fetched_id)),)
             for screen_name, last_fetched_id in last_fetched_ids.items()]
        )
        config_parser_mock.return_value.write.assert_called_once_with(open_mock.return_value)

    @patch('twitter_discord_bot.twitter_discord_bot.receive_stop.wait', side_effect=InterruptedError)
    @patch('twitter_discord_bot.twitter_discord_bot.fetch_and_post')
    @patch('twitter_discord_bot.twitter_discord_bot.save_last_fetched_ids_to_file')
    @patch('twitter_discord_bot.twitter_discord_bot.read_last_fetched_ids_from_file')
    @patch('twitter_discord_bot.twitter_discord_bot.get_secrets')
    @patch('twitter_discord_bot.twitter_discord_bot.get_twitter_user_names')
    @patch('tweepy.API')
    def test_main(
            self,
            tweepy_api_mock: MagicMock,
            get_twitter_user_names_mock: MagicMock,
            get_secrets_mock: MagicMock,
            read_last_fetched_ids_from_file_mock: MagicMock,
            save_last_fetched_ids_to_file_mock: MagicMock,
            fetch_and_post_mock: MagicMock,
            sleep_mock: MagicMock,
    ) -> None:
        auth_handler_mock = NonCallableMagicMock()
        get_twitter_user_names_mock.return_value = ['foo', 'bar']
        get_secrets_mock.return_value = (auth_handler_mock, DISCORD_WEBHOOK_SAMPLE)

        with self.assertRaises(InterruptedError):
            main()

        get_twitter_user_names_mock.assert_called_once()
        get_secrets_mock.assert_called_once()
        tweepy_api_mock.assert_called_once_with(auth_handler=auth_handler_mock)
        fetch_and_post_mock.assert_called_once_with(
            twitter_api=tweepy_api_mock.return_value,
            discord_webhook_url=DISCORD_WEBHOOK_SAMPLE,
            twitter_user_names=ANY,
            last_fetched_ids=read_last_fetched_ids_from_file_mock.return_value,
        )
        save_last_fetched_ids_to_file_mock.assert_called_once()
        sleep_mock.assert_called_once()
