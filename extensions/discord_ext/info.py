from __future__ import annotations

import datetime
from collections import Counter
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Literal,
    Optional,
    Tuple,
    TypeAlias,
    Union,
)

import discord
from discord.ext import commands
from discord.interactions import Interaction

from core import Cog
from utils import (
    USER_FLAGS,
    AllChannels,
    AuthorView,
    fish_download,
    fish_edit,
    fish_go_back,
    human_join,
    reply,
    Review,
    ReviewsPageSource,
    ReviewSender,
    Pager,
)

if TYPE_CHECKING:
    from extensions.context import Context, GuildContext

statuses: TypeAlias = Union[
    Literal["online"], Literal["offline"], Literal["dnd"], Literal["idle"]
]

BURPLE = discord.ButtonStyle.blurple
GREEN = discord.ButtonStyle.green


class UserDropdown(discord.ui.Select):
    def __init__(
        self,
        ctx: Context,
        user: Union[discord.User, discord.Member],
        index_embed: discord.Embed,
        fetched_user: Optional[discord.User] = None,
    ):
        self.ctx = ctx
        self.user = user
        self.fetched_user = fetched_user
        self.index_embed = index_embed

        self.index_cache: Optional[discord.Embed] = None
        self.avatar_cache: Optional[discord.Embed] = None
        self.banner_cache: Optional[discord.Embed] = None
        self.bot_cache: Optional[discord.Embed] = None
        self.status_cache: Optional[discord.Embed] = None

        options = [
            discord.SelectOption(
                label="Index",
                description=f"Goes back to home page",
                emoji=discord.PartialEmoji(name="\U0001f3e0"),
                value="index",
            ),
            discord.SelectOption(
                label="Avatar",
                description=f"View {user}'s avatar",
                emoji=discord.PartialEmoji(name="\U0001f3a8"),
                value="avatar",
            ),
            discord.SelectOption(
                label="Reviews",
                description=f"View {user}'s reviews",
                emoji=discord.PartialEmoji(name="\U0001f4d4"),
                value="reviews",
            ),
        ]

        if fetched_user and fetched_user.banner:
            options.append(
                discord.SelectOption(
                    label="Banner",
                    description=f"View {user}'s banner",
                    emoji=discord.PartialEmoji(name="\U0001f3f3"),
                    value="banner",
                )
            )

        if isinstance(user, discord.Member):
            options.append(
                discord.SelectOption(
                    label="Statuses",
                    description=f"View {user}'s statuses",
                    emoji=discord.PartialEmoji(name="\U000023f3"),
                    value="status",
                )
            )

        if user.bot:
            options.append(
                discord.SelectOption(
                    label="Bot",
                    description=f"View {user}'s bot info",
                    emoji=discord.PartialEmoji(name="\U0001f916"),
                    value="bot",
                )
            )

        super().__init__(placeholder="Make a selection", options=options)

    async def index_response(self):
        return self.index_embed

    async def avatar_response(self) -> discord.Embed:
        if self.avatar_cache:
            return self.avatar_cache

        ctx = self.ctx
        user = self.user
        fuser = self.fetched_user or await ctx.bot.fetch_user(user.id)
        color = fuser.accent_color or ctx.bot.embedcolor

        avatars = [f"[Default]({user.default_avatar.url})"]

        if user.avatar:
            avatars.append(f"[Avatar]({user.avatar.url})")

        if isinstance(user, discord.Member) and user.guild_avatar:
            avatars.append(f"[Guild]({user.guild_avatar.url})")

        embed = discord.Embed(
            color=color, description=human_join([a for a in avatars], final="and")
        )
        embed.set_author(name=f"{user}'s avatars", icon_url=user.display_avatar.url)

        embed.set_footer(text=f"Run {ctx.get_prefix}avatar for more details.")

        embed.set_image(url=user.display_avatar.url)

        self.avatar_cache = embed
        return embed

    async def review_response(self, interaction: discord.Interaction) -> None:
        cog = self.ctx.bot.discord
        if cog:
            await cog.review_func(self.ctx, self.user, hidden=True)
        else:
            await interaction.response.send_message(
                content="Could not find any reviews.", ephemeral=True
            )

    async def banner_response(self) -> discord.Embed:
        if self.banner_cache:
            return self.banner_cache

        ctx = self.ctx
        user = self.user
        fuser = self.fetched_user or await ctx.bot.fetch_user(user.id)
        color = fuser.accent_color or ctx.bot.embedcolor

        embed = discord.Embed(color=color)
        embed.set_author(name=f"{user}'s banner", icon_url=user.display_avatar.url)
        assert fuser.banner

        embed.set_image(url=fuser.banner.url)

        self.banner_cache = embed
        return embed

    async def bot_response(self) -> discord.Embed:
        if self.bot_cache:
            return self.bot_cache

        ctx = self.ctx
        user = self.user
        fuser = self.fetched_user or await ctx.bot.fetch_user(user.id)
        color = fuser.accent_color or ctx.bot.embedcolor

        url = f"https://discord.com/api/v10/oauth2/applications/{user.id}/rpc"

        async with ctx.session.get(url) as r:
            if r.status != 200:
                raise commands.BadArgument(f"Unable to fetch info on {user}")

            data: Dict[Any, Any] = await r.json()

        embed = discord.Embed(color=color)
        embed.set_author(name=f"{user}'s bot info", icon_url=user.display_avatar.url)

        embed.description = data.get("description")

        public = data.get("bot_public") or False
        requires_code = data.get("bot_require_code_grant") or False
        guild_id: Optional[str] = data.get("guild_id")

        info_text = (
            f"Public: {['no', 'yes'][public]}\n"
            f"Requires code: {['no', 'yes'][requires_code]}\n"
        )

        info_text += f"Guild ID: `{guild_id}`" if guild_id else ""

        embed.add_field(name="Bot info", value=info_text)

        tags: Optional[List[str]] = data.get("tags")

        if tags:
            embed.add_field(name="Tags", value="\n".join([f"`{t}`" for t in tags]))

        admin_perms = discord.Permissions.none()
        admin_perms.administrator = True
        invite_perms = [
            ("Administrator", admin_perms),
            ("Advanced", discord.Permissions.advanced()),
            ("General", discord.Permissions.general()),
            ("None", discord.Permissions.none()),
            ("All", discord.Permissions.all()),
        ]

        embed.add_field(
            name="Invites",
            value="\n".join(
                f"[`{name}`]({discord.utils.oauth_url(user.id, permissions=perms)})"
                for name, perms in invite_perms
            ),
        )

        self.bot_cache = embed
        return embed

    async def status_response(self):
        if self.status_cache:
            return self.status_cache

        ctx = self.ctx
        user = self.user
        fuser = self.fetched_user or await ctx.bot.fetch_user(user.id)
        color = fuser.accent_color or ctx.bot.embedcolor

        embed = discord.Embed(color=color)
        embed.set_author(name=f"{user}'s status info", icon_url=user.display_avatar.url)

        if isinstance(user, discord.Member):
            embed.add_field(
                name="Devices",
                value=f"**Desktop**: `{user.desktop_status.value}`\n"
                f"**Website**: `{user.web_status.value}`\n"
                f"**Mobile**: `{user.mobile_status.value}`",
            )
            if ctx.bot.discord:
                online = await self.get_status(user, "online")
                dnd = await self.get_status(user, "dnd")
                idle = await self.get_status(user, "idle")
                offline = await self.get_status(user, "offline")

                statuses = [s for s in [online, dnd, idle, offline] if s]

                text = ""

                for status in statuses:
                    text += f"**{status[1].capitalize()}**: {discord.utils.format_dt(status[0], 'R')}\n"

                if bool(text):
                    embed.add_field(name="Last status", value=text)

        self.status_cache = embed
        return embed

    async def get_status(
        self, member: discord.Member, status: statuses
    ) -> Optional[Tuple[datetime.datetime, str]]:
        if not self.ctx.bot.discord:
            raise commands.BadArgument("Discord cog not found.")

        try:
            return await self.ctx.bot.discord.last_status(member, status=status)
        except commands.BadArgument:
            return None

    async def callback(self, interaction: Interaction):
        value = self.values[0]

        options = {
            "index": self.index_response,
            "avatar": self.avatar_response,
            "banner": self.banner_response,
            "bot": self.bot_response,
            "status": self.status_response,
        }

        if value in options.keys():
            embed = await options[value]()

            if not interaction.message:
                raise commands.BadArgument("Interaction message is gone somehow.")

            await interaction.message.edit(embed=embed)
            await interaction.response.defer()
        else:
            await interaction.response.defer()
            await self.review_response(interaction)


