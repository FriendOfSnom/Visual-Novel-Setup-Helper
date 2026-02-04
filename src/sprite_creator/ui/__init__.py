"""
UI module for Tkinter-based user interfaces.

Provides dialogs and windows for character setup, option selection,
and image review/regeneration workflows.

Includes:
- Dark theme styled components
- Launcher window
- Disclaimer/terms screen
- API key setup dialog
- Full wizard for character creation
- Review windows for outfit/expression generation
"""

from .tk_common import (
    # Window utilities
    compute_display_size,
    center_and_clamp,
    wraplength_for,
    apply_window_size,
    apply_dark_theme,
    get_window_size,
    WINDOW_SIZES,
    # Styled components
    create_primary_button,
    create_secondary_button,
    create_danger_button,
    create_option_card,
    create_help_button,
    show_help_modal,
    OptionCard,
)

from .dialogs import (
    load_name_pool,
    pick_random_name,
)

from .review_windows import (
    review_images_for_step,
    review_initial_base_pose,
    click_to_remove_background,
)

from .launcher import (
    LauncherWindow,
    run_launcher,
    select_character_folder,
)

from .disclaimer import (
    DisclaimerWindow,
    show_disclaimer_if_needed,
    has_accepted_disclaimer,
    record_disclaimer_acceptance,
)

from .api_setup import (
    APISetupWindow,
    show_api_setup,
    ensure_api_key,
    get_existing_api_key,
)

from .full_wizard import (
    FullWizard,
    run_full_wizard,
)

__all__ = [
    # Common utilities
    "compute_display_size",
    "center_and_clamp",
    "wraplength_for",
    "apply_window_size",
    "apply_dark_theme",
    "get_window_size",
    "WINDOW_SIZES",
    # Styled components
    "create_primary_button",
    "create_secondary_button",
    "create_danger_button",
    "create_option_card",
    "create_help_button",
    "show_help_modal",
    "OptionCard",
    # Name utilities
    "load_name_pool",
    "pick_random_name",
    # Review windows
    "review_images_for_step",
    "review_initial_base_pose",
    "click_to_remove_background",
    # Launcher
    "LauncherWindow",
    "run_launcher",
    "select_character_folder",
    # Disclaimer
    "DisclaimerWindow",
    "show_disclaimer_if_needed",
    "has_accepted_disclaimer",
    "record_disclaimer_acceptance",
    # API Setup
    "APISetupWindow",
    "show_api_setup",
    "ensure_api_key",
    "get_existing_api_key",
    # Full Wizard
    "FullWizard",
    "run_full_wizard",
]
