#!/usr/bin/env python3
"""
AI Sprite Creator - Main Entry Point

Run with: python -m sprite_creator

Provides a graphical launcher for:
1. Character Sprite Creator - Full AI-powered sprite generation pipeline
2. Expression Sheet Generator - Create sheets from existing character folders
3. Sprite Tester - Preview sprites in Ren'Py environment
"""

import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox


def main():
    """Main entry point for the standalone launcher."""
    from .ui.disclaimer import show_disclaimer_if_needed
    from .ui.launcher import LauncherWindow
    from .ui.api_setup import ensure_api_key
    from .config import APP_NAME, APP_VERSION

    print(f"\n{'=' * 60}")
    print(f"  {APP_NAME} v{APP_VERSION}")
    print(f"{'=' * 60}\n")

    # Step 1: Show disclaimer on first run
    if not show_disclaimer_if_needed():
        print("[INFO] User declined terms. Exiting.")
        return

    # Step 2: Show launcher to select tool
    def on_sprite_creator():
        pass  # Callback not used, we check result

    def on_expression_sheets():
        pass

    def on_sprite_tester():
        pass

    launcher = LauncherWindow(on_sprite_creator, on_expression_sheets, on_sprite_tester)
    selected_tool = launcher.run()

    if not selected_tool:
        print("[INFO] No tool selected. Exiting.")
        return

    print(f"[INFO] Selected tool: {selected_tool}")

    # Handle each tool
    if selected_tool == "sprite_creator":
        run_sprite_creator()
    elif selected_tool == "expression_sheets":
        run_expression_sheets()
    elif selected_tool == "sprite_tester":
        run_sprite_tester()


def run_sprite_creator():
    """Run the full character sprite creator wizard."""
    from .ui.api_setup import ensure_api_key
    from .ui.full_wizard import run_full_wizard

    print("\n[INFO] Starting Character Sprite Creator...")

    # Ensure API key is configured
    api_key = ensure_api_key()
    if not api_key:
        print("[INFO] API key setup cancelled. Returning to launcher.")
        # Re-run main to show launcher again
        main()
        return

    # Ask for output folder
    root = tk.Tk()
    root.withdraw()
    output_folder = filedialog.askdirectory(
        title="Choose output folder for character sprites"
    )
    root.destroy()

    if not output_folder:
        print("[INFO] No output folder selected. Returning to launcher.")
        main()
        return

    output_path = Path(output_folder)
    print(f"[INFO] Output folder: {output_path}")

    # Run the unified wizard
    try:
        result = run_full_wizard(output_root=output_path, api_key=api_key)
        if result:
            print("\n[INFO] Character sprite creation complete!")
            print(f"[INFO] Character created: {result.display_name}")
            if result.character_folder:
                print(f"[INFO] Output folder: {result.character_folder}")
        else:
            print("[INFO] Wizard cancelled by user.")
    except SystemExit:
        print("[INFO] Wizard exited.")
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred:\n{e}")
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()


def run_expression_sheets():
    """Run the expression sheet generator for existing characters."""
    from .tools.expression_sheets import main as run_sheet_generator
    from .tools.expression_sheets import get_all_pose_paths

    print("\n[INFO] Starting Expression Sheet Generator...")

    # Ask for folder containing character(s)
    root = tk.Tk()
    root.withdraw()
    folder = filedialog.askdirectory(
        title="Select folder containing character(s)"
    )
    root.destroy()

    if not folder:
        print("[INFO] No folder selected. Returning to launcher.")
        main()
        return

    folder_path = Path(folder)

    # Check if valid character folder structure
    pose_paths = get_all_pose_paths(str(folder_path))
    if not pose_paths:
        messagebox.showerror(
            "Invalid Folder",
            "No valid character structure found.\n\n"
            "Expected structure:\n"
            "  <character>/<pose>/faces/face/*.png\n\n"
            "Example:\n"
            "  John/a/faces/face/0.png"
        )
        main()
        return

    # Run the generator
    try:
        # Temporarily override sys.argv for the expression sheet main()
        original_argv = sys.argv
        sys.argv = ["expression_sheets", str(folder_path)]
        run_sheet_generator()
        sys.argv = original_argv
        print("\n[INFO] Expression sheets generated successfully!")
        messagebox.showinfo("Complete", "Expression sheets generated successfully!")
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred:\n{e}")
        print(f"[ERROR] {e}")

    # Return to launcher
    main()


def run_sprite_tester():
    """Run the sprite tester for existing characters."""
    print("\n[INFO] Starting Sprite Tester...")

    # Ask for character folder
    root = tk.Tk()
    root.withdraw()
    folder = filedialog.askdirectory(
        title="Select character folder to test"
    )
    root.destroy()

    if not folder:
        print("[INFO] No folder selected. Returning to launcher.")
        main()
        return

    folder_path = Path(folder)

    # Check if valid character folder (has character.yml)
    char_yml = folder_path / "character.yml"
    if not char_yml.exists():
        messagebox.showerror(
            "Invalid Character Folder",
            "No character.yml found in selected folder.\n\n"
            "Please select a valid character folder created by\n"
            "the Character Sprite Creator."
        )
        main()
        return

    # Run the tester
    try:
        from .tools.tester import launch_sprite_tester
        launch_sprite_tester(folder_path)
        print("\n[INFO] Sprite tester finished.")
    except ImportError:
        messagebox.showerror(
            "Tester Not Available",
            "The sprite tester module is not available.\n"
            "Make sure all dependencies are installed."
        )
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred:\n{e}")
        print(f"[ERROR] {e}")

    # Return to launcher
    main()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] Unhandled exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
