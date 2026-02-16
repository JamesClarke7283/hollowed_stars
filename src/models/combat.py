"""Combat engine for Hollowed Stars.

Implements PLAN.md orbital interception combat:
- Ships match enemy orbit for brief engagement windows
- Formation is set pre-combat and locked during
- Fleet ships plan 2 turns ahead; mothership is directly controlled
- PD intercepts missiles, lasers bypass PD
"""

from __future__ import annotations

import enum
import math
import random
from dataclasses import dataclass, field

from .ships import Fleet, FleetShip, ShipClass, SHIP_CLASS_STATS, WeaponSize
from .weapons import (
    Weapon,
    WeaponRange,
    WeaponType,
    SpecialEffect,
    AUTOCANNON_SMALL,
    MISSILE_SMALL_HE,
    MISSILE_MEDIUM_HE,
    RAILGUN_MEDIUM,
    PD_CANNON_SMALL,
    LASER_MEDIUM,
    weapon_by_name,
    weapons_for_size,
)


class CombatPhase(enum.Enum):
    """Phases of combat."""

    SETUP = "setup"              # Pre-combat: set formation
    APPROACH = "approach"        # Orbits converging
    ENGAGEMENT = "engagement"    # Firing window open
    DISENGAGE = "disengage"      # Orbits diverging
    RESOLUTION = "resolution"    # Post-combat: salvage/flee


@dataclass
class CombatShip:
    """A ship participating in combat (player or enemy)."""

    name: str
    ship_class: ShipClass
    hull: int
    max_hull: int
    armor: int
    weapons: list[Weapon] = field(default_factory=list)
    formation_slot: int = 0

    # Combat state
    is_destroyed: bool = False
    energy_remaining: int = 1000
    pd_charges: int = 0  # How many missiles PD can intercept this window

    # Link back to FleetShip (player ships only)
    fleet_ship_ref: FleetShip | None = None

    # Is this the mothership? (directly controlled per PLAN.md)
    is_mothership: bool = False

    # Action queue (2-turn lookahead per PLAN.md, for fleet ships only)
    planned_actions: list[CombatAction | None] = field(default_factory=lambda: [None, None])

    @property
    def is_alive(self) -> bool:
        return not self.is_destroyed and self.hull > 0

    def take_damage(self, damage: int, armor_piercing: bool = False) -> int:
        """Apply damage accounting for armor. Returns actual damage dealt."""
        effective_armor = 0 if armor_piercing else self.armor
        mitigated = max(0, damage - effective_armor)
        self.hull -= mitigated
        if self.hull <= 0:
            self.hull = 0
            self.is_destroyed = True
        return mitigated


@dataclass
class CombatAction:
    """A planned action for a ship."""

    target_index: int  # Index into enemy fleet
    weapon_index: int  # Index into ship's weapons list


@dataclass
class CombatEvent:
    """A log entry for something that happened during combat."""

    turn: int
    message: str
    event_type: str = "info"  # "hit", "miss", "pd_intercept", "destroyed", "info"


@dataclass
class EnemyFleet:
    """An enemy force encountered in a system."""

    name: str
    description: str
    ships: list[CombatShip] = field(default_factory=list)
    danger_level: int = 1
    loot_metal: int = 0
    loot_energy: int = 0
    loot_rare: int = 0
    is_federation: bool = False

    @property
    def alive_ships(self) -> list[CombatShip]:
        return [s for s in self.ships if s.is_alive]

    @property
    def is_defeated(self) -> bool:
        return len(self.alive_ships) == 0


