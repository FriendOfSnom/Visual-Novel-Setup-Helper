"""
Pose processing and outfit generation.

Handles initial pose normalization, outfit generation, pose flattening,
and character.yml writing.
"""

import random
import shutil
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml
from PIL import Image

from ..api.exceptions import GeminiAPIError, GeminiSafetyError
from ..api.gemini_client import (
    call_gemini_image_edit,
    call_gemini_text_or_refs,
    load_image_as_base64,
    strip_background_ai,
    cleanup_edge_halos,
    REMBG_EDGE_CLEANUP_TOLERANCE,
    REMBG_EDGE_CLEANUP_PASSES,
)
from ..api.prompt_builders import (
    build_initial_pose_prompt,
    build_outfit_prompt,
    build_standard_school_uniform_prompt,
)
from ..config import (
    SAFETY_FALLBACK_UNDERWEAR_PROMPTS,
    SAFETY_FALLBACK_UNDERWEAR_TIER4,
    SAFETY_FALLBACK_ATHLETIC_UNDERWEAR,
)
from .image_utils import (
    save_image_bytes_as_png,
    get_standard_uniform_reference_images,
)


def write_character_yml(
    path: Path,
    display_name: str,
    voice: str,
    eye_line: float,
    name_color: str,
    scale: float,
    poses: Dict[str, Dict[str, str]],
    *,
    game: Optional[str] = None,
) -> None:
    """
    Write final character metadata YAML in organizer format.

    Args:
        path: Path to character.yml file.
        display_name: Character's display name.
        voice: Character voice ("girl"/"boy", converted to "male" if "boy").
        eye_line: Eye line ratio (0.0-1.0).
        name_color: Hex color for name display.
        scale: Character scale multiplier.
        poses: Dict of pose letters to pose metadata.
        game: Optional game name to include in metadata.
    """
    v = (voice or "").lower()
    voice_out = "male" if v == "boy" else voice

    data = {
        "display_name": display_name,
        "eye_line": round(float(eye_line), 4),
        "name_color": name_color,
        "poses": poses,
        "scale": float(scale),
        "voice": voice_out,
    }
    if game:
        data["game"] = game

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.dump(data, f, sort_keys=False, allow_unicode=True)

    print(f"[INFO] Wrote character YAML to: {path}")


def generate_initial_pose_once(
    api_key: str,
    image_path: Path,
    out_stem: Path,
    gender_style: str,
    archetype_label: str = "",
    additional_instructions: str = "",
) -> Path:
    """
    Normalize the original sprite into pose A.

    Returns the raw Gemini output (no background removal). This serves as the
    template for all outfits - background removal happens per-outfit later.

    Args:
        api_key: Gemini API key.
        image_path: Source image path.
        out_stem: Output path stem (without extension).
        gender_style: 'f' or 'm'.
        archetype_label: Character archetype (e.g., "young woman", "adult man").
        additional_instructions: Optional extra instructions to append to the prompt.

    Returns:
        Path to saved normalized pose image (with solid background from Gemini).
    """
    print("  [Gemini] Normalizing base pose...")
    image_b64 = load_image_as_base64(image_path)
    # Use black background - this will be the template for outfit generation
    prompt = build_initial_pose_prompt(
        gender_style, archetype_label, "solid black (#000000)", additional_instructions
    )

    # Get raw Gemini output - NO background removal (that happens per-outfit)
    img_bytes = call_gemini_image_edit(api_key, prompt, image_b64, skip_background_removal=True)
    final_path = save_image_bytes_as_png(img_bytes, out_stem)
    print(f"  Saved base pose to: {final_path}")
    return final_path


