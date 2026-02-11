"""Combat screen — orbital interception visualization."""

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
from ..models.combat import (
    CombatEngine,
    CombatEvent,
    CombatPhase,
    CombatShip,
    EnemyFleet,
)
from ..models.ships import Fleet
from ..states import GameState


class CombatScreen:
    """Orbital combat visualization and control."""

    def __init__(self, combat_engine: CombatEngine) -> None:
        self.engine = combat_engine
        self.font_title = pygame.font.Font(None, 40)
        self.font_name = pygame.font.Font(None, 28)
        self.font_info = pygame.font.Font(None, 24)
        self.font_small = pygame.font.Font(None, 22)
        self.font_log = pygame.font.Font(None, 20)

        self.timer = 0.0
        self.auto_advance_timer = 0.0
        self.auto_advance_delay = 1.5  # Seconds between auto-turns during engagement
        self.next_state: GameState | None = None

        # Combat log display (last N events)
        self.visible_events: list[CombatEvent] = []
        self.max_visible_events = 12

        # Visual effects
        self._fire_effects: list[dict] = []  # Active weapon fire animations
        self._explosion_effects: list[dict] = []

        # Advance to start
        if self.engine.phase == CombatPhase.SETUP:
            events = self.engine.advance_turn()
            self._add_events(events)

    def handle_events(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE or event.key == pygame.K_RETURN:
                if self.engine.is_over:
                    self.engine.apply_results_to_fleet()
                    self.next_state = GameState.STAR_MAP
                else:
                    self._advance()
            elif event.key == pygame.K_ESCAPE:
                if self.engine.is_over:
                    self.engine.apply_results_to_fleet()
                    self.next_state = GameState.STAR_MAP

    def update(self, dt: float) -> None:
        self.timer += dt

        # Auto-advance during engagement
        if self.engine.phase == CombatPhase.ENGAGEMENT and not self.engine.is_over:
            self.auto_advance_timer += dt
            if self.auto_advance_timer >= self.auto_advance_delay:
                self._advance()

        # Update visual effects
        self._update_effects(dt)

    def draw(self, surface: pygame.Surface) -> None:
        # Phase header
        phase_text = self._phase_display_text()
        phase_color = AMBER if self.engine.phase == CombatPhase.ENGAGEMENT else LIGHT_GREY
        header = self.font_title.render(phase_text, True, phase_color)
        header_rect = header.get_rect(center=(SCREEN_WIDTH // 2, 30))
        surface.blit(header, header_rect)

        # Turn counter
        turn_text = f"Turn {self.engine.turn}"
        turn_surf = self.font_info.render(turn_text, True, LIGHT_GREY)
        surface.blit(turn_surf, (SCREEN_WIDTH - turn_surf.get_width() - 15, 15))

        # Orbital visualization (center area)
        self._draw_orbital_view(surface)

        # Player fleet panel (left)
        self._draw_fleet_panel(surface, self.engine.player_ships, "YOUR FLEET", 10, True)

        # Enemy fleet panel (right)
        self._draw_fleet_panel(surface, self.engine.enemy.ships, self.engine.enemy.name.upper(), SCREEN_WIDTH - 260, False)

        # Combat log (bottom)
        self._draw_combat_log(surface)

        # Visual effects
        self._draw_effects(surface)

        # Prompt
        if self.engine.is_over:
            result = "VICTORY!" if self.engine.player_won else "DEFEAT!"
            result_color = HULL_GREEN if self.engine.player_won else RED_ALERT
            result_surf = self.font_title.render(result, True, result_color)
            result_rect = result_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 40))
            surface.blit(result_surf, result_rect)

            if self.engine.player_won:
                loot = self.engine.enemy
                loot_text = f"Salvage: {loot.loot_metal} metal, {loot.loot_energy} energy, {loot.loot_rare} rare"
                loot_surf = self.font_name.render(loot_text, True, CYAN)
                loot_rect = loot_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
                surface.blit(loot_surf, loot_rect)

            prompt = self.font_info.render("Press ENTER to continue", True, LIGHT_GREY)
            blink = (math.sin(self.timer * 3) + 1) / 2
            prompt.set_alpha(int(blink * 255))
            prompt_rect = prompt.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 40))
            surface.blit(prompt_surf, prompt_rect) if False else surface.blit(prompt, prompt_rect)
        else:
            prompt = self.font_small.render("SPACE / ENTER — advance turn", True, LIGHT_GREY)
            surface.blit(prompt, (SCREEN_WIDTH // 2 - prompt.get_width() // 2, SCREEN_HEIGHT - 25))

    def _advance(self) -> None:
        """Advance one combat turn."""
        self.auto_advance_timer = 0.0
        events = self.engine.advance_turn()
        self._add_events(events)

        # Spawn visual effects for hits
        for event in events:
            if event.event_type == "hit":
                self._spawn_fire_effect()
            elif event.event_type == "destroyed":
                self._spawn_explosion_effect()

    def _add_events(self, events: list[CombatEvent]) -> None:
        self.visible_events.extend(events)
        if len(self.visible_events) > self.max_visible_events:
            self.visible_events = self.visible_events[-self.max_visible_events:]

    def _phase_display_text(self) -> str:
        phase_map = {
            CombatPhase.SETUP: "PREPARING FOR COMBAT",
            CombatPhase.APPROACH: f"APPROACHING — {int(self.engine.orbit_progress * 100)}%",
            CombatPhase.ENGAGEMENT: f"⚔ ENGAGEMENT — {self.engine.engagement_turns_remaining} turns remaining",
            CombatPhase.DISENGAGE: "DISENGAGING",
            CombatPhase.RESOLUTION: "COMBAT RESOLVED",
        }
        return phase_map.get(self.engine.phase, "COMBAT")

    # ------------------------------------------------------------------
    # Orbital view
    # ------------------------------------------------------------------

    def _draw_orbital_view(self, surface: pygame.Surface) -> None:
        """Draw the orbital interception visualization."""
        cx = SCREEN_WIDTH // 2
        cy = SCREEN_HEIGHT // 2 - 30

        # Orbit ellipses
        orbit_radius = 150
        pygame.draw.ellipse(
            surface, (40, 40, 55),
            (cx - orbit_radius, cy - orbit_radius // 2, orbit_radius * 2, orbit_radius),
            1,
        )

        # Player fleet dot (orbiting)
        player_angle = self.timer * 0.5
        px = cx + int(math.cos(player_angle) * orbit_radius)
        py = cy + int(math.sin(player_angle) * orbit_radius // 2)
        pygame.draw.circle(surface, CYAN, (px, py), 8)
        pygame.draw.circle(surface, WHITE, (px, py), 4)

        # Enemy fleet dot (counter-orbiting)
        engagement_offset = math.pi  # Opposite side
        if self.engine.phase == CombatPhase.ENGAGEMENT:
            engagement_offset = 0.1  # Very close during engagement
        elif self.engine.phase == CombatPhase.APPROACH:
            engagement_offset = math.pi * (1.0 - self.engine.orbit_progress)

        enemy_angle = player_angle + engagement_offset
        ex = cx + int(math.cos(enemy_angle) * orbit_radius)
        ey = cy + int(math.sin(enemy_angle) * orbit_radius // 2)
        pygame.draw.circle(surface, RED_ALERT, (ex, ey), 8)
        pygame.draw.circle(surface, WHITE, (ex, ey), 4)

        # Labels
        p_label = self.font_small.render("You", True, CYAN)
        surface.blit(p_label, (px - p_label.get_width() // 2, py - 20))
        e_label = self.font_small.render("Enemy", True, RED_ALERT)
        surface.blit(e_label, (ex - e_label.get_width() // 2, ey - 20))

        # Engagement distance indicator
        if self.engine.phase in (CombatPhase.APPROACH, CombatPhase.ENGAGEMENT):
            dist = math.hypot(px - ex, py - ey)
            dist_text = "IN RANGE!" if self.engine.phase == CombatPhase.ENGAGEMENT else f"Closing: {int(dist)}u"
            dist_color = AMBER if self.engine.phase == CombatPhase.ENGAGEMENT else LIGHT_GREY
            dist_surf = self.font_info.render(dist_text, True, dist_color)
            dist_rect = dist_surf.get_rect(center=(cx, cy + orbit_radius // 2 + 30))
            surface.blit(dist_surf, dist_rect)

    # ------------------------------------------------------------------
    # Fleet panels
    # ------------------------------------------------------------------

    def _draw_fleet_panel(
        self,
        surface: pygame.Surface,
        ships: list[CombatShip],
        title: str,
        x: int,
        is_player: bool,
    ) -> None:
        """Draw a fleet status panel."""
        panel_w = 250
        panel_h = min(400, 50 + len(ships) * 45)
        y = 60

        bg = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        bg.fill(PANEL_BG)
        surface.blit(bg, (x, y))
        pygame.draw.rect(surface, PANEL_BORDER, (x, y, panel_w, panel_h), 1, border_radius=4)

        # Title
        title_color = CYAN if is_player else RED_ALERT
        title_surf = self.font_info.render(title, True, title_color)
        surface.blit(title_surf, (x + 8, y + 6))

        # Ships
        for i, ship in enumerate(ships[:8]):
            sy = y + 30 + i * 45
            self._draw_ship_status(surface, ship, x + 8, sy, panel_w - 16, is_player)

    def _draw_ship_status(
        self,
        surface: pygame.Surface,
        ship: CombatShip,
        x: int,
        y: int,
        w: int,
        is_player: bool,
    ) -> None:
        """Draw a single ship's status in the fleet panel."""
        name_color = LIGHT_GREY if ship.is_alive else (80, 80, 80)

        # Name (truncated)
        display_name = ship.name[:20]
        name_surf = self.font_small.render(display_name, True, name_color)
        surface.blit(name_surf, (x, y))

        if ship.is_alive:
            # Hull bar
            bar_y = y + 18
            bar_w = w
            bar_h = 6
            hull_pct = ship.hull / ship.max_hull

            # Background
            pygame.draw.rect(surface, (40, 40, 50), (x, bar_y, bar_w, bar_h))
            # Fill
            fill_color = HULL_GREEN if hull_pct > 0.5 else AMBER if hull_pct > 0.25 else RED_ALERT
            pygame.draw.rect(surface, fill_color, (x, bar_y, int(bar_w * hull_pct), bar_h))

            # Hull text
            hull_text = f"{ship.hull}/{ship.max_hull}"
            hull_surf = self.font_log.render(hull_text, True, LIGHT_GREY)
            surface.blit(hull_surf, (x + bar_w - hull_surf.get_width(), bar_y + 8))
        else:
            destroyed_surf = self.font_small.render("DESTROYED", True, RED_ALERT)
            surface.blit(destroyed_surf, (x, y + 18))

    # ------------------------------------------------------------------
    # Combat log
    # ------------------------------------------------------------------

    def _draw_combat_log(self, surface: pygame.Surface) -> None:
        """Draw the scrolling combat log at the bottom."""
        log_h = 160
        log_y = SCREEN_HEIGHT - log_h - 30
        log_x = 270
        log_w = SCREEN_WIDTH - 540

        bg = pygame.Surface((log_w, log_h), pygame.SRCALPHA)
        bg.fill((10, 10, 20, 200))
        surface.blit(bg, (log_x, log_y))
        pygame.draw.rect(surface, PANEL_BORDER, (log_x, log_y, log_w, log_h), 1, border_radius=4)

        # Header
        header = self.font_info.render("COMBAT LOG", True, AMBER)
        surface.blit(header, (log_x + 8, log_y + 4))

        # Events
        event_y = log_y + 26
        for event in self.visible_events[-8:]:
            color_map = {
                "hit": HULL_GREEN,
                "miss": LIGHT_GREY,
                "pd_intercept": SHIELD_BLUE,
                "destroyed": RED_ALERT,
                "info": AMBER,
            }
            color = color_map.get(event.event_type, LIGHT_GREY)

            # Truncate long messages
            msg = event.message[:70]
            msg_surf = self.font_log.render(f"[T{event.turn}] {msg}", True, color)
            surface.blit(msg_surf, (log_x + 8, event_y))
            event_y += 16

    # ------------------------------------------------------------------
    # Visual effects
    # ------------------------------------------------------------------

    def _spawn_fire_effect(self) -> None:
        """Add a weapon fire line effect."""
        import random
        self._fire_effects.append({
            "x1": random.randint(200, 400),
            "y1": random.randint(150, 450),
            "x2": random.randint(SCREEN_WIDTH - 400, SCREEN_WIDTH - 200),
            "y2": random.randint(150, 450),
            "life": 0.5,
            "max_life": 0.5,
        })

    def _spawn_explosion_effect(self) -> None:
        """Add an explosion effect."""
        import random
        self._explosion_effects.append({
            "x": random.randint(SCREEN_WIDTH - 400, SCREEN_WIDTH - 200),
            "y": random.randint(150, 450),
            "radius": 0,
            "max_radius": 30,
            "life": 0.8,
            "max_life": 0.8,
        })

    def _update_effects(self, dt: float) -> None:
        for effect in self._fire_effects:
            effect["life"] -= dt
        self._fire_effects = [e for e in self._fire_effects if e["life"] > 0]

        for effect in self._explosion_effects:
            effect["life"] -= dt
            effect["radius"] = int(effect["max_radius"] * (1 - effect["life"] / effect["max_life"]))
        self._explosion_effects = [e for e in self._explosion_effects if e["life"] > 0]

    def _draw_effects(self, surface: pygame.Surface) -> None:
        for effect in self._fire_effects:
            alpha = int((effect["life"] / effect["max_life"]) * 255)
            line_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            pygame.draw.line(
                line_surf,
                (*CYAN, alpha),
                (effect["x1"], effect["y1"]),
                (effect["x2"], effect["y2"]),
                2,
            )
            surface.blit(line_surf, (0, 0))

        for effect in self._explosion_effects:
            alpha = int((effect["life"] / effect["max_life"]) * 200)
            if effect["radius"] > 0:
                exp_surf = pygame.Surface((effect["radius"] * 2 + 4, effect["radius"] * 2 + 4), pygame.SRCALPHA)
                center = effect["radius"] + 2
                pygame.draw.circle(exp_surf, (*AMBER, alpha), (center, center), effect["radius"])
                pygame.draw.circle(exp_surf, (*RED_ALERT, alpha // 2), (center, center), effect["radius"] + 2, 2)
                surface.blit(exp_surf, (effect["x"] - center, effect["y"] - center))
