"""
Review wizard step.

- ReviewStep: Step 4 - Review base image and selected options before generation
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional

from PIL import Image, ImageTk

from ...config import (
    BG_COLOR,
    CARD_BG,
    TEXT_COLOR,
    TEXT_SECONDARY,
    ACCENT_COLOR,
    PAGE_TITLE_FONT,
    SECTION_FONT,
    BODY_FONT,
    SMALL_FONT,
    EXPRESSIONS_SEQUENCE,
)
from .base import WizardStep, WizardState


class ReviewStep(WizardStep):
    """
    Step 4: Review Before Generation.

    Review step showing the base image and selected options before
    proceeding to outfit and expression generation. No generation
    happens here - it's purely for reviewing the character and settings.
    """

    STEP_ID = "review"
    STEP_TITLE = "Review"
    STEP_HELP = """Review Before Generation

This is your final check before the AI starts generating images.

LEFT SIDE: BASE CHARACTER
Shows the image that will be used as the reference for all outfit and expression generation. This is your cropped/modified image from Step 2.

If this doesn't look right, click Back to return to the previous steps.

RIGHT SIDE: SELECTED OPTIONS
Summary of your choices:

Character: Name, voice, and archetype
Base Outfit: Whether the base image is included as an outfit
Outfits to Generate: List of outfit types selected
Expressions to Generate: Number of expressions per outfit

IMPORTANT NOTICE (if shown)
If you selected custom outfits, custom expressions, or underwear, a warning box appears. Gemini's safety filters may block some generations.

You must check the acknowledgment box before proceeding:
"I understand that some items may not generate"

If an outfit or expression is blocked, it will be skipped - the wizard will continue with the items that succeed.

WHAT HAPPENS NEXT
Clicking "Accept" starts outfit generation:
1. Each selected outfit is generated using your base image
2. Automatic background removal is applied
3. You'll review each outfit and can regenerate or adjust

This process requires API calls to Gemini and may take several minutes depending on how many outfits you selected.

