from __future__ import annotations

import asyncio
import random
from io import BytesIO
from typing import TYPE_CHECKING, Optional

import asyncpg
import discord
from discord.ext import commands

from core import Cog
from utils import resize_to_limit

if TYPE_CHECKING:
    from core import Fishie
    from extensions.context import Context


class Avatars(Cog):
    async def add_avatar(
        self,
        user: discord.User | discord.Member,
        asset: discord.Asset,
        guild_id: Optional[int] = None,
    ):
        webhook = discord.Webhook.from_url(
            random.choice(self.bot.config["webhooks"]["images"]),
            session=self.bot.session,
        )
        try:
            image = await asyncio.to_thread(
                resize_to_limit, BytesIO(await asset.read()), 8388608
            )

            message = await webhook.send(
                f"{user.mention} | {user} | {user.id} | {discord.utils.format_dt(discord.utils.utcnow())}",
                file=discord.File(
                    image,
                    filename=f"{user.id}_{asset.key}.{['png', 'gif'][asset.is_animated()]}",
                ),
                wait=True,
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except discord.HTTPException as e:
            raise commands.BadArgument(str(e))

        sql = (
            """
        INSERT INTO guild_avatars(member_id, guild_id, avatar_key, created_at, avatar)
        VALUES($1, $2, $3, $4, $5)"""
            if guild_id
            else """
        INSERT INTO avatars(user_id, avatar_key, created_at, avatar)
        VALUES($1, $2, $3, $4)
        """
        )
        args = (
            (
                user.id,
                guild_id,
                asset.key,
                discord.utils.utcnow(),
                message.attachments[0].url,
            )
            if guild_id
            else (
                user.id,
                asset.key,
                discord.utils.utcnow(),
                message.attachments[0].url,
            )
        )

        try:
            await self.bot.pool.execute(sql, *args)
        except asyncpg.UniqueViolationError:
            pass

    @commands.Cog.listener("on_user_update")
    async def user_update(self, before_u: discord.User, after_u: discord.User):
        if before_u.display_avatar.key == after_u.display_avatar.key:
            return

        if "avatar" in self.bot.db_cache.get_opted_out(after_u.id):
            return

        await self.add_avatar(after_u, after_u.display_avatar)

    @commands.Cog.listener("on_member_update")
    async def member_update(self, before_m: discord.Member, after_m: discord.Member):
        if after_m.guild_avatar is None:
            return

        if before_m.display_avatar.key == after_m.display_avatar.key:
            return

        if "avatar" in self.bot.db_cache.get_opted_out(after_m.id):
            return

        await self.add_avatar(before_m, after_m.display_avatar, after_m.guild.id)
