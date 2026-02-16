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
    special_tag: str = ""  # Quest-critical tag: "earth", "gateway", "ninurta"


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
# Planet subtypes (PLAN.md: "Most planets are already inhabited")
# ---------------------------------------------------------------------------

class PlanetSubtype(enum.Enum):
    """Planet subtypes that determine description and events."""

    INHABITED = "inhabited"          # Alien civilisation present
    HABITABLE = "habitable"          # Breathable atmosphere, no settlers
    GAS_GIANT = "gas_giant"          # Gas giant with resource moons
    BARREN = "barren"                # Rocky, lifeless
    FROZEN = "frozen"                # Ice world
    VOLCANIC = "volcanic"            # Tectonic activity, rare minerals
    TOXIC = "toxic"                  # Atmosphere deadly, rich in chemicals
    OCEAN = "ocean"                  # Water world, possible life
    SHATTERED = "shattered"          # Broken apart, asteroid-like debris


_PLANET_SUBTYPES_BY_DANGER: dict[int, list[tuple[PlanetSubtype, int]]] = {
    # danger: [(subtype, weight), ...]
    0: [
        (PlanetSubtype.BARREN, 30), (PlanetSubtype.FROZEN, 25),
        (PlanetSubtype.GAS_GIANT, 20), (PlanetSubtype.HABITABLE, 15),
        (PlanetSubtype.OCEAN, 10),
    ],
    1: [
        (PlanetSubtype.BARREN, 25), (PlanetSubtype.FROZEN, 15),
        (PlanetSubtype.GAS_GIANT, 15), (PlanetSubtype.HABITABLE, 15),
        (PlanetSubtype.INHABITED, 10), (PlanetSubtype.OCEAN, 10),
        (PlanetSubtype.VOLCANIC, 10),
    ],
    2: [
        (PlanetSubtype.INHABITED, 25), (PlanetSubtype.BARREN, 15),
        (PlanetSubtype.GAS_GIANT, 15), (PlanetSubtype.VOLCANIC, 15),
        (PlanetSubtype.TOXIC, 10), (PlanetSubtype.HABITABLE, 10),
        (PlanetSubtype.OCEAN, 10),
    ],
    3: [
        (PlanetSubtype.INHABITED, 35), (PlanetSubtype.TOXIC, 15),
        (PlanetSubtype.VOLCANIC, 15), (PlanetSubtype.BARREN, 10),
        (PlanetSubtype.GAS_GIANT, 10), (PlanetSubtype.SHATTERED, 10),
        (PlanetSubtype.FROZEN, 5),
    ],
    4: [
        (PlanetSubtype.INHABITED, 40), (PlanetSubtype.TOXIC, 15),
        (PlanetSubtype.SHATTERED, 15), (PlanetSubtype.VOLCANIC, 10),
        (PlanetSubtype.GAS_GIANT, 10), (PlanetSubtype.BARREN, 10),
    ],
    5: [
        (PlanetSubtype.INHABITED, 45), (PlanetSubtype.SHATTERED, 20),
        (PlanetSubtype.TOXIC, 15), (PlanetSubtype.VOLCANIC, 10),
        (PlanetSubtype.GAS_GIANT, 10),
    ],
}

_PLANET_NAMES: dict[PlanetSubtype, list[str]] = {
    PlanetSubtype.INHABITED: [
        "Settled World", "Alien Colony", "Populous World",
        "Trade Hub", "Fortified World", "Alien Homeworld",
    ],
    PlanetSubtype.HABITABLE: [
        "Garden World", "Temperate World", "Green World",
        "Earthlike World", "Verdant Planet", "Paradise World",
    ],
    PlanetSubtype.GAS_GIANT: [
        "Gas Giant", "Jovian World", "Ringed Giant",
        "Storm World", "Hydrogen Colossus",
    ],
    PlanetSubtype.BARREN: [
        "Barren Rock", "Dust World", "Dead World",
        "Grey Moon", "Airless Rock", "Cratered Wastes",
    ],
    PlanetSubtype.FROZEN: [
        "Frozen Wasteland", "Ice World", "Glacial Planet",
        "Cryo World", "Frozen Moon", "Permafrost World",
    ],
    PlanetSubtype.VOLCANIC: [
        "Volcanic Moon", "Molten World", "Magma Planet",
        "Tectonic World", "Cinder World",
    ],
    PlanetSubtype.TOXIC: [
        "Acid World", "Toxic Wasteland", "Chemical World",
        "Corrosive Planet", "Venomous Atmosphere",
    ],
    PlanetSubtype.OCEAN: [
        "Ocean World", "Water World", "Deep Sea Planet",
        "Tidal World", "Archipelago World",
    ],
    PlanetSubtype.SHATTERED: [
        "Shattered Planet", "Broken World", "Debris Field Planet",
        "Fractured Moon", "Sundered World",
    ],
}