class CombatEngine:
    """Resolves orbital interception combat."""

    def __init__(
        self,
        player_fleet: Fleet,
        enemy: EnemyFleet,
        seed: int | None = None,
    ) -> None:
        self.player_fleet = player_fleet
        self.enemy = enemy
        self.rng = random.Random(seed)

        self.phase = CombatPhase.SETUP
        self.turn = 0
        self.engagement_turns_remaining = 0
        self.max_engagement_turns = 3  # Firing window size
        self.orbit_progress = 0.0  # 0.0 → 1.0 approach cycle
        self.log: list[CombatEvent] = []

        # Build player combat ships from fleet
        self.player_ships = self._build_player_ships()

    def _build_player_ships(self) -> list[CombatShip]:
        """Convert player fleet data into combat ships."""
        ships: list[CombatShip] = []

        # Mothership is always present
        ms = self.player_fleet.mothership
        mothership_weapons = []
        for slot in ms.weapon_slots:
            mothership_weapons.append(self._resolve_weapon(slot.equipped, slot.size.value))

        ships.append(CombatShip(
            name=ms.name,
            ship_class=ShipClass.BATTLESHIP,  # Mothership fights as battleship
            hull=ms.hull,
            max_hull=ms.max_hull,
            armor=ms.armor,
            weapons=mothership_weapons,
            energy_remaining=ms.power,
            is_mothership=True,
        ))

        # Individual fleet ships (only combat-capable ones)
        for fs in self.player_fleet.ships:
            if not fs.is_combat:
                continue
            # Build weapons from equipped slots
            ship_weapons: list[Weapon] = []
            for slot in fs.weapon_slots:
                ship_weapons.append(self._resolve_weapon(slot.equipped, slot.size.value))
            ships.append(CombatShip(
                name=fs.name,
                ship_class=fs.ship_class,
                hull=fs.hull,
                max_hull=fs.max_hull,
                armor=fs.armor,
                weapons=ship_weapons,
                formation_slot=fs.formation_slot,
                energy_remaining=500,
                fleet_ship_ref=fs,
            ))

        return ships

    def _resolve_weapon(self, equipped_name: str | None, size: str) -> Weapon:
        """Resolve an equipped weapon name to a Weapon, falling back to default."""
        if equipped_name:
            wpn = weapon_by_name(equipped_name)
            if wpn is not None:
                return wpn
        return self._default_weapon_for_size(size)

    def _default_weapon_for_size(self, size: str) -> Weapon:
        """Get a default weapon for a mount size."""
        defaults = {
            "small": AUTOCANNON_SMALL,
            "medium": MISSILE_MEDIUM_HE,
            "large": RAILGUN_MEDIUM,
            "capital": RAILGUN_MEDIUM,
        }
        return defaults.get(size, MISSILE_SMALL_HE)

    # ------------------------------------------------------------------
    # Turn processing
    # ------------------------------------------------------------------

    def advance_turn(self) -> list[CombatEvent]:
        """Process one combat turn. Returns events that occurred."""
        events: list[CombatEvent] = []
        self.turn += 1

        if self.phase == CombatPhase.SETUP:
            self.phase = CombatPhase.APPROACH
            self.orbit_progress = 0.0
            events.append(CombatEvent(self.turn, "Matching enemy orbit...", "info"))

        elif self.phase == CombatPhase.APPROACH:
            self.orbit_progress += 0.33
            if self.orbit_progress >= 1.0:
                self.phase = CombatPhase.ENGAGEMENT
                self.engagement_turns_remaining = self.max_engagement_turns
                events.append(CombatEvent(
                    self.turn,
                    f"ENGAGEMENT WINDOW OPEN — {self.engagement_turns_remaining} turns of fire!",
                    "info",
                ))
            else:
                events.append(CombatEvent(
                    self.turn,
                    f"Closing distance... {int(self.orbit_progress * 100)}%",
                    "info",
                ))

        elif self.phase == CombatPhase.ENGAGEMENT:
            # Process all weapon fire
            fire_events = self._resolve_engagement()
            events.extend(fire_events)

            self.engagement_turns_remaining -= 1
            if self.engagement_turns_remaining <= 0:
                self.phase = CombatPhase.DISENGAGE
                events.append(CombatEvent(self.turn, "Engagement window closing...", "info"))

            # Check victory/defeat
            if self.enemy.is_defeated:
                self.phase = CombatPhase.RESOLUTION
                events.append(CombatEvent(self.turn, "ENEMY FLEET DESTROYED!", "info"))
            elif all(not s.is_alive for s in self.player_ships):
                self.phase = CombatPhase.RESOLUTION
                events.append(CombatEvent(self.turn, "YOUR FLEET HAS BEEN DESTROYED!", "info"))

        elif self.phase == CombatPhase.DISENGAGE:
            self.orbit_progress -= 0.5
            if self.orbit_progress <= 0:
                # Re-approach for another pass
                self.phase = CombatPhase.APPROACH
                self.orbit_progress = 0.0
                events.append(CombatEvent(self.turn, "Orbits diverged. Re-approaching...", "info"))
            else:
                events.append(CombatEvent(self.turn, "Disengaging...", "info"))

        self.log.extend(events)
        return events

    def _resolve_engagement(self) -> list[CombatEvent]:
        """Resolve one turn of weapon fire from both sides."""
        events: list[CombatEvent] = []

        # Player fires at enemies
        for ship in self.player_ships:
            if not ship.is_alive:
                continue
            for weapon in ship.weapons:
                if not self.enemy.alive_ships:
                    break
                target = self.rng.choice(self.enemy.alive_ships)
                fire_events = self._fire_weapon(ship, weapon, target, "player")
                events.extend(fire_events)

        # Enemies fire at player
        for ship in self.enemy.alive_ships:
            for weapon in ship.weapons:
                alive_player = [s for s in self.player_ships if s.is_alive]
                if not alive_player:
                    break
                target = self.rng.choice(alive_player)
                fire_events = self._fire_weapon(ship, weapon, target, "enemy")
                events.extend(fire_events)

        return events

    def _fire_weapon(
        self,
        attacker: CombatShip,
        weapon: Weapon,
        target: CombatShip,
        side: str,
    ) -> list[CombatEvent]:
        """Resolve a single weapon firing. Returns combat events."""
        events: list[CombatEvent] = []

        # Energy check
        if attacker.energy_remaining < weapon.energy_cost:
            return events
        attacker.energy_remaining -= weapon.energy_cost

        # Calculate shots this turn
        shots = max(1, int(weapon.rate_of_fire))

        for _ in range(shots):
            if not target.is_alive:
                break

            # PD intercept check (for missiles)
            if weapon.weapon_type == WeaponType.MISSILE and weapon.special_effect != SpecialEffect.BYPASSES_PD:
                if target.pd_charges > 0:
                    target.pd_charges -= 1
                    events.append(CombatEvent(
                        self.turn,
                        f"PD intercepts {weapon.name} aimed at {target.name}!",
                        "pd_intercept",
                    ))
                    continue

            # Hit check
            if self.rng.random() > weapon.accuracy:
                events.append(CombatEvent(
                    self.turn,
                    f"{attacker.name}'s {weapon.name} misses {target.name}",
                    "miss",
                ))
                continue

            # Damage calculation
            armor_piercing = weapon.special_effect == SpecialEffect.ARMOR_PIERCING
            actual_damage = target.take_damage(weapon.damage, armor_piercing)

            events.append(CombatEvent(
                self.turn,
                f"{attacker.name}'s {weapon.name} hits {target.name} for {actual_damage} damage!",
                "hit",
            ))

            if target.is_destroyed:
                events.append(CombatEvent(
                    self.turn,
                    f"{target.name} DESTROYED!",
                    "destroyed",
                ))

        # Refresh PD charges for PD weapons
        if weapon.weapon_type == WeaponType.PD_CANNON or weapon.can_target_missiles:
            attacker.pd_charges += shots

        return events

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    @property
    def is_over(self) -> bool:
        return self.phase == CombatPhase.RESOLUTION

    @property
    def player_won(self) -> bool:
        return self.is_over and self.enemy.is_defeated

    @property
    def player_alive_count(self) -> int:
        return sum(1 for s in self.player_ships if s.is_alive)

    def apply_results_to_fleet(self) -> dict[str, int]:
        """Apply combat results back to fleet. Returns loot gained."""
        # Update mothership hull
        if self.player_ships:
            ms_combat = self.player_ships[0]
            self.player_fleet.mothership.hull = ms_combat.hull

        # Remove destroyed fleet ships
        destroyed_refs = set()
        for cs in self.player_ships:
            if not cs.is_alive and cs.fleet_ship_ref is not None:
                destroyed_refs.add(id(cs.fleet_ship_ref))
        self.player_fleet.ships = [
            s for s in self.player_fleet.ships if id(s) not in destroyed_refs
        ]

        # Award loot if won
        loot = {"metal": 0, "energy": 0, "rare": 0}
        if self.player_won:
            loot["metal"] = self.enemy.loot_metal
            loot["energy"] = self.enemy.loot_energy
            loot["rare"] = self.enemy.loot_rare
            self.player_fleet.resources.metal += loot["metal"]
            self.player_fleet.resources.energy += loot["energy"]
            self.player_fleet.resources.rare_materials += loot["rare"]

        return loot


