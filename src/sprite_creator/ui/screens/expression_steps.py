"""
Expression wizard step (Step 10).

Handles expression generation and review for each outfit.
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
)
from ..tk_common import (
    create_primary_button,
    create_secondary_button,
    show_error_dialog,
)
from .base import WizardStep, WizardState
from ...logging_utils import log_info, log_error, log_generation_start, log_generation_complete


class ExpressionReviewStep(WizardStep):
    """
    Step 10: Expression Review.

    Generates and displays expressions for each outfit.
    Allows per-expression regeneration.
    """

    STEP_ID = "expression_review"
    STEP_TITLE = "Expressions"
    STEP_HELP = """Expression Review

This step shows all generated expressions for each outfit.

HOW THIS RELATES TO THE PREVIOUS STEP
The background removal settings (Tolerance/Depth) you set on the Outfit Review step were used to process these expressions. If backgrounds look good here, those settings worked well!

If backgrounds need work, use the "Touch Up BG" or "Remove BG" buttons below each expression to fix them individually.

IMPORTANT: You must review ALL outfits before proceeding.

═══════════════════════════════════════════════════
TROUBLESHOOTING - WHEN TO REGENERATE
═══════════════════════════════════════════════════

REGENERATE if you see any of these issues:

• Expression goes off-screen or is cropped weirdly
  The AI sometimes generates images that extend past the frame. Click "Regen" to try again.

• Bad framing / expression doesn't match others
  If one expression looks zoomed in/out differently, or the character is positioned differently, regenerate to get better consistency.

• Showing feet or different body position
  All expressions should match the base outfit's framing. If not, regenerate.

• Arm/body pixels look "eaten" or deleted
  This is caused by the automatic background removal (rembg) being too aggressive. You have two options:
  1. Click "Regen" - may produce a version that rembg handles better
  2. Use "Touch Up BG" or "Remove BG" to manually fix it (see below)

═══════════════════════════════════════════════════
HOW TO USE THE FLOOD FILL / TOUCH-UP TOOL
═══════════════════════════════════════════════════

Click "Touch Up BG" or "Remove BG" to open the editor:

1. CLICK on background areas to remove them
   Each click removes a connected area of similar color (flood fill).

2. ADJUST TOLERANCE (slider at top)
   - Low tolerance (10-30): Only removes very similar colors
   - High tolerance (50-80): Removes a wider range of colors
   Start with lower values to avoid accidentally removing parts of the character.

3. Work from OUTSIDE IN
   Click on the main background area first, then work toward edges.

4. For FINE DETAILS (hair strands, edges):
   Lower the tolerance and click carefully on remaining spots.

5. RESTART button: Undoes ALL your changes and starts over.

6. Click ACCEPT when the background is fully removed.

Tip: If you switched to "Manual Mode" on the previous step because rembg was eating arm pixels, use "Remove BG" here to manually remove the black background while preserving the full character.

═══════════════════════════════════════════════════

NAVIGATION
Use the "< Prev" and "Next >" buttons to switch between outfits.

The progress indicator shows:
- Current outfit number and name
- How many outfits you've viewed

The Next button is disabled until you've viewed every outfit at least once.

EXPRESSION CARDS
Each card shows one expression with its number and description.

Expression 0 (neutral) cannot be regenerated - it uses the outfit image directly and is the base for all other expressions.

REGENERATION
Click "Regen" on any expression (except 0) to generate a new version. The AI will create a different interpretation of that expression while keeping the same outfit.

BACKGROUND TOUCH-UP
Each expression has a background button:

"Touch Up BG" (if outfit used auto mode):
Opens a click-based editor starting from the auto-removed result. Use this to clean up any remaining background artifacts around hair, edges, etc.

"Remove BG" (if outfit used manual mode):
Opens a click-based editor starting from the original black-background image. Use this for full manual background removal.

WORKFLOW
1. Use Prev/Next to view each outfit's expressions
2. Regenerate any expressions that don't look right
3. Use "Touch Up BG" to fix any background issues you notice
4. Once all outfits are viewed, click Next

