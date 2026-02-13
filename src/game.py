"""Hollowed Stars — main game module (state router)."""

from __future__ import annotations

import random
import sys

import pygame

from .constants import AMBER, CYAN, DARK_GREY, FPS, HULL_GREEN, LIGHT_GREY, RED_ALERT, SCREEN_HEIGHT, SCREEN_WIDTH, TITLE, WHITE
from .models.combat import CombatEngine, EnemyFleet, generate_enemy_fleet
from .models.events import get_event_for_object_type
from .models.galaxy import Galaxy
from .models.mothership_systems import ShipSystem, apply_ftl_decay, create_default_systems
from .models.quest import LoreEntry, QuestFlag, QuestState
from .models.ships import SIGNAL_OF_DAWN, Fleet
from .screens.combat import CombatScreen
from .screens.event_dialog import EventDialogScreen
from .screens.fleet_screen import FleetScreen
from .screens.formation_screen import FormationScreen
from .screens.mothership import MothershipScreen
from .screens.ship_select import ShipSelectScreen
from .screens.star_map import StarMapScreen
from .screens.system_view import SystemViewScreen
from .screens.title import TitleScreen
from .states import GameState
from .ui.hud import HUD
from .ui.starfield import StarField


class Game:
    """Core game class — routes state to screen objects."""

    def __init__(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()
        self.running = True
        self.state = GameState.TITLE

        # Shared components
        self.starfield = StarField()
        self.hud = HUD()

        # Game data (initialized during ship select / galaxy gen)
        self.fleet: Fleet | None = None
        self.galaxy: Galaxy | None = None
        self.mothership_systems: list[ShipSystem] = []
        self.quest_state = QuestState()

        # Screens
        self.title_screen = TitleScreen()
        self.ship_select_screen = ShipSelectScreen()
        self.star_map_screen: StarMapScreen | None = None
        self.system_view_screen: SystemViewScreen | None = None
        self.combat_screen: CombatScreen | None = None
        self.event_dialog_screen: EventDialogScreen | None = None
        self.mothership_screen: MothershipScreen | None = None
        self.fleet_screen: FleetScreen | None = None
        self.formation_screen: FormationScreen | None = None

        # Pending combat from events (stored so formation screen can route to it)
        self._pending_enemy: EnemyFleet | None = None
        self._pending_combat_quest_flag: str = ""

        # Cryosleep overlay state
        self._cryosleep_active = False
        self._cryosleep_timer = 0.0
        self._cryosleep_years = 0
        self._cryosleep_decay_msgs: list[str] = []
        self._cryosleep_colonist_loss = 0

        # Game over
        self.ending_type = None
        self._game_over_font = None
        self._game_over_timer = 0.0

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self._handle_events()
            self._update(dt)
            self._draw(dt)

        pygame.quit()
        sys.exit()

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return

            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self._handle_escape()
                continue

            # Route to active screen
            if self.state == GameState.TITLE:
                self.title_screen.handle_events(event)
            elif self.state == GameState.SHIP_SELECT:
                self.ship_select_screen.handle_events(event)
            elif self.state == GameState.STAR_MAP and self.star_map_screen:
                self.star_map_screen.handle_events(event)
            elif self.state == GameState.SYSTEM_VIEW and self.system_view_screen:
                self.system_view_screen.handle_events(event)
            elif self.state == GameState.COMBAT and self.combat_screen:
                self.combat_screen.handle_events(event)
            elif self.state == GameState.EVENT_DIALOG and self.event_dialog_screen:
                self.event_dialog_screen.handle_events(event)
            elif self.state == GameState.MOTHERSHIP and self.mothership_screen:
                self.mothership_screen.handle_events(event)
            elif self.state == GameState.FLEET_MANAGEMENT and self.fleet_screen:
                self.fleet_screen.handle_events(event)
            elif self.state == GameState.FORMATION_SETUP and self.formation_screen:
                self.formation_screen.handle_events(event)
            elif self.state == GameState.GAME_OVER:
                if event.type == pygame.KEYDOWN:
                    self.running = False

    def _handle_escape(self) -> None:
        """Navigate back through screens, or quit from title."""
        if self.state == GameState.TITLE:
            self.running = False
        elif self.state == GameState.SHIP_SELECT:
            self.state = GameState.TITLE
            self.title_screen = TitleScreen()
        elif self.state == GameState.SYSTEM_VIEW:
            self.state = GameState.STAR_MAP
        elif self.state == GameState.STAR_MAP:
            self.state = GameState.SHIP_SELECT
            self.ship_select_screen = ShipSelectScreen()
        elif self.state == GameState.MOTHERSHIP:
            self.state = GameState.STAR_MAP
        elif self.state == GameState.FLEET_MANAGEMENT:
            self.state = GameState.STAR_MAP
        elif self.state == GameState.COMBAT:
            pass  # Can't escape from combat
        elif self.state == GameState.EVENT_DIALOG:
            pass  # Can't escape from event

    def _update(self, dt: float) -> None:
        self.starfield.update(dt)

        if self.state == GameState.TITLE:
            self.title_screen.update(dt)
            if self.title_screen.next_state:
                self.state = self.title_screen.next_state
                self.title_screen.next_state = None

        elif self.state == GameState.SHIP_SELECT:
            self.ship_select_screen.update(dt)
            if self.ship_select_screen.next_state:
                self.fleet = self.ship_select_screen.chosen_fleet
                self.galaxy = Galaxy()
                self.mothership_systems = create_default_systems()
                self.quest_state = QuestState()
                self.star_map_screen = StarMapScreen(self.galaxy)
                self.state = self.ship_select_screen.next_state
                self.ship_select_screen.next_state = None

        elif self.state == GameState.STAR_MAP and self.star_map_screen:
            # Handle cryosleep overlay
            if self._cryosleep_active:
                self._cryosleep_timer += dt
                if self._cryosleep_timer > 4.0:
                    self._cryosleep_active = False
                return

            self.star_map_screen.update(dt)
            if self.star_map_screen.next_state:
                if self.star_map_screen.next_state == GameState.SYSTEM_VIEW:
                    self.system_view_screen = SystemViewScreen(
                        self.galaxy, self.fleet, self.quest_state,
                    )

                    # Apply FTL maintenance decay when traveling
                    self._cryosleep_decay_msgs = []
                    if self.mothership_systems:
                        warnings = apply_ftl_decay(self.mothership_systems)
                        if warnings:
                            self._cryosleep_decay_msgs = [str(w) for w in warnings]

                    # Passive sublight decay (PLAN.md: maintenance goes down with use and time)
                    for sys in self.mothership_systems:
                        sys.maintenance_level = max(
                            0.0, sys.maintenance_level - 0.02,
                        )

                    # Cryosleep: years pass, colonists may die
                    self._cryosleep_years = random.randint(200, 2000)
                    cryo_death_rate = random.uniform(0.001, 0.01)
                    self._cryosleep_colonist_loss = int(self.fleet.colonists * cryo_death_rate)
                    self.fleet.colonists = max(0, self.fleet.colonists - self._cryosleep_colonist_loss)
                    self._cryosleep_active = True
                    self._cryosleep_timer = 0.0

                elif self.star_map_screen.next_state == GameState.MOTHERSHIP:
                    self.mothership_screen = MothershipScreen(self.fleet, self.mothership_systems)

                elif self.star_map_screen.next_state == GameState.FLEET_MANAGEMENT:
                    self.fleet_screen = FleetScreen(self.fleet)

                self.state = self.star_map_screen.next_state
                self.star_map_screen.next_state = None

        elif self.state == GameState.SYSTEM_VIEW and self.system_view_screen:
            self.system_view_screen.update(dt)
            if self.system_view_screen.next_state:
                next_st = self.system_view_screen.next_state
                self.system_view_screen.next_state = None

                if next_st == GameState.EVENT_DIALOG and self.system_view_screen.pending_event:
                    self.event_dialog_screen = EventDialogScreen(
                        self.system_view_screen.pending_event,
                        self.fleet,
                    )
                    self.state = GameState.EVENT_DIALOG
                elif next_st == GameState.STAR_MAP:
                    self.state = GameState.STAR_MAP
                else:
                    self.state = next_st

        elif self.state == GameState.COMBAT and self.combat_screen:
            self.combat_screen.update(dt)
            if self.combat_screen.next_state:
                # Apply combat results (fleet losses, loot)
                if self.combat_screen.engine and self.fleet:
                    self.combat_screen.engine.apply_results_to_fleet()

                    # Process pending combat quest flag (e.g. defeated Earth defense)
                    if self._pending_combat_quest_flag:
                        self._process_quest_flag(self._pending_combat_quest_flag)
                        self._pending_combat_quest_flag = ""

                self.state = self.combat_screen.next_state
                self.combat_screen.next_state = None
                self.combat_screen = None
                self._check_game_over()

        elif self.state == GameState.EVENT_DIALOG and self.event_dialog_screen:
            self.event_dialog_screen.update(dt)
            if self.event_dialog_screen.next_state:
                # Process quest flag from the resolved outcome
                self._process_quest_flag(self.event_dialog_screen.resolved_quest_flag)

                # Check if event triggered combat
                if self.event_dialog_screen.trigger_combat and self.fleet:
                    enemy = generate_enemy_fleet(
                        self.event_dialog_screen.combat_danger,
                        self.event_dialog_screen.combat_is_federation,
                    )
                    self._pending_enemy = enemy
                    self._pending_combat_quest_flag = self.event_dialog_screen.resolved_quest_flag
                    # Route through formation setup before combat
                    self.formation_screen = FormationScreen()
                    self.formation_screen.setup(self.fleet)
                    self.state = GameState.FORMATION_SETUP
                else:
                    # Check for colony establishment
                    if hasattr(self.event_dialog_screen, 'colony_established') and self.event_dialog_screen.colony_established:
                        self.quest_state.colonies_established += 1
                    self.state = GameState.SYSTEM_VIEW
                self.event_dialog_screen = None
                self._check_game_over()

        elif self.state == GameState.MOTHERSHIP and self.mothership_screen:
            self.mothership_screen.update(dt)
            if self.mothership_screen.next_state:
                self.state = self.mothership_screen.next_state
                self.mothership_screen.next_state = None

        elif self.state == GameState.FLEET_MANAGEMENT and self.fleet_screen:
            self.fleet_screen.update(dt)
            if self.fleet_screen.next_state:
                self.state = self.fleet_screen.next_state
                self.fleet_screen.next_state = None

        elif self.state == GameState.FORMATION_SETUP and self.formation_screen:
            self.formation_screen.update(dt)
            if self.formation_screen.next_state == GameState.COMBAT:
                # Formation confirmed — start combat
                if self._pending_enemy and self.fleet:
                    engine = CombatEngine(self.fleet, self._pending_enemy)
                    self.combat_screen = CombatScreen(engine)
                    self.state = GameState.COMBAT
                    self._pending_enemy = None
                else:
                    self.state = GameState.SYSTEM_VIEW
                self.formation_screen = None

        elif self.state == GameState.GAME_OVER:
            self._game_over_timer += dt

    def _draw(self, dt: float) -> None:
        self.screen.fill(DARK_GREY)
        self.starfield.draw(self.screen)

        if self.state == GameState.TITLE:
            self.title_screen.draw(self.screen)
        elif self.state == GameState.SHIP_SELECT:
            self.ship_select_screen.draw(self.screen)
        elif self.state == GameState.STAR_MAP and self.star_map_screen:
            self.star_map_screen.draw(self.screen)
            if self.fleet:
                self.hud.draw(self.screen, self.fleet)
            self._draw_star_map_hints()
            # Cryosleep overlay on top
            if self._cryosleep_active:
                self._draw_cryosleep_overlay()
        elif self.state == GameState.SYSTEM_VIEW and self.system_view_screen:
            self.system_view_screen.draw(self.screen)
            if self.fleet:
                self.hud.draw(self.screen, self.fleet)
        elif self.state == GameState.COMBAT and self.combat_screen:
            self.combat_screen.draw(self.screen)
        elif self.state == GameState.EVENT_DIALOG and self.event_dialog_screen:
            # Draw system view behind the dialog
            if self.system_view_screen:
                self.system_view_screen.draw(self.screen)
            self.event_dialog_screen.draw(self.screen)
        elif self.state == GameState.MOTHERSHIP and self.mothership_screen:
            self.mothership_screen.draw(self.screen)
            if self.fleet:
                self.hud.draw(self.screen, self.fleet)
        elif self.state == GameState.FLEET_MANAGEMENT and self.fleet_screen:
            self.fleet_screen.draw(self.screen)
            if self.fleet:
                self.hud.draw(self.screen, self.fleet)
        elif self.state == GameState.FORMATION_SETUP and self.formation_screen:
            self.formation_screen.draw(self.screen)
            if self.fleet:
                self.hud.draw(self.screen, self.fleet)
        elif self.state == GameState.GAME_OVER:
            self._draw_game_over()

        pygame.display.flip()

    # ------------------------------------------------------------------
    # Star map keybinds hint
    # ------------------------------------------------------------------

    def _draw_star_map_hints(self) -> None:
        """Show keybind hints for star map screens."""
        font = pygame.font.Font(None, 22)
        hint = font.render("TAB — Mothership    F — Fleet Management", True, LIGHT_GREY)
        self.screen.blit(hint, (10, SCREEN_HEIGHT - 25))

    def _draw_cryosleep_overlay(self) -> None:
        """Draw the FTL cryosleep narrative overlay."""
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        alpha = min(220, int(self._cryosleep_timer * 200))
        overlay.fill((5, 5, 15, alpha))
        self.screen.blit(overlay, (0, 0))

        if self._cryosleep_timer < 0.5:
            return  # Fade in

        font_big = pygame.font.Font(None, 56)
        font_med = pygame.font.Font(None, 30)
        font_small = pygame.font.Font(None, 24)

        # Title
        title = font_big.render("C R Y O S L E E P", True, CYAN)
        self.screen.blit(title, ((SCREEN_WIDTH - title.get_width()) // 2, 150))

        # Years elapsed
        years_text = font_med.render(f"You awaken. {self._cryosleep_years:,} years have passed.", True, WHITE)
        self.screen.blit(years_text, ((SCREEN_WIDTH - years_text.get_width()) // 2, 230))

        # Colonist losses
        y = 280
        if self._cryosleep_colonist_loss > 0:
            loss_text = font_small.render(
                f"Cryo failures: {self._cryosleep_colonist_loss:,} colonists lost",
                True, RED_ALERT,
            )
            self.screen.blit(loss_text, ((SCREEN_WIDTH - loss_text.get_width()) // 2, y))
            y += 30

        # Maintenance decay
        if self._cryosleep_decay_msgs:
            decay_header = font_small.render("Systems degraded during transit:", True, AMBER)
            self.screen.blit(decay_header, ((SCREEN_WIDTH - decay_header.get_width()) // 2, y))
            y += 26
            for msg in self._cryosleep_decay_msgs[:5]:
                msg_surf = font_small.render(f"  • {msg}", True, LIGHT_GREY)
                self.screen.blit(msg_surf, ((SCREEN_WIDTH - msg_surf.get_width()) // 2, y))
                y += 22

        # Continue hint
        if self._cryosleep_timer > 2.0:
            hint = font_small.render("Awakening...", True, LIGHT_GREY)
            self.screen.blit(hint, ((SCREEN_WIDTH - hint.get_width()) // 2, SCREEN_HEIGHT - 80))

    # ------------------------------------------------------------------
    # Quest progression
    # ------------------------------------------------------------------

    # Map event outcome quest_flag strings to QuestFlag enum values
    _QUEST_FLAG_MAP: dict[str, QuestFlag] = {
        "class_4_id_code": QuestFlag.CLASS_4_ID_CODE,
        "defeated_earth_defense": QuestFlag.DEFEATED_EARTH_DEFENSE,
        "discovered_earth": QuestFlag.DISCOVERED_EARTH,
        "reached_gateway": QuestFlag.REACHED_GATEWAY,
        "defeated_ninurta": QuestFlag.DEFEATED_NINURTA,
        "lore_old_federation": QuestFlag.LORE_FRAGMENT_1,
        "lore_prison_station": QuestFlag.LORE_FRAGMENT_2,
        "lore_gateway_project": QuestFlag.LORE_FRAGMENT_3,
        "lore_ninurta_origin": QuestFlag.LORE_FRAGMENT_4,
        "lore_exiles": QuestFlag.LORE_FRAGMENT_5,
    }

    def _process_quest_flag(self, flag_str: str) -> None:
        """Process a quest flag string from an event outcome."""
        if not flag_str:
            return

        flag = self._QUEST_FLAG_MAP.get(flag_str)
        if flag is None:
            return

        self.quest_state.set_flag(flag)

        # Lore fragments — create a LoreEntry
        if flag_str.startswith("lore_"):
            lore_data = {
                "lore_old_federation": (
                    "The Fall of the Federation",
                    "The Old Federation collapsed 5000 years ago in a war against Ninurta.",
                ),
                "lore_prison_station": (
                    "The Prison Station",
                    "Your prison station was once a Federation military outpost.",
                ),
                "lore_gateway_project": (
                    "Project Gateway",
                    "The Trans-Galactic Gateway was the Federation's greatest achievement.",
                ),
                "lore_ninurta_origin": (
                    "The Entity Called Ninurta",
                    "Ninurta is a malevolent entity that consumed the galaxy's life.",
                ),
                "lore_exiles": (
                    "The Exiles' Legacy",
                    "Not all Federation survivors perished. Some became the exiles.",
                ),
            }
            title, text = lore_data.get(flag_str, ("Unknown Fragment", "A fragment of lost history."))
            self.quest_state.add_lore(LoreEntry(title=title, text=text, quest_flag=flag))

        # Signal of Dawn unlock chain:
        # Defeating Earth defense → unlock Signal of Dawn → swap mothership
        if flag == QuestFlag.DEFEATED_EARTH_DEFENSE:
            self.quest_state.set_flag(QuestFlag.UNLOCKED_SIGNAL_OF_DAWN)
            self.quest_state.set_flag(QuestFlag.CLASS_1_ID_CODE)

            # Swap mothership — preserve fleet, resources, colonists
            if self.fleet:
                old = self.fleet.mothership
                new_ms = SIGNAL_OF_DAWN
                # Copy dynamic state
                new_ms.hull = new_ms.max_hull
                new_ms.power = new_ms.max_power
                self.fleet.mothership = new_ms
                # Keep colonists (capped at new capacity)
                self.fleet.colonists = min(
                    self.fleet.colonists,
                    self.fleet.effective_colonist_capacity,
                )

        # True ending: defeating Ninurta means crossing to Andromeda
        if flag == QuestFlag.DEFEATED_NINURTA:
            self.quest_state.set_flag(QuestFlag.CROSSED_TO_ANDROMEDA)

    # ------------------------------------------------------------------
    # Game over
    # ------------------------------------------------------------------

    def _check_game_over(self) -> None:
        """Check if any ending condition is met."""
        if not self.fleet:
            return

        fleet_destroyed = self.fleet.mothership.hull <= 0
        ending = self.quest_state.check_ending(self.fleet.colonists, fleet_destroyed)

        if ending is not None:
            self.ending_type = ending
            self.state = GameState.GAME_OVER
            self._game_over_timer = 0.0

    def _draw_game_over(self) -> None:
        """Draw the game over screen."""
        if self._game_over_font is None:
            self._game_over_font = pygame.font.Font(None, 60)

        from .models.quest import EndingType

        endings = {
            EndingType.FLEET_DESTROYED: ("YOUR FLEET HAS BEEN DESTROYED", RED_ALERT,
                "The last hope of humanity drifts silently through the void..."),
            EndingType.COLONIST_COLLAPSE: ("COLONIST POPULATION CRITICAL", RED_ALERT,
                "With fewer than 15,000 colonists, humanity cannot sustain itself."),
            EndingType.COLONY_SUCCESS: ("A NEW HOME", HULL_GREEN,
                "Against all odds, humanity has found its place among the stars."),
            EndingType.TRUE_ENDING: ("BEYOND THE GATEWAY", CYAN,
                "Ninurta is defeated. Through the gateway, Andromeda awaits. Humanity endures."),
        }

        title, color, desc = endings.get(
            self.ending_type,
            ("GAME OVER", RED_ALERT, "Your journey has ended."),
        )

        # Title
        title_surf = self._game_over_font.render(title, True, color)
        title_rect = title_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 40))
        self.screen.blit(title_surf, title_rect)

        # Description
        font_desc = pygame.font.Font(None, 30)
        desc_surf = font_desc.render(desc, True, LIGHT_GREY)
        desc_rect = desc_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 20))
        self.screen.blit(desc_surf, desc_rect)

        # Continue prompt
        if self._game_over_timer > 2.0:
            font_hint = pygame.font.Font(None, 24)
            hint = font_hint.render("Press any key to exit", True, LIGHT_GREY)
            hint_rect = hint.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 70))
            self.screen.blit(hint, hint_rect)


def main() -> None:
    """Entry point for the hollowed-stars command."""
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
