"""
Outfit wizard steps (Steps 8-9).

These steps handle outfit generation and review:
- Step 8: Outfit Review with per-outfit regeneration and cleanup
- Step 9: Manual BG Removal Modal (embedded in step 8)
"""

import threading
import tkinter as tk
from tkinter import ttk, messagebox
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PIL import Image, ImageTk

from ...config import (
    BG_COLOR,
    BG_SECONDARY,
    CARD_BG,
    TEXT_COLOR,
    TEXT_SECONDARY,
    ACCENT_COLOR,
    PAGE_TITLE_FONT,
    SECTION_FONT,
    BODY_FONT,
    SMALL_FONT,
    DATA_DIR,
)
from ...api.gemini_client import (
    REMBG_EDGE_CLEANUP_TOLERANCE,
    REMBG_EDGE_CLEANUP_PASSES,
)
from ..tk_common import (
    create_primary_button,
    create_secondary_button,
    create_danger_button,
)
from .base import WizardStep, WizardState


class OutfitReviewStep(WizardStep):
    """
    Step 8: Outfit Review.

    Displays all generated outfits with per-outfit controls:
    - Regenerate (same prompt)
    - Regenerate (new prompt)
    - Cleanup BG (tolerance/depth sliders)
    - Switch to Manual BG removal

    Also provides global Accept/Regenerate All buttons.
    """

    STEP_ID = "outfit_review"
    STEP_TITLE = "Outfits"
    STEP_HELP = """Outfit Review

This step shows all generated outfits. Scroll horizontally to see them all.

PREVIEW BACKGROUND (Top Right)
Use the dropdown to preview outfits on different backgrounds:
- Black/White: Solid colors to check edges
- Game backgrounds: If available, shows how outfits look in-game

OUTFIT CARDS
Each card shows one generated outfit with controls below.

REGENERATION BUTTONS
Regen Same Outfit: Generate a new image using the same outfit description. Useful if the pose or quality isn't right but you like the outfit concept.

Regen New Outfit: Generate with a completely different random outfit description. Use this to try a different look entirely.

Note: "Regen Same Outfit" is hidden for underwear because the tier system makes same-prompt regeneration unreliable.

BACKGROUND REMOVAL (Auto Mode)
When an outfit shows the "rembg" sliders:

Tolerance (0-150): How aggressively to remove edge pixels.
- Low values (0-30): Only removes very similar colors
- High values (100+): Removes more, but may eat into the character
- Default: 50

Depth (0-50): How many cleanup passes to run.
- Low values (0-5): Light cleanup
- High values (20+): More aggressive edge cleaning
- Default: 5

Click "Apply" after adjusting sliders to see the result.

MANUAL MODE
Click "Switch to Manual BG Removal" to use click-based removal instead. In manual mode, you click on areas to remove (flood-fill style).

Click "Switch to Auto BG Removal" to return to slider-based mode.

NAVIGATION
Use mouse wheel to scroll horizontally through outfits.

When satisfied with all outfits, click Next to proceed to expression generation."""

    def __init__(self, wizard, state: WizardState):
        super().__init__(wizard, state)
        self._canvas: Optional[tk.Canvas] = None
        self._inner_frame: Optional[tk.Frame] = None
        self._img_labels: List[tk.Label] = []
        self._thumb_refs: List[ImageTk.PhotoImage] = []
        self._current_bytes: List[bytes] = []
        self._tolerance_vars: List[tk.IntVar] = []
        self._depth_vars: List[tk.IntVar] = []
        self._bg_var: Optional[tk.StringVar] = None
        self._is_generating: bool = False
        self._original_preview_sizes: Dict[int, int] = {}  # Track original max_h per outfit

    def build_ui(self, parent: tk.Frame) -> None:
        parent.configure(bg=BG_COLOR)

        # Header row
        header = tk.Frame(parent, bg=BG_COLOR)
        header.pack(fill="x", pady=(0, 8))

        # Title
        tk.Label(
            header,
            text="Review Outfits",
            bg=BG_COLOR,
            fg=TEXT_COLOR,
            font=PAGE_TITLE_FONT,
        ).pack(side="left")

        # Background preview dropdown
        bg_frame = tk.Frame(header, bg=BG_COLOR)
        bg_frame.pack(side="right")

        tk.Label(
            bg_frame,
            text="Preview BG:",
            bg=BG_COLOR,
            fg=TEXT_SECONDARY,
            font=SMALL_FONT,
        ).pack(side="left", padx=(0, 4))

        self._bg_var = tk.StringVar(value="White")
        bg_options = self._get_background_options()
        bg_menu = tk.OptionMenu(bg_frame, self._bg_var, *[name for name, _ in bg_options])
        bg_menu.configure(width=12, bg=CARD_BG, fg=TEXT_COLOR)
        bg_menu.pack(side="left")
        self._bg_var.trace_add("write", lambda *_: self._update_all_previews())

        # Scrollable canvas for outfit cards
        canvas_frame = tk.Frame(parent, bg=BG_COLOR)
        canvas_frame.pack(fill="both", expand=True)

        self._canvas = tk.Canvas(
            canvas_frame,
            bg=BG_COLOR,
            highlightthickness=0,
        )
        self._canvas.pack(side="left", fill="both", expand=True)

        h_scroll = ttk.Scrollbar(canvas_frame, orient="horizontal", command=self._canvas.xview)
        h_scroll.pack(side="bottom", fill="x")
        self._canvas.configure(xscrollcommand=h_scroll.set)

        self._inner_frame = tk.Frame(self._canvas, bg=BG_COLOR)
        self._canvas.create_window((0, 0), window=self._inner_frame, anchor="nw")
        self._inner_frame.bind("<Configure>", self._on_frame_configure)

        # Note: Accept All / Regenerate All buttons removed - use Next button to accept
        # Note: Status label removed to save vertical space

    def _get_background_options(self) -> List[Tuple[str, Optional[Path]]]:
        """Get available background options for preview."""
        from ...config import DATA_DIR
        options = [
            ("Black", None),
            ("White", None),
        ]
        # Add game backgrounds if available
        bg_dir = DATA_DIR / "reference_sprites" / "backgrounds"
        if bg_dir.is_dir():
            for p in sorted(bg_dir.iterdir()):
                if p.suffix.lower() in (".png", ".jpg", ".jpeg"):
                    options.append((p.stem, p))
        return options

    def _on_frame_configure(self, event=None) -> None:
        """Update scroll region when content changes."""
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))
        # Bind mouse wheel for horizontal scrolling
        self._canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        # Linux scroll bindings
        self._canvas.bind_all("<Button-4>", lambda e: self._canvas.xview_scroll(-1, "units"))
        self._canvas.bind_all("<Button-5>", lambda e: self._canvas.xview_scroll(1, "units"))

    def _on_mousewheel(self, event) -> None:
        """Handle mouse wheel for horizontal scrolling."""
        # Windows: event.delta is typically 120 or -120
        self._canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")

    def on_enter(self) -> None:
        """Generate outfits when step becomes active."""
        # Check if we need to regenerate (user changed something upstream)
        if self.state.is_step_dirty(self._get_step_index()):
            self.state.outfits_generated = False
            self._start_outfit_generation()
            return

        # Check if we already have valid outfits (prevents regeneration on back navigation)
        if (self.state.outfits_generated and
            self.state.outfit_paths and
            all(p.exists() for p in self.state.outfit_paths)):
            self._load_existing_outfits()
            return

        # No outfits yet, generate them
        self._start_outfit_generation()

    def _get_step_index(self) -> int:
        """Get this step's index in the wizard."""
        for i, step in enumerate(self.wizard._steps):
            if step is self:
                return i
        return -1

    def _start_outfit_generation(self) -> None:
        """Start generating all outfits in background."""
        if self._is_generating:
            return

        self._is_generating = True
        self.show_loading("Generating outfits...")

        def generate():
            try:
                paths, cleanup_data, used_prompts = self._do_outfit_generation()
                self.wizard.root.after(0, lambda p=paths, c=cleanup_data, u=used_prompts: self._on_generation_complete(p, c, u))
            except Exception as e:
                error_msg = str(e)
                self.wizard.root.after(0, lambda msg=error_msg: self._on_generation_error(msg))

        thread = threading.Thread(target=generate, daemon=True)
        thread.start()

    def _do_outfit_generation(self) -> Tuple[List[Path], List[Tuple[bytes, bytes]], Dict[str, str]]:
        """Perform outfit generation."""
        from ...processing import generate_outfits_once, get_unique_folder_name
        from ...api import build_outfit_prompts_with_config
        from ..api_setup import ensure_api_key

        if not self.state.api_key:
            self.state.api_key = ensure_api_key()

        # Create character folder if it doesn't exist
        if not self.state.character_folder:
            if not self.state.output_root:
                raise ValueError("Output folder not set. Please select an output folder before generating.")
            self.state.character_folder = self.state.output_root / get_unique_folder_name(
                self.state.output_root, self.state.display_name
            )
        self.state.character_folder.mkdir(parents=True, exist_ok=True)

        # Copy base pose to character folder if not already there
        base_dest = self.state.character_folder / "a_base.png"
        if self.state.base_pose_path and self.state.base_pose_path.exists() and not base_dest.exists():
            import shutil
            shutil.copy2(self.state.base_pose_path, base_dest)
            # Update base_pose_path to point to the new location
            self.state.base_pose_path = base_dest

        # Build outfit prompts with configuration (uses Gemini text API for random mode)
        # Note: For underwear, this returns a placeholder; actual prompt determined at generation
        outfit_descriptions = build_outfit_prompts_with_config(
            self.state.api_key,
            self.state.archetype_label,
            self.state.gender_style,
            self.state.selected_outfits,
            self.state.outfit_prompt_config,
        )

        # Create outfits directory
        outfits_dir = self.state.character_folder / "a" / "outfits"
        outfits_dir.mkdir(parents=True, exist_ok=True)

        # Generate outfits using the base pose
        # Returns (paths, cleanup_data, used_prompts) where used_prompts contains
        # the actual prompts that succeeded (important for underwear tier system)
        paths, cleanup_data, used_prompts = generate_outfits_once(
            api_key=self.state.api_key,
            base_pose_path=self.state.base_pose_path,
            outfits_dir=outfits_dir,
            gender_style=self.state.gender_style,
            outfit_descriptions=outfit_descriptions,
            outfit_prompt_config=self.state.outfit_prompt_config,
            archetype_label=self.state.archetype_label,
            include_base_outfit=self.state.use_base_as_outfit,
            for_interactive_review=True,
        )

        return paths, cleanup_data, used_prompts

    def _on_generation_complete(self, paths: List[Path], cleanup_data: List[Tuple[bytes, bytes]], used_prompts: Dict[str, str]) -> None:
        """Handle outfit generation completion."""
        self._is_generating = False
        self.hide_loading()

        self.state.outfit_paths = paths
        self.state.outfit_cleanup_data = cleanup_data
        self.state.outfits_generated = True  # Mark as generated to prevent regeneration on back

        # Store the actual prompts that succeeded (important for underwear tier system)
        self.state.outfit_prompts = used_prompts

        # Track which outfit keys actually succeeded (for expression step)
        # This handles cases where outfits like underwear may be skipped due to safety filters
        generated_keys = []
        if self.state.use_base_as_outfit:
            generated_keys.append("base")
        generated_keys.extend(used_prompts.keys())
        self.state.generated_outfit_keys = generated_keys

        # Initialize current bytes from rembg results
        self._current_bytes = [rembg_bytes for _, rembg_bytes in cleanup_data]
        self.state.current_outfit_bytes = self._current_bytes.copy()

        # Build outfit cards
        self._build_outfit_cards()

    def _on_generation_error(self, error: str) -> None:
        """Handle generation error."""
        self._is_generating = False
        self.hide_loading()
        messagebox.showerror("Generation Error", f"Failed to generate outfits:\n\n{error}")

    def _load_existing_outfits(self) -> None:
        """Load existing outfits from state."""
        # Load current bytes
        if self.state.current_outfit_bytes:
            self._current_bytes = self.state.current_outfit_bytes.copy()
        else:
            self._current_bytes = []
            for path in self.state.outfit_paths:
                if path.exists():
                    self._current_bytes.append(path.read_bytes())
                else:
                    self._current_bytes.append(b"")

        self._build_outfit_cards()

    def _build_outfit_cards(self) -> None:
        """Build UI cards for each outfit."""
        # Clear existing
        for widget in self._inner_frame.winfo_children():
            widget.destroy()
        self._img_labels.clear()
        self._thumb_refs.clear()
        self._tolerance_vars.clear()
        self._depth_vars.clear()
        self._original_preview_sizes.clear()

        # Get canvas dimensions for sizing - use larger images
        self._canvas.update_idletasks()
        canvas_h = self._canvas.winfo_height()
        max_thumb_h = max(int(canvas_h * 0.85), 450)  # Increased from 0.70/300

        # Get outfit names (only those that succeeded generation)
        outfit_names = self.state.generated_outfit_keys.copy() if self.state.generated_outfit_keys else []

        # Build cards
        for idx, (path, name) in enumerate(zip(self.state.outfit_paths, outfit_names)):
            card = self._build_single_outfit_card(idx, path, name, max_thumb_h)
            card.grid(row=0, column=idx, padx=10, pady=6)

    def _build_single_outfit_card(self, idx: int, path: Path, name: str, max_h: int) -> tk.Frame:
        """Build a single outfit card with image and controls."""
        card = tk.Frame(self._inner_frame, bg=CARD_BG, padx=6, pady=4)

        # Load and display image
        img_bytes = self._current_bytes[idx] if idx < len(self._current_bytes) else path.read_bytes()
        preview = self._create_preview_image(img_bytes, max_h)
        self._thumb_refs.append(preview)
        self._original_preview_sizes[idx] = max_h  # Store for consistent updates

        img_label = tk.Label(card, image=preview, bg=CARD_BG)
        img_label.pack()
        self._img_labels.append(img_label)

        # Caption
        tk.Label(
            card,
            text=name.capitalize(),
            bg=CARD_BG,
            fg=TEXT_COLOR,
            font=BODY_FONT,
        ).pack(pady=(1, 1))

        # === GROUP 1: Regenerate buttons (horizontal, not for base) ===
        if name.lower() != "base":
            # Check if this outfit uses standard_uniform mode (only one option, no "new outfit" needed)
            outfit_config = self.state.outfit_prompt_config.get(name.lower(), {})
            is_standard_uniform = outfit_config.get("use_standard_uniform", False)
            is_underwear = name.lower() == "underwear"

            regen_frame = tk.Frame(card, bg=CARD_BG)
            regen_frame.pack(pady=(1, 1))

            # Don't show "Regen Same Outfit" for underwear - the generation is too unreliable
            # and uses a tier system that won't produce the same result anyway
            if not is_underwear:
                create_secondary_button(
                    regen_frame, "Regen Same Outfit",
                    lambda i=idx: self._regenerate_outfit(i, same_prompt=True),
                    width=14
                ).pack(side="left", padx=(0, 4))

            # Only show "Regen New Outfit" if not using standard uniform
            if not is_standard_uniform:
                create_secondary_button(
                    regen_frame, "Regen New Outfit",
                    lambda i=idx: self._regenerate_outfit(i, same_prompt=False),
                    width=14
                ).pack(side="left")

        # BG mode and cleanup controls
        mode = self.state.outfit_bg_modes.get(idx, "rembg")

        if mode == "rembg":
            # === GROUP 2: Cleanup sliders + Apply (all horizontal) ===
            cleanup_frame = tk.Frame(card, bg=CARD_BG)
            cleanup_frame.pack(pady=(1, 1))

            # Tolerance label and slider
            tk.Label(cleanup_frame, text="Tolerance:", font=("", 8), bg=CARD_BG, fg=TEXT_SECONDARY).pack(side="left")

            restored_tol = REMBG_EDGE_CLEANUP_TOLERANCE
            if self.state.outfit_cleanup_settings and idx < len(self.state.outfit_cleanup_settings):
                restored_tol = self.state.outfit_cleanup_settings[idx][0]
            tol_var = tk.IntVar(value=restored_tol)
            self._tolerance_vars.append(tol_var)

            tk.Scale(
                cleanup_frame, from_=0, to=150, orient="horizontal",
                variable=tol_var, length=280, showvalue=True,
                font=("", 7), bg=CARD_BG, highlightthickness=0
            ).pack(side="left")

            # Depth label and slider
            tk.Label(cleanup_frame, text="Depth:", font=("", 8), bg=CARD_BG, fg=TEXT_SECONDARY).pack(side="left", padx=(4, 0))

            restored_depth = REMBG_EDGE_CLEANUP_PASSES
            if self.state.outfit_cleanup_settings and idx < len(self.state.outfit_cleanup_settings):
                restored_depth = self.state.outfit_cleanup_settings[idx][1]
            depth_var = tk.IntVar(value=restored_depth)
            self._depth_vars.append(depth_var)

            tk.Scale(
                cleanup_frame, from_=0, to=50, orient="horizontal",
                variable=depth_var, length=280, showvalue=True,
                font=("", 7), bg=CARD_BG, highlightthickness=0
            ).pack(side="left")

            # Apply button
            create_secondary_button(
                cleanup_frame, "Apply",
                lambda i=idx: self._apply_cleanup(i),
                width=6
            ).pack(side="left", padx=(4, 0))

            # === GROUP 3: BG Mode Switch ===
            create_secondary_button(
                card, "Switch to Manual BG Removal",
                lambda i=idx: self._switch_to_manual(i),
                width=24
            ).pack(pady=(1, 0))
        else:
            # Manual mode - no sliders, just buttons
            tk.Label(
                card,
                text="Manual mode",
                bg=CARD_BG,
                fg=TEXT_SECONDARY,
                font=("", 8),
            ).pack(pady=(1, 0))

            # Placeholders for vars (to keep index alignment) - restore previous values to preserve settings
            restored_tol = REMBG_EDGE_CLEANUP_TOLERANCE
            restored_depth = REMBG_EDGE_CLEANUP_PASSES
            if self.state.outfit_cleanup_settings and idx < len(self.state.outfit_cleanup_settings):
                restored_tol = self.state.outfit_cleanup_settings[idx][0]
                restored_depth = self.state.outfit_cleanup_settings[idx][1]
            self._tolerance_vars.append(tk.IntVar(value=restored_tol))
            self._depth_vars.append(tk.IntVar(value=restored_depth))

            # === BG Mode Switch (no Edit button - BG removal handled in Expressions step) ===
            create_secondary_button(
                card, "Switch to Auto BG Removal",
                lambda i=idx: self._switch_to_auto(i),
                width=24
            ).pack(pady=(1, 0))

        return card

    def _create_preview_image(self, img_bytes: bytes, max_h: int) -> ImageTk.PhotoImage:
        """Create a preview image with current background."""
        try:
            img = Image.open(BytesIO(img_bytes)).convert("RGBA")
        except Exception:
            img = Image.new("RGBA", (100, 100), (128, 128, 128, 255))

        bg_name = self._bg_var.get() if self._bg_var else "White"
        bg_options = dict(self._get_background_options())
        bg_path = bg_options.get(bg_name)

        # Create background
        if bg_name == "Black":
            bg = Image.new("RGBA", img.size, (0, 0, 0, 255))
        elif bg_name == "White":
            bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
        elif bg_path and bg_path.exists():
            bg = Image.open(bg_path).convert("RGBA")
            # Center-bottom crop background to match character dimensions
            bg_w, bg_h = bg.size
            char_w, char_h = img.size
            # Scale up if background is smaller than character
            if bg_w < char_w or bg_h < char_h:
                scale = max(char_w / bg_w, char_h / bg_h)
                bg = bg.resize((int(bg_w * scale), int(bg_h * scale)), Image.LANCZOS)
                bg_w, bg_h = bg.size
            # Center-bottom crop to character dimensions
            left = (bg_w - char_w) // 2
            top = bg_h - char_h  # Bottom-aligned instead of center
            bg = bg.crop((left, top, left + char_w, top + char_h))
        else:
            bg = Image.new("RGBA", img.size, (255, 255, 255, 255))

        # Composite
        composite = Image.alpha_composite(bg, img)
        composite.thumbnail((max_h, max_h), Image.LANCZOS)

        return ImageTk.PhotoImage(composite)

    def _update_preview(self, idx: int) -> None:
        """Update preview for a single outfit."""
        if idx >= len(self._current_bytes) or idx >= len(self._img_labels):
            return

        # Use stored size to prevent shrinking
        max_h = self._original_preview_sizes.get(idx, 450)
        preview = self._create_preview_image(self._current_bytes[idx], max_h)
        self._thumb_refs[idx] = preview
        self._img_labels[idx].configure(image=preview)

    def _update_all_previews(self) -> None:
        """Update all previews (e.g., when background changes)."""
        for idx in range(len(self._img_labels)):
            self._update_preview(idx)

    def _apply_cleanup(self, idx: int) -> None:
        """Apply cleanup with current slider settings."""
        if idx >= len(self.state.outfit_cleanup_data):
            return

        from ...api.gemini_client import cleanup_edge_halos

        original_bytes, rembg_bytes = self.state.outfit_cleanup_data[idx]
        tol = self._tolerance_vars[idx].get()
        depth = self._depth_vars[idx].get()

        cleaned = cleanup_edge_halos(original_bytes, rembg_bytes, tolerance=tol, passes=depth)
        self._current_bytes[idx] = cleaned
        self.state.current_outfit_bytes = self._current_bytes.copy()

        self._update_preview(idx)

    def _save_cleanup_settings(self) -> None:
        """Save current slider values to state (preserves settings when switching modes)."""
        if not self._tolerance_vars or not self._depth_vars:
            return
        settings = []
        for idx in range(len(self._tolerance_vars)):
            settings.append((self._tolerance_vars[idx].get(), self._depth_vars[idx].get()))
        self.state.outfit_cleanup_settings = settings

    def _switch_to_manual(self, idx: int) -> None:
        """Switch outfit to manual BG removal mode."""
        # Save current cleanup settings before rebuilding (preserves slider values)
        self._save_cleanup_settings()

        self.state.outfit_bg_modes[idx] = "manual"
        # Revert to original black bg bytes for manual editing
        if idx < len(self.state.outfit_cleanup_data) and self.state.outfit_cleanup_data[idx][0]:
            original_bytes, _ = self.state.outfit_cleanup_data[idx]
            self._current_bytes[idx] = original_bytes
            self.state.current_outfit_bytes = self._current_bytes.copy()
        elif idx < len(self.state.outfit_paths) and self.state.outfit_paths[idx].exists():
            # Fallback: read from file if cleanup_data is missing
            self._current_bytes[idx] = self.state.outfit_paths[idx].read_bytes()
            self.state.current_outfit_bytes = self._current_bytes.copy()
        self._build_outfit_cards()  # Rebuild to show manual UI

    def _switch_to_auto(self, idx: int) -> None:
        """Switch outfit back to auto (rembg) mode."""
        # Save current cleanup settings before rebuilding (preserves slider values)
        self._save_cleanup_settings()

        self.state.outfit_bg_modes[idx] = "rembg"
        # Reset to rembg result
        if idx < len(self.state.outfit_cleanup_data):
            _, rembg_bytes = self.state.outfit_cleanup_data[idx]
            self._current_bytes[idx] = rembg_bytes
            self.state.current_outfit_bytes = self._current_bytes.copy()
        self._build_outfit_cards()

    def _regenerate_outfit(self, idx: int, same_prompt: bool = True) -> None:
        """Regenerate a single outfit."""
        if self._is_generating:
            return

        self._is_generating = True
        self.show_loading(f"Regenerating outfit...")

        def regenerate():
            try:
                new_path, new_cleanup, used_prompt = self._do_single_regeneration(idx, same_prompt)
                self.wizard.root.after(0, lambda i=idx, p=new_path, c=new_cleanup, u=used_prompt: self._on_single_regen_complete(i, p, c, u))
            except Exception as e:
                error_msg = str(e)
                self.wizard.root.after(0, lambda msg=error_msg: self._on_generation_error(msg))

        thread = threading.Thread(target=regenerate, daemon=True)
        thread.start()

    def _do_single_regeneration(self, idx: int, same_prompt: bool) -> Tuple[Path, Tuple[bytes, bytes], str]:
        """
        Regenerate a single outfit.

        For underwear with same_prompt=True: Try cached prompt up to 4 times.
        For underwear with same_prompt=False: Start fresh from Tier 0.
        For other outfits: Standard regeneration logic.

        Returns:
            Tuple of (path, (original_bytes, rembg_bytes), used_prompt)

        Raises:
            RuntimeError: If regeneration fails after all attempts.
        """
        from ...processing import generate_single_outfit
        from ...api import build_outfit_prompts_with_config

        # Use generated_outfit_keys which only includes outfits that succeeded
        outfit_names = self.state.generated_outfit_keys.copy() if self.state.generated_outfit_keys else []

        outfit_key = outfit_names[idx]
        outfits_dir = self.state.character_folder / "a" / "outfits"
        config = self.state.outfit_prompt_config.get(outfit_key, {})
        use_random = config.get("use_random", True)

        # =====================================================================
        # UNDERWEAR: Special regeneration handling
        # =====================================================================
        if outfit_key == "underwear" and use_random:
            if same_prompt:
                # "Regen Same Outfit": Try the cached prompt once
                cached_prompt = self.state.outfit_prompts.get(outfit_key) if self.state.outfit_prompts else None

                if cached_prompt:
                    print(f"[Underwear Regen] Using cached prompt: \"{cached_prompt}\"")
                    result = generate_single_outfit(
                        api_key=self.state.api_key,
                        base_pose_path=self.state.base_pose_path,
                        outfits_dir=outfits_dir,
                        gender_style=self.state.gender_style,
                        outfit_key=outfit_key,
                        outfit_desc=cached_prompt,
                        outfit_prompt_config=self.state.outfit_prompt_config,
                        archetype_label=self.state.archetype_label,
                        for_interactive_review=True,
                    )
                    if result is not None:
                        new_path, original_bytes, rembg_bytes, used_prompt = result
                        return new_path, (original_bytes, rembg_bytes), used_prompt

                    # Attempt failed
                    raise RuntimeError(
                        f"Could not regenerate underwear.\n\n"
                        f"The prompt \"{cached_prompt}\" was blocked by safety filters.\n\n"
                        f"Try \"Regen New Outfit\" instead for a different underwear style."
                    )

            # "Regen New Outfit" OR no cached prompt: Start fresh from Tier 0
            # The tier system will be invoked by generate_single_outfit
            result = generate_single_outfit(
                api_key=self.state.api_key,
                base_pose_path=self.state.base_pose_path,
                outfits_dir=outfits_dir,
                gender_style=self.state.gender_style,
                outfit_key=outfit_key,
                outfit_desc="",  # Empty - tier system will pick prompts
                outfit_prompt_config=self.state.outfit_prompt_config,
                archetype_label=self.state.archetype_label,
                for_interactive_review=True,
            )

            if result is None:
                raise RuntimeError(
                    f"Failed to generate underwear outfit.\n\n"
                    f"All tier prompts were blocked by safety filters."
                )

            new_path, original_bytes, rembg_bytes, used_prompt = result
            # Update stored prompt with what actually worked
            if not self.state.outfit_prompts:
                self.state.outfit_prompts = {}
            self.state.outfit_prompts[outfit_key] = used_prompt
            return new_path, (original_bytes, rembg_bytes), used_prompt

        # =====================================================================
        # NON-UNDERWEAR: Standard regeneration
        # =====================================================================
        if same_prompt and self.state.outfit_prompts and outfit_key in self.state.outfit_prompts:
            # Use existing prompt
            outfit_desc = self.state.outfit_prompts[outfit_key]
        else:
            # Generate new random prompt via Gemini text API
            new_prompt_dict = build_outfit_prompts_with_config(
                self.state.api_key,
                self.state.archetype_label,
                self.state.gender_style,
                [outfit_key],
                self.state.outfit_prompt_config,
            )
            outfit_desc = new_prompt_dict[outfit_key]

        result = generate_single_outfit(
            api_key=self.state.api_key,
            base_pose_path=self.state.base_pose_path,
            outfits_dir=outfits_dir,
            gender_style=self.state.gender_style,
            outfit_key=outfit_key,
            outfit_desc=outfit_desc,
            outfit_prompt_config=self.state.outfit_prompt_config,
            archetype_label=self.state.archetype_label,
            for_interactive_review=True,
        )

        if result is None:
            raise RuntimeError(f"Failed to regenerate outfit: {outfit_key}")

        new_path, original_bytes, rembg_bytes, used_prompt = result
        # Update stored prompts with what was actually used
        if not self.state.outfit_prompts:
            self.state.outfit_prompts = {}
        self.state.outfit_prompts[outfit_key] = used_prompt
        return new_path, (original_bytes, rembg_bytes), used_prompt

    def _on_single_regen_complete(self, idx: int, new_path: Path, cleanup_data: Tuple[bytes, bytes], used_prompt: str) -> None:
        """Handle single outfit regeneration completion."""
        self._is_generating = False
        self.hide_loading()

        # Save current cleanup settings before rebuilding (preserves other outfits' settings)
        self._save_cleanup_settings()

        # Update state for regenerated outfit only
        self.state.outfit_paths[idx] = new_path
        self.state.outfit_cleanup_data[idx] = cleanup_data
        _, rembg_bytes = cleanup_data
        self._current_bytes[idx] = rembg_bytes
        self.state.current_outfit_bytes = self._current_bytes.copy()

        # Update the cached prompt with what actually worked (important for underwear)
        # Use generated_outfit_keys which only includes outfits that succeeded
        outfit_names = self.state.generated_outfit_keys.copy() if self.state.generated_outfit_keys else []
        outfit_key = outfit_names[idx]
        if not self.state.outfit_prompts:
            self.state.outfit_prompts = {}
        self.state.outfit_prompts[outfit_key] = used_prompt

        # After regeneration, switch back to auto mode for this outfit
        # (regen always produces auto-removed BG as the result)
        self.state.outfit_bg_modes[idx] = "rembg"

        # Reset cleanup settings for regenerated outfit to defaults (since it's a new image)
        if self.state.outfit_cleanup_settings and idx < len(self.state.outfit_cleanup_settings):
            self.state.outfit_cleanup_settings[idx] = (REMBG_EDGE_CLEANUP_TOLERANCE, REMBG_EDGE_CLEANUP_PASSES)

        # Rebuild cards to show correct UI for mode
        self._build_outfit_cards()

    def _on_regenerate_all(self) -> None:
        """Regenerate all outfits."""
        result = messagebox.askyesno(
            "Regenerate All",
            "This will regenerate all outfits. Continue?"
        )
        if result:
            self._start_outfit_generation()

    def _on_accept(self) -> None:
        """Accept all outfits and continue."""
        if self._is_generating:
            messagebox.showwarning("Generation in Progress", "Please wait for generation to complete.")
            return

        # Save current bytes to disk
        for idx, path in enumerate(self.state.outfit_paths):
            if idx < len(self._current_bytes):
                path.write_bytes(self._current_bytes[idx])

        # Save cleanup settings
        settings = []
        for idx in range(len(self._tolerance_vars)):
            settings.append((self._tolerance_vars[idx].get(), self._depth_vars[idx].get()))
        self.state.outfit_cleanup_settings = settings

        self.request_next()

    def on_leave(self) -> None:
        """Save current bytes to disk and unbind mouse wheel when leaving this step."""
        # Save current bytes to disk so expression generation uses correct images
        # This ensures expression 0 (copied from outfit file) matches what user saw
        for idx, path in enumerate(self.state.outfit_paths):
            if idx < len(self._current_bytes) and self._current_bytes[idx]:
                path.write_bytes(self._current_bytes[idx])

        try:
            self._canvas.unbind_all("<MouseWheel>")
            self._canvas.unbind_all("<Button-4>")
            self._canvas.unbind_all("<Button-5>")
        except Exception:
            pass  # Ignore if already unbound

    def validate(self) -> bool:
        """Validate before advancing."""
        if self._is_generating:
            messagebox.showwarning("Generation in Progress", "Please wait for generation to complete.")
            return False

        if not self.state.outfit_paths:
            messagebox.showerror("No Outfits", "No outfits have been generated.")
            return False

        return True

    def is_dirty(self) -> bool:
        return True

    def get_dirty_steps(self) -> list:
        return [9, 10]  # Expression steps