def _generate_outfit_with_safety_recovery(
    api_key: str,
    base_pose_path: Path,
    gender_style: str,
    outfit_key: str,
    outfit_desc: str,
    outfit_database: Dict[str, Dict[str, List[str]]],
    archetype_label: str,
    outfit_prompt_config: Dict[str, Dict[str, Optional[str]]],
    skip_background_removal: bool = False,
) -> bytes:
    """
    Generate outfit with 3-tier safety error recovery.

    Tier 1: Retry same prompt once
    Tier 2: Pick new random CSV prompt (if available)
    Tier 3: Use archetype-specific modest fallback

    AI background removal is automatically applied unless skip_background_removal=True.

    Args:
        api_key: Gemini API key.
        base_pose_path: Path to base pose image.
        gender_style: 'f' or 'm'.
        outfit_key: Outfit identifier.
        outfit_desc: Initial outfit description/prompt.
        outfit_database: All loaded CSV prompts.
        archetype_label: Character archetype.
        outfit_prompt_config: Per-outfit configuration.
        skip_background_removal: If True, return raw Gemini output without rembg.

    Returns:
        Generated outfit image bytes (with or without transparent background).

    Raises:
        GeminiAPIError: If all recovery tiers fail.
    """
    image_b64 = load_image_as_base64(base_pose_path)
    tried_prompts = set()
    # Use black background for clean AI removal
    background_color = "solid black (#000000)"

    def try_generate(desc: str, tier_name: str) -> Optional[bytes]:
        tried_prompts.add(desc)
        try:
            prompt = build_outfit_prompt(desc, gender_style, background_color)
            return call_gemini_image_edit(api_key, prompt, image_b64, skip_background_removal)
        except GeminiSafetyError as e:
            print(f"[WARN] {tier_name}: Safety error during '{outfit_key}' generation")
            print(f"[WARN] Blocked prompt: \"{desc[:100]}{'...' if len(desc) > 100 else ''}\"")
            if e.safety_ratings:
                print(f"[WARN] Safety ratings: {e.safety_ratings}")
            return None
        except GeminiAPIError as e:
            print(f"[WARN] {tier_name}: API error during '{outfit_key}' generation: {e}")
            return None

    # Tier 1: Try original prompt
    print(f"  [Safety] Attempting '{outfit_key}' generation...")
    img_bytes = try_generate(outfit_desc, "Tier 1")
    if img_bytes:
        return img_bytes

    # Tier 1 Retry
    print(f"[INFO] Tier 1 Recovery: Retrying same prompt once...")
    img_bytes = try_generate(outfit_desc, "Tier 1 Retry")
    if img_bytes:
        print(f"[INFO] Tier 1 Recovery: Retry succeeded")
        return img_bytes

    print(f"[WARN] Tier 1 Recovery: Retry failed")

    # Tier 2: New random CSV prompt (underwear only, random mode only)
    if outfit_key == "underwear":
        config = outfit_prompt_config.get(outfit_key, {})
        if config.get("use_random", True):
            archetype_prompts = outfit_database.get(archetype_label, {})
            available_prompts = archetype_prompts.get(outfit_key, [])
            untried = [p for p in available_prompts if p not in tried_prompts]

            if untried:
                new_desc = random.choice(untried)
                print(f"[INFO] Tier 2 Recovery: Selecting new random prompt from CSV...")
                print(f"[INFO] New prompt: \"{new_desc[:100]}{'...' if len(new_desc) > 100 else ''}\"")

                img_bytes = try_generate(new_desc, "Tier 2")
                if img_bytes:
                    print(f"[INFO] Tier 2 Recovery: New prompt succeeded")
                    return img_bytes

                print(f"[WARN] Tier 2 Recovery: New prompt also blocked")
            else:
                print(f"[INFO] Tier 2 Recovery: No untried CSV prompts available")
        else:
            print(f"[INFO] Tier 2 Recovery: Skipped (not using random prompts)")
    else:
        print(f"[INFO] Tier 2 Recovery: Skipped (not underwear outfit)")

    # Tier 3: Archetype-specific modest fallback
    fallback = SAFETY_FALLBACK_UNDERWEAR_PROMPTS.get(archetype_label)

    if fallback and fallback not in tried_prompts:
        print(f"[INFO] Tier 3 Recovery: Using archetype-specific modest fallback")
        print(f"[INFO] Fallback prompt: \"{fallback[:100]}{'...' if len(fallback) > 100 else ''}\"")

        img_bytes = try_generate(fallback, "Tier 3")
        if img_bytes:
            print(f"[INFO] Tier 3 Recovery: Fallback succeeded")
            return img_bytes

    # Tier 4: Ultra-generic prompt (no specific garment names)
    tier4_fallback = SAFETY_FALLBACK_UNDERWEAR_TIER4.get(archetype_label)
    if tier4_fallback and tier4_fallback not in tried_prompts:
        print(f"[INFO] Tier 4 Recovery: Using ultra-generic prompt")
        print(f"[INFO] Ultra-generic prompt: \"{tier4_fallback}\"")

        img_bytes = try_generate(tier4_fallback, "Tier 4")
        if img_bytes:
            print(f"[INFO] Tier 4 Recovery: Ultra-generic prompt succeeded")
            return img_bytes

    # Tier 5: Athletic underwear alternative (sports bra + running shorts)
    athletic_alt = SAFETY_FALLBACK_ATHLETIC_UNDERWEAR.get(archetype_label)
    if athletic_alt and athletic_alt not in tried_prompts:
        print(f"[INFO] Tier 5 Recovery: Trying athletic underwear alternative")
        print(f"[INFO] Athletic prompt: \"{athletic_alt}\"")

        img_bytes = try_generate(athletic_alt, "Tier 5")
        if img_bytes:
            print(f"[INFO] Tier 5 Recovery: Athletic alternative succeeded")
            return img_bytes

    # All tiers exhausted - return None to skip gracefully
    print(
        f"[WARN] All recovery tiers exhausted for outfit '{outfit_key}' "
        f"(archetype: {archetype_label}). Skipping this outfit."
    )
    return None


