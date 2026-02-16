"""Star map screen — navigate between star systems via FTL."""

from __future__ import annotations

import math

import pygame

from ..constants import (
    AMBER,
    BLACK,
    CYAN,
    DARK_GREY,
    LIGHT_GREY,
    PANEL_BG,
    PANEL_BORDER,
    RED_ALERT,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    STAR_COLORS,
    WHITE,
)
from ..models.galaxy import Galaxy, StarSystem
from ..states import GameState


class StarMapScreen:
    """Galactic star map with pan/zoom and clickable systems."""

    def __init__(self, galaxy: Galaxy) -> None:
        self.galaxy = galaxy
        self.font_name = pygame.font.Font(None, 28)
        self.font_info = pygame.font.Font(None, 24)
        self.font_title = pygame.font.Font(None, 40)

        # Camera
        self.cam_x = 0.0
        self.cam_y = 0.0
        self.zoom = 1.0
        self.min_zoom = 0.3
        self.max_zoom = 3.0

        # Center camera on starting system
        start = self.galaxy.current_system
        self.cam_x = -start.x
        self.cam_y = -start.y

        # Interaction
        self.hovered_system: StarSystem | None = None
        self.next_state: GameState | None = None
        self.selected_system_id: int | None = None

        # Pan state
        self._pan_speed = 400.0
        self._keys_held: set[int] = set()

        # FTL travel animation
        self._travelling = False
        self._travel_progress = 0.0
        self._travel_target_id: int | None = None
        self._travel_start_pos: tuple[float, float] = (0, 0)
        self._travel_end_pos: tuple[float, float] = (0, 0)

        # FTL confirmation prompt (PLAN.md: cryosleep warning before jump)
        self._ftl_confirm = False
        self._ftl_confirm_font = pygame.font.Font(None, 32)
        self._ftl_confirm_body = pygame.font.Font(None, 24)

    def handle_events(self, event: pygame.event.Event) -> None:
        if self._travelling:
            return  # No input during FTL jump

        if event.type == pygame.KEYDOWN:
            # FTL confirmation overlay intercepts all keys
            if self._ftl_confirm:
                if event.key == pygame.K_RETURN:
                    self._ftl_confirm = False
                    self._start_travel(self.selected_system_id)
                elif event.key == pygame.K_ESCAPE:
                    self._ftl_confirm = False
                return

            self._keys_held.add(event.key)
            if event.key == pygame.K_RETURN and self.selected_system_id is not None:
                # Show confirmation instead of jumping immediately
                self._ftl_confirm = True
            elif event.key == pygame.K_TAB:
                self.open_fleet_tab = False
                self.next_state = GameState.MOTHERSHIP
            elif event.key == pygame.K_f:
                self.open_fleet_tab = True
                self.next_state = GameState.MOTHERSHIP
            elif event.key == pygame.K_l:
                self.next_state = GameState.CAPTAINS_LOG
        elif event.type == pygame.KEYUP:
            self._keys_held.discard(event.key)
        elif event.type == pygame.MOUSEWHEEL:
            # Zoom toward cursor
            factor = 1.15 if event.y > 0 else 1 / 1.15
            self.zoom = max(self.min_zoom, min(self.max_zoom, self.zoom * factor))
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if not self._ftl_confirm:
                self._handle_click(event.pos)

    def update(self, dt: float) -> None:
        # Keyboard panning
        speed = self._pan_speed / self.zoom * dt
        if pygame.K_w in self._keys_held or pygame.K_UP in self._keys_held:
            self.cam_y += speed
        if pygame.K_s in self._keys_held or pygame.K_DOWN in self._keys_held:
            self.cam_y -= speed
        if pygame.K_a in self._keys_held or pygame.K_LEFT in self._keys_held:
            self.cam_x += speed
        if pygame.K_d in self._keys_held or pygame.K_RIGHT in self._keys_held:
            self.cam_x -= speed

        # Hover detection
        mx, my = pygame.mouse.get_pos()
        self.hovered_system = self._system_at_screen_pos(mx, my)

        # FTL travel animation
        if self._travelling:
            self._travel_progress += dt * 0.8  # ~1.25 seconds to travel
            if self._travel_progress >= 1.0:
                self._complete_travel()

    def draw(self, surface: pygame.Surface) -> None:
        # Draw connections first (behind nodes)
        for system in self.galaxy.systems:
            sx, sy = self._world_to_screen(system.x, system.y)
            for conn_id in system.connections:
                conn = self.galaxy.get_system(conn_id)
                cx, cy = self._world_to_screen(conn.x, conn.y)
                # Only draw each connection once
                if conn.id > system.id:
                    color = (40, 40, 55) if not system.visited and not conn.visited else (60, 60, 80)
                    pygame.draw.line(surface, color, (sx, sy), (cx, cy), 1)

        # Draw systems
        current_id = self.galaxy.current_system_id
        connected_ids = set(self.galaxy.current_system.connections)

        for system in self.galaxy.systems:
            sx, sy = self._world_to_screen(system.x, system.y)

            # Skip if off screen
            if sx < -50 or sx > SCREEN_WIDTH + 50 or sy < -50 or sy > SCREEN_HEIGHT + 50:
                continue

            # Node size and color
            is_current = system.id == current_id
            is_connected = system.id in connected_ids
            is_selected = system.id == self.selected_system_id
            is_hovered = self.hovered_system and system.id == self.hovered_system.id

            star_color = STAR_COLORS.get(system.star_type.value, WHITE)
            radius = int(6 * self.zoom)

            if is_current:
                # Current system — pulsing ring
                pulse = 1.0 + 0.3 * math.sin(pygame.time.get_ticks() / 300)
                pygame.draw.circle(surface, AMBER, (sx, sy), int(radius * 1.8 * pulse), 2)
                pygame.draw.circle(surface, star_color, (sx, sy), radius)
            elif is_selected:
                pygame.draw.circle(surface, CYAN, (sx, sy), radius + 4, 2)
                pygame.draw.circle(surface, star_color, (sx, sy), radius)
            elif is_connected:
                pygame.draw.circle(surface, star_color, (sx, sy), radius)
                # Subtle highlight for reachable systems
                pygame.draw.circle(surface, (*star_color[:3],), (sx, sy), radius + 2, 1)
            else:
                dim = tuple(max(c // 2, 30) for c in star_color)
                r = max(2, radius - 2)
                pygame.draw.circle(surface, dim, (sx, sy), r)

            # System name (only for visited, hovered, or connected)
            if is_current or is_hovered or (is_connected and self.zoom > 0.8):
                name_color = WHITE if is_current or is_hovered else LIGHT_GREY
                name_surf = self.font_info.render(system.name, True, name_color)
                surface.blit(name_surf, (sx - name_surf.get_width() // 2, sy + radius + 6))

        # FTL travel effect
        if self._travelling:
            self._draw_ftl_effect(surface)

        # Tooltip for hovered system
        if self.hovered_system and not self._travelling:
            self._draw_tooltip(surface, self.hovered_system)

        # Info panel for selected system
        if self.selected_system_id is not None and not self._travelling:
            self._draw_system_panel(surface, self.galaxy.get_system(self.selected_system_id))

        # FTL cryosleep confirmation overlay (drawn on top of everything)
        if self._ftl_confirm:
            self._draw_ftl_confirm(surface)

    # ------------------------------------------------------------------
    # FTL travel
    # ------------------------------------------------------------------

    def _start_travel(self, target_id: int) -> None:
        if target_id not in self.galaxy.current_system.connections:
            return
        self._travelling = True
        self._travel_progress = 0.0
        self._travel_target_id = target_id

        start = self.galaxy.current_system
        end = self.galaxy.get_system(target_id)
        self._travel_start_pos = self._world_to_screen(start.x, start.y)
        self._travel_end_pos = self._world_to_screen(end.x, end.y)

    def _complete_travel(self) -> None:
        self._travelling = False
        if self._travel_target_id is not None:
            self.galaxy.travel_to(self._travel_target_id)
            # Center camera on new system
            new_sys = self.galaxy.current_system
            self.cam_x = -new_sys.x
            self.cam_y = -new_sys.y
            self.selected_system_id = None
            # Enter system view
            self.next_state = GameState.SYSTEM_VIEW

    def _draw_ftl_effect(self, surface: pygame.Surface) -> None:
        """Draw streaking lines during FTL jump."""
        t = self._travel_progress
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)

        # Streak lines radiating from center
        cx, cy = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
        num_streaks = 60
        for i in range(num_streaks):
            angle = (i / num_streaks) * math.tau
            length = 50 + t * 400
            inner_r = 20 + t * 100
            x1 = cx + math.cos(angle) * inner_r
            y1 = cy + math.sin(angle) * inner_r
            x2 = cx + math.cos(angle) * length
            y2 = cy + math.sin(angle) * length
            alpha = int(min(255, t * 400))
            pygame.draw.line(overlay, (*CYAN, alpha), (x1, y1), (x2, y2), 1)

        # Flash at completion
        if t > 0.8:
            flash_alpha = int((t - 0.8) / 0.2 * 200)
            overlay.fill((*WHITE, flash_alpha))

        surface.blit(overlay, (0, 0))

    # ------------------------------------------------------------------
    # Coordinate conversion
    # ------------------------------------------------------------------

    def _world_to_screen(self, wx: float, wy: float) -> tuple[int, int]:
        sx = int((wx + self.cam_x) * self.zoom + SCREEN_WIDTH / 2)
        sy = int((wy + self.cam_y) * self.zoom + SCREEN_HEIGHT / 2)
        return sx, sy

    def _screen_to_world(self, sx: int, sy: int) -> tuple[float, float]:
        wx = (sx - SCREEN_WIDTH / 2) / self.zoom - self.cam_x
        wy = (sy - SCREEN_HEIGHT / 2) / self.zoom - self.cam_y
        return wx, wy

    def _system_at_screen_pos(self, mx: int, my: int) -> StarSystem | None:
        """Find the system nearest to screen coords, within click radius."""
        hit_radius = max(12, 8 * self.zoom)
        best: StarSystem | None = None
        best_dist = float("inf")

        for system in self.galaxy.systems:
            sx, sy = self._world_to_screen(system.x, system.y)
            dist = math.hypot(mx - sx, my - sy)
            if dist < hit_radius and dist < best_dist:
                best = system
                best_dist = dist
        return best

    def _handle_click(self, pos: tuple[int, int]) -> None:
        clicked = self._system_at_screen_pos(*pos)
        if clicked:
            if clicked.id == self.galaxy.current_system_id:
                # Click current system → enter system view
                self.next_state = GameState.SYSTEM_VIEW
            elif clicked.id in self.galaxy.current_system.connections:
                self.selected_system_id = clicked.id
            else:
                self.selected_system_id = None
        else:
            self.selected_system_id = None

    # ------------------------------------------------------------------
    # UI panels
    # ------------------------------------------------------------------

    def _draw_tooltip(self, surface: pygame.Surface, system: StarSystem) -> None:
        mx, my = pygame.mouse.get_pos()
        lines = [
            system.name,
            f"Type: {system.star_type.value.replace('_', ' ').title()}",
            f"Danger: {'★' * system.danger_level}{'☆' * (5 - system.danger_level)}",
            f"Objects: {len(system.objects)}",
        ]
        if system.visited:
            lines.append("✓ Visited")

        line_height = 22
        w = 220
        h = len(lines) * line_height + 16
        tx = min(mx + 20, SCREEN_WIDTH - w - 10)
        ty = min(my - 10, SCREEN_HEIGHT - h - 10)

        tip_bg = pygame.Surface((w, h), pygame.SRCALPHA)
        tip_bg.fill((15, 15, 25, 220))
        surface.blit(tip_bg, (tx, ty))
        pygame.draw.rect(surface, PANEL_BORDER, (tx, ty, w, h), 1, border_radius=4)

        for i, line in enumerate(lines):
            color = AMBER if i == 0 else LIGHT_GREY
            surf = self.font_info.render(line, True, color)
            surface.blit(surf, (tx + 10, ty + 8 + i * line_height))

    def _draw_system_panel(self, surface: pygame.Surface, system: StarSystem) -> None:
        """Bottom panel showing selected system info with travel prompt."""
        panel_h = 60
        panel = pygame.Surface((SCREEN_WIDTH, panel_h), pygame.SRCALPHA)
        panel.fill(PANEL_BG)
        surface.blit(panel, (0, SCREEN_HEIGHT - panel_h))
        pygame.draw.line(
            surface, PANEL_BORDER,
            (0, SCREEN_HEIGHT - panel_h), (SCREEN_WIDTH, SCREEN_HEIGHT - panel_h),
        )

        name_surf = self.font_name.render(f"Target: {system.name}", True, AMBER)
        surface.blit(name_surf, (20, SCREEN_HEIGHT - panel_h + 8))

        danger_text = f"Danger: {'★' * system.danger_level}{'☆' * (5 - system.danger_level)}"
        danger_surf = self.font_info.render(danger_text, True, LIGHT_GREY)
        surface.blit(danger_surf, (20, SCREEN_HEIGHT - panel_h + 34))

        prompt = self.font_name.render("ENTER to jump", True, CYAN)
        surface.blit(prompt, (SCREEN_WIDTH - prompt.get_width() - 20, SCREEN_HEIGHT - panel_h + 16))

    def _draw_ftl_confirm(self, surface: pygame.Surface) -> None:
        """Draw the FTL cryosleep confirmation overlay."""
        # Dim background
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        surface.blit(overlay, (0, 0))

        # Dialog box
        box_w, box_h = 500, 200
        bx = SCREEN_WIDTH // 2 - box_w // 2
        by = SCREEN_HEIGHT // 2 - box_h // 2

        box = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        box.fill((10, 10, 20, 240))
        surface.blit(box, (bx, by))
        pygame.draw.rect(surface, AMBER, (bx, by, box_w, box_h), 2, border_radius=6)

        # Title
        title = self._ftl_confirm_font.render("⚠ ENTER CRYOSLEEP?", True, AMBER)
        surface.blit(title, (bx + box_w // 2 - title.get_width() // 2, by + 20))

        # Body text
        lines = [
            "FTL jump will put the fleet into cryogenic sleep.",
            "Systems will degrade. Colonists may not survive.",
            "Fleet ship hulls will deteriorate during transit.",
        ]
        for i, line in enumerate(lines):
            txt = self._ftl_confirm_body.render(line, True, LIGHT_GREY)
            surface.blit(txt, (bx + box_w // 2 - txt.get_width() // 2, by + 65 + i * 24))

        # Prompts
        enter_txt = self._ftl_confirm_body.render("ENTER — Confirm jump", True, CYAN)
        esc_txt = self._ftl_confirm_body.render("ESC — Cancel", True, RED_ALERT)
        surface.blit(enter_txt, (bx + 60, by + box_h - 40))
        surface.blit(esc_txt, (bx + box_w - 200, by + box_h - 40))
