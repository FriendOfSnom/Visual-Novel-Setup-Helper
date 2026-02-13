#!/usr/bin/env python3
"""
Entry point for PyInstaller frozen executable.

This wrapper module properly initializes the package context
so relative imports work correctly in the frozen app.
"""

import os
import sys

# Fix for windowed (console=False) PyInstaller builds:
# sys.stdout and sys.stderr are None when there's no console,
# which crashes any library that tries to print (e.g., rembg/onnxruntime).
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

if __name__ == "__main__":
    # Import and run the main function from the package
    from sprite_creator.__main__ import main
    main()