class UserView(AuthorView):
    def __init__(
        self,
        ctx: Context,
        user: Union[discord.User, discord.Member],
        index_embed: discord.Embed,
        fetched_user: Optional[discord.User] = None,
    ):
        super().__init__(ctx)
        self.add_item(UserDropdown(ctx, user, index_embed, fetched_user))


class QualityDropdown(discord.ui.Select):
    view: EditDropdownView

    def __init__(self):
        sizes = ["16", "32", "64", "128", "256", "512", "1024", "2048", "4096"]
        options = [
            discord.SelectOption(label=f"{size}px", value=size) for size in sizes
        ]

        super().__init__(placeholder="Select a quality", options=options)

    async def callback(self, interaction: discord.Interaction):
        self.view.asset = self.view.asset.with_size(int(self.values[0]))
        self.view.embed.set_image(url=self.view.asset.url)

        await interaction.response.edit_message(embed=self.view.embed)


class FormatDropdown(discord.ui.Select):
    view: EditDropdownView

    def __init__(
        self,
        asset: discord.Asset,
    ):
        formats = ["webp", "jpeg", "jpg", "png"]

        if asset.is_animated():
            formats.append("gif")

        options = [
            discord.SelectOption(label=_format, value=_format) for _format in formats
        ]

        super().__init__(placeholder="Select a format", options=options)

    async def callback(self, interaction: discord.Interaction):
        self.view.asset = self.view.asset.with_format(self.values[0])  # type: ignore
        self.view.embed.set_image(url=self.view.asset.url)

        await interaction.response.edit_message(embed=self.view.embed)


