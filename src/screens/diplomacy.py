"""Diplomacy screen — interact with alien factions.

PLAN.md: Alien civilisations can be communicated with via a diplomacy system
by interacting with any station, planet, etc. owned by them.
"""

from __future__ import annotations

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
from ..models.diplomacy import (
    DiplomacyAction,
    DiplomacyResult,
    Faction,
    FactionDisposition,
    FactionTrait,
    resolve_diplomacy_action,
)
from ..models.ships import Fleet
from ..states import GameState


# Disposition → colour mapping
_DISP_COLORS = {
    FactionDisposition.HOSTILE: RED_ALERT,
    FactionDisposition.WARY: AMBER,
    FactionDisposition.NEUTRAL: LIGHT_GREY,
    FactionDisposition.FRIENDLY: HULL_GREEN,
    FactionDisposition.ALLIED: CYAN,
}

# Action display names and descriptions
_ACTION_INFO: list[tuple[DiplomacyAction, str, str]] = [
    (DiplomacyAction.TRADE, "Trade", "Exchange technology for materials"),
    (DiplomacyAction.BUY_SUPPLIES, "Buy Supplies", "Purchase materials at the local market"),
    (DiplomacyAction.HIRE_GUIDES, "Hire Guides", "Recruit local scouts for intel and crew"),
    (DiplomacyAction.SHARE_TECHNOLOGY, "Share Tech", "Gift precursor knowledge for goodwill"),
    (DiplomacyAction.DEMAND_TRIBUTE, "Demand Tribute", "Use your advanced position to demand resources"),
    (DiplomacyAction.THREATEN, "Threaten", "Intimidate with your ancient warships"),
    (DiplomacyAction.OFFER_ALLIANCE, "Offer Alliance", "Propose a formal military alliance"),
    (DiplomacyAction.REQUEST_PASSAGE, "Request Passage", "Ask for safe transit through their territory"),
]


