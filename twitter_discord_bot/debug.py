"""For debugging

python -m twitter_discord_bot.debug {Tweet ID}
"""

import sys
from pprint import pprint

import tweepy
import tweepy.models

from .configs import TWITTER_SECRETS_PATH
from .discord_api import DiscordPost
from .twitter_api import TwitterUser, get_auth_handler
from .twitter_discord_bot import get_twitter_secrets


def main() -> None:

    twitter_tokens = get_twitter_secrets(path=TWITTER_SECRETS_PATH)
    api = tweepy.API(auth=get_auth_handler(*twitter_tokens))

    tweet_id = sys.argv[1]

    print(f'Fetching Tweet ID: {tweet_id}')
    print()

    tweet: tweepy.models.Status = api.get_status(
        id=tweet_id,
        tweet_mode='extended',
    )
    stub_user = TwitterUser(
        name='name',
        screen_name='screen_name',
        user_id=0,
        profile_image_url='profile_image_url',
    )

    print('[Medias]')
    try:
        pprint(DiscordPost._get_medias_from_twitter_status(tweet))
    except DiscordPost._HasVideoException:
        print('!!!HAS VIDEO!!!')
    print()

    print('[Discord Post]')
    pprint(DiscordPost.generate_from_twitter_status(user=stub_user, status=tweet))
    print()


if __name__ == '__main__':
    main()
