"""Colony management screen — view and advance active colonies.

Shows all colonies with their current stage, lets the player invest
resources to advance a colony, reachable from system view (C key) or
captain's log.
"""

from __future__ import annotations

import pygame

from ..constants import (
    AMBER,
    CYAN,
    DARK_GREY,
    HULL_GREEN,
    LIGHT_GREY,
    METAL_COLOR,
    ENERGY_COLOR,
    PANEL_BG,
    PANEL_BORDER,
    RED_ALERT,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    WHITE,
)
from ..models.colony import Colony, ColonyManager, ColonyStage
from ..models.ships import Fleet
from ..states import GameState


_STAGE_ICONS: dict[ColonyStage, str] = {
    ColonyStage.SURVEYED: "◎",
    ColonyStage.LANDING: "▽",
    ColonyStage.INFRASTRUCTURE: "▣",
    ColonyStage.TERRAFORMING: "◆",
    ColonyStage.ESTABLISHED: "★",
}

_STAGE_COLORS: dict[ColonyStage, tuple[int, int, int]] = {
    ColonyStage.SURVEYED: LIGHT_GREY,
    ColonyStage.LANDING: AMBER,
    ColonyStage.INFRASTRUCTURE: CYAN,
    ColonyStage.TERRAFORMING: (100, 200, 100),
    ColonyStage.ESTABLISHED: HULL_GREEN,
}