class DiplomacyScreen:
    """Modal diplomacy screen for interacting with alien factions."""

    def __init__(self, faction: Faction, fleet: Fleet) -> None:
        self.faction = faction
        self.fleet = fleet
        self.next_state: GameState | None = None

        # UI state
        self.selected_action: int = 0
        self.result: DiplomacyResult | None = None
        self.result_timer: float = 0.0
        self._action_cooldown: float = 0.0

        # Fonts
        self.font_title = pygame.font.Font(None, 42)
        self.font_heading = pygame.font.Font(None, 30)
        self.font_body = pygame.font.Font(None, 24)
        self.font_small = pygame.font.Font(None, 20)

    def handle_events(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return

        if event.key == pygame.K_ESCAPE or event.key == pygame.K_BACKSPACE:
            self.next_state = GameState.SYSTEM_VIEW
            return

        if self.result and self.result_timer > 1.0:
            # Any key dismisses result
            if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                if self.result.triggers_combat:
                    # Signal to game.py that combat should start
                    self.next_state = GameState.SYSTEM_VIEW
                    return
                self.result = None
                return

        if self._action_cooldown > 0:
            return

        if event.key == pygame.K_UP:
            self.selected_action = (self.selected_action - 1) % len(_ACTION_INFO)
        elif event.key == pygame.K_DOWN:
            self.selected_action = (self.selected_action + 1) % len(_ACTION_INFO)
        elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
            self._execute_action()

    def _execute_action(self) -> None:
        """Execute the currently selected diplomatic action."""
        action, _, _ = _ACTION_INFO[self.selected_action]
        import random
        self.result = resolve_diplomacy_action(action, self.faction, random.Random())

        # Apply relation change
        self.faction.adjust_relation(self.result.relation_change)

        # Apply resource gains to fleet
        if self.result.metal_gained:
            self.fleet.resources.metal += self.result.metal_gained
        if self.result.energy_gained:
            self.fleet.resources.energy += self.result.energy_gained
        if self.result.rare_gained:
            self.fleet.resources.rare_materials += self.result.rare_gained
        if self.result.colonists_gained:
            self.fleet.colonists += self.result.colonists_gained

        self.result_timer = 0.0
        self._action_cooldown = 0.5

    def update(self, dt: float) -> None:
        if self.result:
            self.result_timer += dt
        if self._action_cooldown > 0:
            self._action_cooldown -= dt

    def draw(self, surface: pygame.Surface) -> None:
        # Background overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 10, 20, 230))
        surface.blit(overlay, (0, 0))

        # Main panel
        panel_w, panel_h = 800, 560
        px = (SCREEN_WIDTH - panel_w) // 2
        py = (SCREEN_HEIGHT - panel_h) // 2
        pygame.draw.rect(surface, PANEL_BG, (px, py, panel_w, panel_h), border_radius=8)
        pygame.draw.rect(surface, PANEL_BORDER, (px, py, panel_w, panel_h), 2, border_radius=8)

        # -- Header section --
        self._draw_header(surface, px, py, panel_w)

        # -- Faction info --
        self._draw_faction_info(surface, px + 20, py + 90, panel_w - 40)

        # -- Actions --
        self._draw_actions(surface, px + 20, py + 240, panel_w - 40)

        # -- Result overlay --
        if self.result:
            self._draw_result(surface, px, py, panel_w, panel_h)

        # Back hint
        hint = self.font_small.render("ESC — Back to System View", True, LIGHT_GREY)
        surface.blit(hint, (px + 20, py + panel_h - 30))

    def _draw_header(self, surface: pygame.Surface, px: int, py: int, pw: int) -> None:
        """Draw faction name, species, and disposition badge."""
        # Title
        title = self.font_title.render(f"— {self.faction.name} —", True, CYAN)
        surface.blit(title, (px + (pw - title.get_width()) // 2, py + 12))

        # Species name
        species = self.font_heading.render(
            f"Species: {self.faction.species_name}", True, LIGHT_GREY,
        )
        surface.blit(species, (px + 20, py + 58))

        # Disposition badge
        disp = self.faction.disposition
        disp_color = _DISP_COLORS.get(disp, LIGHT_GREY)
        disp_text = self.font_heading.render(
            disp.value.upper(), True, disp_color,
        )
        surface.blit(disp_text, (px + pw - disp_text.get_width() - 20, py + 58))

    def _draw_faction_info(self, surface: pygame.Surface, x: int, y: int, w: int) -> None:
        """Draw faction description, traits, and relation bar."""
        # Description (word-wrapped)
        words = self.faction.description.split()
        lines: list[str] = []
        current_line = ""
        for word in words:
            test = f"{current_line} {word}".strip()
            if self.font_body.size(test)[0] > w - 20:
                lines.append(current_line)
                current_line = word
            else:
                current_line = test
        if current_line:
            lines.append(current_line)

        for line in lines[:3]:
            ts = self.font_body.render(line, True, LIGHT_GREY)
            surface.blit(ts, (x, y))
            y += 22

        y += 8

        # Traits
        trait_str = "Traits: " + ", ".join(t.value.title() for t in self.faction.traits)
        ts = self.font_body.render(trait_str, True, AMBER)
        surface.blit(ts, (x, y))
        y += 24

        # Tech level
        tech_str = f"Technology Level: {'★' * self.faction.tech_level}{'☆' * (5 - self.faction.tech_level)}"
        ts = self.font_body.render(tech_str, True, LIGHT_GREY)
        surface.blit(ts, (x, y))
        y += 24

        # Local settlement info
        if self.faction.settlement_name:
            settle_str = f"Settlement: {self.faction.settlement_name}  (Local attitude: {self.faction.settlement_attitude:+d})"
            sc = HULL_GREEN if self.faction.settlement_attitude > 10 else (RED_ALERT if self.faction.settlement_attitude < -10 else LIGHT_GREY)
            ss = self.font_body.render(settle_str, True, sc)
            surface.blit(ss, (x, y))
            y += 28
        else:
            y += 4

        # Relation bar
        label = self.font_body.render("Relations:", True, WHITE)
        surface.blit(label, (x, y))

        bar_x = x + label.get_width() + 10
        bar_w = w - label.get_width() - 30
        bar_h = 16

        # Background
        pygame.draw.rect(surface, (30, 30, 40), (bar_x, y + 2, bar_w, bar_h), border_radius=3)

        # Fill (relation mapped from -100..+100 to 0..bar_w)
        fill_ratio = (self.faction.relation + 100) / 200.0
        fill_w = max(2, int(bar_w * fill_ratio))

        disp_color = _DISP_COLORS.get(self.faction.disposition, LIGHT_GREY)
        pygame.draw.rect(surface, disp_color, (bar_x, y + 2, fill_w, bar_h), border_radius=3)

        # Relation number
        rel_text = self.font_small.render(f"{self.faction.relation:+d}", True, WHITE)
        surface.blit(rel_text, (bar_x + bar_w + 5, y + 1))

    def _draw_actions(self, surface: pygame.Surface, x: int, y: int, w: int) -> None:
        """Draw the list of diplomatic actions."""
        header = self.font_heading.render("Diplomatic Actions", True, WHITE)
        surface.blit(header, (x, y))
        y += 30

        for i, (action, label, desc) in enumerate(_ACTION_INFO):
            selected = i == self.selected_action

            # Selection highlight
            if selected:
                pygame.draw.rect(
                    surface, (20, 40, 65),
                    (x - 4, y - 2, w + 8, 40),
                    border_radius=4,
                )

            color = CYAN if selected else LIGHT_GREY
            prefix = "▸ " if selected else "  "

            label_surf = self.font_body.render(f"{prefix}{label}", True, color)
            surface.blit(label_surf, (x, y + 2))

            desc_surf = self.font_small.render(desc, True, DARK_GREY if not selected else LIGHT_GREY)
            surface.blit(desc_surf, (x + 200, y + 6))

            y += 42

    def _draw_result(self, surface: pygame.Surface, px: int, py: int, pw: int, ph: int) -> None:
        """Draw the result of a diplomatic action as an overlay."""
        # Dim background
        dim = pygame.Surface((pw, ph), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 180))
        surface.blit(dim, (px, py))

        # Result panel
        rw, rh = 600, 220
        rx = px + (pw - rw) // 2
        ry = py + (ph - rh) // 2

        pygame.draw.rect(surface, PANEL_BG, (rx, ry, rw, rh), border_radius=6)
        border_color = HULL_GREEN if self.result.success else RED_ALERT
        pygame.draw.rect(surface, border_color, (rx, ry, rw, rh), 2, border_radius=6)

        # Result title
        status = "SUCCESS" if self.result.success else "FAILED"
        title_color = HULL_GREEN if self.result.success else RED_ALERT
        title = self.font_heading.render(status, True, title_color)
        surface.blit(title, (rx + (rw - title.get_width()) // 2, ry + 15))

        # Result description (word-wrapped)
        words = self.result.description.split()
        lines: list[str] = []
        current = ""
        for word in words:
            test = f"{current} {word}".strip()
            if self.font_body.size(test)[0] > rw - 40:
                lines.append(current)
                current = word
            else:
                current = test
        if current:
            lines.append(current)

        ty = ry + 50
        for line in lines[:4]:
            ts = self.font_body.render(line, True, WHITE)
            surface.blit(ts, (rx + 20, ty))
            ty += 22

        # Rewards summary
        ty += 10
        rewards = []
        if self.result.metal_gained:
            rewards.append(f"+{self.result.metal_gained} Metal")
        if self.result.energy_gained:
            rewards.append(f"+{self.result.energy_gained} Energy")
        if self.result.rare_gained:
            rewards.append(f"+{self.result.rare_gained} Rare Materials")
        if self.result.colonists_gained:
            rewards.append(f"+{self.result.colonists_gained} Colonists")
        if self.result.relation_change:
            sign = "+" if self.result.relation_change > 0 else ""
            rewards.append(f"{sign}{self.result.relation_change} Relations")

        if rewards:
            reward_str = "  |  ".join(rewards)
            rs = self.font_body.render(reward_str, True, AMBER)
            surface.blit(rs, (rx + (rw - rs.get_width()) // 2, ty))

        # Continue hint
        if self.result_timer > 1.0:
            if self.result.triggers_combat:
                hint = self.font_small.render("ENTER — Engage in combat", True, RED_ALERT)
            else:
                hint = self.font_small.render("ENTER — Continue", True, LIGHT_GREY)
            surface.blit(hint, (rx + (rw - hint.get_width()) // 2, ry + rh - 30))