# ---------------------------------------------------------------------------
# Ship class combat stats (for enemy generation)
# ---------------------------------------------------------------------------

_DEFAULT_STATS = {
    "hull": 100, "armor": 10, "energy": 200,
    "weapons": lambda: [AUTOCANNON_SMALL],
}

_SHIP_CLASS_STATS: dict[ShipClass, dict] = {
    ShipClass.DRONE: {
        "hull": 30, "armor": 0, "energy": 50,
        "weapons": lambda: [AUTOCANNON_SMALL],
    },
    ShipClass.FIGHTER: {
        "hull": 60, "armor": 5, "energy": 100,
        "weapons": lambda: [AUTOCANNON_SMALL, MISSILE_SMALL_HE],
    },
    ShipClass.CORVETTE: {
        "hull": 150, "armor": 20, "energy": 300,
        "weapons": lambda: [AUTOCANNON_SMALL, MISSILE_SMALL_HE, PD_CANNON_SMALL],
    },
    ShipClass.FRIGATE: {
        "hull": 300, "armor": 40, "energy": 500,
        "weapons": lambda: [MISSILE_MEDIUM_HE, AUTOCANNON_SMALL, PD_CANNON_SMALL],
    },
    ShipClass.DESTROYER: {
        "hull": 500, "armor": 60, "energy": 800,
        "weapons": lambda: [MISSILE_MEDIUM_HE, RAILGUN_MEDIUM, PD_CANNON_SMALL],
    },
    ShipClass.CRUISER: {
        "hull": 800, "armor": 100, "energy": 1200,
        "weapons": lambda: [MISSILE_MEDIUM_HE, RAILGUN_MEDIUM, LASER_MEDIUM, PD_CANNON_SMALL],
    },
    ShipClass.HEAVY_CRUISER: {
        "hull": 1200, "armor": 150, "energy": 1800,
        "weapons": lambda: [MISSILE_MEDIUM_HE, MISSILE_MEDIUM_HE, RAILGUN_MEDIUM, LASER_MEDIUM, PD_CANNON_SMALL],
    },
    ShipClass.BATTLESHIP: {
        "hull": 2000, "armor": 250, "energy": 3000,
        "weapons": lambda: [MISSILE_MEDIUM_HE, MISSILE_MEDIUM_HE, RAILGUN_MEDIUM, RAILGUN_MEDIUM, LASER_MEDIUM, PD_CANNON_SMALL, PD_CANNON_SMALL],
    },
}


