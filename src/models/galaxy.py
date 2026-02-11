"""Procedural galaxy generation for Hollowed Stars."""

from __future__ import annotations

import enum
import math
import random
from dataclasses import dataclass, field


class StarType(enum.Enum):
    """Types of stars in the galaxy."""

    RED_DWARF = "red_dwarf"
    YELLOW = "yellow"
    BLUE_GIANT = "blue_giant"
    NEUTRON = "neutron"
    BLACK_HOLE = "black_hole"


# Weighted probabilities for star types
_STAR_WEIGHTS: list[tuple[StarType, int]] = [
    (StarType.RED_DWARF, 40),
    (StarType.YELLOW, 30),
    (StarType.BLUE_GIANT, 15),
    (StarType.NEUTRON, 10),
    (StarType.BLACK_HOLE, 5),
]


class ObjectType(enum.Enum):
    """Types of objects found in star systems."""

    PLANET = "planet"
    ASTEROID_FIELD = "asteroid_field"
    DERELICT = "derelict"
    ANOMALY = "anomaly"
    STATION_RUIN = "station_ruin"
    ALIEN_OUTPOST = "alien_outpost"


@dataclass
class SystemObject:
    """An object orbiting within a star system."""

    obj_type: ObjectType
    name: str
    description: str
    orbit_radius: float  # Distance from star (0.0–1.0 normalized)
    orbit_angle: float  # Current angle in radians
    surveyed: bool = False
    danger_level: int = 0  # 0 = safe, 1–5 = increasing risk
    loot_value: int = 0  # Resource reward for surveying/salvaging


@dataclass
class StarSystem:
    """A single star system in the galaxy."""

    id: int
    name: str
    x: float  # Galaxy-space position
    y: float
    star_type: StarType
    objects: list[SystemObject] = field(default_factory=list)
    connections: list[int] = field(default_factory=list)  # IDs of connected systems
    visited: bool = False
    danger_level: int = 0  # Overall system danger (0–5)


# ---------------------------------------------------------------------------
# Name generation
# ---------------------------------------------------------------------------

_PREFIXES = [
    "Ald", "Bel", "Cor", "Den", "Eri", "Fom", "Gal", "Hyd", "Ith",
    "Jov", "Kep", "Lyr", "Mir", "Neb", "Ori", "Pol", "Qua", "Rig",
    "Sol", "Tau", "Ult", "Veg", "Wol", "Xen", "Ygg", "Zan",
]

_SUFFIXES = [
    "aris", "eon", "ix", "us", "ara", "ion", "ax", "is", "or",
    "ium", "oth", "ael", "ine", "ova", "ux", "enn", "ark", "os",
]

_DESIGNATIONS = [
    "Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta", "Eta",
    "Theta", "Iota", "Kappa", "Lambda", "Mu", "Nu", "Xi", "Omicron",
    "Pi", "Rho", "Sigma", "Tau", "Upsilon", "Phi", "Chi", "Psi", "Omega",
]


def _generate_system_name(rng: random.Random) -> str:
    """Generate a procedural star system name."""
    style = rng.randint(0, 2)
    if style == 0:
        # "Aldaris" style
        return rng.choice(_PREFIXES) + rng.choice(_SUFFIXES)
    elif style == 1:
        # "Aldaris Beta" style
        return rng.choice(_PREFIXES) + rng.choice(_SUFFIXES) + " " + rng.choice(_DESIGNATIONS)
    else:
        # "HD-47291" catalogue style
        catalogue = rng.choice(["HD", "GJ", "HR", "TYC", "KOI"])
        number = rng.randint(1000, 99999)
        return f"{catalogue}-{number}"


# ---------------------------------------------------------------------------
# Object generation
# ---------------------------------------------------------------------------

_PLANET_NAMES = [
    "barren world", "frozen wasteland", "gas giant", "molten rock",
    "dust world", "ice planet", "volcanic moon", "shattered planet",
]

_DERELICT_NAMES = [
    "Federation cruiser wreck", "abandoned cargo hauler", "drifting warship hull",
    "ancient research station", "deactivated defense platform", "colony ship husk",
]

