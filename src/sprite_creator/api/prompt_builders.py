"""
Prompt builders for Gemini API requests.

All prompt generation logic for sprite creation, outfit changes, and expressions.
Prompts are preserved exactly as originally written per user request.
"""

import csv
import random
from pathlib import Path
from typing import Dict, List, Optional

from ..config import GENDER_ARCHETYPES


# =============================================================================
# Archetype and Gender Utilities
# =============================================================================

def archetype_to_gender_style(archetype_label: str) -> str:
    """
    Given an archetype label, return gender style code 'f' or 'm'.

    Args:
        archetype_label: Archetype name (e.g., "young woman", "adult man").

    Returns:
        'f' for female archetypes, 'm' for male archetypes, 'f' as default.
    """
    for label, gender in GENDER_ARCHETYPES:
        if label == archetype_label:
            return gender
    return "f"  # Default to female


# =============================================================================
# Core Prompt Builders (DO NOT MODIFY - per user request)
# =============================================================================

def build_initial_pose_prompt(
    gender_style: str,
    archetype_label: str = "",
    background_color: str = "black (#000000)",
    additional_instructions: str = "",
) -> str:
    """
    Prompt to normalize the original sprite (mid-thigh, specified background).

    NOTE: Prompt wording preserved exactly as-is per user request.

    Args:
        gender_style: 'f' or 'm' (currently unused but kept for signature consistency).
        background_color: Background color description (e.g., "magenta (#FF00FF)" or "black (#000000)").
        additional_instructions: Optional extra instructions to append to the prompt.

    Returns:
        Prompt string for initial pose normalization.
    """
    bg = background_color.split("(")[0].strip()  # Extract color name (magenta or black)
    prompt = (
        f"Ensure the character's appearance matches a {archetype_label} - their age and features should be appropriate for this archetype. Edit the character if they are not already a {archetype_label}, to match being a {archetype_label}. "
        "Sharpen the image to at least 720p resolution if it is lower than that and correct any artifacts of blurriness. "
        "Don't change the size, proportions, framing, or art style of the character. "
        f"Give the character a {bg} background behind them. "
        "Make sure the head, arms, hair, hands, and clothes are all kept within the image. "
        "Keep the crop the same from the mid-thigh on up, no matter what."
    )
    if additional_instructions.strip():
        prompt += f" Additionally: {additional_instructions.strip()}"
    return prompt


def build_expression_prompt(expression_desc: str, background_color: str = "black (#000000)") -> str:
    """
    Prompt to change facial expression, keeping style and framing.

    NOTE: Prompt wording preserved exactly as-is per user request.

    Args:
        expression_desc: Description of the desired expression.
        background_color: Background color description (e.g., "magenta (#FF00FF)" or "black (#000000)").

    Returns:
        Prompt string for expression generation.
    """
    bg = background_color.split("(")[0].strip()  # Extract color name (magenta or black)
    return (
        f"Edit the character's expression and pose to match this emotion: {expression_desc}, but don't change the size, proportions, framing, or art style of the character. "
        "Keep the hair volume, hair outlines, and the hair style all the exact same. "
        f"Give the character a {bg} background behind them. "
        "Make sure the head, arms, hair, hands, and clothes are all kept within the image."
    )

def build_outfit_prompt(base_outfit_desc: str, gender_style: str, background_color: str = "black (#000000)") -> str:
    """
    Prompt to change clothing to base_outfit_desc on the given pose.

    NOTE: Prompt wording updated to avoid triggering safety filters while maintaining functionality.

    Args:
        base_outfit_desc: Description of the outfit to generate.
        gender_style: 'f' or 'm' for gender-appropriate wording.
        background_color: Background color description (e.g., "magenta (#FF00FF)" or "black (#000000)").

    Returns:
        Prompt string for outfit generation.
    """
    bg = background_color.split("(")[0].strip()  # Extract color name (magenta or black)
    return (
        f"Edit the character's clothes to match this description: {base_outfit_desc}, but don't change the size, proportions, framing, or art style of the character. "
        "Don't change the hair length, but edit the hair style to better fit the new outfit. "
        f"Give the character a {bg} background behind them. "
        "Make sure the head, arms, hair, hands, and clothes are all kept within the image."
    )

