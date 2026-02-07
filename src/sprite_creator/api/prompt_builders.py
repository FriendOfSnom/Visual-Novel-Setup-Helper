"""
Prompt builders for Gemini API requests.

All prompt generation logic for sprite creation, outfit changes, and expressions.
Prompts are preserved exactly as originally written per user request.
"""

import random
from typing import Dict, List, Optional

from ..config import GENDER_ARCHETYPES


# =============================================================================
# Outfit Description Generation - Dynamic via Gemini Text API
# =============================================================================

# Age ranges by archetype (used in Gemini text prompts)
AGE_RANGES = {
    "young woman": "18-20",
    "young man": "18-20",
    "adult woman": "20-35",
    "adult man": "20-35",
    "motherly woman": "35-50",
    "fatherly man": "35-50",
}

# Style words by (archetype, outfit_type) - includes article for grammar
# IMPORTANT: Style words must match the outfit type! "Elegant" implies formal wear.
# Casual needs casual descriptors, formal needs formal descriptors.
STYLE_WORDS = {
    # CASUAL - relaxed, everyday descriptors (no "sexy" - these are everyday outfits)
    ("young woman", "casual"): ["a cute", "a comfy", "a trendy", "a laid-back"],
    ("adult woman", "casual"): ["a relaxed", "a comfortable", "a casual", "an effortless"],
    ("motherly woman", "casual"): ["a comfortable", "a practical", "a relaxed", "a cozy"],
    ("young man", "casual"): ["a chill", "a comfy", "a laid-back", "a relaxed"],
    ("adult man", "casual"): ["a relaxed", "a comfortable", "a casual", "an easy-going"],
    ("fatherly man", "casual"): ["a comfortable", "a practical", "a relaxed", "a classic"],

    # FORMAL - dressy, elegant descriptors (includes "sexy" option)
    ("young woman", "formal"): ["a cute", "a stylish", "a trendy", "a glamorous", "a sexy"],
    ("adult woman", "formal"): ["a chic", "an elegant", "a sophisticated", "a stunning", "a sexy"],
    ("motherly woman", "formal"): ["a put-together", "a polished", "a flattering", "an elegant", "a sexy"],
    ("young man", "formal"): ["a fresh", "a stylish", "a sharp", "a dapper", "a sexy"],
    ("adult man", "formal"): ["a sharp", "a refined", "a polished", "a suave", "a sexy"],
    ("fatherly man", "formal"): ["a distinguished", "a classic", "a dapper", "a refined", "a sexy"],

    # ATHLETIC - sporty descriptors (includes "sexy" option)
    ("young woman", "athletic"): ["a sporty", "a cute", "a trendy", "an athletic", "a sexy"],
    ("adult woman", "athletic"): ["a sleek", "a sporty", "a stylish", "an athletic", "a sexy"],
    ("motherly woman", "athletic"): ["a practical", "a comfortable", "a sporty", "an athletic", "a sexy"],
    ("young man", "athletic"): ["a sporty", "a cool", "an athletic", "a fresh", "a sexy"],
    ("adult man", "athletic"): ["a sporty", "an athletic", "a sharp", "a performance", "a sexy"],
    ("fatherly man", "athletic"): ["a classic", "a practical", "a sporty", "a comfortable", "a sexy"],

    # SWIMSUIT - beach/pool appropriate descriptors (includes "sexy" option)
    ("young woman", "swimsuit"): ["a cute", "a trendy", "a stylish", "a fun", "a sexy"],
    ("adult woman", "swimsuit"): ["a chic", "a stylish", "a flattering", "a sophisticated", "a sexy"],
    ("motherly woman", "swimsuit"): ["a flattering", "a comfortable", "a classic", "a stylish", "a sexy"],
    ("young man", "swimsuit"): ["a cool", "a trendy", "a casual", "a fun", "a sexy"],
    ("adult man", "swimsuit"): ["a sharp", "a classic", "a stylish", "a comfortable", "a sexy"],
    ("fatherly man", "swimsuit"): ["a classic", "a comfortable", "a practical", "a casual", "a sexy"],

    # UNDERWEAR - comfortable/loungewear descriptors (no "sexy" - handled by tier system)
    ("young woman", "underwear"): ["a cute", "a comfy", "a trendy", "a soft"],
    ("adult woman", "underwear"): ["a chic", "a comfortable", "an elegant", "a stylish"],
    ("motherly woman", "underwear"): ["a comfortable", "a practical", "a soft", "a cozy"],
    ("young man", "underwear"): ["a comfy", "a basic", "a simple", "a casual"],
    ("adult man", "underwear"): ["a simple", "a comfortable", "a basic", "a classic"],
    ("fatherly man", "underwear"): ["a comfortable", "a practical", "a simple", "a classic"],

    # UNIFORM - professional/standard descriptors (no "sexy" - uniforms are standardized)
    ("young woman", "uniform"): ["a neat", "a crisp", "a proper", "a standard"],
    ("adult woman", "uniform"): ["a professional", "a neat", "a crisp", "a proper"],
    ("motherly woman", "uniform"): ["a professional", "a neat", "a proper", "a standard"],
    ("young man", "uniform"): ["a neat", "a crisp", "a proper", "a standard"],
    ("adult man", "uniform"): ["a professional", "a neat", "a crisp", "a sharp"],
    ("fatherly man", "uniform"): ["a professional", "a distinguished", "a proper", "a neat"],
}

