"""
Main Launcher Window for AI Sprite Creator.

Provides a graphical launcher with three tool options:
1. Character Sprite Creator (primary) - Full AI-powered sprite generation pipeline
2. Expression Sheet Generator - Generate sheets from existing character folders
3. Sprite Tester - Preview sprites in Ren'Py environment
"""

import tkinter as tk
import webbrowser
from tkinter import filedialog, messagebox
from pathlib import Path
from typing import Optional, Callable

from ..config import (
    APP_NAME,
    APP_VERSION,
    BG_COLOR,
    BG_SECONDARY,
    CARD_BG,
    CARD_BG_HOVER,
    TEXT_COLOR,
    TEXT_SECONDARY,
    ACCENT_COLOR,
    TITLE_FONT,
    SECTION_FONT,
    BODY_FONT,
    SMALL_FONT,
    CARD_PADDING,
)
from .tk_common import (
    apply_dark_theme,
    apply_window_size,
    create_primary_button,
    create_secondary_button,
    create_help_button,
)
from .api_setup import show_api_setup, get_existing_api_key


# Google AI Studio usage dashboard URL
AI_STUDIO_USAGE_URL = "https://aistudio.google.com/usage"


# Help text for the launcher
LAUNCHER_HELP_TEXT = """Welcome to AI Sprite Creator!

Choose one of the three tools:

Character Sprite Creator (Recommended)
Generate complete character sprites using AI. This includes:
- AI-powered sprite generation from text or images
- Multiple outfits and expressions
- Automatic background removal and cropping
- Expression sheet generation
- Sprite testing in Ren'Py

Expression Sheet Generator
Create expression sheet images from existing character folders. Use this if you have already created characters and want to generate reference sheets.

Sprite Tester
Preview existing character sprites in a Ren'Py environment. Tests outfit switching, expressions, and the character loading system.

Note: You'll need a Google Cloud API key (not the basic AI Studio free tier). New Google Cloud accounts get $300 in free credits - see the API setup help for instructions."""


class ToolCard(tk.Frame):
    """
    A large clickable card for tool selection.
    """

    def __init__(
        self,
        parent: tk.Widget,
        title: str,
        description: str,
        icon_text: str = "",
        primary: bool = False,
        on_click: Optional[Callable] = None,
    ):
        # Primary cards get accent border
        highlight_color = ACCENT_COLOR if primary else CARD_BG
        super().__init__(parent, bg=CARD_BG, highlightbackground=highlight_color,
                         highlightthickness=2 if primary else 1)

        self._on_click = on_click
        self._primary = primary
        self._base_bg = CARD_BG

        # Padding frame
        inner = tk.Frame(self, bg=CARD_BG, padx=20, pady=16)
        inner.pack(fill="both", expand=True)

        # Icon/emoji area (optional)
        if icon_text:
            icon_label = tk.Label(
                inner,
                text=icon_text,
                bg=CARD_BG,
                fg=TEXT_COLOR,
                font=(SECTION_FONT[0], 28),
            )
            icon_label.pack(pady=(0, 8))
            icon_label.bind("<Button-1>", self._handle_click)
            icon_label.bind("<Enter>", self._on_enter)
            icon_label.bind("<Leave>", self._on_leave)

        # Title
        title_label = tk.Label(
            inner,
            text=title,
            bg=CARD_BG,
            fg=TEXT_COLOR,
            font=SECTION_FONT,
        )
        title_label.pack(pady=(0, 6))

        # Description
        desc_label = tk.Label(
            inner,
            text=description,
            bg=CARD_BG,
            fg=TEXT_SECONDARY,
            font=SMALL_FONT,
            wraplength=220,
            justify="center",
        )
        desc_label.pack()

        # Primary badge
        if primary:
            badge = tk.Label(
                inner,
                text="Recommended",
                bg=ACCENT_COLOR,
                fg=TEXT_COLOR,
                font=(SMALL_FONT[0], 9),
                padx=8,
                pady=2,
            )
            badge.pack(pady=(10, 0))
            badge.bind("<Button-1>", self._handle_click)
            badge.bind("<Enter>", self._on_enter)
            badge.bind("<Leave>", self._on_leave)

        # Store references for hover effects
        self._inner = inner
        self._labels = [title_label, desc_label]
        if icon_text:
            self._labels.append(icon_label)

        # Bind click and hover
        self.bind("<Button-1>", self._handle_click)
        inner.bind("<Button-1>", self._handle_click)
        title_label.bind("<Button-1>", self._handle_click)
        desc_label.bind("<Button-1>", self._handle_click)

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        inner.bind("<Enter>", self._on_enter)
        inner.bind("<Leave>", self._on_leave)
        title_label.bind("<Enter>", self._on_enter)
        title_label.bind("<Leave>", self._on_leave)
        desc_label.bind("<Enter>", self._on_enter)
        desc_label.bind("<Leave>", self._on_leave)

        self.configure(cursor="hand2")

    def _handle_click(self, event=None):
        if self._on_click:
            self._on_click()

    def _on_enter(self, event=None):
        self._set_bg(CARD_BG_HOVER)

    def _on_leave(self, event=None):
        self._set_bg(self._base_bg)

    def _set_bg(self, color: str):
        self.configure(bg=color)
        self._inner.configure(bg=color)
        for label in self._labels:
            label.configure(bg=color)


