"""Combat screen — orbital interception visualization.

Redesigned for intuitive player interaction:
- Player selects targets with A/D
- Player fires each turn with SPACE/ENTER
- Ship silhouettes instead of dots
- Floating damage numbers
- Phase guide text explaining what's happening
- Engagement countdown bar
- Retreat option during approach (R key)
"""

from __future__ import annotations

import math
import random as py_random

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
)
from ..states import GameState


# ---------------------------------------------------------------------------
# Floating damage numbers
# ---------------------------------------------------------------------------

class DamageFloat:
    """A floating damage/miss number that drifts upward and fades."""

    def __init__(self, text: str, x: int, y: int, color: tuple) -> None:
        self.text = text
        self.x = x + py_random.randint(-20, 20)
        self.y = float(y)
        self.color = color
        self.life = 1.5
        self.max_life = 1.5
        self.font = pygame.font.Font(None, 26)

    def update(self, dt: float) -> bool:
        """Returns False when expired."""
        self.life -= dt
        self.y -= 40 * dt  # Drift up
        return self.life > 0

    def draw(self, surface: pygame.Surface) -> None:
        alpha = int(min(255, (self.life / self.max_life) * 255))
        text_surf = self.font.render(self.text, True, self.color)
        text_surf.set_alpha(alpha)
        surface.blit(text_surf, (self.x, int(self.y)))


# ---------------------------------------------------------------------------
# Ship silhouette rendering
# ---------------------------------------------------------------------------

def _draw_ship_silhouette(
    surface: pygame.Surface,
    x: int, y: int,
    ship_class_name: str,
    color: tuple,
    scale: float = 1.0,
    facing_left: bool = False,
) -> None:
    """Draw a simple geometric ship shape based on class."""
    s = scale
    pts: list[tuple[float, float]]

    if ship_class_name in ("battleship", "heavy_cruiser"):
        # Big wedge shape
        pts = [(0, -12*s), (30*s, 0), (0, 12*s), (-5*s, 8*s), (-5*s, -8*s)]
    elif ship_class_name in ("cruiser", "destroyer"):
        # Medium angular
        pts = [(0, -8*s), (22*s, 0), (0, 8*s), (-4*s, 5*s), (-4*s, -5*s)]
    elif ship_class_name in ("frigate", "corvette"):
        # Small arrow
        pts = [(0, -5*s), (16*s, 0), (0, 5*s), (-3*s, 3*s), (-3*s, -3*s)]
    else:
        # Tiny triangle (drone/fighter)
        pts = [(0, -4*s), (12*s, 0), (0, 4*s)]

    if facing_left:
        pts = [(-px, py) for px, py in pts]

    final = [(x + px, y + py) for px, py in pts]
    pygame.draw.polygon(surface, color, final)
    pygame.draw.polygon(surface, WHITE, final, 1)


# ---------------------------------------------------------------------------
# Main combat screen
# ---------------------------------------------------------------------------