def build_standard_school_uniform_prompt(
    archetype_label: str,
    gender_style: str,
    background_color: str = "black (#000000)",
) -> str:
    """
    Build a standardized school-uniform prompt matching the rest of the outfit prompts.

    Uses archetype label and gender style to describe the character,
    then describes the school uniform in text. The cropped uniform reference
    image is used as visual backup.

    NOTE: Prompt wording updated to avoid triggering safety filters while maintaining functionality.

    Args:
        archetype_label: Character archetype (e.g., "young woman").
        gender_style: 'f' or 'm'.
        background_color: Background color description (e.g., "magenta (#FF00FF)" or "black (#000000)").

    Returns:
        Prompt string for standard school uniform generation.
    """
    # Base description that applies to both variants
    base_intro = (
        "Edit the visual novel character sprite, to have them wear the attached school uniform outfit, but don't change the size, proportions, framing, or art style of the character. "
        "For redundancy, I am going to also describe the outfit below... "
    )

    if gender_style == "f":
        # Female student uniform: blazer + bow + pleated skirt description
        uniform_desc = (
            "The character should be wearing: A navy blue tailored sleeveless blazer hybrid, tightly fitted to the torso. The blazer has gold piping along all the outer edges. The front features a double-breasted design with two rows of two gold buttons. The vest dips into a sharp angled hem near the waist, creating a stylish contour. Underneath it is a white short-sleeved dress shirt. The sleeve has a school crest patch on the upper arm: gold/yellow with an emblem inside. The arms are bare below the sleeves. There should be a bright red necktie with white stripes near the bottom. A short, red, plaid, pleated skirt finishes out the outfit. No ribbons. "
        )
    else:
        # Male student uniform: blazer + tie + slacks description
        uniform_desc = (
            "The character should be wearing: A white short-sleeved dress shirt. The sleeve has a school crest patch on the upper arm: gold/yellow with an emblem inside. There should be a bright red necktie with white stripes near the bottom. A pair of dark-colored slacks with a belt, which the white shirt tucks into, completes the look. "
        )

    bg = background_color.split("(")[0].strip()  # Extract color name (magenta or black)
    # Shared constraints and ST-format requirements
    tail = (
        "Edit the proportions of the school uniform to better fit the character, to keep the character consistent. "
        "Edit the hair style to better fit the new school uniform, but don't change the hair length. "
        f"Give the character a {bg} background behind them. "
        "Make sure the head, arms, hair, hands, and clothes are all kept within the image."
    )

    return base_intro + uniform_desc + tail


def build_prompt_for_idea(concept: str, archetype_label: str, gender_style: str, background_color: str = "black (#000000)") -> str:
    """
    Build text prompt used when generating a new character from a concept.

    NOTE: Prompt wording updated to avoid triggering safety filters while maintaining functionality.

    Args:
        concept: User's character concept description.
        archetype_label: Character archetype.
        gender_style: 'f' or 'm'.
        background_color: Background color description (e.g., "magenta (#FF00FF)" or "black (#000000)").

    Returns:
        Prompt string for new character generation from text.
    """
    bg = background_color.split("(")[0].strip()  # Extract color name (magenta or black)
    return (
        f"Create concept art for an original {archetype_label}, for a Japanese-style visual novel. The character idea is: "
        f"{concept} "
        "Match the art style and rendering of the attached reference character images so the new character has clean line art and vibrant, but not overly saturated colors, that make it look like it came from the same artist. "
        "Have them facing mostly toward the viewer in a friendly, neutral pose, that would work as a base sprite. "
        "They should not be holding anything in their hands. "
        f"Give the character a {bg} background behind them. "
        "Make sure the head, arms, hair, hands, and clothes are all kept within the image."
    )


# =============================================================================
# Outfit Prompt Loading and Configuration
# =============================================================================

