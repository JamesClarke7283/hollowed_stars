"""System view — explore objects within a star system."""

from __future__ import annotations

import math

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
    STAR_COLORS,
    WHITE,
)
from ..models.events import Event, get_event_for_object_type, get_quest_event
from ..models.galaxy import Galaxy, ObjectType, PlanetSubtype, StarSystem, SystemObject
from ..models.quest import QuestFlag, QuestState
from ..models.ships import Fleet
from ..states import GameState


# Colors for different object types
_OBJECT_COLORS: dict[ObjectType, tuple[int, int, int]] = {
    ObjectType.PLANET: (100, 140, 180),
    ObjectType.ASTEROID_FIELD: (160, 150, 120),
    ObjectType.DERELICT: (180, 80, 60),
    ObjectType.ANOMALY: (180, 100, 255),
    ObjectType.STATION_RUIN: (140, 140, 160),
    ObjectType.ALIEN_OUTPOST: (60, 200, 120),
}

# Planet subtype colors for richer visual differentiation
_PLANET_SUBTYPE_COLORS: dict[str, tuple[int, int, int]] = {
    "Settled": (220, 160, 40),   # Gold — inhabited/trade
    "Alien Colony": (220, 160, 40),
    "Populous": (220, 160, 40),
    "Trade Hub": (220, 160, 40),
    "Fortified": (200, 60, 60),   # Red — militaristic inhabited
    "Alien Homeworld": (200, 60, 60),
    "Garden": (60, 200, 80),     # Green — habitable
    "Temperate": (60, 200, 80),
    "Green": (60, 200, 80),
    "Earthlike": (60, 200, 80),
    "Verdant": (60, 200, 80),
    "Paradise": (60, 200, 80),
    "Gas Giant": (200, 160, 100), # Tan — gas giants
    "Jovian": (200, 160, 100),
    "Ringed": (200, 160, 100),
    "Storm": (200, 160, 100),
    "Hydrogen": (200, 160, 100),
    "Frozen": (140, 200, 240),    # Ice blue — frozen
    "Ice": (140, 200, 240),
    "Glacial": (140, 200, 240),
    "Cryo": (140, 200, 240),
    "Permafrost": (140, 200, 240),
    "Volcanic": (220, 80, 30),    # Orange — volcanic
    "Molten": (220, 80, 30),
    "Magma": (220, 80, 30),
    "Tectonic": (220, 80, 30),
    "Cinder": (220, 80, 30),
    "Acid": (180, 220, 50),       # Yellow-green — toxic
    "Toxic": (180, 220, 50),
    "Chemical": (180, 220, 50),
    "Corrosive": (180, 220, 50),
    "Venomous": (180, 220, 50),
    "Ocean": (40, 120, 220),      # Blue — ocean
    "Water": (40, 120, 220),
    "Deep Sea": (40, 120, 220),
    "Tidal": (40, 120, 220),
    "Archipelago": (40, 120, 220),
    "Shattered": (140, 100, 80),  # Dark brown — shattered
    "Broken": (140, 100, 80),
    "Debris Field": (140, 100, 80),
    "Fractured": (140, 100, 80),
    "Sundered": (140, 100, 80),
    "Barren": (120, 110, 100),    # Grey — barren
    "Dust": (120, 110, 100),
    "Dead": (120, 110, 100),
    "Grey Moon": (120, 110, 100),
    "Airless": (120, 110, 100),
    "Cratered": (120, 110, 100),
}

_OBJECT_ICONS: dict[ObjectType, str] = {
    ObjectType.PLANET: "●",
    ObjectType.ASTEROID_FIELD: "◆",
    ObjectType.DERELICT: "▣",
    ObjectType.ANOMALY: "◎",
    ObjectType.STATION_RUIN: "▤",
    ObjectType.ALIEN_OUTPOST: "▲",
}


def _planet_color(name: str) -> tuple[int, int, int]:
    """Get the display color for a planet based on its name's first word."""
    first_word = name.split()[0]
    if first_word in _PLANET_SUBTYPE_COLORS:
        return _PLANET_SUBTYPE_COLORS[first_word]
    # Also try first two words for compound names
    if " " in name:
        two_words = " ".join(name.split()[:2])
        if two_words in _PLANET_SUBTYPE_COLORS:
            return _PLANET_SUBTYPE_COLORS[two_words]
    return _OBJECT_COLORS[ObjectType.PLANET]


