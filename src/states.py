"""Game state management for Hollowed Stars."""

import enum


class GameState(enum.Enum):
    """Top-level game states."""

    TITLE = "title"
    SHIP_SELECT = "ship_select"
    STAR_MAP = "star_map"
    SYSTEM_VIEW = "system_view"
    FORMATION_SETUP = "formation_setup"
    COMBAT = "combat"
    EVENT_DIALOG = "event_dialog"
    MOTHERSHIP = "mothership"
    CAPTAINS_LOG = "captains_log"
    GAME_OVER = "game_over"
    CREDITS = "credits"
    DIPLOMACY = "diplomacy"
    COLONY_MANAGEMENT = "colony_management"
    DEEP_SURVEY = "deep_survey"