def generate_single_outfit(
    api_key: str,
    base_pose_path: Path,
    outfits_dir: Path,
    gender_style: str,
    outfit_key: str,
    outfit_desc: str,
    outfit_prompt_config: Dict[str, Dict[str, Optional[str]]],
    archetype_label: str,
    outfit_database: Dict[str, Dict[str, List[str]]],
    for_interactive_review: bool = False,
) -> Optional[Path] | Optional[Tuple[Path, bytes, bytes]]:
    """
    Generate or regenerate a single outfit image for the given key.

    This is used both by the bulk outfit generator and by the
    per-outfit "regenerate" buttons in the review window.
    AI background removal is automatically applied.

    Args:
        api_key: Gemini API key.
        base_pose_path: Path to base pose image.
        outfits_dir: Directory to save outfits.
        gender_style: 'f' or 'm'.
        outfit_key: Outfit identifier.
        outfit_desc: Outfit description/prompt.
        outfit_prompt_config: Per-outfit configuration.
        archetype_label: Character archetype.
        outfit_database: All loaded CSV prompts for safety recovery.
        for_interactive_review: If True, return (path, original_bytes, rembg_bytes)
            so the review UI can apply custom edge cleanup settings.

    Returns:
        If for_interactive_review=False: Path to saved outfit, or None if failed.
        If for_interactive_review=True: (path, original_bytes, rembg_bytes), or None if failed.
    """
    outfits_dir.mkdir(parents=True, exist_ok=True)

    config = outfit_prompt_config.get(outfit_key, {})

    # Special handling for standardized school uniform
    if outfit_key == "uniform" and config.get("use_standard_uniform"):
        result = generate_standard_uniform_outfit(
            api_key,
            base_pose_path,
            outfits_dir,
            gender_style,
            archetype_label,
            outfit_desc,
            for_interactive_review=for_interactive_review,
        )
        if result is None:
            return None
        if for_interactive_review:
            final_path, original_bytes, rembg_bytes = result
            print(f"  Saved standardized outfit '{outfit_key}' to: {final_path}")
            return (final_path, original_bytes, rembg_bytes)
        else:
            print(f"  Saved standardized outfit '{outfit_key}' to: {result}")
            return result

    # Normal text-prompt-based outfit with safety recovery
    out_stem = outfits_dir / outfit_key.capitalize()

    try:
        if for_interactive_review:
            # Get raw Gemini output (no rembg yet)
            original_bytes = _generate_outfit_with_safety_recovery(
                api_key,
                base_pose_path,
                gender_style,
                outfit_key,
                outfit_desc,
                outfit_database,
                archetype_label,
                outfit_prompt_config,
                skip_background_removal=True,
            )

            if original_bytes is None:
                print(f"[WARN] Skipping outfit '{outfit_key}' - could not generate safely")
                return None

            # Run rembg without edge cleanup (user will apply cleanup in review UI)
            rembg_bytes = strip_background_ai(original_bytes, skip_edge_cleanup=True)

            # Save rembg result initially (may be updated after review)
            final_path = save_image_bytes_as_png(rembg_bytes, out_stem)
            print(f"  Saved outfit '{outfit_key}' to: {final_path}")
            return (final_path, original_bytes, rembg_bytes)
        else:
            # Normal flow: full background removal with default edge cleanup
            img_bytes = _generate_outfit_with_safety_recovery(
                api_key,
                base_pose_path,
                gender_style,
                outfit_key,
                outfit_desc,
                outfit_database,
                archetype_label,
                outfit_prompt_config,
            )

            if img_bytes is None:
                print(f"[WARN] Skipping outfit '{outfit_key}' - could not generate safely")
                return None

            final_path = save_image_bytes_as_png(img_bytes, out_stem)
            print(f"  Saved outfit '{outfit_key}' to: {final_path}")
            return final_path
    except GeminiSafetyError as e:
        # This should not happen (recovery should handle it), but just in case
        print(f"[ERROR] Unrecovered safety error for outfit '{outfit_key}': {e}")
        raise