Click Accept when ready to begin generation."""

    def __init__(self, wizard, state: WizardState):
        super().__init__(wizard, state)
        self._preview_label: Optional[tk.Label] = None
        self._preview_frame: Optional[tk.Frame] = None
        self._options_frame: Optional[tk.Frame] = None
        self._tk_img: Optional[ImageTk.PhotoImage] = None
        # Acknowledgment checkbox for risky options
        self._ack_var: Optional[tk.IntVar] = None
        self._ack_frame: Optional[tk.Frame] = None
        self._has_risky_options: bool = False

    def build_ui(self, parent: tk.Frame) -> None:
        parent.configure(bg=BG_COLOR)

        # Title
        tk.Label(
            parent,
            text="Review Before Generation",
            bg=BG_COLOR,
            fg=TEXT_COLOR,
            font=PAGE_TITLE_FONT,
        ).pack(pady=(0, 8))

        # Instructions
        tk.Label(
            parent,
            text="Review your character and selected options before generating outfits and expressions.",
            bg=BG_COLOR,
            fg=TEXT_SECONDARY,
            font=SMALL_FONT,
        ).pack(pady=(0, 12))

        # Main content area - two columns
        content = tk.Frame(parent, bg=BG_COLOR)
        content.pack(fill="both", expand=True)

        # Left: Image preview
        left_frame = tk.Frame(content, bg=BG_COLOR)
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 16))

        tk.Label(
            left_frame,
            text="Base Character",
            bg=BG_COLOR,
            fg=TEXT_COLOR,
            font=SECTION_FONT,
        ).pack(anchor="w", pady=(0, 8))

        self._preview_frame = tk.Frame(left_frame, bg=CARD_BG, padx=4, pady=4)
        self._preview_frame.pack(expand=True, anchor="n")

        self._preview_label = tk.Label(
            self._preview_frame,
            text="Loading...",
            bg=CARD_BG,
            fg=TEXT_SECONDARY,
            font=BODY_FONT,
            width=40,
            height=20,
        )
        self._preview_label.pack()

        # Right: Selected options
        right_frame = tk.Frame(content, bg=BG_COLOR, width=320)
        right_frame.pack(side="right", fill="y", padx=(16, 0))
        right_frame.pack_propagate(False)

        tk.Label(
            right_frame,
            text="Selected Options",
            bg=BG_COLOR,
            fg=TEXT_COLOR,
            font=SECTION_FONT,
        ).pack(anchor="w", pady=(0, 12))

        # Options will be populated in on_enter
        self._options_frame = tk.Frame(right_frame, bg=BG_COLOR)
        self._options_frame.pack(fill="both", expand=True)

    def _check_risky_options(self) -> bool:
        """Check if user has selected options that might trigger Gemini safety filters."""
        # Check for custom outfit prompts or underwear
        if self.state.outfit_prompt_config:
            for key, config in self.state.outfit_prompt_config.items():
                # Custom prompt means user typed something
                if config.get("custom_prompt"):
                    return True
                # Underwear with random mode is risky
                if key == "underwear" and config.get("use_random"):
                    return True

        # Check for custom expressions (beyond standard set)
        if self.state.expressions_sequence:
            standard_keys = {key for key, _ in EXPRESSIONS_SEQUENCE}
            for key, _ in self.state.expressions_sequence:
                if key not in standard_keys:
                    return True

        return False

    def _on_ack_changed(self) -> None:
        """Handle acknowledgment checkbox state change."""
        if hasattr(self.wizard, '_next_btn') and self.wizard._next_btn:
            if self._ack_var and self._ack_var.get() == 1:
                self.wizard._next_btn.configure(state="normal")
            else:
                self.wizard._next_btn.configure(state="disabled")

    def on_enter(self) -> None:
        """Display base image and selected options when step becomes active."""
        # Check for risky options first
        self._has_risky_options = self._check_risky_options()

        # Change Next button to "Accept" for this review step
        if hasattr(self.wizard, '_next_btn') and self.wizard._next_btn:
            self.wizard._next_btn.configure(text="Accept")
            # Disable if risky options and not acknowledged
            if self._has_risky_options:
                if not self._ack_var or self._ack_var.get() == 0:
                    self.wizard._next_btn.configure(state="disabled")

        # Display the base image from Step 2
        self._display_base_image()

        # Display selected options from Step 3
        self._display_options()

        # Set base_pose_path to the cropped image for downstream steps
        if self.state.cropped_image_path and self.state.cropped_image_path.exists():
            self.state.base_pose_path = self.state.cropped_image_path

    def on_exit(self) -> None:
        """Restore Next button text and state when leaving step."""
        if hasattr(self.wizard, '_next_btn') and self.wizard._next_btn:
            self.wizard._next_btn.configure(text="Next", state="normal")

    def _display_base_image(self) -> None:
        """Display the base character image from Step 2."""
        # Try cropped image first, then fall back to source image
        image_path = None
        if self.state.cropped_image_path and self.state.cropped_image_path.exists():
            image_path = self.state.cropped_image_path
        elif self.state.image_path and self.state.image_path.exists():
            image_path = self.state.image_path

        if image_path is None:
            self._preview_label.configure(
                text="No image available.\nPlease go back to Step 2.",
                fg="#ff5555",
            )
            return

        try:
            img = Image.open(image_path).convert("RGBA")

            # Get display dimensions
            parent = self._preview_label.winfo_toplevel()
            max_h = int(parent.winfo_screenheight() * 0.50)
            max_w = int(parent.winfo_screenwidth() * 0.30)

            # Scale to fit
            img.thumbnail((max_w, max_h), Image.LANCZOS)

            self._tk_img = ImageTk.PhotoImage(img)
            self._preview_label.configure(
                image=self._tk_img,
                text="",
                width=img.width,
                height=img.height,
            )
        except Exception as e:
            self._preview_label.configure(
                text=f"Error loading image:\n{e}",
                fg="#ff5555",
            )

    def _display_options(self) -> None:
        """Display the selected options from Step 3."""
        # Clear existing options
        for widget in self._options_frame.winfo_children():
            widget.destroy()

        # Character info section
        info_frame = tk.Frame(self._options_frame, bg=CARD_BG, padx=12, pady=10)
        info_frame.pack(fill="x", pady=(0, 12))

        tk.Label(
            info_frame,
            text="Character",
            bg=CARD_BG,
            fg=ACCENT_COLOR,
            font=BODY_FONT,
        ).pack(anchor="w")

        tk.Label(
            info_frame,
            text=f"Name: {self.state.display_name or 'Not set'}",
            bg=CARD_BG,
            fg=TEXT_COLOR,
            font=SMALL_FONT,
        ).pack(anchor="w", pady=(4, 0))

        tk.Label(
            info_frame,
            text=f"Voice: {(self.state.voice or 'Not set').capitalize()}",
            bg=CARD_BG,
            fg=TEXT_COLOR,
            font=SMALL_FONT,
        ).pack(anchor="w")

        tk.Label(
            info_frame,
            text=f"Archetype: {self.state.archetype_label or 'Not set'}",
            bg=CARD_BG,
            fg=TEXT_COLOR,
            font=SMALL_FONT,
        ).pack(anchor="w")

        # Base outfit section
        base_outfit_frame = tk.Frame(self._options_frame, bg=CARD_BG, padx=12, pady=10)
        base_outfit_frame.pack(fill="x", pady=(0, 12))

        tk.Label(
            base_outfit_frame,
            text="Base Outfit",
            bg=CARD_BG,
            fg=ACCENT_COLOR,
            font=BODY_FONT,
        ).pack(anchor="w")

        include_base = "Yes" if self.state.use_base_as_outfit else "No"
        tk.Label(
            base_outfit_frame,
            text=f"Include as outfit: {include_base}",
            bg=CARD_BG,
            fg=TEXT_COLOR,
            font=SMALL_FONT,
        ).pack(anchor="w", pady=(4, 0))

        # Outfits section
        outfits_frame = tk.Frame(self._options_frame, bg=CARD_BG, padx=12, pady=10)
        outfits_frame.pack(fill="x", pady=(0, 12))

        tk.Label(
            outfits_frame,
            text="Outfits to Generate",
            bg=CARD_BG,
            fg=ACCENT_COLOR,
            font=BODY_FONT,
        ).pack(anchor="w")

        if self.state.selected_outfits:
            outfit_count = len(self.state.selected_outfits)
            outfit_names = ", ".join([o.capitalize() for o in self.state.selected_outfits[:5]])
            if outfit_count > 5:
                outfit_names += f" (+{outfit_count - 5} more)"
            tk.Label(
                outfits_frame,
                text=f"{outfit_count} outfits: {outfit_names}",
                bg=CARD_BG,
                fg=TEXT_COLOR,
                font=SMALL_FONT,
                wraplength=280,
                justify="left",
            ).pack(anchor="w", pady=(4, 0))
        else:
            tk.Label(
                outfits_frame,
                text="No additional outfits selected",
                bg=CARD_BG,
                fg=TEXT_SECONDARY,
                font=SMALL_FONT,
            ).pack(anchor="w", pady=(4, 0))

        # Expressions section
        expr_frame = tk.Frame(self._options_frame, bg=CARD_BG, padx=12, pady=10)
        expr_frame.pack(fill="x", pady=(0, 12))

        tk.Label(
            expr_frame,
            text="Expressions to Generate",
            bg=CARD_BG,
            fg=ACCENT_COLOR,
            font=BODY_FONT,
        ).pack(anchor="w")

        if self.state.expressions_sequence:
            expr_count = len(self.state.expressions_sequence)
            tk.Label(
                expr_frame,
                text=f"{expr_count} expressions (including neutral)",
                bg=CARD_BG,
                fg=TEXT_COLOR,
                font=SMALL_FONT,
            ).pack(anchor="w", pady=(4, 0))
        else:
            tk.Label(
                expr_frame,
                text="Default expressions",
                bg=CARD_BG,
                fg=TEXT_SECONDARY,
                font=SMALL_FONT,
            ).pack(anchor="w", pady=(4, 0))

        # Acknowledgment section for risky options
        if self._has_risky_options:
            self._ack_frame = tk.Frame(self._options_frame, bg=CARD_BG, padx=12, pady=10)
            self._ack_frame.pack(fill="x", pady=(0, 12))

            tk.Label(
                self._ack_frame,
                text="⚠️ Important Notice",
                bg=CARD_BG,
                fg="#FFB347",  # Warning orange
                font=BODY_FONT,
            ).pack(anchor="w")

            tk.Label(
                self._ack_frame,
                text="You have selected custom outfits, expressions, or underwear options. "
                     "Gemini's safety filters may block some generations. "
                     "If this happens, affected items will be skipped.",
                bg=CARD_BG,
                fg=TEXT_COLOR,
                font=SMALL_FONT,
                wraplength=280,
                justify="left",
            ).pack(anchor="w", pady=(4, 8))

            # Checkbox for acknowledgment
            self._ack_var = tk.IntVar(value=0)
            ack_check = ttk.Checkbutton(
                self._ack_frame,
                text="I understand that some items may not generate",
                variable=self._ack_var,
                command=self._on_ack_changed,
            )
            ack_check.pack(anchor="w")

    def validate(self) -> bool:
        """Validate before advancing."""
        # Check we have a base image
        if not self.state.cropped_image_path or not self.state.cropped_image_path.exists():
            if not self.state.image_path or not self.state.image_path.exists():
                messagebox.showerror(
                    "No Base Image",
                    "No base image found. Please go back to Step 2."
                )
                return False

        # Check acknowledgment if risky options are selected
        if self._has_risky_options:
            if not self._ack_var or self._ack_var.get() == 0:
                messagebox.showwarning(
                    "Acknowledgment Required",
                    "Please check the box to acknowledge that some items may not generate."
                )
                return False

        return True

    def should_skip(self) -> bool:
        """Never skip - this step is used for both image and prompt modes."""
        return False

    def is_dirty(self) -> bool:
        """Check if review affects downstream steps."""
        return False  # Review-only, no changes made here

    def get_dirty_steps(self) -> list:
        """Review doesn't invalidate other steps."""
        return []
