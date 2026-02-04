"""
Generation wizard steps (Steps 6-7).

These steps handle base pose generation and review.
- Step 6: Base Generation & Review (for image mode)
- Step 7: Prompt-Generated Review (for prompt mode)
"""

import threading
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from typing import Optional

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
    create_danger_button,
)
from .base import WizardStep, WizardState


class BaseGenerationStep(WizardStep):
    """
    Step 6: Base Generation & Review.

    Generates the normalized base pose and allows user to accept,
    regenerate with instructions, or reset to original.
    """

    STEP_ID = "base_generation"
    STEP_TITLE = "Base Image"
    STEP_HELP = """Base Character Image

Review your normalized base character image.

You must choose whether to include this image as a 'Base' outfit:
- Yes: This image will be included as one of the character's outfits
- No: Only the other outfits you selected will be generated

If you need to make changes to the character, use the Back button
to return to the previous step.
"""

    def __init__(self, wizard, state: WizardState):
        super().__init__(wizard, state)
        self._preview_label: Optional[tk.Label] = None
        self._preview_frame: Optional[tk.Frame] = None
        self._use_as_outfit_var: Optional[tk.IntVar] = None
        self._status_label: Optional[tk.Label] = None
        self._btn_frame: Optional[tk.Frame] = None
        self._accept_btn: Optional[tk.Button] = None
        self._tk_img: Optional[ImageTk.PhotoImage] = None
        self._is_generating: bool = False

    def build_ui(self, parent: tk.Frame) -> None:
        parent.configure(bg=BG_COLOR)

        # Title
        tk.Label(
            parent,
            text="Review Base Character Image",
            bg=BG_COLOR,
            fg=TEXT_COLOR,
            font=PAGE_TITLE_FONT,
        ).pack(pady=(0, 8))

        # Instructions
        tk.Label(
            parent,
            text="Review the base image and choose whether to include it as an outfit.",
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

        self._preview_frame = tk.Frame(left_frame, bg=CARD_BG, padx=4, pady=4)
        self._preview_frame.pack(expand=True)

        self._preview_label = tk.Label(
            self._preview_frame,
            text="Generating...",
            bg=CARD_BG,
            fg=TEXT_SECONDARY,
            font=BODY_FONT,
            width=40,
            height=20,
        )
        self._preview_label.pack()

        # Right: Controls
        right_frame = tk.Frame(content, bg=BG_COLOR, width=280)
        right_frame.pack(side="right", fill="y", padx=(16, 0))
        right_frame.pack_propagate(False)

        # Use as outfit - styled card with prominent border
        outfit_option_frame = tk.Frame(right_frame, bg=CARD_BG, padx=16, pady=16,
                                       highlightbackground=ACCENT_COLOR, highlightthickness=2)
        outfit_option_frame.pack(fill="x", pady=(0, 16))

        tk.Label(
            outfit_option_frame,
            text="Include as Base Outfit?",
            bg=CARD_BG,
            fg=ACCENT_COLOR,
            font=SECTION_FONT,
        ).pack(anchor="w")

        tk.Label(
            outfit_option_frame,
            text="Select whether to include this image as one of the character's outfits.\nYou must make a selection to continue.",
            bg=CARD_BG,
            fg=TEXT_SECONDARY,
            font=SMALL_FONT,
        ).pack(anchor="w", pady=(2, 8))

        # Start with no selection (-1) to require explicit choice
        self._use_as_outfit_var = tk.IntVar(value=-1)
        option_btns = tk.Frame(outfit_option_frame, bg=CARD_BG)
        option_btns.pack(anchor="w")

        # Larger, more prominent buttons with vertical layout
        self._yes_rb = tk.Radiobutton(
            option_btns,
            text="  Yes - Include this as a 'Base' outfit  ",
            variable=self._use_as_outfit_var,
            value=1,
            bg=CARD_BG,
            fg=TEXT_COLOR,
            selectcolor=BG_COLOR,
            activebackground=CARD_BG,
            activeforeground=TEXT_COLOR,
            font=BODY_FONT,
            indicatoron=True,
            padx=10,
            pady=6,
        )
        self._yes_rb.pack(anchor="w", pady=(0, 8))

        self._no_rb = tk.Radiobutton(
            option_btns,
            text="  No - Do not include as an outfit  ",
            variable=self._use_as_outfit_var,
            value=0,
            bg=CARD_BG,
            fg=TEXT_COLOR,
            selectcolor=BG_COLOR,
            activebackground=CARD_BG,
            activeforeground=TEXT_COLOR,
            font=BODY_FONT,
            indicatoron=True,
            padx=10,
            pady=6,
        )
        self._no_rb.pack(anchor="w")

        # Status label
        self._status_label = tk.Label(
            right_frame,
            text="",
            bg=BG_COLOR,
            fg=ACCENT_COLOR,
            font=SMALL_FONT,
            wraplength=260,
        )
        self._status_label.pack(pady=(0, 16))

        # Action buttons
        self._btn_frame = tk.Frame(right_frame, bg=BG_COLOR)
        self._btn_frame.pack(fill="x")

        # Note: This step is review-only. Regeneration is not available.
        # Use the Back button to return to Character step if you need changes.
        self._accept_btn = create_primary_button(
            self._btn_frame,
            "Accept & Continue",
            self._on_accept,
            width=16,
        )
        self._accept_btn.pack(fill="x", pady=(0, 8))

    def on_enter(self) -> None:
        """Generate base pose when step becomes active."""
        # Check if we already have a base pose
        if self.state.base_pose_path and self.state.base_pose_path.exists():
            # Already generated - just display it
            self._display_image(self.state.base_pose_path)
            self._status_label.configure(text="Review the image and select an option above.")
            return

        # Need to generate
        self._start_generation()

    def _start_generation(self, additional_instructions: str = "") -> None:
        """Start base pose generation in background thread."""
        if self._is_generating:
            return

        self._is_generating = True
        self._set_ui_generating(True)
        self._status_label.configure(text="Generating base character image...")

        # Run generation in background thread
        def generate():
            try:
                result_path = self._do_generation(additional_instructions)
                # Update UI on main thread
                self.wizard.root.after(0, lambda p=result_path: self._on_generation_complete(p))
            except Exception as e:
                error_msg = str(e)
                self.wizard.root.after(0, lambda msg=error_msg: self._on_generation_error(msg))

        thread = threading.Thread(target=generate, daemon=True)
        thread.start()

    def _do_generation(self, additional_instructions: str = "") -> Path:
        """Perform the actual generation (runs in background thread)."""
        from ...processing import generate_initial_pose_once
        from ..api_setup import ensure_api_key

        # Ensure we have an API key
        if not self.state.api_key:
            self.state.api_key = ensure_api_key()

        # Determine source image
        if self.state.cropped_image_path and self.state.cropped_image_path.exists():
            source_image = self.state.cropped_image_path
        else:
            source_image = self.state.image_path

        # Determine output path
        if not self.state.character_folder:
            # Create character folder if not exists
            from ...processing import get_unique_folder_name
            if not self.state.output_root:
                raise ValueError("Output folder not set. Please select an output folder before generating.")
            self.state.character_folder = self.state.output_root / get_unique_folder_name(
                self.state.output_root, self.state.display_name
            )

        self.state.character_folder.mkdir(parents=True, exist_ok=True)
        out_stem = self.state.character_folder / "a_base"

        # Generate
        result_path = generate_initial_pose_once(
            api_key=self.state.api_key,
            image_path=source_image,
            out_stem=out_stem,
            gender_style=self.state.gender_style,
            archetype_label=self.state.archetype_label,
            additional_instructions=additional_instructions,
        )

        return result_path

    def _on_generation_complete(self, result_path: Path) -> None:
        """Handle generation completion."""
        self._is_generating = False
        self._set_ui_generating(False)

        self.state.base_pose_path = result_path

        # Store original bytes for potential future use
        if not self.state.original_base_bytes:
            self.state.original_base_bytes = result_path.read_bytes()

        self._display_image(result_path)
        self._status_label.configure(text="Review the image and select an option above.")

    def _on_generation_error(self, error: str) -> None:
        """Handle generation error."""
        self._is_generating = False
        self._set_ui_generating(False)
        self._status_label.configure(text=f"Error: {error}", fg="#ff5555")
        messagebox.showerror("Generation Error", f"Failed to generate base image:\n\n{error}")

    def _display_image(self, image_path: Path) -> None:
        """Display the generated image in the preview."""
        try:
            img = Image.open(image_path).convert("RGBA")

            # Get display dimensions
            parent = self._preview_label.winfo_toplevel()
            max_h = int(parent.winfo_screenheight() * 0.50)
            max_w = int(parent.winfo_screenwidth() * 0.35)

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

    def _set_ui_generating(self, generating: bool) -> None:
        """Update UI state for generating/ready."""
        state = "disabled" if generating else "normal"
        if self._accept_btn:
            self._accept_btn.configure(state=state)

        if generating:
            self._preview_label.configure(text="Generating...", image="")
            self.show_loading("Generating base character image...")
        else:
            self.hide_loading()

    def _on_accept(self) -> None:
        """Handle accept button click."""
        if self._is_generating:
            return

        # Save settings
        self.state.use_base_as_outfit = bool(self._use_as_outfit_var.get())

        # Move to next step
        self.request_next()

    def validate(self) -> bool:
        """Validate before advancing."""
        if self._is_generating:
            messagebox.showwarning(
                "Generation in Progress",
                "Please wait for generation to complete."
            )
            return False

        if not self.state.base_pose_path or not self.state.base_pose_path.exists():
            messagebox.showerror(
                "No Base Image",
                "Base pose generation failed. Please try regenerating."
            )
            return False

        # Check that base outfit selection was made
        if self._use_as_outfit_var.get() == -1:
            messagebox.showwarning(
                "Selection Required",
                "Please select Yes or No for 'Include as Base Outfit' before continuing."
            )
            return False

        # Save settings
        self.state.use_base_as_outfit = bool(self._use_as_outfit_var.get())
        return True

    def should_skip(self) -> bool:
        """Never skip - this step is used for both image and prompt modes."""
        return False

    def is_dirty(self) -> bool:
        """Check if base pose affects downstream steps."""
        return True  # Base always affects outfits

    def get_dirty_steps(self) -> list:
        """Changing base invalidates all downstream generation."""
        return [7, 8, 9, 10]  # All outfit and expression steps


class PromptGenerationStep(WizardStep):
    """
    Step 7: Prompt-Generated Character Review.

    For prompt mode only - reviews the AI-generated character from text description.
    Similar to BaseGenerationStep but uses prompt-based generation.
    """

    STEP_ID = "prompt_generation"
    STEP_TITLE = "Character"
    STEP_HELP = """Prompt-Generated Character Review

The AI has created a character based on your description.

Review Options:
- Accept: Use this character design and continue
- Regenerate: Generate a new variation (you can modify the description)
- Reset: Revert to the first generated design

If the character doesn't match your vision, try adjusting your description and regenerating."""

    def __init__(self, wizard, state: WizardState):
        super().__init__(wizard, state)
        self._preview_label: Optional[tk.Label] = None
        self._instructions_text: Optional[tk.Text] = None
        self._status_label: Optional[tk.Label] = None
        self._tk_img: Optional[ImageTk.PhotoImage] = None
        self._is_generating: bool = False

    def build_ui(self, parent: tk.Frame) -> None:
        parent.configure(bg=BG_COLOR)

        # Title
        tk.Label(
            parent,
            text="Review Generated Character",
            bg=BG_COLOR,
            fg=TEXT_COLOR,
            font=PAGE_TITLE_FONT,
        ).pack(pady=(0, 8))

        # Instructions
        tk.Label(
            parent,
            text="The AI has generated a character based on your description.",
            bg=BG_COLOR,
            fg=TEXT_SECONDARY,
            font=SMALL_FONT,
        ).pack(pady=(0, 12))

        # Main content
        content = tk.Frame(parent, bg=BG_COLOR)
        content.pack(fill="both", expand=True)

        # Left: Preview
        left_frame = tk.Frame(content, bg=BG_COLOR)
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 16))

        preview_container = tk.Frame(left_frame, bg=CARD_BG, padx=4, pady=4)
        preview_container.pack(expand=True)

        self._preview_label = tk.Label(
            preview_container,
            text="Generating...",
            bg=CARD_BG,
            fg=TEXT_SECONDARY,
            font=BODY_FONT,
            width=40,
            height=20,
        )
        self._preview_label.pack()

        # Right: Controls
        right_frame = tk.Frame(content, bg=BG_COLOR, width=280)
        right_frame.pack(side="right", fill="y", padx=(16, 0))
        right_frame.pack_propagate(False)

        # Original concept display
        tk.Label(
            right_frame,
            text="Your description:",
            bg=BG_COLOR,
            fg=TEXT_COLOR,
            font=SMALL_FONT,
        ).pack(anchor="w", pady=(0, 4))

        concept_display = tk.Text(
            right_frame,
            height=4,
            width=32,
            wrap="word",
            bg="#1E1E1E",
            fg=TEXT_SECONDARY,
            font=SMALL_FONT,
            state="disabled",
        )
        concept_display.pack(fill="x", pady=(0, 16))
        self._concept_display = concept_display

        # Modification instructions
        tk.Label(
            right_frame,
            text="Modify description for regeneration:",
            bg=BG_COLOR,
            fg=TEXT_COLOR,
            font=SMALL_FONT,
        ).pack(anchor="w", pady=(0, 4))

        self._instructions_text = tk.Text(
            right_frame,
            height=4,
            width=32,
            wrap="word",
            bg="#1E1E1E",
            fg=TEXT_COLOR,
            insertbackground=TEXT_COLOR,
            font=SMALL_FONT,
        )
        self._instructions_text.pack(fill="x", pady=(0, 16))

        # Status
        self._status_label = tk.Label(
            right_frame,
            text="",
            bg=BG_COLOR,
            fg=ACCENT_COLOR,
            font=SMALL_FONT,
            wraplength=260,
        )
        self._status_label.pack(pady=(0, 16))

        # Buttons (Accept button removed - use wizard's Next button to proceed)
        btn_frame = tk.Frame(right_frame, bg=BG_COLOR)
        btn_frame.pack(fill="x")

        self._regen_btn = create_secondary_button(
            btn_frame, "Regenerate", self._on_regenerate, width=12
        )
        self._regen_btn.pack(fill="x", pady=(0, 8))

        self._reset_btn = create_secondary_button(
            btn_frame, "Reset to Original", self._on_reset, width=12
        )
        # Hidden by default

    def on_enter(self) -> None:
        """Generate character from prompt when step becomes active."""
        # Display the concept text
        self._concept_display.configure(state="normal")
        self._concept_display.delete("1.0", "end")
        self._concept_display.insert("1.0", self.state.concept_text)
        self._concept_display.configure(state="disabled")

        # Pre-fill modification text with original
        if not self._instructions_text.get("1.0", "end").strip():
            self._instructions_text.insert("1.0", self.state.concept_text)

        # Check if already generated (from a previous visit to this step)
        if self.state.base_pose_path and self.state.base_pose_path.exists():
            self._display_image(self.state.base_pose_path)
            self._update_button_states()
            return

        # Check if CharacterStep already generated an image (in the new flow)
        if self.state.cropped_image_path and self.state.cropped_image_path.exists():
            # Use the character image from CharacterStep, normalize it
            self._start_normalization()
            return

        # Generate from scratch
        self._start_generation()

    def _start_normalization(self) -> None:
        """Normalize the already-generated character image from CharacterStep."""
        if self._is_generating:
            return

        self._is_generating = True
        self._set_ui_generating(True)
        self._status_label.configure(text="Normalizing character image...")

        def normalize():
            try:
                result_path = self._do_normalization()
                self.wizard.root.after(0, lambda p=result_path: self._on_generation_complete(p))
            except Exception as e:
                error_msg = str(e)
                self.wizard.root.after(0, lambda msg=error_msg: self._on_generation_error(msg))

        thread = threading.Thread(target=normalize, daemon=True)
        thread.start()

    def _do_normalization(self) -> Path:
        """Normalize the character image using the base pose generation function."""
        from ...processing import generate_initial_pose_once
        from ..api_setup import ensure_api_key

        if not self.state.api_key:
            self.state.api_key = ensure_api_key()

        # Create output folder
        if not self.state.character_folder:
            from ...processing import get_unique_folder_name
            if not self.state.output_root:
                raise ValueError("Output folder not set. Please select an output folder before generating.")
            self.state.character_folder = self.state.output_root / get_unique_folder_name(
                self.state.output_root, self.state.display_name
            )

        self.state.character_folder.mkdir(parents=True, exist_ok=True)
        out_stem = self.state.character_folder / "a_base"

        # Use the image from CharacterStep
        result_path = generate_initial_pose_once(
            api_key=self.state.api_key,
            image_path=self.state.cropped_image_path,
            out_stem=out_stem,
            gender_style=self.state.gender_style,
            archetype_label=self.state.archetype_label,
        )

        return result_path

    def _start_generation(self, modified_concept: str = "") -> None:
        """Start character generation from prompt."""
        if self._is_generating:
            return

        self._is_generating = True
        self._set_ui_generating(True)
        self._status_label.configure(text="Generating character from description...")

        concept = modified_concept or self.state.concept_text

        def generate():
            try:
                result_path = self._do_generation(concept)
                self.wizard.root.after(0, lambda p=result_path: self._on_generation_complete(p))
            except Exception as e:
                error_msg = str(e)
                self.wizard.root.after(0, lambda msg=error_msg: self._on_generation_error(msg))

        thread = threading.Thread(target=generate, daemon=True)
        thread.start()

    def _do_generation(self, concept: str) -> Path:
        """Perform prompt-based generation."""
        from ...processing import generate_initial_character_from_prompt
        from ..api_setup import ensure_api_key

        if not self.state.api_key:
            self.state.api_key = ensure_api_key()

        # Create output folder
        if not self.state.character_folder:
            from ...processing import get_unique_folder_name
            if not self.state.output_root:
                raise ValueError("Output folder not set. Please select an output folder before generating.")
            self.state.character_folder = self.state.output_root / get_unique_folder_name(
                self.state.output_root, self.state.display_name
            )

        self.state.character_folder.mkdir(parents=True, exist_ok=True)
        out_stem = self.state.character_folder / "a_base"

        result_path = generate_initial_character_from_prompt(
            api_key=self.state.api_key,
            concept=concept,
            out_stem=out_stem,
            gender_style=self.state.gender_style,
            archetype_label=self.state.archetype_label,
        )

        return result_path

    def _on_generation_complete(self, result_path: Path) -> None:
        """Handle generation completion."""
        self._is_generating = False
        self._set_ui_generating(False)

        self.state.base_pose_path = result_path

        if not self.state.original_base_bytes:
            self.state.original_base_bytes = result_path.read_bytes()
            self.state.base_has_been_regenerated = False
        else:
            self.state.base_has_been_regenerated = True

        self._display_image(result_path)
        self._update_button_states()
        self._status_label.configure(text="Character generated. Review and accept or regenerate.")

    def _on_generation_error(self, error: str) -> None:
        """Handle generation error."""
        self._is_generating = False
        self._set_ui_generating(False)
        self._status_label.configure(text=f"Error: {error}", fg="#ff5555")
        messagebox.showerror("Generation Error", f"Failed to generate character:\n\n{error}")

    def _display_image(self, image_path: Path) -> None:
        """Display image in preview."""
        try:
            img = Image.open(image_path).convert("RGBA")
            parent = self._preview_label.winfo_toplevel()
            max_h = int(parent.winfo_screenheight() * 0.50)
            max_w = int(parent.winfo_screenwidth() * 0.35)
            img.thumbnail((max_w, max_h), Image.LANCZOS)

            self._tk_img = ImageTk.PhotoImage(img)
            self._preview_label.configure(
                image=self._tk_img,
                text="",
                width=img.width,
                height=img.height,
            )
        except Exception as e:
            self._preview_label.configure(text=f"Error: {e}", fg="#ff5555")

    def _set_ui_generating(self, generating: bool) -> None:
        """Update UI for generating state."""
        state = "disabled" if generating else "normal"
        self._regen_btn.configure(state=state)
        if self._reset_btn.winfo_ismapped():
            self._reset_btn.configure(state=state)

        if generating:
            self._preview_label.configure(text="Generating...", image="")
            self.show_loading("Generating character from description...")
        else:
            self.hide_loading()

    def _update_button_states(self) -> None:
        """Update reset button visibility."""
        if self.state.base_has_been_regenerated:
            self._reset_btn.pack(fill="x", pady=(0, 8))
        else:
            self._reset_btn.pack_forget()

    def _on_regenerate(self) -> None:
        """Regenerate with modified concept."""
        if self._is_generating:
            return
        modified = self._instructions_text.get("1.0", "end").strip()
        self._start_generation(modified)

    def _on_reset(self) -> None:
        """Reset to original generation."""
        if self._is_generating:
            return
        if self.state.original_base_bytes and self.state.base_pose_path:
            self.state.base_pose_path.write_bytes(self.state.original_base_bytes)
            self.state.base_has_been_regenerated = False
            self._display_image(self.state.base_pose_path)
            self._update_button_states()
            self._status_label.configure(text="Reset to original character.")

    def validate(self) -> bool:
        if self._is_generating:
            messagebox.showwarning("Generation in Progress", "Please wait for generation to complete.")
            return False
        if not self.state.base_pose_path or not self.state.base_pose_path.exists():
            messagebox.showerror("No Character", "Character generation failed. Please try again.")
            return False
        # Always use base as outfit in prompt mode (previously done in Accept button)
        self.state.use_base_as_outfit = True
        return True

    def should_skip(self) -> bool:
        """Only show for prompt mode."""
        return self.state.source_mode != "prompt"

    def is_dirty(self) -> bool:
        return True

    def get_dirty_steps(self) -> list:
        return [8, 9, 10]
