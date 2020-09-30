"""Models"""

from dataclasses import dataclass
from typing import Optional, List


@dataclass
class TwitterAccount:
    """Information of a Twitter account to be fetched"""
    twitter: str
    discord_channels: Optional[List[str]] = None
