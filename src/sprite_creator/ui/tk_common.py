"""
Common Tkinter utilities and layout helpers.

Shared functions for window sizing, positioning, styled components,
and UI calculations for the dark theme design.
"""

import tkinter as tk
from tkinter import ttk
from typing import Tuple, Callable, Optional, List

from ..config import (
    # Colors
    BG_COLOR,
    BG_SECONDARY,
    CARD_BG,
    CARD_BG_HOVER,
    CARD_BG_SELECTED,
    TEXT_COLOR,
    TEXT_SECONDARY,
    TEXT_DISABLED,
    ACCENT_COLOR,
    ACCENT_HOVER,
    SECONDARY_COLOR,
    SECONDARY_HOVER,
    DANGER_COLOR,
    DANGER_HOVER,
    BORDER_COLOR,
    LINE_COLOR,
    # Fonts
    FONT_FAMILY,
    TITLE_FONT,
    PAGE_TITLE_FONT,
    SECTION_FONT,
    BODY_FONT,
    BODY_FONT_BOLD,
    SMALL_FONT,
    SMALL_FONT_BOLD,
    BUTTON_FONT,
    BUTTON_FONT_LARGE,
    INSTRUCTION_FONT,
    # Layout
    WINDOW_MARGIN,
    WRAP_PADDING,
    CARD_PADDING,
)


# ═══════════════════════════════════════════════════════════════════════════════
# WINDOW SIZE CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

WINDOW_SIZES = {
    "compact": (0.35, 0.45),     # Simple dialogs (disclaimer, API setup)
    "standard": (0.50, 0.60),    # Setup dialogs (launcher, wizard)
    "large": (0.70, 0.80),       # Review dialogs
    "fullscreen": (0.95, 0.90), # Image editing
}


def get_window_size(size_class: str, screen_w: int, screen_h: int) -> Tuple[int, int]:
    """
    Get window dimensions for a size class.

    Args:
        size_class: One of "compact", "standard", "large", "fullscreen"
        screen_w: Screen width in pixels
        screen_h: Screen height in pixels

    Returns:
        (width, height) in pixels
    """
    w_ratio, h_ratio = WINDOW_SIZES.get(size_class, WINDOW_SIZES["standard"])
    return int(screen_w * w_ratio), int(screen_h * h_ratio)


def apply_window_size(root: tk.Tk, size_class: str) -> None:
    """
    Apply a standard size class to a window and center it.

    Args:
        root: Tkinter window
        size_class: One of "compact", "standard", "large", "fullscreen"
    """
    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()

    w, h = get_window_size(size_class, sw, sh)
    x = (sw - w) // 2
    y = (sh - h) // 2

    root.geometry(f"{w}x{h}+{x}+{y}")


# ═══════════════════════════════════════════════════════════════════════════════
# DARK THEME APPLICATION
# ═══════════════════════════════════════════════════════════════════════════════

def apply_dark_theme(root: tk.Tk) -> None:
    """
    Apply dark theme styling to a Tkinter window.

    Sets background color and configures ttk styles for dark theme.

    Args:
        root: Tkinter root window
    """
    root.configure(bg=BG_COLOR)

    # Configure ttk styles for dark theme
    style = ttk.Style()
    style.theme_use('clam')  # Use clam as base for better customization

    # Frame styles
    style.configure("Dark.TFrame", background=BG_COLOR)
    style.configure("Card.TFrame", background=CARD_BG)
    style.configure("Header.TFrame", background=BG_SECONDARY)

    # Label styles
    style.configure("Dark.TLabel",
                    background=BG_COLOR,
                    foreground=TEXT_COLOR,
                    font=BODY_FONT)
    style.configure("Title.TLabel",
                    background=BG_COLOR,
                    foreground=TEXT_COLOR,
                    font=TITLE_FONT)
    style.configure("Section.TLabel",
                    background=BG_COLOR,
                    foreground=TEXT_COLOR,
                    font=SECTION_FONT)
    style.configure("Secondary.TLabel",
                    background=BG_COLOR,
                    foreground=TEXT_SECONDARY,
                    font=SMALL_FONT)
    style.configure("Card.TLabel",
                    background=CARD_BG,
                    foreground=TEXT_COLOR,
                    font=BODY_FONT)

    # Checkbutton style
    style.configure("Dark.TCheckbutton",
                    background=BG_COLOR,
                    foreground=TEXT_COLOR,
                    font=BODY_FONT)
    style.map("Dark.TCheckbutton",
              background=[("active", BG_COLOR)],
              foreground=[("active", TEXT_COLOR)])


# ═══════════════════════════════════════════════════════════════════════════════
# STYLED BUTTON FACTORIES
# ═══════════════════════════════════════════════════════════════════════════════