# ---------------------------------------------------------------------------
# Enemy generation
# ---------------------------------------------------------------------------

def generate_enemy_fleet(
    danger_level: int,
    is_federation: bool = False,
    rng: random.Random | None = None,
) -> EnemyFleet:
    """Generate an enemy fleet scaled to danger level (1–5)."""
    if rng is None:
        rng = random.Random()

    if is_federation:
        return _generate_federation_fleet(danger_level, rng)

    # Alien fleet — inferior tech but more numerous
    names = [
        "Raider Pack", "Scavenger Band", "Warlord's Vanguard",
        "Hunter Fleet", "Corsair Armada", "Xeno War Party",
    ]

    fleet = EnemyFleet(
        name=rng.choice(names),
        description="A hostile alien fleet.",
        danger_level=danger_level,
        is_federation=False,
    )

    # Scale ship count and quality with danger
    num_ships = danger_level * 2 + rng.randint(1, 3)
    for i in range(num_ships):
        # Higher danger = bigger ships
        if danger_level >= 4 and rng.random() < 0.3:
            ship_class = rng.choice([ShipClass.CRUISER, ShipClass.HEAVY_CRUISER])
        elif danger_level >= 2 and rng.random() < 0.5:
            ship_class = rng.choice([ShipClass.FRIGATE, ShipClass.DESTROYER])
        else:
            ship_class = rng.choice([ShipClass.DRONE, ShipClass.FIGHTER, ShipClass.CORVETTE])

        stats = _SHIP_CLASS_STATS.get(ship_class, _DEFAULT_STATS)
        # Aliens have ~70% of our stats (inferior tech per PLAN.md)
        hull = int(stats["hull"] * 0.7)
        armor = int(stats["armor"] * 0.5)

        fleet.ships.append(CombatShip(
            name=f"Alien {ship_class.value.replace('_', ' ').title()} {i + 1}",
            ship_class=ship_class,
            hull=hull,
            max_hull=hull,
            armor=armor,
            weapons=stats["weapons"](),
            energy_remaining=int(stats["energy"] * 0.7),
            formation_slot=i,
        ))

    fleet.loot_metal = danger_level * 200 + rng.randint(50, 200)
    fleet.loot_energy = danger_level * 100 + rng.randint(25, 100)
    fleet.loot_rare = danger_level * 20 + rng.randint(0, 50)

    return fleet


