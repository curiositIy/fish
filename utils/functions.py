from __future__ import annotations

import asyncio
import json
import logging
import math
import re
import sys
import textwrap
from io import BytesIO
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    List,
    Literal,
    Optional,
    Sequence,
    Tuple,
    Union,
)

import aiohttp
import asyncpg
import discord
import pandas as pd
from aiohttp import ClientResponse
from discord.ext import commands
from PIL import Image, ImageSequence

from .types import P, T
from .vars import USER_FLAGS

if TYPE_CHECKING:
    from core import Fishie


def to_thread(func: Callable[P, T]) -> Callable[P, Awaitable[T]]:
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        return await asyncio.to_thread(func, *args, **kwargs)

    return wrapper


async def create_pool(connection_url: str) -> "asyncpg.Pool[asyncpg.Record]":
    def _encode_jsonb(value: Any) -> Any:
        return json.dumps(value)

    def _decode_jsonb(value: Any) -> Any:
        return json.loads(value)

    async def init(con: "asyncpg.Connection[Any]"):
        await con.set_type_codec(
            "jsonb",
            schema="pg_catalog",
            encoder=_encode_jsonb,
            decoder=_decode_jsonb,
            format="text",
        )

    connection = await asyncpg.create_pool(connection_url, init=init)

    if connection is None:
        raise Exception("Failed to connect to database")

    return connection


def format_name(user: Union[discord.User, discord.Member]) -> str:
    emoji = USER_FLAGS.get(user.id)
    emoji = f"{emoji} " if emoji else ""
    return f"{emoji}{user}"


def human_join(seq: Sequence[str], delim=", ", final="or", spaces: bool = True) -> str:
    size = len(seq)
    if size == 0:
        return ""

    if size == 1:
        return seq[0]

    if size == 2:
        return f"{seq[0]} {final} {seq[1]}"

    final = f" {final} " if spaces else final
    return delim.join(seq[:-1]) + f"{final}{seq[-1]}"


def response_checker(response: ClientResponse) -> bool:
    if response.status == 200:
        return True

    bad_response = {
        502: "The server is down or under maintenance, try again later.",
        404: "The requested resource could not be found.",
        400: "The request was invalid.",
        401: "The request requires authentication.",
        403: "The request was forbidden.",
    }
    for br, reason in bad_response.items():
        if br == response:
            raise commands.BadArgument(reason)

    if str(response.status).startswith("5"):
        reason = (
            f"\nReason: {textwrap.shorten(response.reason, 100)}"
            if response.reason
            else ""
        )
        raise commands.BadArgument(
            f"The server returned an error ({response.status}). {reason}"
        )

    raise commands.BadArgument(
        f"Something went wrong, try again later? \nStatus code: `{response.status}`"
    )


async def get_sp_cover(bot: Fishie, query: str) -> Tuple[str, bool]:
    results = bot.cached_covers.get(query)

    if results:
        return results

    if bot.spotify_key is None:
        raise commands.BadArgument(
            "Spotify key is not set yet, maybe spotify cog needs loaded?"
        )

    url = "https://api.spotify.com/v1/search"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {bot.spotify_key}",
    }

    data = {"q": query, "type": "album", "limit": "1"}

    async with bot.session.get(url, headers=headers, params=data) as r:
        results = await r.json()

    try:
        cover = results["albums"]["items"][0]["images"][0]["url"]
        nsfw = results["albums"]["items"][0]["id"] in bot.db_cache.nsfw_covers

        try:
            bot.cached_covers[query] = (cover, nsfw)
        except KeyError:
            pass

        return cover, nsfw
    except (IndexError, KeyError):
        raise commands.BadArgument("No cover found for this album, sorry.")


async def to_image(
    session: aiohttp.ClientSession,
    url: str,
    bytes: bool = False,
    skip_check: bool = False,
) -> BytesIO | bytes:
    async with session.get(url) as resp:
        if not skip_check:
            response_checker(resp)

        data = await resp.read()

        return data if bytes else BytesIO(data)


