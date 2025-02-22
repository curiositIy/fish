from __future__ import annotations

import asyncio
from io import BytesIO
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import discord
from discord.ext import commands
from discord.utils import escape_markdown
from playwright.async_api import async_playwright
from discord import app_commands
from extensions.context import Context
from utils import (
    Pager,
    SimplePages,
    TenorUrlConverter,
    UrbanPageSource,
    URLConverter,
    get_or_fetch_user,
    AuthorView,
)
from utils.emojis import user, fish_trash, fish_check

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


value_formatter = {
    "osu": "OSU",
    "lastfm": "Last.fm",
    "steam": "Steam",
    "roblox": "Roblox",
    "genshin": "Genshin",
}


class AccountLinking(discord.ui.Modal, title="Account linking"):

    def __init__(self, ctx: Context, data: Dict[str, str], embed: discord.Embed):
        super().__init__()
        self.ctx = ctx
        self.data = data
        self.embed = embed

        for name, value in self.data.items():
            if name == "user_id":
                continue

            self.add_item(
                item=discord.ui.TextInput(
                    label=value_formatter[name],
                    default=value,
                    placeholder=f"Enter your {value_formatter[name]} Username/ID here.",
                    required=False,
                )
            )

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        self.ctx.bot.logger.info(
            f'View {self} errored by {self.ctx.author}. Full content: "{self.ctx.message.content}"'
        )
        await self.ctx.bot.log_error(error)

        try:
            await interaction.response.send_message(str(error), ephemeral=True)
        except discord.InteractionResponded:
            await interaction.followup.send(content=str(error), ephemeral=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message(str(self.children))


class AccountsView(AuthorView):
    def __init__(self, ctx: Context, data: Dict[Any, Any], embed: discord.Embed):
        super().__init__(ctx)
        self.ctx = ctx
        self.data = data
        self.embed = embed

    @discord.ui.button(emoji=user, style=discord.ButtonStyle.green)
    async def open(self, interaction: discord.Interaction, __):
        await interaction.response.send_modal(
            AccountLinking(self.ctx, self.data, self.embed)
        )

    @discord.ui.button(emoji=fish_trash, style=discord.ButtonStyle.red)
    async def delete(self, interaction: discord.Interaction, __):
        await interaction.response.defer()
        await interaction.delete_original_response()
        await self.ctx.message.add_reaction(fish_check)
        self.stop()


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

    @commands.hybrid_command(name="leaderboard", aliases=("lb",))
    async def leaderboard(self, ctx: Context):
        """Check the global XP leaderboard"""
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

    @commands.hybrid_command(name="accounts")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def accounts_group(self, ctx: Context):
        """Shows your accounts connected to the bot, also connect some if you want."""
        sql = """SELECT * FROM accounts WHERE user_id = $1"""

        results = await self.bot.pool.fetchrow(sql, ctx.author.id)  # type: ignore

        if not bool(results):
            sql = await self.bot.pool.fetchrow(
                "INSERT INTO accounts (user_id) VALUES ($1)"
            )
            results = await self.bot.pool.fetchrow(sql, ctx.author.id)  # type: ignore

        results: Dict[Any, Any] = dict(results)  # type: ignore

        embed = discord.Embed(color=self.bot.embedcolor)
        embed.set_author(
            name=f"{ctx.author}'s linked accounts",
            icon_url=ctx.author.display_avatar.url,
        )
        for key, value in results.items():
            if key == "user_id":
                continue
            embed.add_field(
                name=value_formatter[key],
                value=f"`{value or 'Set with button below.'}`",
                inline=False,
            )

        embed.set_footer(text="To add or remove accounts please click the button below")
        await ctx.send(embed=embed, view=AccountsView(ctx, results, embed))


async def setup(bot: Fishie):
    await bot.add_cog(Tools(bot))
