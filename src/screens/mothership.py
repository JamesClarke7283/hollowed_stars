"""Mothership systems management screen."""

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
    WHITE,
)
from ..models.mothership_systems import ShipSystem, SystemType
from ..models.ships import Fleet
from ..states import GameState


# Visual layout for system rooms on the cross-section
_SYSTEM_POSITIONS: dict[SystemType, tuple[int, int]] = {
    SystemType.SHIELDS:       (1, 0),
    SystemType.POWER_CORE:    (0, 1),
    SystemType.WEAPONS_ARRAY: (2, 1),
    SystemType.SENSORS:       (1, 1),
    SystemType.LIFE_SUPPORT:  (0, 2),
    SystemType.CRYO_VAULTS:   (2, 2),
    SystemType.THRUSTERS:     (0, 3),
    SystemType.HANGAR:        (2, 3),
}


class MothershipScreen:
    """Mothership cross-section view with system management."""

    def __init__(self, fleet: Fleet, systems: list[ShipSystem]) -> None:
        self.fleet = fleet
        self.systems = systems
        self.font_title = pygame.font.Font(None, 40)
        self.font_name = pygame.font.Font(None, 28)
        self.font_info = pygame.font.Font(None, 24)
        self.font_small = pygame.font.Font(None, 22)

        self.selected_index = 0
        self.timer = 0.0
        self.next_state: GameState | None = None

        # Repair feedback
        self._message = ""
        self._message_timer = 0.0
        self._message_color = WHITE

    def handle_events(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.next_state = GameState.STAR_MAP
            elif event.key in (pygame.K_UP, pygame.K_w):
                self.selected_index = max(0, self.selected_index - 1)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected_index = min(len(self.systems) - 1, self.selected_index + 1)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._repair_selected()

    def update(self, dt: float) -> None:
        self.timer += dt
        if self._message_timer > 0:
            self._message_timer -= dt

    def draw(self, surface: pygame.Surface) -> None:
        # Title
        title = self.font_title.render("MOTHERSHIP SYSTEMS", True, AMBER)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 35))
        surface.blit(title, title_rect)

        ship_name = self.font_info.render(self.fleet.mothership.name, True, LIGHT_GREY)
        name_rect = ship_name.get_rect(center=(SCREEN_WIDTH // 2, 62))
        surface.blit(ship_name, name_rect)

        # Ship cross-section (left side)
        self._draw_cross_section(surface)

        # System list with details (right side)
        self._draw_system_list(surface)

        # Selected system detail
        if 0 <= self.selected_index < len(self.systems):
            self._draw_system_detail(surface, self.systems[self.selected_index])

        # Message
        if self._message_timer > 0:
            alpha = min(255, int(self._message_timer * 255))
            msg_surf = self.font_name.render(self._message, True, self._message_color)
            msg_surf.set_alpha(alpha)
            msg_rect = msg_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 60))
            surface.blit(msg_surf, msg_rect)

        # Hint
        hint = self.font_small.render("W/S select  |  ENTER repair  |  ESC back", True, LIGHT_GREY)
        hint_rect = hint.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 25))
        surface.blit(hint, hint_rect)

    def _draw_cross_section(self, surface: pygame.Surface) -> None:
        """Draw simplified mothership cross-section with system rooms."""
        base_x = 40
        base_y = 90
        room_w = 130
        room_h = 90
        gap = 10

        # Ship hull outline
        hull_w = 3 * room_w + 4 * gap
        hull_h = 4 * room_h + 5 * gap
        pygame.draw.rect(
            surface, PANEL_BORDER,
            (base_x - gap, base_y - gap, hull_w, hull_h),
            2, border_radius=12,
        )

        for i, system in enumerate(self.systems):
            pos = _SYSTEM_POSITIONS.get(system.system_type, (i % 3, i // 3))
            rx = base_x + pos[0] * (room_w + gap)
            ry = base_y + pos[1] * (room_h + gap)
            is_selected = i == self.selected_index

            # Room background color based on maintenance
            if system.is_critical:
                room_color = (60, 15, 15)
            elif system.is_warning:
                room_color = (50, 40, 10)
            else:
                room_color = (15, 25, 15)

            room_surf = pygame.Surface((room_w, room_h), pygame.SRCALPHA)
            room_surf.fill((*room_color, 200))
            surface.blit(room_surf, (rx, ry))

            border_color = AMBER if is_selected else PANEL_BORDER
            pygame.draw.rect(surface, border_color, (rx, ry, room_w, room_h), 2 if is_selected else 1, border_radius=4)

            # System name
            name = self.font_small.render(system.name, True, WHITE if is_selected else LIGHT_GREY)
            surface.blit(name, (rx + 5, ry + 5))

            # Maintenance bar
            bar_y = ry + room_h - 18
            bar_w = room_w - 10
            bar_h = 8
            pct = system.maintenance_level / 100.0
            fill_color = HULL_GREEN if pct > 0.5 else AMBER if pct > 0.25 else RED_ALERT
            pygame.draw.rect(surface, (30, 30, 40), (rx + 5, bar_y, bar_w, bar_h))
            pygame.draw.rect(surface, fill_color, (rx + 5, bar_y, int(bar_w * pct), bar_h))

            # Percentage
            pct_text = f"{system.maintenance_level:.0f}%"
            pct_surf = self.font_small.render(pct_text, True, fill_color)
            surface.blit(pct_surf, (rx + 5, ry + room_h - 34))

    def _draw_system_list(self, surface: pygame.Surface) -> None:
        """Draw system list on the right side."""
        list_x = SCREEN_WIDTH - 310
        list_y = 90

        header = self.font_info.render("SYSTEMS", True, AMBER)
        surface.blit(header, (list_x, list_y))

        for i, system in enumerate(self.systems):
            sy = list_y + 28 + i * 28
            is_selected = i == self.selected_index

            prefix = "▸" if is_selected else " "
            name_color = WHITE if is_selected else LIGHT_GREY
            name_surf = self.font_small.render(f"{prefix} {system.name}", True, name_color)
            surface.blit(name_surf, (list_x, sy))

            # Status indicator
            pct = system.maintenance_level
            status_color = HULL_GREEN if pct > 50 else AMBER if pct > 25 else RED_ALERT
            status_surf = self.font_small.render(f"{pct:.0f}%", True, status_color)
            surface.blit(status_surf, (list_x + 220, sy))

    def _draw_system_detail(self, surface: pygame.Surface, system: ShipSystem) -> None:
        """Draw detailed info for the selected system."""
        panel_x = SCREEN_WIDTH - 310
        panel_y = 340
        panel_w = 295
        panel_h = 220

        bg = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        bg.fill(PANEL_BG)
        surface.blit(bg, (panel_x, panel_y))
        pygame.draw.rect(surface, PANEL_BORDER, (panel_x, panel_y, panel_w, panel_h), 1, border_radius=4)

        # System name
        name_surf = self.font_name.render(system.name, True, AMBER)
        surface.blit(name_surf, (panel_x + 10, panel_y + 8))

        # Description
        desc_surf = self.font_small.render(system.description[:50], True, LIGHT_GREY)
        surface.blit(desc_surf, (panel_x + 10, panel_y + 34))

        # Maintenance
        maint_text = f"Maintenance: {system.maintenance_level:.1f}%"
        pct = system.maintenance_level
        maint_color = HULL_GREEN if pct > 50 else AMBER if pct > 25 else RED_ALERT
        maint_surf = self.font_info.render(maint_text, True, maint_color)
        surface.blit(maint_surf, (panel_x + 10, panel_y + 58))

        # Effectiveness
        eff = system.effectiveness * 100
        eff_surf = self.font_info.render(f"Effectiveness: {eff:.0f}%", True, CYAN)
        surface.blit(eff_surf, (panel_x + 10, panel_y + 80))

        # Upgrade tier
        tier_text = f"Tier: {'★' * system.upgrade_tier}{'☆' * (5 - system.upgrade_tier)}"
        tier_surf = self.font_info.render(tier_text, True, AMBER)
        surface.blit(tier_surf, (panel_x + 10, panel_y + 102))

        # Components
        comp_y = panel_y + 128
        comp_header = self.font_small.render("Components:", True, LIGHT_GREY)
        surface.blit(comp_header, (panel_x + 10, comp_y))
        for j, comp in enumerate(system.components[:3]):
            cy = comp_y + 18 + j * 16
            q_color = {
                "standard": LIGHT_GREY,
                "alien": HULL_GREEN,
                "federation": CYAN,
            }.get(comp.quality.value, LIGHT_GREY)
            comp_text = f"  {comp.name} [{comp.quality.value}] {comp.condition:.0f}%"
            comp_surf = self.font_small.render(comp_text, True, q_color)
            surface.blit(comp_surf, (panel_x + 10, cy))

        # Repair cost
        cost = system.repair_cost(10)
        cost_text = f"Repair +10%: {cost['metal']} metal, {cost['energy']} energy"
        can_afford = (
            self.fleet.resources.metal >= cost["metal"]
            and self.fleet.resources.energy >= cost["energy"]
        )
        cost_color = HULL_GREEN if can_afford else RED_ALERT
        cost_surf = self.font_small.render(cost_text, True, cost_color)
        surface.blit(cost_surf, (panel_x + 10, panel_y + panel_h - 22))

    def _repair_selected(self) -> None:
        """Repair the selected system by 10%."""
        if self.selected_index >= len(self.systems):
            return

        system = self.systems[self.selected_index]
        if system.maintenance_level >= 100:
            self._message = f"{system.name} is already at full maintenance."
            self._message_color = LIGHT_GREY
            self._message_timer = 2.0
            return

        cost = system.repair_cost(10)
        if (self.fleet.resources.metal >= cost["metal"]
                and self.fleet.resources.energy >= cost["energy"]):
            self.fleet.resources.metal -= cost["metal"]
            self.fleet.resources.energy -= cost["energy"]
            system.repair(10)
            self._message = f"Repaired {system.name} (+10%)"
            self._message_color = HULL_GREEN
            self._message_timer = 2.0
        else:
            self._message = "Not enough resources!"
            self._message_color = RED_ALERT
            self._message_timer = 2.0