def create_primary_button(
    parent: tk.Widget,
    text: str,
    command: Callable,
    width: int = 15,
    large: bool = False,
) -> tk.Button:
    """
    Create a styled primary action button (blue accent).

    Args:
        parent: Parent widget
        text: Button text
        command: Click handler
        width: Button width in characters
        large: Use larger font for prominent buttons

    Returns:
        Configured tk.Button
    """
    btn = tk.Button(
        parent,
        text=text,
        command=command,
        width=width,
        bg=ACCENT_COLOR,
        fg=TEXT_COLOR,
        activebackground=ACCENT_HOVER,
        activeforeground=TEXT_COLOR,
        font=BUTTON_FONT_LARGE if large else BUTTON_FONT,
        relief="flat",
        cursor="hand2",
        bd=0,
        padx=12,
        pady=5 if large else 3,
    )

    # Hover effects
    btn.bind("<Enter>", lambda e: btn.configure(bg=ACCENT_HOVER))
    btn.bind("<Leave>", lambda e: btn.configure(bg=ACCENT_COLOR))

    return btn


def create_secondary_button(
    parent: tk.Widget,
    text: str,
    command: Callable,
    width: int = 15,
) -> tk.Button:
    """
    Create a styled secondary button (gray, muted).

    Args:
        parent: Parent widget
        text: Button text
        command: Click handler
        width: Button width in characters

    Returns:
        Configured tk.Button
    """
    btn = tk.Button(
        parent,
        text=text,
        command=command,
        width=width,
        bg=SECONDARY_COLOR,
        fg=TEXT_COLOR,
        activebackground=SECONDARY_HOVER,
        activeforeground=TEXT_COLOR,
        font=BUTTON_FONT,
        relief="flat",
        cursor="hand2",
        bd=0,
        padx=12,
        pady=3,
    )

    btn.bind("<Enter>", lambda e: btn.configure(bg=SECONDARY_HOVER))
    btn.bind("<Leave>", lambda e: btn.configure(bg=SECONDARY_COLOR))

    return btn


def create_danger_button(
    parent: tk.Widget,
    text: str,
    command: Callable,
    width: int = 15,
) -> tk.Button:
    """
    Create a styled danger/cancel button (red).

    Args:
        parent: Parent widget
        text: Button text
        command: Click handler
        width: Button width in characters

    Returns:
        Configured tk.Button
    """
    btn = tk.Button(
        parent,
        text=text,
        command=command,
        width=width,
        bg=DANGER_COLOR,
        fg=TEXT_COLOR,
        activebackground=DANGER_HOVER,
        activeforeground=TEXT_COLOR,
        font=BUTTON_FONT,
        relief="flat",
        cursor="hand2",
        bd=0,
        padx=12,
        pady=3,
    )

    btn.bind("<Enter>", lambda e: btn.configure(bg=DANGER_HOVER))
    btn.bind("<Leave>", lambda e: btn.configure(bg=DANGER_COLOR))

    return btn


# ═══════════════════════════════════════════════════════════════════════════════
# OPTION CARDS
# ═══════════════════════════════════════════════════════════════════════════════

class OptionCard(tk.Frame):
    """
    A clickable card for selection interfaces.

    Used for source mode selection, outfit/expression toggles, etc.
    """

    def __init__(
        self,
        parent: tk.Widget,
        title: str,
        description: str = "",
        selected: bool = False,
        on_click: Optional[Callable] = None,
        width: int = 200,
        height: int = 100,
    ):
        super().__init__(parent, bg=CARD_BG, width=width, height=height)
        self.pack_propagate(False)

        self._selected = selected
        self._on_click = on_click
        self._title = title

        # Content
        self._title_label = tk.Label(
            self,
            text=title,
            bg=CARD_BG,
            fg=TEXT_COLOR,
            font=BODY_FONT_BOLD,
        )
        self._title_label.pack(pady=(CARD_PADDING, 4))

        if description:
            self._desc_label = tk.Label(
                self,
                text=description,
                bg=CARD_BG,
                fg=TEXT_SECONDARY,
                font=SMALL_FONT,
                wraplength=width - 20,
            )
            self._desc_label.pack(pady=(0, CARD_PADDING))
        else:
            self._desc_label = None

        # Click handling
        self.bind("<Button-1>", self._handle_click)
        self._title_label.bind("<Button-1>", self._handle_click)
        if self._desc_label:
            self._desc_label.bind("<Button-1>", self._handle_click)

        # Hover effects
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self._title_label.bind("<Enter>", self._on_enter)
        self._title_label.bind("<Leave>", self._on_leave)
        if self._desc_label:
            self._desc_label.bind("<Enter>", self._on_enter)
            self._desc_label.bind("<Leave>", self._on_leave)

        self.configure(cursor="hand2")
        self._update_appearance()

    def _handle_click(self, event=None):
        if self._on_click:
            self._on_click(self)

    def _on_enter(self, event=None):
        if not self._selected:
            self._set_bg(CARD_BG_HOVER)

    def _on_leave(self, event=None):
        self._update_appearance()

    def _set_bg(self, color: str):
        self.configure(bg=color)
        self._title_label.configure(bg=color)
        if self._desc_label:
            self._desc_label.configure(bg=color)

    def _update_appearance(self):
        if self._selected:
            self._set_bg(CARD_BG_SELECTED)
        else:
            self._set_bg(CARD_BG)

    @property
    def selected(self) -> bool:
        return self._selected

    @selected.setter
    def selected(self, value: bool):
        self._selected = value
        self._update_appearance()

    @property
    def title(self) -> str:
        return self._title


