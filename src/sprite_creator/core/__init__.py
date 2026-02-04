"""
Core business logic layer.

Contains data models, validation, and core processing logic
that is independent of the UI layer.
"""

from .models import WizardState, CharacterConfig

__all__ = [
    "WizardState",
    "CharacterConfig",
]