_ANOMALY_NAMES = [
    "spatial distortion", "energy signature", "unknown signal source",
    "quantum fluctuation", "gravitational anomaly", "temporal echo",
]


def _generate_objects(rng: random.Random, danger: int) -> list[SystemObject]:
    """Generate objects for a star system based on danger level."""
    objects: list[SystemObject] = []

    # Planets (1–4)
    num_planets = rng.randint(1, 4)
    for i in range(num_planets):
        name = rng.choice(_PLANET_NAMES).title()
        objects.append(
            SystemObject(
                obj_type=ObjectType.PLANET,
                name=name,
                description=f"A {name.lower()} orbiting the star.",
                orbit_radius=0.2 + (i * 0.2),
                orbit_angle=rng.uniform(0, math.tau),
                danger_level=0,
                loot_value=rng.randint(0, 50),
            )
        )

    # Asteroid fields (0–2)
    for _ in range(rng.randint(0, 2)):
        objects.append(
            SystemObject(
                obj_type=ObjectType.ASTEROID_FIELD,
                name="Asteroid Field",
                description="Dense cluster of mineable asteroids.",
                orbit_radius=rng.uniform(0.3, 0.9),
                orbit_angle=rng.uniform(0, math.tau),
                danger_level=0,
                loot_value=rng.randint(100, 400),
            )
        )

    # Derelicts (chance increases with danger)
    if rng.random() < 0.3 + danger * 0.1:
        derelict_name = rng.choice(_DERELICT_NAMES).title()
        objects.append(
            SystemObject(
                obj_type=ObjectType.DERELICT,
                name=derelict_name,
                description="Wreckage from the old federation. Could hold valuable salvage... or worse.",
                orbit_radius=rng.uniform(0.1, 0.8),
                orbit_angle=rng.uniform(0, math.tau),
                danger_level=rng.randint(0, min(danger + 1, 5)),
                loot_value=rng.randint(200, 800),
            )
        )

    # Anomalies (rare)
    if rng.random() < 0.15 + danger * 0.05:
        anomaly_name = rng.choice(_ANOMALY_NAMES).title()
        objects.append(
            SystemObject(
                obj_type=ObjectType.ANOMALY,
                name=anomaly_name,
                description="An unexplained phenomenon. Investigation may yield discoveries... or disaster.",
                orbit_radius=rng.uniform(0.2, 0.7),
                orbit_angle=rng.uniform(0, math.tau),
                danger_level=rng.randint(1, min(danger + 2, 5)),
                loot_value=rng.randint(300, 1000),
            )
        )

    # Alien outpost (rare, mid-danger)
    if danger >= 2 and rng.random() < 0.2:
        objects.append(
            SystemObject(
                obj_type=ObjectType.ALIEN_OUTPOST,
                name="Alien Outpost",
                description="A settlement of one of the new species. They may trade... or attack.",
                orbit_radius=rng.uniform(0.3, 0.6),
                orbit_angle=rng.uniform(0, math.tau),
                danger_level=rng.randint(1, 3),
                loot_value=0,
            )
        )

    return objects


# ---------------------------------------------------------------------------
# Galaxy generation
# ---------------------------------------------------------------------------