_PLANET_DESCRIPTIONS: dict[PlanetSubtype, list[str]] = {
    PlanetSubtype.INHABITED: [
        "An alien civilisation has taken root here. Their cities glow faintly from orbit.",
        "Sensor readings show an industrial civilisation. They have detected your approach.",
        "A thriving alien settlement. Trade may be possible — or conflict.",
        "Fortified alien installations dot the surface. This species is clearly militaristic.",
        "A busy trade world. Ships of alien design orbit in tight formation.",
    ],
    PlanetSubtype.HABITABLE: [
        "Against all odds, this world has breathable atmosphere and liquid water.",
        "Lush vegetation covers the continents. No intelligent life detected.",
        "A pristine world untouched by civilisation. Could support a colony.",
        "Temperate climate, fertile soil. A potential new home for humanity.",
    ],
    PlanetSubtype.GAS_GIANT: [
        "A massive gas giant with resource-rich moons orbiting it.",
        "Swirling storms of hydrogen and helium. The moons may hold value.",
        "A ringed giant whose moons contain mineable deposits.",
    ],
    PlanetSubtype.BARREN: [
        "A lifeless rock with no atmosphere. Mineral scans are inconclusive.",
        "Nothing but dust and craters. The old federation catalogued it as worthless.",
        "An airless world baked by stellar radiation. Possible subsurface deposits.",
    ],
    PlanetSubtype.FROZEN: [
        "Ice covers everything. Sub-surface oceans may harbour microbial life.",
        "A frozen wasteland lashed by nitrogen storms.",
        "Glaciers stretch from pole to pole. Cryo-materials may be extractable.",
    ],
    PlanetSubtype.VOLCANIC: [
        "Magma flows illuminate the dark side. Rich in rare minerals.",
        "Constant eruptions reshape the surface. Dangerous but mineral-rich.",
        "Tectonic instability makes landing risky, but the rare materials are tempting.",
    ],
    PlanetSubtype.TOXIC: [
        "The atmosphere is a caustic soup of acids and toxic gases.",
        "Chemical clouds obscure the surface. Specialised equipment could extract value.",
        "Lethal to all known life, but the chemical compounds are industrially useful.",
    ],
    PlanetSubtype.OCEAN: [
        "An endless ocean stretches across the entire surface.",
        "Deep water world. Sonar pings reveal vast underwater structures of unknown origin.",
        "Warm oceans teem with primitive aquatic life.",
    ],
    PlanetSubtype.SHATTERED: [
        "Something destroyed this world. Debris orbits where a planet once was.",
        "The remains of a catastrophic impact. Useful materials float among the rubble.",
        "A world cracked apart by forces unknown. Old federation records are blank.",
    ],
}

_DERELICT_NAMES = [
    "Federation Cruiser Wreck", "Abandoned Cargo Hauler", "Drifting Warship Hull",
    "Ancient Research Station", "Deactivated Defense Platform", "Colony Ship Husk",
    "Orbital Foundry Ruin", "Signal Relay Wreckage", "Patrol Corvette Debris",
    "Command Frigate Shell", "Deep Scanner Satellite", "Mining Barge Skeleton",
]

_DERELICT_DESCRIPTIONS = [
    "A wreck from the old federation. 5,000 years of silence, but the hull is intact.",
    "Drifting in the void since before the fall. Salvage teams report mixed readings.",
    "Federation markings are still visible beneath the carbon scoring. Worth investigating.",
    "Automated distress beacon still pulsing after millennia. Contents unknown.",
    "The superstructure is crumpled but internal compartments may be sealed and pressurised.",
    "Blast damage suggests combat. The old federation fought something here.",
]

_STATION_RUIN_NAMES = [
    "Collapsed Station", "Orbital Habitat Ruin", "Federation Outpost Husk",
    "Abandoned Refinery", "Derelict Shipyard", "Burnt-Out Observatory",
]

_STATION_RUIN_DESCRIPTIONS = [
    "The remains of a massive orbital structure. Entire sections have collapsed.",
    "A once-great station now gutted and dark. It still holds its orbit against all odds.",
    "Federation insignia on the outer hull. The interior has been picked over by aliens.",
    "Automated turrets still track your approach. Some may still be active.",
]

