"""
Name pool utilities for character creation.

Provides functions to load and select character names from CSV data.
"""

import csv
import random
from pathlib import Path
from typing import List, Tuple

from ..config import NAMES_CSV_PATH


def load_name_pool(csv_path: Path = NAMES_CSV_PATH) -> Tuple[List[str], List[str]]:
    """
    Load girl/boy name pools from CSV with columns: name, gender.

    Args:
        csv_path: Path to CSV file containing names.

    Returns:
        (girl_names, boy_names) tuple of name lists.
    """
    girl_names: List[str] = []
    boy_names: List[str] = []

    try:
        with csv_path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                gender = (row.get("gender") or "").strip().lower()
                name = (row.get("name") or "").strip()
                if not name:
                    continue
                if gender == "girl":
                    girl_names.append(name)
                elif gender == "boy":
                    boy_names.append(name)
    except FileNotFoundError:
        print(f"[WARN] Could not find {csv_path}. Using fallback names.")
        girl_names = ["Sakura", "Emily", "Yuki", "Hannah", "Aiko", "Madison", "Kana", "Sara"]
        boy_names = ["Takashi", "Ethan", "Yuto", "Liam", "Kenta", "Jacob", "Hiro", "Alex"]
    except Exception as e:
        print(f"[WARN] Failed to read {csv_path}: {e}. Using fallback names.")
        girl_names = ["Sakura", "Emily", "Yuki", "Hannah", "Aiko", "Madison", "Kana", "Sara"]
        boy_names = ["Takashi", "Ethan", "Yuto", "Liam", "Kenta", "Jacob", "Hiro", "Alex"]

    return girl_names, boy_names


def pick_random_name(voice: str, girl_names: List[str], boy_names: List[str]) -> str:
    """
    Pick a random name based on voice.

    Args:
        voice: "girl" or "boy".
        girl_names: List of girl names.
        boy_names: List of boy names.

    Returns:
        Random name from appropriate list.
    """
    pool = girl_names if (voice or "").lower() == "girl" else boy_names
    if not pool:
        pool = ["Alex", "Riley", "Taylor", "Jordan"]
    return random.choice(pool)
