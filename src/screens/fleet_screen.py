"""Fleet management screen — build, scrap, equip ships."""

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
    RARE_COLOR,
    ENERGY_COLOR,
    METAL_COLOR,
    RED_ALERT,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    SHIELD_BLUE,
    WHITE,
)
from ..models.ships import (
    Fleet,
    FleetShip,
    ShipClass,
    SHIP_CLASS_STATS,
    WeaponSize,
)
from ..models.weapons import CRAFTABLE_WEAPONS, Weapon, weapons_for_size
from ..states import GameState


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


class FleetScreen:
    """Manage fleet: build ships, equip weapons, assign formations."""

    def __init__(self, fleet: Fleet) -> None:
        self.fleet = fleet
        self.next_state: GameState | None = None

        # UI state
        self.mode = "list"  # "list", "build", "equip"
        self.selected_ship_idx = 0
        self.build_cursor = 0
        self.equip_slot_idx = 0
        self.equip_weapon_idx = 0
        self.timer = 0.0

        # Fonts
        self.font_title = pygame.font.Font(None, 48)
        self.font_name = pygame.font.Font(None, 32)
        self.font_body = pygame.font.Font(None, 24)
        self.font_stat = pygame.font.Font(None, 22)
        self.font_hint = pygame.font.Font(None, 22)

    def handle_events(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return

        if self.mode == "list":
            self._handle_list(event.key)
        elif self.mode == "build":
            self._handle_build(event.key)
        elif self.mode == "equip":
            self._handle_equip(event.key)

    def _handle_list(self, key: int) -> None:
        ships = self.fleet.ships
        if key in (pygame.K_UP, pygame.K_w):
            if ships:
                self.selected_ship_idx = (self.selected_ship_idx - 1) % len(ships)
        elif key in (pygame.K_DOWN, pygame.K_s):
            if ships:
                self.selected_ship_idx = (self.selected_ship_idx + 1) % len(ships)
        elif key == pygame.K_b:
            self.mode = "build"
            self.build_cursor = 0
        elif key == pygame.K_e and ships:
            self.mode = "equip"
            self.equip_slot_idx = 0
            self.equip_weapon_idx = 0
        elif key == pygame.K_x and ships:
            # Scrap selected ship
            ship = ships[self.selected_ship_idx]
            self.fleet.scrap_ship(ship)
            if self.selected_ship_idx >= len(ships):
                self.selected_ship_idx = max(0, len(ships) - 1)
        elif key == pygame.K_ESCAPE:
            self.next_state = GameState.STAR_MAP

    def _handle_build(self, key: int) -> None:
        if key in (pygame.K_UP, pygame.K_w):
            self.build_cursor = (self.build_cursor - 1) % len(BUILDABLE_CLASSES)
        elif key in (pygame.K_DOWN, pygame.K_s):
            self.build_cursor = (self.build_cursor + 1) % len(BUILDABLE_CLASSES)
        elif key in (pygame.K_RETURN, pygame.K_SPACE):
            sc = BUILDABLE_CLASSES[self.build_cursor]
            self.fleet.build_ship(sc)
        elif key == pygame.K_ESCAPE:
            self.mode = "list"

    def _handle_equip(self, key: int) -> None:
        ships = self.fleet.ships
        if not ships:
            self.mode = "list"
            return
        ship = ships[self.selected_ship_idx]
        if not ship.weapon_slots:
            self.mode = "list"
            return

        slot = ship.weapon_slots[self.equip_slot_idx]
        available = weapons_for_size(slot.size.value)
        if not available:
            available = []

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
            # Check build cost
            r = self.fleet.resources
            if (r.metal >= wpn.build_cost_metal
                    and r.energy >= wpn.build_cost_energy
                    and r.rare_materials >= wpn.build_cost_rare):
                r.metal -= wpn.build_cost_metal
                r.energy -= wpn.build_cost_energy
                r.rare_materials -= wpn.build_cost_rare
                slot.equipped = wpn.name
        elif key == pygame.K_ESCAPE:
            self.mode = "list"

    def update(self, dt: float) -> None:
        self.timer += dt

    def draw(self, surface: pygame.Surface) -> None:
        # Background panel
        panel = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        panel.fill((10, 10, 20, 240))
        surface.blit(panel, (0, 0))

        # Title
        title = self.font_title.render("FLEET MANAGEMENT", True, AMBER)
        surface.blit(title, ((SCREEN_WIDTH - title.get_width()) // 2, 15))

        # Resources bar
        self._draw_resource_bar(surface)

        if self.mode == "list":
            self._draw_ship_list(surface)
            self._draw_ship_detail(surface)
            self._draw_list_hints(surface)
        elif self.mode == "build":
            self._draw_build_menu(surface)
        elif self.mode == "equip":
            self._draw_equip_menu(surface)

    def _draw_resource_bar(self, surface: pygame.Surface) -> None:
        y = 55
        items = [
            (f"Metal: {self.fleet.resources.metal:,}", METAL_COLOR),
            (f"Energy: {self.fleet.resources.energy:,}", ENERGY_COLOR),
            (f"Rare: {self.fleet.resources.rare_materials:,}", RARE_COLOR),
            (f"Ships: {self.fleet.total_ships}/{self.fleet.mothership.hangar_capacity}", CYAN),
        ]
        x = 30
        for text, color in items:
            surf = self.font_body.render(text, True, color)
            surface.blit(surf, (x, y))
            x += surf.get_width() + 40

    def _draw_ship_list(self, surface: pygame.Surface) -> None:
        """Left panel: list of fleet ships."""
        x, y0 = 20, 85
        header = self.font_name.render("Fleet Ships", True, WHITE)
        surface.blit(header, (x, y0))

        ships = self.fleet.ships
        visible_start = max(0, self.selected_ship_idx - 10)
        for i in range(visible_start, min(len(ships), visible_start + 20)):
            ship = ships[i]
            y = y0 + 35 + (i - visible_start) * 26
            selected = i == self.selected_ship_idx

            # Row background
            if selected:
                pygame.draw.rect(surface, (30, 50, 80), (x, y - 2, 350, 24), border_radius=3)

            # Name and class
            color = WHITE if selected else LIGHT_GREY
            label = f"{ship.name} ({ship.display_name})"
            surf = self.font_stat.render(label, True, color)
            surface.blit(surf, (x + 5, y))

            # Hull bar
            hull_pct = ship.hull / ship.max_hull
            bar_x = x + 280
            bar_w = 60
            bar_h = 6
            bar_y = y + 8
            pygame.draw.rect(surface, (30, 30, 45), (bar_x, bar_y, bar_w, bar_h), border_radius=3)
            fill_color = HULL_GREEN if hull_pct > 0.5 else AMBER if hull_pct > 0.25 else RED_ALERT
            pygame.draw.rect(surface, fill_color, (bar_x, bar_y, int(bar_w * hull_pct), bar_h), border_radius=3)

        if not ships:
            empty = self.font_body.render("No ships. Press B to build.", True, LIGHT_GREY)
            surface.blit(empty, (x + 10, y0 + 50))

    def _draw_ship_detail(self, surface: pygame.Surface) -> None:
        """Right panel: selected ship details."""
        ships = self.fleet.ships
        if not ships:
            return

        ship = ships[self.selected_ship_idx]
        x = 400
        y0 = 85

        # Name
        name_surf = self.font_name.render(ship.name, True, AMBER)
        surface.blit(name_surf, (x, y0))

        # Class
        cls_surf = self.font_body.render(f"Class: {ship.display_name}", True, LIGHT_GREY)
        surface.blit(cls_surf, (x, y0 + 32))

        # Stats
        y = y0 + 60
        stats = [
            ("Hull", f"{ship.hull}/{ship.max_hull}", HULL_GREEN),
            ("Armor", f"{ship.armor}", SHIELD_BLUE),
            ("Combat", "Yes" if ship.is_combat else "No", WHITE),
            ("Formation", f"Slot {ship.formation_slot}", WHITE),
        ]
        for label, val, color in stats:
            lbl = self.font_stat.render(f"{label}:", True, LIGHT_GREY)
            surface.blit(lbl, (x, y))
            val_surf = self.font_stat.render(val, True, color)
            surface.blit(val_surf, (x + 130, y))
            y += 22

        # Weapon slots
        y += 10
        wpn_header = self.font_name.render("Weapon Slots", True, WHITE)
        surface.blit(wpn_header, (x, y))
        y += 30

        if not ship.weapon_slots:
            no_wpn = self.font_stat.render("No weapon mounts (non-combat)", True, LIGHT_GREY)
            surface.blit(no_wpn, (x, y))
        else:
            for i, slot in enumerate(ship.weapon_slots):
                size_label = slot.size.value.upper()
                equipped = slot.equipped or "— empty —"
                color = CYAN if slot.equipped else LIGHT_GREY
                text = f"[{size_label}] {equipped}"
                surf = self.font_stat.render(text, True, color)
                surface.blit(surf, (x + 10, y))
                y += 22

        # Non-combat role info
        if not ship.is_combat:
            y += 15
            role_texts = {
                ShipClass.SCOUT: "Scouts boost sensor range by 20% each",
                ShipClass.MINER: "Miners boost resource yield by 25% each",
                ShipClass.TRANSPORT: "Transports add 50k colonist capacity each",
            }
            role = role_texts.get(ship.ship_class, "")
            if role:
                surf = self.font_stat.render(role, True, AMBER)
                surface.blit(surf, (x, y))

    def _draw_list_hints(self, surface: pygame.Surface) -> None:
        hints = "W/S Navigate  |  B Build  |  E Equip  |  X Scrap  |  ESC Back"
        surf = self.font_hint.render(hints, True, LIGHT_GREY)
        surface.blit(surf, ((SCREEN_WIDTH - surf.get_width()) // 2, SCREEN_HEIGHT - 30))

    def _draw_build_menu(self, surface: pygame.Surface) -> None:
        """Build ship overlay."""
        x, y0 = 80, 85
        header = self.font_name.render("BUILD SHIP", True, AMBER)
        surface.blit(header, (x, y0))

        cap_text = f"Hangar: {self.fleet.total_ships}/{self.fleet.mothership.hangar_capacity}"
        cap_surf = self.font_body.render(cap_text, True, CYAN)
        surface.blit(cap_surf, (x + 250, y0 + 4))

        y = y0 + 40
        for i, sc in enumerate(BUILDABLE_CLASSES):
            stats = SHIP_CLASS_STATS[sc]
            selected = i == self.build_cursor
            can_afford = self.fleet.can_build(sc)

            # Row background
            if selected:
                pygame.draw.rect(surface, (30, 50, 80), (x - 5, y - 2, 800, 24), border_radius=3)

            name = sc.value.replace("_", " ").title()
            cost_text = f"M:{stats['cost_metal']}  E:{stats['cost_energy']}  R:{stats['cost_rare']}"
            hull_text = f"Hull:{stats['hull']}  Armor:{stats['armor']}  Slots:{len(stats['slots'])}"

            name_color = AMBER if can_afford else RED_ALERT
            if selected:
                name_color = WHITE if can_afford else RED_ALERT

            name_surf = self.font_stat.render(name, True, name_color)
            surface.blit(name_surf, (x, y))

            cost_color = LIGHT_GREY if can_afford else (80, 50, 50)
            cost_surf = self.font_stat.render(cost_text, True, cost_color)
            surface.blit(cost_surf, (x + 180, y))

            hull_surf = self.font_stat.render(hull_text, True, LIGHT_GREY)
            surface.blit(hull_surf, (x + 480, y))

            y += 26

        # Hints
        hints = "W/S Navigate  |  ENTER Build  |  ESC Cancel"
        surf = self.font_hint.render(hints, True, LIGHT_GREY)
        surface.blit(surf, ((SCREEN_WIDTH - surf.get_width()) // 2, SCREEN_HEIGHT - 30))

    def _draw_equip_menu(self, surface: pygame.Surface) -> None:
        """Weapon equip overlay."""
        ships = self.fleet.ships
        if not ships:
            return
        ship = ships[self.selected_ship_idx]
        if not ship.weapon_slots:
            return

        x, y0 = 80, 85
        header = self.font_name.render(f"EQUIP WEAPONS — {ship.name}", True, AMBER)
        surface.blit(header, (x, y0))

        y = y0 + 40
        for i, slot in enumerate(ship.weapon_slots):
            selected_slot = i == self.equip_slot_idx
            size_label = slot.size.value.upper()
            equipped = slot.equipped or "— empty —"

            if selected_slot:
                pygame.draw.rect(surface, (30, 50, 80), (x - 5, y - 2, 800, 24), border_radius=3)

            color = WHITE if selected_slot else LIGHT_GREY
            text = f"Slot {i + 1} [{size_label}]: {equipped}"
            surf = self.font_stat.render(text, True, color)
            surface.blit(surf, (x, y))

            # Show available weapons for selected slot
            if selected_slot:
                available = weapons_for_size(slot.size.value)
                if available:
                    wpn_y = y + 26
                    for j, wpn in enumerate(available):
                        is_wpn_selected = j == self.equip_weapon_idx
                        r = self.fleet.resources
                        can_afford = (
                            r.metal >= wpn.build_cost_metal
                            and r.energy >= wpn.build_cost_energy
                            and r.rare_materials >= wpn.build_cost_rare
                        )

                        prefix = "►" if is_wpn_selected else " "
                        cost = f"M:{wpn.build_cost_metal} E:{wpn.build_cost_energy} R:{wpn.build_cost_rare}"
                        text = f"  {prefix} {wpn.name} — DMG:{wpn.damage} ACC:{int(wpn.accuracy*100)}% — {cost}"

                        wpn_color = CYAN if is_wpn_selected and can_afford else LIGHT_GREY if can_afford else (80, 50, 50)
                        surf = self.font_stat.render(text, True, wpn_color)
                        surface.blit(surf, (x + 20, wpn_y))
                        wpn_y += 20
                    y = wpn_y + 5
                else:
                    no_wpn = self.font_stat.render("  No weapons available for this size", True, LIGHT_GREY)
                    surface.blit(no_wpn, (x + 20, y + 26))
                    y += 50
            else:
                y += 26

        hints = "W/S Slot  |  A/D Weapon  |  ENTER Equip  |  ESC Cancel"
        surf = self.font_hint.render(hints, True, LIGHT_GREY)
        surface.blit(surf, ((SCREEN_WIDTH - surf.get_width()) // 2, SCREEN_HEIGHT - 30))
