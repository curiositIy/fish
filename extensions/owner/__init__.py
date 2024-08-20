from __future__ import annotations

import json
from typing import TYPE_CHECKING, List, Optional, Union

import discord
from discord.abc import Messageable
from discord.ext import commands

from core import Cog
from utils import fish_owner, greenTick, ReviewsPageSource, Review, ReviewSender, Pager

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
        channel: Optional[Union[Messageable, discord.User]] = commands.CurrentChannel,
        *,
        text: str,
    ):
        """Send a message"""
        channel = channel or ctx.channel
        await channel.send(text, allowed_mentions=discord.AllowedMentions.all())

        await self._add_reaction(ctx, ctx.message)

    @commands.command(name="test")
    async def test(self, ctx: Context, user: discord.User = commands.Author):
        async with ctx.session.get(
            f"https://manti.vendicated.dev/api/reviewdb/users/{user.id}/reviews"
        ) as resp:
            json = await resp.json()

        data: List[Review] = [
            Review(
                id=r["id"],
                sender=ReviewSender(
                    user_id=r["sender"]["discordID"],
                    profilePhoto=r["sender"]["profilePhoto"],
                    username=r["sender"]["username"],
                ),
                comment=r["comment"],
                timestamp=r["timestamp"],
                target_id=user.id,
            )
            for r in json["reviews"][1:]
        ]

        source = ReviewsPageSource(entries=data)
        source.embed.title = f"Review for {user.display_name} (via ReviewDB)"
        pager = Pager(source, ctx=ctx)
        await pager.start(ctx)

    async def cog_check(self, ctx: commands.Context[Fishie]) -> bool:
        if await ctx.bot.is_owner(ctx.author):
            return True

        raise commands.BadArgument("You are not allowed to use this command.")


async def setup(bot: Fishie):
    await bot.add_cog(Owner(bot))
