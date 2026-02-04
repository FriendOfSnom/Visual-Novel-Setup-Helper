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
)
from .base import WizardStep, WizardState


class ExpressionReviewStep(WizardStep):
    """
    Step 10: Expression Review.

    Generates and displays expressions for each outfit.
    Allows per-expression regeneration.
    """

    STEP_ID = "expression_review"
    STEP_TITLE = "Expressions"
    STEP_HELP = """Expression Review

Review the generated expressions for each outfit.

The system generates one neutral expression (0) plus all selected expressions
for each outfit that was generated.

Per-Expression Options:
- Regenerate: Generate a new version of that specific expression

All outfits share the same expression set for consistency.

Accept All when satisfied to continue to finalization."""

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
        """Get list of outfit names."""
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
        self._status_label.configure(
            text=f"Generating expressions for {outfit_name}... ({self._current_outfit_idx + 1}/{len(outfit_names)})"
        )

        def generate():
            try:
                expr_paths = self._do_expression_generation(outfit_name)
                self.wizard.root.after(0, lambda n=outfit_name, p=expr_paths: self._on_outfit_expressions_complete(n, p))
            except Exception as e:
                error_msg = str(e)
                self.wizard.root.after(0, lambda msg=error_msg: self._on_generation_error(msg))

        thread = threading.Thread(target=generate, daemon=True)
        thread.start()

    def _do_expression_generation(self, outfit_name: str) -> Dict[str, Path]:
        """Generate expressions for one outfit."""
        from ...processing import generate_expressions_for_single_outfit_once

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

        # Generate expressions - returns list of paths
        expr_path_list = generate_expressions_for_single_outfit_once(
            api_key=self.state.api_key,
            pose_dir=pose_dir,
            outfit_path=outfit_path,
            faces_root=faces_root,
            expressions_sequence=self.state.expressions_sequence,
            edge_cleanup_tolerance=edge_cleanup_tolerance,
            edge_cleanup_passes=edge_cleanup_passes,
            for_interactive_review=False,  # We handle review in the wizard
            bg_removal_mode=bg_removal_mode,
        )

        # Convert list to dict keyed by expression index
        expr_paths: Dict[str, Path] = {}
        for i, path in enumerate(expr_path_list):
            # Expression key is the index (0 = neutral, 1+ = selected expressions)
            expr_key = str(i)
            expr_paths[expr_key] = path

        return expr_paths

    def _on_outfit_expressions_complete(self, outfit_name: str, expr_paths: Dict[str, Path]) -> None:
        """Handle completion of one outfit's expressions."""
        # Store in state
        if not self.state.expression_paths:
            self.state.expression_paths = {}
        self.state.expression_paths[outfit_name] = expr_paths

        # Move to next outfit
        self._current_outfit_idx += 1
        self._generate_next_outfit()

    def _on_generation_error(self, error: str) -> None:
        """Handle generation error."""
        self._is_generating = False
        self.hide_loading()
        self._status_label.configure(text=f"Error: {error}", fg="#ff5555")
        messagebox.showerror("Generation Error", f"Failed to generate expressions:\n\n{error}")

    def _show_outfit_expressions(self) -> None:
        """Display expressions for the currently selected outfit (horizontal layout like outfits)."""
        # Clear existing
        for widget in self._inner_frame.winfo_children():
            widget.destroy()
        self._img_refs.clear()

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
            col += 1

    def _build_expression_card(self, outfit_name: str, expr_key: str, path: Path, max_h: int) -> tk.Frame:
        """Build a single expression card (matching outfit step style)."""
        card = tk.Frame(self._inner_frame, bg=CARD_BG, padx=6, pady=4)

        # Load image with height constraint (like outfit step)
        try:
            img = Image.open(path).convert("RGBA")
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

    def _regenerate_expression(self, outfit_name: str, expr_key: str) -> None:
        """Regenerate a single expression."""
        if self._is_generating:
            return

        self._is_generating = True
        self._status_label.configure(text=f"Regenerating {expr_key}...")
        self.show_loading(f"Regenerating expression...")

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
        self.hide_loading()

        # Update state
        self.state.expression_paths[outfit_name][expr_key] = new_path

        # Refresh display
        self._show_outfit_expressions()
        self._status_label.configure(text=f"Expression {expr_key} regenerated.")

    def _open_manual_bg(self, outfit_name: str, expr_key: str, path: Path) -> None:
        """Open manual background removal for an expression."""
        if self._is_generating:
            return

        if not path.exists():
            messagebox.showerror("Error", f"Expression file not found: {path}")
            return

        # Verify file has content
        if path.stat().st_size < 100:  # Minimum size for a valid PNG
            messagebox.showerror("Error", f"Expression file appears to be empty or corrupted: {path}")
            return

        # Open manual removal (blocking call)
        from ..review_windows import click_to_remove_background

        accepted = click_to_remove_background(path, threshold=30)

        if accepted:
            # Refresh display to show changes
            self._show_outfit_expressions()
            self._status_label.configure(text=f"Manual BG removal applied to expression {expr_key}.")

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