def _generate_federation_fleet(danger_level: int, rng: random.Random) -> EnemyFleet:
    """Generate an old federation automated fleet (very dangerous)."""
    fleet = EnemyFleet(
        name="Federation Automated Defense Fleet",
        description="Still-functioning machine-driven military forces of the old federation.",
        danger_level=danger_level,
        is_federation=True,
    )

    # Federation ships are MUCH stronger
    num_ships = danger_level + rng.randint(1, 2)
    for i in range(num_ships):
        ship_class = rng.choice([ShipClass.DESTROYER, ShipClass.CRUISER, ShipClass.HEAVY_CRUISER, ShipClass.BATTLESHIP])
        stats = _SHIP_CLASS_STATS.get(ship_class, _DEFAULT_STATS)
        # Federation has 150% of our stats (superior tech per PLAN.md)
        hull = int(stats["hull"] * 1.5)
        armor = int(stats["armor"] * 1.5)

        fleet.ships.append(CombatShip(
            name=f"Fed. {ship_class.value.replace('_', ' ').title()} {i + 1}",
            ship_class=ship_class,
            hull=hull,
            max_hull=hull,
            armor=armor,
            weapons=stats["weapons"](),
            energy_remaining=int(stats["energy"] * 1.5),
            formation_slot=i,
        ))

    fleet.loot_metal = danger_level * 500 + rng.randint(200, 500)
    fleet.loot_energy = danger_level * 300 + rng.randint(100, 300)
    fleet.loot_rare = danger_level * 100 + rng.randint(50, 200)

    return fleet
