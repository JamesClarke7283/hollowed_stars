"""Title screen with fade-in animation."""

from __future__ import annotations

import math

import pygame

from ..constants import (
    AMBER,
    CYAN,
    GAME_SUBTITLE,
    GAME_TITLE,
    LIGHT_GREY,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from ..states import GameState


class TitleScreen:
    """Title screen: logo fade-in, subtitle, blinking prompt."""

    def __init__(self) -> None:
        self.font_large = pygame.font.Font(None, 96)
        self.font_medium = pygame.font.Font(None, 48)
        self.font_small = pygame.font.Font(None, 32)
        self.title_alpha = 0.0
        self.subtitle_alpha = 0.0
        self.timer = 0.0
        self.next_state: GameState | None = None

    def handle_events(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if self.subtitle_alpha >= 255:
                self.next_state = GameState.SHIP_SELECT

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

        # Blinking prompt
        if self.subtitle_alpha >= 255:
            blink = (math.sin(self.timer * 3) + 1) / 2
            prompt_surf = self.font_small.render("Press any key to begin", True, LIGHT_GREY)
            prompt_surf.set_alpha(int(blink * 255))
            prompt_rect = prompt_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT * 2 // 3))
            surface.blit(prompt_surf, prompt_rect)