Note: Changes are saved automatically. You can go back and forth between outfits without losing work."""

    def __init__(self, wizard, state: WizardState):
        super().__init__(wizard, state)
        self._canvas: Optional[tk.Canvas] = None
        self._inner_frame: Optional[tk.Frame] = None
        self._outfit_frames: Dict[str, tk.Frame] = {}
        self._img_refs: List[ImageTk.PhotoImage] = []
        self._status_label: Optional[tk.Label] = None
        self._is_generating: bool = False
        self._current_outfit_idx: int = 0
        self._viewed_outfits: set = set()  # Track which outfits have been viewed
        self._progress_label: Optional[tk.Label] = None
        # Store cleanup data for manual BG removal: {"outfit_name": {"0": (orig_bytes, rembg_bytes), ...}}
        self._expression_cleanup_data: Dict[str, Dict[str, Tuple[bytes, bytes]]] = {}
        # Per-card loading: {(outfit_name, expr_key): card_frame}
        self._expr_card_frames: Dict[Tuple[str, str], tk.Frame] = {}
        self._expr_card_overlays: Dict[Tuple[str, str], tk.Frame] = {}
        self._regenerating_expr: Optional[Tuple[str, str]] = None  # (outfit, expr_key)

    def build_ui(self, parent: tk.Frame) -> None:
        parent.configure(bg=BG_COLOR)

        # Header
        header = tk.Frame(parent, bg=BG_COLOR)
        header.pack(fill="x", pady=(0, 8))

        tk.Label(
            header,
            text="Review Expressions",
            bg=BG_COLOR,
            fg=TEXT_COLOR,
            font=PAGE_TITLE_FONT,
        ).pack(side="left")

        # Note: BG mode is determined per-outfit from the Outfits step
        # (removed global BG mode toggle that didn't do anything)

        # Progress indicator (centered) with prev/next arrows
        progress_frame = tk.Frame(parent, bg=BG_COLOR)
        progress_frame.pack(fill="x", pady=(0, 8))

        # Prev button
        self._prev_btn = create_secondary_button(
            progress_frame, "< Prev",
            self._prev_outfit,
            width=8
        )
        self._prev_btn.pack(side="left", padx=(20, 10))

        # Center progress label
        center_frame = tk.Frame(progress_frame, bg=BG_COLOR)
        center_frame.pack(side="left", expand=True)

        self._progress_label = tk.Label(
            center_frame,
            text="Outfit 1 of 1: Loading...",
            bg=BG_COLOR,
            fg=ACCENT_COLOR,
            font=SECTION_FONT,
        )
        self._progress_label.pack()

        # Next button
        self._next_outfit_btn = create_secondary_button(
            progress_frame, "Next >",
            self._next_outfit,
            width=8
        )
        self._next_outfit_btn.pack(side="right", padx=(10, 20))

        # Inline tip
        tk.Label(
            parent,
            text="💡 Use 'Touch Up BG' or 'Remove BG' buttons to fix background issues on any expression. "
                 "You must view ALL outfits before proceeding.",
            bg=BG_COLOR,
            fg="#FFB347",  # Warning orange
            font=SMALL_FONT,
            wraplength=800,
            justify="left",
        ).pack(fill="x", pady=(0, 8))

        # Scrollable canvas for expression cards (horizontal like outfits)
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

        # Status
        self._status_label = tk.Label(
            parent,
            text="",
            bg=BG_COLOR,
            fg=ACCENT_COLOR,
            font=SMALL_FONT,
        )
        self._status_label.pack(pady=(8, 0))

        # Hidden outfit var for compatibility
        self._outfit_var = tk.StringVar(value="")

    def _on_frame_configure(self, event=None) -> None:
        """Update scroll region and bind mouse wheel."""
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))
        # Bind mouse wheel for horizontal scrolling
        self._canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self._canvas.bind_all("<Button-4>", lambda e: self._canvas.xview_scroll(-1, "units"))
        self._canvas.bind_all("<Button-5>", lambda e: self._canvas.xview_scroll(1, "units"))

    def _on_mousewheel(self, event) -> None:
        """Handle mouse wheel for horizontal scrolling."""
        self._canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")

    def _prev_outfit(self) -> None:
        """Navigate to previous outfit."""
        outfit_names = self._get_outfit_names()
        if not outfit_names:
            return
        current_idx = outfit_names.index(self._outfit_var.get()) if self._outfit_var.get() in outfit_names else 0
        if current_idx > 0:
            self._outfit_var.set(outfit_names[current_idx - 1])
            self._show_outfit_expressions()

    def _next_outfit(self) -> None:
        """Navigate to next outfit."""
        outfit_names = self._get_outfit_names()
        if not outfit_names:
            return
        current_idx = outfit_names.index(self._outfit_var.get()) if self._outfit_var.get() in outfit_names else 0
        if current_idx < len(outfit_names) - 1:
            self._outfit_var.set(outfit_names[current_idx + 1])
            self._show_outfit_expressions()

    def _update_progress_indicator(self) -> None:
        """Update the progress indicator label and buttons."""
        outfit_names = self._get_outfit_names()
        if not outfit_names:
            self._progress_label.configure(text="No outfits")
            return

        current_outfit = self._outfit_var.get()
        if current_outfit not in outfit_names:
            current_outfit = outfit_names[0]
            self._outfit_var.set(current_outfit)

        current_idx = outfit_names.index(current_outfit)
        total = len(outfit_names)

        # Mark as viewed
        self._viewed_outfits.add(current_outfit)

        # Update label
        viewed_count = len(self._viewed_outfits)
        self._progress_label.configure(
            text=f"Outfit {current_idx + 1} of {total}: {current_outfit.capitalize()}"
        )

        # Update prev/next button states
        self._prev_btn.configure(state="normal" if current_idx > 0 else "disabled")
        self._next_outfit_btn.configure(state="normal" if current_idx < total - 1 else "disabled")

        # Update status to show progress and control wizard's Next button
        if viewed_count < total:
            self._status_label.configure(
                text=f"Review all outfits before continuing ({viewed_count}/{total} viewed)"
            )
            # Disable wizard's Next button until all outfits are viewed
            self.wizard._next_btn.configure(state="disabled")
        else:
            self._status_label.configure(
                text=f"All {total} outfits reviewed. Click Next to continue."
            )
            # Enable wizard's Next button when all outfits are viewed
            self.wizard._next_btn.configure(state="normal")

    def on_enter(self) -> None:
        """Generate expressions when step becomes active."""
        # Reset viewed outfits tracking
        self._viewed_outfits = set()

        # Disable wizard's Next button initially (will be enabled once all outfits viewed)
        self.wizard._next_btn.configure(state="disabled")

        # Initialize outfit selection
        outfit_names = self._get_outfit_names()
        if outfit_names:
            self._outfit_var.set(outfit_names[0])

        # Check if we already have expressions
        if self.state.expression_paths and len(self.state.expression_paths) > 0:
            first_outfit = list(self.state.expression_paths.keys())[0]
            if all(p.exists() for p in self.state.expression_paths[first_outfit].values()):
                self._show_outfit_expressions()
                self._update_progress_indicator()
                return

        # Generate expressions
        self._start_expression_generation()

    def on_leave(self) -> None:
        """Unbind mouse wheel and restore Next button when leaving this step."""
        # Restore wizard's Next button state
        self.wizard._next_btn.configure(state="normal")

        try:
            self._canvas.unbind_all("<MouseWheel>")
            self._canvas.unbind_all("<Button-4>")
            self._canvas.unbind_all("<Button-5>")
        except Exception:
            pass

    def _get_outfit_names(self) -> List[str]:
        """Get list of outfit names that were actually generated.

        Uses generated_outfit_keys which tracks outfits that succeeded,
        handling cases where outfits like underwear may be skipped due to safety filters.
        """
        # Use generated_outfit_keys if available (includes only outfits that succeeded)
        if self.state.generated_outfit_keys:
            return self.state.generated_outfit_keys.copy()

        # Fallback for backwards compatibility (shouldn't happen in normal flow)
        names = []
        if self.state.use_base_as_outfit:
            names.append("base")
        names.extend(self.state.selected_outfits)
        return names

    def _start_expression_generation(self) -> None:
        """Start generating expressions for all outfits."""
        if self._is_generating:
            return

        self._is_generating = True
        self._current_outfit_idx = 0
        self._status_label.configure(text="Generating expressions...")
        self.show_loading("Generating expressions...")

        # Generate for first outfit, then chain to next
        self._generate_next_outfit()

    def _generate_next_outfit(self) -> None:
        """Generate expressions for the next outfit."""
        outfit_names = self._get_outfit_names()

        if self._current_outfit_idx >= len(outfit_names):
            # All done
            self._is_generating = False
            self.hide_loading()
            self._show_outfit_expressions()
            self._status_label.configure(text="All expressions generated. Review and accept.")
            return

        outfit_name = outfit_names[self._current_outfit_idx]
        outfit_num = self._current_outfit_idx + 1
        total_outfits = len(outfit_names)
        self._status_label.configure(
            text=f"Generating expressions for {outfit_name}... ({outfit_num}/{total_outfits})"
        )

        def update_expression_progress(current: int, total: int, expression_name: str):
            """Update loading message with per-expression progress."""
            self.wizard.root.after(0, lambda: self.show_loading(
                f"Outfit {outfit_num}/{total_outfits}: {outfit_name}\n"
                f"Expression {current}/{total}: {expression_name.replace('_', ' ').title()}"
            ))

        def generate():
            try:
                expr_paths, cleanup_dict = self._do_expression_generation(outfit_name, update_expression_progress)
                self.wizard.root.after(0, lambda n=outfit_name, p=expr_paths, c=cleanup_dict: self._on_outfit_expressions_complete(n, p, c))
            except Exception as e:
                error_msg = str(e)
                self.wizard.root.after(0, lambda msg=error_msg: self._on_generation_error(msg))

        thread = threading.Thread(target=generate, daemon=True)
        thread.start()

    def _do_expression_generation(self, outfit_name: str, progress_callback=None) -> Tuple[Dict[str, Path], Dict[str, Tuple[bytes, bytes]]]:
        """Generate expressions for one outfit."""
        from ...processing import generate_expressions_for_single_outfit_once

        log_generation_start(f"expressions_{outfit_name}", count=len(self.state.expressions_sequence))

        # Find the outfit path
        outfit_names = self._get_outfit_names()
        idx = outfit_names.index(outfit_name)

        if idx >= len(self.state.outfit_paths):
            raise ValueError(f"No outfit path for {outfit_name}")

        outfit_path = self.state.outfit_paths[idx]

        # Determine paths
        pose_dir = self.state.character_folder / "a"
        faces_root = pose_dir / "faces"
        faces_root.mkdir(parents=True, exist_ok=True)

        # Get cleanup settings from outfit review (if available)
        edge_cleanup_tolerance = None
        edge_cleanup_passes = None
        if self.state.outfit_cleanup_settings and idx < len(self.state.outfit_cleanup_settings):
            edge_cleanup_tolerance, edge_cleanup_passes = self.state.outfit_cleanup_settings[idx]

        # Get bg removal mode from outfit review
        bg_removal_mode = self.state.outfit_bg_modes.get(idx, "rembg")

        # Generate expressions - returns (path_list, cleanup_data_list) when for_interactive_review=True
        expr_path_list, cleanup_data_list = generate_expressions_for_single_outfit_once(
            api_key=self.state.api_key,
            pose_dir=pose_dir,
            outfit_path=outfit_path,
            faces_root=faces_root,
            expressions_sequence=self.state.expressions_sequence,
            edge_cleanup_tolerance=edge_cleanup_tolerance,
            edge_cleanup_passes=edge_cleanup_passes,
            for_interactive_review=True,  # Need cleanup_data for manual BG removal
            bg_removal_mode=bg_removal_mode,
            progress_callback=progress_callback,
        )

        # Convert lists to dicts keyed by expression index
        expr_paths: Dict[str, Path] = {}
        cleanup_dict: Dict[str, Tuple[bytes, bytes]] = {}
        for i, path in enumerate(expr_path_list):
            expr_key = str(i)
            expr_paths[expr_key] = path
            if i < len(cleanup_data_list):
                cleanup_dict[expr_key] = cleanup_data_list[i]

        # Fix expression 0's cleanup data - use outfit's original black-bg bytes instead of transparent
        # Expression 0 is just the outfit file, which at this point has transparent BG from rembg.
        # For manual BG removal to work, we need the original black-bg bytes from the outfit step.
        if "0" in cleanup_dict and self.state.outfit_cleanup_data and idx < len(self.state.outfit_cleanup_data):
            original_outfit_bytes, _ = self.state.outfit_cleanup_data[idx]
            if original_outfit_bytes and len(original_outfit_bytes) > 100:
                # Keep the rembg result as the second element (what's currently displayed)
                _, current_rembg = cleanup_dict["0"]
                cleanup_dict["0"] = (original_outfit_bytes, current_rembg)

        return expr_paths, cleanup_dict

    def _on_outfit_expressions_complete(self, outfit_name: str, expr_paths: Dict[str, Path], cleanup_dict: Dict[str, Tuple[bytes, bytes]]) -> None:
        """Handle completion of one outfit's expressions."""
        log_generation_complete(f"expressions_{outfit_name}", True, f"Generated {len(expr_paths)} expressions")

        # Store in state
        if not self.state.expression_paths:
            self.state.expression_paths = {}
        self.state.expression_paths[outfit_name] = expr_paths

        # Store cleanup data for manual BG removal
        self._expression_cleanup_data[outfit_name] = cleanup_dict

        # Move to next outfit
        self._current_outfit_idx += 1
        self._generate_next_outfit()

    def _on_generation_error(self, error: str) -> None:
        """Handle generation error."""
        self._is_generating = False
        log_generation_complete("expressions", False, error)
        # Hide per-card loading if regenerating single expression, otherwise hide full-screen loading
        if self._regenerating_expr is not None:
            outfit_name, expr_key = self._regenerating_expr
            self._hide_expr_card_loading(outfit_name, expr_key)
            self._regenerating_expr = None
        else:
            self.hide_loading()
        self._status_label.configure(text=f"Error: {error}", fg="#ff5555")
        show_error_dialog(self._canvas, "Generation Error", f"Failed to generate expressions:\n\n{error}")

    def _show_outfit_expressions(self) -> None:
        """Display expressions for the currently selected outfit (horizontal layout like outfits)."""
        # Clear existing
        for widget in self._inner_frame.winfo_children():
            widget.destroy()
        self._img_refs.clear()
        self._expr_card_frames.clear()
        self._expr_card_overlays.clear()

        # Update progress indicator
        self._update_progress_indicator()

        outfit_name = self._outfit_var.get()
        if not outfit_name or outfit_name not in self.state.expression_paths:
            return

        expr_paths = self.state.expression_paths[outfit_name]

        # Get canvas dimensions - use same sizing as outfit step
        self._canvas.update_idletasks()
        canvas_h = self._canvas.winfo_height()
        max_thumb_h = max(int(canvas_h * 0.85), 450)  # Match outfit step sizing

        # Build horizontal row of cards (like outfits)
        col = 0
        for expr_key, expr_path in sorted(expr_paths.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 999):
            if not expr_path.exists():
                continue

            card = self._build_expression_card(outfit_name, expr_key, expr_path, max_thumb_h)
            card.grid(row=0, column=col, padx=10, pady=6)
            self._expr_card_frames[(outfit_name, expr_key)] = card
            col += 1

    def _build_expression_card(self, outfit_name: str, expr_key: str, path: Path, max_h: int) -> tk.Frame:
        """Build a single expression card (matching outfit step style)."""
        card = tk.Frame(self._inner_frame, bg=CARD_BG, padx=6, pady=4)

        # Load image with height constraint (like outfit step)
        # Use bytes from cleanup_data if available (avoids file caching issues after edits)
        try:
            if (outfit_name in self._expression_cleanup_data and
                expr_key in self._expression_cleanup_data[outfit_name]):
                # Use the current (potentially edited) bytes from memory
                _, current_bytes = self._expression_cleanup_data[outfit_name][expr_key]
                img = Image.open(BytesIO(current_bytes)).convert("RGBA")
            else:
                # Fall back to reading from disk
                img = Image.open(BytesIO(path.read_bytes())).convert("RGBA")
            # Scale to fit max height while maintaining aspect ratio
            if img.height > max_h:
                ratio = max_h / img.height
                new_w = int(img.width * ratio)
                img = img.resize((new_w, max_h), Image.LANCZOS)

            # Create white background composite
            bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
            composite = Image.alpha_composite(bg, img)

            tk_img = ImageTk.PhotoImage(composite)
            self._img_refs.append(tk_img)

            img_label = tk.Label(card, image=tk_img, bg=CARD_BG)
            img_label.pack()
        except Exception:
            tk.Label(card, text="Error", bg=CARD_BG, fg="#ff5555").pack()

        # Get expression description
        expr_desc = expr_key
        for key, desc in self.state.expressions_sequence:
            if key == expr_key:
                expr_desc = f"{key}: {desc[:20]}..." if len(desc) > 20 else f"{key}: {desc}"
                break

        # Caption
        tk.Label(
            card,
            text=expr_desc,
            bg=CARD_BG,
            fg=TEXT_COLOR,
            font=BODY_FONT,
        ).pack(pady=(2, 2))

        # Buttons row (horizontal like outfits)
        btn_row = tk.Frame(card, bg=CARD_BG)
        btn_row.pack(pady=(2, 0))

        # Expression 0 (neutral) cannot be regenerated - it comes directly from the outfit
        if expr_key != "0":
            # Regenerate button
            create_secondary_button(
                btn_row, "Regen",
                lambda o=outfit_name, e=expr_key: self._regenerate_expression(o, e),
                width=6
            ).pack(side="left", padx=(0, 4))

        # BG removal button - label depends on outfit's BG mode
        outfit_names = self._get_outfit_names()
        outfit_idx = outfit_names.index(outfit_name) if outfit_name in outfit_names else 0
        bg_mode = self.state.outfit_bg_modes.get(outfit_idx, "rembg")
        btn_label = "Touch Up BG" if bg_mode == "rembg" else "Remove BG"

        create_secondary_button(
            btn_row, btn_label,
            lambda o=outfit_name, e=expr_key, p=path: self._open_manual_bg(o, e, p),
            width=10
        ).pack(side="left")

        return card

    def _show_expr_card_loading(self, outfit_name: str, expr_key: str, message: str = "Regenerating...") -> None:
        """Show a loading overlay on a specific expression card."""
        key = (outfit_name, expr_key)
        if key not in self._expr_card_frames:
            return

        card = self._expr_card_frames[key]

        # Create semi-transparent overlay frame
        overlay = tk.Frame(card, bg="#1a1a2e")
        overlay.place(relx=0, rely=0, relwidth=1, relheight=1)

        # Loading message
        tk.Label(
            overlay,
            text=message,
            bg="#1a1a2e",
            fg=TEXT_COLOR,
            font=BODY_FONT,
            wraplength=150,
        ).place(relx=0.5, rely=0.5, anchor="center")

        self._expr_card_overlays[key] = overlay

    def _hide_expr_card_loading(self, outfit_name: str, expr_key: str) -> None:
        """Hide the loading overlay on a specific expression card."""
        key = (outfit_name, expr_key)
        if key in self._expr_card_overlays:
            try:
                self._expr_card_overlays[key].destroy()
            except tk.TclError:
                pass
            del self._expr_card_overlays[key]

    def _regenerate_expression(self, outfit_name: str, expr_key: str) -> None:
        """Regenerate a single expression."""
        if self._is_generating:
            return

        self._is_generating = True
        self._regenerating_expr = (outfit_name, expr_key)
        self._status_label.configure(text=f"Regenerating expression {expr_key}...")
        # Use per-card loading instead of full-screen overlay
        self._show_expr_card_loading(outfit_name, expr_key, "Regenerating\nexpression...")

        def regenerate():
            try:
                new_path = self._do_single_expression_regen(outfit_name, expr_key)
                self.wizard.root.after(0, lambda o=outfit_name, e=expr_key, p=new_path: self._on_single_expr_complete(o, e, p))
            except Exception as e:
                error_msg = str(e)
                self.wizard.root.after(0, lambda msg=error_msg: self._on_generation_error(msg))

        thread = threading.Thread(target=regenerate, daemon=True)
        thread.start()

    def _do_single_expression_regen(self, outfit_name: str, expr_key: str) -> Path:
        """Regenerate a single expression."""
        from ...processing import regenerate_single_expression

        # Get outfit path
        outfit_names = self._get_outfit_names()
        idx = outfit_names.index(outfit_name)
        outfit_path = self.state.outfit_paths[idx]

        # Determine output directory based on outfit name
        pose_dir = self.state.character_folder / "a"
        if outfit_name.lower() == "base":
            out_dir = pose_dir / "faces" / "face"
        else:
            out_dir = pose_dir / "faces" / outfit_name

        # Convert expr_key to index
        expr_index = int(expr_key)

        # Get cleanup settings from outfit review (if available)
        edge_cleanup_tolerance = None
        edge_cleanup_passes = None
        if self.state.outfit_cleanup_settings and idx < len(self.state.outfit_cleanup_settings):
            edge_cleanup_tolerance, edge_cleanup_passes = self.state.outfit_cleanup_settings[idx]

        # Get bg removal mode from outfit review
        bg_removal_mode = self.state.outfit_bg_modes.get(idx, "rembg")

        new_path = regenerate_single_expression(
            api_key=self.state.api_key,
            outfit_path=outfit_path,
            out_dir=out_dir,
            expressions_sequence=self.state.expressions_sequence,
            expr_index=expr_index,
            edge_cleanup_tolerance=edge_cleanup_tolerance,
            edge_cleanup_passes=edge_cleanup_passes,
            bg_removal_mode=bg_removal_mode,
        )

        return new_path

    def _on_single_expr_complete(self, outfit_name: str, expr_key: str, new_path: Path) -> None:
        """Handle single expression regeneration completion."""
        self._is_generating = False
        self._hide_expr_card_loading(outfit_name, expr_key)
        self._regenerating_expr = None

        # Update state
        self.state.expression_paths[outfit_name][expr_key] = new_path

        # Refresh display
        self._show_outfit_expressions()
        self._status_label.configure(text=f"Expression {expr_key} regenerated.")

    def _open_manual_bg(self, outfit_name: str, expr_key: str, path: Path) -> None:
        """Open manual background removal for an expression."""
        if self._is_generating:
            return

        # Get original black-bg bytes from stored cleanup data
        if outfit_name not in self._expression_cleanup_data:
            messagebox.showerror("Error", "No original image data available for this outfit.")
            return

        cleanup_data = self._expression_cleanup_data[outfit_name].get(expr_key)
        if not cleanup_data:
            messagebox.showerror("Error", f"No cleanup data for expression {expr_key}.")
            return

        original_bytes, rembg_bytes = cleanup_data

        # Determine which bytes to use based on outfit's BG mode
        # "Touch Up" mode (rembg): Start from rembg result, so Restart goes back to rembg output
        # "Remove BG" mode (manual): Start from original black-bg, so Restart goes back to original
        outfit_names = self._get_outfit_names()
        outfit_idx = outfit_names.index(outfit_name) if outfit_name in outfit_names else 0
        bg_mode = self.state.outfit_bg_modes.get(outfit_idx, "rembg")

        if bg_mode == "rembg":
            # Touch Up mode: use rembg result as starting point
            working_bytes = rembg_bytes
        else:
            # Manual mode: use original black-bg as starting point
            working_bytes = original_bytes

        # Verify bytes are valid
        if not working_bytes or len(working_bytes) < 100:
            messagebox.showerror("Error", "Image data is missing or invalid.")
            return

        # Check if the expression file path still exists (may have been moved by flattening)
        if not path.exists():
            log_error("Manual BG removal", f"Expression file no longer exists: {path}")
            messagebox.showerror(
                "File Not Found",
                f"The expression file no longer exists at:\n{path}\n\n"
                "This can happen if you navigated back after the character was finalized. "
                "The folder structure may have changed."
            )
            return

        # Write to temp file for manual editing - use a safe temp location
        # Use the expression file's directory if it exists
        temp_dir = path.parent
        if not temp_dir.exists():
            log_error("Manual BG removal", f"Directory no longer exists: {temp_dir}")
            messagebox.showerror(
                "Directory Not Found",
                f"The directory no longer exists:\n{temp_dir}\n\n"
                "This can happen if you navigated back after the character was finalized."
            )
            return

        temp_path = temp_dir / f"_temp_manual_{expr_key}.png"

        try:
            temp_path.write_bytes(working_bytes)
            log_info(f"Wrote temp file for manual BG edit: {temp_path} ({len(working_bytes)} bytes)")
        except Exception as e:
            log_error("Manual BG removal", f"Failed to write temp file: {e}")
            messagebox.showerror("Error", f"Failed to create temp file:\n{e}")
            return

        # Verify temp file was written
        if not temp_path.exists():
            log_error("Manual BG removal", "Temp file doesn't exist after writing")
            messagebox.showerror("Error", "Failed to create temp file for editing.")
            return

        from ..review_windows import click_to_remove_background
        accepted = click_to_remove_background(temp_path, threshold=30)

        if accepted:
            # Verify temp file still exists after editor closed
            if not temp_path.exists():
                log_error("Manual BG removal", f"Temp file missing after editor closed: {temp_path}")
                messagebox.showerror(
                    "Error",
                    "The edited file could not be found after the editor closed.\n"
                    "Please try again."
                )
                return

            # Read edited bytes from temp file
            try:
                edited_bytes = temp_path.read_bytes()
            except Exception as e:
                log_error("Manual BG removal", f"Failed to read temp file: {e}")
                messagebox.showerror("Error", f"Failed to read edited image:\n{e}")
                return

            # Verify we got valid edited bytes
            if not edited_bytes or len(edited_bytes) < 100:
                log_error("Manual BG removal", "Failed to read edited image - bytes empty or too small")
                messagebox.showerror("Error", "Failed to read edited image from temp file.")
                return

            # Write to the expression file on disk
            try:
                path.write_bytes(edited_bytes)
                log_info(f"Saved manually edited BG for {outfit_name}/{expr_key} ({len(edited_bytes)} bytes)")
            except Exception as e:
                log_error("Manual BG removal", f"Failed to save edited image: {e}")
                messagebox.showerror("Error", f"Failed to save edited image:\n{e}")
                return

            # Update cleanup data with edited result (keep original for future Restart, update current display bytes)
            self._expression_cleanup_data[outfit_name][expr_key] = (original_bytes, edited_bytes)

            # Force complete UI refresh - schedule it after the modal fully closes
            # This ensures the modal window is destroyed before we try to rebuild cards
            def refresh_display():
                # Clear and rebuild all expression cards
                self._show_outfit_expressions()
                # Force canvas to fully update
                self._canvas.update()
                self._inner_frame.update()
                self._status_label.configure(text=f"Manual BG removal applied to expression {expr_key}.")
                log_info(f"UI refreshed after manual BG edit for {expr_key}")

            # Use after(50) to let the modal window fully close before refreshing
            self.wizard.root.after(50, refresh_display)

        # Clean up temp file
        if temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass  # Ignore cleanup errors

    def _on_regenerate_all(self) -> None:
        """Regenerate all expressions."""
        result = messagebox.askyesno(
            "Regenerate All",
            "This will regenerate all expressions for all outfits. Continue?"
        )
        if result:
            self.state.expression_paths = {}
            self._start_expression_generation()

    def _on_accept(self) -> None:
        """Accept all expressions."""
        if self._is_generating:
            messagebox.showwarning("Generation in Progress", "Please wait for generation to complete.")
            return

        self.request_next()

    def validate(self) -> bool:
        """Validate before advancing."""
        if self._is_generating:
            messagebox.showwarning("Generation in Progress", "Please wait for generation to complete.")
            return False

        if not self.state.expression_paths:
            messagebox.showerror("No Expressions", "No expressions have been generated.")
            return False

        # Check all outfits have been viewed
        outfit_names = self._get_outfit_names()
        if len(self._viewed_outfits) < len(outfit_names):
            unviewed = [name for name in outfit_names if name not in self._viewed_outfits]
            messagebox.showwarning(
                "Review All Outfits",
                f"Please review expressions for all outfits before continuing.\n\n"
                f"Not yet viewed: {', '.join(unviewed)}"
            )
            return False

        return True
