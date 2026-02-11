"""Mothership selection screen."""

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
    SHIELD_BLUE,
    WHITE,
)
from ..models.ships import MOTHERSHIPS, Fleet, Mothership
from ..states import GameState


class ShipSelectScreen:
    """Choose your mothership before the journey begins."""

    def __init__(self) -> None:
        self.ships = MOTHERSHIPS
        self.selected_index = 0
        self.font_title = pygame.font.Font(None, 56)
        self.font_name = pygame.font.Font(None, 44)
        self.font_body = pygame.font.Font(None, 26)
        self.font_stat = pygame.font.Font(None, 24)
        self.font_hint = pygame.font.Font(None, 28)

        self.next_state: GameState | None = None
        self.chosen_fleet: Fleet | None = None
        self.timer = 0.0

    @property
    def selected_ship(self) -> Mothership:
        return self.ships[self.selected_index]

    def handle_events(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_LEFT, pygame.K_a):
                self.selected_index = (self.selected_index - 1) % len(self.ships)
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                self.selected_index = (self.selected_index + 1) % len(self.ships)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._confirm_selection()

    def update(self, dt: float) -> None:
        self.timer += dt

    def draw(self, surface: pygame.Surface) -> None:
        # Header
        header = self.font_title.render("CHOOSE YOUR MOTHERSHIP", True, AMBER)
        header_rect = header.get_rect(center=(SCREEN_WIDTH // 2, 50))
        surface.blit(header, header_rect)

        # Ship cards
        card_w = 340
        card_h = 500
        total_w = card_w * len(self.ships) + 30 * (len(self.ships) - 1)
        start_x = (SCREEN_WIDTH - total_w) // 2

        for i, ship in enumerate(self.ships):
            x = start_x + i * (card_w + 30)
            y = 90
            is_selected = i == self.selected_index

            self._draw_ship_card(surface, ship, x, y, card_w, card_h, is_selected)

        # Navigation hint
        blink = (math.sin(self.timer * 2.5) + 1) / 2
        hint = self.font_hint.render("◄ A/D ►   ENTER to confirm", True, LIGHT_GREY)
        hint.set_alpha(int(150 + blink * 105))
        hint_rect = hint.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 40))
        surface.blit(hint, hint_rect)

    def _draw_ship_card(
        self,
        surface: pygame.Surface,
        ship: Mothership,
        x: int,
        y: int,
        w: int,
        h: int,
        selected: bool,
    ) -> None:
        # Card background
        card = pygame.Surface((w, h), pygame.SRCALPHA)
        card.fill(PANEL_BG)
        surface.blit(card, (x, y))

        # Border (highlighted if selected)
        border_color = AMBER if selected else PANEL_BORDER
        border_width = 3 if selected else 1
        pygame.draw.rect(surface, border_color, (x, y, w, h), border_width, border_radius=6)

        # Selection glow
        if selected:
            glow = pygame.Surface((w + 8, h + 8), pygame.SRCALPHA)
            glow_alpha = int(30 + 20 * math.sin(self.timer * 3))
            glow.fill((*AMBER, glow_alpha))
            surface.blit(glow, (x - 4, y - 4))

        # Ship silhouette area
        silhouette_rect = pygame.Rect(x + 20, y + 15, w - 40, 100)
        pygame.draw.rect(surface, (15, 15, 25), silhouette_rect, border_radius=4)

        # Simple ship shape based on type
        cx = silhouette_rect.centerx
        cy = silhouette_rect.centery
        ship_color = AMBER if selected else LIGHT_GREY

        if ship.name == "Iron Bastion":
            # Bulky rectangle shape
            points = [
                (cx - 40, cy - 15), (cx + 50, cy - 15), (cx + 60, cy),
                (cx + 50, cy + 15), (cx - 40, cy + 15), (cx - 50, cy),
            ]
        elif ship.name == "Whisper of Stars":
            # Sleek narrow shape
            points = [
                (cx - 20, cy - 8), (cx + 60, cy), (cx - 20, cy + 8),
                (cx - 35, cy + 5), (cx - 40, cy), (cx - 35, cy - 5),
            ]
        else:
            # Balanced shape (Aegis of Dawn)
            points = [
                (cx - 30, cy - 12), (cx + 55, cy), (cx - 30, cy + 12),
                (cx - 45, cy + 8), (cx - 45, cy - 8),
            ]
        pygame.draw.polygon(surface, ship_color, points)
        # Engine glow
        pygame.draw.circle(surface, CYAN, (int(points[-1][0]) - 5, cy), 4)

        # Ship name
        name_surf = self.font_name.render(ship.name, True, WHITE if selected else LIGHT_GREY)
        name_rect = name_surf.get_rect(center=(x + w // 2, y + 140))
        surface.blit(name_surf, name_rect)

        # Description (word-wrapped)
        desc_lines = self._wrap_text(ship.description, self.font_body, w - 40)
        for i, line in enumerate(desc_lines[:3]):
            desc_surf = self.font_body.render(line, True, LIGHT_GREY)
            desc_rect = desc_surf.get_rect(center=(x + w // 2, y + 168 + i * 22))
            surface.blit(desc_surf, desc_rect)

        # Stats
        stats_y = y + 170 + len(desc_lines[:3]) * 22 + 10
        stats = [
            ("Hull", f"{ship.max_hull:,}", HULL_GREEN),
            ("Armor", f"{ship.armor}", SHIELD_BLUE),
            ("Power", f"{ship.max_power:,}", CYAN),
            ("Speed", f"{ship.speed:.1f}x", WHITE),
            ("Sensors", f"{ship.sensor_range:.1f}x", WHITE),
            ("Colonists", f"{ship.colonist_capacity:,}", WHITE),
            ("Hangar", f"{ship.hangar_capacity} ships", WHITE),
            ("Weapons", f"{len(ship.weapon_slots)} slots", RED_ALERT),
        ]

        for j, (label, value, color) in enumerate(stats):
            sy = stats_y + j * 24
            lbl = self.font_stat.render(f"{label}:", True, LIGHT_GREY)
            surface.blit(lbl, (x + 20, sy))
            val = self.font_stat.render(value, True, color)
            surface.blit(val, (x + w - 20 - val.get_width(), sy))

        # Special ability
        ability_y = stats_y + len(stats) * 24 + 10
        ability_label = self.font_stat.render("Special:", True, AMBER)
        surface.blit(ability_label, (x + 20, ability_y))
        ability_name = self.font_stat.render(ship.special_ability, True, CYAN)
        surface.blit(ability_name, (x + 20, ability_y + 22))

    def _wrap_text(self, text: str, font: pygame.font.Font, max_width: int) -> list[str]:
        """Word-wrap text to fit within max_width pixels."""
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

    def _confirm_selection(self) -> None:
        ship = self.selected_ship
        self.chosen_fleet = Fleet(
            mothership=ship,
            colonists=min(1_000_000, ship.colonist_capacity),
        )
        self.next_state = GameState.STAR_MAP

