#!/usr/bin/env python3
"""
pipeline.py

Single-character visual novel sprite builder using Gemini.

This is the main orchestrator that coordinates the entire sprite generation workflow.
All heavy lifting has been refactored into the sprite_creator package modules.

Flow (per character):
  - Start from either an existing image or a prompt-generated base
  - Pick voice, name, archetype
  - Choose extra outfits + expressions
  - Normalize to pose A (mid-thigh, magenta bg) and review
  - Generate outfits and expressions, with review loops
  - Pick eye line, name color, and scale vs reference
  - Flatten pose/outfit combos into letter-based poses and write character.yml
"""

import argparse
import os
import random
import sys
import tkinter as tk
from io import BytesIO
from pathlib import Path
from tkinter import filedialog
from typing import Dict, List, Optional, Tuple

from PIL import Image

from .constants import DATA_DIR, EXPRESSIONS_SEQUENCE

# Import from package modules
from .api import (
    get_api_key,
    load_outfit_prompts,
    build_outfit_prompts_with_config,
    cleanup_edge_halos,
    strip_background_ai,
    REMBG_EDGE_CLEANUP_TOLERANCE,
    REMBG_EDGE_CLEANUP_PASSES,
)
from .ui import (
    prompt_voice_archetype_and_name,
    prompt_source_mode,
    prompt_character_idea_and_archetype,
    prompt_outfits_and_expressions,
    prompt_for_crop,
    review_images_for_step,
    review_initial_base_pose,
    click_to_remove_background,
)
from .processing import (
    generate_initial_pose_once,
    generate_single_outfit,
    generate_outfits_once,
    generate_and_review_expressions_for_pose,
    generate_initial_character_from_prompt,
    finalize_character,
    generate_expression_sheets_for_root,
    get_unique_folder_name,
)


# =============================================================================
# Main Character Processing Pipeline
# =============================================================================

