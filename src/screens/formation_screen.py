"""Pre-combat formation setup screen.

PLAN.md: "Your combat ships are assigned a position in the formation
before combat and this formation order cannot be changed during it."
"""

from __future__ import annotations

import pygame

from src.constants import (
    AMBER,
    BLACK,
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
from src.models.ships import Fleet, FleetShip
from src.states import GameState


class FormationScreen:
    """Allows the player to arrange combat ship formation before battle."""

    def __init__(self) -> None:
        self.fleet: Fleet | None = None
        self.combat_ships: list[FleetShip] = []
        self.selected_index: int = 0
        self.next_state: GameState | None = None
        self.confirmed: bool = False

        # Fonts
        self.title_font = pygame.font.SysFont("monospace", 32, bold=True)
        self.label_font = pygame.font.SysFont("monospace", 20, bold=True)
        self.body_font = pygame.font.SysFont("monospace", 16)
        self.hint_font = pygame.font.SysFont("monospace", 14)

    def setup(self, fleet: Fleet) -> None:
        """Initialize the screen with the current fleet."""
        self.fleet = fleet
        # Only combat ships participate in formation
        self.combat_ships = [s for s in fleet.ships if s.is_combat]
        # Sort by current formation slot
        self.combat_ships.sort(key=lambda s: s.formation_slot)
        self.selected_index = 0
        self.confirmed = False
        self.next_state = None

    def handle_events(self, event: pygame.event.Event) -> None:
        """Handle input for formation arrangement."""
        if event.type != pygame.KEYDOWN:
            return

        if event.key == pygame.K_UP or event.key == pygame.K_w:
            self.selected_index = max(0, self.selected_index - 1)
        elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
            self.selected_index = min(
                len(self.combat_ships) - 1, self.selected_index + 1
            )
        elif event.key == pygame.K_PAGEUP:
            # Move selected ship UP in formation
            if self.selected_index > 0:
                ships = self.combat_ships
                ships[self.selected_index], ships[self.selected_index - 1] = (
                    ships[self.selected_index - 1],
                    ships[self.selected_index],
                )
                self.selected_index -= 1
                self._reassign_slots()
        elif event.key == pygame.K_PAGEDOWN:
            # Move selected ship DOWN in formation
            if self.selected_index < len(self.combat_ships) - 1:
                ships = self.combat_ships
                ships[self.selected_index], ships[self.selected_index + 1] = (
                    ships[self.selected_index + 1],
                    ships[self.selected_index],
                )
                self.selected_index += 1
                self._reassign_slots()
        elif event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
            self.confirmed = True
            self.next_state = GameState.COMBAT

    def _reassign_slots(self) -> None:
        """Update formation_slot values to match current order."""
        for i, ship in enumerate(self.combat_ships):
            ship.formation_slot = i + 1

    def update(self, dt: float) -> None:
        """No continuous updates needed."""
        pass

    def draw(self, surface: pygame.Surface) -> None:
        """Draw the formation setup screen."""
        if not self.fleet:
            return

        # Title
        title = self.title_font.render("FORMATION SETUP", True, AMBER)
        surface.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 30))

        subtitle = self.body_font.render(
            "Arrange your combat ships. Front ships engage first.",
            True, LIGHT_GREY,
        )
        surface.blit(subtitle, (SCREEN_WIDTH // 2 - subtitle.get_width() // 2, 70))

        # Formation list
        list_x = 200
        list_y = 120
        row_height = 40

        # Header
        header = self.label_font.render(
            f"{'#':>3}  {'Ship Name':<25} {'Class':<18} {'Hull':>6}  {'Weapons':>7}",
            True, CYAN,
        )
        surface.blit(header, (list_x, list_y))
        list_y += row_height

        # Draw separator
        pygame.draw.line(
            surface, PANEL_BORDER,
            (list_x, list_y - 5),
            (list_x + 700, list_y - 5),
        )

        for i, ship in enumerate(self.combat_ships):
            is_selected = i == self.selected_index
            color = AMBER if is_selected else WHITE

            # Highlight bar
            if is_selected:
                highlight_rect = pygame.Rect(
                    list_x - 10, list_y - 2, 720, row_height - 4
                )
                highlight_surf = pygame.Surface(
                    highlight_rect.size, pygame.SRCALPHA
                )
                highlight_surf.fill((255, 191, 0, 40))
                surface.blit(highlight_surf, highlight_rect)

            # Position indicator
            pos_label = "FRONT" if i == 0 else "REAR" if i == len(self.combat_ships) - 1 else ""
            pos_color = RED_ALERT if i == 0 else HULL_GREEN if i == len(self.combat_ships) - 1 else LIGHT_GREY

            # Ship info
            weapons_count = sum(1 for w in ship.weapon_slots if w.equipped)
            total_slots = len(ship.weapon_slots)
            class_name = ship.ship_class.value.replace("_", " ").title()

            line = self.body_font.render(
                f"{i + 1:>3}  {ship.name:<25} {class_name:<18} {ship.hull:>5}/{ship.max_hull}  {weapons_count}/{total_slots}",
                True, color,
            )
            surface.blit(line, (list_x, list_y))

            # Position tag
            if pos_label:
                tag = self.hint_font.render(pos_label, True, pos_color)
                surface.blit(tag, (list_x + 730, list_y + 2))

            list_y += row_height

        # Controls help
        help_y = SCREEN_HEIGHT - 100
        controls = [
            ("↑/↓ or W/S", "Select ship"),
            ("PgUp/PgDn", "Move ship in formation"),
            ("ENTER", "Confirm and begin combat"),
        ]

        for key, desc in controls:
            help_text = self.hint_font.render(f"  {key}: {desc}", True, LIGHT_GREY)
            surface.blit(help_text, (list_x, help_y))
            help_y += 20

        # Ship count
        count_text = self.body_font.render(
            f"{len(self.combat_ships)} combat ships ready",
            True, HULL_GREEN if self.combat_ships else RED_ALERT,
        )
        surface.blit(count_text, (SCREEN_WIDTH // 2 - count_text.get_width() // 2, SCREEN_HEIGHT - 40))