def generate_standard_uniform_outfit(
    api_key: str,
    base_pose_path: Path,
    outfits_dir: Path,
    gender_style: str,
    archetype_label: str,
    outfit_desc: str,  # Kept for signature compatibility
    for_interactive_review: bool = False,
) -> Path | Tuple[Path, bytes, bytes]:
    """
    Generate the standardized school uniform outfit using reference images.

    Uses the base pose as the main character to keep, and a cropped uniform
    reference image (gender-specific) as visual guidance.
    AI background removal is automatically applied.

    Args:
        api_key: Gemini API key.
        base_pose_path: Path to base pose image.
        outfits_dir: Directory to save outfits.
        gender_style: 'f' or 'm'.
        archetype_label: Character archetype.
        outfit_desc: Not used directly, kept for compatibility.
        for_interactive_review: If True, return (path, original_bytes, rembg_bytes).

    Returns:
        If for_interactive_review=False: Path to saved uniform outfit.
        If for_interactive_review=True: (path, original_bytes, rembg_bytes).
    """
    outfits_dir.mkdir(parents=True, exist_ok=True)
    # Use black background for clean AI removal
    background_color = "solid black (#000000)"

    # Collect the uniform reference image(s) for this gender
    uniform_refs = get_standard_uniform_reference_images(gender_style)

    if not uniform_refs:
        # Fallback to normal outfit prompt path
        print("[WARN] No uniform reference found, falling back to normal prompt-based uniform.")
        image_b64 = load_image_as_base64(base_pose_path)
        prompt = build_outfit_prompt(outfit_desc, gender_style, background_color)

        if for_interactive_review:
            original_bytes = call_gemini_image_edit(api_key, prompt, image_b64, skip_background_removal=True)
            rembg_bytes = strip_background_ai(original_bytes, skip_edge_cleanup=True)
            out_stem = outfits_dir / "Uniform"
            final_path = save_image_bytes_as_png(rembg_bytes, out_stem)
            print(f"  Saved fallback prompt-based uniform to: {final_path}")
            return (final_path, original_bytes, rembg_bytes)
        else:
            img_bytes = call_gemini_image_edit(api_key, prompt, image_b64)
            out_stem = outfits_dir / "Uniform"
            final_path = save_image_bytes_as_png(img_bytes, out_stem)
            print(f"  Saved fallback prompt-based uniform to: {final_path}")
            return final_path

    # Use first uniform reference
    uniform_ref = uniform_refs[0]
    print(f"[INFO] Using uniform reference: {uniform_ref}")

    # Build unified, standardized uniform prompt
    uniform_prompt = build_standard_school_uniform_prompt(
        archetype_label,
        gender_style,
        background_color,
    )

    # Call Gemini with prompt and two reference images:
    #   1) the base pose (the character to keep)
    #   2) the cropped uniform example (clothes to copy)
    if for_interactive_review:
        original_bytes = call_gemini_text_or_refs(
            api_key,
            uniform_prompt,
            ref_images=[base_pose_path, uniform_ref],
            skip_background_removal=True,
        )
        rembg_bytes = strip_background_ai(original_bytes, skip_edge_cleanup=True)
        out_stem = outfits_dir / "Uniform"
        final_path = save_image_bytes_as_png(rembg_bytes, out_stem)
        print(f"  Saved standardized school uniform to: {final_path}")
        return (final_path, original_bytes, rembg_bytes)
    else:
        img_bytes = call_gemini_text_or_refs(
            api_key,
            uniform_prompt,
            ref_images=[base_pose_path, uniform_ref],
        )
        out_stem = outfits_dir / "Uniform"
        final_path = save_image_bytes_as_png(img_bytes, out_stem)
        print(f"  Saved standardized school uniform to: {final_path}")
        return final_path