def process_single_character(
    api_key: str,
    image_path: Path,
    output_root: Path,
    outfit_db: Dict[str, Dict[str, List[str]]],
    game_name: Optional[str] = None,
    preselected: Optional[Dict[str, str]] = None,
) -> None:
    """
    Run the pipeline for a single source image.

    Steps:
      - voice/name/archetype (or preselected for prompt mode)
      - choose outfits+expressions
      - normalize base pose with review
      - generate outfits + expressions
      - finalize (eye line, color, scale, flatten, yaml)

    Args:
        api_key: Gemini API key.
        image_path: Path to source character image.
        output_root: Root directory for output.
        outfit_db: Loaded outfit prompts database.
        game_name: Optional game name for metadata.
        preselected: Optional preselected character info (from prompt mode).
    """
    print(f"\n=== Processing source image: {image_path.name} ===")

    # Get character metadata
    if preselected is not None:
        voice = preselected["voice"]
        display_name = preselected["display_name"]
        archetype_label = preselected["archetype_label"]
        gender_style = preselected["gender_style"]
        print(
            f"[INFO] Using preselected voice/name/archetype for {display_name}: "
            f"voice={voice}, archetype={archetype_label}, gender_style={gender_style}"
        )
    else:
        voice, display_name, archetype_label, gender_style = \
            prompt_voice_archetype_and_name(image_path)

    # Get outfit and expression selections
    (
        selected_outfit_keys,
        expressions_sequence,
        outfit_prompt_config,
    ) = prompt_outfits_and_expressions(archetype_label, gender_style)

    print(f"[INFO] Selected outfits (Base always included): {selected_outfit_keys}")
    print(
        "[INFO] Selected expressions (including neutral): "
        f"{[key for key, _ in expressions_sequence]}"
    )
    print("[INFO] Per-outfit prompt config:")
    for key in selected_outfit_keys:
        cfg = outfit_prompt_config.get(key, {})
        if key == "uniform" and cfg.get("use_standard_uniform"):
            mode_str = "standard_uniform"
        elif cfg.get("use_random", True):
            mode_str = "random"
        else:
            mode_str = "custom"
        print(f"  - {key}: {mode_str}")

    # Create character folder
    char_folder_name = get_unique_folder_name(output_root, display_name)
    char_dir = output_root / char_folder_name
    char_dir.mkdir(parents=True, exist_ok=True)
    print(f"[INFO] Output character folder: {char_dir}")

    # Prepare pose A directory
    a_dir = char_dir / "a"
    a_dir.mkdir(parents=True, exist_ok=True)
    a_base_stem = a_dir / "base"

    use_base_as_outfit = True

    # Generate normalized base pose (black background, AI removal applied)
    a_base_path = generate_initial_pose_once(
        api_key,
        image_path,
        a_base_stem,
        gender_style,
        archetype_label,
    )

    # Store original base image for potential reset
    original_base_bytes = a_base_path.read_bytes()
    has_been_regenerated = False

    # Review loop for base pose (simplified - no edge cleanup controls here)
    while True:
        choice, use_flag, additional_text = review_initial_base_pose(
            a_base_path,
            has_been_regenerated=has_been_regenerated,
        )
        use_base_as_outfit = use_flag

        if choice == "accept":
            break

        if choice == "regenerate":
            a_base_path = generate_initial_pose_once(
                api_key,
                image_path,
                a_base_stem,
                gender_style,
                archetype_label,
                additional_instructions=additional_text,
            )
            has_been_regenerated = True
            continue

        if choice == "reset":
            # Restore original base image
            a_base_path.write_bytes(original_base_bytes)
            has_been_regenerated = False
            print("  [INFO] Reset to original base pose")
            continue

        if choice == "cancel":
            sys.exit(0)

    # Generate outfits
    print("[INFO] Generating outfits for pose A...")
    outfits_dir = a_dir / "outfits"
    outfits_dir.mkdir(parents=True, exist_ok=True)

    # Build outfit prompts with configuration
    current_outfit_prompts = build_outfit_prompts_with_config(
        archetype_label,
        gender_style,
        selected_outfit_keys,
        outfit_db,
        outfit_prompt_config,
    )

    # Initial generation: make Base (if requested) and all outfits once
    # Use interactive review mode to get cleanup data for per-outfit edge cleanup
    outfit_paths, cleanup_data = generate_outfits_once(
        api_key,
        a_base_path,
        outfits_dir,
        gender_style,
        current_outfit_prompts,
        outfit_prompt_config,
        archetype_label,
        outfit_db,
        include_base_outfit=use_base_as_outfit,
        for_interactive_review=True,
    )

    # Build mapping from path to index for cleanup_data updates
    path_to_index: Dict[Path, int] = {p: i for i, p in enumerate(outfit_paths)}

    # Initialize cleanup settings (will be populated on accept)
    outfit_cleanup_settings: Dict[Path, Tuple[int, int]] = {}

    # Per-outfit background removal mode: "rembg" (auto) or "manual"
    bg_removal_mode: Dict[Path, str] = {p: "rembg" for p in outfit_paths}

    # State to restore on next iteration (for preserving slider settings during regeneration)
    restore_state: Optional[Dict[str, object]] = None

    # Review loop: regenerate individual outfits as needed
    while True:
        a_out_paths: List[Path] = []
        per_buttons: List[List[Tuple[str, str]]] = []
        index_to_outfit_key: Dict[int, str] = {}
        review_cleanup_data: List[Tuple[bytes, bytes]] = []

        # Use tracked outfit_paths instead of scanning disk
        for p in outfit_paths:
            if not p.exists():
                continue

            a_out_paths.append(p)
            stem_lower = p.stem.lower()

            # Get the cleanup data for this outfit
            path_idx = path_to_index.get(p)
            if path_idx is not None and path_idx < len(cleanup_data):
                review_cleanup_data.append(cleanup_data[path_idx])
            else:
                # Fallback: use same bytes for original and rembg
                fallback_bytes = p.read_bytes()
                review_cleanup_data.append((fallback_bytes, fallback_bytes))

            # Try to match this file back to one of the logical outfit keys
            matched_key: Optional[str] = None
            for key in selected_outfit_keys:
                if key.lower() == stem_lower or key.capitalize().lower() == stem_lower:
                    matched_key = key
                    break
            # Also check for "Base" which isn't in selected_outfit_keys
            if stem_lower == "base":
                matched_key = "base"

            # Decide which per-card buttons to show based on mode
            btn_list: List[Tuple[str, str]] = []
            mode = bg_removal_mode.get(p, "rembg")

            if matched_key == "base":
                # Base outfit: no regeneration, just BG options
                if mode == "rembg":
                    btn_list.append(("Cleanup BG", "cleanup_bg"))
                    btn_list.append(("Switch to Manual", "switch_manual"))
                else:
                    btn_list.append(("Manual BG removal", "manual_base"))
                    btn_list.append(("Switch to Auto", "switch_auto"))
                index_to_outfit_key[len(a_out_paths) - 1] = matched_key
            elif matched_key is not None:
                cfg = outfit_prompt_config.get(matched_key, {})
                # Regeneration buttons (always shown)
                btn_list.append(("Regen (same outfit)", "same"))
                # "New random outfit" button only for CSV/random system
                if not (matched_key == "uniform" and cfg.get("use_standard_uniform")):
                    btn_list.append(("Regen (new outfit)", "new"))
                # Mode-specific BG buttons
                if mode == "rembg":
                    btn_list.append(("Cleanup BG", "cleanup_bg"))
                    btn_list.append(("Switch to Manual", "switch_manual"))
                else:
                    btn_list.append(("Manual BG removal", "manual_outfit"))
                    btn_list.append(("Switch to Auto", "switch_auto"))
                index_to_outfit_key[len(a_out_paths) - 1] = matched_key

            per_buttons.append(btn_list)

        a_infos = [(p, f"Pose A – {p.name}") for p in a_out_paths]

        # Build index -> mode mapping for the review UI
        index_to_mode: Dict[int, str] = {
            i: bg_removal_mode.get(p, "rembg") for i, p in enumerate(a_out_paths)
        }

        decision = review_images_for_step(
            a_infos,
            "Review Outfits for Pose A",
            (
                "Accept these outfits, regenerate individual outfits (random outfits will pick new "
                "CSV prompts when you choose 'New random outfit'; custom outfits and standard "
                "uniforms will keep the same prompt), or cancel.\n\n"
                "Use the edge cleanup controls under each outfit to adjust halo removal."
            ),
            per_item_buttons=per_buttons,
            show_global_regenerate=False,
            cleanup_data=review_cleanup_data,
            restore_state=restore_state,
            bg_removal_modes=index_to_mode,
        )

        choice = decision.get("choice")

        if choice == "accept":
            # Save final bytes with user's cleanup settings
            final_bytes_list = decision.get("final_bytes")
            if final_bytes_list:
                for i, path in enumerate(a_out_paths):
                    if i < len(final_bytes_list):
                        path.write_bytes(final_bytes_list[i])
                        print(f"  Saved edge-cleaned outfit to: {path}")

            # Capture cleanup settings to pass to expression generation
            outfit_cleanup_settings: Dict[Path, Tuple[int, int]] = {}
            cleanup_settings_list = decision.get("cleanup_settings")
            if cleanup_settings_list:
                for i, path in enumerate(a_out_paths):
                    if i < len(cleanup_settings_list):
                        outfit_cleanup_settings[path] = cleanup_settings_list[i]
            break
        if choice == "cancel":
            sys.exit(0)

        if choice == "per_item":
            idx = decision.get("index")
            action = decision.get("action")
            if idx is None or action is None:
                continue

            # Capture state to restore on next iteration (preserves slider settings for OTHER outfits)
            restore_state = {
                "cleanup_settings": decision.get("cleanup_settings"),
                "current_bytes": decision.get("current_bytes"),
                "background_selection": decision.get("background_selection"),
            }

            outfit_key = index_to_outfit_key.get(int(idx))
            if not outfit_key:
                continue

            # Cleanup BG: touch-up existing transparent image (for rembg mode)
            if action == "cleanup_bg":
                old_path = a_out_paths[idx]
                # Open click_to_remove on current bytes for touch-up
                accepted = click_to_remove_background(old_path, threshold=30)
                if accepted:
                    new_bytes = old_path.read_bytes()
                    path_idx = path_to_index.get(old_path)
                    if path_idx is not None:
                        original_bytes, _ = cleanup_data[path_idx]
                        cleanup_data[path_idx] = (original_bytes, new_bytes)
                    if restore_state and restore_state.get("current_bytes"):
                        if idx < len(restore_state["current_bytes"]):
                            restore_state["current_bytes"][idx] = new_bytes
                    print(f"  Applied BG cleanup: {old_path}")
                continue

            # Switch to Manual mode: revert to original (black bg) and change mode
            if action == "switch_manual":
                old_path = a_out_paths[idx]
                path_idx = path_to_index.get(old_path)
                if path_idx is not None and path_idx < len(cleanup_data):
                    # Revert to original bytes (black background)
                    original_bytes, _ = cleanup_data[path_idx]
                    old_path.write_bytes(original_bytes)
                    cleanup_data[path_idx] = (original_bytes, original_bytes)

                    # Update mode tracking
                    bg_removal_mode[old_path] = "manual"

                    # Update restore_state
                    if restore_state and restore_state.get("current_bytes"):
                        if idx < len(restore_state["current_bytes"]):
                            restore_state["current_bytes"][idx] = original_bytes

                    print(f"  Switched to manual mode: {old_path}")
                continue

            # Switch to Auto (rembg) mode: restore rembg bytes and change mode
            if action == "switch_auto":
                old_path = a_out_paths[idx]
                path_idx = path_to_index.get(old_path)
                if path_idx is not None and path_idx < len(cleanup_data):
                    # We need to re-run rembg on the original to get fresh rembg bytes
                    original_bytes, _ = cleanup_data[path_idx]
                    rembg_bytes = strip_background_ai(original_bytes, skip_edge_cleanup=True)
                    old_path.write_bytes(rembg_bytes)
                    cleanup_data[path_idx] = (original_bytes, rembg_bytes)

                    # Update mode tracking
                    bg_removal_mode[old_path] = "rembg"

                    # Update restore_state
                    if restore_state and restore_state.get("current_bytes"):
                        if idx < len(restore_state["current_bytes"]):
                            restore_state["current_bytes"][idx] = rembg_bytes

                    print(f"  Switched to auto (rembg) mode: {old_path}")
                continue

            # Manual background removal for Base outfit
            if action == "manual_base" and outfit_key == "base":
                old_path = a_out_paths[idx]
                path_idx = path_to_index.get(old_path)
                if path_idx is not None and path_idx < len(cleanup_data):
                    original_bytes, rembg_bytes = cleanup_data[path_idx]
                    # Save original (with black bg) to the outfit path for manual editing
                    original_img = Image.open(BytesIO(original_bytes)).convert("RGBA")
                    original_img.save(old_path, format="PNG", compress_level=0, optimize=False)

                    # Open manual removal UI (edits the file in-place)
                    accepted = click_to_remove_background(old_path, threshold=30)

                    if accepted:
                        # Read the manually edited result
                        new_bytes = old_path.read_bytes()
                        cleanup_data[path_idx] = (original_bytes, new_bytes)
                        print(f"  Applied manual background removal: {old_path}")
                        # Update restore_state with new bytes
                        if restore_state and restore_state.get("current_bytes"):
                            if idx < len(restore_state["current_bytes"]):
                                restore_state["current_bytes"][idx] = new_bytes
                    else:
                        # User cancelled - restore the rembg version
                        old_path.write_bytes(rembg_bytes)
                continue

            # Manual background removal for any outfit (non-Base)
            if action == "manual_outfit" and outfit_key != "base":
                old_path = a_out_paths[idx]
                path_idx = path_to_index.get(old_path)
                if path_idx is not None and path_idx < len(cleanup_data):
                    original_bytes, rembg_bytes = cleanup_data[path_idx]
                    # Save original (with black bg) for manual editing
                    original_img = Image.open(BytesIO(original_bytes)).convert("RGBA")
                    original_img.save(old_path, format="PNG", compress_level=0, optimize=False)

                    # Open manual removal UI
                    accepted = click_to_remove_background(old_path, threshold=30)

                    if accepted:
                        new_bytes = old_path.read_bytes()
                        cleanup_data[path_idx] = (original_bytes, new_bytes)
                        print(f"  Applied manual background removal: {old_path}")
                        if restore_state and restore_state.get("current_bytes"):
                            if idx < len(restore_state["current_bytes"]):
                                restore_state["current_bytes"][idx] = new_bytes
                    else:
                        # User cancelled - restore rembg version
                        old_path.write_bytes(rembg_bytes)
                continue

            # If "new" random outfit, roll a fresh prompt
            if action == "new":
                new_prompt_dict = build_outfit_prompts_with_config(
                    archetype_label,
                    gender_style,
                    [outfit_key],
                    outfit_db,
                    outfit_prompt_config,
                )
                current_outfit_prompts[outfit_key] = new_prompt_dict[outfit_key]

            # Get description (reuse existing or generate new)
            desc = current_outfit_prompts.get(outfit_key)
            if not desc:
                fallback_prompt_dict = build_outfit_prompts_with_config(
                    archetype_label,
                    gender_style,
                    [outfit_key],
                    outfit_db,
                    outfit_prompt_config,
                )
                desc = fallback_prompt_dict[outfit_key]
                current_outfit_prompts[outfit_key] = desc

            # Regenerate just this one outfit image (with interactive review)
            result = generate_single_outfit(
                api_key,
                a_base_path,
                outfits_dir,
                gender_style,
                outfit_key,
                desc,
                outfit_prompt_config,
                archetype_label,
                outfit_db,
                for_interactive_review=True,
            )

            # Update cleanup_data for this outfit
            if result is not None:
                new_path, new_original, new_rembg = result
                # Find and update the entry in our tracking
                old_path = a_out_paths[idx]
                if old_path in path_to_index:
                    old_idx = path_to_index[old_path]
                    cleanup_data[old_idx] = (new_original, new_rembg)
                    # Update path mapping if path changed
                    if new_path != old_path:
                        outfit_paths[old_idx] = new_path
                        del path_to_index[old_path]
                        path_to_index[new_path] = old_idx

                # Update restore_state with new bytes so we don't restore the old image
                if restore_state and restore_state.get("current_bytes"):
                    if idx < len(restore_state["current_bytes"]):
                        restore_state["current_bytes"][idx] = new_rembg
            continue

        # Safety: support "regenerate_all" if ever re-enabled
        if choice == "regenerate_all":
            current_outfit_prompts = build_outfit_prompts_with_config(
                archetype_label,
                gender_style,
                selected_outfit_keys,
                outfit_db,
                outfit_prompt_config,
            )
            outfit_paths, cleanup_data = generate_outfits_once(
                api_key,
                a_base_path,
                outfits_dir,
                gender_style,
                current_outfit_prompts,
                outfit_prompt_config,
                archetype_label,
                outfit_db,
                include_base_outfit=use_base_as_outfit,
                for_interactive_review=True,
            )
            path_to_index = {p: i for i, p in enumerate(outfit_paths)}
            continue

    # Generate expressions for all outfits, using the cleanup settings from outfit review
    print("[INFO] Generating expressions for pose A (per outfit)...")
    generate_and_review_expressions_for_pose(
        api_key,
        char_dir,
        a_dir,
        "A",
        expressions_sequence=expressions_sequence,
        cleanup_settings=outfit_cleanup_settings,
        bg_removal_modes=bg_removal_mode,
    )

    # Finalize character
    finalize_character(char_dir, display_name, voice, game_name)

    # Generate expression sheets for this character only
    generate_expression_sheets_for_root(char_dir)

    # Optional: Launch sprite tester if available
    try:
        from .tester import launch_sprite_tester
        launch_sprite_tester(char_dir)
    except ImportError:
        pass  # Tester module not available, skip silently
    except Exception as e:
        print(f"[INFO] Sprite tester skipped: {e}")