# Colors for formal outfits (female archetypes only)
# Each archetype has ~20 colors with some overlap
FORMAL_COLORS = {
    "young woman": [
        "black", "navy", "burgundy", "emerald", "gold", "silver",
        "blush pink", "baby blue", "lavender", "hot pink", "coral",
        "mint green", "peach", "lilac", "sky blue", "rose",
        "champagne", "periwinkle", "fuchsia", "turquoise", "soft yellow",
    ],
    "adult woman": [
        "black", "navy", "burgundy", "emerald", "gold", "silver",
        "champagne", "wine red", "cobalt blue", "ivory", "plum",
        "forest green", "sapphire", "copper", "charcoal", "ruby red",
        "midnight blue", "bronze", "deep teal", "cream", "hunter green",
    ],
    "motherly woman": [
        "black", "navy", "burgundy", "emerald", "gold", "silver",
        "mauve", "teal", "rose gold", "slate blue", "dusty rose",
        "deep purple", "cranberry", "pearl", "olive", "aubergine",
        "taupe", "rich chocolate", "peacock blue", "merlot", "sage green",
    ],
}

# Colors for swimsuit outfits (female archetypes only)
# Beach/pool appropriate colors for each age group
SWIMSUIT_COLORS = {
    "young woman": [
        # Shared
        "black", "navy", "white", "coral", "turquoise", "red",
        # Bright/vibrant
        "hot pink", "neon orange", "electric blue", "lime green", "sunny yellow",
        # Pastels
        "baby pink", "lavender", "mint", "peach", "sky blue",
        # Trendy
        "tie-dye", "tropical print", "watermelon pink",
    ],
    "adult woman": [
        # Shared
        "black", "navy", "white", "coral", "turquoise", "red",
        # Classic bold
        "emerald", "cobalt blue", "cherry red", "royal blue",
        # Sophisticated
        "olive", "rust", "bronze", "burgundy", "forest green",
        # Patterns
        "animal print", "tropical print", "classic stripe",
    ],
    "motherly woman": [
        # Shared
        "black", "navy", "white", "coral", "turquoise", "red",
        # Classic/flattering
        "deep teal", "burgundy", "plum", "forest green", "royal blue",
        # Muted tones
        "slate blue", "olive", "rust", "berry", "deep coral",
        # Subtle patterns
        "subtle stripe", "classic navy and white", "muted floral",
    ],
}

