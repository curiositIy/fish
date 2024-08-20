from __future__ import annotations

import json
import re
import secrets
from typing import TYPE_CHECKING, Any, Dict, Optional

import discord
import yt_dlp
from discord.ext import commands

from .errors import DownloadError, InvalidWebsite, VideoIsLive
from .functions import to_thread, run
from .regexes import (
    SOUNDCLOUD_RE,
    TIKTOK_RE,
    TWITTER_RE,
    VIDEOS_RE,
    INSTAGRAM_RE,
    YOUTUBE_RE,
    YT_SHORT_RE,
    YT_CLIP_RE,
)
from io import BytesIO

if TYPE_CHECKING:
    from core import Fishie
    from core import Context


def match_filter(info: Dict[Any, Any]):
    if info.get("live_status", None) == "is_live":
        raise VideoIsLive()


def cobalt_checker(url: str) -> bool:
    if (
        TIKTOK_RE.search(url)
        or INSTAGRAM_RE.search(url)
        or YT_SHORT_RE.search(url)
        or YT_CLIP_RE.search(url)
        or YOUTUBE_RE.search(url)
        or TWITTER_RE.search(url)
    ):
        return True
    else:
        return False


async def download(
    ctx: Context,
    url: str,
    format: str = "mp4",
    bot: Optional[Fishie] = None,
    twitterGif: Optional[bool] = True,
):
    name = secrets.token_urlsafe(8).strip("-")

    if cobalt_checker(url):
        if not bot:
            raise commands.BadArgument("Bot was not supplied, command cannot run.")

        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        data = {
            "url": url,
            "vQuality": "max",
            "isAudioOnly": format == "mp3",
            "vCodec": "h264",
            "twitterGif": twitterGif,
        }
        s = await bot.session.post(
            headers=headers, url="https://api.cobalt.tools/api/json", json=data
        )
        data = await s.json()
        try:
            # await ctx.send(file=bot.too_big(json.dumps(data, indent=4))) # debug
            async with bot.session.get(url=data["url"]) as body:
                rData = await body.read()

                if TWITTER_RE.search(url) and data["status"] == "stream":
                    format = "gif"

                file = discord.File(BytesIO(rData), filename=f"{name}.{format}")
        except:
            err_chan: discord.TextChannel = bot.get_channel(989112775487922237)  # type: ignore
            await err_chan.send(
                "<@766953372309127168>",
                file=bot.too_big(json.dumps(data, indent=4)),
                allowed_mentions=discord.AllowedMentions.all(),
            )
            return await ctx.send(
                "Something went wrong, this was sent to the developers, sorry."
            )
    else:
        name = await yt_dlp_download(name=name, url=url, format=format, bot=bot)
        file = discord.File(f"files/downloads/{name}", filename=name)

    await ctx.send(file=file)

    try:
        await run(f"cd files/downloads && rm {name}.{format}")
    except:
        pass


@to_thread
def yt_dlp_download(
    name: str, url: str, format: str = "mp4", bot: Optional[Fishie] = None
):
    video_match = VIDEOS_RE.search(url)
    audio = False

    if video_match is None or video_match and video_match.group(0) == "":
        raise InvalidWebsite()

    video = video_match.group(0)

    options: Dict[Any, Any] = {
        "outtmpl": rf"files/downloads/{name}.%(ext)s",
        "quiet": True,
        "max_filesize": 100_000_000,
        "match_filter": match_filter,
    }

    if SOUNDCLOUD_RE.search(video) or format == "mp3":
        format = "mp3"
        audio = True

    if TWITTER_RE.search(video):
        options["cookies"] = r"twitter-cookies.txt"
        options["postprocessors"] = [
            {
                "key": "Exec",
                "exec_cmd": [
                    "mv %(filename)q %(filename)q.temp",
                    "ffmpeg -y -i %(filename)q.temp -c copy -map 0 -brand mp42 %(filename)q",
                    "rm %(filename)q.temp",
                ],
                "when": "after_move",
            }
        ]
        video = re.sub("x.com", "twitter.com", video, count=1)

    if audio:
        options.setdefault("postprocessors", []).append(
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": format,
                "preferredquality": "192",
            }
        )
        options["format"] = "bestaudio/best"
    else:
        options["format"] = f"bestvideo+bestaudio[ext={format}]/best"

    with yt_dlp.YoutubeDL(options) as ydl:
        try:
            ydl.download(video)
            if bot:
                bot.current_downloads.append(f"{name}.{format}")
        except ValueError as e:
            raise DownloadError(str(e))

    if bot:
        bot.logger.info(f"Downloaded video: {name}.{format}")

    return f"{name}.{format}"
