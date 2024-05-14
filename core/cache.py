from typing import Any, Dict, List


class db_cache:
    prefixes: Dict[int, List[str]] = {}
    opted_out: Dict[int, List[str]] = {}
    auto_downloads: List[int] = []
    poketwo_guilds: List[int] = []
    auto_reaction_guilds: List[int] = []
    nsfw_covers: List[int] = []
    pinboard: Dict[int, int] = {}

    def add_prefix(self, guild_id: int, prefix: str) -> List[str]:
        try:
            self.prefixes[guild_id].append(prefix)
        except KeyError:
            self.prefixes.update({guild_id: [prefix]})

        return self.prefixes[guild_id]

    def remove_prefix(self, guild_id: int, prefix: str) -> List[str]:
        try:
            self.prefixes[guild_id].remove(prefix)
        except KeyError:
            return []
        except ValueError:
            return self.prefixes[guild_id]

        return self.prefixes[guild_id]

    def add_pinboard(self, guild_id: int, channel_id: int):
        self.pinboard.update({guild_id: channel_id})

    def remove_pinboard(self, guild_id: int, channel_id: int):
        try:
            del self.pinboard[guild_id]
        except:
            return self.pinboard[guild_id]

    def add_opt_out(self, object_id: int, value: str):
        try:
            self.opted_out[object_id].append(value)
        except KeyError:
            self.opted_out.update({object_id: [value]})

        return self.opted_out[object_id]

    def remove_opt_out(self, object_id: int, value: str):
        try:
            self.opted_out[object_id].remove(value)
        except KeyError:
            return []
        except ValueError:
            return self.opted_out[object_id]

        return self.opted_out[object_id]

    def add_adl(self, channel_id: int):
        self.auto_downloads.append(channel_id)

    def remove_adl(self, channel_id: int):
        try:
            self.auto_downloads.remove(channel_id)
        except ValueError:
            pass

    def add_poketwo(self, guild_id: int):
        self.poketwo_guilds.append(guild_id)

    def remove_poketwo(self, guild_id: int):
        try:
            self.poketwo_guilds.remove(guild_id)
        except ValueError:
            pass

    def add_reaction_guilds(self, guild_id: int):
        self.auto_reaction_guilds.append(guild_id)

    def remove_reaction_guilds(self, guild_id: int):
        try:
            self.auto_reaction_guilds.remove(guild_id)
        except ValueError:
            pass

    def get_opted_out(self, object_id: int) -> List[str]:
        try:
            return self.opted_out[object_id]
        except:  # idc
            return []
