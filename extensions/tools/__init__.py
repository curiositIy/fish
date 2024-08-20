from __future__ import annotations

import asyncio
from io import BytesIO
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import discord
from discord.ext import commands
from discord.utils import escape_markdown
from playwright.async_api import async_playwright

from utils import (
    Pager,
    SimplePages,
    TenorUrlConverter,
    UrbanPageSource,
    URLConverter,
    get_or_fetch_user,
)

from .downloads import Downloads
from .google import Google
from .purge import PurgeCog
from .reminders import Reminder
from .spotify import Spotify

if TYPE_CHECKING:
    from core import Fishie
    from extensions.context import Context

param = commands.param


class ScreenshotFlags(commands.FlagConverter, delimiter=" ", prefix="-"):
    delay: int = commands.flag(default=0, aliases=["d"])
    full_page: bool = commands.flag(default=False, aliases=["fp"])


# class AccountLinking(discord.ui.Modal, title='Account linking'):

#     def __init__(self, ctx: Context, data: Dict[str, str]):
#         super().__init__()
#         self.ctx = ctx
#         self.data = data

#     lastfm = discord.ui.TextInput(
#         label='Last.fm',
#         default=data[""],
#         placeholder='Enter your Last.fm account name here...',
#     )

#     steam = discord.ui.TextInput(
#         label='Steam',
#         placeholder='Enter your steam profile URL here...',
#     )


#     roblox = discord.ui.TextInput(
#         label='Roblox',
#         placeholder='Your Roblox account name OR ID here...',
#     )

#     osu = discord.ui.TextInput(
#         label='OSU',
#         placeholder='Your OSU account name OR ID here...',
#     )

#     genshin = discord.ui.TextInput(
#         label='Genshin',
#         placeholder='Your Genshin account ID here...',
#     )

#     osu = discord.ui.TextInput(
#         label='OSU',
#         placeholder='Your OSU account name here...',
#     )

#     osu = discord.ui.TextInput(
#         label='OSU',
#         placeholder='Your OSU account name here...',
#     )

#     async def on_error(self, interaction: discord.Interaction, error: Exception):
#         self.ctx.bot.logger.info(
#             f'View {self} errored by {self.ctx.author}. Full content: "{self.ctx.message.content}"'
#         )
#         await self.ctx.bot.log_error(error)

#         try:
#             await interaction.response.send_message(str(error), ephemeral=True)
#         except discord.InteractionResponded:
#             await interaction.followup.send(content=str(error), ephemeral=True)


class Tools(Downloads, Reminder, Google, Spotify, PurgeCog):
    """Quality of life tools"""

    emoji = discord.PartialEmoji(name="\U0001f6e0")

    @commands.command(name="screenshot", aliases=("ss",))
    async def screenshot(
        self,
        ctx: Context,
        website: str = param(description="The website's url.", converter=URLConverter),
        *,
        flags: ScreenshotFlags = param(
            description="Flags to use while screenshotting."
        ),
    ):
        """Screenshot a website from the internet"""
        async with ctx.typing():
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch()
                page = await browser.new_page(locale="en-US")
                await page.goto(website)
                await asyncio.sleep(flags.delay)
                file = discord.File(
                    BytesIO(
                        await page.screenshot(
                            type="png", timeout=15 * 1000, full_page=flags.full_page
                        )
                    ),
                    filename="screenshot.png",
                )

        await ctx.send(file=file)

    @commands.command(name="tenor")
    async def tenor(self, ctx: commands.Context, url: TenorUrlConverter):
        """Gets the actual gif URL from a tenor link"""

        await ctx.send(f"Here is the real URL: {url}")

    @commands.command(name="urban")
    async def urban(self, ctx: Context, *, word: str):
        """Search for a word on urban

        Warning: could be NSFW"""

        url = "https://api.urbandictionary.com/v0/define"

        async with ctx.session.get(url, params={"term": word}) as resp:
            json = await resp.json()
            data: List[Dict[Any, Any]] = json.get("list", [])

            if not data:
                raise commands.BadArgument("Nothing was found for this phrase.")

        p = UrbanPageSource(data, per_page=4)
        menu = Pager(p, ctx=ctx)
        await menu.start(ctx)

    @commands.hybrid_command(name="xp")
    async def xp(self, ctx: Context, *, user: discord.User = commands.Author):
        """Check the XP you have."""
        xp: Optional[int] = await self.bot.pool.fetchval(
            "SELECT xp FROM message_xp WHERE user_id = $1", user.id
        )

        if not bool(xp):
            raise commands.BadArgument("This user has no recorded XP")

        await ctx.send(f"{user} has {xp:,} XP")

    async def lb_name(self, user_id: int) -> discord.User | int:
        try:
            return await get_or_fetch_user(self.bot, user_id)
        except:
            return user_id

    @commands.hybrid_command(name="rank", aliases=("leaderboard", "lb"))
    async def rank(self, ctx: Context):
        """Check your global rank"""
        xp = await self.bot.pool.fetch(
            "SELECT user_id, xp FROM message_xp ORDER BY xp DESC LIMIT 100",
        )

        if not bool(xp):
            raise commands.BadArgument("No data found")

        data: Data[int, int] = dict(xp)  # type: ignore

        data = [
            escape_markdown(f"{await self.lb_name(user_id)}: {xp:,}")
            for user_id, xp in data.items()
        ]
        pages = SimplePages(entries=data, per_page=10, ctx=ctx)
        pages.embed.title = f"Gloabl ranks"
        await pages.start(ctx)

    # @commands.hybrid_group(name="accounts", fallback="list")
    # async def accounts_group(self, ctx: Context):
    #     sql = """SELECT * FROM accounts WHERE user_id = $1"""

    #     results = await self.bot.pool.fetchrow(sql, ctx.author.id)

    #     if not bool(results):
    #         ...

    #     results = dict(results) # type: ignore

    #     embed = discord.Embed(color=self.bot.embedcolor)
    #     embed.set_author(name=f"{ctx.author}'s linked accounts", icon_url=ctx.author.display_avatar.url)
    #     for key, value in results.items():
    #         if key == "user_id":
    #             continue
    #         embed.add_field(name=key.capitalize(), value=f"`{value}`", inline=False)

    #     embed.set_footer(text="To add or remove accounts please run the command 'accounts link'")
    #     await ctx.send(embed=embed)

    # @accounts_group.command(name="link")
    # async def accounts_link(self, ctx: Context):
    #     """Opens up a menu to add or remove some accounts."""
    #     sql = """SELECT * FROM accounts WHERE user_id = $1"""

    #     results = await self.bot.pool.fetchrow(sql, ctx.author.id) # type: ignore

    #     results: Dict[Any, Any] = dict(results) # type: ignore

    #     if ctx.interaction:
    #         await ctx.interaction.response.send_modal(AccountLinking(ctx, results))


async def setup(bot: Fishie):
    await bot.add_cog(Tools(bot))