# =============================================================================
# Main Pipeline Entry Point
# =============================================================================

def run_pipeline(output_root: Path, game_name: Optional[str] = None) -> None:
    """
    Run the interactive sprite pipeline for a single character.

    This is the core entry point used both by:
      - the command-line interface in main(), and
      - the external hub script (pipeline_runner.py).

    Args:
        output_root: Root folder where character sprite folders will be created.
        game_name: Optional game name to include in character.yml.
    """
    random.seed(int.from_bytes(os.urandom(16), "big"))
    api_key = get_api_key()

    outfit_db = load_outfit_prompts(DATA_DIR)
    output_root.mkdir(parents=True, exist_ok=True)

    # Ask how we are creating the character: from an image, or from a text prompt
    mode = prompt_source_mode()

    if mode == "image":
        # Choose the source image via file dialog
        root = tk.Tk()
        root.withdraw()
        initialdir = str(Path.cwd())
        filename = filedialog.askopenfilename(
            title="Choose character source image",
            initialdir=initialdir,
            filetypes=[
                ("Images", "*.png;*.jpg;*.jpeg;*.webp"),
                ("PNG", "*.png"),
                ("JPEG", "*.jpg;*.jpeg"),
                ("WEBP", "*.webp"),
                ("All files", "*.*"),
            ],
        )
        root.destroy()
        if not filename:
            raise SystemExit("No image selected. Exiting.")

        image_path = Path(filename)
        print(f"[INFO] Selected source image: {image_path}")

        # Optional thigh crop UI before normalization
        try:
            src_img = Image.open(image_path).convert("RGBA")
        except Exception as e:
            print(f"[WARN] Could not open image for cropping ({e}); using original.")
            src_img = None

        if src_img is not None:
            prompt_text = (
                "If this sprite is not already cropped to mid-thigh, click where you "
                "want the lower thigh-level crop line.\n\n"
                "If it *is* already cropped the way you like, just click along the "
                "existing bottom edge of the character."
            )

            y_cut, used_gallery = prompt_for_crop(
                src_img,
                prompt_text,
                previous_crops=[],
            )

            # If the user clicked somewhere above the bottom edge, crop
            if y_cut is not None and 0 < y_cut < src_img.height:
                cropped = src_img.crop((0, 0, src_img.width, y_cut))
                crop_dir = output_root / "_cropped_sources"
                crop_dir.mkdir(parents=True, exist_ok=True)
                cropped_path = crop_dir / f"{image_path.stem}_cropped.png"
                cropped.save(cropped_path, format="PNG", compress_level=0, optimize=False)
                print(f"[INFO] Saved thigh-cropped source image to: {cropped_path}")
                image_path = cropped_path
            else:
                print("[INFO] User kept original height; skipping pre-crop.")

        process_single_character(api_key, image_path, output_root, outfit_db, game_name)

    else:
        # Prompt-generated character path
        concept, arch_label, voice, display_name, gender_style = (
            prompt_character_idea_and_archetype()
        )

        # Generate and review the initial prompt-based sprite
        while True:
            src_path = generate_initial_character_from_prompt(
                api_key,
                concept,
                arch_label,
                output_root,
            )

            decision = review_images_for_step(
                [(src_path, f"Prompt-generated base: {src_path.name}")],
                "Review Prompt-Generated Base Sprite",
                "Accept this as the starting sprite, regenerate it, or cancel.",
            )

            choice = decision.get("choice")

            if choice == "accept":
                break
            if choice == "regenerate_all":
                continue
            if choice == "cancel":
                sys.exit(0)

        # === Crop step for prompt-generated character ===
        try:
            src_img = Image.open(src_path).convert("RGBA")
        except Exception as e:
            print(f"[WARN] Could not open image for cropping ({e}); using original.")
            src_img = None

        if src_img is not None:
            crop_prompt_text = (
                "If this sprite is not already cropped to mid-thigh, click where you "
                "want the lower thigh-level crop line.\n\n"
                "If it *is* already cropped the way you like, just click along the "
                "existing bottom edge of the character."
            )

            y_cut, used_gallery = prompt_for_crop(
                src_img,
                crop_prompt_text,
                previous_crops=[],
            )

            # If the user clicked somewhere above the bottom edge, crop
            if y_cut is not None and 0 < y_cut < src_img.height:
                cropped = src_img.crop((0, 0, src_img.width, y_cut))
                crop_dir = output_root / "_cropped_sources"
                crop_dir.mkdir(parents=True, exist_ok=True)
                cropped_path = crop_dir / f"{src_path.stem}_cropped.png"
                cropped.save(cropped_path, format="PNG", compress_level=0, optimize=False)
                print(f"[INFO] Saved thigh-cropped source image to: {cropped_path}")
                src_path = cropped_path
            else:
                print("[INFO] User kept original height; skipping pre-crop.")

        preselected = {
            "voice": voice,
            "display_name": display_name,
            "archetype_label": arch_label,
            "gender_style": gender_style,
        }
        process_single_character(
            api_key,
            src_path,
            output_root,
            outfit_db,
            game_name,
            preselected=preselected,
        )

    print("\nCharacter processed.")
    print(f"Final sprite folder(s) are in:\n  {output_root}")


