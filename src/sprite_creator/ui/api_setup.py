"""
API Key Setup Screen for AI Sprite Creator.

Provides a GUI dialog for entering and validating Gemini API keys,
replacing the CLI-based interactive setup.
"""

import json
import tkinter as tk
from tkinter import ttk
import webbrowser
from typing import Optional

from ..config import (
    CONFIG_PATH,
    GEMINI_API_URL,
    BG_COLOR,
    TEXT_COLOR,
    TEXT_SECONDARY,
    ACCENT_COLOR,
    SUCCESS_COLOR,
    DANGER_COLOR,
    TITLE_FONT,
    SECTION_FONT,
    BODY_FONT,
    SMALL_FONT,
)
from .tk_common import (
    apply_dark_theme,
    apply_window_size,
    create_primary_button,
    create_secondary_button,
    create_help_button,
)


API_SETUP_HELP_TEXT = """Getting Your Gemini API Key

1. Click "Open Google AI Studio" to go to the API key page
2. Sign in with your Google account
3. Click "Create API Key" if you don't have one
4. Copy the key and paste it here
5. Click "Verify & Save" to test it

Free Credits for New Accounts:
New Google Cloud accounts receive approximately $300 in free credits that can be used for Gemini API calls. This is usually more than enough for creating many character sprites.

Tip: When your credits run low, you can create a new Google account to get fresh credits.

API Key Security:
Your API key is stored locally in your home directory and is only used to communicate with Google's servers. It is never shared with anyone else.

Already Have a Key?
If you've previously saved an API key, it will be shown in the input field (masked). You can replace it with a new key at any time."""


