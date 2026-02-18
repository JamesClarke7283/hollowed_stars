"""Captain's Log — three-tab interface: event log, lore, and quest tasks.

Redesigned per PLAN.md with category filtering, quest task tracking,
and a master/detail layout.
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

# Category style: (icon character, colour)
_CAT_STYLE: dict[str, tuple[str, tuple[int, int, int]]] = {
    "event":       ("●", WHITE),
    "ftl":         ("◆", CYAN),
    "combat":      ("⚔", RED_ALERT),
    "exploration": ("◎", HULL_GREEN),
    "lore":        ("★", AMBER),
}
_ALL_CATEGORIES = ["all", "event", "ftl", "combat", "exploration", "lore"]

# Layout constants
_HEADER_H = 55
_TAB_H = 32
_FILTER_H = 28
_MENU_BAR_H = 36
_LIST_W = 420
_CONTENT_TOP = _HEADER_H + _TAB_H + _FILTER_H + 8
_CONTENT_BOTTOM = SCREEN_HEIGHT - _MENU_BAR_H - 8
_DETAIL_X = _LIST_W + 20
_DETAIL_W = SCREEN_WIDTH - _DETAIL_X - 15


class CaptainsLogScreen:
    """Three-tab captain's log: event log, lore, quest tasks."""

    def __init__(self, quest_state: QuestState) -> None:
        self.quest_state = quest_state
        self.font_title  = pygame.font.Font(None, 44)
        self.font_tab    = pygame.font.Font(None, 28)
        self.font_head   = pygame.font.Font(None, 30)
        self.font_body   = pygame.font.Font(None, 24)
        self.font_small  = pygame.font.Font(None, 20)
        self.font_hint   = pygame.font.Font(None, 22)

        self.next_state: GameState | None = None

        # Active tab: "log", "lore", or "tasks"
        self.active_tab = "log"

        # Selection indices
        self.log_selected = 0
        self.lore_selected = 0
        self.task_selected = 0

        # Log category filter
        self.filter_idx = 0  # index into _ALL_CATEGORIES

    # ── Input ──────────────────────────────────────────────────────────

    def handle_events(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return

        if event.key in (pygame.K_ESCAPE, pygame.K_l):
            self.next_state = GameState.STAR_MAP
        elif event.key == pygame.K_TAB:
            tabs = ["log", "lore", "tasks"]
            idx = tabs.index(self.active_tab)
            self.active_tab = tabs[(idx + 1) % len(tabs)]
        elif event.key in (pygame.K_UP, pygame.K_w):
            self._move_selection(-1)
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self._move_selection(1)
        elif event.key in (pygame.K_LEFT, pygame.K_a) and self.active_tab == "log":
            self.filter_idx = (self.filter_idx - 1) % len(_ALL_CATEGORIES)
            self.log_selected = 0
        elif event.key in (pygame.K_RIGHT, pygame.K_d) and self.active_tab == "log":
            self.filter_idx = (self.filter_idx + 1) % len(_ALL_CATEGORIES)
            self.log_selected = 0

    def _move_selection(self, delta: int) -> None:
        if self.active_tab == "log":
            filtered = self._filtered_log_entries()
            n = len(filtered)
            if n:
                self.log_selected = max(0, min(n - 1, self.log_selected + delta))
        elif self.active_tab == "lore":
            n = len(self.quest_state.lore_entries)
            if n:
                self.lore_selected = max(0, min(n - 1, self.lore_selected + delta))
        else:
            tasks = self.quest_state.active_tasks
            n = len(tasks)
            if n:
                self.task_selected = max(0, min(n - 1, self.task_selected + delta))

    def _filtered_log_entries(self) -> list[LogEntry]:
        cat = _ALL_CATEGORIES[self.filter_idx]
        entries = self.quest_state.log_entries
        if cat == "all":
            return entries
        return [e for e in entries if e.category == cat]

    def update(self, dt: float) -> None:
        pass

    # ── Draw ───────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((5, 8, 15, 230))
        surface.blit(overlay, (0, 0))

        self._draw_header(surface)
        self._draw_tabs(surface)

        if self.active_tab == "log":
            self._draw_filter_bar(surface)
            self._draw_log_list(surface)
            self._draw_log_detail(surface)
        elif self.active_tab == "lore":
            self._draw_lore_list(surface)
            self._draw_lore_detail(surface)
        else:
            self._draw_tasks(surface)

        self._draw_menu_bar(surface)

    # ── Header ─────────────────────────────────────────────────────────

    def _draw_header(self, surface: pygame.Surface) -> None:
        bar = pygame.Surface((SCREEN_WIDTH, _HEADER_H), pygame.SRCALPHA)
        bar.fill((8, 12, 22, 230))
        surface.blit(bar, (0, 0))
        pygame.draw.line(surface, AMBER, (0, _HEADER_H - 1), (SCREEN_WIDTH, _HEADER_H - 1), 1)

        title = self.font_title.render("CAPTAIN'S LOG", True, AMBER)
        surface.blit(title, (20, 12))

        turn = self.quest_state.turn
        cols = self.quest_state.colonies_established
        info = self.font_small.render(
            f"Turn {turn}  ·  Colonies: {cols}/5", True, LIGHT_GREY,
        )
        surface.blit(info, (SCREEN_WIDTH - info.get_width() - 20, 20))

    # ── Tabs ───────────────────────────────────────────────────────────

    def _draw_tabs(self, surface: pygame.Surface) -> None:
        log_n = len(self.quest_state.log_entries)
        lore_n = len(self.quest_state.lore_entries)
        task_n = len(self.quest_state.active_tasks)
        tabs = [
            ("log",   f"Event Log ({log_n})"),
            ("lore",  f"Lore ({lore_n})"),
            ("tasks", f"Objectives ({task_n})"),
        ]

        x = 20
        y = _HEADER_H + 4
        for tab_id, label in tabs:
            active = self.active_tab == tab_id
            color = AMBER if active else DARK_GREY
            surf = self.font_tab.render(label, True, color)
            surface.blit(surf, (x, y))
            if active:
                w = surf.get_width()
                pygame.draw.line(surface, AMBER, (x, y + 24), (x + w, y + 24), 2)
            x += surf.get_width() + 35

    # ── Log filter bar ─────────────────────────────────────────────────

    def _draw_filter_bar(self, surface: pygame.Surface) -> None:
        y = _HEADER_H + _TAB_H + 2
        label = self.font_small.render("Filter:", True, LIGHT_GREY)
        surface.blit(label, (20, y + 4))
        x = 75
        for i, cat in enumerate(_ALL_CATEGORIES):
            active = i == self.filter_idx
            display = cat.upper() if cat != "all" else "ALL"
            icon = ""
            if cat in _CAT_STYLE:
                icon = _CAT_STYLE[cat][0] + " "
            text = f"{icon}{display}"
            color = AMBER if active else DARK_GREY
            s = self.font_small.render(text, True, color)
            surface.blit(s, (x, y + 4))
            if active:
                pygame.draw.line(surface, AMBER, (x, y + 20), (x + s.get_width(), y + 20), 1)
            x += s.get_width() + 20

    # ── Log list ───────────────────────────────────────────────────────

    def _draw_log_list(self, surface: pygame.Surface) -> None:
        entries = self._filtered_log_entries()
        if not entries:
            cat = _ALL_CATEGORIES[self.filter_idx]
            msg = "No events recorded yet." if cat == "all" else f"No {cat} events."
            self._draw_empty(msg, surface)
            return

        panel_h = _CONTENT_BOTTOM - _CONTENT_TOP
        panel = pygame.Surface((_LIST_W, panel_h), pygame.SRCALPHA)
        panel.fill((10, 14, 24, 200))
        surface.blit(panel, (8, _CONTENT_TOP))
        pygame.draw.rect(surface, PANEL_BORDER, (8, _CONTENT_TOP, _LIST_W, panel_h), 1, border_radius=4)

        # Newest first
        displayed = list(reversed(entries))
        row_h = 38
        max_visible = panel_h // row_h
        sel_rev = len(entries) - 1 - self.log_selected

        scroll = max(0, sel_rev - max_visible + 1)
        visible = displayed[scroll : scroll + max_visible]

        y = _CONTENT_TOP + 4
        for i, entry in enumerate(visible):
            idx = scroll + i
            selected = idx == sel_rev
            lx = 16

            if selected:
                pygame.draw.rect(
                    surface, (20, 40, 65),
                    (10, y, _LIST_W - 4, row_h - 2),
                    border_radius=3,
                )

            icon, icon_c = _CAT_STYLE.get(entry.category, ("●", WHITE))
            ic = self.font_body.render(icon, True, icon_c)
            surface.blit(ic, (lx, y + 4))

            title_c = CYAN if selected else WHITE
            max_title_w = _LIST_W - 110
            title_text = entry.title
            title_s = self.font_body.render(title_text, True, title_c)
            if title_s.get_width() > max_title_w:
                while title_s.get_width() > max_title_w and len(title_text) > 4:
                    title_text = title_text[:-2]
                    title_s = self.font_body.render(title_text + "…", True, title_c)
            surface.blit(title_s, (lx + 24, y + 2))

            turn_s = self.font_small.render(f"T{entry.turn:03d}", True, DARK_GREY)
            surface.blit(turn_s, (lx + 24, y + 20))

            preview = entry.text[:60] + ("…" if len(entry.text) > 60 else "")
            prev_s = self.font_small.render(preview, True, LIGHT_GREY if selected else DARK_GREY)
            pw = _LIST_W - 90
            if prev_s.get_width() > pw:
                clip = pygame.Rect(0, 0, pw, prev_s.get_height())
                surface.blit(prev_s, (lx + 80, y + 20), clip)
            else:
                surface.blit(prev_s, (lx + 80, y + 20))

            y += row_h

    # ── Log detail ─────────────────────────────────────────────────────

    def _draw_log_detail(self, surface: pygame.Surface) -> None:
        entries = self._filtered_log_entries()
        if not entries:
            return
        if not (0 <= self.log_selected < len(entries)):
            return
        entry = entries[self.log_selected]

        panel_h = _CONTENT_BOTTOM - _CONTENT_TOP
        bg = pygame.Surface((_DETAIL_W, panel_h), pygame.SRCALPHA)
        bg.fill((12, 16, 28, 200))
        surface.blit(bg, (_DETAIL_X, _CONTENT_TOP))
        pygame.draw.rect(
            surface, PANEL_BORDER,
            (_DETAIL_X, _CONTENT_TOP, _DETAIL_W, panel_h),
            1, border_radius=4,
        )

        x = _DETAIL_X + 16
        y = _CONTENT_TOP + 14

        icon, icon_c = _CAT_STYLE.get(entry.category, ("●", WHITE))
        header = self.font_head.render(f"{icon}  {entry.title}", True, icon_c)
        surface.blit(header, (x, y))
        y += 34

        meta = self.font_small.render(
            f"Turn {entry.turn}  ·  Category: {entry.category.upper()}", True, DARK_GREY,
        )
        surface.blit(meta, (x, y))
        y += 24
        pygame.draw.line(surface, PANEL_BORDER, (x, y), (x + _DETAIL_W - 32, y), 1)
        y += 12

        lines = self._wrap(entry.text, _DETAIL_W - 40, self.font_body)
        for line in lines:
            if y > _CONTENT_BOTTOM - 20:
                break
            ts = self.font_body.render(line, True, WHITE)
            surface.blit(ts, (x, y))
            y += 22

    # ── Lore list ──────────────────────────────────────────────────────

    def _draw_lore_list(self, surface: pygame.Surface) -> None:
        entries = self.quest_state.lore_entries

        panel_h = _CONTENT_BOTTOM - _CONTENT_TOP
        panel = pygame.Surface((_LIST_W, panel_h), pygame.SRCALPHA)
        panel.fill((10, 14, 24, 200))
        surface.blit(panel, (8, _CONTENT_TOP))
        pygame.draw.rect(surface, PANEL_BORDER, (8, _CONTENT_TOP, _LIST_W, panel_h), 1, border_radius=4)

        found = sum(
            1 for f in [
                QuestFlag.LORE_FRAGMENT_1, QuestFlag.LORE_FRAGMENT_2,
                QuestFlag.LORE_FRAGMENT_3, QuestFlag.LORE_FRAGMENT_4,
                QuestFlag.LORE_FRAGMENT_5,
            ]
            if self.quest_state.has_flag(f)
        )
        counter = self.font_small.render(f"Fragments: {found}/5", True, LIGHT_GREY)
        surface.blit(counter, (16, _CONTENT_TOP + 8))

        if not entries:
            empty = self.font_body.render("No lore discovered.", True, DARK_GREY)
            surface.blit(empty, (16, _CONTENT_TOP + 40))
            hint = self.font_small.render(
                "Survey derelicts and ancient ruins to uncover lost history.", True, DARK_GREY,
            )
            surface.blit(hint, (16, _CONTENT_TOP + 66))
            return

        y = _CONTENT_TOP + 30
        for i, entry in enumerate(entries):
            selected = i == self.lore_selected
            if selected:
                pygame.draw.rect(
                    surface, (20, 40, 65),
                    (10, y, _LIST_W - 4, 28),
                    border_radius=3,
                )
            color = CYAN if selected else LIGHT_GREY
            prefix = "★ " if selected else "  "
            ts = self.font_body.render(f"{prefix}{entry.title}", True, color)
            surface.blit(ts, (16, y + 4))
            y += 30

    # ── Lore detail ────────────────────────────────────────────────────

    def _draw_lore_detail(self, surface: pygame.Surface) -> None:
        entries = self.quest_state.lore_entries
        if not entries:
            return
        if not (0 <= self.lore_selected < len(entries)):
            return
        entry = entries[self.lore_selected]

        panel_h = _CONTENT_BOTTOM - _CONTENT_TOP
        bg = pygame.Surface((_DETAIL_W, panel_h), pygame.SRCALPHA)
        bg.fill((12, 16, 28, 200))
        surface.blit(bg, (_DETAIL_X, _CONTENT_TOP))
        pygame.draw.rect(
            surface, PANEL_BORDER,
            (_DETAIL_X, _CONTENT_TOP, _DETAIL_W, panel_h),
            1, border_radius=4,
        )

        x = _DETAIL_X + 16
        y = _CONTENT_TOP + 14

        header = self.font_head.render(f"★  {entry.title}", True, AMBER)
        surface.blit(header, (x, y))
        y += 34
        pygame.draw.line(surface, PANEL_BORDER, (x, y), (x + _DETAIL_W - 32, y), 1)
        y += 14

        lines = self._wrap(entry.text, _DETAIL_W - 40, self.font_body)
        for line in lines:
            if y > _CONTENT_BOTTOM - 20:
                break
            ts = self.font_body.render(line, True, WHITE)
            surface.blit(ts, (x, y))
            y += 22

        # Quest progress section
        y += 20
        if y < _CONTENT_BOTTOM - 100:
            pygame.draw.line(surface, PANEL_BORDER, (x, y), (x + _DETAIL_W - 32, y), 1)
            y += 12
            qh = self.font_body.render("Quest Milestones", True, AMBER)
            surface.blit(qh, (x, y))
            y += 28

            milestones = [
                (QuestFlag.DEFEATED_FEDERATION_FLEET, "Defeated Federation Fleet"),
                (QuestFlag.CLASS_4_ID_CODE, "Class 4 ID Code"),
                (QuestFlag.DISCOVERED_EARTH, "Discovered Earth"),
                (QuestFlag.DEFEATED_EARTH_DEFENSE, "Defeated Earth Defense"),
                (QuestFlag.UNLOCKED_SIGNAL_OF_DAWN, "Signal of Dawn"),
                (QuestFlag.REACHED_GATEWAY, "Reached the Gateway"),
            ]
            for flag, label in milestones:
                if y > _CONTENT_BOTTOM - 20:
                    break
                done = self.quest_state.has_flag(flag)
                icon = "✓" if done else "○"
                color = HULL_GREEN if done else DARK_GREY
                ms = self.font_small.render(f"  {icon}  {label}", True, color)
                surface.blit(ms, (x, y))
                y += 20

    # ── Tasks tab ──────────────────────────────────────────────────────

    def _draw_tasks(self, surface: pygame.Surface) -> None:
        tasks = self.quest_state.active_tasks

        # Full-width panel
        panel_w = SCREEN_WIDTH - 30
        panel_h = _CONTENT_BOTTOM - _CONTENT_TOP
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel.fill((10, 14, 24, 200))
        surface.blit(panel, (15, _CONTENT_TOP))
        pygame.draw.rect(surface, PANEL_BORDER, (15, _CONTENT_TOP, panel_w, panel_h), 1, border_radius=4)

        if not tasks:
            empty = self.font_body.render(
                "No objectives yet. Explore the galaxy to discover your purpose.", True, DARK_GREY,
            )
            surface.blit(empty, (30, _CONTENT_TOP + 40))
            return

        x = 30
        y = _CONTENT_TOP + 12

        # Section header
        header = self.font_head.render("MAIN QUEST", True, AMBER)
        surface.blit(header, (x, y))
        y += 34
        pygame.draw.line(surface, PANEL_BORDER, (x, y), (x + panel_w - 40, y), 1)
        y += 12

        for i, (task, completed) in enumerate(tasks):
            selected = i == self.task_selected
            row_h = 58

            if selected:
                pygame.draw.rect(
                    surface, (20, 40, 65),
                    (18, y - 2, panel_w - 6, row_h),
                    border_radius=3,
                )

            # Status icon
            if completed:
                icon = "✓"
                icon_color = HULL_GREEN
            else:
                icon = "▸" if selected else "○"
                icon_color = CYAN if selected else LIGHT_GREY

            ic = self.font_head.render(icon, True, icon_color)
            surface.blit(ic, (x, y + 4))

            # Title
            title_color = HULL_GREEN if completed else (WHITE if selected else LIGHT_GREY)
            ts = self.font_head.render(task.title, True, title_color)
            surface.blit(ts, (x + 28, y + 2))

            # Description
            desc_color = LIGHT_GREY if not completed else DARK_GREY
            desc_lines = self._wrap(task.description, panel_w - 80, self.font_small)
            for dl in desc_lines[:2]:
                ds = self.font_small.render(dl, True, desc_color)
                surface.blit(ds, (x + 28, y + 26))
                y += 16
            y += row_h - 16 * min(len(desc_lines), 2)

            if y > _CONTENT_BOTTOM - 30:
                break

        # Optional tasks section
        y += 10
        if y < _CONTENT_BOTTOM - 40:
            self.quest_state.ensure_optional_tasks()
            opt_tasks = self.quest_state.optional_tasks
            if opt_tasks:
                pygame.draw.line(surface, PANEL_BORDER, (x, y), (x + panel_w - 40, y), 1)
                y += 12
                opt_header = self.font_head.render("OPTIONAL OBJECTIVES", True, AMBER)
                surface.blit(opt_header, (x, y))
                y += 30

                for ot in opt_tasks:
                    if y > _CONTENT_BOTTOM - 40:
                        break
                    done = ot.completed
                    icon = "✓" if done else "○"
                    color = HULL_GREEN if done else WHITE
                    progress_str = f"{ot.progress}/{ot.target}"
                    text = f"{icon}  {ot.title} ({progress_str})"
                    ts = self.font_body.render(text, True, color)
                    surface.blit(ts, (x, y))
                    y += 22
                    desc = self.font_small.render(
                        ot.description, True, LIGHT_GREY if not done else DARK_GREY,
                    )
                    surface.blit(desc, (x + 28, y))
                    y += 22

    # ── Menu bar ───────────────────────────────────────────────────────

    def _draw_menu_bar(self, surface: pygame.Surface) -> None:
        bar_y = SCREEN_HEIGHT - _MENU_BAR_H
        bar = pygame.Surface((SCREEN_WIDTH, _MENU_BAR_H), pygame.SRCALPHA)
        bar.fill((8, 12, 22, 230))
        surface.blit(bar, (0, bar_y))
        pygame.draw.line(surface, AMBER, (0, bar_y), (SCREEN_WIDTH, bar_y), 1)

        actions = [
            ("[W/S]", "Navigate"),
            ("[TAB]", "Switch Tab"),
        ]
        if self.active_tab == "log":
            actions.append(("[A/D]", "Filter"))
        actions += [
            ("[L]", "Exit"),
            ("[ESC]", "Exit"),
        ]
        x = 20
        for key, label in actions:
            ks = self.font_hint.render(key, True, AMBER)
            surface.blit(ks, (x, bar_y + 10))
            x += ks.get_width() + 6
            ls = self.font_hint.render(label, True, LIGHT_GREY)
            surface.blit(ls, (x, bar_y + 10))
            x += ls.get_width() + 30

    # ── Utility ────────────────────────────────────────────────────────

    def _draw_empty(self, msg: str, surface: pygame.Surface) -> None:
        s = self.font_body.render(msg, True, DARK_GREY)
        r = s.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        surface.blit(s, r)

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
