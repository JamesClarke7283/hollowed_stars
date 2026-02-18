"""Hollowed Stars — main game module (state router)."""

from __future__ import annotations

import random
import sys

import pygame

from .constants import AMBER, CYAN, DARK_GREY, FPS, HULL_GREEN, LIGHT_GREY, RED_ALERT, SCREEN_HEIGHT, SCREEN_WIDTH, TITLE, WHITE
from .models.combat import CombatEngine, EnemyFleet, generate_enemy_fleet
from .models.events import get_event_for_object_type
from .models.galaxy import Galaxy, assign_factions_to_systems
from .models.diplomacy import Faction, generate_factions
from .models.mothership_systems import ShipSystem, apply_ftl_decay, create_default_systems
from .models.colony import ColonyManager
from .models.quest import LoreEntry, QuestFlag, QuestState
from .models.save import delete_save, load_game, save_game
from .models.ships import SIGNAL_OF_DAWN, Fleet
from .screens.combat import CombatScreen
from .screens.captains_log import CaptainsLogScreen
from .screens.colony_screen import ColonyScreen
from .screens.credits import CreditsScreen
from .screens.deep_survey import DeepSurveyScreen
from .screens.diplomacy import DiplomacyScreen
from .screens.event_dialog import EventDialogScreen
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
        self.formation_screen: FormationScreen | None = None
        self.captains_log_screen: CaptainsLogScreen | None = None
        self.credits_screen: CreditsScreen | None = None
        self.diplomacy_screen: DiplomacyScreen | None = None
        self.colony_screen: ColonyScreen | None = None
        self.deep_survey_screen: DeepSurveyScreen | None = None

        # Colony management
        self.colony_manager = ColonyManager()

        # Faction data (generated alongside galaxy)
        self.factions: list[Faction] = []

        # Save feedback
        self._save_msg = ""
        self._save_msg_timer = 0.0

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

            # Ctrl+S — save game (only when in-game)
            if (
                event.type == pygame.KEYDOWN
                and event.key == pygame.K_s
                and (event.mod & pygame.KMOD_CTRL)
                and self.fleet and self.galaxy
            ):
                path = save_game(self.fleet, self.galaxy, self.mothership_systems, self.quest_state)
                self._save_msg = f"Game saved to {path}"
                self._save_msg_timer = 2.5
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
            elif self.state == GameState.FORMATION_SETUP and self.formation_screen:
                self.formation_screen.handle_events(event)
            elif self.state == GameState.CAPTAINS_LOG and self.captains_log_screen:
                self.captains_log_screen.handle_events(event)
            elif self.state == GameState.CREDITS and self.credits_screen:
                self.credits_screen.handle_events(event)
            elif self.state == GameState.DIPLOMACY and self.diplomacy_screen:
                self.diplomacy_screen.handle_events(event)
            elif self.state == GameState.DEEP_SURVEY and self.deep_survey_screen:
                self.deep_survey_screen.handle_events(event)
            elif self.state == GameState.COLONY_MANAGEMENT and self.colony_screen:
                self.colony_screen.handle_events(event)
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
        elif self.state == GameState.COMBAT:
            pass  # Can't escape from combat
        elif self.state == GameState.EVENT_DIALOG:
            pass  # Can't escape from event
        elif self.state == GameState.CAPTAINS_LOG:
            self.state = GameState.STAR_MAP
        elif self.state == GameState.CREDITS:
            self.state = GameState.TITLE
            self.title_screen = TitleScreen()
        elif self.state == GameState.DIPLOMACY:
            self.state = GameState.SYSTEM_VIEW
        elif self.state == GameState.DEEP_SURVEY:
            self.state = GameState.SYSTEM_VIEW
            self.deep_survey_screen = None
        elif self.state == GameState.COLONY_MANAGEMENT:
            self.state = GameState.SYSTEM_VIEW
            self.colony_screen = None

    def _update(self, dt: float) -> None:
        self.starfield.update(dt)

        # Save feedback timer
        if self._save_msg_timer > 0:
            self._save_msg_timer -= dt
            if self._save_msg_timer <= 0:
                self._save_msg = ""

        if self.state == GameState.TITLE:
            self.title_screen.update(dt)
            if self.title_screen.next_state:
                next_s = self.title_screen.next_state
                self.title_screen.next_state = None

                if next_s == GameState.CREDITS:
                    self.credits_screen = CreditsScreen()
                    self.state = GameState.CREDITS
                elif self.title_screen.load_save:
                    self.title_screen.load_save = False
                    result = load_game()
                    if result:
                        self.fleet, self.galaxy, self.mothership_systems, self.quest_state = result
                        self.star_map_screen = StarMapScreen(self.galaxy, self.factions)
                        self.state = GameState.STAR_MAP
                    else:
                        # Save corrupted — fall through to ship select
                        self.state = GameState.SHIP_SELECT
                else:
                    self.state = next_s

        elif self.state == GameState.SHIP_SELECT:
            self.ship_select_screen.update(dt)
            if self.ship_select_screen.next_state:
                self.fleet = self.ship_select_screen.chosen_fleet
                self.galaxy = Galaxy()
                self.mothership_systems = create_default_systems()
                self.quest_state = QuestState()
                self.star_map_screen = StarMapScreen(self.galaxy, self.factions)
                self.state = self.ship_select_screen.next_state
                self.ship_select_screen.next_state = None

                # Generate alien factions and assign to galaxy systems
                self.factions = generate_factions(rng=random.Random(self.galaxy.seed))
                assign_factions_to_systems(self.galaxy.systems, self.factions, random.Random(self.galaxy.seed))

                self.quest_state.log_event(
                    "Departure",
                    f"The {self.fleet.mothership.name} has launched from the prison station "
                    f"deep within the heart of a dying star. {self.fleet.colonists:,} souls "
                    f"sleep in cryogenic vaults, dreaming of a world they have never seen. "
                    f"Eight thousand years of isolation end now. The dead galaxy awaits, "
                    f"and with it, the ghosts of what we once were.",
                    "event",
                )

        elif self.state == GameState.STAR_MAP and self.star_map_screen:
            # Handle cryosleep overlay
            if self._cryosleep_active:
                self._cryosleep_timer += dt
                if self._cryosleep_timer > 4.0:
                    self._cryosleep_active = False
                return

            self.star_map_screen.update(dt)
            if self.star_map_screen.next_state:
                if self.star_map_screen.next_state == GameState.CAPTAINS_LOG:
                    self.captains_log_screen = CaptainsLogScreen(self.quest_state)
                elif self.star_map_screen.next_state == GameState.SYSTEM_VIEW:
                    self.system_view_screen = SystemViewScreen(
                        self.galaxy, self.fleet, self.quest_state,
                        colony_manager=self.colony_manager,
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

                    # Fleet ships degrade during FTL (PLAN.md: fleet health goes down)
                    destroyed_ships: list[str] = []
                    for ship in list(self.fleet.ships):
                        decay_pct = random.uniform(0.02, 0.05)
                        hull_loss = int(ship.max_hull * decay_pct)
                        ship.hull = max(0, ship.hull - hull_loss)
                        if ship.hull <= 0:
                            destroyed_ships.append(ship.name)
                            self.fleet.ships.remove(ship)
                    if destroyed_ships:
                        for name in destroyed_ships:
                            self._cryosleep_decay_msgs.append(
                                f"⚠ {name} destroyed during FTL transit!"
                            )

                    self._cryosleep_active = True
                    self._cryosleep_timer = 0.0

                    # Log the jump
                    sid = self.star_map_screen.selected_system_id
                    target_sys = self.galaxy.systems[sid] if sid is not None and 0 <= sid < len(self.galaxy.systems) else None
                    sys_name = target_sys.name if target_sys else "unknown system"
                    self.quest_state.turn += 1
                    destroyed_note = f" Lost: {', '.join(destroyed_ships)}." if destroyed_ships else ""
                    self.quest_state.log_event(
                        f"FTL Jump to {sys_name}",
                        f"Arrived after {self._cryosleep_years} years in cryosleep. "
                        f"{self._cryosleep_colonist_loss:,} colonists lost during transit.{destroyed_note}",
                        "ftl",
                    )
                    self._auto_save()

                elif self.star_map_screen.next_state == GameState.MOTHERSHIP:
                    initial_tab = "fleet" if getattr(self.star_map_screen, 'open_fleet_tab', False) else "systems"
                    self.mothership_screen = MothershipScreen(self.fleet, self.mothership_systems, initial_tab=initial_tab)

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
                elif next_st == GameState.DIPLOMACY and self.system_view_screen.pending_diplomacy_faction_id:
                    # Look up faction by id
                    fid = self.system_view_screen.pending_diplomacy_faction_id
                    faction = next((f for f in self.factions if f.id == fid), None)
                    if faction:
                        # Set local settlement context
                        sel_obj = self.system_view_screen.selected_object
                        if sel_obj:
                            faction.settlement_name = f"{sel_obj.name} Settlement"
                        self.diplomacy_screen = DiplomacyScreen(faction, self.fleet)
                        self.state = GameState.DIPLOMACY
                    else:
                        self.state = GameState.SYSTEM_VIEW
                    self.system_view_screen.pending_diplomacy_faction_id = ""
                elif next_st == GameState.STAR_MAP:
                    self.state = GameState.STAR_MAP
                elif next_st == GameState.DEEP_SURVEY:
                    obj = self.system_view_screen.pending_deep_survey_object
                    if obj:
                        self.deep_survey_screen = DeepSurveyScreen(
                            planet_name=obj.name,
                            system_id=self.galaxy.current_system.id,
                            survey_seed=obj.survey_seed,
                            fleet=self.fleet,
                            scout_count=len(self.fleet.scouts),
                            sensor_level=1,
                        )
                        self.state = GameState.DEEP_SURVEY
                        self.system_view_screen.pending_deep_survey_object = None
                    else:
                        self.state = GameState.SYSTEM_VIEW
                elif next_st == GameState.COLONY_MANAGEMENT:
                    self.colony_screen = ColonyScreen(
                        self.colony_manager, self.fleet,
                        focus_system=self.galaxy.current_system.id,
                    )
                    self.state = GameState.COLONY_MANAGEMENT
                    self.system_view_screen.pending_colony_management = False
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

                # Log combat result
                won = self.fleet is not None  # Still alive
                if won:
                    combat_desc = (
                        "The guns fall silent and the debris field spreads like a "
                        "funeral shroud. Your fleet survives, scarred but unbroken. "
                        "The void does not care for victory or defeat — only silence."
                    )
                else:
                    combat_desc = (
                        "The final transmission cuts to static. Across the wreckage, "
                        "emergency beacons pulse in vain. Heavy losses have been sustained."
                    )
                self.quest_state.log_event("Combat Resolved", combat_desc, "combat")
                self._auto_save()

        elif self.state == GameState.EVENT_DIALOG and self.event_dialog_screen:
            self.event_dialog_screen.update(dt)
            if self.event_dialog_screen.next_state:
                # Process quest flag from the resolved outcome
                self._process_quest_flag(self.event_dialog_screen.resolved_quest_flag)

                # Track optional tasks based on event context
                self.quest_state.ensure_optional_tasks()
                if self.event_dialog_screen.event:
                    evt_title = self.event_dialog_screen.event.title.lower()
                    if any(kw in evt_title for kw in ("derelict", "wreck", "salvage", "hull")):
                        msg = self.quest_state.increment_optional("explore_derelicts")
                        if msg:
                            self.quest_state.log_event("Objective Complete", msg, "event")
                    elif any(kw in evt_title for kw in ("anomal", "distortion", "signal", "quantum")):
                        msg = self.quest_state.increment_optional("survey_anomalies")
                        if msg:
                            self.quest_state.log_event("Objective Complete", msg, "event")

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
                        n = self.quest_state.colonies_established
                        self.quest_state.log_event(
                            f"Colony #{n} Established",
                            f"A new colony has been founded — humanity's {n}{'st' if n == 1 else 'nd' if n == 2 else 'rd' if n == 3 else 'th'} "
                            f"settlement. {self.fleet.colonists:,} colonists remain aboard.",
                            "event",
                        )
                        msg = self.quest_state.increment_optional("establish_colonies")
                        if msg:
                            self.quest_state.log_event("Objective Complete", msg, "event")
                    self.state = GameState.SYSTEM_VIEW
                self.event_dialog_screen = None
                self._check_game_over()
                self._auto_save()

        elif self.state == GameState.MOTHERSHIP and self.mothership_screen:
            self.mothership_screen.update(dt)
            if self.mothership_screen.next_state:
                self.state = self.mothership_screen.next_state
                self.mothership_screen.next_state = None



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

        elif self.state == GameState.CAPTAINS_LOG and self.captains_log_screen:
            self.captains_log_screen.update(dt)
            if self.captains_log_screen.next_state:
                self.state = self.captains_log_screen.next_state
                self.captains_log_screen.next_state = None

        elif self.state == GameState.CREDITS and self.credits_screen:
            self.credits_screen.update(dt)
            if self.credits_screen.next_state:
                self.state = GameState.TITLE
                self.title_screen = TitleScreen()
                self.credits_screen = None

        elif self.state == GameState.DIPLOMACY and self.diplomacy_screen:
            self.diplomacy_screen.update(dt)
            if self.diplomacy_screen.next_state:
                # Check if diplomacy triggered combat
                if (self.diplomacy_screen.result
                        and self.diplomacy_screen.result.triggers_combat
                        and self.fleet):
                    enemy = generate_enemy_fleet(
                        danger=2,
                        is_federation=False,
                    )
                    self._pending_enemy = enemy
                    self._pending_combat_quest_flag = ""
                    self.formation_screen = FormationScreen()
                    self.formation_screen.setup(self.fleet)
                    self.state = GameState.FORMATION_SETUP
                    self.quest_state.log_event(
                        f"Hostilities with {self.diplomacy_screen.faction.name}",
                        f"Diplomatic negotiations with the {self.diplomacy_screen.faction.species_name} "
                        f"have broken down. Their warships move to engage.",
                        "combat",
                    )
                else:
                    # Log diplomacy interaction
                    if self.diplomacy_screen.result:
                        result = self.diplomacy_screen.result
                        verb = "succeeded" if result.success else "failed"
                        self.quest_state.log_event(
                            f"Diplomacy: {self.diplomacy_screen.faction.name}",
                            f"Diplomatic action {verb}. {result.description[:100]}",
                            "event",
                        )
                        # Track trade optional task
                        if result.success and (result.metal_gained or result.energy_gained or result.rare_gained):
                            msg = self.quest_state.increment_optional("trade_factions")
                            if msg:
                                self.quest_state.log_event("Objective Complete", msg, "event")
                    self.state = self.diplomacy_screen.next_state
                self.diplomacy_screen.next_state = None

        elif self.state == GameState.DEEP_SURVEY and self.deep_survey_screen:
            self.deep_survey_screen.update(dt)
            if self.deep_survey_screen.next_state:
                # Mark planet as deep-surveyed
                if self.system_view_screen:
                    for obj in self.system_view_screen.system.objects:
                        if obj.name == self.deep_survey_screen.planet_name:
                            obj.deep_surveyed = True
                            break
                # If colony site was found, create a colony
                if self.deep_survey_screen.colony_site_found:
                    sid = self.deep_survey_screen.system_id
                    pname = self.deep_survey_screen.planet_name
                    if not self.colony_manager.get_colony_at(sid):
                        self.colony_manager.start_colony(
                            sid, pname, self.quest_state.turn,
                        )
                        self.quest_state.log_event(
                            f"Colony Site: {pname}",
                            f"Deep survey complete. A viable colony site has been "
                            f"identified on {pname}. Visit the Colony Manager (C) "
                            f"to begin development.",
                            "event",
                        )
                self.state = self.deep_survey_screen.next_state
                self.deep_survey_screen = None

        elif self.state == GameState.COLONY_MANAGEMENT and self.colony_screen:
            self.colony_screen.update(dt)
            if self.colony_screen.next_state:
                self.state = self.colony_screen.next_state
                self.colony_screen = None

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

        elif self.state == GameState.FORMATION_SETUP and self.formation_screen:
            self.formation_screen.draw(self.screen)
            if self.fleet:
                self.hud.draw(self.screen, self.fleet)
        elif self.state == GameState.CAPTAINS_LOG and self.captains_log_screen:
            self.captains_log_screen.draw(self.screen)
        elif self.state == GameState.CREDITS and self.credits_screen:
            self.credits_screen.draw(self.screen)
        elif self.state == GameState.DIPLOMACY and self.diplomacy_screen:
            if self.system_view_screen:
                self.system_view_screen.draw(self.screen)
            self.diplomacy_screen.draw(self.screen)
        elif self.state == GameState.DEEP_SURVEY and self.deep_survey_screen:
            self.deep_survey_screen.draw(self.screen)
        elif self.state == GameState.COLONY_MANAGEMENT and self.colony_screen:
            self.colony_screen.draw(self.screen)
            if self.fleet:
                self.hud.draw(self.screen, self.fleet)
        elif self.state == GameState.GAME_OVER:
            self._draw_game_over()

        pygame.display.flip()

        # Save feedback overlay (drawn after flip to appear on next frame)
        if self._save_msg:
            font = pygame.font.Font(None, 24)
            msg_surf = font.render(self._save_msg, True, HULL_GREEN)
            bg = pygame.Surface((msg_surf.get_width() + 20, msg_surf.get_height() + 10), pygame.SRCALPHA)
            bg.fill((0, 0, 0, 180))
            x = SCREEN_WIDTH - bg.get_width() - 10
            y = 10
            self.screen.blit(bg, (x, y))
            self.screen.blit(msg_surf, (x + 10, y + 5))
            pygame.display.update(pygame.Rect(x, y, bg.get_width(), bg.get_height()))

    # ------------------------------------------------------------------
    # Star map keybinds hint
    # ------------------------------------------------------------------

    def _auto_save(self) -> None:
        """Auto-save at key gameplay checkpoints."""
        if self.fleet and self.galaxy:
            save_game(self.fleet, self.galaxy, self.mothership_systems, self.quest_state)
            self._save_msg = "Auto-saved"
            self._save_msg_timer = 1.5

    def _draw_star_map_hints(self) -> None:
        """Show keybind hints for star map screens."""
        font = pygame.font.Font(None, 22)
        hint = font.render("TAB — Mothership    F — Fleet    L — Log    Ctrl+S — Save", True, LIGHT_GREY)
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
        self.screen.blit(title, ((SCREEN_WIDTH - title.get_width()) // 2, 130))

        # Narrative line
        narrative = font_small.render(
            "The universe moves on without you. Stars are born and die in the time it takes to blink.",
            True, LIGHT_GREY,
        )
        self.screen.blit(narrative, ((SCREEN_WIDTH - narrative.get_width()) // 2, 195))

        # Years elapsed
        years_text = font_med.render(
            f"You awaken. {self._cryosleep_years:,} years have passed in frozen silence.",
            True, WHITE,
        )
        self.screen.blit(years_text, ((SCREEN_WIDTH - years_text.get_width()) // 2, 240))

        # Colonist losses
        y = 290
        if self._cryosleep_colonist_loss > 0:
            loss_text = font_small.render(
                f"Cryo-vault malfunctions claimed {self._cryosleep_colonist_loss:,} souls. "
                f"Their names are added to a list that grows longer with every jump.",
                True, RED_ALERT,
            )
            self.screen.blit(loss_text, ((SCREEN_WIDTH - loss_text.get_width()) // 2, y))
            y += 30

        # Maintenance decay
        if self._cryosleep_decay_msgs:
            decay_header = font_small.render(
                "The ship groans. Systems have degraded in transit:", True, AMBER,
            )
            self.screen.blit(decay_header, ((SCREEN_WIDTH - decay_header.get_width()) // 2, y))
            y += 26
            for msg in self._cryosleep_decay_msgs[:5]:
                msg_surf = font_small.render(f"  • {msg}", True, LIGHT_GREY)
                self.screen.blit(msg_surf, ((SCREEN_WIDTH - msg_surf.get_width()) // 2, y))
                y += 22

        # Continue hint
        if self._cryosleep_timer > 2.0:
            hint = font_small.render("Consciousness returns...", True, LIGHT_GREY)
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
            EndingType.FLEET_DESTROYED: (
                "YOUR FLEET HAS BEEN DESTROYED", RED_ALERT,
                "The last hope of humanity drifts silently through the void, "
                "a tomb of steel and frozen dreams. In a thousand years, "
                "perhaps some alien archaeologist will find the wreckage "
                "and wonder what manner of beings built such a vessel."
            ),
            EndingType.COLONIST_COLLAPSE: (
                "COLONIST POPULATION CRITICAL", RED_ALERT,
                "With fewer than 15,000 colonists, genetic diversity has collapsed. "
                "The crew maintains the ship as a monument to what was lost, "
                "but the species they were born to save is already gone."
            ),
            EndingType.COLONY_SUCCESS: (
                "A NEW HOME", HULL_GREEN,
                "Against impossible odds, humanity has planted its roots once more. "
                "From the ashes of a dead civilisation, new cities rise under alien skies. "
                "The old federation is a memory, but its children endure."
            ),
            EndingType.TRUE_ENDING: (
                "BEYOND THE GATEWAY", CYAN,
                "Ninurta falls silent at last. The ancient gateway hums with power "
                "as your fleet crosses the threshold to Andromeda. Behind you, "
                "the Milky Way fades — a graveyard of gods and empires. Ahead, "
                "a galaxy untouched by ruin. Humanity endures."
            ),
        }

        title, color, desc = endings.get(
            self.ending_type,
            ("GAME OVER", RED_ALERT, "Your journey has ended."),
        )

        # Title
        title_surf = self._game_over_font.render(title, True, color)
        title_rect = title_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 60))
        self.screen.blit(title_surf, title_rect)

        # Description (word-wrapped)
        font_desc = pygame.font.Font(None, 28)
        words = desc.split()
        lines: list[str] = []
        current = ""
        for word in words:
            test = f"{current} {word}".strip()
            if font_desc.size(test)[0] > SCREEN_WIDTH - 200:
                lines.append(current)
                current = word
            else:
                current = test
        if current:
            lines.append(current)

        y = SCREEN_HEIGHT // 2
        for line in lines:
            line_surf = font_desc.render(line, True, LIGHT_GREY)
            line_rect = line_surf.get_rect(center=(SCREEN_WIDTH // 2, y))
            self.screen.blit(line_surf, line_rect)
            y += 26

        # Continue prompt
        if self._game_over_timer > 2.0:
            font_hint = pygame.font.Font(None, 24)
            hint = font_hint.render("Press any key to exit", True, LIGHT_GREY)
            hint_rect = hint.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 100))
            self.screen.blit(hint, hint_rect)


def main() -> None:
    """Entry point for the hollowed-stars command."""
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
