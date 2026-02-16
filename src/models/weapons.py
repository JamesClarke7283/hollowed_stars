"""Weapon definitions for Hollowed Stars.

PLAN.md defines 6 craftable + 3 federation-only weapon types:
- Missile: long range, material cost, countered by PD, multiple warheads
- Railgun: medium range, energy cost, massive single-target, slow recharge
- SMAC: medium range, both costs, splits into slugs, bypasses mid PD
- Autocannon: short range, low cost, high ROF, anti-small only
- Laser: short range, extreme energy, no PD counter, dual PD mode
- PD Cannon: short range, cheap, guaranteed intercept, can't attack
- (Fed) Neutron Beam: short range, low cost, kills crew, ruins salvage
- (Fed) Anti-matter Device: medium range, extreme energy, no salvage
- (Fed) Flagship Beam: long range, extreme energy, Signal of Dawn only
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field


class WeaponType(enum.Enum):
    """All weapon types in the game."""

    # Craftable
    MISSILE = "missile"
    RAILGUN = "railgun"
    SMAC = "smac"
    AUTOCANNON = "autocannon"
    LASER = "laser"
    PD_CANNON = "pd_cannon"

    # Old Federation only (salvage)
    NEUTRON_BEAM = "neutron_beam"
    ANTIMATTER_DEVICE = "antimatter_device"
    FLAGSHIP_BEAM = "flagship_beam"


class WeaponRange(enum.Enum):
    """Engagement ranges."""

    SHORT = "short"      # ~100 units
    MEDIUM = "medium"    # ~250 units
    LONG = "long"        # ~500 units


class WarheadType(enum.Enum):
    """Missile warhead variants."""

    HE = "he"                    # Standard high explosive
    NUCLEAR = "nuclear"          # High damage, area effect
    BLACK_HOLE = "black_hole"    # Federation tech, devastating


class SpecialEffect(enum.Enum):
    """Special weapon effects applied on hit."""

    NONE = "none"
    AREA_DAMAGE = "area_damage"           # Hits nearby ships too
    ARMOR_PIERCING = "armor_piercing"     # Ignores % of armor
    CREW_KILL = "crew_kill"               # Kills crew, leaves hull
    ANNIHILATE = "annihilate"             # Destroys everything, no salvage
    PD_INTERCEPT = "pd_intercept"         # Can shoot down missiles/drones
    SPLIT_PROJECTILE = "split_projectile" # Splits into multiple hits
    BYPASSES_PD = "bypasses_pd"           # Cannot be intercepted


@dataclass
class Weapon:
    """A weapon that can be mounted on a ship."""

    name: str
    weapon_type: WeaponType
    size: str  # "small", "medium", "large", "capital"
    description: str

    # Combat stats
    damage: int
    range: WeaponRange
    rate_of_fire: float     # Shots per engagement window
    accuracy: float         # 0.0–1.0 base hit chance

    # Costs per shot
    energy_cost: int
    material_cost: int

    # Build/acquire
    build_cost_metal: int
    build_cost_energy: int
    build_cost_rare: int
    can_be_crafted: bool = True

    # Special
    special_effect: SpecialEffect = SpecialEffect.NONE
    can_target_missiles: bool = False  # PD mode
    pd_mode_available: bool = False    # Laser PD toggle

    # Missile-specific
    warhead: WarheadType | None = None


# ---------------------------------------------------------------------------
# Weapon definitions — organized by type
# Each type has small/medium/large variants where applicable
# ---------------------------------------------------------------------------

# --- Missiles ---
# Long range, material cost, versatile, countered by PD

MISSILE_SMALL_HE = Weapon(
    name="Light Missile Launcher",
    weapon_type=WeaponType.MISSILE,
    size="small",
    description="Standard light missile rack. Reliable but vulnerable to PD.",
    damage=80,
    range=WeaponRange.LONG,
    rate_of_fire=3.0,
    accuracy=0.85,
    energy_cost=10,
    material_cost=30,
    build_cost_metal=200,
    build_cost_energy=100,
    build_cost_rare=0,
    warhead=WarheadType.HE,
)

MISSILE_MEDIUM_HE = Weapon(
    name="Missile Battery",
    weapon_type=WeaponType.MISSILE,
    size="medium",
    description="Medium missile battery with improved warheads.",
    damage=160,
    range=WeaponRange.LONG,
    rate_of_fire=2.5,
    accuracy=0.85,
    energy_cost=20,
    material_cost=60,
    build_cost_metal=500,
    build_cost_energy=250,
    build_cost_rare=20,
    warhead=WarheadType.HE,
)

MISSILE_LARGE_HE = Weapon(
    name="Heavy Missile Array",
    weapon_type=WeaponType.MISSILE,
    size="large",
    description="Massive missile array. Devastating volleys at extreme range.",
    damage=300,
    range=WeaponRange.LONG,
    rate_of_fire=2.0,
    accuracy=0.80,
    energy_cost=40,
    material_cost=120,
    build_cost_metal=1200,
    build_cost_energy=600,
    build_cost_rare=80,
    warhead=WarheadType.HE,
)

MISSILE_NUCLEAR = Weapon(
    name="Nuclear Missile Launcher",
    weapon_type=WeaponType.MISSILE,
    size="large",
    description="Nuclear warheads. Extreme damage with area effect.",
    damage=600,
    range=WeaponRange.LONG,
    rate_of_fire=1.0,
    accuracy=0.80,
    energy_cost=60,
    material_cost=250,
    build_cost_metal=2000,
    build_cost_energy=1000,
    build_cost_rare=200,
    warhead=WarheadType.NUCLEAR,
    special_effect=SpecialEffect.AREA_DAMAGE,
)

MISSILE_BLACK_HOLE = Weapon(
    name="Singularity Torpedo",
    weapon_type=WeaponType.MISSILE,
    size="capital",
    description="Old federation black hole warhead. Creates a localized singularity.",
    damage=2000,
    range=WeaponRange.LONG,
    rate_of_fire=0.5,
    accuracy=0.90,
    energy_cost=100,
    material_cost=500,
    build_cost_metal=0,
    build_cost_energy=0,
    build_cost_rare=0,
    can_be_crafted=False,
    warhead=WarheadType.BLACK_HOLE,
    special_effect=SpecialEffect.ANNIHILATE,
)

# --- Railgun ---
# Medium range, energy cost, massive single-target, slow recharge

RAILGUN_MEDIUM = Weapon(
    name="Railgun",
    weapon_type=WeaponType.RAILGUN,
    size="medium",
    description="Electromagnetic accelerator. Devastating against heavy targets.",
    damage=400,
    range=WeaponRange.MEDIUM,
    rate_of_fire=0.5,
    accuracy=0.90,
    energy_cost=150,
    material_cost=5,
    build_cost_metal=600,
    build_cost_energy=400,
    build_cost_rare=50,
    special_effect=SpecialEffect.ARMOR_PIERCING,
)

RAILGUN_LARGE = Weapon(
    name="Heavy Railgun",
    weapon_type=WeaponType.RAILGUN,
    size="large",
    description="Capital-grade railgun. Can punch clean through a cruiser.",
    damage=800,
    range=WeaponRange.MEDIUM,
    rate_of_fire=0.3,
    accuracy=0.85,
    energy_cost=300,
    material_cost=10,
    build_cost_metal=1500,
    build_cost_energy=1000,
    build_cost_rare=150,
    special_effect=SpecialEffect.ARMOR_PIERCING,
)

RAILGUN_CAPITAL = Weapon(
    name="Spinal Railgun",
    weapon_type=WeaponType.RAILGUN,
    size="capital",
    description="Ship-length magnetic accelerator. One shot, one kill.",
    damage=1500,
    range=WeaponRange.MEDIUM,
    rate_of_fire=0.2,
    accuracy=0.80,
    energy_cost=600,
    material_cost=20,
    build_cost_metal=3000,
    build_cost_energy=2000,
    build_cost_rare=300,
    special_effect=SpecialEffect.ARMOR_PIERCING,
)

# --- SMAC (Scattering Missile Accelerator Cannon) ---
# Medium range, both costs, splits into slugs, bypasses mid PD

SMAC_LARGE = Weapon(
    name="SMAC Launcher",
    weapon_type=WeaponType.SMAC,
    size="large",
    description="Accelerates a missile that splits into hundreds of slugs.",
    damage=1000,
    range=WeaponRange.MEDIUM,
    rate_of_fire=0.3,
    accuracy=0.75,
    energy_cost=400,
    material_cost=200,
    build_cost_metal=2000,
    build_cost_energy=1500,
    build_cost_rare=250,
    special_effect=SpecialEffect.SPLIT_PROJECTILE,
)

SMAC_CAPITAL = Weapon(
    name="Heavy SMAC",
    weapon_type=WeaponType.SMAC,
    size="capital",
    description="Capital-grade SMAC. A storm of death that nothing survives.",
    damage=2000,
    range=WeaponRange.MEDIUM,
    rate_of_fire=0.2,
    accuracy=0.70,
    energy_cost=700,
    material_cost=400,
    build_cost_metal=4000,
    build_cost_energy=3000,
    build_cost_rare=500,
    special_effect=SpecialEffect.SPLIT_PROJECTILE,
)

# --- Autocannon ---
# Short range, low cost, high ROF, anti-small

AUTOCANNON_SMALL = Weapon(
    name="Light Autocannon",
    weapon_type=WeaponType.AUTOCANNON,
    size="small",
    description="Rapid-fire kinetic weapon. Shreds drones and fighters.",
    damage=25,
    range=WeaponRange.SHORT,
    rate_of_fire=8.0,
    accuracy=0.70,
    energy_cost=5,
    material_cost=5,
    build_cost_metal=100,
    build_cost_energy=50,
    build_cost_rare=0,
)

AUTOCANNON_MEDIUM = Weapon(
    name="Twin Autocannon",
    weapon_type=WeaponType.AUTOCANNON,
    size="medium",
    description="Dual-barrel autocannon. Effective up to corvette-class.",
    damage=50,
    range=WeaponRange.SHORT,
    rate_of_fire=6.0,
    accuracy=0.65,
    energy_cost=10,
    material_cost=10,
    build_cost_metal=300,
    build_cost_energy=150,
    build_cost_rare=10,
)

# --- Laser ---
# Short range, extreme energy, can't be PD'd, has PD mode

LASER_MEDIUM = Weapon(
    name="Focusing Laser",
    weapon_type=WeaponType.LASER,
    size="medium",
    description="Concentrated beam. Cannot be intercepted by point defence.",
    damage=200,
    range=WeaponRange.SHORT,
    rate_of_fire=2.0,
    accuracy=0.95,
    energy_cost=250,
    material_cost=0,
    build_cost_metal=800,
    build_cost_energy=600,
    build_cost_rare=100,
    special_effect=SpecialEffect.BYPASSES_PD,
    pd_mode_available=True,
)

LASER_LARGE = Weapon(
    name="Heavy Beam Laser",
    weapon_type=WeaponType.LASER,
    size="large",
    description="High-intensity beam. Melts through armor like nothing.",
    damage=450,
    range=WeaponRange.SHORT,
    rate_of_fire=1.5,
    accuracy=0.95,
    energy_cost=500,
    material_cost=0,
    build_cost_metal=2000,
    build_cost_energy=1500,
    build_cost_rare=250,
    special_effect=SpecialEffect.BYPASSES_PD,
    pd_mode_available=True,
)

# --- PD Cannon ---
# Short range, cheap, guaranteed intercept, can't attack enemies

PD_CANNON_SMALL = Weapon(
    name="Point Defence Turret",
    weapon_type=WeaponType.PD_CANNON,
    size="small",
    description="Automated turret. Guaranteed to destroy one incoming projectile.",
    damage=0,
    range=WeaponRange.SHORT,
    rate_of_fire=4.0,
    accuracy=1.0,
    energy_cost=5,
    material_cost=2,
    build_cost_metal=80,
    build_cost_energy=40,
    build_cost_rare=0,
    can_target_missiles=True,
    special_effect=SpecialEffect.PD_INTERCEPT,
)

# --- Old Federation weapons (cannot be crafted, salvage only) ---

NEUTRON_BEAM = Weapon(
    name="Neutron Beam Emitter",
    weapon_type=WeaponType.NEUTRON_BEAM,
    size="large",
    description="Turns biological life into goo and circuits into scrap. Ship hull remains intact but unsalvageable.",
    damage=800,
    range=WeaponRange.SHORT,
    rate_of_fire=1.0,
    accuracy=0.95,
    energy_cost=80,
    material_cost=0,
    build_cost_metal=0,
    build_cost_energy=0,
    build_cost_rare=0,
    can_be_crafted=False,
    special_effect=SpecialEffect.CREW_KILL,
)

ANTIMATTER_DEVICE = Weapon(
    name="Anti-Matter Conversion Device",
    weapon_type=WeaponType.ANTIMATTER_DEVICE,
    size="capital",
    description="Converts part of the target into anti-matter. Total annihilation, no salvage.",
    damage=3000,
    range=WeaponRange.MEDIUM,
    rate_of_fire=0.3,
    accuracy=0.90,
    energy_cost=1500,
    material_cost=0,
    build_cost_metal=0,
    build_cost_energy=0,
    build_cost_rare=0,
    can_be_crafted=False,
    special_effect=SpecialEffect.ANNIHILATE,
)

FLAGSHIP_BEAM = Weapon(
    name="Experimental Flagship Beam",
    weapon_type=WeaponType.FLAGSHIP_BEAM,
    size="capital",
    description="Colossal beam weapon. Superior range, devastating damage. Signal of Dawn only.",
    damage=2500,
    range=WeaponRange.LONG,
    rate_of_fire=0.5,
    accuracy=0.95,
    energy_cost=2000,
    material_cost=0,
    build_cost_metal=0,
    build_cost_energy=0,
    build_cost_rare=0,
    can_be_crafted=False,
    special_effect=SpecialEffect.BYPASSES_PD,
)


# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------

ALL_WEAPONS: list[Weapon] = [
    MISSILE_SMALL_HE, MISSILE_MEDIUM_HE, MISSILE_LARGE_HE,
    MISSILE_NUCLEAR, MISSILE_BLACK_HOLE,
    RAILGUN_MEDIUM, RAILGUN_LARGE, RAILGUN_CAPITAL,
    SMAC_LARGE, SMAC_CAPITAL,
    AUTOCANNON_SMALL, AUTOCANNON_MEDIUM,
    LASER_MEDIUM, LASER_LARGE,
    PD_CANNON_SMALL,
    NEUTRON_BEAM, ANTIMATTER_DEVICE, FLAGSHIP_BEAM,
]

CRAFTABLE_WEAPONS: list[Weapon] = [w for w in ALL_WEAPONS if w.can_be_crafted]

FEDERATION_WEAPONS: list[Weapon] = [w for w in ALL_WEAPONS if not w.can_be_crafted]


def weapons_for_size(size: str) -> list[Weapon]:
    """Get all craftable weapons that fit a given mount size."""
    return [w for w in CRAFTABLE_WEAPONS if w.size == size]


# Name → Weapon mapping for quick lookup (used by combat engine)
_WEAPON_BY_NAME: dict[str, Weapon] = {w.name: w for w in ALL_WEAPONS}


def weapon_by_name(name: str) -> Weapon | None:
    """Look up a weapon definition by its name string."""
    return _WEAPON_BY_NAME.get(name)
