"""Ship, fleet, and mothership definitions for Hollowed Stars."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field


class WeaponSize(enum.Enum):
    """Weapon mount sizes — determines what can be equipped."""

    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    CAPITAL = "capital"


class ShipClass(enum.Enum):
    """Classification of ships in the fleet."""

    # Combat (ascending size/cost/firepower)
    DRONE = "drone"
    FIGHTER = "fighter"
    CORVETTE = "corvette"
    FRIGATE = "frigate"
    DESTROYER = "destroyer"
    CRUISER = "cruiser"
    HEAVY_CRUISER = "heavy_cruiser"
    BATTLESHIP = "battleship"

    # Non-combat
    SCOUT = "scout"
    MINER = "miner"
    TRANSPORT = "transport"


@dataclass
class WeaponSlot:
    """A weapon mount point on a ship."""

    size: WeaponSize
    equipped: str | None = None  # Weapon name or None if empty


@dataclass
class Mothership:
    """The player's mothership — the heart of the fleet."""

    name: str
    description: str
    lore: str

    # Stats
    hull: int
    max_hull: int
    armor: int
    power: int
    max_power: int
    speed: float  # Sublight speed modifier
    sensor_range: float  # Affects discovery radius

    # Capacity
    colonist_capacity: int
    hangar_capacity: int  # Max fleet ships
    weapon_slots: list[WeaponSlot] = field(default_factory=list)

    # Special
    special_ability: str = ""
    special_description: str = ""


@dataclass
class Resources:
    """Fleet resource stockpile."""

    metal: int = 5000
    energy: int = 3000
    rare_materials: int = 500


@dataclass
class Fleet:
    """The player's entire fleet state."""

    mothership: Mothership
    ships: dict[ShipClass, int] = field(default_factory=dict)
    resources: Resources = field(default_factory=Resources)
    colonists: int = 1_000_000

    @property
    def total_ships(self) -> int:
        return sum(self.ships.values())


# ---------------------------------------------------------------------------
# Pre-defined motherships
# ---------------------------------------------------------------------------

MOTHERSHIPS: list[Mothership] = [
    Mothership(
        name="Aegis of Dawn",
        description="Balanced ark — high colonist capacity, decent defenses.",
        lore=(
            "Built in the final years of the station, the Aegis was designed\n"
            "as the ultimate lifeboat. Its cavernous cryo-vaults can hold\n"
            "over a million souls, and its balanced systems make it\n"
            "adaptable to any challenge the dead galaxy throws at you."
        ),
        hull=10000,
        max_hull=10000,
        armor=400,
        power=5000,
        max_power=5000,
        speed=1.0,
        sensor_range=1.0,
        colonist_capacity=1_200_000,
        hangar_capacity=30,
        weapon_slots=[
            WeaponSlot(WeaponSize.MEDIUM),
            WeaponSlot(WeaponSize.MEDIUM),
            WeaponSlot(WeaponSize.SMALL),
            WeaponSlot(WeaponSize.SMALL),
            WeaponSlot(WeaponSize.SMALL),
            WeaponSlot(WeaponSize.SMALL),
        ],
        special_ability="Emergency Cryo-Revival",
        special_description="Can rapidly thaw colonists to crew damaged systems, granting a temporary repair boost.",
    ),
    Mothership(
        name="Iron Bastion",
        description="Combat fortress — heavy armor, devastating firepower.",
        lore=(
            "Originally a battlestation prototype, the Iron Bastion was\n"
            "converted into an ark when hope ran out. Its massive weapons\n"
            "arrays and layered armor plating make it a terrifying\n"
            "opponent, but its cramped interior limits colonist capacity."
        ),
        hull=15000,
        max_hull=15000,
        armor=800,
        power=7000,
        max_power=7000,
        speed=0.7,
        sensor_range=0.8,
        colonist_capacity=600_000,
        hangar_capacity=20,
        weapon_slots=[
            WeaponSlot(WeaponSize.CAPITAL),
            WeaponSlot(WeaponSize.LARGE),
            WeaponSlot(WeaponSize.LARGE),
            WeaponSlot(WeaponSize.MEDIUM),
            WeaponSlot(WeaponSize.MEDIUM),
            WeaponSlot(WeaponSize.SMALL),
            WeaponSlot(WeaponSize.SMALL),
            WeaponSlot(WeaponSize.SMALL),
        ],
        special_ability="Broadside Barrage",
        special_description="Fires all weapons simultaneously for one devastating alpha strike per engagement.",
    ),
    Mothership(
        name="Whisper of Stars",
        description="Exploration vessel — superior sensors, unmatched speed.",
        lore=(
            "A deep-space research vessel, the Whisper was never meant\n"
            "for war. Its cutting-edge sensor arrays can detect anomalies\n"
            "across entire star systems, and its efficient drives outrun\n"
            "anything in the galaxy. What it lacks in firepower, it\n"
            "makes up for in the ability to find — and flee — anything."
        ),
        hull=7000,
        max_hull=7000,
        armor=200,
        power=4000,
        max_power=4000,
        speed=1.5,
        sensor_range=2.0,
        colonist_capacity=800_000,
        hangar_capacity=40,
        weapon_slots=[
            WeaponSlot(WeaponSize.MEDIUM),
            WeaponSlot(WeaponSize.SMALL),
            WeaponSlot(WeaponSize.SMALL),
        ],
        special_ability="Deep Scan",
        special_description="Reveals all objects and dangers in a system before entering, preventing ambushes.",
    ),
]
