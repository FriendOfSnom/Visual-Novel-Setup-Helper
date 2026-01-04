#!/usr/bin/env python3
"""
gsp_constants.py

All global paths, constants, and static tables for the Gemini sprite pipeline.
"""

from pathlib import Path
from typing import Dict, List, Tuple

# Base directory for scripts
SCRIPT_DIR = Path(__file__).resolve().parent

# Paths for configuration and data files
CONFIG_PATH = Path.home() / ".st_gemini_config.json"
OUTFIT_CSV_PATH = SCRIPT_DIR / "outfit_prompts.csv"
NAMES_CSV_PATH = SCRIPT_DIR / "names.csv"
REF_SPRITES_DIR = SCRIPT_DIR / "reference_sprites"

# Gemini API constants
GEMINI_IMAGE_MODEL = "gemini-2.5-flash-image"
GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_IMAGE_MODEL}:generateContent"
)

# Background color we ask Gemini to use.
GBG_COLOR = (255, 0, 255)  # pure magenta (#FF00FF)

# Tk UI style constants
BG_COLOR = "lightgray"
TITLE_FONT = ("Arial", 16, "bold")
INSTRUCTION_FONT = ("Arial", 12)
LINE_COLOR = "#00E5FF"
WINDOW_MARGIN = 10
WRAP_PADDING = 40

# New wizard UI constants
PAGE_TITLE_FONT = ("Arial", 18, "bold")
SECTION_FONT = ("Arial", 14, "bold")
BODY_FONT = ("Arial", 11)
BUTTON_FONT = ("Arial", 10)

# Color scheme
PRIMARY_COLOR = "#0066CC"      # Blue for primary actions
SECONDARY_COLOR = "#666666"    # Gray for secondary text
DANGER_COLOR = "#CC0000"       # Red for destructive actions
SUCCESS_COLOR = "#00AA00"      # Green for completion
HIGHLIGHT_COLOR = "#00E5FF"    # Cyan for interactive elements (same as LINE_COLOR)

# Outfit keys:
# Base is always included by the pipeline, but you can choose which additional
# outfits to generate. These keys should match outfit_key values in the CSV.
ALL_OUTFIT_KEYS: List[str] = ["formal", "casual", "uniform", "athletic", "swimsuit"]

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
