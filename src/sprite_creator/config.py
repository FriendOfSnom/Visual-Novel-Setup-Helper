#!/usr/bin/env python3
"""
constants.py

All global paths, constants, and static tables for the Gemini sprite pipeline.
"""

from pathlib import Path
from typing import Dict, List, Tuple

# ═══════════════════════════════════════════════════════════════════════════════
# APPLICATION INFO
# ═══════════════════════════════════════════════════════════════════════════════
APP_NAME = "AI Sprite Creator"
APP_VERSION = "2.1.0"

# Base directory for this package
SPRITE_CREATOR_DIR = Path(__file__).resolve().parent

# Data directory (contains CSVs and reference sprites)
DATA_DIR = SPRITE_CREATOR_DIR / "data"

# Paths for configuration and data files
CONFIG_PATH = Path.home() / ".st_gemini_config.json"
# OUTFIT_CSV_PATH deprecated - outfit prompts now in individual files per archetype+outfit
NAMES_CSV_PATH = DATA_DIR / "names.csv"
REF_SPRITES_DIR = DATA_DIR / "reference_sprites"

# Gemini API constants
GEMINI_IMAGE_MODEL = "gemini-2.5-flash-image"
GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_IMAGE_MODEL}:generateContent"
)

# ═══════════════════════════════════════════════════════════════════════════════
# DARK THEME COLOR SCHEME
# ═══════════════════════════════════════════════════════════════════════════════
BG_COLOR = "#2B2B2B"              # Main window background
BG_SECONDARY = "#1E1E1E"          # Darker areas (header, footer)
CARD_BG = "#3C3C3C"               # Card/panel backgrounds
CARD_BG_HOVER = "#4A4A4A"         # Card hover state
CARD_BG_SELECTED = "#4A90D9"      # Selected card background

TEXT_COLOR = "#FFFFFF"            # Primary text
TEXT_SECONDARY = "#A0A0A0"        # Secondary/muted text
TEXT_DISABLED = "#666666"         # Disabled text

ACCENT_COLOR = "#4A90D9"          # Blue accent for primary buttons
ACCENT_HOVER = "#5BA0E9"          # Primary button hover
PRIMARY_COLOR = "#4A90D9"         # Alias for accent (backwards compatibility)
SECONDARY_COLOR = "#666666"       # Secondary button background
SECONDARY_HOVER = "#777777"       # Secondary button hover
DANGER_COLOR = "#D94A4A"          # Red for destructive actions
DANGER_HOVER = "#E95A5A"          # Danger button hover
SUCCESS_COLOR = "#4AD94A"         # Green for success states

LINE_COLOR = "#00E5FF"            # Cyan accent for highlights
HIGHLIGHT_COLOR = "#00E5FF"       # Interactive element highlights
BORDER_COLOR = "#555555"          # Subtle borders

# ═══════════════════════════════════════════════════════════════════════════════
# FONT DEFINITIONS (Segoe UI for modern Windows look)
# ═══════════════════════════════════════════════════════════════════════════════
FONT_FAMILY = "Segoe UI"

# Title fonts (large, prominent)
TITLE_FONT = (FONT_FAMILY, 24, "bold")       # Main screen titles
PAGE_TITLE_FONT = (FONT_FAMILY, 20, "bold")  # Page/wizard step titles
SECTION_FONT = (FONT_FAMILY, 16, "bold")     # Section headers

# Body fonts (medium, readable)
BODY_FONT = (FONT_FAMILY, 12)                # Regular body text
BODY_FONT_BOLD = (FONT_FAMILY, 12, "bold")   # Emphasized body text

# Small fonts (compact, secondary)
SMALL_FONT = (FONT_FAMILY, 10)               # Labels, hints, secondary text
SMALL_FONT_BOLD = (FONT_FAMILY, 10, "bold")  # Small emphasized text

# Button fonts
BUTTON_FONT = (FONT_FAMILY, 11)              # Standard buttons
BUTTON_FONT_LARGE = (FONT_FAMILY, 13, "bold") # Large action buttons

# Legacy aliases (backwards compatibility)
INSTRUCTION_FONT = BODY_FONT

# Layout constants
WINDOW_MARGIN = 10
WRAP_PADDING = 40
CARD_PADDING = 16
CARD_RADIUS = 8  # For styling reference (tkinter doesn't support border-radius natively)

