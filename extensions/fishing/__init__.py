from __future__ import annotations

import random
from typing import TYPE_CHECKING, Optional

import discord
from discord.ext import commands

from core import Cog
from files.data import FishingPoles, FishCollection, Fish

if TYPE_CHECKING:
    from core import Fishie
    from extensions.context import Context


class Fishing(Cog):
    """if u see this no u dont. coming soon heh"""

    emoji = discord.PartialEmoji(name="\U0001f3a3")

    def __init__(self, bot: Fishie):
        super().__init__()
        self.bot = bot
        self.fishing_poles: FishingPoles = FishingPoles()
        self.fish: FishCollection = FishCollection()

    def cast_function(self, user: discord.User | discord.Member) -> Optional[Fish]:
        pole = self.fishing_poles.get_pole("mythic")

        # Gather all fish and their weights that are within the pole's level range
        fish_weights = {}
        for fish_key, fish in self.fish.list_fish().items():
            if pole.id <= fish.max_level:
                # Calculate weight considering the pole's multiplier and fish rarity
                adjusted_weight = fish.weight * pole.multiplier * fish.rarity.weight
                fish_weights[fish_key] = adjusted_weight

        # If no fish are available for the current fishing pole level, return None
        if not fish_weights:
            return None

        # Normalize weights to sum to 1 for probability distribution
        total_weight = sum(fish_weights.values())
        fish_probabilities = {
            key: weight / total_weight for key, weight in fish_weights.items()
        }

        # Perform weighted random selection
        fish_keys = list(fish_probabilities.keys())
        fish_chosen = random.choices(fish_keys, weights=fish_probabilities.values(), k=1)[0]  # type: ignore

        # Return the chosen fish
        return self.fish.get_fish(fish_chosen)

    @commands.hybrid_command(name="cast", aliases=("fish",))
    @commands.is_owner()
    async def cast(self, ctx: Context):
        fish = self.cast_function(ctx.author)
        description = f"You cast your Paper Fishing Rod"
        description += f" and got a {fish.name} fish!" if fish else " and got nothing!"

        embed = discord.Embed(
            color=discord.Color.gold(),
            description=description,
        )
        await ctx.send(embed=embed)

    async def cog_unload(self):
        self.fishing_poles = FishingPoles()
        self.fish = FishCollection()

    async def cog_load(self):
        self.fishing_poles.add_poles_from_dict()
        self.fish.add_fish_from_dict()


async def setup(bot: Fishie):
    await bot.add_cog(Fishing(bot))
