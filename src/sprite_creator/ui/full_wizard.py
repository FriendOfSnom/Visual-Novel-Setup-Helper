"""
Full Wizard Controller for AI Sprite Creator.

Provides a unified wizard interface that handles the entire sprite creation
process from source selection to final output. All screens are wizard steps
with back/forward navigation.

Usage:
    wizard = FullWizard(output_root=Path("/path/to/output"), api_key="...")
    result = wizard.run()
    if result:
        print(f"Character created at: {result.character_folder}")
"""

import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from typing import Dict, List, Optional, Type

from ..config import (
    BG_COLOR,
    BG_SECONDARY,
    CARD_BG,
    TEXT_COLOR,
    TEXT_SECONDARY,
    ACCENT_COLOR,
    TITLE_FONT,
    PAGE_TITLE_FONT,
    SECTION_FONT,
    BODY_FONT,
    SMALL_FONT,
    BUTTON_FONT,
)
from .tk_common import (
    apply_dark_theme,
    apply_window_size,
    create_primary_button,
    create_secondary_button,
    create_help_button,
    show_help_modal,
)
from .screens.base import WizardStep, WizardState


class FullWizard:
    """
    Main wizard controller that orchestrates all steps of sprite creation.

    The wizard maintains a list of steps and handles navigation between them.
    Each step is a WizardStep subclass that handles one phase of the process.
    """

    def __init__(
        self,
        output_root: Optional[Path] = None,
        api_key: Optional[str] = None,
    ):
        """
        Initialize the wizard.

        Args:
            output_root: Root folder for character output. If None, will be
                prompted during wizard.
            api_key: Gemini API key. If None, will be obtained via ensure_api_key.
        """
        self.root = tk.Tk()
        self.root.title("AI Sprite Creator")
        self.root.protocol("WM_DELETE_WINDOW", self._on_cancel)

        apply_dark_theme(self.root)
        apply_window_size(self.root, "fullscreen")

        # State
        self._state = WizardState()
        self._state.output_root = output_root
        self._state.api_key = api_key

        # Steps
        self._steps: List[WizardStep] = []
        self._step_classes: List[Type[WizardStep]] = []
        self._current_step_index: int = 0

        # UI references
        self._step_labels: List[tk.Label] = []
        self._content_frame: Optional[tk.Frame] = None
        self._back_btn: Optional[tk.Button] = None
        self._next_btn: Optional[tk.Button] = None
        self._help_btn: Optional[tk.Button] = None
        self._loading_frame: Optional[tk.Frame] = None
        self._loading_label: Optional[tk.Label] = None

        # Result tracking
        self._cancelled = False
        self._completed = False

        self._build_ui()

    @property
    def state(self) -> WizardState:
        """Get the wizard state."""
        return self._state

    @property
    def current_step(self) -> Optional[WizardStep]:
        """Get the current active step."""
        if 0 <= self._current_step_index < len(self._steps):
            return self._steps[self._current_step_index]
        return None

    def register_step(self, step_class: Type[WizardStep]) -> None:
        """
        Register a step class to be instantiated when wizard builds.

        Steps are shown in the order they are registered.

        Args:
            step_class: WizardStep subclass to register.
        """
        self._step_classes.append(step_class)

    def _build_ui(self) -> None:
        """Build the main wizard UI structure."""
        self._main_frame = tk.Frame(self.root, bg=BG_COLOR)
        self._main_frame.pack(fill="both", expand=True)

        # Header with step indicator
        self._build_header()

        # Content area (step frames go here)
        self._content_frame = tk.Frame(self._main_frame, bg=BG_COLOR, padx=30, pady=20)
        self._content_frame.pack(fill="both", expand=True)

        # Loading overlay (hidden by default)
        self._build_loading_overlay()

        # Footer with navigation buttons
        self._build_footer()

    def _build_header(self) -> None:
        """Build the header with step indicator."""
        header = tk.Frame(self._main_frame, bg=BG_SECONDARY, padx=30, pady=10)
        header.pack(fill="x")

        # Title
        tk.Label(
            header,
            text="AI Sprite Creator",
            bg=BG_SECONDARY,
            fg=TEXT_COLOR,
            font=TITLE_FONT,
        ).pack(side="left")

        # Step indicator (built when steps are registered)
        self._indicator_frame = tk.Frame(header, bg=BG_SECONDARY)
        self._indicator_frame.pack(side="right")

    def _build_step_indicator(self) -> None:
        """Build the step indicator based on registered steps."""
        # Clear existing
        for widget in self._indicator_frame.winfo_children():
            widget.destroy()
        self._step_labels.clear()

        for i, step in enumerate(self._steps):
            # Step label
            step_frame = tk.Frame(self._indicator_frame, bg=BG_SECONDARY)
            step_frame.pack(side="left")

            label = tk.Label(
                step_frame,
                text=f"({i+1}) {step.STEP_TITLE}",
                bg=BG_SECONDARY,
                fg=TEXT_SECONDARY,
                font=SMALL_FONT,
            )
            label.pack()
            self._step_labels.append(label)

            # Connector (except after last)
            if i < len(self._steps) - 1:
                connector = tk.Label(
                    self._indicator_frame,
                    text="  ─  ",
                    bg=BG_SECONDARY,
                    fg=TEXT_SECONDARY,
                    font=SMALL_FONT,
                )
                connector.pack(side="left")

    def _build_loading_overlay(self) -> None:
        """Build the loading overlay (hidden by default)."""
        self._loading_frame = tk.Frame(self._main_frame, bg=BG_COLOR)

        # Center the loading indicator
        inner = tk.Frame(self._loading_frame, bg=CARD_BG, padx=40, pady=30)
        inner.place(relx=0.5, rely=0.5, anchor="center")

        self._loading_label = tk.Label(
            inner,
            text="Loading...",
            bg=CARD_BG,
            fg=TEXT_COLOR,
            font=SECTION_FONT,
        )
        self._loading_label.pack()

        # Progress indicator (simple dots animation could be added)
        tk.Label(
            inner,
            text="Please wait while the AI generates content.",
            bg=CARD_BG,
            fg=TEXT_SECONDARY,
            font=SMALL_FONT,
        ).pack(pady=(10, 0))

    def _build_footer(self) -> None:
        """Build the footer with navigation buttons."""
        footer = tk.Frame(self._main_frame, bg=BG_COLOR, padx=30, pady=12)
        footer.pack(fill="x", side="bottom")

        # Use grid layout for left-center-right positioning
        footer.columnconfigure(0, weight=1)  # Left section
        footer.columnconfigure(1, weight=1)  # Center section
        footer.columnconfigure(2, weight=1)  # Right section

        # Left side: Cancel button only
        left_frame = tk.Frame(footer, bg=BG_COLOR)
        left_frame.grid(row=0, column=0, sticky="w")

        self._cancel_btn = create_secondary_button(
            left_frame, "Cancel", self._on_cancel, width=10
        )
        self._cancel_btn.pack(side="left")

        # Center: Help button
        center_frame = tk.Frame(footer, bg=BG_COLOR)
        center_frame.grid(row=0, column=1)

        self._help_btn = create_help_button(center_frame, "?", "")
        self._help_btn.pack()

        # Right side: Navigation buttons - Next rightmost, Back to its left
        nav_frame = tk.Frame(footer, bg=BG_COLOR)
        nav_frame.grid(row=0, column=2, sticky="e")

        # Pack Next first with side="right" so it appears rightmost
        self._next_btn = create_primary_button(
            nav_frame, "Next", self.go_next, width=12, large=True
        )
        self._next_btn.pack(side="right")

        # Pack Back with side="right" so it appears left of Next
        self._back_btn = create_secondary_button(
            nav_frame, "Back", self.go_back, width=10
        )
        self._back_btn.pack(side="right", padx=(0, 12))

    def _update_step_indicator(self) -> None:
        """Update step indicator to highlight current step."""
        for i, label in enumerate(self._step_labels):
            if i == self._current_step_index:
                label.configure(
                    fg=ACCENT_COLOR,
                    font=(SMALL_FONT[0], SMALL_FONT[1], "bold")
                )
            elif i < self._current_step_index:
                label.configure(fg=TEXT_COLOR, font=SMALL_FONT)
            else:
                label.configure(fg=TEXT_SECONDARY, font=SMALL_FONT)

    def _update_help_button(self) -> None:
        """Update help button for current step."""
        step = self.current_step
        if not step:
            return

        help_text = step.STEP_HELP

        # Recreate help button with new text
        parent = self._help_btn.master
        self._help_btn.destroy()
        self._help_btn = create_help_button(
            parent,
            f"Help: {step.STEP_TITLE}",
            help_text
        )
        self._help_btn.pack(side="left")

    def _update_nav_buttons(self) -> None:
        """Update navigation button states and text."""
        # Back button: hidden on first step
        if self._current_step_index == 0:
            self._back_btn.pack_forget()
        else:
            self._back_btn.pack(side="left", padx=(0, 10))

        # Next button text
        if self._current_step_index == len(self._steps) - 1:
            self._next_btn.configure(text="Finish")
        else:
            self._next_btn.configure(text="Next")

    def _show_step(self, index: int) -> None:
        """
        Show the step at the given index.

        Handles hiding current step, showing new step, and updating UI.

        Args:
            index: Index of step to show (0-based).
        """
        if index < 0 or index >= len(self._steps):
            return

        # Leave current step
        if self.current_step:
            self.current_step.on_leave()
            if self.current_step.frame:
                self.current_step.frame.pack_forget()

        # Update index
        self._current_step_index = index

        # Show new step
        new_step = self._steps[index]

        # Skip if needed
        while new_step.should_skip():
            if self._current_step_index < len(self._steps) - 1:
                self._current_step_index += 1
                new_step = self._steps[self._current_step_index]
            else:
                break

        if new_step.frame:
            new_step.frame.pack(fill="both", expand=True)
        new_step.on_enter()

        # Update UI
        self._update_step_indicator()
        self._update_help_button()
        self._update_nav_buttons()

    def go_next(self) -> None:
        """Navigate to the next step if validation passes."""
        step = self.current_step
        if not step:
            return

        # Validate current step
        if not step.validate():
            return

        # Note: "Changes Detected" popup removed - warnings are now shown
        # only when user clicks a Regenerate button in the respective steps

        # Move to next step
        if self._current_step_index < len(self._steps) - 1:
            self._show_step(self._current_step_index + 1)
        else:
            # Last step - complete wizard
            self._completed = True
            self.root.quit()

    def go_back(self) -> None:
        """Navigate to the previous step."""
        if self._current_step_index > 0:
            # Leave current step
            if self.current_step:
                self.current_step.on_leave()

            # Find previous non-skipped step
            target = self._current_step_index - 1
            while target > 0 and self._steps[target].should_skip():
                target -= 1

            self._show_step(target)

    def go_to_step(self, index: int) -> None:
        """
        Navigate directly to a specific step.

        Args:
            index: Target step index (0-based).
        """
        if 0 <= index < len(self._steps):
            self._show_step(index)

    def show_loading(self, message: str = "Loading...") -> None:
        """
        Show loading overlay with message.

        Args:
            message: Text to display during loading.
        """
        if self._loading_label:
            self._loading_label.configure(text=message)
        if self._loading_frame:
            self._loading_frame.place(relx=0, rely=0, relwidth=1, relheight=1)
            self._loading_frame.lift()
        self.root.update()

    def hide_loading(self) -> None:
        """Hide the loading overlay."""
        if self._loading_frame:
            self._loading_frame.place_forget()
        self.root.update()

    def _on_cancel(self) -> None:
        """Handle cancel button or window close."""
        result = messagebox.askyesno(
            "Cancel",
            "Are you sure you want to cancel?\n\n"
            "Any unsaved progress will be lost.",
            icon="warning"
        )
        if result:
            self._cancelled = True
            self.root.quit()

    def _initialize_steps(self) -> None:
        """Instantiate all registered step classes."""
        for step_class in self._step_classes:
            step = step_class(self, self._state)
            step.build(self._content_frame)
            self._steps.append(step)

        # Build step indicator now that we know the steps
        self._build_step_indicator()

    def run(self) -> Optional[WizardState]:
        """
        Run the wizard and return the final state.

        Returns:
            WizardState if completed successfully, None if cancelled.
        """
        # Initialize steps
        self._initialize_steps()

        if not self._steps:
            messagebox.showerror("Error", "No wizard steps registered.")
            self.root.destroy()
            return None

        # Show first step
        self._show_step(0)

        # Run main loop
        self.root.mainloop()

        # Cleanup
        if self._cancelled or not self._completed:
            self.root.destroy()
            return None

        result = self._state
        self.root.destroy()
        return result


