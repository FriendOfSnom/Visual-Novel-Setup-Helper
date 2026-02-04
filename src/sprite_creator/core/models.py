"""
Data models for the sprite creator.

Contains dataclasses that represent the state and configuration
of characters and the wizard workflow.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class CharacterConfig:
    """
    Configuration for a character to be generated.

    This represents the user's choices about what kind of character
    to create, separate from the wizard UI state.
    """
    name: str = ""
    voice: str = ""  # "girl" or "boy"
    archetype_label: str = ""  # e.g., "Young Woman", "Adult Man"
    gender_style: str = ""  # "f" or "m"
    concept_text: str = ""  # Text description for prompt-based generation
    outfits: List[str] = field(default_factory=list)
    expressions: List[Tuple[str, str]] = field(default_factory=list)
    outfit_prompts: Dict[str, Dict] = field(default_factory=dict)


@dataclass
class WizardState:
    """
    Complete state container for the wizard.

    Tracks all data collected and generated throughout the sprite creation
    process, including setup data, generated artifacts, and navigation state.
    """

    # === Setup Data (Steps 1-4) ===
    source_mode: str = "image"  # "image" or "prompt"
    image_path: Optional[Path] = None
    source_image: Optional[Any] = None  # PIL Image for image mode (possibly cropped)
    generated_character_image: Optional[Any] = None  # PIL Image for prompt mode
    voice: str = ""
    display_name: str = ""
    archetype_label: str = ""
    gender_style: str = ""
    concept_text: str = ""  # Only for prompt mode
    selected_outfits: List[str] = field(default_factory=list)
    expressions_sequence: List[Tuple[str, str]] = field(default_factory=list)
    outfit_prompt_config: Dict[str, Dict] = field(default_factory=dict)

    # === Generation Data (Steps 5-10) ===

    # Step 5: Crop
    crop_y: Optional[int] = None
    cropped_image_path: Optional[Path] = None

    # Step 6-7: Base generation
    base_pose_path: Optional[Path] = None
    original_base_bytes: Optional[bytes] = None  # For reset functionality
    use_base_as_outfit: bool = True
    base_has_been_regenerated: bool = False
    base_regen_instructions: str = ""

    # Step 8: Outfit generation
    outfits_generated: bool = False  # Flag to prevent regeneration on back navigation
    outfit_paths: List[Path] = field(default_factory=list)
    outfit_cleanup_data: List[Tuple[bytes, bytes]] = field(default_factory=list)  # (original, rembg)
    current_outfit_bytes: List[bytes] = field(default_factory=list)
    outfit_bg_modes: Dict[int, str] = field(default_factory=dict)  # index -> "rembg" or "manual"
    outfit_cleanup_settings: List[Tuple[int, int]] = field(default_factory=list)  # (tolerance, depth)
    outfit_prompts: Dict[str, str] = field(default_factory=dict)  # key -> current prompt text

    # Step 10: Expression generation (per outfit)
    expression_paths: Dict[str, Dict[str, Path]] = field(default_factory=dict)  # outfit -> {expr: path}

    # === Finalization Data (Steps 11-12) ===
    eye_line_ratio: Optional[float] = None
    name_color: Optional[str] = None
    scale_factor: float = 1.0

    # === Output ===
    output_root: Optional[Path] = None
    character_folder: Optional[Path] = None
    api_key: Optional[str] = None

    # === Navigation State ===
    current_step: int = 0
    dirty_from_step: Optional[int] = None  # Steps >= this need regeneration

    def mark_dirty_from(self, step_index: int) -> None:
        """
        Mark that steps from the given index onwards need regeneration.

        Used when user navigates back and makes changes that invalidate
        later generated content.
        """
        if self.dirty_from_step is None or step_index < self.dirty_from_step:
            self.dirty_from_step = step_index

    def clear_dirty(self) -> None:
        """Clear the dirty flag after regeneration has been handled."""
        self.dirty_from_step = None

    def is_step_dirty(self, step_index: int) -> bool:
        """Check if a step needs regeneration."""
        return self.dirty_from_step is not None and step_index >= self.dirty_from_step

    def get_preselected_dict(self) -> Dict:
        """
        Get character info as a dict for pipeline compatibility.

        Returns dict with voice, display_name, archetype_label, gender_style,
        selected_outfits, expressions_sequence, outfit_prompt_config.
        """
        return {
            "voice": self.voice,
            "display_name": self.display_name,
            "archetype_label": self.archetype_label,
            "gender_style": self.gender_style,
            "selected_outfits": self.selected_outfits,
            "expressions_sequence": self.expressions_sequence,
            "outfit_prompt_config": self.outfit_prompt_config,
        }

    def to_character_config(self) -> CharacterConfig:
        """Convert wizard state to a CharacterConfig."""
        return CharacterConfig(
            name=self.display_name,
            voice=self.voice,
            archetype_label=self.archetype_label,
            gender_style=self.gender_style,
            concept_text=self.concept_text,
            outfits=list(self.selected_outfits),
            expressions=list(self.expressions_sequence),
            outfit_prompts=dict(self.outfit_prompt_config),
        )