class LauncherWindow:
    """
    Main launcher window for the AI Sprite Creator application.
    """

    def __init__(self, on_sprite_creator: Callable, on_expression_sheets: Callable,
                 on_sprite_tester: Callable):
        """
        Initialize the launcher window.

        Args:
            on_sprite_creator: Callback when Character Sprite Creator is selected
            on_expression_sheets: Callback when Expression Sheet Generator is selected
            on_sprite_tester: Callback when Sprite Tester is selected
        """
        self._on_sprite_creator = on_sprite_creator
        self._on_expression_sheets = on_expression_sheets
        self._on_sprite_tester = on_sprite_tester

        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} v{APP_VERSION}")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Apply dark theme and sizing
        apply_dark_theme(self.root)
        apply_window_size(self.root, "standard")

        self._build_ui()
        self._result: Optional[str] = None

    def _build_ui(self):
        """Build the launcher UI."""
        # Main container
        main_frame = tk.Frame(self.root, bg=BG_COLOR, padx=40, pady=30)
        main_frame.pack(fill="both", expand=True)

        # Header with help button
        header_frame = tk.Frame(main_frame, bg=BG_COLOR)
        header_frame.pack(fill="x", pady=(0, 10))

        # Title area (left side)
        title_frame = tk.Frame(header_frame, bg=BG_COLOR)
        title_frame.pack(side="left", fill="x", expand=True)

        title_label = tk.Label(
            title_frame,
            text=APP_NAME,
            bg=BG_COLOR,
            fg=TEXT_COLOR,
            font=TITLE_FONT,
        )
        title_label.pack(anchor="w")

        version_label = tk.Label(
            title_frame,
            text=f"Version {APP_VERSION}",
            bg=BG_COLOR,
            fg=TEXT_SECONDARY,
            font=SMALL_FONT,
        )
        version_label.pack(anchor="w")

        # Help button (right side)
        help_btn = create_help_button(header_frame, "About This Tool", LAUNCHER_HELP_TEXT)
        help_btn.pack(side="right", anchor="ne")

        # Subtitle
        subtitle_label = tk.Label(
            main_frame,
            text="AI-powered character sprite generation for visual novels",
            bg=BG_COLOR,
            fg=TEXT_SECONDARY,
            font=BODY_FONT,
        )
        subtitle_label.pack(pady=(0, 30))

        # Tool cards container
        cards_frame = tk.Frame(main_frame, bg=BG_COLOR)
        cards_frame.pack(fill="both", expand=True)

        # Configure grid for responsive layout
        cards_frame.columnconfigure(0, weight=1)
        cards_frame.columnconfigure(1, weight=1)
        cards_frame.columnconfigure(2, weight=1)

        # Card 1: Character Sprite Creator (primary)
        card1 = ToolCard(
            cards_frame,
            title="Character Sprite\nCreator",
            description="Generate complete character sprites with AI. Includes expressions, outfits, and automatic processing.",
            icon_text="\u2728",  # Sparkles emoji
            primary=True,
            on_click=self._select_sprite_creator,
        )
        card1.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        # Card 2: Expression Sheet Generator
        card2 = ToolCard(
            cards_frame,
            title="Expression Sheet\nGenerator",
            description="Create expression reference sheets from existing character folders.",
            icon_text="\U0001F5BC",  # Frame emoji
            primary=False,
            on_click=self._select_expression_sheets,
        )
        card2.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        # Card 3: Sprite Tester
        card3 = ToolCard(
            cards_frame,
            title="Sprite\nTester",
            description="Preview character sprites in a Ren'Py environment with outfit and expression switching.",
            icon_text="\U0001F3AE",  # Game controller emoji
            primary=False,
            on_click=self._select_sprite_tester,
        )
        card3.grid(row=0, column=2, padx=10, pady=10, sticky="nsew")

        # Footer
        footer_frame = tk.Frame(main_frame, bg=BG_COLOR)
        footer_frame.pack(fill="x", pady=(30, 0))

        footer_text = tk.Label(
            footer_frame,
            text="Requires a Google Cloud API key (free $300 credits for new accounts)",
            bg=BG_COLOR,
            fg=TEXT_SECONDARY,
            font=SMALL_FONT,
        )
        footer_text.pack()

        # Button row for API settings and usage
        btn_row = tk.Frame(footer_frame, bg=BG_COLOR)
        btn_row.pack(pady=(10, 0))

        # API Settings button
        settings_btn = create_secondary_button(
            btn_row,
            "API Settings",
            self._open_api_settings,
            width=14,
        )
        settings_btn.pack(side="left", padx=(0, 8))

        # View Usage button
        usage_btn = create_secondary_button(
            btn_row,
            "View API Usage",
            self._open_usage_dashboard,
            width=14,
        )
        usage_btn.pack(side="left")

    def _select_sprite_creator(self):
        """Handle Character Sprite Creator selection."""
        self._result = "sprite_creator"
        self.root.quit()

    def _select_expression_sheets(self):
        """Handle Expression Sheet Generator selection."""
        self._result = "expression_sheets"
        self.root.quit()

    def _select_sprite_tester(self):
        """Handle Sprite Tester selection."""
        self._result = "sprite_tester"
        self.root.quit()

    def _open_api_settings(self):
        """Open the API settings dialog to view/change the Gemini API key."""
        existing_key = get_existing_api_key() or ""
        # Show the API setup dialog as modal (passes parent so it works properly)
        show_api_setup(existing_key, parent=self.root)

    def _open_usage_dashboard(self):
        """Open the Google AI Studio usage dashboard in the default browser."""
        webbrowser.open(AI_STUDIO_USAGE_URL)

    def _on_close(self):
        """Handle window close."""
        self._result = None
        self.root.quit()

    def run(self) -> Optional[str]:
        """
        Run the launcher and return the selected tool.

        Returns:
            "sprite_creator", "expression_sheets", "sprite_tester", or None if closed
        """
        self.root.mainloop()
        result = self._result
        self.root.destroy()
        return result


def select_character_folder(title: str = "Select Character Folder") -> Optional[Path]:
    """
    Show a folder selection dialog for choosing a character folder.

    Args:
        title: Dialog title

    Returns:
        Path to selected folder, or None if cancelled
    """
    root = tk.Tk()
    root.withdraw()

    folder = filedialog.askdirectory(title=title)

    root.destroy()

    if folder:
        return Path(folder)
    return None


def run_launcher() -> Optional[str]:
    """
    Create and run the launcher window.

    Returns:
        Selected tool name or None if closed
    """
    # Placeholder callbacks - the actual implementation will wire these up
    def on_sprite_creator():
        pass

    def on_expression_sheets():
        pass

    def on_sprite_tester():
        pass

    launcher = LauncherWindow(on_sprite_creator, on_expression_sheets, on_sprite_tester)
    return launcher.run()


# For testing
if __name__ == "__main__":
    result = run_launcher()
    print(f"Selected: {result}")
