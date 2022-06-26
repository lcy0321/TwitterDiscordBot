"""Test"""
# pylint: disable=C

import logging
import unittest
from unittest.mock import MagicMock, NonCallableMagicMock, mock_open, patch

from twitter_discord_bot.twitter_discord_bot import (
    DiscordPost,
    _get_twitter_bearer_token,
    _post_tweets_to_discord,
    _read_last_fetched_ids_from_file,
    _save_last_fetched_ids_to_file,
)

from .help import DISCORD_WEBHOOK_SAMPLE

module_logger = logging.getLogger('twitter_discord_bot.twitter_discord_bot')
module_logger.setLevel(logging.CRITICAL)


class TestHelpFunctions(unittest.TestCase):
    @patch.object(DiscordPost, 'generate_from_twitter_status')
    def test_post_tweets_to_discord(self, generate_from_twitter_status_mock: MagicMock) -> None:
        user_mock = NonCallableMagicMock()
        webhook_url = DISCORD_WEBHOOK_SAMPLE
        status_number = 10
        status_mocks = [NonCallableMagicMock() for _ in range(status_number)]
        generate_from_twitter_status_mock.return_value.save.side_effect = [
            200, 201, 204, 304, 400, 401, 403, 404, 405, 429
        ]

        _post_tweets_to_discord(user=user_mock, statuses=status_mocks, webhook_url=webhook_url)

        self.assertEqual(
            generate_from_twitter_status_mock.call_args_list,
            [({'user': user_mock, 'status': status},) for status in reversed(status_mocks)]
        )
        self.assertEqual(
            generate_from_twitter_status_mock.return_value.save.call_count,
            status_number
        )

    @patch('twitter_discord_bot.twitter_discord_bot.open', new=mock_open())
    @patch('twitter_discord_bot.twitter_discord_bot.ConfigParser', new=MagicMock())
    def test_read_last_fetched_ids_from_file(self) -> None:
        last_id_filename = 'last_id_test.ini'

        last_ids = _read_last_fetched_ids_from_file(filename=last_id_filename)

        self.assertIsInstance(last_ids, dict)

    @patch('twitter_discord_bot.twitter_discord_bot.open', new=MagicMock(side_effect=OSError))
    @patch('twitter_discord_bot.twitter_discord_bot.ConfigParser')
    def test_read_last_fetched_ids_from_file_not_exists(
            self, config_parser_mock: MagicMock
    ) -> None:
        last_id_filename = 'last_id_test.ini'

        last_ids = _read_last_fetched_ids_from_file(filename=last_id_filename)

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

        _save_last_fetched_ids_to_file(
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

        _save_last_fetched_ids_to_file(
            filename=last_id_filename, last_fetched_ids=last_fetched_ids
        )

        config_parser_mock.return_value.add_section.assert_called_once_with('LastID')
        self.assertEqual(
            config_parser_mock.return_value.__getitem__.return_value.__setitem__.call_args_list,
            [((screen_name, str(last_fetched_id)),)
             for screen_name, last_fetched_id in last_fetched_ids.items()]
        )
        config_parser_mock.return_value.write.assert_called_once_with(open_mock.return_value)
