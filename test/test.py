"""Test"""
# pylint: disable=C

import logging
import unittest
from unittest.mock import (ANY, MagicMock, NonCallableMagicMock, mock_open,
                           patch)

from twitter_discord_bot.twitter_discord_bot import (fetch_and_post,
                                                     get_secrets,
                                                     get_twitter_user_names,
                                                     main,
                                                     post_tweets_to_discord,
                                                     read_last_fetched_ids_from_file,
                                                     save_last_fetched_ids_to_file,
                                                     DiscordPost)

from .help import (DISCORD_WEBHOOK_SAMPLE, TWITTER_USER_NAMES_SAMPLE,
                   _get_user_mock)

module_logger = logging.getLogger('twitter_discord_bot.twitter_discord_bot')
module_logger.setLevel(logging.CRITICAL)


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

        twitter_tokens, webhook_url = get_secrets(secret_filename)

        open_mock.assert_called_once_with(secret_filename)
        self.assertTrue(len(twitter_tokens) == 4)
        self.assertIsNotNone(webhook_url)

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

    @patch('twitter_discord_bot.twitter_discord_bot.receive_stop.wait',
           side_effect=InterruptedError)
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
        get_twitter_user_names_mock.return_value = ['foo', 'bar']
        get_secrets_mock.return_value = (['a', 'b', 'c', 'd'], DISCORD_WEBHOOK_SAMPLE)

        with self.assertRaises(InterruptedError):
            main()

        get_twitter_user_names_mock.assert_called_once()
        get_secrets_mock.assert_called_once()
        tweepy_api_mock.assert_called_once()
        fetch_and_post_mock.assert_called_once_with(
            twitter_api=tweepy_api_mock.return_value,
            discord_webhook_url=DISCORD_WEBHOOK_SAMPLE,
            twitter_user_names=ANY,
            last_fetched_ids=read_last_fetched_ids_from_file_mock.return_value,
        )
        save_last_fetched_ids_to_file_mock.assert_called_once()
        sleep_mock.assert_called_once()
