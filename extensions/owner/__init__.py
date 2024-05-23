from __future__ import annotations

import json
from typing import TYPE_CHECKING, Optional, Union

import discord
from discord.abc import Messageable
from discord.ext import commands

from core import Cog
from utils import fish_owner, greenTick
from io import BytesIO

if TYPE_CHECKING:
    from core import Fishie


class Owner(Cog):
    emoji = fish_owner
    hidden: bool = True

    def __init__(self, bot: Fishie):
        super().__init__()
        self.bot = bot

    @commands.command(name="reply")
    async def reply(
        self,
        ctx: commands.Context[Fishie],
        message: Union[str, int],
        channel: Optional[Messageable] = None,
        *,
        text: str,
    ):
        """Reply to a message"""
        _message = await ctx.bot.fetch_message(message=message, channel=channel)

        await _message.reply(text)

        await ctx.message.add_reaction(greenTick)

    @commands.command(name="message", aliases=("send", "msg", "dm"))
    async def message(
        self,
        ctx: commands.Context[Fishie],
        channel: Optional[Union[Messageable, discord.User]] = commands.CurrentChannel,
        *,
        text: str,
    ):
        """Send a message"""
        channel = channel or ctx.channel
        await channel.send(text)

        await ctx.message.add_reaction(greenTick)

    @commands.command(name="test")
    async def test(self, ctx: commands.Context[Fishie], url: str):
        headers = {"Accept": "application/json", "Content-Type": "application/json"}

        data = {"url": url}

        s = await self.bot.session.post(
            headers=headers, url="https://co.wuk.sh/api/json", json=data
        )
        data = await s.json()

        await ctx.send(file=self.bot.too_big(json.dumps(data, indent=4)))

        # async with self.bot.session.get(url=data["url"]) as body:
        #    data = await body.read()
        #    await ctx.send(file=discord.File(BytesIO(data), filename="temp.mp4"))

    async def cog_check(self, ctx: commands.Context[Fishie]) -> bool:
        if await ctx.bot.is_owner(ctx.author):
            return True

        raise commands.BadArgument("You are not allowed to use this command.")


async def setup(bot: Fishie):
    await bot.add_cog(Owner(bot))