def load_outfit_prompts(data_dir: Path) -> Dict[str, Dict[str, List[str]]]:
    """
    Load outfit prompts from individual CSV files per archetype+outfit combination.

    CSV files are named: {archetype}_{outfit_key}.csv
    CSV format: Single 'prompt' column with one prompt per row.

    Args:
        data_dir: Directory containing the outfit CSV files (e.g., DATA_DIR).

    Returns:
        {archetype: {outfit_key: [prompt, ...]}, ...}

    Example:
        {
            "young woman": {
                "casual": ["prompt1", "prompt2", ...],
                "formal": ["prompt1", "prompt2", ...],
                ...
            },
            ...
        }
    """
    from ..config import GENDER_ARCHETYPES, ALL_OUTFIT_KEYS

    database: Dict[str, Dict[str, List[str]]] = {}

    # Extract archetype names from GENDER_ARCHETYPES constant
    archetypes = [archetype for archetype, _ in GENDER_ARCHETYPES]

    for archetype in archetypes:
        for outfit_key in ALL_OUTFIT_KEYS:
            # Generate filename: "young woman" -> "young_woman_casual.csv"
            filename = f"{archetype.replace(' ', '_')}_{outfit_key}.csv"
            csv_path = data_dir / filename

            if not csv_path.is_file():
                print(f"[WARN] Outfit CSV not found: {filename}")
                continue

            try:
                with csv_path.open("r", encoding="utf-8", newline="") as f:
                    reader = csv.DictReader(f)
                    prompts = []

                    for row in reader:
                        prompt = (row.get("prompt") or "").strip()
                        if prompt:
                            prompts.append(prompt)

                    # Only add to database if we found prompts
                    if prompts:
                        database.setdefault(archetype, {})[outfit_key] = prompts

            except Exception as e:
                print(f"[WARN] Failed to read {filename}: {e}")

    # Validation message
    total_prompts = sum(
        len(prompts)
        for outfit_dict in database.values()
        for prompts in outfit_dict.values()
    )
    print(f"[INFO] Loaded {total_prompts} outfit prompts from {len(database)} archetypes")

    return database


def build_simple_outfit_description(outfit_key: str, gender_style: str) -> str:
    """
    Fallback generic outfit description if no CSV prompt is available.

    Args:
        outfit_key: Outfit type (formal, casual, uniform, athletic, swimsuit).
        gender_style: 'f' or 'm'.

    Returns:
        Generic outfit description string.
    """
    gender_word = "female character" if gender_style == "f" else "male character"

    if outfit_key == "formal":
        return (
            f"a slightly dressy outfit this {gender_word} would wear to a school dance "
            "or evening party, grounded and modern"
        )
    if outfit_key == "casual":
        return (
            f"a comfy everyday casual outfit this {gender_word} would wear to school "
            "or to hang out with friends"
        )
    if outfit_key == "uniform":
        return (
            f"a school or work uniform that fits this {gender_word}'s age and vibe, "
            "with clean lines and a coordinated look"
        )
    if outfit_key == "athletic":
        return (
            f"a sporty and practical athletic outfit this {gender_word} would wear "
            "for PE, training, or a casual game"
        )
    if outfit_key == "swimsuit":
        return (
            f"a modest but cute swimsuit this {gender_word} would wear to swim practice "
            "or a beach episode, nothing too revealing"
        )

    return f"a simple outfit that fits this {gender_word}'s personality"


def build_outfit_prompts_with_config(
    archetype_label: str,
    gender_style: str,
    selected_outfit_keys: List[str],
    outfit_database: Dict[str, Dict[str, List[str]]],
    outfit_prompt_config: Dict[str, Dict[str, Optional[str]]],
) -> Dict[str, str]:
    """
    Build one prompt per selected outfit_key, honoring per-outfit settings.

    For each key:
      - use_random=True: pick random CSV prompt if available; else fallback.
      - use_random=False: use custom_prompt (fallback if empty for safety).

    Args:
        archetype_label: Character archetype.
        gender_style: 'f' or 'm'.
        selected_outfit_keys: List of outfit keys to generate.
        outfit_database: Loaded CSV outfit prompts.
        outfit_prompt_config: Per-outfit configuration settings.

    Returns:
        {outfit_key: prompt_text}
    """
    prompts: Dict[str, str] = {}
    archetype_pool = outfit_database.get(archetype_label, {})

    for key in selected_outfit_keys:
        config = outfit_prompt_config.get(key, {})
        use_random = bool(config.get("use_random", True))
        custom_prompt = config.get("custom_prompt")

        if use_random:
            # Try to get random CSV prompt
            candidates = archetype_pool.get(key)
            if candidates:
                prompts[key] = random.choice(candidates)
            else:
                # Fallback to generic description
                prompts[key] = build_simple_outfit_description(key, gender_style)
        else:
            # Use custom prompt, or fallback if empty
            prompts[key] = custom_prompt or build_simple_outfit_description(key, gender_style)

    return prompts