# Occasions by (archetype, outfit_type) - provides context for outfit generation
# Values can be strings or lists (lists are randomly chosen from for variety)
OCCASIONS = {
    # FORMAL - Female archetypes get variety lists
    ("young woman", "formal"): [
        "going to prom",
        "attending a homecoming dance",
        "going to a winter formal",
        "attending a sorority formal",
        "going to a graduation dinner",
        "attending a sweet sixteen party",
    ],
    ("adult woman", "formal"): [
        "attending a cocktail party",
        "going to a wedding as a guest",
        "attending a gallery opening",
        "going to a charity gala",
        "attending an awards ceremony",
        "going to a black-tie dinner",
    ],
    ("motherly woman", "formal"): [
        "attending a gala",
        "going to a special occasion dinner",
        "attending a charity fundraiser",
        "going to an anniversary celebration",
        "attending an awards banquet",
        "going to the opera or symphony",
    ],
    ("young man", "formal"): [
        "going to prom",
        "attending a homecoming dance",
        "going to a winter formal",
        "attending a graduation dinner",
        "going to a fraternity formal",
        "attending a family wedding",
    ],
    ("adult man", "formal"): [
        "attending a wedding as a guest",
        "going to a business formal event",
        "attending a cocktail party",
        "going to a charity gala",
        "attending an awards dinner",
        "going to a formal date night",
    ],
    ("fatherly man", "formal"): [
        "attending a formal dinner",
        "going to an awards ceremony",
        "attending a charity gala",
        "going to a business banquet",
        "attending an anniversary dinner",
        "going to the theater or opera",
    ],

    # CASUAL
    ("young woman", "casual"): [
        "going to class",
        "hanging out with friends",
        "grabbing coffee",
        "going to the mall",
        "attending a movie night",
        "going on a casual date",
        "studying at a coffee shop",
        "going to weekend brunch",
    ],
    ("adult woman", "casual"): [
        "running weekend errands",
        "grabbing coffee with a friend",
        "doing some casual shopping",
        "a relaxed weekend afternoon",
        "working from home",
        "meeting a friend for lunch",
        "a casual day off",
        "hanging out on the weekend",
    ],
    ("motherly woman", "casual"): [
        "running errands",
        "picking up the kids",
        "at a school pickup",
        "going to weekend activities",
        "having coffee with friends",
        "going to a casual lunch",
        "doing weekend shopping",
        "at a backyard barbecue",
    ],
    ("young man", "casual"): [
        "hanging out with friends",
        "going to a casual party",
        "catching a movie",
        "playing video games with buddies",
        "grabbing food with friends",
        "going to a weekend hangout",
        "attending a house party",
        "chilling on campus",
    ],
    ("adult man", "casual"): [
        "going to weekend brunch",
        "on a casual date",
        "watching the game at a sports bar",
        "attending a barbecue",
        "hanging out with buddies",
        "running weekend errands",
        "going to a casual dinner",
        "relaxing on the weekend",
    ],
    ("fatherly man", "casual"): [
        "hosting a weekend barbecue",
        "running errands",
        "at a casual family outing",
        "watching the game with friends",
        "attending a neighborhood gathering",
        "going to a casual lunch",
        "doing weekend yard work",
        "taking the family out",
    ],

    # ATHLETIC
    ("young woman", "athletic"): "going to yoga class or working out at the gym",
    ("adult woman", "athletic"): "going for a morning run or attending a fitness class",
    ("motherly woman", "athletic"): "going for a jog or doing yoga",
    ("young man", "athletic"): "playing basketball or working out at the gym",
    ("adult man", "athletic"): "going for a run or hitting the gym",
    ("fatherly man", "athletic"): "going for a morning jog or playing golf",

    # SWIMSUIT
    ("young woman", "swimsuit"): "at the beach with friends or a pool party",
    ("adult woman", "swimsuit"): "relaxing at a resort or on a beach vacation",
    ("motherly woman", "swimsuit"): "at a family beach day or the neighborhood pool",
    ("young man", "swimsuit"): "at the beach with friends or a pool party",
    ("adult man", "swimsuit"): "at a beach resort or a pool club",
    ("fatherly man", "swimsuit"): "at a family pool day or the beach with kids",

    # UNDERWEAR
    ("young woman", "underwear"): "lounging at home or getting ready for the day",
    ("adult woman", "underwear"): "getting ready for a date night or relaxing at home",
    ("motherly woman", "underwear"): "for everyday wear around the house",
    ("young man", "underwear"): "lounging at home or getting ready for the day",
    ("adult man", "underwear"): "for everyday basics or getting ready in the morning",
    ("fatherly man", "underwear"): "for everyday wear around the house",

    # UNIFORM
    ("young woman", "uniform"): "Japanese school uniform",
    ("adult woman", "uniform"): "working at an office or in a medical setting",
    ("motherly woman", "uniform"): "working at an office or in a medical setting",
    ("young man", "uniform"): "Japanese school uniform",
    ("adult man", "uniform"): "working at an office or in a service industry",
    ("fatherly man", "uniform"): "in a managerial role or professional setting",
}


