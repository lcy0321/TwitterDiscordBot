"""A bot that fetch tweets from Twitter and post to Discord"""
import logging
import re
from configparser import ConfigParser
from time import sleep
from typing import Any, Dict, List, Optional, Tuple, Union

import requests

import tweepy
from dataclasses import dataclass

# logging.getLogger('urllib3').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)    # pylint: disable=invalid-name
logger.setLevel(logging.DEBUG)
logging.basicConfig(format='%(asctime)s:%(levelname)-7s:%(message)s', datefmt='%Y-%m-%d %H:%M:%S')


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


@dataclass
class DiscordPost():
    """Contains the contents of a Discord channel message"""

    username: str
    avatar_url: str
    content: str = ''
    embeds: Optional[List[Dict[str, Any]]] = None

    class _HasVideoException(Exception):
        pass

    @classmethod
    def _get_medias_from_twitter_status(
            cls, status: tweepy.Status
    ) -> Optional[List[Dict[str, Dict[str, str]]]]:
        medias = []
        try:
            for media in status.extended_entities['media']:
                if media['type'] == 'video':
                    raise cls._HasVideoException

                medias.append({'image': {'url': media['media_url_https']}})
        except AttributeError:
            return None
        else:
            return medias

    @classmethod
    def generate_from_twitter_status(
            cls, user: TwitterUser, status: tweepy.Status
    ) -> 'DiscordPost':
        """Generate DiscordPost from a TwitterUser and a tweepy.Status"""

        # Whether the tweet is a retweet
        is_retweet = hasattr(status, 'retweeted_status')

        # Discord api does not accept videos in the embeds
        if not is_retweet:
            try:
                embeds = cls._get_medias_from_twitter_status(status=status)
                has_video = False
            except cls._HasVideoException:
                has_video = True

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

        post = DiscordPost(
            username=user.name, avatar_url=user.profile_image_url,
            content=content, embeds=embeds,
        )

        return post

    def save(self, webhook_url: str, sleep_seconds: float = 0.5) -> int:
        """Post the content to Discord with the webhook"""

        payload: Dict[str, Union[str, List[Dict[str, Any]]]] = {
            'username': self.username,
            'avatar_url': self.avatar_url,
            'content': self.content,
        }
        if self.embeds is not None:
            payload['embeds'] = self.embeds

        response = requests.post(webhook_url, json=payload)

        sleep(sleep_seconds)

        return response.status_code


# class DiscordBotStreamListener(tweepy.StreamListener):
#     """Override tweepy.StreamListener to post new tweets to the Discord channel"""

#     def __init__(
#             self,
#             discord_webhook_url: str,
#             api: tweepy.API = None
#     ) -> None:
#         self.discord_webhook_url = discord_webhook_url
#         super().__init__(api=api)

#     def on_status(self, status: tweepy.Status) -> None:
#         """Called when a new status arrives"""

#         logger.info('New status from %s at %s', status.user.name, status.created_at)

#         post = DiscordPost.generate_from_twitter_status(status=status)
#         status_code = post.save(webhook_url=self.discord_webhook_url)

#         if status_code not in [200, 201, 204]:
#             logger.error('Failed to post to the Discord cahnnel, status code: %d.', status_code)


def get_secrets(filename: str) -> Tuple[tweepy.OAuthHandler, str]:
    """Read secret file and return tweepy.OAuthHandler and Discord webhook"""
    config_parser = ConfigParser()

    with open(filename) as secret_config_file:
        config_parser.read_file(secret_config_file)

    consumer_key = config_parser['Twitter']['ConsumerKey']
    consumer_secret = config_parser['Twitter']['ConsumerSecret']
    access_token = config_parser['Twitter']['AccessToken']
    access_token_secret = config_parser['Twitter']['AccessTokenSecret']
    webhook_url = config_parser['Discord']['BotWebHookUrl']

    auth_handler = tweepy.OAuthHandler(
        consumer_key=consumer_key, consumer_secret=consumer_secret
    )
    auth_handler.set_access_token(key=access_token, secret=access_token_secret)

    return auth_handler, webhook_url


def get_twitter_users_infos(
        api: tweepy.API, twitter_user_names: List[str]
) -> Dict[int, TwitterUser]:
    """Get user objects from Twitter"""

    twitter_users_infos: Dict[int, TwitterUser] = {}

    for screen_name in twitter_user_names:
        twitter_user = TwitterUser.get_from_twitter_api(api=api, screen_name=screen_name)
        twitter_users_infos[twitter_user.user_id] = twitter_user

    return twitter_users_infos


