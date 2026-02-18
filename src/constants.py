"""Game-wide constants for Hollowed Stars."""

# --- Display ---
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60
TITLE = "Hollowed Stars"

# --- Colors (RGB) ---
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
DARK_GREY = (30, 30, 40)
LIGHT_GREY = (180, 180, 190)
STAR_WHITE = (220, 220, 235)
STAR_DIM = (140, 140, 160)

# HUD / UI accent colors
AMBER = (255, 191, 0)
CYAN = (0, 200, 220)
RED_ALERT = (200, 40, 40)
SHIELD_BLUE = (60, 120, 255)
HULL_GREEN = (40, 200, 80)

# --- Star type colors (keyed by StarType.value) ---
STAR_COLORS: dict[str, tuple[int, int, int]] = {
    "red_dwarf": (200, 80, 60),
    "yellow": (255, 220, 100),
    "blue_giant": (100, 160, 255),
    "neutron": (200, 200, 255),
    "black_hole": (120, 40, 180),
}

# --- UI Panel ---
PANEL_BG = (20, 20, 30, 200)
PANEL_BORDER = (60, 60, 80)

# --- Resource colors ---
METAL_COLOR = (160, 160, 170)
ENERGY_COLOR = (255, 220, 50)
RARE_COLOR = (180, 100, 255)

# --- Game Metadata ---
GAME_TITLE = "HOLLOWED STARS"
GAME_SUBTITLE = "The Last Fleet"
GAME_VERSION = "0.6.3"

# --- Gameplay ---
MIN_COLONISTS = 15_000  # Below this, game is lost
STARTING_COLONISTS = 1_000_000

# --- Star field ---
NUM_BACKGROUND_STARS = 300
