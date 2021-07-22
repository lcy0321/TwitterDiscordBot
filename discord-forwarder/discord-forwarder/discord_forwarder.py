"""Receive the message request from ZeroMQ, and post them to Discord via webhooks."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from time import sleep
from typing import Any, Dict, List, Optional, Union

import requests
import zmq
from zmq.utils import jsonapi

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

INTERVAL_BETWEEN_WEBHOOK_SEC = 3


@dataclass
class MessageRequest:
    """A message request received from ZMQ."""

    source_id: str
    source_type: str
    username: str
    avatar_url: str
    content: str = ''
    embeds: Optional[List[Dict[str, Any]]] = None

    @classmethod
    def from_dict(cls, dict: Dict) -> MessageRequest:
        return cls(**dict)


@dataclass
class DiscordMessage:
    """Contains the contents of a Discord channel message."""

    username: str
    avatar_url: str
    content: str = ''
    embeds: Optional[List[Dict[str, Any]]] = None

    @classmethod
    def from_message_request(cls, message_request: MessageRequest):
        return cls(
            username=message_request.username,
            avatar_url=message_request.avatar_url,
            content=message_request.content,
            embeds=message_request.embeds,
        )

    def save(self, webhook_url: str) -> int:
        """Post the content to Discord via the webhook."""

        payload: Dict[str, Union[str, List[Dict[str, Any]]]] = {
            'username': self.username,
            'avatar_url': self.avatar_url,
            'content': self.content,
        }
        if self.embeds is not None:
            payload['embeds'] = self.embeds

        response = requests.post(webhook_url, json=payload)

        return response.status_code


def main():

    addr = 'tcp://127.0.0.1:5555'
    webhook = 'https://discord.com/api/webhooks/484173834543431700/FozlbxJ3Gj8rkSB1f9byX2CpfmVoHlNXrELKndB5oICz57l18_dXG_OheQXsok2vsG2i'

    zmq_server = zmq.Context().socket(zmq.REP)
    zmq_server.bind(addr)
    logger.info(f'Bound to {addr}')

    while True:
        message_request = zmq_server.recv_json(object_hook=MessageRequest.from_dict)
        logger.info(
            f'Received message from: {message_request.source_type}, '
            f'id: {message_request.source_id}'
        )

        DiscordMessage.from_message_request(message_request).save(webhook)
        zmq_server.send(b'')
        sleep(INTERVAL_BETWEEN_WEBHOOK_SEC)