def generate_outfits_once(
    api_key: str,
    base_pose_path: Path,
    outfits_dir: Path,
    gender_style: str,
    outfit_descriptions: Dict[str, str],
    outfit_prompt_config: Dict[str, Dict[str, Optional[str]]],
    archetype_label: str,
    outfit_database: Dict[str, Dict[str, List[str]]],
    include_base_outfit: bool = True,
    for_interactive_review: bool = False,
) -> List[Path] | Tuple[List[Path], List[Tuple[bytes, bytes]]]:
    """
    Generate outfits for a pose.

    Layout:
      - If include_base_outfit=True: copies base pose as Base.png.
      - For each outfit_descriptions[key], generate <Key>.png.

    AI background removal is automatically applied to all generated outfits.

    Args:
        api_key: Gemini API key.
        base_pose_path: Path to base pose image.
        outfits_dir: Directory to save outfits.
        gender_style: 'f' or 'm'.
        outfit_descriptions: Dict of outfit keys to descriptions.
        outfit_prompt_config: Per-outfit configuration.
        archetype_label: Character archetype.
        outfit_database: All loaded CSV prompts for safety recovery.
        include_base_outfit: Whether to include base pose as an outfit.
        for_interactive_review: If True, return cleanup data for review UI.

    Returns:
        If for_interactive_review=False: List of paths to generated outfit images.
        If for_interactive_review=True: (paths, cleanup_data) where cleanup_data is
            list of (original_bytes, rembg_bytes) tuples for each outfit.
    """
    outfits_dir.mkdir(parents=True, exist_ok=True)
    paths: List[Path] = []
    cleanup_data: List[Tuple[bytes, bytes]] = []

    # Optional: include base pose as "Base.png" outfit (with background removal)
    if include_base_outfit:
        base_bytes = base_pose_path.read_bytes()  # Original with solid background
        base_out_path = (outfits_dir / "Base").with_suffix(".png")

        if for_interactive_review:
            # Run rembg without edge cleanup (user will apply cleanup in review UI)
            rembg_bytes = strip_background_ai(base_bytes, skip_edge_cleanup=True)
            # Save rembg result initially (may be updated after review)
            base_img = Image.open(BytesIO(rembg_bytes)).convert("RGBA")
            base_img.save(base_out_path, format="PNG", compress_level=0, optimize=False)
            paths.append(base_out_path)
            cleanup_data.append((base_bytes, rembg_bytes))
        else:
            # Normal flow: full background removal with default edge cleanup
            processed_bytes = strip_background_ai(base_bytes)
            base_img = Image.open(BytesIO(processed_bytes)).convert("RGBA")
            base_img.save(base_out_path, format="PNG", compress_level=0, optimize=False)
            paths.append(base_out_path)

    # Generate each selected outfit key
    for key, desc in outfit_descriptions.items():
        result = generate_single_outfit(
            api_key,
            base_pose_path,
            outfits_dir,
            gender_style,
            key,
            desc,
            outfit_prompt_config,
            archetype_label,
            outfit_database,
            for_interactive_review=for_interactive_review,
        )

        if result is None:
            continue

        if for_interactive_review:
            final_path, original_bytes, rembg_bytes = result
            paths.append(final_path)
            cleanup_data.append((original_bytes, rembg_bytes))
        else:
            paths.append(result)

    if for_interactive_review:
        return (paths, cleanup_data)
    return paths


