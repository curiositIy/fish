from __future__ import annotations

from typing import TYPE_CHECKING, List, Literal, Optional, Union

import discord
from discord.abc import Messageable
from discord.ext import commands

from core import Cog
from utils import fish_owner, greenTick, AllMsgbleChannels

if TYPE_CHECKING:
    from core import Fishie
    from extensions.context import Context


class Owner(Cog):
    emoji = fish_owner
    hidden: bool = True

    def __init__(self, bot: Fishie):
        super().__init__()
        self.bot = bot

    async def _add_reaction(self, ctx: Context, msg: discord.Message):
        try:
            await ctx.message.add_reaction(greenTick)
        except:
            pass

    @commands.command(name="reply")
    async def reply(
        self,
        ctx: Context,
        message: Union[str, int],
        channel: Optional[Messageable] = None,
        *,
        text: str,
    ):
        """Reply to a message"""
        _message = await ctx.bot.fetch_message(message=message, channel=channel)

        await _message.reply(text)

        await self._add_reaction(ctx, ctx.message)

    @commands.command(name="message", aliases=("send", "msg", "dm"))
    async def message(
        self,
        ctx: Context,
        channel: Optional[Union[AllMsgbleChannels, discord.User]] = None,
        *,
        text: str,
    ):
        """Send a message"""
        channel = channel or ctx.channel # type: ignore
        await channel.send(text, allowed_mentions=discord.AllowedMentions.all()) # type: ignore

        await self._add_reaction(ctx, ctx.message)

    @commands.command(name="test")
    async def test(self, ctx: Context, user: discord.User = commands.Author): ...

    async def cog_check(self, ctx: commands.Context[Fishie]) -> bool:
        if await ctx.bot.is_owner(ctx.author):
            return True

        raise commands.BadArgument("You are not allowed to use this command.")


async def setup(bot: Fishie):
    await bot.add_cog(Owner(bot))
