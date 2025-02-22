from __future__ import annotations

import discord
from discord.ext import commands

from core import Cog


class User(Cog):
    async def add_username(self, user: discord.User):
        sql = """
        INSERT INTO username_logs(user_id, username, created_at)
        VALUES ($1, $2, $3)
        """

        await self.bot.pool.execute(sql, user.id, user.name, discord.utils.utcnow())

    @commands.Cog.listener("on_user_update")
    async def username_update(self, before_u: discord.User, after_u: discord.User):
        if before_u.name == after_u.name:
            return

        if "username" in self.bot.db_cache.get_opted_out(after_u.id):
            return

        await self.add_username(after_u)

    async def add_display_name(self, user: discord.User):
        sql = """
        INSERT INTO display_name_logs(user_id, display_name, created_at)
        VALUES($1, $2, $3)
        """

        await self.bot.pool.execute(
            sql, user.id, user.display_name, discord.utils.utcnow()
        )

    @commands.Cog.listener("on_user_update")
    async def display_name_update(self, before_u: discord.User, after_u: discord.User):
        if before_u.display_name == after_u.display_name:
            return

        if "display" in self.bot.db_cache.get_opted_out(after_u.id):
            return

        await self.add_display_name(after_u)

    async def add_nickname(self, member: discord.Member):
        sql = """
        INSERT INTO nickname_logs(user_id, guild_id, nickname, created_at)
        VALUES($1, $2, $3, $4)
        """

        await self.bot.pool.execute(
            sql, member.id, member.guild.id, member.nick, discord.utils.utcnow()
        )

    @commands.Cog.listener("on_member_update")
    async def nickname_update(self, before_m: discord.Member, after_m: discord.Member):
        if before_m.nick == after_m.nick:
            return

        if not after_m.nick:
            return

        if "nickname" in self.bot.db_cache.get_opted_out(after_m.id):
            return

        await self.add_nickname(after_m)

    async def add_status(self, member: discord.Member):
        sql = """
        INSERT INTO status_logs(user_id, status_name, guild_id, created_at)
        VALUES($1, $2, $3, $4)
        """

        await self.bot.pool.execute(
            sql, member.id, member.status.name, member.guild.id, discord.utils.utcnow()
        )

    @commands.Cog.listener("on_presence_update")
    async def status_update(self, before_m: discord.Member, after_m: discord.Member):
        if before_m.status == after_m.status:
            return

        if "status" in self.bot.db_cache.get_opted_out(after_m.id):
            return

        await self.add_status(after_m)

    async def add_join(self, member: discord.Member):
        sql = """
        INSERT INTO member_join_logs(member_id, guild_id, time)
        VALUES($1, $2, $3)
        """

        await self.bot.pool.execute(
            sql, member.id, member.guild.id, discord.utils.utcnow()
        )

    @commands.Cog.listener("on_member_join")
    async def member_join_logs(self, member: discord.Member):
        if "joins" in self.bot.db_cache.get_opted_out(member.id):
            return

        await self.add_join(member)