class EditDropdownView(AuthorView):
    asset: discord.Asset

    def __init__(
        self,
        ctx: Context,
        user: Union[discord.User, discord.Member],
        embed: discord.Embed,
        asset: discord.Asset,
        fetched_user: Optional[discord.User] = None,
        option: Union[Literal["quality"], Literal["format"]] = "quality",
    ):
        super().__init__(ctx)
        self.user = user
        self.fetched_user = fetched_user
        self.embed = embed
        self.asset = asset

        (
            self.add_item(QualityDropdown())
            if option == "quality"
            else self.add_item(FormatDropdown(asset))
        )

    @discord.ui.button(emoji=fish_go_back, row=1, style=BURPLE)
    async def go_back(self, interaction: discord.Interaction, _):
        await interaction.response.edit_message(
            embed=self.embed,
            view=EditView(
                self.ctx, self.user, self.embed, self.asset, self.fetched_user
            ),
        )


class EditView(AuthorView):
    asset: discord.Asset

    def __init__(
        self,
        ctx: Context,
        user: Union[discord.User, discord.Member],
        embed: discord.Embed,
        asset: discord.Asset,
        fetched_user: Optional[discord.User] = None,
    ):
        super().__init__(ctx)
        self.user = user
        self.fetched_user = fetched_user
        self.embed = embed
        self.asset = asset

        self.server.disabled = isinstance(user, discord.User) or not hasattr(
            user, "guild_avatar"
        )

        self.avatar.disabled = not user.avatar or user.avatar.key == asset.key

    async def edit_message(self, interaction: discord.Interaction):
        self.embed.set_image(url=self.asset.url)
        await interaction.response.edit_message(embed=self.embed)

    @discord.ui.button(label="Default Avatar", row=0, style=BURPLE)
    async def avatar(self, interaction: discord.Interaction, _):
        if not self.user.avatar:
            self.avatar.disabled = True
            raise commands.BadArgument("User's avatar does not exist")

        self.asset = self.user.avatar

        await self.edit_message(interaction)

    @discord.ui.button(label="Server Avatar", row=0, style=BURPLE)
    async def server(self, interaction: discord.Interaction, _):
        if not isinstance(self.user, discord.Member) or self.user.guild_avatar is None:
            self.server.disabled = True
            raise commands.BadArgument("User's server avatar does not exist")

        self.asset = self.user.guild_avatar

        await self.edit_message(interaction)

    @discord.ui.button(emoji=fish_go_back, row=0, style=BURPLE)
    async def go_back(self, interaction: discord.Interaction, _):
        await interaction.response.edit_message(
            embed=self.embed,
            view=AvatarView(
                self.ctx, self.user, self.embed, self.fetched_user, self.asset
            ),
        )

    @discord.ui.button(label="Avatar Quality", row=1, style=GREEN)
    async def quality(self, interaction: discord.Interaction, _):
        await interaction.response.edit_message(
            embed=self.embed,
            view=EditDropdownView(
                self.ctx,
                self.user,
                self.embed,
                self.asset,
                self.fetched_user,
                "quality",
            ),
        )

    @discord.ui.button(label="Avatar Format", row=1, style=GREEN)
    async def _format(self, interaction: discord.Interaction, _):
        await interaction.response.edit_message(
            embed=self.embed,
            view=EditDropdownView(
                self.ctx, self.user, self.embed, self.asset, self.fetched_user, "format"
            ),
        )