# =============================================================================
# CLI Entry Point
# =============================================================================

def main() -> None:
    """
    Command-line entry point.

    Parses optional arguments, chooses an output folder if needed,
    and then runs the interactive pipeline.
    """
    parser = argparse.ArgumentParser(
        description=(
            "End-to-end visual novel sprite builder using Google Gemini:\n"
            "  - base pose\n"
            "  - outfits (Base + selected extras like Formal/Casual/Uniform/...)\n"
            "  - expressions per outfit (0 + selected non-neutral ones)\n"
            "  - eye line / name color / scale\n"
            "  - character.yml\n"
        )
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help=(
            "Root folder to write final character sprite folders. "
            "If omitted, you will be prompted to choose a folder."
        ),
    )
    parser.add_argument(
        "--game-name",
        type=str,
        default=None,
        help="Optional game name to write into character.yml (game field).",
    )

    args = parser.parse_args()

    output_root: Path | None = args.output_dir
    game_name: Optional[str] = args.game_name

    # If no output folder was provided, ask the user via a folder picker
    if output_root is None:
        root = tk.Tk()
        root.withdraw()
        root.update_idletasks()
        chosen = filedialog.askdirectory(
            title="Choose output folder for character sprite(s)"
        )
        root.destroy()
        if not chosen:
            raise SystemExit("No output folder selected. Exiting.")
        output_root = Path(os.path.abspath(os.path.expanduser(chosen)))

    run_pipeline(output_root, game_name)


if __name__ == "__main__":
    main()