class CombatScreen:
    """Orbital combat visualization and control — player-driven engagement."""

    def __init__(self, combat_engine: CombatEngine) -> None:
        self.engine = combat_engine
        self.font_title = pygame.font.Font(None, 42)
        self.font_phase = pygame.font.Font(None, 32)
        self.font_name = pygame.font.Font(None, 28)
        self.font_info = pygame.font.Font(None, 24)
        self.font_small = pygame.font.Font(None, 22)
        self.font_log = pygame.font.Font(None, 20)
        self.font_hint = pygame.font.Font(None, 24)

        self.timer = 0.0
        self.next_state: GameState | None = None

        # Player targeting (selectable enemy)
        self.selected_target_idx = 0

        # Combat log
        self.visible_events: list[CombatEvent] = []
        self.max_visible_events = 10

        # Floating damage numbers
        self.damage_floats: list[DamageFloat] = []

        # Visual effects
        self._fire_effects: list[dict] = []
        self._explosion_effects: list[dict] = []
        self._screen_shake = 0.0

        # Phase text guide
        self._phase_guide = ""
        self._phase_guide_timer = 0.0

        # Laser PD mode toggle (per PLAN.md)
        self.laser_pd_active = False

        # Setup phase: auto-advance to approach
        if self.engine.phase == CombatPhase.SETUP:
            events = self.engine.advance_turn()
            self._add_events(events)
            self._set_phase_guide("Your fleet is matching the enemy's orbit. Press SPACE to close distance.")

    def handle_events(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return

        key = event.key

        # Combat is over — any confirm key exits
        if self.engine.is_over:
            if key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE):
                self.engine.apply_results_to_fleet()
                self.next_state = GameState.STAR_MAP
            return

        # Target selection
        if key in (pygame.K_a, pygame.K_LEFT):
            self._cycle_target(-1)
        elif key in (pygame.K_d, pygame.K_RIGHT):
            self._cycle_target(1)

        # Main action: advance turn / fire
        elif key in (pygame.K_SPACE, pygame.K_RETURN):
            self._player_advance()

        # Retreat during approach
        elif key == pygame.K_r:
            if self.engine.phase == CombatPhase.APPROACH:
                # Retreat: take some damage and leave
                self._retreat()

        # Laser PD mode toggle
        elif key == pygame.K_p:
            self._toggle_laser_pd()

    def update(self, dt: float) -> None:
        self.timer += dt

        # Phase guide timer
        if self._phase_guide_timer > 0:
            self._phase_guide_timer -= dt

        # Floating damage numbers
        self.damage_floats = [d for d in self.damage_floats if d.update(dt)]

        # Screen shake
        if self._screen_shake > 0:
            self._screen_shake -= dt * 4

        # Visual effects
        self._update_effects(dt)

    def draw(self, surface: pygame.Surface) -> None:
        # Screen shake offset
        shake_x = int(py_random.uniform(-self._screen_shake, self._screen_shake) * 5) if self._screen_shake > 0 else 0
        shake_y = int(py_random.uniform(-self._screen_shake, self._screen_shake) * 5) if self._screen_shake > 0 else 0

        # Phase header with status bar
        self._draw_phase_header(surface)

        # Tactical view (center — the main battlefield)
        self._draw_tactical_view(surface, shake_x, shake_y)

        # Player fleet panel (left)
        self._draw_player_panel(surface)

        # Enemy fleet panel (right) — with target selector
        self._draw_enemy_panel(surface)

        # Combat log (bottom center)
        self._draw_combat_log(surface)

        # Draw floating damage numbers (over everything)
        for df in self.damage_floats:
            df.draw(surface)

        # Draw visual effects
        self._draw_effects(surface)

        # Phase guide / tutorial text
        self._draw_phase_guide(surface)

        # Victory/Defeat overlay
        if self.engine.is_over:
            self._draw_result_overlay(surface)
        else:
            self._draw_action_hints(surface)

    # ------------------------------------------------------------------
    # Player actions
    # ------------------------------------------------------------------

    def _player_advance(self) -> None:
        """Player presses SPACE/ENTER — advance based on phase."""
        events = self.engine.advance_turn()
        self._add_events(events)

        # Spawn visuals for events
        for event in events:
            if event.event_type == "hit":
                self._spawn_fire_effect(is_player=True)
                self._spawn_damage_float(event.message, True)
                self._screen_shake = max(self._screen_shake, 0.3)
            elif event.event_type == "miss":
                self._spawn_damage_float(event.message, False)
            elif event.event_type == "pd_intercept":
                self._spawn_damage_float("INTERCEPTED", False)
            elif event.event_type == "destroyed":
                self._spawn_explosion_effect(is_player=False)
                self._screen_shake = max(self._screen_shake, 0.8)

        # Update phase guide
        if self.engine.phase == CombatPhase.APPROACH:
            pct = int(self.engine.orbit_progress * 100)
            self._set_phase_guide(f"Closing distance ({pct}%). Press SPACE to continue. R to retreat.")
        elif self.engine.phase == CombatPhase.ENGAGEMENT:
            turns = self.engine.engagement_turns_remaining
            self._set_phase_guide(f"FIRING WINDOW: {turns} turns left! Use A/D to select target, SPACE to fire!")
        elif self.engine.phase == CombatPhase.DISENGAGE:
            self._set_phase_guide("Orbits diverging. Press SPACE to re-approach for another pass.")
        elif self.engine.phase == CombatPhase.RESOLUTION:
            self._set_phase_guide("")

    def _retreat(self) -> None:
        """Retreat during approach — take glancing damage, return to star map."""
        # Apply some hull damage for fleeing
        if self.engine.player_ships:
            ms = self.engine.player_ships[0]
            damage = max(50, ms.max_hull // 10)
            ms.take_damage(damage)
            self.engine.player_fleet.mothership.hull = ms.hull

        self.engine.phase = CombatPhase.RESOLUTION
        self._add_events([CombatEvent(
            self.engine.turn,
            "Emergency retreat! Your fleet takes fire while disengaging.",
            "info",
        )])
        self._set_phase_guide("Retreated. Press ENTER to continue.")

    def _cycle_target(self, direction: int) -> None:
        """Cycle through alive enemy ships."""
        alive = self.engine.enemy.alive_ships
        if not alive:
            return
        self.selected_target_idx = (self.selected_target_idx + direction) % len(alive)

    def _set_phase_guide(self, text: str) -> None:
        self._phase_guide = text
        self._phase_guide_timer = 6.0

    def _toggle_laser_pd(self) -> None:
        """Toggle laser weapons into/out of point-defense mode.

        When active, lasers with pd_mode_available stop firing offensively
        and instead provide PD charges each turn.
        """
        self.laser_pd_active = not self.laser_pd_active

        # Update can_target_missiles on all player laser weapons
        count = 0
        for ship in self.engine.player_ships:
            if not ship.is_alive:
                continue
            for wpn in ship.weapons:
                if wpn.pd_mode_available:
                    wpn.can_target_missiles = self.laser_pd_active
                    count += 1

        if self.laser_pd_active:
            self._set_phase_guide(f"LASER PD MODE ON — {count} laser(s) now intercepting missiles!")
        else:
            self._set_phase_guide(f"LASER PD MODE OFF — {count} laser(s) firing offensively.")

    # ------------------------------------------------------------------
    # Phase header
    # ------------------------------------------------------------------

    def _draw_phase_header(self, surface: pygame.Surface) -> None:
        """Draw phase name, turn counter, and engagement progress bar."""
        # Phase name
        phase_names = {
            CombatPhase.SETUP: "PREPARING...",
            CombatPhase.APPROACH: "APPROACHING",
            CombatPhase.ENGAGEMENT: "⚔ ENGAGEMENT",
            CombatPhase.DISENGAGE: "DISENGAGING",
            CombatPhase.RESOLUTION: "RESOLVED",
        }
        phase_text = phase_names.get(self.engine.phase, "COMBAT")
        is_engagement = self.engine.phase == CombatPhase.ENGAGEMENT
        phase_color = RED_ALERT if is_engagement else AMBER

        header = self.font_title.render(phase_text, True, phase_color)
        header_rect = header.get_rect(center=(SCREEN_WIDTH // 2, 28))
        surface.blit(header, header_rect)

        # Turn counter
        turn_surf = self.font_info.render(f"Turn {self.engine.turn}", True, LIGHT_GREY)
        surface.blit(turn_surf, (SCREEN_WIDTH - turn_surf.get_width() - 15, 10))

        # Progress bar
        bar_w = 300
        bar_h = 10
        bar_x = (SCREEN_WIDTH - bar_w) // 2
        bar_y = 50

        pygame.draw.rect(surface, (30, 30, 45), (bar_x, bar_y, bar_w, bar_h), border_radius=5)

        if self.engine.phase == CombatPhase.APPROACH:
            fill = self.engine.orbit_progress
            fill_color = AMBER
            label = f"Closing: {int(fill * 100)}%"
        elif self.engine.phase == CombatPhase.ENGAGEMENT:
            fill = self.engine.engagement_turns_remaining / self.engine.max_engagement_turns
            fill_color = RED_ALERT
            label = f"Window: {self.engine.engagement_turns_remaining}/{self.engine.max_engagement_turns} turns"
        elif self.engine.phase == CombatPhase.DISENGAGE:
            fill = self.engine.orbit_progress
            fill_color = LIGHT_GREY
            label = "Diverging..."
        else:
            fill = 0
            label = ""

        if fill > 0:
            pygame.draw.rect(surface, fill_color, (bar_x, bar_y, int(bar_w * fill), bar_h), border_radius=5)

        if label:
            label_surf = self.font_small.render(label, True, WHITE)
            label_rect = label_surf.get_rect(center=(SCREEN_WIDTH // 2, bar_y + bar_h + 14))
            surface.blit(label_surf, label_rect)

    # ------------------------------------------------------------------
    # Tactical view (center battlefield)
    # ------------------------------------------------------------------

    def _draw_tactical_view(self, surface: pygame.Surface, sx: int, sy: int) -> None:
        """Draw the main battlefield with ship silhouettes."""
        # Battle area bounds
        area_x = 265
        area_y = 80
        area_w = SCREEN_WIDTH - 530
        area_h = 280

        # Subtle grid background
        for gx in range(area_x, area_x + area_w, 40):
            pygame.draw.line(surface, (25, 25, 35), (gx + sx, area_y + sy), (gx + sx, area_y + area_h + sy))
        for gy in range(area_y, area_y + area_h, 40):
            pygame.draw.line(surface, (25, 25, 35), (area_x + sx, gy + sy), (area_x + area_w + sx, gy + sy))

        # Border
        pygame.draw.rect(surface, PANEL_BORDER, (area_x, area_y, area_w, area_h), 1, border_radius=4)

        # Orbit track (curved line)
        track_cx = area_x + area_w // 2
        track_cy = area_y + area_h // 2
        track_rx = area_w // 2 - 30
        track_ry = area_h // 2 - 30
        pygame.draw.ellipse(
            surface, (35, 35, 50),
            (track_cx - track_rx, track_cy - track_ry, track_rx * 2, track_ry * 2),
            1,
        )

        # Player fleet ships (left side, stacked vertically)
        alive_player = [s for s in self.engine.player_ships if s.is_alive]
        player_base_x = area_x + 60 + sx
        for i, ship in enumerate(alive_player[:6]):
            py_pos = area_y + 40 + i * 40 + sy
            class_name = ship.ship_class.value
            _draw_ship_silhouette(surface, player_base_x, py_pos, class_name, CYAN, scale=1.2)

            # Name label
            label = self.font_log.render(ship.name[:14], True, CYAN)
            surface.blit(label, (player_base_x + 25, py_pos - 8))

        # Enemy fleet ships (right side)
        alive_enemy = self.engine.enemy.alive_ships
        enemy_base_x = area_x + area_w - 60 + sx
        for i, ship in enumerate(alive_enemy[:6]):
            ey_pos = area_y + 40 + i * 40 + sy
            class_name = ship.ship_class.value
            is_selected = i == self.selected_target_idx
            color = WHITE if is_selected else RED_ALERT
            _draw_ship_silhouette(surface, enemy_base_x, ey_pos, class_name, color, scale=1.2, facing_left=True)

            # Name + highlight for selected
            label_color = WHITE if is_selected else RED_ALERT
            label = self.font_log.render(ship.name[:14], True, label_color)
            surface.blit(label, (enemy_base_x - label.get_width() - 25, ey_pos - 8))

            if is_selected and self.engine.phase == CombatPhase.ENGAGEMENT:
                # Target reticle
                pulse = abs(math.sin(self.timer * 4))
                reticle_size = int(16 + pulse * 4)
                pygame.draw.circle(surface, WHITE, (enemy_base_x, ey_pos), reticle_size, 2)
                pygame.draw.line(surface, WHITE, (enemy_base_x - reticle_size - 3, ey_pos), (enemy_base_x + reticle_size + 3, ey_pos), 1)
                pygame.draw.line(surface, WHITE, (enemy_base_x, ey_pos - reticle_size - 3), (enemy_base_x, ey_pos + reticle_size + 3), 1)

        # Engagement lines (weapon fire traces during engagement)
        if self.engine.phase == CombatPhase.ENGAGEMENT and alive_player and alive_enemy:
            # Subtle targeting lines from player ships to selected target
            if self.selected_target_idx < len(alive_enemy):
                tx = enemy_base_x
                ty = area_y + 40 + self.selected_target_idx * 40 + sy
                for i, ship in enumerate(alive_player[:4]):
                    px = player_base_x + 20
                    py_pos = area_y + 40 + i * 40 + sy
                    line_alpha = int(60 + 30 * abs(math.sin(self.timer * 2 + i)))
                    line_surf = pygame.Surface((area_w, area_h), pygame.SRCALPHA)
                    pygame.draw.line(line_surf, (*CYAN, line_alpha), (px - area_x, py_pos - area_y), (tx - area_x, ty - area_y), 1)
                    surface.blit(line_surf, (area_x, area_y))

        # Central label
        if self.engine.phase == CombatPhase.APPROACH:
            approach_text = f"CLOSING: {int(self.engine.orbit_progress * 100)}%"
            center_surf = self.font_phase.render(approach_text, True, AMBER)
            center_rect = center_surf.get_rect(center=(track_cx, track_cy))
            surface.blit(center_surf, center_rect)
        elif self.engine.phase == CombatPhase.ENGAGEMENT:
            # Flashing "FIRE!" text
            blink = abs(math.sin(self.timer * 5))
            if blink > 0.3:
                fire_color = (int(255 * blink), int(80 * blink), 0)
                fire_surf = self.font_title.render("FIRE!", True, fire_color)
                fire_rect = fire_surf.get_rect(center=(track_cx, track_cy))
                surface.blit(fire_surf, fire_rect)

    # ------------------------------------------------------------------
    # Fleet panels
    # ------------------------------------------------------------------

    def _draw_player_panel(self, surface: pygame.Surface) -> None:
        """Left panel — your fleet status."""
        x, y, w = 5, 80, 255
        ships = self.engine.player_ships
        h = min(320, 38 + len(ships) * 38)

        bg = pygame.Surface((w, h), pygame.SRCALPHA)
        bg.fill((*PANEL_BG[:3], 220))
        surface.blit(bg, (x, y))
        pygame.draw.rect(surface, CYAN, (x, y, w, h), 1, border_radius=4)

        title = self.font_info.render("YOUR FLEET", True, CYAN)
        surface.blit(title, (x + 8, y + 6))

        for i, ship in enumerate(ships[:7]):
            sy = y + 30 + i * 38
            self._draw_ship_bar(surface, ship, x + 8, sy, w - 16, True)

    def _draw_enemy_panel(self, surface: pygame.Surface) -> None:
        """Right panel — enemy fleet with target selector."""
        x, w = SCREEN_WIDTH - 260, 255
        y = 80
        ships = self.engine.enemy.ships
        h = min(320, 38 + len(ships) * 38)

        bg = pygame.Surface((w, h), pygame.SRCALPHA)
        bg.fill((*PANEL_BG[:3], 220))
        surface.blit(bg, (x, y))
        pygame.draw.rect(surface, RED_ALERT, (x, y, w, h), 1, border_radius=4)

        title = self.font_info.render(self.engine.enemy.name.upper()[:25], True, RED_ALERT)
        surface.blit(title, (x + 8, y + 6))

        alive_ships = self.engine.enemy.alive_ships
        for i, ship in enumerate(ships[:7]):
            sy = y + 30 + i * 38
            is_target = ship.is_alive and ship in alive_ships and alive_ships.index(ship) == self.selected_target_idx
            self._draw_ship_bar(surface, ship, x + 8, sy, w - 16, False, is_target)

    def _draw_ship_bar(
        self, surface: pygame.Surface, ship: CombatShip,
        x: int, y: int, w: int, is_player: bool, is_target: bool = False,
    ) -> None:
        """Draw a compact ship status bar."""
        if not ship.is_alive:
            # Destroyed — dimmed with strikethrough
            name_surf = self.font_small.render(f"✕ {ship.name[:18]}", True, (80, 50, 50))
            surface.blit(name_surf, (x, y))
            return

        # Name with target indicator
        prefix = "▸ " if is_target else "  "
        name_color = WHITE if is_target else LIGHT_GREY
        name_surf = self.font_small.render(f"{prefix}{ship.name[:18]}", True, name_color)
        surface.blit(name_surf, (x, y))

        # Hull bar
        bar_y = y + 18
        bar_w = w
        bar_h = 8
        hull_pct = ship.hull / ship.max_hull

        pygame.draw.rect(surface, (30, 30, 45), (x, bar_y, bar_w, bar_h), border_radius=3)
        fill_color = HULL_GREEN if hull_pct > 0.5 else AMBER if hull_pct > 0.25 else RED_ALERT
        fill_w = max(1, int(bar_w * hull_pct))
        pygame.draw.rect(surface, fill_color, (x, bar_y, fill_w, bar_h), border_radius=3)

        # Hull numbers
        hp_text = f"{ship.hull}/{ship.max_hull}"
        hp_surf = self.font_log.render(hp_text, True, fill_color)
        surface.blit(hp_surf, (x + bar_w - hp_surf.get_width(), bar_y + 10))

        # Weapon count on player ships
        if is_player:
            wpn_count = len(ship.weapons)
            wpn_text = f"{wpn_count} wpn"
            wpn_surf = self.font_log.render(wpn_text, True, AMBER)
            surface.blit(wpn_surf, (x, bar_y + 10))

    # ------------------------------------------------------------------
    # Combat log
    # ------------------------------------------------------------------

    def _draw_combat_log(self, surface: pygame.Surface) -> None:
        """Bottom-center scrolling combat log."""
        log_x = 265
        log_y = SCREEN_HEIGHT - 175
        log_w = SCREEN_WIDTH - 530
        log_h = 130

        bg = pygame.Surface((log_w, log_h), pygame.SRCALPHA)
        bg.fill((8, 8, 18, 220))
        surface.blit(bg, (log_x, log_y))
        pygame.draw.rect(surface, PANEL_BORDER, (log_x, log_y, log_w, log_h), 1, border_radius=4)

        # Header
        log_header = self.font_info.render("COMBAT LOG", True, AMBER)
        surface.blit(log_header, (log_x + 8, log_y + 4))

        # Events
        event_y = log_y + 24
        for event in self.visible_events[-7:]:
            color_map = {
                "hit": HULL_GREEN,
                "miss": (100, 100, 100),
                "pd_intercept": SHIELD_BLUE,
                "destroyed": RED_ALERT,
                "info": AMBER,
            }
            color = color_map.get(event.event_type, LIGHT_GREY)
            icon_map = {"hit": "💥", "miss": "·", "pd_intercept": "🛡", "destroyed": "💀", "info": "ℹ"}
            icon = icon_map.get(event.event_type, "·")

            msg = event.message[:65]
            msg_surf = self.font_log.render(f" {icon} T{event.turn}: {msg}", True, color)
            surface.blit(msg_surf, (log_x + 4, event_y))
            event_y += 15

    # ------------------------------------------------------------------
    # Phase guide / tutorial text
    # ------------------------------------------------------------------

    def _draw_phase_guide(self, surface: pygame.Surface) -> None:
        """Draw contextual help text above the combat log."""
        if not self._phase_guide or self._phase_guide_timer <= 0:
            return

        guide_y = SCREEN_HEIGHT - 195
        alpha = int(min(255, self._phase_guide_timer * 200))

        guide_surf = self.font_hint.render(self._phase_guide, True, AMBER)
        guide_surf.set_alpha(alpha)
        guide_rect = guide_surf.get_rect(center=(SCREEN_WIDTH // 2, guide_y))
        surface.blit(guide_surf, guide_rect)

    # ------------------------------------------------------------------
    # Action hints (bottom bar)
    # ------------------------------------------------------------------

    def _draw_action_hints(self, surface: pygame.Surface) -> None:
        """Draw keybind hints at the very bottom."""
        hints: list[str] = []
        if self.engine.phase == CombatPhase.APPROACH:
            hints = ["SPACE — Close distance", "R — Retreat", "P — Laser PD"]
        elif self.engine.phase == CombatPhase.ENGAGEMENT:
            pd_status = "ON" if self.laser_pd_active else "OFF"
            hints = ["A/D — Select target", "SPACE — Fire all weapons", f"P — Laser PD [{pd_status}]"]
        elif self.engine.phase == CombatPhase.DISENGAGE:
            hints = ["SPACE — Re-approach", "P — Laser PD"]

        if hints:
            hint_text = "  |  ".join(hints)
            hint_surf = self.font_small.render(hint_text, True, LIGHT_GREY)
            hint_rect = hint_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 12))
            surface.blit(hint_surf, hint_rect)

    # ------------------------------------------------------------------
    # Result overlay (victory / defeat)
    # ------------------------------------------------------------------

    def _draw_result_overlay(self, surface: pygame.Surface) -> None:
        """Draw victory or defeat overlay."""
        # Semi-transparent backdrop
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        surface.blit(overlay, (0, 0))

        is_retreat = not self.engine.player_won and not self.engine.enemy.is_defeated and any(s.is_alive for s in self.engine.player_ships)
        
        if is_retreat:
            title = "RETREATED"
            title_color = AMBER
        elif self.engine.player_won:
            title = "VICTORY!"
            title_color = HULL_GREEN
        else:
            title = "DEFEAT!"
            title_color = RED_ALERT

        title_surf = self.font_title.render(title, True, title_color)
        title_rect = title_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50))
        surface.blit(title_surf, title_rect)

        # Loot display (if won)
        if self.engine.player_won:
            loot = self.engine.enemy
            loot_lines = [
                (f"+{loot.loot_metal} Metal", HULL_GREEN),
                (f"+{loot.loot_energy} Energy", CYAN),
                (f"+{loot.loot_rare} Rare Materials", AMBER),
            ]
            for i, (text, color) in enumerate(loot_lines):
                loot_surf = self.font_name.render(text, True, color)
                loot_rect = loot_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 10 + i * 28))
                surface.blit(loot_surf, loot_rect)
        elif is_retreat:
            retreat_msg = self.font_info.render("You escaped, but took hull damage.", True, LIGHT_GREY)
            retreat_rect = retreat_msg.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 10))
            surface.blit(retreat_msg, retreat_rect)

        # Continue prompt
        blink = (math.sin(self.timer * 3) + 1) / 2
        prompt = self.font_info.render("Press ENTER to continue", True, LIGHT_GREY)
        prompt.set_alpha(int(blink * 255))
        prompt_rect = prompt.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 70))
        surface.blit(prompt, prompt_rect)

    # ------------------------------------------------------------------
    # Floating damage & effects
    # ------------------------------------------------------------------

    def _spawn_damage_float(self, message: str, is_hit: bool) -> None:
        """Create a floating text from a combat event."""
        import re

        # Extract damage number from message like "...for 45 damage!"
        match = re.search(r'for (\d+) damage', message)
        if match:
            text = f"-{match.group(1)}"
            color = RED_ALERT
        elif "miss" in message.lower():
            text = "MISS"
            color = (100, 100, 120)
        elif "INTERCEPT" in message.upper():
            text = "BLOCKED"
            color = SHIELD_BLUE
        elif "DESTROYED" in message.upper():
            text = "DESTROYED!"
            color = RED_ALERT
        else:
            return

        # Position: enemy side for player hits, player side for enemy hits
        x = SCREEN_WIDTH - 300 + py_random.randint(-40, 40)
        y = 130 + py_random.randint(0, 200)
        self.damage_floats.append(DamageFloat(text, x, y, color))

    def _spawn_fire_effect(self, is_player: bool = True) -> None:
        """Add a weapon fire line effect."""
        start_x = 320 if is_player else SCREEN_WIDTH - 320
        end_x = SCREEN_WIDTH - 320 if is_player else 320
        y_jitter = py_random.randint(-60, 60)
        self._fire_effects.append({
            "x1": start_x,
            "y1": 220 + y_jitter,
            "x2": end_x,
            "y2": 220 + py_random.randint(-60, 60),
            "life": 0.4,
            "max_life": 0.4,
            "color": CYAN if is_player else RED_ALERT,
        })

    def _spawn_explosion_effect(self, is_player: bool = False) -> None:
        """Add an explosion burst effect."""
        x = 340 if is_player else SCREEN_WIDTH - 340
        y = 220 + py_random.randint(-60, 60)
        self._explosion_effects.append({
            "x": x, "y": y,
            "radius": 0, "max_radius": 35,
            "life": 0.9, "max_life": 0.9,
        })

    def _update_effects(self, dt: float) -> None:
        for e in self._fire_effects:
            e["life"] -= dt
        self._fire_effects = [e for e in self._fire_effects if e["life"] > 0]

        for e in self._explosion_effects:
            e["life"] -= dt
            e["radius"] = int(e["max_radius"] * (1 - e["life"] / e["max_life"]))
        self._explosion_effects = [e for e in self._explosion_effects if e["life"] > 0]

    def _draw_effects(self, surface: pygame.Surface) -> None:
        for e in self._fire_effects:
            alpha = int((e["life"] / e["max_life"]) * 200)
            line_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            c = e.get("color", CYAN)
            pygame.draw.line(line_surf, (*c, alpha), (e["x1"], e["y1"]), (e["x2"], e["y2"]), 2)
            # Glow
            pygame.draw.line(line_surf, (*c, alpha // 3), (e["x1"], e["y1"]), (e["x2"], e["y2"]), 6)
            surface.blit(line_surf, (0, 0))

        for e in self._explosion_effects:
            if e["radius"] > 0:
                alpha = int((e["life"] / e["max_life"]) * 200)
                exp_surf = pygame.Surface((e["radius"] * 2 + 10, e["radius"] * 2 + 10), pygame.SRCALPHA)
                center = e["radius"] + 5
                pygame.draw.circle(exp_surf, (*AMBER, alpha), (center, center), e["radius"])
                pygame.draw.circle(exp_surf, (*RED_ALERT, alpha // 2), (center, center), e["radius"] + 3, 2)
                pygame.draw.circle(exp_surf, (*WHITE, alpha // 3), (center, center), e["radius"] // 2)
                surface.blit(exp_surf, (e["x"] - center, e["y"] - center))

    def _add_events(self, events: list[CombatEvent]) -> None:
        self.visible_events.extend(events)
        if len(self.visible_events) > self.max_visible_events:
            self.visible_events = self.visible_events[-self.max_visible_events:]