class SystemViewScreen:
    """In-system exploration: star and orbiting objects."""

    def __init__(self, galaxy: Galaxy, fleet: Fleet, quest_state: QuestState | None = None) -> None:
        self.galaxy = galaxy
        self.fleet = fleet
        self.quest_state = quest_state or QuestState()
        self.font_title = pygame.font.Font(None, 40)
        self.font_name = pygame.font.Font(None, 28)
        self.font_info = pygame.font.Font(None, 24)
        self.font_small = pygame.font.Font(None, 22)

        self.timer = 0.0
        self.hovered_object: SystemObject | None = None
        self.selected_object: SystemObject | None = None
        self.next_state: GameState | None = None

        # Center of the system view
        self.center_x = SCREEN_WIDTH // 2
        self.center_y = SCREEN_HEIGHT // 2 + 20  # Offset for HUD

        # Event trigger
        self.pending_event: Event | None = None

        # Diplomacy trigger — faction_id for game.py to look up
        self.pending_diplomacy_faction_id: str = ""

        # Survey result message
        self._message: str = ""
        self._message_timer: float = 0.0
        self._message_color: tuple[int, int, int] = WHITE

    @property
    def system(self) -> StarSystem:
        return self.galaxy.current_system

    def handle_events(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE or event.key == pygame.K_m:
                self.next_state = GameState.STAR_MAP
            elif event.key == pygame.K_RETURN and self.selected_object is not None:
                self._survey_object(self.selected_object)
            elif event.key == pygame.K_d and self.selected_object is not None:
                self._try_diplomacy(self.selected_object)
            elif event.key == pygame.K_p:
                self._send_scout_probe()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._handle_click(event.pos)

    def update(self, dt: float) -> None:
        self.timer += dt

        # Only iterate visible objects (quest-filtered)
        visible = self._visible_objects()

        # Rotate objects
        for obj in visible:
            speed = 0.15 / max(obj.orbit_radius, 0.1)
            obj.orbit_angle += speed * dt

        # Hover
        mx, my = pygame.mouse.get_pos()
        self.hovered_object = self._object_at_pos(mx, my)

        # Message fade
        if self._message_timer > 0:
            self._message_timer -= dt

    def draw(self, surface: pygame.Surface) -> None:
        system = self.system
        star_color = STAR_COLORS.get(system.star_type.value, WHITE)

        # System title
        title = self.font_title.render(system.name, True, AMBER)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 60))
        surface.blit(title, title_rect)

        type_text = system.star_type.value.replace("_", " ").title()
        type_surf = self.font_info.render(type_text, True, LIGHT_GREY)
        type_rect = type_surf.get_rect(center=(SCREEN_WIDTH // 2, 88))
        surface.blit(type_surf, type_rect)

        # Orbit rings
        scale = min(SCREEN_WIDTH, SCREEN_HEIGHT) * 0.38
        orbit_radii = sorted(set(obj.orbit_radius for obj in system.objects))
        for r in orbit_radii:
            pixel_r = int(r * scale)
            pygame.draw.circle(surface, (35, 35, 50), (self.center_x, self.center_y), pixel_r, 1)

        # Central star
        star_radius = 18
        pulse = 1.0 + 0.08 * math.sin(self.timer * 2)
        pygame.draw.circle(surface, star_color, (self.center_x, self.center_y), int(star_radius * pulse))
        # Star glow
        glow_surf = pygame.Surface((star_radius * 6, star_radius * 6), pygame.SRCALPHA)
        for i in range(3):
            r = star_radius * (2 + i)
            alpha = 20 - i * 6
            pygame.draw.circle(glow_surf, (*star_color, max(alpha, 0)), (star_radius * 3, star_radius * 3), r)
        surface.blit(glow_surf, (self.center_x - star_radius * 3, self.center_y - star_radius * 3))

        # Objects (only visible ones — quest objects hidden without flags)
        visible = self._visible_objects()
        for obj in visible:
            self._draw_object(surface, obj, scale)

        # Selected object panel
        if self.selected_object:
            self._draw_object_panel(surface, self.selected_object)

        # Survey message
        if self._message_timer > 0:
            alpha = min(255, int(self._message_timer * 255))
            msg_surf = self.font_name.render(self._message, True, self._message_color)
            msg_surf.set_alpha(alpha)
            msg_rect = msg_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 80))
            surface.blit(msg_surf, msg_rect)

        # Keybind hints
        hints = ["ESC/M — star map", "ENTER — survey"]
        if self.fleet.scouts:
            hints.append("P — scout probe")
        if self.selected_object and self._can_diplomacy(self.selected_object):
            hints.append("D — diplomacy")
        hint_text = "   ".join(hints)
        hint = self.font_small.render(hint_text, True, LIGHT_GREY)
        surface.blit(hint, (10, SCREEN_HEIGHT - 25))

    def _draw_object(self, surface: pygame.Surface, obj: SystemObject, scale: float) -> None:
        ox = self.center_x + int(math.cos(obj.orbit_angle) * obj.orbit_radius * scale)
        oy = self.center_y + int(math.sin(obj.orbit_angle) * obj.orbit_radius * scale)

        # Planets use subtype-specific colors; others use the general mapping
        if obj.obj_type == ObjectType.PLANET:
            color = _planet_color(obj.name)
        else:
            color = _OBJECT_COLORS.get(obj.obj_type, WHITE)

        is_hovered = obj is self.hovered_object
        is_selected = obj is self.selected_object

        # Object dot — planets are slightly larger
        if obj.obj_type == ObjectType.PLANET:
            radius = 10 if is_hovered else 8
        else:
            radius = 8 if is_hovered else 6
        pygame.draw.circle(surface, color, (ox, oy), radius)

        if is_selected:
            pygame.draw.circle(surface, AMBER, (ox, oy), radius + 4, 2)

        if obj.surveyed:
            pygame.draw.circle(surface, HULL_GREEN, (ox, oy), radius + 3, 1)

        # Label
        if is_hovered or is_selected:
            label = self.font_small.render(obj.name, True, WHITE)
            surface.blit(label, (ox - label.get_width() // 2, oy - 22))

    def _object_at_pos(self, mx: int, my: int) -> SystemObject | None:
        scale = min(SCREEN_WIDTH, SCREEN_HEIGHT) * 0.38
        best: SystemObject | None = None
        best_dist = float("inf")

        for obj in self._visible_objects():
            ox = self.center_x + int(math.cos(obj.orbit_angle) * obj.orbit_radius * scale)
            oy = self.center_y + int(math.sin(obj.orbit_angle) * obj.orbit_radius * scale)
            dist = math.hypot(mx - ox, my - oy)
            if dist < 16 and dist < best_dist:
                best = obj
                best_dist = dist
        return best

    def _handle_click(self, pos: tuple[int, int]) -> None:
        clicked = self._object_at_pos(*pos)
        self.selected_object = clicked

    def _survey_object(self, obj: SystemObject) -> None:
        if obj.surveyed:
            self._message = f"{obj.name} already surveyed."
            self._message_color = LIGHT_GREY
            self._message_timer = 2.0
            return

        obj.surveyed = True

        # Quest-critical objects use their own event pool
        if obj.special_tag:
            event = get_quest_event(obj.special_tag)
            if event:
                self.pending_event = event
                self.next_state = GameState.EVENT_DIALOG
                return

        # Mining: asteroid fields yield resources scaled by mining bonus
        if obj.obj_type == ObjectType.ASTEROID_FIELD:
            base_yield = obj.loot_value
            bonus = self.fleet.mining_bonus
            metal_gain = int(base_yield * bonus)
            rare_gain = int(base_yield * 0.15 * bonus)
            self.fleet.resources.metal += metal_gain
            self.fleet.resources.rare_materials += rare_gain
            self._message = (
                f"Mined {obj.name} — {metal_gain} metal, {rare_gain} rare "
                f"(mining bonus: x{bonus:.1f})"
            )
            self._message_color = HULL_GREEN
            self._message_timer = 3.5
            return

        # Try to trigger a narrative event
        event = get_event_for_object_type(obj.obj_type.value)
        if event:
            self.pending_event = event
            self.next_state = GameState.EVENT_DIALOG
        else:
            # Fallback: flat resource reward
            if obj.loot_value > 0:
                self.fleet.resources.metal += obj.loot_value
                self._message = f"Surveyed {obj.name} — salvaged {obj.loot_value} metal!"
                self._message_color = HULL_GREEN
            else:
                self._message = f"Surveyed {obj.name} — nothing of value."
                self._message_color = LIGHT_GREY
            self._message_timer = 3.0

    def _visible_objects(self) -> list[SystemObject]:
        """Filter objects based on quest state — hide locked quest objectives."""
        visible: list[SystemObject] = []
        for obj in self.system.objects:
            if obj.special_tag == "earth":
                # Earth is only visible with Class 4 ID Code
                if not self.quest_state.has_flag(QuestFlag.CLASS_4_ID_CODE):
                    continue
            elif obj.special_tag == "gateway":
                # Gateway requires Signal of Dawn (Class 1 ID Code)
                if not self.quest_state.has_flag(QuestFlag.UNLOCKED_SIGNAL_OF_DAWN):
                    continue
            visible.append(obj)
        return visible

    def _draw_object_panel(self, surface: pygame.Surface, obj: SystemObject) -> None:
        panel_w = 300
        panel_h = 160
        px = SCREEN_WIDTH - panel_w - 15
        py = 50

        bg = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        bg.fill(PANEL_BG)
        surface.blit(bg, (px, py))
        pygame.draw.rect(surface, PANEL_BORDER, (px, py, panel_w, panel_h), 1, border_radius=4)

        color = _OBJECT_COLORS.get(obj.obj_type, WHITE)

        name_surf = self.font_name.render(obj.name, True, color)
        surface.blit(name_surf, (px + 12, py + 10))

        type_text = obj.obj_type.value.replace("_", " ").title()
        type_surf = self.font_info.render(type_text, True, LIGHT_GREY)
        surface.blit(type_surf, (px + 12, py + 36))

        danger_text = f"Danger: {'★' * obj.danger_level}{'☆' * (5 - obj.danger_level)}"
        danger_color = RED_ALERT if obj.danger_level >= 3 else LIGHT_GREY
        danger_surf = self.font_info.render(danger_text, True, danger_color)
        surface.blit(danger_surf, (px + 12, py + 58))

        status = "Surveyed ✓" if obj.surveyed else "Not surveyed"
        status_color = HULL_GREEN if obj.surveyed else LIGHT_GREY
        status_surf = self.font_info.render(status, True, status_color)
        surface.blit(status_surf, (px + 12, py + 80))

        # Faction info
        if obj.faction_id:
            fac_surf = self.font_small.render(f"Faction: {obj.faction_id}", True, AMBER)
            surface.blit(fac_surf, (px + 12, py + 100))
            desc_offset = 120
        else:
            desc_offset = 104

        # Wrap description
        desc_lines = self._wrap_text(obj.description, panel_w - 24)
        for i, line in enumerate(desc_lines[:3]):
            desc_surf = self.font_small.render(line, True, LIGHT_GREY)
            surface.blit(desc_surf, (px + 12, py + desc_offset + i * 18))

        if not obj.surveyed:
            prompt = self.font_info.render("ENTER to survey", True, CYAN)
            surface.blit(prompt, (px + panel_w - prompt.get_width() - 12, py + panel_h - 26))
        elif self._can_diplomacy(obj):
            prompt = self.font_info.render("D — Diplomacy", True, CYAN)
            surface.blit(prompt, (px + panel_w - prompt.get_width() - 12, py + panel_h - 26))

    def _can_diplomacy(self, obj: SystemObject) -> bool:
        """Check if this object supports a diplomacy interaction."""
        if not obj.faction_id:
            return False
        return obj.obj_type in (ObjectType.ALIEN_OUTPOST, ObjectType.PLANET)

    def _try_diplomacy(self, obj: SystemObject) -> None:
        """Attempt to open diplomacy with the faction owning this object."""
        if not self._can_diplomacy(obj):
            self._message = "No faction to communicate with here."
            self._message_color = LIGHT_GREY
            self._message_timer = 2.0
            return
        self.pending_diplomacy_faction_id = obj.faction_id
        self.next_state = GameState.DIPLOMACY

    def _send_scout_probe(self) -> None:
        """Send a scout ship to probe the system, revealing all objects."""
        scouts = self.fleet.scouts
        if not scouts:
            self._message = "No scout ships available."
            self._message_color = RED_ALERT
            self._message_timer = 2.5
            return

        # Consume one scout
        scout = scouts[0]
        self.fleet.ships.remove(scout)

        # Reveal all objects + reduce danger
        revealed = 0
        for obj in self._visible_objects():
            if not obj.surveyed:
                obj.surveyed = True
                obj.danger_level = max(0, obj.danger_level - 1)
                revealed += 1

        self._message = (
            f"Scout probe '{scout.name}' deployed! "
            f"{revealed} objects revealed, danger reduced."
        )
        self._message_color = HULL_GREEN
        self._message_timer = 4.0

    def _wrap_text(self, text: str, max_width: int) -> list[str]:
        words = text.split()
        lines: list[str] = []
        current = ""
        for word in words:
            test = f"{current} {word}".strip()
            if self.font_small.size(test)[0] <= max_width:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines
