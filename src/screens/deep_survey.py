"""Deep Survey screen — continent-based planetary surface exploration.

The player explores a procedurally generated planetary surface composed
of Voronoi regions resembling tectonic plates and continents.  Each
region holds terrain specific to the planet's subtype (volcanic, icy,
oceanic, etc.).  Revealing a region costs a survey action; adjacents
become partially visible, rewarding strategic exploration.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

import pygame

from ..constants import (
    AMBER,
    CYAN,
    DARK_GREY,
    HULL_GREEN,
    LIGHT_GREY,
    PANEL_BG,
    PANEL_BORDER,
    RED_ALERT,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    WHITE,
)
from ..models.ships import Fleet
from ..states import GameState

# ---------------------------------------------------------------------------
# Planet type → terrain profile
# ---------------------------------------------------------------------------

# Canonical planet categories derived from the first word(s) of planet names
_PLANET_CATEGORY_MAP: dict[str, str] = {
    "Rocky": "rocky", "Dust": "rocky", "Cratered": "rocky",
    "Barren": "rocky", "Dead": "rocky", "Airless": "rocky", "Grey Moon": "rocky",
    "Volcanic": "volcanic", "Molten": "volcanic", "Magma": "volcanic",
    "Tectonic": "volcanic", "Cinder": "volcanic",
    "Frozen": "ice", "Ice": "ice", "Glacial": "ice",
    "Cryo": "ice", "Permafrost": "ice",
    "Ocean": "ocean", "Water": "ocean", "Deep Sea": "ocean",
    "Tidal": "ocean", "Archipelago": "ocean",
    "Garden": "garden", "Temperate": "garden", "Green": "garden",
    "Earthlike": "garden", "Verdant": "garden", "Paradise": "garden",
    "Acid": "toxic", "Toxic": "toxic", "Chemical": "toxic",
    "Corrosive": "toxic", "Venomous": "toxic",
    "Gas Giant": "gas", "Jovian": "gas", "Ringed": "gas",
    "Storm": "gas", "Hydrogen": "gas",
    "Shattered": "shattered", "Broken": "shattered",
    "Debris Field": "shattered", "Fractured": "shattered", "Sundered": "shattered",
    "Settled": "garden", "Alien Colony": "garden", "Populous": "garden",
    "Trade Hub": "garden", "Fortified": "garden", "Alien Homeworld": "garden",
}


@dataclass
class TerrainType:
    """A single kind of surface terrain."""
    name: str
    icon: str
    color: tuple[int, int, int]
    description: str
    # Resource rewards on reveal
    metal: int = 0
    energy: int = 0
    rare: int = 0
    hull_damage: int = 0           # Hazard damage (0 = none)
    is_colony_site: bool = False
    # Flavour event (brief choice text) — if set, shown on reveal
    event_text: str = ""
    event_choice_a: str = ""       # Button label
    event_choice_b: str = ""
    event_bonus_a: dict[str, int] = field(default_factory=dict)
    event_bonus_b: dict[str, int] = field(default_factory=dict)


# ---- Terrain catalogues per planet category ----

_T_ROCKY: list[tuple[TerrainType, int]] = [
    (TerrainType("Dust Plains", "~", (160, 140, 120), "Flat expanses of iron-rich regolith stretch to the horizon."), 5),
    (TerrainType("Mineral Veins", "◆", (200, 170, 80), "Glittering seams of refined ore wind through the bedrock.", metal=250, energy=60), 3),
    (TerrainType("Impact Crater", "○", (130, 120, 110), "A vast circular scar pocked with secondary craters.  Trace metals in ejecta.", metal=120), 3),
    (TerrainType("Deep Caves", "▼", (90, 85, 80), "Subterranean networks plunge into darkness.  Echoes suggest vast chambers.", rare=80,
                 event_text="Your probe detects a faint energy signature deep inside.  Investigate further or seal the entrance?",
                 event_choice_a="Investigate", event_choice_b="Seal it",
                 event_bonus_a={"rare": 150}, event_bonus_b={"metal": 100}), 2),
    (TerrainType("Ancient Ruins", "▣", (170, 160, 180), "Fragments of pre-Federation construction.  Millennia old.", metal=100, rare=120), 1),
    (TerrainType("Seismic Fault", "⚠", (200, 80, 60), "The ground shudders.  Unstable tectonic activity.", hull_damage=40), 2),
]

_T_VOLCANIC: list[tuple[TerrainType, int]] = [
    (TerrainType("Ash Wastes", "≋", (100, 80, 70), "Layers of volcanic ash blanket the terrain.  Visibility near zero."), 4),
    (TerrainType("Obsidian Fields", "◆", (50, 45, 60), "Sheets of black volcanic glass.  Razor-sharp and beautiful.", metal=200, rare=80), 3),
    (TerrainType("Lava Flows", "▮", (230, 100, 30), "Rivers of molten rock carve through the landscape.", energy=200), 3),
    (TerrainType("Geothermal Vents", "△", (220, 160, 60), "Superheated gas erupts from fissures.  Incredible energy potential.", energy=350,
                 event_text="A vent system could be tapped for power, but risks triggering a chain eruption.",
                 event_choice_a="Tap it", event_choice_b="Leave it",
                 event_bonus_a={"energy": 400}, event_bonus_b={}), 2),
    (TerrainType("Ancient Ruins", "▣", (170, 130, 100), "Heat-warped ruins, half-consumed by lava.  Something survived.", rare=100), 1),
    (TerrainType("Eruption Zone", "⚠", (255, 60, 20), "The ground splits open.  Lava bombs rain from above.", hull_damage=60), 3),
]

_T_ICE: list[tuple[TerrainType, int]] = [
    (TerrainType("Glacial Plains", "═", (180, 210, 240), "Endless sheets of ancient ice.  Beautiful and desolate."), 4),
    (TerrainType("Ice Caves", "▼", (140, 180, 220), "Crystalline caverns glow with refracted light.", rare=100,
                 event_text="Deep inside, your scanners detect preserved biological specimens frozen in amber-ice.",
                 event_choice_a="Extract", event_choice_b="Document only",
                 event_bonus_a={"rare": 200}, event_bonus_b={"rare": 50}), 2),
    (TerrainType("Cryogeysers", "↑", (200, 230, 255), "Jets of pressurised ice crystals erupt periodically.", energy=180), 3),
    (TerrainType("Frozen Sea", "≈", (100, 150, 200), "An ocean locked beneath kilometres of ice.  Life signs flicker.", energy=120), 3),
    (TerrainType("Sub-ice Life", "♦", (80, 220, 130), "Bioluminescent organisms pulse beneath the frozen surface.", rare=60), 1),
    (TerrainType("Whiteout Zone", "⚠", (240, 245, 250), "Blinding ice storms.  Navigation impossible.  Probe lost.", hull_damage=35), 2),
]

_T_OCEAN: list[tuple[TerrainType, int]] = [
    (TerrainType("Shallow Reefs", "≈", (60, 180, 160), "Colourful mineral formations in warm shallows.", metal=100), 3),
    (TerrainType("Kelp Forests", "♣", (40, 160, 80), "Vast underwater forests sway in deep currents.", energy=120), 3),
    (TerrainType("Deep Trench", "▼", (20, 60, 140), "Abyssal depths.  Crushing pressure.  Unknown readings.", rare=150,
                 event_text="Something enormous moves in the darkness.  Your probe's light catches a metallic glint — wreckage or creature?",
                 event_choice_a="Descend", event_choice_b="Retreat",
                 event_bonus_a={"rare": 250, "metal": 100}, event_bonus_b={}), 2),
    (TerrainType("Tidal Pools", "○", (80, 200, 200), "Teeming with simple organisms.  Water samples rich in minerals.", metal=80, energy=60), 3),
    (TerrainType("Marine Life", "♦", (60, 220, 120), "Complex organisms.  Bio-signatures suggest intelligence.", rare=80), 2),
    (TerrainType("Typhoon Zone", "⚠", (30, 80, 160), "Massive storm systems churn the surface.  Waves breach orbit.", hull_damage=45), 2),
    (TerrainType("Colony Site", "★", HULL_GREEN, "Coastal plateau with fresh water, arable soil, and natural harbour.", is_colony_site=True), 0),
]

_T_GARDEN: list[tuple[TerrainType, int]] = [
    (TerrainType("Grasslands", "~", (100, 180, 70), "Rolling plains of alien grasses under a yellow sky."), 3),
    (TerrainType("Dense Forest", "♣", (40, 130, 50), "Towering xenoflora.  Canopy blocks orbital scans.", energy=100,
                 event_text="Your team discovers a clearing with carved stones — a meeting place?  Sacred ground or navigation marker?",
                 event_choice_a="Study", event_choice_b="Mark and leave",
                 event_bonus_a={"rare": 120}, event_bonus_b={"energy": 80}), 3),
    (TerrainType("River Valley", "≈", (70, 140, 180), "Fertile alluvial plains.  Perfect for agriculture.", metal=60, energy=80), 3),
    (TerrainType("Ancient Ruins", "▣", (160, 150, 170), "Overgrown structures.  Nature has reclaimed what was built.", metal=80, rare=150), 1),
    (TerrainType("Wildlife", "♦", (80, 200, 100), "Megafauna roam in herds.  The ecosystem is thriving.", rare=40), 2),
    (TerrainType("Toxic Bloom", "⚠", (200, 200, 40), "A sudden algal bloom releases neurotoxic spores.", hull_damage=25), 1),
    (TerrainType("Colony Site", "★", HULL_GREEN, "Temperate plateau with water access, mineral deposits, and shelter from storms.", is_colony_site=True), 0),
]

_T_TOXIC: list[tuple[TerrainType, int]] = [
    (TerrainType("Chemical Flats", "═", (160, 190, 50), "Crystallised chemical deposits cover the terrain."), 4),
    (TerrainType("Acid Lakes", "≈", (180, 200, 40), "Pools of concentrated acid.  Valuable industrial solvents.", energy=150, rare=60), 3),
    (TerrainType("Corrosive Fog", "◌", (200, 210, 80), "Dense clouds of reactive gas.  Corrodes everything.", hull_damage=50), 3),
    (TerrainType("Mineral Veins", "◆", (190, 180, 60), "Unusual mineral formations created by extreme chemistry.", metal=300), 2),
    (TerrainType("Hardy Microbes", "♦", (120, 200, 60), "Extremophile organisms thrive in the caustic soup.", rare=100,
                 event_text="These microbes produce compounds unknown to human science.  Harvest aggressively or cultivate samples?",
                 event_choice_a="Harvest", event_choice_b="Cultivate",
                 event_bonus_a={"rare": 200}, event_bonus_b={"rare": 80, "energy": 60}), 1),
    (TerrainType("Contamination", "⚠", (220, 180, 30), "A sudden chain reaction.  The ground dissolves beneath the probe.", hull_damage=55), 2),
]

_T_GAS: list[tuple[TerrainType, int]] = [
    (TerrainType("Cloud Bands", "≋", (200, 180, 130), "Layered atmospheric bands of hydrogen and helium."), 5),
    (TerrainType("Storm Eye", "◎", (220, 150, 80), "The calm centre of a planet-scale hurricane.  Energy readings spike.", energy=250), 2),
    (TerrainType("Atmospheric Mining", "◆", (180, 160, 100), "Dense pockets of harvestable gases.", energy=200, metal=80), 3),
    (TerrainType("Lightning Layer", "⚡", (255, 240, 100), "Continuous electrical discharges.  Beautiful and lethal.", energy=300,
                 event_text="Your probe can ride the lightning to reach deeper layers, but risks destruction.",
                 event_choice_a="Ride it", event_choice_b="Stay safe",
                 event_bonus_a={"energy": 500, "rare": 100}, event_bonus_b={"energy": 100}), 1),
    (TerrainType("Anomaly", "◎", (200, 120, 255), "Sensors detect something solid where nothing solid should exist.", rare=180), 1),
    (TerrainType("Pressure Crush", "⚠", (180, 140, 90), "Atmospheric pressure exceeds structural limits.  Probe implodes.", hull_damage=50), 3),
]

_T_SHATTERED: list[tuple[TerrainType, int]] = [
    (TerrainType("Debris Field", "◇", (140, 120, 100), "Floating chunks of what was once a planet's crust."), 4),
    (TerrainType("Exposed Core", "◆", (200, 100, 60), "The planet's iron core is visible.  Incredible mineral wealth.", metal=400, rare=100), 1),
    (TerrainType("Fragment Caves", "▼", (120, 110, 100), "Hollow interiors of shattered continental plates.", metal=150,
                 event_text="Your probe detects a sealed chamber inside the fragment — artificial, not geological.",
                 event_choice_a="Breach it", event_choice_b="Scan only",
                 event_bonus_a={"rare": 300, "metal": 100}, event_bonus_b={"rare": 80}), 2),
    (TerrainType("Anomaly", "◎", (180, 100, 255), "Residual energy from whatever destroyed this world.", rare=120), 2),
    (TerrainType("Ancient Ruins", "▣", (150, 140, 160), "Ruins frozen in the moment of cataclysm.", rare=200), 1),
    (TerrainType("Gravitational Collapse", "⚠", (170, 100, 80), "Fragment shifts unpredictably.  Probe crushed.", hull_damage=55), 3),
]

_PROFILES: dict[str, list[tuple[TerrainType, int]]] = {
    "rocky": _T_ROCKY,
    "volcanic": _T_VOLCANIC,
    "ice": _T_ICE,
    "ocean": _T_OCEAN,
    "garden": _T_GARDEN,
    "toxic": _T_TOXIC,
    "gas": _T_GAS,
    "shattered": _T_SHATTERED,
}

# Background colours for the planet disc per category
_BG_COLORS: dict[str, tuple[int, int, int]] = {
    "rocky": (70, 65, 58),
    "volcanic": (60, 35, 25),
    "ice": (55, 70, 85),
    "ocean": (20, 45, 80),
    "garden": (35, 60, 40),
    "toxic": (55, 65, 25),
    "gas": (75, 65, 50),
    "shattered": (50, 40, 35),
}

# Atmosphere tint overlaid on unrevealed regions
_FOG_COLORS: dict[str, tuple[int, int, int, int]] = {
    "rocky": (80, 70, 60, 160),
    "volcanic": (100, 50, 30, 170),
    "ice": (120, 140, 160, 150),
    "ocean": (30, 60, 100, 160),
    "garden": (40, 70, 50, 140),
    "toxic": (80, 90, 30, 170),
    "gas": (90, 80, 60, 160),
    "shattered": (60, 50, 40, 170),
}


def _get_category(planet_name: str) -> str:
    """Determine planet category from its name."""
    # Try first two words, then first word
    words = planet_name.split()
    if len(words) >= 2:
        two = " ".join(words[:2])
        if two in _PLANET_CATEGORY_MAP:
            return _PLANET_CATEGORY_MAP[two]
    if words and words[0] in _PLANET_CATEGORY_MAP:
        return _PLANET_CATEGORY_MAP[words[0]]
    return "rocky"  # fallback


# ---------------------------------------------------------------------------
# Voronoi region generation
# ---------------------------------------------------------------------------

@dataclass
class SurveyRegion:
    """A single Voronoi region on the planet surface."""
    idx: int
    seed_x: float
    seed_y: float
    terrain: TerrainType
    polygon: list[tuple[float, float]] = field(default_factory=list)
    neighbours: list[int] = field(default_factory=list)
    revealed: bool = False
    adjacent_revealed: bool = False  # Partially visible (silhouette)
    # Event state
    event_resolved: bool = False
    event_choice: str = ""


def _generate_voronoi_regions(
    cx: float, cy: float, radius: float,
    num_regions: int, seed: int,
    planet_category: str,
) -> list[SurveyRegion]:
    """Generate Voronoi regions inside a circle using Lloyd relaxation."""
    rng = random.Random(seed)
    profile = _PROFILES.get(planet_category, _T_ROCKY)

    # --- Generate seed points inside circle ---
    points: list[tuple[float, float]] = []
    for _ in range(num_regions):
        while True:
            angle = rng.uniform(0, 2 * math.pi)
            r = radius * math.sqrt(rng.random()) * 0.88  # Keep slightly inside
            px = cx + r * math.cos(angle)
            py = cy + r * math.sin(angle)
            # Ensure minimum separation
            if all(math.hypot(px - ex, py - ey) > radius * 0.12 for ex, ey in points):
                points.append((px, py))
                break

    # --- Lloyd relaxation (3 iterations for organic feel) ---
    for _ in range(3):
        # Build Voronoi cells via pixel sampling (simple but effective)
        cell_points: list[list[tuple[float, float]]] = [[] for _ in range(num_regions)]
        step = 6
        for gx in range(int(cx - radius), int(cx + radius) + 1, step):
            for gy in range(int(cy - radius), int(cy + radius) + 1, step):
                dx, dy = gx - cx, gy - cy
                if dx * dx + dy * dy > radius * radius:
                    continue
                # Find nearest seed
                best_i = 0
                best_d = float("inf")
                for i, (sx, sy) in enumerate(points):
                    d = (gx - sx) ** 2 + (gy - sy) ** 2
                    if d < best_d:
                        best_d = d
                        best_i = i
                cell_points[best_i].append((float(gx), float(gy)))

        # Move seeds to centroids
        new_points: list[tuple[float, float]] = []
        for i, pts in enumerate(cell_points):
            if pts:
                avg_x = sum(p[0] for p in pts) / len(pts)
                avg_y = sum(p[1] for p in pts) / len(pts)
                # Keep inside circle
                dx, dy = avg_x - cx, avg_y - cy
                dist = math.hypot(dx, dy)
                if dist > radius * 0.85:
                    scale = radius * 0.85 / dist
                    avg_x = cx + dx * scale
                    avg_y = cy + dy * scale
                new_points.append((avg_x, avg_y))
            else:
                new_points.append(points[i])
        points = new_points

    # --- Build polygon boundaries ---
    # Use angular sweep to build convex-ish polygon for each cell
    regions: list[SurveyRegion] = []
    boundary_step = 4
    for i, (sx, sy) in enumerate(points):
        boundary: list[tuple[float, float]] = []
        # Sample points around seed and find Voronoi boundary
        angles = 36
        for a_idx in range(angles):
            angle = 2 * math.pi * a_idx / angles
            # March outward from seed until another seed is closer or we leave circle
            for dist in range(2, int(radius * 2), boundary_step):
                px = sx + dist * math.cos(angle)
                py = sy + dist * math.sin(angle)
                # Outside circle?
                if (px - cx) ** 2 + (py - cy) ** 2 > radius * radius:
                    boundary.append((px, py))
                    break
                # Closer to another seed?
                my_d = (px - sx) ** 2 + (py - sy) ** 2
                closer = False
                for j, (ox, oy) in enumerate(points):
                    if j == i:
                        continue
                    if (px - ox) ** 2 + (py - oy) ** 2 < my_d:
                        closer = True
                        break
                if closer:
                    boundary.append((px, py))
                    break
            else:
                boundary.append((sx + radius * 0.9 * math.cos(angle),
                                 sy + radius * 0.9 * math.sin(angle)))

        # Clip to circle
        clipped = []
        for bx, by in boundary:
            dx, dy = bx - cx, by - cy
            d = math.hypot(dx, dy)
            if d > radius:
                scale = radius / d
                clipped.append((cx + dx * scale, cy + dy * scale))
            else:
                clipped.append((bx, by))

        regions.append(SurveyRegion(
            idx=i,
            seed_x=sx, seed_y=sy,
            terrain=TerrainType("", "", (0, 0, 0), ""),  # Assigned below
            polygon=clipped,
        ))

    # --- Assign terrain types based on profile weights ---
    terrain_pool: list[TerrainType] = []
    for terrain, weight in profile:
        terrain_pool.extend([terrain] * weight)

    # Colony sites: only garden/ocean, 30% chance
    can_colony = planet_category in ("garden", "ocean")
    colony_terrain = None
    if can_colony:
        for terrain, _w in profile:
            if terrain.is_colony_site:
                colony_terrain = terrain
                break

    has_colony = False
    for reg in regions:
        if colony_terrain and not has_colony and can_colony and rng.random() < 0.3:
            reg.terrain = colony_terrain
            has_colony = True
        else:
            reg.terrain = rng.choice(terrain_pool)

    # Shuffle so colony site isn't always first
    rng.shuffle(regions)
    for i, reg in enumerate(regions):
        reg.idx = i

    # --- Compute adjacency ---
    threshold = radius * 0.65
    for i, a in enumerate(regions):
        for j, b in enumerate(regions):
            if i >= j:
                continue
            d = math.hypot(a.seed_x - b.seed_x, a.seed_y - b.seed_y)
            if d < threshold:
                a.neighbours.append(j)
                b.neighbours.append(i)

    return regions


# ---------------------------------------------------------------------------
# Deep Survey Screen
# ---------------------------------------------------------------------------

PLANET_CX = 340
PLANET_CY = 340
PLANET_RADIUS = 260
NUM_REGIONS = 15


class DeepSurveyScreen:
    """Continent-based deep survey of a planet surface."""

    def __init__(
        self,
        planet_name: str,
        system_id: int,
        survey_seed: int,
        fleet: Fleet,
        scout_count: int = 0,
        sensor_level: int = 1,
    ) -> None:
        self.planet_name = planet_name
        self.system_id = system_id
        self.fleet = fleet
        self.next_state: GameState | None = None

        self.font_title = pygame.font.Font(None, 36)
        self.font_head = pygame.font.Font(None, 26)
        self.font_body = pygame.font.Font(None, 20)
        self.font_small = pygame.font.Font(None, 16)
        self.font_icon = pygame.font.Font(None, 32)

        self.category = _get_category(planet_name)

        # Survey actions: base 6 + 2 per scout + 1 per sensor level
        self.max_actions = 6 + scout_count * 2 + sensor_level
        self.actions_remaining = self.max_actions
        self.sensor_level = sensor_level

        # Generate regions
        self.regions = _generate_voronoi_regions(
            PLANET_CX, PLANET_CY, PLANET_RADIUS,
            NUM_REGIONS, survey_seed, self.category,
        )

        self.selected = 0
        self.colony_site_found = False
        self.discoveries: list[str] = []
        self.completed = False

        # Event overlay state
        self._event_active = False
        self._event_region: SurveyRegion | None = None
        self._event_selected = 0  # 0 = choice A, 1 = choice B

        # Message
        self.message = ""
        self.message_timer = 0.0
        self.message_color = WHITE

        # Scan animation
        self._scan_timer = 0.0
        self._scan_region: SurveyRegion | None = None

    def handle_events(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return

        # Event overlay has priority
        if self._event_active and self._event_region:
            if event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                self._event_selected = 1 - self._event_selected
            elif event.key == pygame.K_RETURN:
                self._resolve_event()
            return

        if event.key == pygame.K_LEFT or event.key == pygame.K_UP:
            self.selected = (self.selected - 1) % len(self.regions)
        elif event.key == pygame.K_RIGHT or event.key == pygame.K_DOWN:
            self.selected = (self.selected + 1) % len(self.regions)
        elif event.key == pygame.K_RETURN:
            self._reveal_region()
        elif event.key in (pygame.K_ESCAPE, pygame.K_q):
            self.next_state = GameState.SYSTEM_VIEW

    def _reveal_region(self) -> None:
        region = self.regions[self.selected]

        if region.revealed:
            self.message = "This region has already been surveyed."
            self.message_color = LIGHT_GREY
            self.message_timer = 2.0
            return

        if self.actions_remaining <= 0:
            self.message = "No survey actions remaining."
            self.message_color = RED_ALERT
            self.message_timer = 3.0
            return

        self.actions_remaining -= 1
        region.revealed = True

        # Start scan animation
        self._scan_timer = 0.6
        self._scan_region = region

        # Reveal adjacents (silhouette)
        adj_count = min(len(region.neighbours), 1 + self.sensor_level)
        for ni in region.neighbours[:adj_count]:
            if ni < len(self.regions):
                self.regions[ni].adjacent_revealed = True

        terrain = region.terrain

        # Hazard
        if terrain.hull_damage > 0:
            dmg = terrain.hull_damage
            self.fleet.mothership.hull = max(0, self.fleet.mothership.hull - dmg)
            self.message = f"⚠ {terrain.name}! Hull -{dmg}"
            self.message_color = RED_ALERT
            self.message_timer = 3.0
            self.discoveries.append(f"⚠ {terrain.name} (Hull -{dmg})")
        elif terrain.is_colony_site:
            self.colony_site_found = True
            self.message = "★ Colony site identified!"
            self.message_color = HULL_GREEN
            self.message_timer = 4.0
            self.discoveries.append("★ Colony site discovered!")
        elif terrain.event_text and not region.event_resolved:
            # Trigger terrain event
            self._event_active = True
            self._event_region = region
            self._event_selected = 0
            return  # Don't give resources yet — wait for choice
        else:
            # Resource rewards
            self._apply_resources(terrain, region)

        self._check_completion()

    def _apply_resources(self, terrain: TerrainType, region: SurveyRegion) -> None:
        r = self.fleet.resources
        parts = []
        if terrain.metal:
            r.metal += terrain.metal
            parts.append(f"+{terrain.metal} Metal")
        if terrain.energy:
            r.energy += terrain.energy
            parts.append(f"+{terrain.energy} Energy")
        if terrain.rare:
            r.rare_materials += terrain.rare
            parts.append(f"+{terrain.rare} Rare")

        if parts:
            self.message = f"{terrain.name}: {', '.join(parts)}"
            self.message_color = terrain.color
            self.message_timer = 3.0
            self.discoveries.append(f"{terrain.name}: {', '.join(parts)}")
        else:
            self.message = f"{terrain.name} — nothing of value."
            self.message_color = LIGHT_GREY
            self.message_timer = 2.0

    def _resolve_event(self) -> None:
        region = self._event_region
        if not region:
            return
        region.event_resolved = True
        terrain = region.terrain

        bonus = terrain.event_bonus_a if self._event_selected == 0 else terrain.event_bonus_b
        r = self.fleet.resources
        parts = []
        for key, val in bonus.items():
            if key == "metal":
                r.metal += val
                parts.append(f"+{val} Metal")
            elif key == "energy":
                r.energy += val
                parts.append(f"+{val} Energy")
            elif key == "rare":
                r.rare_materials += val
                parts.append(f"+{val} Rare")

        choice_label = terrain.event_choice_a if self._event_selected == 0 else terrain.event_choice_b
        region.event_choice = choice_label
        if parts:
            self.message = f"{choice_label}: {', '.join(parts)}"
            self.discoveries.append(f"Event: {choice_label} → {', '.join(parts)}")
        else:
            self.message = f"{choice_label} — no immediate gain."
            self.discoveries.append(f"Event: {choice_label}")
        self.message_color = AMBER
        self.message_timer = 3.0

        self._event_active = False
        self._event_region = None

        # Also apply base terrain resources
        self._apply_resources(terrain, region)
        self._check_completion()

    def _check_completion(self) -> None:
        revealed = sum(1 for r in self.regions if r.revealed)
        if revealed >= len(self.regions) or self.actions_remaining <= 0:
            self.completed = True

    def update(self, dt: float) -> None:
        if self.message_timer > 0:
            self.message_timer -= dt
        if self._scan_timer > 0:
            self._scan_timer -= dt

    def draw(self, surface: pygame.Surface) -> None:
        # Full-screen dark background
        bg = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        bg.fill((6, 8, 14, 245))
        surface.blit(bg, (0, 0))

        # Title
        cat_label = self.category.upper()
        title = self.font_title.render(
            f"DEEP SURVEY — {self.planet_name.upper()} [{cat_label}]", True, AMBER,
        )
        surface.blit(title, (20, 12))

        # Actions remaining
        ac = HULL_GREEN if self.actions_remaining > 2 else RED_ALERT
        at = self.font_head.render(
            f"Scans: {self.actions_remaining}/{self.max_actions}", True, ac,
        )
        surface.blit(at, (20, 46))

        # Resources
        r = self.fleet.resources
        res = f"M:{r.metal:,}  E:{r.energy:,}  R:{r.rare_materials:,}"
        rs = self.font_small.render(res, True, LIGHT_GREY)
        surface.blit(rs, (20, 68))

        # --- Planet disc ---
        disc_bg = _BG_COLORS.get(self.category, (50, 50, 50))
        pygame.draw.circle(surface, disc_bg, (PLANET_CX, PLANET_CY), PLANET_RADIUS)

        fog_rgba = _FOG_COLORS.get(self.category, (80, 80, 80, 160))

        # Draw regions
        for i, region in enumerate(self.regions):
            if len(region.polygon) < 3:
                continue

            poly = [(int(p[0]), int(p[1])) for p in region.polygon]

            if region.revealed:
                # Filled polygon with terrain colour
                col = region.terrain.color
                pygame.draw.polygon(surface, col, poly)
                pygame.draw.polygon(surface, (col[0] // 2, col[1] // 2, col[2] // 2), poly, 1)

                # Terrain icon at seed point
                icon_s = self.font_icon.render(region.terrain.icon, True, WHITE)
                icon_r = icon_s.get_rect(center=(int(region.seed_x), int(region.seed_y)))
                surface.blit(icon_s, icon_r)
            elif region.adjacent_revealed:
                # Silhouette — faintly visible
                dim = (fog_rgba[0] + 20, fog_rgba[1] + 20, fog_rgba[2] + 20)
                pygame.draw.polygon(surface, dim, poly)
                pygame.draw.polygon(surface, (dim[0] - 10, dim[1] - 10, dim[2] - 10), poly, 1)
                q = self.font_body.render("?", True, (dim[0] + 40, dim[1] + 40, min(255, dim[2] + 40)))
                qr = q.get_rect(center=(int(region.seed_x), int(region.seed_y)))
                surface.blit(q, qr)
            else:
                # Full fog
                fog_col = (fog_rgba[0], fog_rgba[1], fog_rgba[2])
                pygame.draw.polygon(surface, fog_col, poly)
                pygame.draw.polygon(surface, (fog_col[0] - 15, fog_col[1] - 15, max(0, fog_col[2] - 15)), poly, 1)

            # Selection highlight
            if i == self.selected:
                pygame.draw.polygon(surface, CYAN, poly, 2)

        # Planet rim (atmosphere glow)
        rim_col = _BG_COLORS.get(self.category, (50, 50, 50))
        for t in range(3):
            alpha_col = (min(255, rim_col[0] + 40), min(255, rim_col[1] + 40), min(255, rim_col[2] + 40))
            pygame.draw.circle(surface, alpha_col, (PLANET_CX, PLANET_CY), PLANET_RADIUS + t, 1)

        # Scan animation (pulsing ring on recently revealed region)
        if self._scan_timer > 0 and self._scan_region:
            alpha = int(255 * (self._scan_timer / 0.6))
            scan_col = (min(255, CYAN[0]), min(255, CYAN[1]), min(255, CYAN[2]))
            sr = self._scan_region
            scan_r = int(40 * (1.0 - self._scan_timer / 0.6))
            pygame.draw.circle(surface, scan_col, (int(sr.seed_x), int(sr.seed_y)), 10 + scan_r, 2)

        # --- Right panel ---
        panel_x = PLANET_CX + PLANET_RADIUS + 40
        panel_w = SCREEN_WIDTH - panel_x - 20

        region = self.regions[self.selected]
        # Region header
        if region.revealed:
            name_s = self.font_head.render(region.terrain.name, True, region.terrain.color)
            surface.blit(name_s, (panel_x, 95))

            # Description (word-wrapped)
            desc_lines = self._wrap(region.terrain.description, panel_w, self.font_body)
            y = 122
            for line in desc_lines:
                ls = self.font_body.render(line, True, LIGHT_GREY)
                surface.blit(ls, (panel_x, y))
                y += 18

            # Event choice made
            if region.event_resolved and region.event_choice:
                ec = self.font_small.render(f"Choice: {region.event_choice}", True, AMBER)
                surface.blit(ec, (panel_x, y + 4))
                y += 20
        else:
            status = "Adjacent — partially visible" if region.adjacent_revealed else "Unexplored region"
            name_s = self.font_head.render(status, True, DARK_GREY)
            surface.blit(name_s, (panel_x, 95))
            hint = self.font_body.render("Press Enter to scan", True, LIGHT_GREY)
            surface.blit(hint, (panel_x, 122))

        # Discoveries log
        disc_y = 260
        if self.discoveries:
            dh = self.font_head.render("Discoveries", True, AMBER)
            surface.blit(dh, (panel_x, disc_y))
            dy = disc_y + 26
            for d in self.discoveries[-10:]:
                ds = self.font_small.render(f"• {d}", True, LIGHT_GREY)
                surface.blit(ds, (panel_x, dy))
                dy += 16

        # Colony indicator
        if self.colony_site_found:
            cs = self.font_head.render("★ Colony Site Identified", True, HULL_GREEN)
            surface.blit(cs, (panel_x, SCREEN_HEIGHT - 58))

        # Message
        if self.message and self.message_timer > 0:
            ms = self.font_body.render(self.message, True, self.message_color)
            surface.blit(ms, (20, SCREEN_HEIGHT - 52))

        # Hints
        h = "←→ / ↑↓ — Select Region   Enter — Scan   Esc — Exit"
        hs = self.font_small.render(h, True, DARK_GREY)
        surface.blit(hs, (20, SCREEN_HEIGHT - 22))

        # --- Event overlay ---
        if self._event_active and self._event_region:
            self._draw_event_overlay(surface)

    def _draw_event_overlay(self, surface: pygame.Surface) -> None:
        """Draw the terrain event choice overlay."""
        region = self._event_region
        if not region:
            return
        terrain = region.terrain

        ow, oh = 520, 220
        ox = (SCREEN_WIDTH - ow) // 2
        oy = (SCREEN_HEIGHT - oh) // 2

        # Overlay background
        overlay = pygame.Surface((ow, oh), pygame.SRCALPHA)
        overlay.fill((10, 14, 24, 230))
        surface.blit(overlay, (ox, oy))
        pygame.draw.rect(surface, AMBER, (ox, oy, ow, oh), 2, border_radius=6)

        # Title
        et = self.font_head.render(f"— {terrain.name} —", True, terrain.color)
        surface.blit(et, (ox + (ow - et.get_width()) // 2, oy + 12))

        # Event text (wrapped)
        lines = self._wrap(terrain.event_text, ow - 40, self.font_body)
        y = oy + 42
        for line in lines:
            ls = self.font_body.render(line, True, LIGHT_GREY)
            surface.blit(ls, (ox + 20, y))
            y += 20

        # Choice buttons
        btn_w = 200
        btn_h = 34
        btn_y = oy + oh - 52
        for i, (label, bonus) in enumerate([(terrain.event_choice_a, terrain.event_bonus_a),
                                             (terrain.event_choice_b, terrain.event_bonus_b)]):
            bx = ox + 40 + i * (btn_w + 40)
            sel = i == self._event_selected
            bc = AMBER if sel else PANEL_BORDER
            fill = (30, 40, 55) if sel else (15, 18, 28)
            pygame.draw.rect(surface, fill, (bx, btn_y, btn_w, btn_h), border_radius=4)
            pygame.draw.rect(surface, bc, (bx, btn_y, btn_w, btn_h), 2, border_radius=4)

            tc = WHITE if sel else LIGHT_GREY
            ls = self.font_body.render(label, True, tc)
            surface.blit(ls, (bx + (btn_w - ls.get_width()) // 2, btn_y + 8))

    @staticmethod
    def _wrap(text: str, max_width: int, font: pygame.font.Font) -> list[str]:
        words = text.split()
        lines: list[str] = []
        current = ""
        for word in words:
            test = f"{current} {word}".strip()
            if font.size(test)[0] <= max_width:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines
