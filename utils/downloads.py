from __future__ import annotations

import json
import os
import secrets
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import discord
import yt_dlp

from .errors import DownloadError, InvalidWebsite, VideoIsLive
from .functions import to_thread, run, litterbox, capitalize_text
from .regexes import (
    SOUNDCLOUD_RE,
    TIKTOK_RE,
    TWITTER_RE,
    VIDEOS_RE,
    INSTAGRAM_RE,
    YOUTUBE_RE,
    YT_SHORT_RE,
    YT_CLIP_RE,
    REDDIT_RE,
)
from io import BytesIO, BufferedReader

if TYPE_CHECKING:
    from core import Context


def match_filter(info: Dict[Any, Any]):
    if info.get("live_status", None) == "is_live":
        raise VideoIsLive()


def cobalt_checker(url: str) -> bool:
    if (
        TIKTOK_RE.search(url)
        or YT_SHORT_RE.search(url)
        or YOUTUBE_RE.search(url)
        or TWITTER_RE.search(url)
        or REDDIT_RE.search(url)
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
        hidden: Optional[bool] = False,
    ) -> None:
        self.ctx = ctx
        self.url = url
        self.format = format
        self.twitterGif = twitterGif
        self.picker = picker
        self.filename = filename
        self.hidden = hidden
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
        if YT_CLIP_RE.search(self.url):
            raise DownloadError("Youtube clips are not supported at the moment, sorry.")

        if cobalt_checker(self.url):
            s = await self.ctx.session.post(
                headers=self.headers,
                url="https://api.cobalt.tools/api/json",
                json=self.json_data,
            )
            data: Dict[Any, Any] = await s.json()

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
                _id = secrets.token_urlsafe(5)

                await err_chan.send(
                    f"<@766953372309127168> | <{self.url}> | {_id}",
                    file=self.ctx.too_big(json.dumps(data, indent=4)),
                    allowed_mentions=discord.AllowedMentions.all(),
                )
                await self.ctx.bot.log_error(error=err)
                _err = data.get(
                    "error",
                    "Something went wrong, this was sent to the developers, sorry.",
                )
                raise DownloadError(f"{capitalize_text(_err)} Error ID: `{_id}`")
        else:
            file = await self.yt_dlp_download()

        return file

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
            self.format = "mp3"
            audio = True

        # if TWITTER_RE.search(video):
        #     options["cookies"] = r"files/cookies/twitter-cookies.txt"
        #     options["postprocessors"] = [
        #         {
        #             "key": "Exec",
        #             "exec_cmd": [
        #                 "mv %(filename)q %(filename)q.temp",
        #                 "ffmpeg -y -i %(filename)q.temp -c copy -map 0 -brand mp42 %(filename)q",
        #                 "rm %(filename)q.temp",
        #             ],
        #             "when": "after_move",
        #         }
        #     ]
        #     video = re.sub("x.com", "twitter.com", video, count=1)

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
            options["format"] = f"bestvideo+bestaudio[ext={self.format}]/best"

        with yt_dlp.YoutubeDL(options) as ydl:
            try:
                ydl.download(video)
                self.ctx.bot.current_downloads.append(f"{self.filename}.{self.format}")
            except ValueError as e:
                raise DownloadError(str(e))

        return discord.File(
            f"files/downloads/{self.filename}.{self.format}",
            filename=f"{self.filename}.{self.format}",
        )

    async def manual_dl(self, cookies: Optional[str]) -> discord.File:
        """Manually runs the yt-dlp command line download.

        Cookies should be a path to the cookies"""
        cmd = f"venv/bin/yt-dlp {self.url} "
        if cookies:
            cmd += f"--cookies {cookies} "
        cmd += f"--format bestvideo+bestaudio[ext={self.format}]/best "
        cmd += f'-o "{self.filename}.%(ext)s" '
        cmd += '-P "files/downloads"'

        self.ctx.bot.logger.warn(cmd)

        await run(cmd)
        self.ctx.bot.current_downloads.append(f"{self.filename}.{self.format}")

        return discord.File(
            f"files/downloads/{self.filename}.{self.format}",
            filename=f"{self.filename}.{self.format}",
        )

    async def download(self):
        files: List[discord.File] = []

        if INSTAGRAM_RE.search(self.url):
            files.append(
                await self.manual_dl(cookies="files/cookies/instagram-cookies.txt")
            )

        elif TWITTER_RE.search(self.url):
            s = await self.ctx.session.post(
                headers=self.headers,
                url="https://api.cobalt.tools/api/json",
                json=self.json_data,
            )
            data: Dict[Any, Any] = await s.json()
            if data.get("status") == "picker":
                MVD = await self.ctx.send("Multiple videos detected, downloading.")
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
                    await MVD.delete()

            else:
                files.append(await self._download())
        else:
            files.append(await self._download())
        try:

            await self.ctx.send(
                files=files,
                mention_author=True,
                reference=self.ctx.message.to_reference(fail_if_not_exists=False),
                ephemeral=self.hidden,
            )
        except discord.HTTPException:
            text = "Files were too big, try a smaller video. **These will delete after 72 hours**\n\n"
            for file in files:
                bytes = await self.file_to_bytes(file)
                url = await litterbox(self.ctx.session, bytes, file.filename)
                text += f"{url}\n"

            await self.ctx.send(text, ephemeral=self.hidden)

        for file in files:

            try:
                await run(f"cd files/downloads && rm {file.filename}")
            except:
                pass

    @to_thread
    def file_to_bytes(self, file: discord.File) -> bytes:
        fp: BufferedReader | BytesIO = file.fp  # type: ignore

        if isinstance(fp, os.PathLike):
            with open(fp.name, "rb") as f:
                return f.read()
        else:
            return fp.read()
