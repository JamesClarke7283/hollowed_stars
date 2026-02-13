"""Event dialog screen — narrative choices and outcomes."""

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
from ..models.events import Event, EventChoice, EventOutcome, EventOutcomeType
from ..models.ships import Fleet
from ..states import GameState


class EventDialogScreen:
    """Modal event dialog with narrative text and choice buttons."""

    def __init__(self, event: Event, fleet: Fleet) -> None:
        self.event = event
        self.fleet = fleet
        self.font_title = pygame.font.Font(None, 38)
        self.font_body = pygame.font.Font(None, 26)
        self.font_choice = pygame.font.Font(None, 28)
        self.font_outcome = pygame.font.Font(None, 26)
        self.font_small = pygame.font.Font(None, 22)

        self.selected_choice = 0
        self.outcome: EventOutcome | None = None
        self.next_state: GameState | None = None
        self.timer = 0.0

        # Combat trigger (set when outcome is COMBAT)
        self.trigger_combat = False
        self.combat_danger = 0
        self.combat_is_federation = False

        # Colony establishment flag (set when colonists are sent to establish a colony)
        self.colony_established = False

        # Quest flag resolved from outcome
        self.resolved_quest_flag: str = ""

    def handle_events(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if self.outcome is not None:
                # Outcome shown, any key to continue
                if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE):
                    if self.outcome.outcome_type == EventOutcomeType.COMBAT:
                        self.trigger_combat = True
                        self.combat_danger = self.outcome.combat_danger
                        self.combat_is_federation = self.outcome.combat_is_federation
                    self.next_state = GameState.SYSTEM_VIEW
            else:
                # Choosing
                if event.key in (pygame.K_UP, pygame.K_w):
                    self.selected_choice = max(0, self.selected_choice - 1)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    self.selected_choice = min(len(self.event.choices) - 1, self.selected_choice + 1)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self._make_choice(self.event.choices[self.selected_choice])

    def update(self, dt: float) -> None:
        self.timer += dt

    def draw(self, surface: pygame.Surface) -> None:
        # Dim background
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surface.blit(overlay, (0, 0))

        # Dialog panel
        panel_w = 650
        panel_h = 450
        px = (SCREEN_WIDTH - panel_w) // 2
        py = (SCREEN_HEIGHT - panel_h) // 2

        bg = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        bg.fill(PANEL_BG)
        surface.blit(bg, (px, py))
        pygame.draw.rect(surface, AMBER, (px, py, panel_w, panel_h), 2, border_radius=8)

        # Title
        title_surf = self.font_title.render(self.event.title, True, AMBER)
        title_rect = title_surf.get_rect(center=(SCREEN_WIDTH // 2, py + 30))
        surface.blit(title_surf, title_rect)

        # Description (word-wrapped)
        desc_lines = self._wrap_text(self.event.description, self.font_body, panel_w - 60)
        for i, line in enumerate(desc_lines[:6]):
            desc_surf = self.font_body.render(line, True, LIGHT_GREY)
            surface.blit(desc_surf, (px + 30, py + 60 + i * 24))

        desc_bottom = py + 60 + min(6, len(desc_lines)) * 24 + 20

        if self.outcome is None:
            # Draw choices
            for i, choice in enumerate(self.event.choices):
                cy = desc_bottom + i * 50
                is_selected = i == self.selected_choice

                # Choice box
                box_color = AMBER if is_selected else PANEL_BORDER
                pygame.draw.rect(surface, box_color, (px + 30, cy, panel_w - 60, 40), 2 if is_selected else 1, border_radius=4)

                # Selection indicator
                prefix = "▸ " if is_selected else "  "
                text_color = WHITE if is_selected else LIGHT_GREY
                choice_surf = self.font_choice.render(f"{prefix}{choice.text}", True, text_color)
                surface.blit(choice_surf, (px + 40, cy + 8))

                # Risk indicator
                if choice.success_chance < 1.0:
                    risk_pct = int(choice.success_chance * 100)
                    risk_color = HULL_GREEN if risk_pct >= 70 else AMBER if risk_pct >= 40 else RED_ALERT
                    risk_surf = self.font_small.render(f"{risk_pct}% success", True, risk_color)
                    surface.blit(risk_surf, (px + panel_w - 130, cy + 12))

            # Hint
            hint = self.font_small.render("W/S to select, ENTER to choose", True, LIGHT_GREY)
            hint_rect = hint.get_rect(center=(SCREEN_WIDTH // 2, py + panel_h - 20))
            surface.blit(hint, hint_rect)
        else:
            # Draw outcome
            outcome_color = self._outcome_color(self.outcome.outcome_type)
            outcome_lines = self._wrap_text(self.outcome.description, self.font_outcome, panel_w - 60)

            for i, line in enumerate(outcome_lines[:4]):
                out_surf = self.font_outcome.render(line, True, outcome_color)
                surface.blit(out_surf, (px + 30, desc_bottom + i * 26))

            # Show rewards/penalties
            rewards_y = desc_bottom + min(4, len(outcome_lines)) * 26 + 15
            rewards = self._format_rewards(self.outcome)
            for i, (text, color) in enumerate(rewards):
                r_surf = self.font_small.render(text, True, color)
                surface.blit(r_surf, (px + 40, rewards_y + i * 20))

            # Continue prompt
            blink = (math.sin(self.timer * 3) + 1) / 2
            prompt = self.font_small.render("Press ENTER to continue", True, LIGHT_GREY)
            prompt.set_alpha(int(blink * 255))
            prompt_rect = prompt.get_rect(center=(SCREEN_WIDTH // 2, py + panel_h - 20))
            surface.blit(prompt, prompt_rect)

    def _make_choice(self, choice: EventChoice) -> None:
        """Resolve a choice, applying success/failure."""
        import random
        if random.random() <= choice.success_chance:
            self.outcome = choice.outcome
        else:
            # Failed — reverse outcome or give nothing
            self.outcome = EventOutcome(
                EventOutcomeType.NOTHING,
                f"Your attempt failed! {choice.text} was unsuccessful.",
            )

        # Apply outcome to fleet
        self._apply_outcome(self.outcome)

    def _apply_outcome(self, outcome: EventOutcome) -> None:
        """Apply outcome effects to the player fleet."""
        self.fleet.resources.metal += outcome.metal
        self.fleet.resources.energy += outcome.energy
        self.fleet.resources.rare_materials += outcome.rare
        self.fleet.colonists += outcome.colonists
        self.fleet.mothership.hull += outcome.hull_change

        # Detect colony establishment (colonists sent to settle)
        if outcome.colonists < 0 and "colony" in outcome.description.lower():
            self.colony_established = True

        # Track quest flag for game.py to process
        if outcome.quest_flag:
            self.resolved_quest_flag = outcome.quest_flag

        # Clamp values
        self.fleet.colonists = max(0, self.fleet.colonists)
        self.fleet.mothership.hull = max(0, min(
            self.fleet.mothership.hull,
            self.fleet.mothership.max_hull,
        ))

    def _outcome_color(self, outcome_type: EventOutcomeType) -> tuple[int, int, int]:
        colors = {
            EventOutcomeType.GAIN_RESOURCES: HULL_GREEN,
            EventOutcomeType.GAIN_COLONISTS: CYAN,
            EventOutcomeType.GAIN_LORE: AMBER,
            EventOutcomeType.LOSE_RESOURCES: RED_ALERT,
            EventOutcomeType.LOSE_COLONISTS: RED_ALERT,
            EventOutcomeType.HULL_DAMAGE: RED_ALERT,
            EventOutcomeType.HULL_REPAIR: HULL_GREEN,
            EventOutcomeType.COMBAT: RED_ALERT,
            EventOutcomeType.QUEST_FLAG: AMBER,
            EventOutcomeType.NOTHING: LIGHT_GREY,
        }
        return colors.get(outcome_type, WHITE)

    def _format_rewards(self, outcome: EventOutcome) -> list[tuple[str, tuple[int, int, int]]]:
        """Format outcome rewards/penalties as display strings."""
        rewards = []
        if outcome.metal > 0:
            rewards.append((f"+{outcome.metal} Metal", HULL_GREEN))
        elif outcome.metal < 0:
            rewards.append((f"{outcome.metal} Metal", RED_ALERT))
        if outcome.energy > 0:
            rewards.append((f"+{outcome.energy} Energy", CYAN))
        if outcome.rare > 0:
            rewards.append((f"+{outcome.rare} Rare Materials", AMBER))
        if outcome.colonists > 0:
            rewards.append((f"+{outcome.colonists:,} Colonists", HULL_GREEN))
        elif outcome.colonists < 0:
            rewards.append((f"{outcome.colonists:,} Colonists", RED_ALERT))
        if outcome.hull_change > 0:
            rewards.append((f"+{outcome.hull_change} Hull", HULL_GREEN))
        elif outcome.hull_change < 0:
            rewards.append((f"{outcome.hull_change} Hull", RED_ALERT))
        if outcome.outcome_type == EventOutcomeType.COMBAT:
            rewards.append(("⚔ Combat incoming!", RED_ALERT))
        return rewards

    def _wrap_text(self, text: str, font: pygame.font.Font, max_width: int) -> list[str]:
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