# Outfit keys:
# Base is always included by the pipeline, but you can choose which additional
# outfits to generate. These keys should match outfit_key values in the CSV.
ALL_OUTFIT_KEYS: List[str] = ["formal", "casual", "uniform", "athletic", "swimsuit", "underwear"]

# Default subset used when the user does not change anything.
OUTFIT_KEYS: List[str] = ["formal", "casual"]

# Default ordered list of expressions we actually use per outfit.
# The first entry is always neutral.
EXPRESSIONS_SEQUENCE: List[Tuple[str, str]] = [
    ("0",  "neutral and relaxed with a soft smile"),
    ("1",  "neutral with mouth open as if talking"),
    ("2",  "happy and cheerful"),
    ("3",  "playful, giving a wink"),
    ("4",  "surprised with wide eyes"),
    ("5",  "sad and worried"),
    ("6",  "angry or really annoyed"),
    ("7",  "embarrassed with a bright red blush"),
    ("8",  "aroused and blushing heavily"),
    ("9",  "laughing at a good joke"),
    ("10", "confident with an almost smug look"),
    ("11", "deep in thought, pensive"),
    ("12", "crying and bawling"),
]


# Archetypes and their gender style codes
GENDER_ARCHETYPES: List[Tuple[str, str]] = [
    ("young woman", "f"),
    ("adult woman", "f"),
    ("motherly woman", "f"),
    ("young man", "m"),
    ("adult man", "m"),
    ("fatherly man", "m"),
]

# Safety fallback prompts for underwear outfit generation
# Used when safety filters block random CSV prompts
SAFETY_FALLBACK_UNDERWEAR_PROMPTS: Dict[str, str] = {
    "young woman": (
        "a comfortable cotton bralette in a neutral color with soft elastic, "
        "paired with matching cotton high-waisted briefs, simple everyday basics"
    ),
    "adult woman": (
        "a classic supportive bra in a neutral tone with wide straps and full coverage, "
        "paired with matching high-waisted briefs, comfortable everyday essentials"
    ),
    "motherly woman": (
        "a supportive full-coverage bra in a soft neutral color with wide straps, "
        "paired with matching high-waisted briefs, practical everyday comfort"
    ),
    "young man": (
        "classic cotton boxer briefs in a solid neutral color with comfortable elastic waistband, "
        "simple everyday basics"
    ),
    "adult man": (
        "comfortable cotton boxer briefs in a neutral color with supportive fit and elastic waistband, "
        "practical everyday essentials"
    ),
    "fatherly man": (
        "classic supportive boxer briefs in a solid neutral tone with comfortable elastic waistband, "
        "practical everyday basics"
    ),
}

# Tier 4: Ultra-generic underwear prompts with no specific garment names
# Used when Tier 3 prompts (which mention bra/briefs) are still blocked
SAFETY_FALLBACK_UNDERWEAR_TIER4: Dict[str, str] = {
    "young woman": "simple, comfortable underwear that suit this character",
    "adult woman": "simple, comfortable underwear that suit this character",
    "motherly woman": "simple, comfortable underwear that suit this character",
    "young man": "simple, comfortable underwear that suit this character",
    "adult man": "simple, comfortable underwear that suit this character",
    "fatherly man": "simple, comfortable underwear that suit this character",
}

# Tier 5: Athletic underwear alternative (sports bra + running shorts)
# Last resort before skipping - framed as athletic wear to pass filters
SAFETY_FALLBACK_ATHLETIC_UNDERWEAR: Dict[str, str] = {
    "young woman": "a cute cropped sports bra in pastel pink with very short running shorts, youthful athletic style",
    "adult woman": "a sleek fitted sports bra in black with very short running shorts, confident athletic look",
    "motherly woman": "a comfortable supportive sports bra in soft blue with modest running shorts, relaxed athletic style",
    "young man": "very short athletic running shorts in bright colors, no shirt, energetic sporty look",
    "adult man": "fitted athletic compression shorts in dark gray, no shirt, mature athletic build",
    "fatherly man": "comfortable athletic shorts in navy blue, no shirt, relaxed dad-bod athletic style",
}

# Safety fallback prompts for expressions that may trigger safety filters
# Maps expression key to a safer alternative description
SAFETY_FALLBACK_EXPRESSION_PROMPTS: Dict[str, str] = {
    "7": "embarrassed with a soft pink blush on the cheeks",
    "8": "flustered and blushing with a shy, warm expression",
}
