"""Captain's Log screen — view game event timeline and discovered lore.

PLAN.md: "Included must be a sort of captain's log, containing lore and
optional tasks (connected to random events) that may provide either lore,
resources, or both."
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
from ..models.quest import LogEntry, LoreEntry, QuestFlag, QuestState
from ..states import GameState

# Category colours (icon, colour)
_CAT_STYLE: dict[str, tuple[str, tuple[int, int, int]]] = {
    "event": ("●", WHITE),
    "ftl": ("◆", CYAN),
    "combat": ("⚔", RED_ALERT),
    "exploration": ("◎", HULL_GREEN),
    "lore": ("★", AMBER),
}


class CaptainsLogScreen:
    """Two-tab captain's log: EVENT LOG timeline and LORE entries."""

    def __init__(self, quest_state: QuestState) -> None:
        self.quest_state = quest_state
        self.font_title = pygame.font.Font(None, 44)
        self.font_tab = pygame.font.Font(None, 30)
        self.font_heading = pygame.font.Font(None, 28)
        self.font_body = pygame.font.Font(None, 24)
        self.font_small = pygame.font.Font(None, 22)
        self.font_hint = pygame.font.Font(None, 22)

        self.next_state: GameState | None = None

        # Tab: "log" or "lore"
        self.active_tab = "log"

        # Log tab state
        self.log_scroll = 0
        self.log_selected = 0

        # Lore tab state
        self.lore_selected = 0

    def handle_events(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return

        if event.key == pygame.K_ESCAPE or event.key == pygame.K_l:
            self.next_state = GameState.STAR_MAP

        elif event.key == pygame.K_TAB:
            self.active_tab = "lore" if self.active_tab == "log" else "log"

        elif event.key in (pygame.K_UP, pygame.K_w):
            if self.active_tab == "log":
                self.log_selected = max(0, self.log_selected - 1)
            else:
                self.lore_selected = max(0, self.lore_selected - 1)

        elif event.key in (pygame.K_DOWN, pygame.K_s):
            if self.active_tab == "log":
                entries = self.quest_state.log_entries
                self.log_selected = min(len(entries) - 1, self.log_selected)
                if self.log_selected < len(entries) - 1:
                    self.log_selected += 1
            else:
                lore = self.quest_state.lore_entries
                self.lore_selected = min(len(lore) - 1, self.lore_selected)
                if self.lore_selected < len(lore) - 1:
                    self.lore_selected += 1

    def update(self, dt: float) -> None:
        pass  # Static screen

    def draw(self, surface: pygame.Surface) -> None:
        # --- Title ---
        title = self.font_title.render("CAPTAIN'S LOG", True, AMBER)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 35))
        surface.blit(title, title_rect)

        # --- Tabs ---
        self._draw_tabs(surface)

        # --- Content ---
        if self.active_tab == "log":
            self._draw_log_tab(surface)
        else:
            self._draw_lore_tab(surface)

        # --- Quest progress sidebar ---
        self._draw_quest_flags(surface)

        # --- Hints ---
        hint_text = "W/S navigate  |  TAB switch tab  |  ESC / L return to star map"
        hint = self.font_hint.render(hint_text, True, LIGHT_GREY)
        surface.blit(hint, (10, SCREEN_HEIGHT - 25))

    # ------------------------------------------------------------------
    # Tabs
    # ------------------------------------------------------------------

    def _draw_tabs(self, surface: pygame.Surface) -> None:
        log_count = len(self.quest_state.log_entries)
        lore_count = len(self.quest_state.lore_entries)

        tabs = [
            ("log", f"Event Log ({log_count})"),
            ("lore", f"Lore ({lore_count})"),
        ]

        x = 40
        y = 65
        for tab_id, label in tabs:
            is_active = self.active_tab == tab_id
            color = AMBER if is_active else DARK_GREY
            tab_surf = self.font_tab.render(label, True, color)
            surface.blit(tab_surf, (x, y))
            if is_active:
                w = tab_surf.get_width()
                pygame.draw.line(surface, AMBER, (x, y + 26), (x + w, y + 26), 2)
            x += tab_surf.get_width() + 40

    # ------------------------------------------------------------------
    # Log tab — event timeline
    # ------------------------------------------------------------------

    def _draw_log_tab(self, surface: pygame.Surface) -> None:
        entries = self.quest_state.log_entries
        if not entries:
            empty = self.font_heading.render("No events recorded yet.", True, LIGHT_GREY)
            empty_rect = empty.get_rect(center=(SCREEN_WIDTH // 3, SCREEN_HEIGHT // 2))
            surface.blit(empty, empty_rect)
            return

        # Show newest first
        displayed = list(reversed(entries))

        list_x = 30
        list_y = 100
        max_visible = (SCREEN_HEIGHT - 160) // 28
        selected_in_reversed = len(entries) - 1 - self.log_selected

        # Ensure selected is visible
        start = max(0, selected_in_reversed - max_visible + 1)
        end = start + max_visible
        visible = displayed[start:end]

        for i, entry in enumerate(visible):
            actual_idx = start + i
            is_selected = actual_idx == selected_in_reversed

            cat_icon, cat_color = _CAT_STYLE.get(entry.category, ("●", WHITE))

            if is_selected:
                pygame.draw.rect(surface, (20, 35, 55), (list_x - 5, list_y - 2, SCREEN_WIDTH - 310, 26), border_radius=3)

            # Turn number
            turn_text = f"T{entry.turn:03d}"
            turn_surf = self.font_small.render(turn_text, True, DARK_GREY)
            surface.blit(turn_surf, (list_x, list_y + 2))

            # Category icon
            icon_surf = self.font_body.render(cat_icon, True, cat_color)
            surface.blit(icon_surf, (list_x + 50, list_y))

            # Title
            title_color = CYAN if is_selected else WHITE
            title_surf = self.font_body.render(entry.title, True, title_color)
            surface.blit(title_surf, (list_x + 75, list_y))

            # Truncated text preview
            preview = entry.text[:80] + ("..." if len(entry.text) > 80 else "")
            prev_surf = self.font_small.render(preview, True, LIGHT_GREY if is_selected else DARK_GREY)
            max_preview_w = SCREEN_WIDTH - 310 - 80
            if prev_surf.get_width() > max_preview_w:
                # Clip rendering
                clip_rect = pygame.Rect(0, 0, max_preview_w, prev_surf.get_height())
                surface.blit(prev_surf, (list_x + 75, list_y + 14), clip_rect)
            else:
                surface.blit(prev_surf, (list_x + 75, list_y + 14))

            list_y += 28

        # Detail panel for selected entry
        if 0 <= self.log_selected < len(entries):
            self._draw_log_detail(surface, entries[self.log_selected])

    def _draw_log_detail(self, surface: pygame.Surface, entry: LogEntry) -> None:
        """Draw expanded detail for the selected log entry."""
        detail_x = 30
        detail_y = SCREEN_HEIGHT - 120
        detail_w = SCREEN_WIDTH - 320

        bg = pygame.Surface((detail_w, 90), pygame.SRCALPHA)
        bg.fill(PANEL_BG)
        surface.blit(bg, (detail_x, detail_y))
        pygame.draw.rect(surface, PANEL_BORDER, (detail_x, detail_y, detail_w, 90), 1, border_radius=4)

        cat_icon, cat_color = _CAT_STYLE.get(entry.category, ("●", WHITE))
        header = self.font_heading.render(f"{cat_icon} {entry.title}", True, cat_color)
        surface.blit(header, (detail_x + 10, detail_y + 8))

        turn_info = self.font_small.render(f"Turn {entry.turn} — {entry.category.upper()}", True, DARK_GREY)
        surface.blit(turn_info, (detail_x + 10, detail_y + 32))

        lines = self._wrap_text(entry.text, detail_w - 20)
        for i, line in enumerate(lines[:2]):  # Max 2 lines in detail box
            text = self.font_small.render(line, True, WHITE)
            surface.blit(text, (detail_x + 10, detail_y + 52 + i * 18))

    # ------------------------------------------------------------------
    # Lore tab
    # ------------------------------------------------------------------

    def _draw_lore_tab(self, surface: pygame.Surface) -> None:
        entries = self.quest_state.lore_entries

        # Lore progress
        total_lore = 5
        found = sum(
            1 for f in [
                QuestFlag.LORE_FRAGMENT_1, QuestFlag.LORE_FRAGMENT_2,
                QuestFlag.LORE_FRAGMENT_3, QuestFlag.LORE_FRAGMENT_4,
                QuestFlag.LORE_FRAGMENT_5,
            ]
            if self.quest_state.has_flag(f)
        )
        progress = self.font_body.render(
            f"Lore fragments: {found}/{total_lore}", True, LIGHT_GREY
        )
        surface.blit(progress, (40, 98))

        if not entries:
            empty = self.font_heading.render(
                "No lore discovered yet.", True, LIGHT_GREY
            )
            empty_rect = empty.get_rect(center=(SCREEN_WIDTH // 3, SCREEN_HEIGHT // 2))
            surface.blit(empty, empty_rect)
            hint = self.font_body.render(
                "Survey derelicts, anomalies and ruins to discover lore.",
                True, DARK_GREY,
            )
            hint_rect = hint.get_rect(center=(SCREEN_WIDTH // 3, SCREEN_HEIGHT // 2 + 35))
            surface.blit(hint, hint_rect)
            return

        # Left panel — entry list
        list_x = 30
        list_y = 125
        for i, entry in enumerate(entries):
            is_selected = i == self.lore_selected
            color = CYAN if is_selected else LIGHT_GREY
            prefix = "▶ " if is_selected else "  "
            text = self.font_body.render(f"{prefix}{entry.title}", True, color)
            surface.blit(text, (list_x, list_y + i * 26))

        # Right panel — detail view
        if 0 <= self.lore_selected < len(entries):
            self._draw_lore_detail(surface, entries[self.lore_selected])

    def _draw_lore_detail(self, surface: pygame.Surface, entry: LoreEntry) -> None:
        detail_x = 330
        detail_y = 100
        detail_w = SCREEN_WIDTH - 330 - 300
        max_w = max(detail_w, 200)

        panel_h = 300
        bg = pygame.Surface((max_w + 20, panel_h), pygame.SRCALPHA)
        bg.fill(PANEL_BG)
        surface.blit(bg, (detail_x - 10, detail_y - 5))
        pygame.draw.rect(
            surface, PANEL_BORDER,
            (detail_x - 10, detail_y - 5, max_w + 20, panel_h),
            1, border_radius=4,
        )

        title = self.font_heading.render(entry.title, True, AMBER)
        surface.blit(title, (detail_x, detail_y + 10))

        lines = self._wrap_text(entry.text, max_w)
        for i, line in enumerate(lines):
            text = self.font_body.render(line, True, WHITE)
            surface.blit(text, (detail_x, detail_y + 45 + i * 22))

    # ------------------------------------------------------------------
    # Quest progress sidebar
    # ------------------------------------------------------------------

    def _draw_quest_flags(self, surface: pygame.Surface) -> None:
        milestones = [
            (QuestFlag.DEFEATED_FEDERATION_FLEET, "Defeated Federation Fleet"),
            (QuestFlag.CLASS_4_ID_CODE, "Class 4 ID Code acquired"),
            (QuestFlag.DISCOVERED_EARTH, "Discovered Earth"),
            (QuestFlag.DEFEATED_EARTH_DEFENSE, "Defeated Earth Defense Fleet"),
            (QuestFlag.UNLOCKED_SIGNAL_OF_DAWN, "Signal of Dawn unlocked"),
            (QuestFlag.CLASS_1_ID_CODE, "Class 1 ID Code acquired"),
            (QuestFlag.REACHED_GATEWAY, "Reached the Gateway"),
        ]

        px = SCREEN_WIDTH - 270
        py = 100

        header = self.font_heading.render("Quest Progress", True, AMBER)
        surface.blit(header, (px, py))
        py += 28

        for flag, label in milestones:
            done = self.quest_state.has_flag(flag)
            icon = "✓" if done else "○"
            color = HULL_GREEN if done else DARK_GREY
            text = self.font_small.render(f"{icon} {label}", True, color)
            surface.blit(text, (px, py))
            py += 22

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def _wrap_text(self, text: str, max_width: int) -> list[str]:
        words = text.split()
        lines: list[str] = []
        current = ""
        for word in words:
            test = f"{current} {word}".strip()
            if self.font_body.size(test)[0] <= max_width:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines
