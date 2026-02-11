"""Mothership internal systems and maintenance for Hollowed Stars.

PLAN.md: Systems degrade over time and during FTL travel.
Repair bots cost resources + time. Components can be upgraded.
Equipment tiers: standard < alien (easy to get) < federation (salvage, best).
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field


class SystemType(enum.Enum):
    """Internal mothership systems."""

    LIFE_SUPPORT = "life_support"
    THRUSTERS = "thrusters"
    POWER_CORE = "power_core"
    SENSORS = "sensors"
    WEAPONS_ARRAY = "weapons_array"
    HANGAR = "hangar"
    CRYO_VAULTS = "cryo_vaults"
    SHIELDS = "shields"


class ComponentQuality(enum.Enum):
    """Equipment quality tiers (per PLAN.md)."""

    STANDARD = "standard"        # Craftable, baseline
    ALIEN = "alien"              # Easy to get, slightly worse
    FEDERATION = "federation"    # Salvage only, best in every way


@dataclass
class Component:
    """An individual component within a system."""

    name: str
    quality: ComponentQuality
    condition: float = 100.0    # 0–100, degrades with use
    stats_bonus: float = 0.0    # % bonus to parent system

    @property
    def effectiveness(self) -> float:
        """How effective this component is (0.0–1.0+)."""
        quality_mult = {
            ComponentQuality.STANDARD: 1.0,
            ComponentQuality.ALIEN: 0.8,
            ComponentQuality.FEDERATION: 1.5,
        }
        return (self.condition / 100.0) * quality_mult[self.quality] * (1.0 + self.stats_bonus)


@dataclass
class ShipSystem:
    """A mothership system that requires maintenance."""

    system_type: SystemType
    name: str
    description: str
    maintenance_level: float = 100.0  # 0–100
    upgrade_tier: int = 1             # 1–5
    components: list[Component] = field(default_factory=list)

    # Degradation rates
    passive_decay_rate: float = 0.1   # Per in-game turn
    ftl_decay_rate: float = 5.0       # Per FTL jump

    @property
    def effectiveness(self) -> float:
        """Overall system effectiveness (0.0–1.0+)."""
        base = self.maintenance_level / 100.0
        if self.components:
            comp_avg = sum(c.effectiveness for c in self.components) / len(self.components)
            return base * comp_avg * (1 + (self.upgrade_tier - 1) * 0.1)
        return base * (1 + (self.upgrade_tier - 1) * 0.1)

    def degrade(self, amount: float) -> None:
        """Reduce maintenance level."""
        self.maintenance_level = max(0, self.maintenance_level - amount)
        for comp in self.components:
            comp.condition = max(0, comp.condition - amount * 0.5)

    def repair(self, amount: float) -> None:
        """Increase maintenance level (costs resources externally)."""
        self.maintenance_level = min(100, self.maintenance_level + amount)

    def repair_cost(self, amount: float) -> dict[str, int]:
        """Calculate resource cost to repair by given amount."""
        metal = int(amount * 5 * self.upgrade_tier)
        energy = int(amount * 3 * self.upgrade_tier)
        return {"metal": metal, "energy": energy}

    @property
    def is_critical(self) -> bool:
        return self.maintenance_level < 25

    @property
    def is_warning(self) -> bool:
        return self.maintenance_level < 50


def create_default_systems() -> list[ShipSystem]:
    """Create the default set of mothership systems."""
    return [
        ShipSystem(
            system_type=SystemType.LIFE_SUPPORT,
            name="Life Support",
            description="Atmosphere, water recycling, and food production for the crew.",
            components=[
                Component("Air Recycler", ComponentQuality.STANDARD),
                Component("Water Purifier", ComponentQuality.STANDARD),
                Component("Food Synthesizer", ComponentQuality.STANDARD),
            ],
        ),
        ShipSystem(
            system_type=SystemType.THRUSTERS,
            name="Sublight Thrusters",
            description="Primary propulsion for in-system travel.",
            passive_decay_rate=0.15,
            components=[
                Component("Thruster Array A", ComponentQuality.STANDARD),
                Component("Thruster Array B", ComponentQuality.STANDARD),
                Component("Fuel Injector", ComponentQuality.STANDARD),
            ],
        ),
        ShipSystem(
            system_type=SystemType.POWER_CORE,
            name="Power Core",
            description="Main reactor providing energy to all systems.",
            passive_decay_rate=0.12,
            ftl_decay_rate=8.0,
            components=[
                Component("Primary Reactor", ComponentQuality.STANDARD),
                Component("Backup Reactor", ComponentQuality.STANDARD),
                Component("Power Distributor", ComponentQuality.STANDARD),
            ],
        ),
        ShipSystem(
            system_type=SystemType.SENSORS,
            name="Sensor Array",
            description="Long-range scanners and navigation systems.",
            components=[
                Component("Deep Scanner", ComponentQuality.STANDARD),
                Component("Navigation Computer", ComponentQuality.STANDARD),
            ],
        ),
        ShipSystem(
            system_type=SystemType.WEAPONS_ARRAY,
            name="Weapons Systems",
            description="Fire control, targeting, and weapon power conduits.",
            passive_decay_rate=0.08,
            components=[
                Component("Fire Control", ComponentQuality.STANDARD),
                Component("Targeting Computer", ComponentQuality.STANDARD),
                Component("Power Conduit", ComponentQuality.STANDARD),
            ],
        ),
        ShipSystem(
            system_type=SystemType.HANGAR,
            name="Hangar Bay",
            description="Fleet docking, repair, and launch facilities.",
            components=[
                Component("Launch Catapult", ComponentQuality.STANDARD),
                Component("Repair Gantry", ComponentQuality.STANDARD),
            ],
        ),
        ShipSystem(
            system_type=SystemType.CRYO_VAULTS,
            name="Cryo Vaults",
            description="Cryogenic storage for colonists. Failure means death.",
            passive_decay_rate=0.05,
            ftl_decay_rate=3.0,
            components=[
                Component("Cryo Unit Alpha", ComponentQuality.STANDARD),
                Component("Cryo Unit Beta", ComponentQuality.STANDARD),
                Component("Temperature Regulator", ComponentQuality.STANDARD),
            ],
        ),
        ShipSystem(
            system_type=SystemType.SHIELDS,
            name="Shield Generator",
            description="Energy shielding for the mothership.",
            passive_decay_rate=0.1,
            components=[
                Component("Shield Emitter", ComponentQuality.STANDARD),
                Component("Shield Capacitor", ComponentQuality.STANDARD),
            ],
        ),
    ]


def apply_ftl_decay(systems: list[ShipSystem], distance_factor: float = 1.0) -> list[str]:
    """Apply FTL travel degradation to all systems. Returns warning messages."""
    warnings: list[str] = []
    for system in systems:
        decay = system.ftl_decay_rate * distance_factor
        system.degrade(decay)
        if system.is_critical:
            warnings.append(f"⚠ {system.name} critically low ({system.maintenance_level:.0f}%)!")
        elif system.is_warning:
            warnings.append(f"{system.name} degraded to {system.maintenance_level:.0f}%")
    return warnings
