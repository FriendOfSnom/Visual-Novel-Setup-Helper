"""
Character finalization utilities.

Handles expression sheet generation for completed characters.
"""

import subprocess
import sys
from pathlib import Path


def generate_expression_sheets_for_root(root_folder: Path) -> None:
    """
    Run expression_sheets.py on the given folder to generate expression sheets.

    This is used at the end of the pipeline so that a newly created character
    immediately has expression sheets available for Ren'Py scripting.

    Args:
        root_folder: Character folder or root directory containing character folders.
    """
    if not root_folder.is_dir():
        print(f"[WARN] Not generating expression sheets; '{root_folder}' is not a directory.")
        return

    # Get path to expression_sheets.py in the tools subpackage
    expression_sheets_path = Path(__file__).parent.parent / "tools" / "expression_sheets.py"
    cmd = [sys.executable, str(expression_sheets_path), str(root_folder)]
    try:
        print(f"[INFO] Running expression_sheets.py on: {root_folder}")
        subprocess.run(cmd, check=True)
        print("[INFO] Expression sheets generated successfully.")
    except subprocess.CalledProcessError as e:
        print(f"[WARN] expression_sheets.py failed: {e}")
    except Exception as e:
        print(f"[WARN] Could not run expression_sheets.py: {e}")