class ColonyScreen:
    """Colony management — view all colonies and invest resources."""

    def __init__(
        self, colony_manager: ColonyManager, fleet: Fleet,
        focus_system: int | None = None,
    ) -> None:
        self.colony_manager = colony_manager
        self.fleet = fleet
        self.next_state: GameState | None = None

        self.font_title = pygame.font.Font(None, 40)
        self.font_head = pygame.font.Font(None, 28)
        self.font_body = pygame.font.Font(None, 22)
        self.font_small = pygame.font.Font(None, 18)

        self.selected = 0
        self.message = ""
        self.message_timer = 0.0
        self.message_color = WHITE

        # If opened from a system with a colony, focus on it
        if focus_system is not None:
            for i, c in enumerate(self.colony_manager.colonies):
                if c.system_id == focus_system:
                    self.selected = i
                    break

    def handle_events(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return

        colonies = self.colony_manager.colonies
        if not colonies:
            if event.key in (pygame.K_ESCAPE, pygame.K_c):
                self.next_state = GameState.SYSTEM_VIEW
            return

        if event.key == pygame.K_UP:
            self.selected = max(0, self.selected - 1)
        elif event.key == pygame.K_DOWN:
            self.selected = min(len(colonies) - 1, self.selected + 1)
        elif event.key == pygame.K_RETURN:
            self._try_advance()
        elif event.key in (pygame.K_ESCAPE, pygame.K_c):
            self.next_state = GameState.SYSTEM_VIEW

    def _try_advance(self) -> None:
        colonies = self.colony_manager.colonies
        if not colonies or self.selected >= len(colonies):
            return
        colony = colonies[self.selected]

        if colony.is_established:
            self.message = "This colony is already fully established."
            self.message_color = HULL_GREEN
            self.message_timer = 3.0
            return

        cost = colony.advancement_cost
        if cost is None:
            return

        r = self.fleet.resources
        if not colony.can_advance(r.metal, r.energy, self.fleet.colonists):
            self.message = (
                f"Insufficient resources. Need: "
                f"{cost['metal']}M / {cost['energy']}E / "
                f"{cost['colonists']:,} colonists"
            )
            self.message_color = RED_ALERT
            self.message_timer = 4.0
            return

        # Deduct resources
        r.metal -= cost["metal"]
        r.energy -= cost["energy"]
        self.fleet.colonists -= cost["colonists"]

        # Advance
        desc = colony.advance()
        next_stage_name = colony.stage.value.replace("_", " ").title()
        self.message = f"Advanced to {next_stage_name}!"
        self.message_color = HULL_GREEN
        self.message_timer = 4.0

    def update(self, dt: float) -> None:
        if self.message_timer > 0:
            self.message_timer -= dt

    def draw(self, surface: pygame.Surface) -> None:
        # Background panel
        panel_w = SCREEN_WIDTH - 60
        panel_h = SCREEN_HEIGHT - 80
        px = 30
        py = 40

        bg = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        bg.fill((10, 14, 24, 230))
        surface.blit(bg, (px, py))
        pygame.draw.rect(
            surface, PANEL_BORDER, (px, py, panel_w, panel_h), 1,
            border_radius=6,
        )

        # Title
        title = self.font_title.render("COLONY MANAGEMENT", True, AMBER)
        surface.blit(title, (px + 20, py + 12))

        # Resource bar
        res = self.fleet.resources
        res_text = (
            f"Metal: {res.metal:,}  |  Energy: {res.energy:,}  |  "
            f"Rare: {res.rare_materials:,}  |  Colonists: {self.fleet.colonists:,}"
        )
        rs = self.font_small.render(res_text, True, LIGHT_GREY)
        surface.blit(rs, (px + 20, py + 48))

        y = py + 75
        colonies = self.colony_manager.colonies

        if not colonies:
            empty = self.font_body.render(
                "No active colonies. Survey planets to find colony sites.",
                True, DARK_GREY,
            )
            surface.blit(empty, (px + 40, y + 40))
        else:
            # Colony list (left panel)
            list_w = 340
            detail_x = px + list_w + 20

            for i, colony in enumerate(colonies):
                sel = i == self.selected
                row_y = y + i * 50
                if row_y > py + panel_h - 60:
                    break

                # Highlight
                if sel:
                    pygame.draw.rect(
                        surface, (20, 40, 65),
                        (px + 8, row_y - 2, list_w, 46),
                        border_radius=3,
                    )

                icon = _STAGE_ICONS.get(colony.stage, "?")
                color = _STAGE_COLORS.get(colony.stage, WHITE)

                # Icon + name
                ic = self.font_head.render(icon, True, color)
                surface.blit(ic, (px + 16, row_y + 4))
                ns = self.font_head.render(colony.planet_name, True, WHITE if sel else LIGHT_GREY)
                surface.blit(ns, (px + 42, row_y + 2))

                # Stage label
                stage_label = colony.stage.value.replace("_", " ").title()
                sl = self.font_small.render(stage_label, True, color)
                surface.blit(sl, (px + 42, row_y + 26))

                # Progress bar (stage_index / 4)
                bar_x = px + 200
                bar_w = 130
                bar_h = 8
                bar_y = row_y + 30
                pygame.draw.rect(surface, DARK_GREY, (bar_x, bar_y, bar_w, bar_h))
                fill_w = int(bar_w * (colony.stage_index / 4))
                if fill_w > 0:
                    pygame.draw.rect(surface, color, (bar_x, bar_y, fill_w, bar_h))

            # Detail panel (right side)
            if colonies and self.selected < len(colonies):
                colony = colonies[self.selected]
                self._draw_detail(surface, colony, detail_x, y, panel_w - list_w - 40)

        # Message
        if self.message and self.message_timer > 0:
            ms = self.font_body.render(self.message, True, self.message_color)
            surface.blit(ms, (px + 20, py + panel_h - 30))

        # Hints
        hint = "↑↓ Select   Enter — Invest Resources   Esc — Back"
        hs = self.font_small.render(hint, True, DARK_GREY)
        surface.blit(hs, (px + 20, py + panel_h + 8))

    def _draw_detail(
        self, surface: pygame.Surface, colony: Colony,
        x: int, y: int, w: int,
    ) -> None:
        """Draw colony detail panel."""
        # Stage header
        stage_name = colony.stage.value.replace("_", " ").upper()
        color = _STAGE_COLORS.get(colony.stage, WHITE)
        icon = _STAGE_ICONS.get(colony.stage, "?")
        header = self.font_head.render(f"{icon} {colony.planet_name}", True, WHITE)
        surface.blit(header, (x, y))
        y += 30

        stage_s = self.font_body.render(f"Stage: {stage_name}", True, color)
        surface.blit(stage_s, (x, y))
        y += 26

        # Description
        desc = colony.description
        lines = self._wrap(desc, w, self.font_body)
        for line in lines:
            ls = self.font_body.render(line, True, LIGHT_GREY)
            surface.blit(ls, (x, y))
            y += 20
        y += 16

        # Investment totals
        inv_header = self.font_head.render("Total Invested", True, AMBER)
        surface.blit(inv_header, (x, y))
        y += 26
        inv_text = (
            f"Metal: {colony.total_invested_metal:,}  "
            f"Energy: {colony.total_invested_energy:,}  "
            f"Colonists: {colony.total_invested_colonists:,}"
        )
        it = self.font_small.render(inv_text, True, LIGHT_GREY)
        surface.blit(it, (x, y))
        y += 28

        # Next stage cost
        cost = colony.advancement_cost
        if cost is not None:
            next_name = colony.next_stage
            if next_name:
                next_label = next_name.value.replace("_", " ").title()
                nh = self.font_head.render(
                    f"Next: {next_label}", True, CYAN,
                )
                surface.blit(nh, (x, y))
                y += 26

                r = self.fleet.resources
                for label, key, current in [
                    ("Metal", "metal", r.metal),
                    ("Energy", "energy", r.energy),
                    ("Colonists", "colonists", self.fleet.colonists),
                ]:
                    needed = cost[key]
                    has_enough = current >= needed
                    c = HULL_GREEN if has_enough else RED_ALERT
                    cs = self.font_body.render(
                        f"  {label}: {current:,} / {needed:,}", True, c,
                    )
                    surface.blit(cs, (x, y))
                    y += 22
        else:
            done = self.font_head.render(
                "★ Colony Established", True, HULL_GREEN,
            )
            surface.blit(done, (x, y))

    @staticmethod
    def _wrap(text: str, max_width: int, font: pygame.font.Font) -> list[str]:
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
