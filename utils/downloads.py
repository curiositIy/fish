from __future__ import annotations

import json
import re
import secrets
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import discord
import yt_dlp

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


class Downloader:
    def __init__(
        self,
        ctx: Context,
        url: str,
        format: str = "mp4",
        twitterGif: Optional[bool] = True,
        picker: Optional[bool] = False,
        filename: Optional[str] = secrets.token_urlsafe(8).strip("-"),
    ) -> None:
        self.ctx = ctx
        self.url = url
        self.format = format
        self.twitterGif = twitterGif
        self.picker = picker
        self.filename = filename
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        self.json_data = {
            "url": self.url,
            "vQuality": "max",
            "isAudioOnly": format == "mp3",
            "vCodec": "h264",
            "twitterGif": self.twitterGif,
        }

    async def _download(self) -> discord.File:
        if cobalt_checker(self.url):

            s = await self.ctx.session.post(
                headers=self.headers,
                url="https://api.cobalt.tools/api/json",
                json=self.json_data,
            )
            data = await s.json()
            if data["status"] == "picker":
                raise DownloadError(
                    "Twitter posts with multiple media are not downloadable right now, this should be fixed very soon. If you want updates, join the [discord](<https://discord.gg/rM9u4MRFBE>) server."
                )
            try:
                # await ctx.send(file=bot.too_big(json.dumps(data, indent=4))) # debug
                async with self.ctx.session.get(url=data["url"]) as body:
                    bData = await body.read()

                if TWITTER_RE.search(self.url) and data["status"] == "stream":
                    self.format = "gif"

                file = discord.File(
                    BytesIO(bData), filename=f"{self.filename}.{self.format}"
                )

            except Exception as err:
                err_chan: discord.TextChannel = self.ctx.bot.get_channel(989112775487922237)  # type: ignore
                await err_chan.send(
                    "<@766953372309127168>",
                    file=self.ctx.too_big(json.dumps(data, indent=4)),
                    allowed_mentions=discord.AllowedMentions.all(),
                )
                await self.ctx.bot.log_error(error=err)
                raise DownloadError(
                    "Something went wrong, this was sent to the developers, sorry."
                )
        else:
            file = await self.yt_dlp_download()

        return file

    async def download(self):
        files: List[discord.File] = []

        if TWITTER_RE.search(self.url):
            s = await self.ctx.session.post(
                headers=self.headers,
                url="https://api.cobalt.tools/api/json",
                json=self.json_data,
            )
            data: Dict[Any, Any] = await s.json()
            if data.get("status") == "picker":
                for pd in data["picker"]:
                    tempformat = "mp4"

                    if pd["type"] == "photo":
                        continue

                    if pd["type"] == "gif":
                        tempformat = "gif"

                    async with self.ctx.session.get(url=pd["url"]) as body:
                        bData = await body.read()

                    files.append(
                        discord.File(
                            BytesIO(bData), filename=f"{self.filename}.{tempformat}"
                        )
                    )

            else:
                files.append(await self._download())
        else:
            files.append(await self._download())

        await self.ctx.send(
            files=files,
            mention_author=True,
            reference=self.ctx.message.to_reference(fail_if_not_exists=False),
        )

        for file in files:
            try:
                await run(f"cd files/downloads && rm {file.filename}")
            except:
                pass

    @to_thread
    def yt_dlp_download(self) -> discord.File:
        video_match = VIDEOS_RE.search(self.url)
        audio = False

        if video_match is None or video_match and video_match.group(0) == "":
            raise InvalidWebsite()

        video = video_match.group(0)

        options: Dict[Any, Any] = {
            "outtmpl": rf"files/downloads/{self.filename}.%(ext)s",
            "quiet": True,
            "max_filesize": 100_000_000,
            "match_filter": match_filter,
        }

        if SOUNDCLOUD_RE.search(video) or self.format == "mp3":
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
                self.ctx.bot.current_downloads.append(f"{self.filename}.{self.format}")
            except ValueError as e:
                raise DownloadError(str(e))

        return discord.File(f"files/downloads/{self.filename}", filename=self.filename)
