"""
Screen implementations for the unified sprite creation wizard.

Each screen is a self-contained UI component that handles one phase of the
character creation process.
"""

from .base import WizardStep
# Re-export WizardState from core for backward compatibility
from ...core.models import WizardState
from .setup_steps import SourceStep, CharacterStep, OptionsStep
from .generation_steps import ReviewStep
from .outfit_steps import OutfitReviewStep
from .expression_steps import ExpressionReviewStep
from .finalization_steps import EyeLineStep, ScaleStep, SummaryStep

__all__ = [
    # Base classes
    "WizardStep",
    "WizardState",
    # Setup steps (1-3) - crop now in CharacterStep
    "SourceStep",
    "CharacterStep",
    "OptionsStep",
    # Generation steps
    "ReviewStep",
    # Outfit review
    "OutfitReviewStep",
    # Expression review
    "ExpressionReviewStep",
    # Finalization steps
    "EyeLineStep",
    "ScaleStep",
    "SummaryStep",
]