def get_twitter_user_timeline(
        api: tweepy.API, user: TwitterUser, since_id: int = -1,
) -> List[tweepy.Status]:
    """Get statuses of the specific user from Twitter"""

    if since_id == -1:
        logger.info('Doesn\'t found the information of last ids, fetch lastest 10 tweets...')

        statuses = api.user_timeline(
            user.user_id, tweet_mode='extended', trim_user=True, count=10
        )
    else:
        logger.debug('Fetching tweets since id: %s', since_id)

        statuses = api.user_timeline(
            user.user_id, tweet_mode='extended', trim_user=True, since_id=since_id
        )

    return statuses


def post_tweets_to_discord(
        user: TwitterUser, statuses: List[tweepy.Status], webhook_url: str
) -> None:
    """Post the statuses to the Discord channel with the webhook"""
    for status in reversed(statuses):
        post = DiscordPost.generate_from_twitter_status(user=user, status=status)
        response_code = post.save(webhook_url=webhook_url)

        if response_code in [200, 201, 204]:
            logger.info('Successfully post twitter id %d to the Discord channel.', status.id)
        else:
            logger.error(
                'Failed to post twitter id %d to the Discord channel. Code: %d',
                status.id, response_code
            )


def fetch_and_post(
        twitter_api: tweepy.API, discord_webhook_url: str,
        twitter_user_names: List[str], last_fetched_ids: Dict[str, int],
) -> Dict[str, int]:
    """
    Fetch tweets and post them to the Discord channel.
    Return the ids of the lastest tweets.
    """

    # Get user information
    logger.debug('Fetching user information...')
    twitter_users_infos = get_twitter_users_infos(
        api=twitter_api, twitter_user_names=twitter_user_names
    )

    latest_ids = last_fetched_ids.copy()

    # Fetching timeline
    for user in twitter_users_infos.values():
        logger.debug('Fetching timeline from %s...', user.screen_name)

        try:
            since_id = last_fetched_ids[user.screen_name]
        except KeyError:
            since_id = -1

        statuses = get_twitter_user_timeline(api=twitter_api, user=user, since_id=since_id)

        logger.info('Found %d new tweet(s).', len(statuses))

        post_tweets_to_discord(user=user, statuses=statuses, webhook_url=discord_webhook_url)

        if statuses:
            latest_ids[user.screen_name] = statuses[0].id

    return latest_ids


def read_last_fetched_ids_from_file(filename: str) -> Dict[str, int]:
    """Read the id of tweets that have fetched last time from the file"""

    config_parser = ConfigParser()

    try:
        with open(filename) as last_id_file:
            config_parser.read_file(last_id_file)
    except OSError:
        return {}

    return {
        screen_name: int(tweet_id)
        for screen_name, tweet_id in config_parser.items(section='LastID')
    }


def save_last_fetched_ids_to_file(filename: str, last_fetched_ids: Dict[str, int]) -> None:
    """Read the id of tweets that have fetched last time from the file"""

    config_parser = ConfigParser()

    if not config_parser.has_section('LastID'):
        config_parser.add_section('LastID')

    for screen_name, last_id in last_fetched_ids.items():
        config_parser['LastID'][screen_name] = str(last_id)

    with open(filename, 'w') as last_id_file:
        config_parser.write(last_id_file)


def main() -> None:
    """main function"""

    twitter_user_names = [
        'imascg_stage',
        'imasml_theater',
        'imassc_official',
    ]

    secret_filename = 'secret.ini'
    last_fetched_ids_filename = 'last_id.ini'

    auth_handler, discord_webhook_url = get_secrets(filename=secret_filename)
    api = tweepy.API(auth_handler=auth_handler)

    # Get the last ids that have fecthed
    last_fetched_ids = read_last_fetched_ids_from_file(filename=last_fetched_ids_filename)

    while True:
        last_fetched_ids = fetch_and_post(
            twitter_api=api,
            discord_webhook_url=discord_webhook_url,
            twitter_user_names=twitter_user_names,
            last_fetched_ids=last_fetched_ids,
        )
        save_last_fetched_ids_to_file(last_fetched_ids_filename, last_fetched_ids)
        sleep(60)


if __name__ == '__main__':
    main()
