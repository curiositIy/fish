from dataclasses import dataclass
from typing import Dict, Optional
from .raw_fishing_data import fishing_poles, fish


@dataclass
class FishingPole:
    id: int
    name: str
    multiplier: float
    price: float


@dataclass
class FishRarity:
    id: int
    name: str
    weight: float
    max_level: int
    multiplier: float


@dataclass
class Fish:
    id: int
    name: str
    weight: float
    min_level: int
    max_level: int
    value: int
    rarity: FishRarity


class FishRarities:
    # fmt: off
    common = FishRarity(id=1, name="Common", weight=50.0, max_level=6, multiplier=1)
    uncommon = FishRarity(id=2, name="Uncommon", weight=30.0, max_level=8, multiplier=1.2)
    rare = FishRarity(id=3, name="Rare", weight=15.0, max_level=10, multiplier=1.4)
    epic = FishRarity(id=4, name="Epic", weight=8.0, max_level=12, multiplier=2)
    legendary = FishRarity(id=5, name="Legendary", weight=1.5, max_level=14, multiplier=2.5)
    mythic = FishRarity(id=6, name="Mythic", weight=0.5, max_level=6, multiplier=4)
    # fmt: on


class FishingPoles:
    def __init__(self):
        self.poles: Dict[str, FishingPole] = {}

    def add_pole(self, key: str, pole: FishingPole):
        self.poles[key] = pole

    def get_pole(self, key: str) -> FishingPole:
        """Gets requested fishing pole, returns Paper if no results."""
        return self.poles.get(
            key, FishingPole(id=0, name="Paper", multiplier=1.0, price=0.0)
        )

    def get_pole_by_id(self, pole_id: int) -> FishingPole:
        """Gets requested fishing pole by ID, returns Paper if no results."""
        for pole in self.poles.values():
            if pole.id == pole_id:
                return pole

        return FishingPole(id=0, name="Paper", multiplier=1.0, price=0.0)

    def list_poles(self) -> Dict[str, FishingPole]:
        return self.poles

    def add_poles_from_dict(self, poles: Dict[str, Dict] = fishing_poles):
        for key, attrs in poles.items():
            self.add_pole(key, FishingPole(**attrs))


class FishCollection:
    def __init__(self):
        self.fish: Dict[str, Fish] = {}

    def add_fish(self, key: str, fish: Fish):
        self.fish[key] = fish

    def get_fish(self, key: str) -> Optional[Fish]:
        """Gets requested fish, returns None if no results."""
        return self.fish.get(key, None)

    def get_fish_by_id(self, fish_id: int) -> Optional[Fish]:
        """Gets requested fish by ID, returns None if no results."""
        for fish in self.fish.values():
            if fish.id == fish_id:
                return fish

        return None

    def list_fish(self) -> Dict[str, Fish]:
        return self.fish

    def add_fish_from_dict(self, fish: Dict[str, Dict] = fish):
        for key, attrs in fish.items():
            self.add_fish(key, Fish(rarity=FishRarities.common, **attrs))