def create_option_card(
    parent: tk.Widget,
    title: str,
    description: str = "",
    selected: bool = False,
    on_click: Optional[Callable] = None,
    width: int = 200,
    height: int = 100,
) -> OptionCard:
    """
    Factory function to create an OptionCard.

    Args:
        parent: Parent widget
        title: Card title text
        description: Optional description text
        selected: Initial selection state
        on_click: Callback when card is clicked (receives card as argument)
        width: Card width in pixels
        height: Card height in pixels

    Returns:
        Configured OptionCard widget
    """
    return OptionCard(
        parent, title, description, selected, on_click, width, height
    )


# ═══════════════════════════════════════════════════════════════════════════════
# HELP SYSTEM
# ═══════════════════════════════════════════════════════════════════════════════

def create_help_button(
    parent: tk.Widget,
    help_title: str,
    help_text: str,
) -> tk.Button:
    """
    Create a small "?" help button that shows a modal with instructions.

    Args:
        parent: Parent widget
        help_title: Title for the help modal
        help_text: Help content to display

    Returns:
        Configured help button
    """
    def show_help():
        show_help_modal(parent, help_title, help_text)

    btn = tk.Button(
        parent,
        text="?",
        command=show_help,
        width=2,
        height=1,
        bg=SECONDARY_COLOR,
        fg=TEXT_COLOR,
        activebackground=SECONDARY_HOVER,
        activeforeground=TEXT_COLOR,
        font=(FONT_FAMILY, 10, "bold"),
        relief="flat",
        cursor="hand2",
        bd=0,
    )

    btn.bind("<Enter>", lambda e: btn.configure(bg=SECONDARY_HOVER))
    btn.bind("<Leave>", lambda e: btn.configure(bg=SECONDARY_COLOR))

    return btn


def show_help_modal(parent: tk.Widget, title: str, help_text: str) -> None:
    """
    Show a modal overlay with help content.

    Args:
        parent: Parent widget (used to find root window)
        title: Modal title
        help_text: Help content to display
    """
    # Find root window
    root = parent.winfo_toplevel()

    # Create overlay
    overlay = tk.Toplevel(root)
    overlay.title(title)
    overlay.configure(bg=BG_COLOR)
    overlay.transient(root)
    overlay.grab_set()

    # Size and center - larger to accommodate more help text
    modal_w, modal_h = 500, 450
    root_x = root.winfo_x()
    root_y = root.winfo_y()
    root_w = root.winfo_width()
    root_h = root.winfo_height()
    x = root_x + (root_w - modal_w) // 2
    y = root_y + (root_h - modal_h) // 2
    overlay.geometry(f"{modal_w}x{modal_h}+{x}+{y}")
    overlay.resizable(False, False)

    # Content frame
    content = tk.Frame(overlay, bg=BG_COLOR, padx=24, pady=20)
    content.pack(fill="both", expand=True)

    # Title
    title_label = tk.Label(
        content,
        text=title,
        bg=BG_COLOR,
        fg=TEXT_COLOR,
        font=SECTION_FONT,
    )
    title_label.pack(anchor="w", pady=(0, 16))

    # Help text (scrollable)
    text_frame = tk.Frame(content, bg=BG_COLOR)
    text_frame.pack(fill="both", expand=True, pady=(0, 16))

    # Add scrollbar
    scrollbar = ttk.Scrollbar(text_frame, orient="vertical")
    scrollbar.pack(side="right", fill="y")

    text_widget = tk.Text(
        text_frame,
        wrap="word",
        bg=BG_COLOR,
        fg=TEXT_SECONDARY,
        font=BODY_FONT,
        relief="flat",
        highlightthickness=0,
        padx=0,
        pady=0,
        yscrollcommand=scrollbar.set,
    )
    text_widget.insert("1.0", help_text)
    text_widget.configure(state="disabled")
    text_widget.pack(side="left", fill="both", expand=True)
    scrollbar.configure(command=text_widget.yview)

    # Capture mouse wheel events on the modal so they don't propagate to
    # underlying canvases (fixes scroll bug on outfit/expression steps)
    def on_mousewheel(event):
        # Scroll the text widget
        text_widget.yview_scroll(int(-1 * (event.delta / 120)), "units")
        return "break"  # Prevent propagation to other handlers

    def on_mousewheel_linux_up(event):
        text_widget.yview_scroll(-1, "units")
        return "break"

    def on_mousewheel_linux_down(event):
        text_widget.yview_scroll(1, "units")
        return "break"

    # Bind to the overlay window itself (catches all wheel events in modal)
    overlay.bind("<MouseWheel>", on_mousewheel)
    overlay.bind("<Button-4>", on_mousewheel_linux_up)
    overlay.bind("<Button-5>", on_mousewheel_linux_down)

    # Also bind to child widgets to ensure capture
    text_widget.bind("<MouseWheel>", on_mousewheel)
    text_widget.bind("<Button-4>", on_mousewheel_linux_up)
    text_widget.bind("<Button-5>", on_mousewheel_linux_down)
    content.bind("<MouseWheel>", on_mousewheel)
    content.bind("<Button-4>", on_mousewheel_linux_up)
    content.bind("<Button-5>", on_mousewheel_linux_down)

    # Close button
    close_btn = create_primary_button(
        content,
        "Got it",
        overlay.destroy,
        width=12,
    )
    close_btn.pack(pady=(0, 8))

    # Escape to close
    overlay.bind("<Escape>", lambda e: overlay.destroy())

    # Focus the overlay to ensure it receives events
    overlay.focus_set()