class Galaxy:
    """Procedurally generated galaxy of connected star systems."""

    def __init__(self, num_systems: int = 40, seed: int | None = None) -> None:
        self.seed = seed if seed is not None else random.randint(0, 2**32)
        self.rng = random.Random(self.seed)
        self.systems: list[StarSystem] = []
        self.current_system_id: int = 0

        self._generate(num_systems)

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    def _generate(self, num_systems: int) -> None:
        """Build the galaxy: place systems, connect them, populate objects."""
        self._place_systems(num_systems)
        self._connect_systems()
        self._populate_systems()

        # Mark starting system as safe and visited
        start = self.systems[0]
        start.danger_level = 0
        start.visited = True
        # Ensure starting system has at least some asteroids to mine
        has_asteroids = any(o.obj_type == ObjectType.ASTEROID_FIELD for o in start.objects)
        if not has_asteroids:
            start.objects.append(
                SystemObject(
                    obj_type=ObjectType.ASTEROID_FIELD,
                    name="Asteroid Field",
                    description="A rich cluster of mineable asteroids.",
                    orbit_radius=0.5,
                    orbit_angle=self.rng.uniform(0, math.tau),
                    danger_level=0,
                    loot_value=300,
                )
            )

    def _place_systems(self, count: int) -> None:
        """Position star systems using Poisson-disk-like placement."""
        used_names: set[str] = set()
        min_dist = 80.0  # Minimum distance between systems
        galaxy_radius = 600.0

        for i in range(count):
            # Generate position with minimum spacing
            for _ in range(100):  # Max attempts
                angle = self.rng.uniform(0, math.tau)
                # Bias toward center for denser core
                r = galaxy_radius * math.sqrt(self.rng.uniform(0.01, 1.0))
                x = r * math.cos(angle)
                y = r * math.sin(angle)

                # Check minimum distance to existing systems
                too_close = False
                for s in self.systems:
                    dx = x - s.x
                    dy = y - s.y
                    if math.sqrt(dx * dx + dy * dy) < min_dist:
                        too_close = True
                        break

                if not too_close:
                    break

            # Generate unique name
            name = _generate_system_name(self.rng)
            while name in used_names:
                name = _generate_system_name(self.rng)
            used_names.add(name)

            # Pick star type
            star_type = self._weighted_star_type()

            self.systems.append(
                StarSystem(id=i, name=name, x=x, y=y, star_type=star_type)
            )

    def _weighted_star_type(self) -> StarType:
        """Pick a star type based on weighted probabilities."""
        total = sum(w for _, w in _STAR_WEIGHTS)
        roll = self.rng.randint(1, total)
        cumulative = 0
        for star_type, weight in _STAR_WEIGHTS:
            cumulative += weight
            if roll <= cumulative:
                return star_type
        return StarType.RED_DWARF  # Fallback

    def _connect_systems(self) -> None:
        """Connect nearby systems to form a navigable graph."""
        max_connection_dist = 200.0
        max_connections = 5

        for sys_a in self.systems:
            # Sort other systems by distance
            others = sorted(
                self.systems,
                key=lambda s: math.hypot(s.x - sys_a.x, s.y - sys_a.y),
            )

            for sys_b in others:
                if sys_b.id == sys_a.id:
                    continue
                if len(sys_a.connections) >= max_connections:
                    break

                dist = math.hypot(sys_b.x - sys_a.x, sys_b.y - sys_a.y)
                if dist > max_connection_dist:
                    break

                # Add bidirectional connection
                if sys_b.id not in sys_a.connections:
                    sys_a.connections.append(sys_b.id)
                if sys_a.id not in sys_b.connections:
                    sys_b.connections.append(sys_a.id)

        # Ensure connectivity: connect any isolated systems to nearest neighbor
        for sys_a in self.systems:
            if not sys_a.connections:
                nearest = min(
                    (s for s in self.systems if s.id != sys_a.id),
                    key=lambda s: math.hypot(s.x - sys_a.x, s.y - sys_a.y),
                )
                sys_a.connections.append(nearest.id)
                nearest.connections.append(sys_a.id)

    def _populate_systems(self) -> None:
        """Fill each system with objects, scaling danger with distance from start."""
        start = self.systems[0]
        max_dist = max(
            math.hypot(s.x - start.x, s.y - start.y) for s in self.systems
        )

        for system in self.systems:
            dist = math.hypot(system.x - start.x, system.y - start.y)
            # Danger scales 0–5 with distance from start
            danger = int((dist / max(max_dist, 1)) * 5)
            system.danger_level = min(danger, 5)
            system.objects = _generate_objects(self.rng, system.danger_level)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    @property
    def current_system(self) -> StarSystem:
        return self.systems[self.current_system_id]

    def get_system(self, system_id: int) -> StarSystem:
        return self.systems[system_id]

    def get_connected_systems(self, system_id: int) -> list[StarSystem]:
        sys = self.systems[system_id]
        return [self.systems[sid] for sid in sys.connections]

    def travel_to(self, system_id: int) -> bool:
        """Attempt FTL travel to a connected system. Returns True if valid."""
        if system_id in self.current_system.connections:
            self.current_system_id = system_id
            self.systems[system_id].visited = True
            return True
        return False