_ANOMALY_NAMES = [
    "Spatial Distortion", "Energy Signature", "Unknown Signal Source",
    "Quantum Fluctuation", "Gravitational Anomaly", "Temporal Echo",
    "Dark Matter Bloom", "Subspace Tear", "Chrono-Static Field",
]

_ANOMALY_DESCRIPTIONS = [
    "An unexplained phenomenon that defies known physics.",
    "Your sensors struggle to make sense of the readings.",
    "Something here warps space-time in ways that should not be possible.",
    "The anomaly pulses with energy. Ancient federation records mention similar events.",
    "Navigational computers flag this as extremely dangerous — and extremely valuable.",
]


def _weighted_choice(rng: random.Random, choices: list[tuple], key_idx: int = 1) -> object:
    """Weighted random selection from a list of (item, weight) tuples."""
    total = sum(c[key_idx] for c in choices)
    roll = rng.randint(1, total)
    cumulative = 0
    for choice in choices:
        cumulative += choice[key_idx]
        if roll <= cumulative:
            return choice[0]
    return choices[-1][0]


def _generate_planet(
    rng: random.Random, danger: int, orbit_radius: float, orbit_angle: float,
) -> SystemObject:
    """Generate a single planet with subtype-appropriate attributes."""
    subtypes = _PLANET_SUBTYPES_BY_DANGER.get(danger, _PLANET_SUBTYPES_BY_DANGER[0])
    subtype: PlanetSubtype = _weighted_choice(rng, subtypes)

    name = rng.choice(_PLANET_NAMES[subtype])
    description = rng.choice(_PLANET_DESCRIPTIONS[subtype])

    # Danger and loot scale with planet subtype
    if subtype == PlanetSubtype.INHABITED:
        obj_danger = max(1, danger)
        loot_value = rng.randint(100, 400)
    elif subtype == PlanetSubtype.HABITABLE:
        obj_danger = 0
        loot_value = rng.randint(200, 600)
    elif subtype == PlanetSubtype.VOLCANIC:
        obj_danger = rng.randint(0, 2)
        loot_value = rng.randint(150, 500)
    elif subtype == PlanetSubtype.TOXIC:
        obj_danger = rng.randint(1, 3)
        loot_value = rng.randint(100, 350)
    elif subtype == PlanetSubtype.SHATTERED:
        obj_danger = rng.randint(0, 2)
        loot_value = rng.randint(200, 600)
    elif subtype == PlanetSubtype.OCEAN:
        obj_danger = 0
        loot_value = rng.randint(50, 200)
    elif subtype == PlanetSubtype.GAS_GIANT:
        obj_danger = 0
        loot_value = rng.randint(50, 150)
    else:  # BARREN, FROZEN
        obj_danger = 0
        loot_value = rng.randint(0, 80)

    return SystemObject(
        obj_type=ObjectType.PLANET,
        name=name,
        description=description,
        orbit_radius=orbit_radius,
        orbit_angle=orbit_angle,
        danger_level=obj_danger,
        loot_value=loot_value,
    )