# ═══════════════════════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS (preserved from original)
# ═══════════════════════════════════════════════════════════════════════════════

def compute_display_size(
    screen_w: int,
    screen_h: int,
    img_w: int,
    img_h: int,
    *,
    max_w_ratio: float = 0.90,
    max_h_ratio: float = 0.55,
) -> Tuple[int, int]:
    """
    Calculate display size for an image that fits within given screen ratios.

    Maintains aspect ratio while ensuring the image fits on screen with
    room for text and controls.

    Args:
        screen_w: Screen width in pixels.
        screen_h: Screen height in pixels.
        img_w: Image width in pixels.
        img_h: Image height in pixels.
        max_w_ratio: Maximum width as fraction of screen width.
        max_h_ratio: Maximum height as fraction of screen height.

    Returns:
        (display_width, display_height) in pixels.
    """
    max_w = int(screen_w * max_w_ratio) - 2 * WINDOW_MARGIN
    max_h = int(screen_h * max_h_ratio) - 2 * WINDOW_MARGIN
    scale = min(max_w / img_w, max_h / img_h, 1.0)
    return max(1, int(img_w * scale)), max(1, int(img_h * scale))


def center_and_clamp(root: tk.Tk) -> None:
    """
    Clamp window to screen bounds and center horizontally near top.

    Ensures window is fully visible with appropriate margins, positioned
    near the top of the screen for better visibility.

    Args:
        root: Tkinter root window to position.
    """
    root.update_idletasks()
    req_w = root.winfo_reqwidth()
    req_h = root.winfo_reqheight()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()

    w = min(req_w + WINDOW_MARGIN, sw - 2 * WINDOW_MARGIN)
    h = min(req_h + WINDOW_MARGIN, sh - 2 * WINDOW_MARGIN)
    x = max((sw - w) // 2, WINDOW_MARGIN)
    y = WINDOW_MARGIN  # Pin near top instead of vertical centering

    root.geometry(f"{w}x{h}+{x}+{y}")


def wraplength_for(width_px: int) -> int:
    """
    Calculate appropriate wraplength for labels given a target width.

    Ensures text wraps properly without extending beyond window bounds.

    Args:
        width_px: Target width in pixels.

    Returns:
        Wraplength value for Tkinter labels.
    """
    return max(200, width_px - WRAP_PADDING)


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Window sizing
    "WINDOW_SIZES",
    "get_window_size",
    "apply_window_size",
    # Theme
    "apply_dark_theme",
    # Buttons
    "create_primary_button",
    "create_secondary_button",
    "create_danger_button",
    # Cards
    "OptionCard",
    "create_option_card",
    # Help system
    "create_help_button",
    "show_help_modal",
    # Utilities
    "compute_display_size",
    "center_and_clamp",
    "wraplength_for",
    # Re-exported constants
    "BG_COLOR",
    "BG_SECONDARY",
    "CARD_BG",
    "TEXT_COLOR",
    "TEXT_SECONDARY",
    "ACCENT_COLOR",
    "TITLE_FONT",
    "SECTION_FONT",
    "BODY_FONT",
    "SMALL_FONT",
    "BUTTON_FONT",
    "INSTRUCTION_FONT",
    "LINE_COLOR",
    "WINDOW_MARGIN",
]
