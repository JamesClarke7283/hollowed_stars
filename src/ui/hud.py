"""HUD overlay — resource bars, colonist count, hull status."""

from __future__ import annotations

import pygame

from ..constants import (
    AMBER,
    CYAN,
    ENERGY_COLOR,
    HULL_GREEN,
    LIGHT_GREY,
    METAL_COLOR,
    PANEL_BG,
    PANEL_BORDER,
    RARE_COLOR,
    RED_ALERT,
    SCREEN_WIDTH,
    WHITE,
)
from ..models.ships import Fleet


class HUD:
    """Persistent heads-up display drawn over game screens."""

    def __init__(self) -> None:
        self.font = pygame.font.Font(None, 24)
        self.font_small = pygame.font.Font(None, 20)
        self.panel_height = 40

    def draw(self, surface: pygame.Surface, fleet: Fleet) -> None:
        # Semi-transparent top bar
        bar = pygame.Surface((SCREEN_WIDTH, self.panel_height), pygame.SRCALPHA)
        bar.fill(PANEL_BG)
        surface.blit(bar, (0, 0))

        # Border line
        pygame.draw.line(
            surface, PANEL_BORDER, (0, self.panel_height), (SCREEN_WIDTH, self.panel_height)
        )

        x = 15
        y = 10

        # Colonists
        col_color = RED_ALERT if fleet.colonists < 50_000 else WHITE
        self._draw_stat(surface, "👥", f"{fleet.colonists:,}", col_color, x, y)
        x += 160

        # Hull
        hull_pct = fleet.mothership.hull / fleet.mothership.max_hull
        hull_color = RED_ALERT if hull_pct < 0.3 else HULL_GREEN
        self._draw_stat(surface, "🛡", f"{fleet.mothership.hull:,}/{fleet.mothership.max_hull:,}", hull_color, x, y)
        x += 180

        # Metal
        self._draw_stat(surface, "⛏", f"{fleet.resources.metal:,}", METAL_COLOR, x, y)
        x += 130

        # Energy
        self._draw_stat(surface, "⚡", f"{fleet.resources.energy:,}", ENERGY_COLOR, x, y)
        x += 130

        # Rare materials
        self._draw_stat(surface, "💎", f"{fleet.resources.rare_materials:,}", RARE_COLOR, x, y)
        x += 130

        # Fleet count
        self._draw_stat(surface, "🚀", f"{fleet.total_ships}/{fleet.mothership.hangar_capacity}", CYAN, x, y)

    def _draw_stat(
        self,
        surface: pygame.Surface,
        icon: str,
        text: str,
        color: tuple[int, int, int],
        x: int,
        y: int,
    ) -> None:
        # Icon (using font fallback for emoji)
        icon_surf = self.font_small.render(icon, True, LIGHT_GREY)
        surface.blit(icon_surf, (x, y))
        # Value
        val_surf = self.font.render(text, True, color)
        surface.blit(val_surf, (x + 22, y - 1))