def run_full_wizard(
    output_root: Optional[Path] = None,
    api_key: Optional[str] = None,
) -> Optional[WizardState]:
    """
    Run the full sprite creation wizard.

    Convenience function that creates a FullWizard with all steps registered.

    Args:
        output_root: Root folder for character output.
        api_key: Gemini API key.

    Returns:
        WizardState if completed successfully, None if cancelled.
    """
    # Import step classes here to avoid circular imports
    from .screens.setup_steps import (
        SourceStep, CharacterStep, OptionsStep
    )
    from .screens.generation_steps import ReviewStep
    from .screens.outfit_steps import OutfitReviewStep
    from .screens.expression_steps import ExpressionReviewStep
    from .screens.finalization_steps import EyeLineStep, ScaleStep, SummaryStep

    wizard = FullWizard(output_root=output_root, api_key=api_key)

    # Register setup steps (1-3) - crop now handled in CharacterStep
    wizard.register_step(SourceStep)
    wizard.register_step(CharacterStep)
    wizard.register_step(OptionsStep)

    # Register generation step (unified for both image and prompt modes)
    wizard.register_step(ReviewStep)

    # Register outfit review (8)
    wizard.register_step(OutfitReviewStep)

    # Register expression review (10)
    wizard.register_step(ExpressionReviewStep)

    # Register finalization steps (11-13)
    wizard.register_step(EyeLineStep)
    wizard.register_step(ScaleStep)
    wizard.register_step(SummaryStep)

    return wizard.run()


