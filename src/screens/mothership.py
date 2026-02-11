"""Mothership systems & fleet management screen.

Two tabs:
  1. SYSTEMS — repair/maintain the 8 internal mothership systems
  2. FLEET — build ships, equip weapons, scrap ships
"""

from __future__ import annotations

import math

import pygame

from ..constants import (
    AMBER,
    CYAN,
    DARK_GREY,
    ENERGY_COLOR,
    HULL_GREEN,
    LIGHT_GREY,
    METAL_COLOR,
    PANEL_BG,
    PANEL_BORDER,
    RARE_COLOR,
    RED_ALERT,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    SHIELD_BLUE,
    WHITE,
)
from ..models.mothership_systems import ShipSystem, SystemType
from ..models.ships import (
    Fleet,
    FleetShip,
    ShipClass,
    SHIP_CLASS_STATS,
    WeaponSize,
)
from ..models.weapons import CRAFTABLE_WEAPONS, Weapon, weapons_for_size
from ..states import GameState


# Visual layout for system rooms on the cross-section
_SYSTEM_POSITIONS: dict[SystemType, tuple[int, int]] = {
    SystemType.SHIELDS:       (1, 0),
    SystemType.POWER_CORE:    (0, 1),
    SystemType.WEAPONS_ARRAY: (2, 1),
    SystemType.SENSORS:       (1, 1),
    SystemType.LIFE_SUPPORT:  (0, 2),
    SystemType.CRYO_VAULTS:   (2, 2),
    SystemType.THRUSTERS:     (0, 3),
    SystemType.HANGAR:        (2, 3),
}

# All buildable ship classes in menu order
BUILDABLE_CLASSES = [
    ShipClass.DRONE,
    ShipClass.FIGHTER,
    ShipClass.CORVETTE,
    ShipClass.FRIGATE,
    ShipClass.DESTROYER,
    ShipClass.CRUISER,
    ShipClass.HEAVY_CRUISER,
    ShipClass.BATTLESHIP,
    ShipClass.SCOUT,
    ShipClass.MINER,
    ShipClass.TRANSPORT,
]