class AvatarView(AuthorView):
    asset: discord.Asset

    def __init__(
        self,
        ctx: Context,
        user: Union[discord.User, discord.Member],
        embed: discord.Embed,
        fetched_user: Optional[discord.User] = None,
        asset: Optional[discord.Asset] = None,
    ):
        super().__init__(ctx)
        self.user = user
        self.fetched_user = fetched_user
        self.embed = embed
        self.asset = asset or user.display_avatar

        self.edit.disabled = self.asset.key.isdigit()

    @discord.ui.button(label="Edit", row=0, style=BURPLE, emoji=fish_edit)
    async def edit(self, interaction: discord.Interaction, _):
        if interaction.message is None:
            raise commands.BadArgument("Somehow message was none, try again.")

        view = EditView(self.ctx, self.user, self.embed, self.asset)

        await interaction.message.edit(view=view)
        await interaction.response.defer()

    @discord.ui.button(
        label="Save",
        row=0,
        style=GREEN,
        emoji=fish_download,
    )
    async def save(self, interaction: discord.Interaction, _):
        if interaction.message is None:
            raise commands.BadArgument("Somehow message was none, try again.")

        file = await self.asset.to_file()
        self.embed.set_image(url=f"attachment://{file.filename}")
        await interaction.message.edit(embed=self.embed, attachments=[file], view=None)
        await interaction.response.send_message(
            "Avatar saved! Here's how saving avatars works: the avatar is saved as a "
            "file in this message instead of a Discord user avatar. This "
            "means that unless the message with the file gets deleted, the avatar "
            "will remain forever, unlike user avatars, which will be deleted if the "
            "user decides to change theirs to something else later on.",
            ephemeral=True,
        )