# For testing
if __name__ == "__main__":
    from .screens.setup_steps import (
        SourceStep, CharacterStep, OptionsStep
    )
    from .screens.generation_steps import ReviewStep
    from .screens.outfit_steps import OutfitReviewStep
    from .screens.expression_steps import ExpressionReviewStep
    from .screens.finalization_steps import EyeLineStep, ScaleStep, SummaryStep

    # Create wizard with all implemented steps
    wizard = FullWizard()

    # Setup steps (1-3) - crop now handled in CharacterStep
    wizard.register_step(SourceStep)
    wizard.register_step(CharacterStep)
    wizard.register_step(OptionsStep)

    # Generation step (unified for both modes)
    wizard.register_step(ReviewStep)

    # Outfit review (8)
    wizard.register_step(OutfitReviewStep)

    # Expression review (10)
    wizard.register_step(ExpressionReviewStep)

    # Finalization steps (11-13)
    wizard.register_step(EyeLineStep)
    wizard.register_step(ScaleStep)
    wizard.register_step(SummaryStep)

    result = wizard.run()
    if result:
        print("Wizard completed!")
        print(f"  Source mode: {result.source_mode}")
        print(f"  Name: {result.display_name}")
        print(f"  Voice: {result.voice}")
        print(f"  Archetype: {result.archetype_label}")
        print(f"  Outfits: {result.selected_outfits}")
        print(f"  Expressions: {len(result.expressions_sequence)}")
        print(f"  Eye line: {result.eye_line_ratio}")
        print(f"  Name color: {result.name_color}")
        print(f"  Scale: {result.scale_factor}")
        if result.character_folder:
            print(f"  Output: {result.character_folder}")
    else:
        print("Wizard cancelled.")
