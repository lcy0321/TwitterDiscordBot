"""Helping functions that related to Discord API"""
from time import sleep
from typing import Any, Dict, List, Optional, Union

import requests

import tweepy
from dataclasses import dataclass

from .twitter_api import TwitterUser


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
        try:
            media_entities = status.extended_entities['media']
        except AttributeError:
            return None

        medias = []
        for media in media_entities:
            if media['type'] == 'video':
                raise cls._HasVideoException

            medias.append({'image': {'url': media['media_url_https']}})
        return medias

    @classmethod
    def generate_from_twitter_status(
            cls, user: TwitterUser, status: tweepy.Status
    ) -> 'DiscordPost':
        """Generate DiscordPost from a TwitterUser and a tweepy.Status"""

        # Whether the tweet is a retweet
        is_retweet = hasattr(status, 'retweeted_status')
        has_video = False

        if is_retweet:
            # Currently Discord fails to show preview of retweets
            embeds = None
            content = f'http://fxtwitter.com/{user.screen_name}/status/{status.id}'
        else:
            # Discord api does not accept videos in the embeds
            try:
                embeds = cls._get_medias_from_twitter_status(status=status)
            except cls._HasVideoException:
                has_video = True
                embeds = None
                content = f'http://twitter.com/{user.screen_name}/status/{status.id}'

        if not (has_video or is_retweet):
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