class APISetupWindow:
    """
    GUI dialog for entering and validating Gemini API keys.
    """

    def __init__(self, existing_key: str = ""):
        """
        Initialize the API setup window.

        Args:
            existing_key: Pre-existing API key to display (masked)
        """
        self.root = tk.Tk()
        self.root.title("API Key Setup")
        self.root.protocol("WM_DELETE_WINDOW", self._on_cancel)

        apply_dark_theme(self.root)
        apply_window_size(self.root, "compact")

        self._existing_key = existing_key
        self._result_key: Optional[str] = None
        self._is_validating = False

        self._build_ui()

    def _build_ui(self):
        """Build the API setup UI."""
        # Main container
        main_frame = tk.Frame(self.root, bg=BG_COLOR, padx=30, pady=24)
        main_frame.pack(fill="both", expand=True)

        # Header with help button
        header_frame = tk.Frame(main_frame, bg=BG_COLOR)
        header_frame.pack(fill="x", pady=(0, 16))

        title_label = tk.Label(
            header_frame,
            text="Gemini API Key",
            bg=BG_COLOR,
            fg=TEXT_COLOR,
            font=TITLE_FONT,
        )
        title_label.pack(side="left")

        help_btn = create_help_button(header_frame, "API Key Help", API_SETUP_HELP_TEXT)
        help_btn.pack(side="right")

        # Description
        desc_text = (
            "To generate character sprites, you need a Google Gemini API key.\n"
            "This is free for new accounts with ~$300 in credits."
        )
        desc_label = tk.Label(
            main_frame,
            text=desc_text,
            bg=BG_COLOR,
            fg=TEXT_SECONDARY,
            font=BODY_FONT,
            justify="left",
            wraplength=400,
        )
        desc_label.pack(anchor="w", pady=(0, 20))

        # Open browser button
        browser_btn = create_secondary_button(
            main_frame,
            "Open Google AI Studio",
            self._open_api_page,
            width=22,
        )
        browser_btn.pack(pady=(0, 20))

        # API key input section
        input_frame = tk.Frame(main_frame, bg=BG_COLOR)
        input_frame.pack(fill="x", pady=(0, 8))

        key_label = tk.Label(
            input_frame,
            text="API Key:",
            bg=BG_COLOR,
            fg=TEXT_COLOR,
            font=BODY_FONT,
        )
        key_label.pack(anchor="w", pady=(0, 6))

        # Entry with show/hide toggle
        entry_frame = tk.Frame(input_frame, bg=BG_COLOR)
        entry_frame.pack(fill="x")

        self._key_var = tk.StringVar()
        self._key_entry = tk.Entry(
            entry_frame,
            textvariable=self._key_var,
            font=BODY_FONT,
            width=45,
            show="*",
            bg="#1E1E1E",
            fg=TEXT_COLOR,
            insertbackground=TEXT_COLOR,
            highlightthickness=1,
            highlightbackground="#444444",
            highlightcolor=ACCENT_COLOR,
        )
        self._key_entry.pack(side="left", fill="x", expand=True)

        # Show/hide password toggle
        self._show_key = tk.BooleanVar(value=False)
        show_btn = ttk.Checkbutton(
            entry_frame,
            text="Show",
            variable=self._show_key,
            command=self._toggle_key_visibility,
            style="Dark.TCheckbutton",
        )
        show_btn.pack(side="left", padx=(8, 0))

        # Pre-fill with masked existing key indicator
        if self._existing_key:
            self._key_var.set(self._existing_key)

        # Status label (for validation feedback)
        self._status_var = tk.StringVar()
        self._status_label = tk.Label(
            main_frame,
            textvariable=self._status_var,
            bg=BG_COLOR,
            fg=TEXT_SECONDARY,
            font=SMALL_FONT,
        )
        self._status_label.pack(anchor="w", pady=(0, 20))

        # Tip text
        tip_text = (
            "Tip: When your credits run low, create a new Google account\n"
            "to get fresh free credits."
        )
        tip_label = tk.Label(
            main_frame,
            text=tip_text,
            bg=BG_COLOR,
            fg=TEXT_SECONDARY,
            font=SMALL_FONT,
            justify="left",
        )
        tip_label.pack(anchor="w", pady=(0, 20))

        # Buttons
        button_frame = tk.Frame(main_frame, bg=BG_COLOR)
        button_frame.pack(fill="x")

        self._save_btn = create_primary_button(
            button_frame,
            "Verify & Save",
            self._on_verify_and_save,
            width=15,
        )
        self._save_btn.pack(side="right", padx=(10, 0))

        cancel_btn = create_secondary_button(
            button_frame,
            "Cancel",
            self._on_cancel,
            width=10,
        )
        cancel_btn.pack(side="right")

        # Bind Enter key
        self._key_entry.bind("<Return>", lambda e: self._on_verify_and_save())

        # Focus the entry
        self._key_entry.focus_set()

    def _toggle_key_visibility(self):
        """Toggle API key visibility."""
        if self._show_key.get():
            self._key_entry.configure(show="")
        else:
            self._key_entry.configure(show="*")

    def _open_api_page(self):
        """Open the Google AI Studio API key page in browser."""
        url = "https://aistudio.google.com/app/apikey"
        try:
            webbrowser.open(url)
            self._set_status("Browser opened. Copy your API key and paste it above.", TEXT_SECONDARY)
        except Exception as e:
            self._set_status(f"Could not open browser: {e}", DANGER_COLOR)

    def _set_status(self, message: str, color: str = TEXT_SECONDARY):
        """Set the status message."""
        self._status_var.set(message)
        self._status_label.configure(fg=color)

    def _validate_api_key(self, api_key: str) -> tuple[bool, str]:
        """
        Validate an API key by making a simple API call.

        Returns:
            (success, message) tuple
        """
        import requests

        if not api_key or len(api_key) < 10:
            return False, "API key appears too short"

        # Try a simple request to check if the key is valid
        test_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"

        try:
            response = requests.get(test_url, timeout=10)

            if response.status_code == 200:
                return True, "API key is valid!"
            elif response.status_code == 400:
                return False, "Invalid API key format"
            elif response.status_code == 403:
                return False, "API key is invalid or has been revoked"
            else:
                return False, f"Validation failed: HTTP {response.status_code}"

        except requests.exceptions.Timeout:
            return False, "Connection timed out. Check your internet connection."
        except requests.exceptions.ConnectionError:
            return False, "Connection failed. Check your internet connection."
        except Exception as e:
            return False, f"Validation error: {str(e)}"

    def _on_verify_and_save(self):
        """Handle verify and save button click."""
        if self._is_validating:
            return

        api_key = self._key_var.get().strip()

        if not api_key:
            self._set_status("Please enter an API key", DANGER_COLOR)
            return

        # Show validating state
        self._is_validating = True
        self._set_status("Validating API key...", TEXT_SECONDARY)
        self._save_btn.configure(state="disabled")
        self.root.update()

        # Validate
        success, message = self._validate_api_key(api_key)

        self._is_validating = False
        self._save_btn.configure(state="normal")

        if success:
            self._set_status(message, SUCCESS_COLOR)
            self._result_key = api_key
            # Save to config
            self._save_api_key(api_key)
            # Close after short delay to show success message
            self.root.after(800, self.root.quit)
        else:
            self._set_status(message, DANGER_COLOR)

    def _save_api_key(self, api_key: str):
        """Save API key to config file."""
        config = {}
        if CONFIG_PATH.exists():
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    config = json.load(f)
            except (json.JSONDecodeError, IOError):
                pass

        config["api_key"] = api_key

        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

    def _on_cancel(self):
        """Handle cancel button or window close."""
        self._result_key = None
        self.root.quit()

    def run(self) -> Optional[str]:
        """
        Run the API setup dialog.

        Returns:
            The validated API key, or None if cancelled
        """
        self.root.mainloop()
        result = self._result_key
        self.root.destroy()
        return result


def get_existing_api_key() -> Optional[str]:
    """
    Get existing API key from environment or config.

    Returns:
        API key if found, None otherwise
    """
    import os

    # Check environment variable first
    env_key = os.environ.get("GEMINI_API_KEY")
    if env_key:
        return env_key

    # Check config file
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                config = json.load(f)
                return config.get("api_key")
        except (json.JSONDecodeError, IOError):
            pass

    return None


def show_api_setup(existing_key: str = "") -> Optional[str]:
    """
    Show the API setup dialog.

    Args:
        existing_key: Pre-existing API key to display

    Returns:
        The validated API key, or None if cancelled
    """
    window = APISetupWindow(existing_key)
    return window.run()


def ensure_api_key() -> Optional[str]:
    """
    Ensure we have a valid API key, showing setup dialog if needed.

    Returns:
        Valid API key, or None if user cancelled setup
    """
    existing = get_existing_api_key()

    if existing:
        return existing

    # Show setup dialog
    return show_api_setup()


# For testing
if __name__ == "__main__":
    existing = get_existing_api_key()
    result = show_api_setup(existing or "")
    print(f"Result: {result}")
