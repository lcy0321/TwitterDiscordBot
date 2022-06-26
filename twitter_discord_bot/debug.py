"""For debugging

python -m twitter_discord_bot.debug {Tweet ID}
"""

import sys
from pprint import pprint

import tweepy
import tweepy.models

from .configs import TWITTER_SECRETS_PATH
from .discord_api import DiscordPost
from .twitter_api import TwitterUserWrapper
from .twitter_discord_bot import _get_twitter_bearer_token


def main() -> None:

    twitter_bearer_token = _get_twitter_bearer_token(path=TWITTER_SECRETS_PATH)
    api = tweepy.API(auth=tweepy.OAuth2BearerHandler(bearer_token=twitter_bearer_token))

    tweet_id = sys.argv[1]

    print(f'Fetching Tweet ID: {tweet_id}')
    print()

    tweet: tweepy.models.Status = api.get_status(
        id=tweet_id,
        tweet_mode='extended',
    )
    stub_user = TwitterUserWrapper._contruct_for_testing(
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
