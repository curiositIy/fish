from typing import List, Optional, ParamSpec, TypeAlias, TypedDict, TypeVar, Union

import discord

T = TypeVar("T")
P = ParamSpec("P")
EmojiInputType = Union[discord.Emoji, discord.PartialEmoji, str]

AllChannels: TypeAlias = Union[
    discord.TextChannel,
    discord.VoiceChannel,
    discord.CategoryChannel,
    discord.StageChannel,
    discord.ForumChannel,
    discord.Thread,
]
DiscordObjects: TypeAlias = Optional[
    Union[
        discord.Message,
        discord.Member,
        discord.User,
        discord.Guild,
        AllChannels,
    ]
]


class Webhooks(TypedDict):
    avatars: List[str]
    images: List[str]
    icons: List[str]


class Twitter(TypedDict):
    username: str
    password: str


class Databases(TypedDict):
    postgre_dsn: str
    testing_postgre_dsn: str

    redis_dsn: str
    testing_redis_dsn: str


class Ids(TypedDict):
    owner_id: int
    bot_id: int
    poketwo_id: int
    mudae_id: int
    join_logs_id: int


class Keys(TypedDict):
    fishie_api: str
    lastfm: str
    lastfm_secret: str
    google: List[str]
    google_id: str
    spotify_id: str
    spotify_secret: str


class ConfigTokens(TypedDict):
    bot: str
    testing_bot: str


class Config(TypedDict):
    tokens: ConfigTokens
    keys: Keys
    databases: Databases
    twitter: Twitter
    ids: Ids
    webhooks: Webhooks