def flatten_pose_outfits_to_letter_poses(char_dir: Path) -> List[str]:
    """
    Flatten pose/outfit combos into separate letter poses with single outfits.

    Input:
        <char>/a/outfits/OutfitName.png
        <char>/a/faces/face/*.webp
        <char>/a/faces/OutfitName/*.webp

    Output:
        <char>/a, /b, /c, ... each with outfits/<OutfitName>.png (transparent base)
        and faces/face/0.webp..N.webp

    Args:
        char_dir: Character directory.

    Returns:
        List of final pose letters (sorted).
    """
    original_pose_dirs = [
        p for p in char_dir.iterdir()
        if p.is_dir() and len(p.name) == 1 and p.name.isalpha()
    ]
    original_pose_dirs.sort(key=lambda p: p.name)

    tmp_root = char_dir / "_tmp_pose_flattened"
    if tmp_root.exists():
        shutil.rmtree(tmp_root)
    tmp_root.mkdir(parents=True, exist_ok=True)

    letters = [chr(ord("a") + i) for i in range(26)]
    next_index = 0

    def _next_letter() -> Optional[str]:
        nonlocal next_index
        if next_index >= len(letters):
            return None
        letter = letters[next_index]
        next_index += 1
        return letter

    final_pose_letters: List[str] = []

    for pose_dir in original_pose_dirs:
        outfits_dir = pose_dir / "outfits"
        faces_root = pose_dir / "faces"

        if not outfits_dir.is_dir() or not faces_root.is_dir():
            continue

        for outfit_path in sorted(outfits_dir.iterdir()):
            if not outfit_path.is_file():
                continue
            if outfit_path.suffix.lower() not in (".png", ".webp"):
                continue

            outfit_name = outfit_path.stem
            if outfit_name.lower() == "base":
                src_expr_dir = faces_root / "face"
            else:
                src_expr_dir = faces_root / outfit_name

            if not src_expr_dir.is_dir():
                print(
                    f"[WARN] No expression folder for pose '{pose_dir.name}', "
                    f"outfit '{outfit_name}' at {src_expr_dir}; skipping."
                )
                continue

            pose_letter = _next_letter()
            if pose_letter is None:
                print(
                    "[WARN] Ran out of pose letters (more than 26 combinations); "
                    "skipping remaining outfits."
                )
                break

            new_pose_dir = tmp_root / pose_letter
            new_faces_dir = new_pose_dir / "faces" / "face"
            new_outfits_dir = new_pose_dir / "outfits"
            new_faces_dir.mkdir(parents=True, exist_ok=True)
            new_outfits_dir.mkdir(parents=True, exist_ok=True)

            # Copy expression files
            for src in sorted(src_expr_dir.iterdir()):
                if not src.is_file():
                    continue
                dest = new_faces_dir / src.name
                shutil.copy2(src, dest)

            # Create transparent outfit base
            try:
                outfit_img = Image.open(outfit_path).convert("RGBA")
                w, h = outfit_img.size
                transparent = Image.new("RGBA", (w, h), (0, 0, 0, 0))
                out_name = outfit_path.stem + outfit_path.suffix.lower()
                transparent.save(new_outfits_dir / out_name)
            except Exception as e:
                print(
                    f"[WARN] Failed to create transparent outfit for "
                    f"{pose_dir.name}/{outfit_name}: {e}"
                )
                continue

            final_pose_letters.append(pose_letter)
            print(
                f"[INFO] Created pose '{pose_letter}' from "
                f"orig pose '{pose_dir.name}', outfit '{outfit_name}'"
            )

    # Remove original pose directories
    for pose_dir in original_pose_dirs:
        try:
            shutil.rmtree(pose_dir)
        except Exception as e:
            print(f"[WARN] Failed to remove original pose folder {pose_dir}: {e}")

    # Move flattened poses to character directory
    for new_pose_dir in sorted(tmp_root.iterdir(), key=lambda p: p.name):
        if not new_pose_dir.is_dir():
            continue
        target = char_dir / new_pose_dir.name
        if target.exists():
            try:
                shutil.rmtree(target)
            except Exception:
                pass
        shutil.move(str(new_pose_dir), str(target))

    # Clean up temp directory
    try:
        shutil.rmtree(tmp_root)
    except Exception:
        pass

    final_pose_letters.sort()
    return final_pose_letters