class Info(Cog):
    async def has_nitro(
        self, member: discord.Member, fetched_user: Optional[discord.User] = None
    ) -> bool:
        fetched_user = fetched_user or await self.bot.fetch_user(member.id)
        custom_activity: discord.CustomActivity | None = discord.utils.find(  # type: ignore
            lambda a: isinstance(a, discord.CustomActivity), member.activities
        )
        return any(
            [
                member.display_avatar.is_animated(),
                fetched_user.banner,
                custom_activity
                and custom_activity.emoji
                and custom_activity.emoji.is_custom_emoji(),
            ]
        )

    async def get_badges(
        self,
        member: Union[discord.Member, discord.User],
        ctx: Context,
        fetched_user: Optional[discord.User] = None,
    ) -> List[str]:
        public_flags: Dict[Any, Any] = dict(member.public_flags)
        new_values = {
            member.id: True,
            "owner": await ctx.bot.is_owner(member),
            "server_owner": isinstance(member, discord.Member)
            and member.guild.owner == member,
            "booster": isinstance(member, discord.Member) and member.premium_since,
            "nitro": (
                await self.has_nitro(member, fetched_user)
                if isinstance(member, discord.Member)
                else False
            ),
        }
        public_flags.update(new_values)

        user_flags: List[str] = []

        for flag, text in USER_FLAGS.items():
            try:
                if public_flags[flag]:
                    user_flags.append(text)
            except (KeyError, IndexError):
                continue

        return user_flags

    def join_pos(self, member: discord.Member) -> int:
        members = sorted(
            member.guild.members, key=lambda m: m.joined_at or discord.utils.utcnow()
        )
        return members.index(member) + 1

    async def last_status(
        self,
        member: discord.Member,
        status: Optional[statuses] = None,
    ) -> Tuple[datetime.datetime, str]:
        sql = """SELECT created_at, status_name FROM status_logs WHERE user_id = $1 AND guild_id = $2"""
        args = (member.id, member.guild.id)

        if status:
            sql += " AND status_name = $3"
            args = (member.id, member.guild.id, status)

        sql += " ORDER BY created_at DESC"

        results = await self.bot.pool.fetchrow(sql, *args)

        if not bool(results):
            if status:
                raise commands.BadArgument(
                    "Could not find a specific status for that member."
                )

            now = discord.utils.utcnow()
            sql = """
            INSERT INTO status_logs (   user_id, status_name,
                                        guild_id, created_at)
            VALUES ($1, $2, $3, $4)
            """
            await self.bot.pool.execute(
                sql, member.id, member.status.name, member.guild.id, now
            )
            return now, member.status.name

        return results["created_at"], results["status_name"]

    def format_status(self, status: str) -> str:
        return f"{['','on '][status == 'dnd']}{status}"

    async def user_info(self, ctx: Context, user: Union[discord.Member, discord.User]):
        fuser = await self.bot.fetch_user(user.id)

        badges = await self.get_badges(user, ctx, fuser)

        embed = discord.Embed(
            color=fuser.accent_colour or self.bot.embedcolor,
            description=user.mention,
            timestamp=user.created_at,
        )
        embed.set_author(name=str(user), icon_url=user.display_avatar.url)
        bar = "\u2800" * 47
        embed.set_footer(text=f"{bar} \nID: {user.id} \nCreated at")

        if bool(badges):
            embed.add_field(name="Badges", value="\n".join(badges))

        if isinstance(user, discord.Member):
            joined = user.joined_at or discord.utils.utcnow()
            pos_text = (
                f"Position #{self.join_pos(user)}\n"
                f"{discord.utils.format_dt(joined, 'D')}\n"
                f"{reply} {discord.utils.format_dt(joined, 'R')}"
            )
            embed.add_field(name="Joined", value=pos_text)

            status, status_name = await self.last_status(user)

            status_text = (
                f"{discord.utils.format_dt(status, 'D')}\n"
                f"{reply} {discord.utils.format_dt(status, 'R')}"
            )

            embed.add_field(
                name=f"{self.format_status(status_name)} since".capitalize(),
                value=status_text,
            )

        await ctx.send(embed=embed, view=UserView(ctx, user, embed, fuser))

    async def review_func(
        self, ctx: Context, user: discord.User | discord.Member, hidden: bool = False
    ):
        url = f"https://manti.vendicated.dev/api/reviewdb/users/{user.id}/reviews"
        async with ctx.session.get(url) as resp:
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
        await pager.start(ctx, e=hidden)

    @commands.command(name="userinfo", aliases=("ui", "user"))
    async def userinfo(
        self,
        ctx: Context,
        *,
        user: Union[discord.Member, discord.User] = commands.Author,
    ):
        """
        Get information about a user
        """
        async with ctx.typing():
            await self.user_info(ctx, user)

    def channel_embed(self, channel: AllChannels) -> discord.Embed:
        embed = discord.Embed(
            color=self.bot.embedcolor,
            timestamp=channel.created_at,
            title=channel.name,
        )

        embed.set_footer(text=f"ID: {channel.id} \nCreated at")

        if isinstance(
            channel, (discord.TextChannel, discord.VoiceChannel, discord.StageChannel)
        ):
            embed.add_field(
                name="Members",
                value=f"{len(channel.members):,} ({sum(m.bot for m in channel.members):,} bots)",
            )

        return embed

    async def text_info(self, ctx: Context, channel: discord.TextChannel):
        embed = self.channel_embed(channel)
        embed.description = channel.topic
        await ctx.send(embed=embed)

    async def category_info(self, ctx: Context, channel: discord.CategoryChannel):
        embed = self.channel_embed(channel)

        if isinstance(ctx.author, discord.Member):
            text = f"{len(channel.channels)}"
            private = sum(
                not c.permissions_for(ctx.author).read_messages
                for c in channel.channels
            )
            if private > 0:
                text += f" ({private:,} private)"

            embed.add_field(
                name="Channels",
                value=text,
            )

        await ctx.send(embed=embed)

    async def voice_info(
        self, ctx: Context, channel: Union[discord.VoiceChannel, discord.StageChannel]
    ):
        embed = self.channel_embed(channel)

        vc_limit = (
            "No User limit"
            if not bool(channel.user_limit)
            else f"{channel.user_limit:,} User limit"
        )

        embed.add_field(
            name="Details",
            value=f"{channel.video_quality_mode.name.capitalize()} Video Quality\n"
            f"{channel.rtc_region.capitalize() if channel.rtc_region else 'Automatic'} region\n"
            f"{vc_limit}\n"
            f"{str(channel.bitrate)[:-3]}kbps",
        )

        await ctx.send(embed=embed)

    async def thread_info(self, ctx: Context, channel: discord.Thread):
        embed = self.channel_embed(channel)
        members = await channel.fetch_members()
        embed.add_field(
            name="Members",
            value=f"{len(members):,}",
        )

        if channel.parent:
            parent = channel.parent
            embed.add_field(
                name="Parent channel", value=f"{parent} (`{parent.id}`)", inline=False
            )

        if channel.owner:
            owner = channel.owner
            embed.add_field(name="Owner", value=f"{owner} (`{owner.id}`)", inline=False)

        await ctx.send(embed=embed)

    async def forum_info(self, ctx: Context, channel: discord.ForumChannel):
        embed = self.channel_embed(channel)

        embed.description = channel.topic

        embed.add_field(name="Posts", value=f"{len(channel.threads)}")

        embed.add_field(
            name="Tags",
            value=human_join(
                [f"{s.emoji or ''}{s.name}" for s in channel.available_tags],
                final="and",
            ),
        )

        await ctx.send(embed=embed)

    @commands.command(name="channelinfo", aliases=("channel", "ci"))
    async def channelinfo(
        self,
        ctx: Context,
        channel: AllChannels = commands.param(
            displayed_default="[channel=<current channel>]",
            default=lambda ctx: ctx.channel,
        ),
    ):
        """
        Get information about a channel
        """
        types = {
            discord.TextChannel: self.text_info,
            discord.CategoryChannel: self.category_info,
            discord.VoiceChannel: self.voice_info,
            discord.StageChannel: self.voice_info,
            discord.Thread: self.thread_info,
            discord.ForumChannel: self.forum_info,
        }

        await types[type(channel)](ctx, channel)

    @commands.hybrid_group(
        name="avatar", aliases=("pfp", "av", "avy", "avi"), fallback="get"
    )
    async def avatar(
        self,
        ctx: Context,
        *,
        user: Union[discord.Member, discord.User] = commands.Author,
    ):
        """Get or edit a user's avatar"""
        fuser = await self.bot.fetch_user(user.id)
        embed = discord.Embed(color=fuser.accent_color or self.bot.embedcolor)
        embed.set_author(name=f"{user}'s avatar", icon_url=user.display_avatar.url)

        embed.set_image(url=user.display_avatar.url)

        sql = """SELECT created_at FROM avatars WHERE user_id = $1 ORDER BY created_at DESC"""

        last_av: Optional[datetime.datetime] = await self.bot.pool.fetchval(
            sql, user.id
        )

        if last_av:
            embed.timestamp = last_av
            embed.set_footer(text="Last avatar saved")

        await ctx.send(embed=embed, view=AvatarView(ctx, user, embed, fuser))

    @avatar.command(name="history", aliases=("h",))
    async def avatar_history(
        self,
        ctx: Context,
        *,
        user: discord.User = commands.Author,
    ):
        """Get a user's avatar history"""
        logging = self.bot.logging

        if not logging:
            raise commands.BadArgument("Could not find logging cog.")

        await logging.avatars_func(ctx, user)

    @commands.command(name="banner")
    async def user_banner(
        self,
        ctx: Context,
        *,
        user: Union[discord.Member, discord.User] = commands.Author,
    ):
        """Get or edit a user's banner"""
        user = await self.bot.fetch_user(user.id)
        if not user.banner:
            raise commands.BadArgument("User has no banner.")

        embed = discord.Embed(color=user.accent_color or self.bot.embedcolor)
        embed.set_author(name=f"{user}'s banner", icon_url=user.display_avatar.url)

        file = await user.banner.to_file()

        embed.set_image(url=f"attachment://{file.filename}")

        await ctx.send(embed=embed, file=file)

    async def server_info(self, ctx: GuildContext, guild: discord.Guild):
        embed = discord.Embed(timestamp=guild.created_at)
        images = []

        name = (
            f"{guild.name}  •  {guild.vanity_url}" if guild.vanity_url else guild.name
        )
        embed.set_author(name=name)

        if guild.description:
            embed.description = discord.utils.escape_markdown(guild.description)

        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
            images.append(f"[Icon]({guild.icon.url})")

        if guild.banner:
            images.append(f"[Banner]({guild.banner.url})")

        if guild.splash:
            images.append(f"[Splash]({guild.splash.url})")

        bots = sum(m.bot for m in guild.members)
        embed.add_field(
            name=f"Members",
            value=f"{guild.member_count:,} ({bots:,} bots)",
        )

        channels_text = f"{len(guild.channels):,}"
        private = sum(
            not c.permissions_for(ctx.author).read_messages for c in guild.channels
        )
        if private > 0:
            channels_text += f" ({private:,} private)"

        embed.add_field(name=f"Channels", value=channels_text)

        embed.add_field(name="Roles", value=f"{len(guild.roles):,} Roles")

        embed.add_field(name="Owner", value=f"<@{guild.owner_id}>", inline=True)

        embed.add_field(
            name=f"Level {guild.premium_tier}",
            value=f"{len(guild.premium_subscribers):,} Boosters\n"
            f"{guild.premium_subscription_count:,} Boosts",
        )

        emoji_stats = Counter()
        for emoji in guild.emojis:
            if emoji.animated:
                emoji_stats["animated"] += 1
                emoji_stats["animated_disabled"] += not emoji.available
            else:
                emoji_stats["regular"] += 1
                emoji_stats["disabled"] += not emoji.available

        fmt = (
            f'{emoji_stats["regular"]}/{guild.emoji_limit} Regular\n'
            f'{emoji_stats["animated"]}/{guild.emoji_limit} Animated\n'
        )
        if emoji_stats["disabled"] or emoji_stats["animated_disabled"]:
            fmt = f'{fmt}Disabled: {emoji_stats["disabled"]} regular, {emoji_stats["animated_disabled"]} animated\n'

        embed.add_field(name="Emojis", value=fmt)

        if bool(images):
            embed.add_field(name="Images", value=", ".join(images), inline=False)

        embed.set_footer(text=f"ID: {guild.id} \nCreated at")
        await ctx.send(embed=embed)

    @commands.group(name="serverinfo", aliases=("server", "si"))
    @commands.guild_only()
    async def serverinfo(
        self, ctx: GuildContext, *, guild: discord.Guild = commands.CurrentGuild
    ):
        await self.server_info(ctx, guild)

    async def server_icon(self, ctx: Context, guild: discord.Guild):
        if guild.icon is None:
            raise commands.BadArgument(f"{guild} has no icon.")

        embed = discord.Embed(color=self.bot.embedcolor, title=f"{guild}'s icon")
        file = await guild.icon.to_file()

        embed.set_image(url=f"attachment://{file.filename}")

        await ctx.send(embed=embed, file=file)

    async def server_banner(self, ctx: Context, guild: discord.Guild):
        if guild.banner is None:
            raise commands.BadArgument(f"{guild} has no banner.")

        embed = discord.Embed(color=self.bot.embedcolor, title=f"{guild}'s banner")

        file = await guild.banner.to_file()

        embed.set_image(url=f"attachment://{file.filename}")

        await ctx.send(embed=embed, file=file)

    async def server_splash(self, ctx: Context, guild: discord.Guild):
        if guild.splash is None:
            raise commands.BadArgument(f"{guild} has no splash.")

        embed = discord.Embed(color=self.bot.embedcolor, title=f"{guild}'s splash")

        file = await guild.splash.to_file()

        embed.set_image(url=f"attachment://{file.filename}")

        await ctx.send(embed=embed, file=file)

    @serverinfo.command(name="icon")
    async def serverinfo_icon(
        self, ctx: Context, *, guild: discord.Guild = commands.CurrentGuild
    ):
        await self.server_icon(ctx, guild)

    @serverinfo.command(name="banner")
    async def serverinfo_banner(
        self, ctx: Context, *, guild: discord.Guild = commands.CurrentGuild
    ):
        await self.server_banner(ctx, guild)

    @serverinfo.command(name="splash", aliases=("invitebackground", "invitebg", "ibg"))
    async def serverinfo_splash(
        self, ctx: Context, *, guild: discord.Guild = commands.CurrentGuild
    ):
        await self.server_splash(ctx, guild)

    @commands.command(name="icon")
    async def icon(self, ctx: Context, *, guild: discord.Guild = commands.CurrentGuild):
        await self.server_icon(ctx, guild)

    @commands.command(name="serverbanner", aliases=("sbanner",))
    async def server_banner_command(
        self, ctx: Context, *, guild: discord.Guild = commands.CurrentGuild
    ):
        await self.server_banner(ctx, guild)

    @commands.command(name="splash", aliases=("invitebackground", "invitebg", "ibg"))
    async def splash(
        self, ctx: Context, *, guild: discord.Guild = commands.CurrentGuild
    ):
        await self.server_splash(ctx, guild)

    @commands.hybrid_command(name="reviews")
    async def reviews(
        self, ctx: Context, user: discord.User = commands.Author, hidden: bool = False
    ):
        """Get reviews for a user.

        These reviews are provided by ReviewDB ONLY. (for now)
        """

        await self.review_func(ctx, user, hidden)
