"""Ship, fleet, and mothership definitions for Hollowed Stars.

Ships are individually tracked with their own weapons and formation slots,
per PLAN.md: "Each ship can be customised and outfitted with different weapons."
"""

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


# ---------------------------------------------------------------------------
# Individual fleet ship (per PLAN.md: each ship is customisable)
# ---------------------------------------------------------------------------

@dataclass
class FleetShip:
    """An individual ship in the player's fleet."""

    name: str
    ship_class: ShipClass
    hull: int
    max_hull: int
    armor: int
    weapon_slots: list[WeaponSlot] = field(default_factory=list)
    formation_slot: int = 0

    @property
    def is_combat(self) -> bool:
        return self.ship_class not in (ShipClass.SCOUT, ShipClass.MINER, ShipClass.TRANSPORT)

    @property
    def display_name(self) -> str:
        return self.ship_class.value.replace("_", " ").title()


# Ship class stats: hull, armor, weapon slots, build costs
SHIP_CLASS_STATS: dict[ShipClass, dict] = {
    # Combat ships (ascending)
    ShipClass.DRONE: {
        "hull": 30, "armor": 0,
        "slots": [WeaponSize.SMALL],
        "cost_metal": 100, "cost_energy": 50, "cost_rare": 0,
    },
    ShipClass.FIGHTER: {
        "hull": 60, "armor": 5,
        "slots": [WeaponSize.SMALL, WeaponSize.SMALL],
        "cost_metal": 250, "cost_energy": 100, "cost_rare": 0,
    },
    ShipClass.CORVETTE: {
        "hull": 150, "armor": 20,
        "slots": [WeaponSize.SMALL, WeaponSize.SMALL, WeaponSize.SMALL],
        "cost_metal": 600, "cost_energy": 300, "cost_rare": 20,
    },
    ShipClass.FRIGATE: {
        "hull": 300, "armor": 40,
        "slots": [WeaponSize.MEDIUM, WeaponSize.SMALL, WeaponSize.SMALL],
        "cost_metal": 1200, "cost_energy": 600, "cost_rare": 60,
    },
    ShipClass.DESTROYER: {
        "hull": 500, "armor": 60,
        "slots": [WeaponSize.MEDIUM, WeaponSize.MEDIUM, WeaponSize.SMALL],
        "cost_metal": 2000, "cost_energy": 1000, "cost_rare": 120,
    },
    ShipClass.CRUISER: {
        "hull": 800, "armor": 100,
        "slots": [WeaponSize.LARGE, WeaponSize.MEDIUM, WeaponSize.MEDIUM, WeaponSize.SMALL],
        "cost_metal": 3500, "cost_energy": 1800, "cost_rare": 250,
    },
    ShipClass.HEAVY_CRUISER: {
        "hull": 1200, "armor": 150,
        "slots": [WeaponSize.LARGE, WeaponSize.LARGE, WeaponSize.MEDIUM, WeaponSize.MEDIUM, WeaponSize.SMALL],
        "cost_metal": 5000, "cost_energy": 2500, "cost_rare": 400,
    },
    ShipClass.BATTLESHIP: {
        "hull": 2000, "armor": 250,
        "slots": [WeaponSize.CAPITAL, WeaponSize.LARGE, WeaponSize.LARGE, WeaponSize.MEDIUM, WeaponSize.MEDIUM, WeaponSize.SMALL, WeaponSize.SMALL],
        "cost_metal": 8000, "cost_energy": 4000, "cost_rare": 800,
    },
    # Non-combat ships
    ShipClass.SCOUT: {
        "hull": 40, "armor": 0,
        "slots": [],
        "cost_metal": 150, "cost_energy": 100, "cost_rare": 10,
    },
    ShipClass.MINER: {
        "hull": 80, "armor": 10,
        "slots": [],
        "cost_metal": 300, "cost_energy": 150, "cost_rare": 0,
    },
    ShipClass.TRANSPORT: {
        "hull": 120, "armor": 15,
        "slots": [],
        "cost_metal": 500, "cost_energy": 200, "cost_rare": 10,
    },
}


def build_fleet_ship(ship_class: ShipClass, name: str, formation_slot: int = 0) -> FleetShip:
    """Create a new FleetShip with default stats for its class."""
    stats = SHIP_CLASS_STATS[ship_class]
    return FleetShip(
        name=name,
        ship_class=ship_class,
        hull=stats["hull"],
        max_hull=stats["hull"],
        armor=stats["armor"],
        weapon_slots=[WeaponSlot(size) for size in stats["slots"]],
        formation_slot=formation_slot,
    )