def generate_outfit_description(
    api_key: str,
    outfit_type: str,
    archetype_label: str,
) -> str:
    """
    Generate an outfit description using Gemini text API.

    Combines archetype-specific age ranges, style words, and occasion context
    to produce varied, attractive outfit descriptions.

    Args:
        api_key: Google Gemini API key.
        outfit_type: Type of outfit (formal, casual, athletic, swimsuit, underwear, uniform).
        archetype_label: Character archetype (e.g., "young woman", "adult man").

    Returns:
        Generated outfit description string.
    """
    from .gemini_client import call_gemini_text

    # Get archetype-specific data
    age = AGE_RANGES.get(archetype_label, "20-35")
    occasion_data = OCCASIONS.get((archetype_label, outfit_type), f"a {outfit_type} occasion")
    # Support both string and list values (lists provide variety)
    occasion = random.choice(occasion_data) if isinstance(occasion_data, list) else occasion_data
    # Style words now keyed by (archetype, outfit_type) to avoid "elegant casual" oxymorons
    style_word = random.choice(STYLE_WORDS.get((archetype_label, outfit_type), ["a stylish"]))
    gender_word = "woman" if archetype_label.endswith("woman") else "man"

    # Use specific clothing type for certain outfits to avoid deviation
    if outfit_type == "swimsuit":
        clothing_word = "swimsuit"
    elif outfit_type == "athletic":
        clothing_word = "athletic wear"
    else:
        clothing_word = "outfit"

    # Add color hint for formal and swimsuit female outfits (50% of the time)
    color_hint = ""
    if random.random() < 0.5:
        if outfit_type == "formal" and archetype_label in FORMAL_COLORS:
            color = random.choice(FORMAL_COLORS[archetype_label])
            color_hint = f" The outfit should be {color}."
        elif outfit_type == "swimsuit" and archetype_label in SWIMSUIT_COLORS:
            color = random.choice(SWIMSUIT_COLORS[archetype_label])
            color_hint = f" The swimsuit should be {color}."

    # Build prompt
    prompt = f"""Describe {style_word} {clothing_word} for a {gender_word} aged {age} {occasion}.
One brief sentence with specific colors. No preamble, no commentary. Do not mention footwear.{color_hint}"""

    # Call Gemini text API
    description = call_gemini_text(api_key, prompt, temperature=1.0)

    return description


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
        "IMPORTANT: Keep the exact same hair length - do not make the hair shorter or longer. The hair must reach the same point on the body as in the original. You may change the hair style to better suit the outfit."
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
    if gender_style == "f":
        uniform_desc = (
            "a vibrant navy blue sleeveless blazer with a traditional waistcoat-style hem, outlined with thin gold piping along the lapels and bottom edge. "
            "The vest has no emblems or crests on it. "
            "Four gold buttons in a double-breasted 2x2 arrangement positioned at the waist. "
            "Underneath is a white short-sleeved collared dress shirt with thin blue piping around the collar. "
            "A rectangular gold/orange vertical school crest patch on the left sleeve of the white shirt. "
            "A solid red necktie with no pattern. "
            "A short vibrant magenta-red plaid pleated skirt with a tartan pattern and gold trim at the bottom hem"
        )
    else:
        uniform_desc = (
            "a white short-sleeved collared dress shirt with thin dark piping on the collar edge and a small chest pocket on the left breast. "
            "A gold/orange rectangular school crest patch on the left sleeve only. "
            "A solid red necktie with two thin horizontal silver stripes. "
            "Dark navy blue dress trousers with a dark brown leather belt with a gold rectangular buckle. "
            "The shirt is neatly tucked into the trousers"
        )

    # Match the structure of build_outfit_prompt which works correctly
    return (
        f"Edit the character's clothes to match this school uniform: {uniform_desc}. "
        "Don't change the size, proportions, framing, or art style of the character. "
        "IMPORTANT: Keep the exact same hair length - do not make the hair shorter or longer. The hair must reach the same point on the body as in the original. You may change the hair style to better suit the outfit. "
        "Give the character a black background behind them. "
        "Make sure the head, arms, hair, hands, and clothes are all kept within the image."
    )


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
        "IMPORTANT: The character must appear to be 18 years old or older. If the concept describes a younger character, depict them as a young adult (18+) instead. "
        "Match the art style and rendering of the attached reference character images so the new character has clean line art and vibrant, but not overly saturated colors, that make it look like it came from the same artist. "
        "Have them facing mostly toward the viewer in a friendly, neutral pose, that would work as a base sprite. "
        "They should not be holding anything in their hands. "
        f"Give the character a {bg} background behind them. "
        "Make sure the head, arms, hair, hands, and clothes are all kept within the image."
    )