class MothershipScreen:
    """Mothership management — tabbed between systems and fleet."""

    def __init__(self, fleet: Fleet, systems: list[ShipSystem]) -> None:
        self.fleet = fleet
        self.systems = systems
        self.font_title = pygame.font.Font(None, 40)
        self.font_tab = pygame.font.Font(None, 30)
        self.font_name = pygame.font.Font(None, 28)
        self.font_info = pygame.font.Font(None, 24)
        self.font_small = pygame.font.Font(None, 22)

        # Tab state: "systems" or "fleet"
        self.active_tab = "systems"

        # --- Systems tab ---
        self.selected_index = 0
        self.timer = 0.0
        self.next_state: GameState | None = None

        # Repair feedback
        self._message = ""
        self._message_timer = 0.0
        self._message_color = WHITE

        # --- Fleet tab ---
        self.fleet_mode = "list"  # "list", "build", "equip"
        self.fleet_ship_idx = 0
        self.build_cursor = 0
        self.equip_slot_idx = 0
        self.equip_weapon_idx = 0

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def handle_events(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            # Tab switching
            if event.key == pygame.K_TAB:
                if self.active_tab == "systems":
                    self.active_tab = "fleet"
                    self.fleet_mode = "list"
                else:
                    self.active_tab = "systems"
                return

            if event.key == pygame.K_ESCAPE:
                if self.active_tab == "fleet" and self.fleet_mode != "list":
                    self.fleet_mode = "list"
                    return
                self.next_state = GameState.STAR_MAP
                return

            if self.active_tab == "systems":
                self._handle_systems(event.key)
            else:
                self._handle_fleet(event.key)

    def _handle_systems(self, key: int) -> None:
        if key in (pygame.K_UP, pygame.K_w):
            self.selected_index = max(0, self.selected_index - 1)
        elif key in (pygame.K_DOWN, pygame.K_s):
            self.selected_index = min(len(self.systems) - 1, self.selected_index + 1)
        elif key in (pygame.K_RETURN, pygame.K_SPACE):
            self._repair_selected()

    def _handle_fleet(self, key: int) -> None:
        if self.fleet_mode == "list":
            self._handle_fleet_list(key)
        elif self.fleet_mode == "build":
            self._handle_fleet_build(key)
        elif self.fleet_mode == "equip":
            self._handle_fleet_equip(key)

    def _handle_fleet_list(self, key: int) -> None:
        ships = self.fleet.ships
        if key in (pygame.K_UP, pygame.K_w):
            if ships:
                self.fleet_ship_idx = (self.fleet_ship_idx - 1) % len(ships)
        elif key in (pygame.K_DOWN, pygame.K_s):
            if ships:
                self.fleet_ship_idx = (self.fleet_ship_idx + 1) % len(ships)
        elif key == pygame.K_b:
            self.fleet_mode = "build"
            self.build_cursor = 0
        elif key == pygame.K_e and ships:
            ship = ships[self.fleet_ship_idx]
            if ship.weapon_slots:
                self.fleet_mode = "equip"
                self.equip_slot_idx = 0
                self.equip_weapon_idx = 0
            else:
                self._message = "This ship has no weapon mounts."
                self._message_color = AMBER
                self._message_timer = 2.0
        elif key == pygame.K_x and ships:
            ship = ships[self.fleet_ship_idx]
            self.fleet.scrap_ship(ship)
            if self.fleet_ship_idx >= len(ships):
                self.fleet_ship_idx = max(0, len(ships) - 1)
            self._message = f"Scrapped — resources recovered"
            self._message_color = AMBER
            self._message_timer = 2.0

    def _handle_fleet_build(self, key: int) -> None:
        if key in (pygame.K_UP, pygame.K_w):
            self.build_cursor = (self.build_cursor - 1) % len(BUILDABLE_CLASSES)
        elif key in (pygame.K_DOWN, pygame.K_s):
            self.build_cursor = (self.build_cursor + 1) % len(BUILDABLE_CLASSES)
        elif key in (pygame.K_RETURN, pygame.K_SPACE):
            sc = BUILDABLE_CLASSES[self.build_cursor]
            result = self.fleet.build_ship(sc)
            if result:
                self._message = f"Built {result.name}"
                self._message_color = HULL_GREEN
            else:
                self._message = "Cannot build — insufficient resources or hangar full"
                self._message_color = RED_ALERT
            self._message_timer = 2.0
        elif key == pygame.K_ESCAPE:
            self.fleet_mode = "list"

    def _handle_fleet_equip(self, key: int) -> None:
        ships = self.fleet.ships
        if not ships:
            self.fleet_mode = "list"
            return
        ship = ships[self.fleet_ship_idx]
        if not ship.weapon_slots:
            self.fleet_mode = "list"
            return

        slot = ship.weapon_slots[self.equip_slot_idx]
        available = weapons_for_size(slot.size.value)

        if key in (pygame.K_UP, pygame.K_w):
            self.equip_slot_idx = (self.equip_slot_idx - 1) % len(ship.weapon_slots)
            self.equip_weapon_idx = 0
        elif key in (pygame.K_DOWN, pygame.K_s):
            self.equip_slot_idx = (self.equip_slot_idx + 1) % len(ship.weapon_slots)
            self.equip_weapon_idx = 0
        elif key in (pygame.K_LEFT, pygame.K_a) and available:
            self.equip_weapon_idx = (self.equip_weapon_idx - 1) % len(available)
        elif key in (pygame.K_RIGHT, pygame.K_d) and available:
            self.equip_weapon_idx = (self.equip_weapon_idx + 1) % len(available)
        elif key in (pygame.K_RETURN, pygame.K_SPACE) and available:
            wpn = available[self.equip_weapon_idx]
            r = self.fleet.resources
            if (r.metal >= wpn.build_cost_metal
                    and r.energy >= wpn.build_cost_energy
                    and r.rare_materials >= wpn.build_cost_rare):
                r.metal -= wpn.build_cost_metal
                r.energy -= wpn.build_cost_energy
                r.rare_materials -= wpn.build_cost_rare
                slot.equipped = wpn.name
                self._message = f"Equipped {wpn.name}"
                self._message_color = HULL_GREEN
                self._message_timer = 2.0
            else:
                self._message = "Not enough resources!"
                self._message_color = RED_ALERT
                self._message_timer = 2.0
        elif key == pygame.K_ESCAPE:
            self.fleet_mode = "list"

    def update(self, dt: float) -> None:
        self.timer += dt
        if self._message_timer > 0:
            self._message_timer -= dt

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def draw(self, surface: pygame.Surface) -> None:
        # Title
        title = self.font_title.render("MOTHERSHIP", True, AMBER)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 25))
        surface.blit(title, title_rect)

        ship_name = self.font_small.render(self.fleet.mothership.name, True, LIGHT_GREY)
        name_rect = ship_name.get_rect(center=(SCREEN_WIDTH // 2, 48))
        surface.blit(ship_name, name_rect)

        # Tab bar
        self._draw_tabs(surface)

        # Tab content
        if self.active_tab == "systems":
            self._draw_systems_tab(surface)
        else:
            self._draw_fleet_tab(surface)

        # Message
        if self._message_timer > 0:
            alpha = min(255, int(self._message_timer * 255))
            msg_surf = self.font_name.render(self._message, True, self._message_color)
            msg_surf.set_alpha(alpha)
            msg_rect = msg_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 55))
            surface.blit(msg_surf, msg_rect)

        # Hints
        self._draw_hints(surface)

    def _draw_tabs(self, surface: pygame.Surface) -> None:
        tab_y = 62
        tabs = [("SYSTEMS", "systems"), ("FLEET", "fleet")]
        tab_w = 160
        total_w = tab_w * len(tabs) + 10
        start_x = (SCREEN_WIDTH - total_w) // 2

        for i, (label, key) in enumerate(tabs):
            x = start_x + i * (tab_w + 10)
            active = self.active_tab == key

            if active:
                pygame.draw.rect(surface, PANEL_BG, (x, tab_y, tab_w, 28), border_radius=4)
                pygame.draw.rect(surface, AMBER, (x, tab_y, tab_w, 28), 2, border_radius=4)
                color = AMBER
            else:
                pygame.draw.rect(surface, (20, 20, 35), (x, tab_y, tab_w, 28), border_radius=4)
                pygame.draw.rect(surface, PANEL_BORDER, (x, tab_y, tab_w, 28), 1, border_radius=4)
                color = LIGHT_GREY

            surf = self.font_tab.render(label, True, color)
            rect = surf.get_rect(center=(x + tab_w // 2, tab_y + 14))
            surface.blit(surf, rect)

    def _draw_hints(self, surface: pygame.Surface) -> None:
        if self.active_tab == "systems":
            hint = "W/S select  |  ENTER repair  |  TAB→Fleet  |  ESC back"
        elif self.fleet_mode == "list":
            hint = "W/S select  |  B build  |  E equip  |  X scrap  |  TAB→Systems  |  ESC back"
        elif self.fleet_mode == "build":
            hint = "W/S select  |  ENTER build  |  ESC cancel"
        elif self.fleet_mode == "equip":
            hint = "W/S slot  |  A/D weapon  |  ENTER equip  |  ESC cancel"
        else:
            hint = ""
        surf = self.font_small.render(hint, True, LIGHT_GREY)
        rect = surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 25))
        surface.blit(surf, rect)

    # ------------------------------------------------------------------
    # SYSTEMS TAB
    # ------------------------------------------------------------------

    def _draw_systems_tab(self, surface: pygame.Surface) -> None:
        # Ship cross-section (left side)
        self._draw_cross_section(surface)
        # System list with details (right side)
        self._draw_system_list(surface)
        # Selected system detail
        if 0 <= self.selected_index < len(self.systems):
            self._draw_system_detail(surface, self.systems[self.selected_index])

    def _draw_cross_section(self, surface: pygame.Surface) -> None:
        base_x = 40
        base_y = 100
        room_w = 130
        room_h = 90
        gap = 10

        hull_w = 3 * room_w + 4 * gap
        hull_h = 4 * room_h + 5 * gap
        pygame.draw.rect(
            surface, PANEL_BORDER,
            (base_x - gap, base_y - gap, hull_w, hull_h),
            2, border_radius=12,
        )

        for i, system in enumerate(self.systems):
            pos = _SYSTEM_POSITIONS.get(system.system_type, (i % 3, i // 3))
            rx = base_x + pos[0] * (room_w + gap)
            ry = base_y + pos[1] * (room_h + gap)
            is_selected = i == self.selected_index

            if system.is_critical:
                room_color = (60, 15, 15)
            elif system.is_warning:
                room_color = (50, 40, 10)
            else:
                room_color = (15, 25, 15)

            room_surf = pygame.Surface((room_w, room_h), pygame.SRCALPHA)
            room_surf.fill((*room_color, 200))
            surface.blit(room_surf, (rx, ry))

            border_color = AMBER if is_selected else PANEL_BORDER
            pygame.draw.rect(surface, border_color, (rx, ry, room_w, room_h), 2 if is_selected else 1, border_radius=4)

            name = self.font_small.render(system.name, True, WHITE if is_selected else LIGHT_GREY)
            surface.blit(name, (rx + 5, ry + 5))

            bar_y = ry + room_h - 18
            bar_w = room_w - 10
            bar_h = 8
            pct = system.maintenance_level / 100.0
            fill_color = HULL_GREEN if pct > 0.5 else AMBER if pct > 0.25 else RED_ALERT
            pygame.draw.rect(surface, (30, 30, 40), (rx + 5, bar_y, bar_w, bar_h))
            pygame.draw.rect(surface, fill_color, (rx + 5, bar_y, int(bar_w * pct), bar_h))

            pct_text = f"{system.maintenance_level:.0f}%"
            pct_surf = self.font_small.render(pct_text, True, fill_color)
            surface.blit(pct_surf, (rx + 5, ry + room_h - 34))

    def _draw_system_list(self, surface: pygame.Surface) -> None:
        list_x = SCREEN_WIDTH - 310
        list_y = 100

        header = self.font_info.render("SYSTEMS", True, AMBER)
        surface.blit(header, (list_x, list_y))

        for i, system in enumerate(self.systems):
            sy = list_y + 28 + i * 28
            is_selected = i == self.selected_index

            prefix = "▸" if is_selected else " "
            name_color = WHITE if is_selected else LIGHT_GREY
            name_surf = self.font_small.render(f"{prefix} {system.name}", True, name_color)
            surface.blit(name_surf, (list_x, sy))

            pct = system.maintenance_level
            status_color = HULL_GREEN if pct > 50 else AMBER if pct > 25 else RED_ALERT
            status_surf = self.font_small.render(f"{pct:.0f}%", True, status_color)
            surface.blit(status_surf, (list_x + 220, sy))

    def _draw_system_detail(self, surface: pygame.Surface, system: ShipSystem) -> None:
        panel_x = SCREEN_WIDTH - 310
        panel_y = 350
        panel_w = 295
        panel_h = 220

        bg = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        bg.fill(PANEL_BG)
        surface.blit(bg, (panel_x, panel_y))
        pygame.draw.rect(surface, PANEL_BORDER, (panel_x, panel_y, panel_w, panel_h), 1, border_radius=4)

        name_surf = self.font_name.render(system.name, True, AMBER)
        surface.blit(name_surf, (panel_x + 10, panel_y + 8))

        desc_surf = self.font_small.render(system.description[:50], True, LIGHT_GREY)
        surface.blit(desc_surf, (panel_x + 10, panel_y + 34))

        maint_text = f"Maintenance: {system.maintenance_level:.1f}%"
        pct = system.maintenance_level
        maint_color = HULL_GREEN if pct > 50 else AMBER if pct > 25 else RED_ALERT
        maint_surf = self.font_info.render(maint_text, True, maint_color)
        surface.blit(maint_surf, (panel_x + 10, panel_y + 58))

        eff = system.effectiveness * 100
        eff_surf = self.font_info.render(f"Effectiveness: {eff:.0f}%", True, CYAN)
        surface.blit(eff_surf, (panel_x + 10, panel_y + 80))

        tier_text = f"Tier: {'★' * system.upgrade_tier}{'☆' * (5 - system.upgrade_tier)}"
        tier_surf = self.font_info.render(tier_text, True, AMBER)
        surface.blit(tier_surf, (panel_x + 10, panel_y + 102))

        comp_y = panel_y + 128
        comp_header = self.font_small.render("Components:", True, LIGHT_GREY)
        surface.blit(comp_header, (panel_x + 10, comp_y))
        for j, comp in enumerate(system.components[:3]):
            cy = comp_y + 18 + j * 16
            q_color = {
                "standard": LIGHT_GREY,
                "alien": HULL_GREEN,
                "federation": CYAN,
            }.get(comp.quality.value, LIGHT_GREY)
            comp_text = f"  {comp.name} [{comp.quality.value}] {comp.condition:.0f}%"
            comp_surf = self.font_small.render(comp_text, True, q_color)
            surface.blit(comp_surf, (panel_x + 10, cy))

        cost = system.repair_cost(10)
        cost_text = f"Repair +10%: {cost['metal']} metal, {cost['energy']} energy"
        can_afford = (
            self.fleet.resources.metal >= cost["metal"]
            and self.fleet.resources.energy >= cost["energy"]
        )
        cost_color = HULL_GREEN if can_afford else RED_ALERT
        cost_surf = self.font_small.render(cost_text, True, cost_color)
        surface.blit(cost_surf, (panel_x + 10, panel_y + panel_h - 22))

    def _repair_selected(self) -> None:
        if self.selected_index >= len(self.systems):
            return
        system = self.systems[self.selected_index]
        if system.maintenance_level >= 100:
            self._message = f"{system.name} is already at full maintenance."
            self._message_color = LIGHT_GREY
            self._message_timer = 2.0
            return

        cost = system.repair_cost(10)
        if (self.fleet.resources.metal >= cost["metal"]
                and self.fleet.resources.energy >= cost["energy"]):
            self.fleet.resources.metal -= cost["metal"]
            self.fleet.resources.energy -= cost["energy"]
            system.repair(10)
            self._message = f"Repaired {system.name} (+10%)"
            self._message_color = HULL_GREEN
            self._message_timer = 2.0
        else:
            self._message = "Not enough resources!"
            self._message_color = RED_ALERT
            self._message_timer = 2.0

    # ------------------------------------------------------------------
    # FLEET TAB
    # ------------------------------------------------------------------

    def _draw_fleet_tab(self, surface: pygame.Surface) -> None:
        # Resource bar
        self._draw_resource_bar(surface)

        if self.fleet_mode == "list":
            self._draw_ship_list(surface)
            self._draw_ship_detail(surface)
        elif self.fleet_mode == "build":
            self._draw_build_menu(surface)
        elif self.fleet_mode == "equip":
            self._draw_equip_menu(surface)

    def _draw_resource_bar(self, surface: pygame.Surface) -> None:
        y = 95
        items = [
            (f"Metal: {self.fleet.resources.metal:,}", METAL_COLOR),
            (f"Energy: {self.fleet.resources.energy:,}", ENERGY_COLOR),
            (f"Rare: {self.fleet.resources.rare_materials:,}", RARE_COLOR),
            (f"Ships: {self.fleet.total_ships}/{self.fleet.mothership.hangar_capacity}", CYAN),
        ]
        x = 30
        for text, color in items:
            surf = self.font_info.render(text, True, color)
            surface.blit(surf, (x, y))
            x += surf.get_width() + 30

    def _draw_ship_list(self, surface: pygame.Surface) -> None:
        x, y0 = 20, 120
        header = self.font_name.render("Fleet Ships", True, WHITE)
        surface.blit(header, (x, y0))

        ships = self.fleet.ships
        visible_start = max(0, self.fleet_ship_idx - 12)
        for i in range(visible_start, min(len(ships), visible_start + 24)):
            ship = ships[i]
            y = y0 + 30 + (i - visible_start) * 24
            selected = i == self.fleet_ship_idx

            if selected:
                pygame.draw.rect(surface, (30, 50, 80), (x, y - 2, 360, 22), border_radius=3)

            color = WHITE if selected else LIGHT_GREY
            label = f"{ship.name} ({ship.display_name})"
            surf = self.font_small.render(label, True, color)
            surface.blit(surf, (x + 5, y))

            hull_pct = ship.hull / ship.max_hull
            bar_x = x + 290
            bar_w = 60
            bar_h = 6
            bar_y = y + 7
            pygame.draw.rect(surface, (30, 30, 45), (bar_x, bar_y, bar_w, bar_h), border_radius=3)
            fill_color = HULL_GREEN if hull_pct > 0.5 else AMBER if hull_pct > 0.25 else RED_ALERT
            pygame.draw.rect(surface, fill_color, (bar_x, bar_y, int(bar_w * hull_pct), bar_h), border_radius=3)

        if not ships:
            empty = self.font_info.render("No ships. Press B to build.", True, LIGHT_GREY)
            surface.blit(empty, (x + 10, y0 + 50))

    def _draw_ship_detail(self, surface: pygame.Surface) -> None:
        ships = self.fleet.ships
        if not ships:
            return
        ship = ships[self.fleet_ship_idx]
        x = 420
        y0 = 120

        name_surf = self.font_name.render(ship.name, True, AMBER)
        surface.blit(name_surf, (x, y0))

        cls_surf = self.font_info.render(f"Class: {ship.display_name}", True, LIGHT_GREY)
        surface.blit(cls_surf, (x, y0 + 28))

        y = y0 + 55
        stats = [
            ("Hull", f"{ship.hull}/{ship.max_hull}", HULL_GREEN),
            ("Armor", f"{ship.armor}", SHIELD_BLUE),
            ("Role", "Combat" if ship.is_combat else ship.ship_class.value.title(), WHITE),
        ]
        for label, val, color in stats:
            lbl = self.font_small.render(f"{label}:", True, LIGHT_GREY)
            surface.blit(lbl, (x, y))
            val_surf = self.font_small.render(val, True, color)
            surface.blit(val_surf, (x + 120, y))
            y += 20

        # Weapon slots
        y += 8
        wpn_header = self.font_name.render("Weapons", True, WHITE)
        surface.blit(wpn_header, (x, y))
        y += 26

        if not ship.weapon_slots:
            no_wpn = self.font_small.render("No weapon mounts (non-combat)", True, LIGHT_GREY)
            surface.blit(no_wpn, (x, y))
        else:
            for slot in ship.weapon_slots:
                size_label = slot.size.value.upper()
                equipped = slot.equipped or "— empty —"
                color = CYAN if slot.equipped else LIGHT_GREY
                text = f"[{size_label}] {equipped}"
                surf = self.font_small.render(text, True, color)
                surface.blit(surf, (x + 10, y))
                y += 20

        # Non-combat role bonus
        if not ship.is_combat:
            y += 10
            role_texts = {
                ShipClass.SCOUT: f"Sensor boost: {self.fleet.scout_bonus:.1f}x",
                ShipClass.MINER: f"Mining boost: {self.fleet.mining_bonus:.1f}x",
                ShipClass.TRANSPORT: f"Extra capacity: +{self.fleet.transport_capacity:,}",
            }
            role = role_texts.get(ship.ship_class, "")
            if role:
                surf = self.font_small.render(role, True, AMBER)
                surface.blit(surf, (x, y))

    def _draw_build_menu(self, surface: pygame.Surface) -> None:
        x, y0 = 60, 120
        header = self.font_name.render("BUILD SHIP", True, AMBER)
        surface.blit(header, (x, y0))

        cap_text = f"Hangar: {self.fleet.total_ships}/{self.fleet.mothership.hangar_capacity}"
        cap_surf = self.font_info.render(cap_text, True, CYAN)
        surface.blit(cap_surf, (x + 200, y0 + 4))

        y = y0 + 35
        for i, sc in enumerate(BUILDABLE_CLASSES):
            stats = SHIP_CLASS_STATS[sc]
            selected = i == self.build_cursor
            can_afford = self.fleet.can_build(sc)

            if selected:
                pygame.draw.rect(surface, (30, 50, 80), (x - 5, y - 2, 850, 24), border_radius=3)

            name = sc.value.replace("_", " ").title()
            cost_text = f"M:{stats['cost_metal']}  E:{stats['cost_energy']}  R:{stats['cost_rare']}"
            hull_text = f"Hull:{stats['hull']}  Armor:{stats['armor']}  Slots:{len(stats['slots'])}"

            name_color = WHITE if selected and can_afford else AMBER if can_afford else RED_ALERT
            name_surf = self.font_small.render(name, True, name_color)
            surface.blit(name_surf, (x, y))

            cost_color = LIGHT_GREY if can_afford else (80, 50, 50)
            cost_surf = self.font_small.render(cost_text, True, cost_color)
            surface.blit(cost_surf, (x + 160, y))

            hull_surf = self.font_small.render(hull_text, True, LIGHT_GREY)
            surface.blit(hull_surf, (x + 420, y))

            y += 24

    def _draw_equip_menu(self, surface: pygame.Surface) -> None:
        ships = self.fleet.ships
        if not ships:
            return
        ship = ships[self.fleet_ship_idx]
        if not ship.weapon_slots:
            return

        x, y0 = 60, 120
        header = self.font_name.render(f"EQUIP — {ship.name}", True, AMBER)
        surface.blit(header, (x, y0))

        y = y0 + 35
        for i, slot in enumerate(ship.weapon_slots):
            selected_slot = i == self.equip_slot_idx
            size_label = slot.size.value.upper()
            equipped = slot.equipped or "— empty —"

            if selected_slot:
                pygame.draw.rect(surface, (30, 50, 80), (x - 5, y - 2, 850, 24), border_radius=3)

            color = WHITE if selected_slot else LIGHT_GREY
            text = f"Slot {i + 1} [{size_label}]: {equipped}"
            surf = self.font_small.render(text, True, color)
            surface.blit(surf, (x, y))

            if selected_slot:
                available = weapons_for_size(slot.size.value)
                if available:
                    wpn_y = y + 24
                    for j, wpn in enumerate(available):
                        is_wpn_sel = j == self.equip_weapon_idx
                        r = self.fleet.resources
                        can_afford = (
                            r.metal >= wpn.build_cost_metal
                            and r.energy >= wpn.build_cost_energy
                            and r.rare_materials >= wpn.build_cost_rare
                        )

                        prefix = "►" if is_wpn_sel else " "
                        cost = f"M:{wpn.build_cost_metal} E:{wpn.build_cost_energy} R:{wpn.build_cost_rare}"
                        text = f"  {prefix} {wpn.name} — DMG:{wpn.damage} ACC:{int(wpn.accuracy*100)}% — {cost}"

                        wpn_color = CYAN if is_wpn_sel and can_afford else LIGHT_GREY if can_afford else (80, 50, 50)
                        surf = self.font_small.render(text, True, wpn_color)
                        surface.blit(surf, (x + 20, wpn_y))
                        wpn_y += 20
                    y = wpn_y + 4
                else:
                    no_wpn = self.font_small.render("  No weapons for this size", True, LIGHT_GREY)
                    surface.blit(no_wpn, (x + 20, y + 24))
                    y += 46
            else:
                y += 24