@dataclass
class Fleet:
    """The player's entire fleet state."""

    mothership: Mothership
    ships: list[FleetShip] = field(default_factory=list)
    resources: Resources = field(default_factory=Resources)
    colonists: int = 1_000_000

    @property
    def total_ships(self) -> int:
        return len(self.ships)

    @property
    def combat_ships(self) -> list[FleetShip]:
        return [s for s in self.ships if s.is_combat]

    @property
    def scouts(self) -> list[FleetShip]:
        return [s for s in self.ships if s.ship_class == ShipClass.SCOUT]

    @property
    def miners(self) -> list[FleetShip]:
        return [s for s in self.ships if s.ship_class == ShipClass.MINER]

    @property
    def transports(self) -> list[FleetShip]:
        return [s for s in self.ships if s.ship_class == ShipClass.TRANSPORT]

    @property
    def scout_bonus(self) -> float:
        """Sensor range multiplier from scouts (each adds 20%)."""
        return 1.0 + len(self.scouts) * 0.2

    @property
    def mining_bonus(self) -> float:
        """Resource yield multiplier from miners (each adds 25%)."""
        return 1.0 + len(self.miners) * 0.25

    @property
    def transport_capacity(self) -> int:
        """Extra colonist capacity from transports (50k each)."""
        return len(self.transports) * 50_000

    @property
    def effective_colonist_capacity(self) -> int:
        return self.mothership.colonist_capacity + self.transport_capacity

    def can_build(self, ship_class: ShipClass) -> bool:
        """Check if we have resources and hangar space."""
        if self.total_ships >= self.mothership.hangar_capacity:
            return False
        stats = SHIP_CLASS_STATS[ship_class]
        return (
            self.resources.metal >= stats["cost_metal"]
            and self.resources.energy >= stats["cost_energy"]
            and self.resources.rare_materials >= stats["cost_rare"]
        )

    def build_ship(self, ship_class: ShipClass, name: str | None = None) -> FleetShip | None:
        """Build a new ship, deducting resources. Returns the ship or None."""
        if not self.can_build(ship_class):
            return None
        stats = SHIP_CLASS_STATS[ship_class]
        self.resources.metal -= stats["cost_metal"]
        self.resources.energy -= stats["cost_energy"]
        self.resources.rare_materials -= stats["cost_rare"]

        if name is None:
            # Auto-name: "Corvette 3"
            existing = sum(1 for s in self.ships if s.ship_class == ship_class)
            name = f"{ship_class.value.replace('_', ' ').title()} {existing + 1}"

        slot = max((s.formation_slot for s in self.ships), default=0) + 1
        ship = build_fleet_ship(ship_class, name, slot)
        self.ships.append(ship)
        return ship

    def scrap_ship(self, ship: FleetShip) -> None:
        """Scrap a ship, recovering 50% of build cost."""
        if ship in self.ships:
            stats = SHIP_CLASS_STATS[ship.ship_class]
            self.resources.metal += stats["cost_metal"] // 2
            self.resources.energy += stats["cost_energy"] // 2
            self.resources.rare_materials += stats["cost_rare"] // 2
            self.ships.remove(ship)


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


# ---------------------------------------------------------------------------
# Signal of Dawn — unlockable federation flagship (PLAN.md true ending path)
# ---------------------------------------------------------------------------

SIGNAL_OF_DAWN = Mothership(
    name="Signal of Dawn",
    description="The old federation flagship. Unmatched in every way.",
    lore=(
        "The Signal of Dawn was the pride of the Old Federation's fleet.\n"
        "Designed as the vanguard for the Trans-Galactic Gateway project,\n"
        "it carries the experimental flagship beam — a weapon of\n"
        "incomprehensible power. Its Class 1 Identification Code grants\n"
        "access to the Gateway itself. Now, after 5000 years of silence,\n"
        "it answers to a new Admiral."
    ),
    hull=25000,
    max_hull=25000,
    armor=1200,
    power=15000,
    max_power=15000,
    speed=1.2,
    sensor_range=2.5,
    colonist_capacity=2_000_000,
    hangar_capacity=50,
    weapon_slots=[
        WeaponSlot(WeaponSize.CAPITAL),   # Flagship Beam slot
        WeaponSlot(WeaponSize.CAPITAL),
        WeaponSlot(WeaponSize.LARGE),
        WeaponSlot(WeaponSize.LARGE),
        WeaponSlot(WeaponSize.LARGE),
        WeaponSlot(WeaponSize.MEDIUM),
        WeaponSlot(WeaponSize.MEDIUM),
        WeaponSlot(WeaponSize.MEDIUM),
        WeaponSlot(WeaponSize.SMALL),
        WeaponSlot(WeaponSize.SMALL),
    ],
    special_ability="Class 1 Identification Code",
    special_description="Grants access to the Trans-Galactic Gateway. The key to humanity's true salvation.",
)