def build_normalize_image_prompt() -> str:
    """
    Prompt to normalize an uploaded image (sharpen, black background).

    Used in image mode to clean up the source image before further processing.

    Returns:
        Prompt string for image normalization.
    """
    return (
        "IMPORTANT: If the character appears to be under 18 years old, edit their appearance to look like a young adult (18+) while preserving their overall design and style. "
        "Sharpen the image to at least 720p resolution if it is lower than that and "
        "correct any artifacts of blurriness. Don't change the size, proportions, "
        "framing, or art style of the character. Give the character a black (#000000) "
        "background behind them. Make sure the head, arms, hair, hands, and clothes "
        "are all kept within the image."
    )


def build_character_modification_prompt(user_instructions: str) -> str:
    """
    Prompt to modify a character based on user instructions.

    Used when user wants to change aspects of the character (hair, clothes, etc.)
    while maintaining the same art style.

    Args:
        user_instructions: User's description of desired changes.

    Returns:
        Prompt string for character modification.
    """
    return (
        f"Modify this character based on the following instructions: {user_instructions} "
        "Maintain the same art style, proportions, and overall character design. Apply "
        "the requested changes while keeping the character recognizable. Give the "
        "character a black (#000000) background behind them. Make sure the head, arms, "
        "hair, hands, and clothes are all kept within the image."
    )


# =============================================================================
# Outfit Prompt Utilities
# =============================================================================
# Note: The old CSV-based load_outfit_prompts() function has been removed.
# See src/sprite_creator/data/_stashed_csv_system/README.md for rollback instructions.


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
    api_key: str,
    archetype_label: str,
    gender_style: str,
    selected_outfit_keys: List[str],
    outfit_prompt_config: Dict[str, Dict[str, Optional[str]]],
) -> Dict[str, str]:
    """
    Build one prompt per selected outfit_key, honoring per-outfit settings.

    For each key:
      - use_random=True: Generate dynamic outfit description via Gemini text API.
      - use_random=False: use custom_prompt (fallback if empty for safety).

    Special case: Underwear does NOT use Gemini text API due to high safety filter
    rates. Instead, it uses a tiered fallback system handled by pose_processor.
    This function returns a placeholder for underwear; the actual prompt is
    determined at generation time.

    Args:
        api_key: Google Gemini API key (required for random outfit generation).
        archetype_label: Character archetype.
        gender_style: 'f' or 'm'.
        selected_outfit_keys: List of outfit keys to generate.
        outfit_prompt_config: Per-outfit configuration settings.

    Returns:
        {outfit_key: prompt_text}
    """
    from ..config import UNDERWEAR_FALLBACK_TIERS

    prompts: Dict[str, str] = {}

    for key in selected_outfit_keys:
        config = outfit_prompt_config.get(key, {})
        use_random = bool(config.get("use_random", True))
        custom_prompt = config.get("custom_prompt")

        # Special handling for underwear - uses tier system, not Gemini text
        if key == "underwear" and use_random:
            # Return first tier prompt as placeholder; actual prompt determined at generation time
            tiers = UNDERWEAR_FALLBACK_TIERS.get(archetype_label, ["Pink undergarments"])
            prompts[key] = tiers[0] if tiers else "Pink undergarments"
            continue

        if use_random:
            # Generate dynamic outfit description via Gemini text API
            try:
                prompts[key] = generate_outfit_description(api_key, key, archetype_label)
            except Exception as e:
                print(f"[WARN] Failed to generate outfit description for {key}: {e}")
                # Fallback to generic description
                prompts[key] = build_simple_outfit_description(key, gender_style)
        else:
            # Use custom prompt, or fallback if empty
            prompts[key] = custom_prompt or build_simple_outfit_description(key, gender_style)

    return prompts
