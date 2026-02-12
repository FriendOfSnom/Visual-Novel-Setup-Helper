#!/usr/bin/env python3
"""
Entry point for PyInstaller frozen executable.

This wrapper module properly initializes the package context
so relative imports work correctly in the frozen app.
"""

if __name__ == "__main__":
    # Import and run the main function from the package
    from sprite_creator.__main__ import main
    main()
