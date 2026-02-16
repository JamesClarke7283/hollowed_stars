"""Title screen with fade-in animation and menu."""

from __future__ import annotations

import math

import pygame

from ..constants import (
    AMBER,
    CYAN,
    DARK_GREY,
    GAME_SUBTITLE,
    GAME_TITLE,
    GAME_VERSION,
    HULL_GREEN,
    LIGHT_GREY,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    WHITE,
)
from ..models.save import has_save
from ..states import GameState


class TitleScreen:
    """Title screen: logo fade-in, subtitle, menu options."""

    def __init__(self) -> None:
        self.font_large = pygame.font.Font(None, 96)
        self.font_medium = pygame.font.Font(None, 48)
        self.font_menu = pygame.font.Font(None, 36)
        self.font_small = pygame.font.Font(None, 28)
        self.font_version = pygame.font.Font(None, 22)
        self.title_alpha = 0.0
        self.subtitle_alpha = 0.0
        self.timer = 0.0
        self.next_state: GameState | None = None

        # Menu
        self.load_save = False  # True when player picks "Continue"
        self._menu_items = self._build_menu()
        self.selected = 0

    def _build_menu(self) -> list[tuple[str, GameState | str]]:
        items = []
        if has_save():
            items.append(("Continue", "load"))
        items.append(("New Game", GameState.SHIP_SELECT))
        items.append(("Credits", GameState.CREDITS))
        return items

    def handle_events(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if self.subtitle_alpha < 255:
                return  # Wait for fade-in
            if event.key in (pygame.K_UP, pygame.K_w):
                self.selected = (self.selected - 1) % len(self._menu_items)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected = (self.selected + 1) % len(self._menu_items)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                _, action = self._menu_items[self.selected]
                if action == "load":
                    self.load_save = True
                    self.next_state = GameState.STAR_MAP
                else:
                    self.next_state = action

    def update(self, dt: float) -> None:
        self.timer += dt
        if self.title_alpha < 255:
            self.title_alpha = min(255, self.title_alpha + 150 * dt)
        elif self.subtitle_alpha < 255:
            self.subtitle_alpha = min(255, self.subtitle_alpha + 120 * dt)

    def draw(self, surface: pygame.Surface) -> None:
        # Title
        title_surf = self.font_large.render(GAME_TITLE, True, AMBER)
        title_surf.set_alpha(int(self.title_alpha))
        title_rect = title_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 3))
        surface.blit(title_surf, title_rect)

        # Subtitle
        sub_surf = self.font_medium.render(GAME_SUBTITLE, True, CYAN)
        sub_surf.set_alpha(int(self.subtitle_alpha))
        sub_rect = sub_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 3 + 70))
        surface.blit(sub_surf, sub_rect)

        # Menu
        if self.subtitle_alpha >= 255:
            menu_y = SCREEN_HEIGHT // 2 + 40
            for i, (label, _) in enumerate(self._menu_items):
                is_sel = i == self.selected
                color = AMBER if is_sel else LIGHT_GREY
                prefix = "▸ " if is_sel else "  "
                text_surf = self.font_menu.render(f"{prefix}{label}", True, color)
                text_rect = text_surf.get_rect(center=(SCREEN_WIDTH // 2, menu_y + i * 45))
                surface.blit(text_surf, text_rect)

        # Version number (bottom-right)
        ver_surf = self.font_version.render(f"v{GAME_VERSION}", True, LIGHT_GREY)
        ver_surf.set_alpha(120)
        surface.blit(ver_surf, (SCREEN_WIDTH - ver_surf.get_width() - 10, SCREEN_HEIGHT - 24))
