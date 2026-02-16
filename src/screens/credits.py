"""Credits screen — scrolling credits display."""

from __future__ import annotations

import math

import pygame

from ..constants import (
    AMBER,
    CYAN,
    DARK_GREY,
    GAME_VERSION,
    HULL_GREEN,
    LIGHT_GREY,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    WHITE,
)
from ..states import GameState

# Credits data: (role, name, colour)
CREDITS_DATA: list[tuple[str, str, tuple[int, int, int]]] = [
    ("", "HOLLOWED STARS", AMBER),
    ("", "The Last Fleet", CYAN),
    ("", "", WHITE),
    ("Programmer", "James Clarke", WHITE),
    ("Original Story", "Kian Rahman", WHITE),
    ("", "", WHITE),
    ("Engine", "Pygame-CE", LIGHT_GREY),
    ("Language", "Python", LIGHT_GREY),
    ("", "", WHITE),
    ("", f"Version {GAME_VERSION}", DARK_GREY),
    ("", "", WHITE),
    ("", "Thank you for playing.", AMBER),
]


class CreditsScreen:
    """Auto-scrolling credits with manual ESC to return."""

    def __init__(self) -> None:
        self.font_title = pygame.font.Font(None, 64)
        self.font_role = pygame.font.Font(None, 28)
        self.font_name = pygame.font.Font(None, 38)
        self.font_hint = pygame.font.Font(None, 22)

        self.scroll_y = float(SCREEN_HEIGHT)
        self.speed = 40.0  # pixels per second
        self.next_state: GameState | None = None
        self.timer = 0.0

    def handle_events(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.next_state = GameState.TITLE

    def update(self, dt: float) -> None:
        self.timer += dt
        self.scroll_y -= self.speed * dt

    def draw(self, surface: pygame.Surface) -> None:
        y = self.scroll_y

        for role, name, color in CREDITS_DATA:
            if not role and not name:
                y += 30
                continue

            if role:
                role_surf = self.font_role.render(role, True, DARK_GREY)
                role_rect = role_surf.get_rect(center=(SCREEN_WIDTH // 2, y))
                if -50 < role_rect.centery < SCREEN_HEIGHT + 50:
                    surface.blit(role_surf, role_rect)
                y += 28

            if name:
                # Use title font for the game name
                font = self.font_title if name == "HOLLOWED STARS" else self.font_name
                name_color = color
                name_surf = font.render(name, True, name_color)
                name_rect = name_surf.get_rect(center=(SCREEN_WIDTH // 2, y))
                if -50 < name_rect.centery < SCREEN_HEIGHT + 50:
                    surface.blit(name_surf, name_rect)
                y += 45
            elif role:
                y += 10

        # Hint
        hint = self.font_hint.render("ESC — return to title", True, LIGHT_GREY)
        surface.blit(hint, (10, SCREEN_HEIGHT - 25))

        # Auto-return when scrolled past everything
        total_height = sum(
            75 if r or n else 30 for r, n, _ in CREDITS_DATA
        )
        if self.scroll_y < -total_height:
            self.next_state = GameState.TITLE
