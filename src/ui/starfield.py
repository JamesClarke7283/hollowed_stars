"""Twinkling star field background — reusable across screens."""

from __future__ import annotations

import math
import random

import pygame

from ..constants import (
    NUM_BACKGROUND_STARS,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    STAR_DIM,
    STAR_WHITE,
    WHITE,
)


class StarField:
    """Animated twinkling star background."""

    def __init__(self, count: int = NUM_BACKGROUND_STARS) -> None:
        self.timer = 0.0
        self.stars: list[dict] = []
        for _ in range(count):
            self.stars.append(
                {
                    "x": random.randint(0, SCREEN_WIDTH),
                    "y": random.randint(0, SCREEN_HEIGHT),
                    "radius": random.choice([1, 1, 1, 2]),
                    "color": random.choice([STAR_WHITE, STAR_DIM, WHITE]),
                    "twinkle_speed": random.uniform(0.5, 2.0),
                    "twinkle_offset": random.uniform(0, math.tau),
                }
            )

    def update(self, dt: float) -> None:
        self.timer += dt

    def draw(self, surface: pygame.Surface) -> None:
        for star in self.stars:
            brightness = 0.5 + 0.5 * math.sin(
                self.timer * star["twinkle_speed"] + star["twinkle_offset"]
            )
            r = int(star["color"][0] * brightness)
            g = int(star["color"][1] * brightness)
            b = int(star["color"][2] * brightness)
            pygame.draw.circle(
                surface, (r, g, b), (star["x"], star["y"]), star["radius"]
            )