# https://github.com/CuteFwan/Koishi/blob/master/cogs/utils/images.py#L4-L34
def resize_to_limit(data: BytesIO, limit: int) -> BytesIO:
    """
    Downsize it for huge PIL images.
    Half the resolution until the byte count is within the limit.
    """
    current_size = data.getbuffer().nbytes
    while current_size > limit:
        with Image.open(data) as im:
            data = BytesIO()
            if im.format == "PNG":
                im = im.resize(tuple([i // 2 for i in im.size]), resample=Image.BICUBIC)  # type: ignore
                im.save(data, "png")
            elif im.format == "GIF":
                durations = []
                new_frames = []
                for frame in ImageSequence.Iterator(im):
                    durations.append(frame.info["duration"])
                    new_frames.append(
                        frame.resize([i // 2 for i in im.size], resample=Image.BICUBIC)  # type: ignore
                    )
                new_frames[0].save(
                    data,
                    save_all=True,
                    append_images=new_frames[1:],
                    format="gif",
                    version=im.info["version"],
                    duration=durations,
                    loop=0,
                    transparency=0,
                    background=im.info["background"],
                    palette=im.getpalette(),
                )
            data.seek(0)
            current_size = data.getbuffer().nbytes
    return data


# https://github.com/CuteFwan/Koishi/blob/master/cogs/avatar.py#L82-L102
@to_thread
def format_bytes(filesize_limit: int, images: List[bytes]) -> BytesIO:
    xbound = math.ceil(math.sqrt(len(images)))
    ybound = math.ceil(len(images) / xbound)
    size = int(2520 / xbound)

    with Image.new(
        "RGBA", size=(xbound * size, ybound * size), color=(0, 0, 0, 0)
    ) as base:
        x, y = 0, 0
        for avy in images:
            if avy:
                im = Image.open(BytesIO(avy)).resize(
                    (size, size), resample=Image.BICUBIC
                )
                base.paste(im, box=(x * size, y * size))
            if x < xbound - 1:
                x += 1
            else:
                x = 0
                y += 1
        buffer = BytesIO()
        base.save(buffer, "png")
        buffer.seek(0)
        buffer = resize_to_limit(buffer, filesize_limit)
        return buffer


def format_status(member: discord.Member) -> str:
    return f'{"on " if member.status is discord.Status.dnd else ""}{member.raw_status}'


@to_thread
def update_pokemon(bot: Fishie):
    url = "https://raw.githubusercontent.com/poketwo/data/master/csv/pokemon.csv"
    data = pd.read_csv(url)
    pokemon = [str(p).lower() for p in data["name.en"]]

    bot.pokemon = pokemon


async def get_or_fetch_user(bot: Fishie, user_id: int) -> discord.User:
    user = bot.get_user(user_id)

    if user is None:
        user = await bot.fetch_user(user_id)

    return user


async def get_or_fetch_member(
    guild: discord.Guild, member_id: int
) -> Optional[discord.Member]:
    member = guild.get_member(member_id)
    if member is not None:
        return member

    members = await guild.query_members(limit=1, user_ids=[member_id], cache=True)
    if not members:
        return None

    return members[0]


def natural_size(size_in_bytes: int) -> str:
    """
    Converts a number of bytes to an appropriately-scaled unit
    E.g.:
        1024 -> 1.00 KiB
        12345678 -> 11.77 MiB
    """
    units = ("B", "KiB", "MiB", "GiB", "TiB", "PiB", "EiB", "ZiB", "YiB")

    power = int(math.log(max(abs(size_in_bytes), 1), 1024))

    return f"{size_in_bytes / (1024 ** power):.2f} {units[power]}"


async def run(cmd):
    logger = logging.getLogger("fishie")
    proc = await asyncio.create_subprocess_shell(
        cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )

    stdout, stderr = await proc.communicate()

    logger.info(f"[{cmd!r} exited with {proc.returncode}]")
    if stdout:
        logger.info(f"[stdout]\n{stdout.decode()}")
    if stderr:
        logger.error(f"[stderr]\n{stderr.decode()}")


async def identify_mobile(self) -> None:
    """Sends the IDENTIFY packet."""
    payload = {
        "op": self.IDENTIFY,
        "d": {
            "token": self.token,
            "properties": {
                "os": sys.platform,
                "browser": "discord iOS",
                "device": "discord.py",
            },
            "compress": True,
            "large_threshold": 250,
        },
    }

    if self.shard_id is not None and self.shard_count is not None:
        payload["d"]["shard"] = [self.shard_id, self.shard_count]

    state = self._connection
    if state._activity is not None or state._status is not None:
        payload["d"]["presence"] = {
            "status": state._status,
            "game": state._activity,
            "since": 0,
            "afk": False,
        }

    if state._intents is not None:
        payload["d"]["intents"] = state._intents.value

    await self.call_hooks(
        "before_identify", self.shard_id, initial=self._initial_identify
    )
    await self.send_as_json(payload)


async def litterbox(
    session: aiohttp.ClientSession,
    file: bytes,
    filename: str,
    time: Union[
        Literal["1h"], Literal["12h"], Literal["12h"], Literal["24h"], Literal["72h"]
    ] = "72h",
) -> str:
    data = aiohttp.FormData()
    data.add_field(
        "fileToUpload", file, filename=filename, content_type="application/octet-stream"
    )
    data.add_field("reqtype", "fileupload")
    data.add_field("time", time)

    async with session.post(
        "https://litterbox.catbox.moe/resources/internals/api.php", data=data
    ) as resp:
        if resp.status != 200:
            raise commands.CommandError(f"File too large.")

        return await resp.text()


def capitalize_text(text):
    text = text.capitalize()

    pattern = r"(?<=[.!?])\s+(.)"

    def capitalize_match(match):
        return match.group(0).upper()

    capitalized_text = re.sub(pattern, capitalize_match, text)

    return capitalized_text