def _generate_objects(rng: random.Random, danger: int) -> list[SystemObject]:
    """Generate objects for a star system based on danger level."""
    objects: list[SystemObject] = []

    # Planets (1–5, more in safer systems)
    num_planets = rng.randint(1, max(2, 5 - danger // 2))
    for i in range(num_planets):
        orbit_radius = 0.15 + (i * 0.18)
        orbit_angle = rng.uniform(0, math.tau)
        objects.append(_generate_planet(rng, danger, orbit_radius, orbit_angle))

    # Asteroid fields (0–3)
    for _ in range(rng.randint(0, 3)):
        objects.append(
            SystemObject(
                obj_type=ObjectType.ASTEROID_FIELD,
                name=rng.choice(["Asteroid Field", "Debris Belt", "Mineral Cluster", "Rocky Belt"]),
                description=rng.choice([
                    "Dense cluster of mineable asteroids rich in metals.",
                    "Scattered rocks and ore deposits. Good mining prospects.",
                    "A thick belt of rocky debris, remnants of a shattered moon.",
                ]),
                orbit_radius=rng.uniform(0.3, 0.95),
                orbit_angle=rng.uniform(0, math.tau),
                danger_level=0,
                loot_value=rng.randint(100, 500),
            )
        )

    # Derelicts (chance increases with danger)
    if rng.random() < 0.25 + danger * 0.12:
        objects.append(
            SystemObject(
                obj_type=ObjectType.DERELICT,
                name=rng.choice(_DERELICT_NAMES),
                description=rng.choice(_DERELICT_DESCRIPTIONS),
                orbit_radius=rng.uniform(0.1, 0.8),
                orbit_angle=rng.uniform(0, math.tau),
                danger_level=rng.randint(0, min(danger + 1, 5)),
                loot_value=rng.randint(200, 800),
            )
        )

    # Station ruins (rare, higher danger)
    if danger >= 2 and rng.random() < 0.15 + danger * 0.05:
        objects.append(
            SystemObject(
                obj_type=ObjectType.STATION_RUIN,
                name=rng.choice(_STATION_RUIN_NAMES),
                description=rng.choice(_STATION_RUIN_DESCRIPTIONS),
                orbit_radius=rng.uniform(0.2, 0.6),
                orbit_angle=rng.uniform(0, math.tau),
                danger_level=rng.randint(1, min(danger + 1, 5)),
                loot_value=rng.randint(300, 1000),
            )
        )

    # Anomalies (rare, mysterious)
    if rng.random() < 0.12 + danger * 0.06:
        objects.append(
            SystemObject(
                obj_type=ObjectType.ANOMALY,
                name=rng.choice(_ANOMALY_NAMES),
                description=rng.choice(_ANOMALY_DESCRIPTIONS),
                orbit_radius=rng.uniform(0.15, 0.7),
                orbit_angle=rng.uniform(0, math.tau),
                danger_level=rng.randint(1, min(danger + 2, 5)),
                loot_value=rng.randint(300, 1000),
            )
        )

    # Alien outposts (PLAN.md: new species have risen, scales with danger)
    alien_chance = 0.0 if danger < 1 else 0.1 + danger * 0.12
    if rng.random() < alien_chance:
        names = [
            "Alien Outpost", "Alien Trade Station", "Xeno Colony",
            "Alien Fortress", "Alien Mining Post", "Alien Relay",
        ]
        descriptions = [
            "A settlement of one of the new species. They may trade — or attack.",
            "An alien structure bristling with unfamiliar technology.",
            "A guarded alien installation. They have noticed your fleet.",
            "Alien vessels patrol around this outpost. Approach with caution.",
        ]
        objects.append(
            SystemObject(
                obj_type=ObjectType.ALIEN_OUTPOST,
                name=rng.choice(names),
                description=rng.choice(descriptions),
                orbit_radius=rng.uniform(0.3, 0.65),
                orbit_angle=rng.uniform(0, math.tau),
                danger_level=rng.randint(1, min(danger, 4)),
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

        # Sort by distance to assign quest locations to far-away systems
        by_distance = sorted(
            self.systems,
            key=lambda s: math.hypot(s.x - start.x, s.y - start.y),
        )

        # Pick high-danger systems for Earth and Gateway
        earth_system = by_distance[-3] if len(by_distance) > 3 else by_distance[-1]
        gateway_system = by_distance[-1]

        for system in self.systems:
            dist = math.hypot(system.x - start.x, system.y - start.y)
            # Danger scales 0–5 with distance from start
            danger = int((dist / max(max_dist, 1)) * 5)
            system.danger_level = min(danger, 5)
            system.objects = _generate_objects(self.rng, system.danger_level)

        # Inject quest-critical objects
        earth_system.objects.append(
            SystemObject(
                obj_type=ObjectType.STATION_RUIN,
                name="Sol System — Earth",
                description=(
                    "The cradle of humanity. A dead world orbited by the "
                    "wreckage of the old federation's mightiest fleet. "
                    "The Signal of Dawn waits in eternal orbit."
                ),
                orbit_radius=0.5,
                orbit_angle=self.rng.uniform(0, math.tau),
                danger_level=5,
                loot_value=0,
                special_tag="earth",
            )
        )
        earth_system.name = f"{earth_system.name} (Sol Sector)"

        gateway_system.objects.append(
            SystemObject(
                obj_type=ObjectType.ANOMALY,
                name="Trans-Galactic Gateway",
                description=(
                    "The colossal gateway built by the old federation. "
                    "It hums with dormant power, waiting for a Class 1 "
                    "Identification Code to activate. Beyond it lies "
                    "Andromeda — and Ninurta."
                ),
                orbit_radius=0.3,
                orbit_angle=self.rng.uniform(0, math.tau),
                danger_level=5,
                loot_value=0,
                special_tag="gateway",
            )
        )
        gateway_system.name = f"{gateway_system.name} (Gateway Sector)"

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
