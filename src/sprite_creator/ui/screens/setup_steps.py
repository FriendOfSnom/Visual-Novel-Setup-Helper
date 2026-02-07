"""
Setup wizard steps (Steps 1-3).

These steps collect initial configuration data before generation begins:
1. Source Selection - Image upload or text prompt
2. Character Info - Name, voice, archetype, concept (includes crop for image mode)
3. Generation Options - Outfit and expression selection
"""

import random
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PIL import Image, ImageTk

from ...config import (
    NAMES_CSV_PATH,
    GENDER_ARCHETYPES,
    ALL_OUTFIT_KEYS,
    OUTFIT_KEYS,
    EXPRESSIONS_SEQUENCE,
    BG_COLOR,
    BG_SECONDARY,
    CARD_BG,
    TEXT_COLOR,
    TEXT_SECONDARY,
    ACCENT_COLOR,
    PAGE_TITLE_FONT,
    SECTION_FONT,
    BODY_FONT,
    SMALL_FONT,
)
from ..tk_common import (
    create_primary_button,
    create_secondary_button,
    create_option_card,
    OptionCard,
)
from ..dialogs import load_name_pool, pick_random_name
from .base import WizardStep, WizardState


# =============================================================================
# Step 1: Source Selection
# =============================================================================

class SourceStep(WizardStep):
    """Step 1: Choose between image upload or text prompt."""

    STEP_ID = "source"
    STEP_TITLE = "Source"
    STEP_HELP = """How to Create Your Character

This step determines how your character will be created.

FROM AN IMAGE
Click the "From an Image" card, then click "Browse for Image..." to select your source file.

Supported formats: PNG, JPG, JPEG, WEBP

For best results, your image should have:
- A standing pose (full body or waist-up)
- A simple or solid background (the AI will normalize it)
- Anime/illustration style artwork
- Clear, unobstructed view of the character
- Resolution of at least 512x512 pixels

The AI will normalize your image (sharpen, add black background) and then generate outfit variations and expressions while preserving the character's appearance.

FROM A TEXT PROMPT
Click the "From a Text Prompt" card to describe a character from scratch.

You'll enter details in the next step, including:
- Physical appearance (hair color, eye color, body type)
- Clothing style and colors
- Personality traits that affect expression
- Any distinctive features

The AI will design the character based on your description.

WHICH SHOULD I CHOOSE?
- Use "From Image" if you have existing artwork or want to match a specific look
- Use "Text Prompt" to create something entirely new

After selecting, click Next to continue."""

    def __init__(self, wizard, state: WizardState):
        super().__init__(wizard, state)
        self._source_cards: List[OptionCard] = []
        self._image_preview_label: Optional[tk.Label] = None
        self._image_preview_frame: Optional[tk.Frame] = None
        self._preview_image_display: Optional[tk.Label] = None  # For actual image preview
        self._tk_preview_img: Optional[ImageTk.PhotoImage] = None  # Prevent GC

    def build_ui(self, parent: tk.Frame) -> None:
        parent.configure(bg=BG_COLOR)

        # Title
        tk.Label(
            parent,
            text="How would you like to create this character?",
            bg=BG_COLOR,
            fg=TEXT_COLOR,
            font=PAGE_TITLE_FONT,
        ).pack(pady=(0, 24))

        # Cards container
        cards_frame = tk.Frame(parent, bg=BG_COLOR)
        cards_frame.pack()

        # Image card
        image_card = create_option_card(
            cards_frame,
            "From an Image",
            "Upload an existing character image.\nAI will create variations while\nmaintaining their appearance.",
            selected=True,
            on_click=lambda c: self._select_source_card(c, "image"),
            width=260,
            height=140,
        )
        image_card.pack(side="left", padx=16)
        self._source_cards.append(image_card)

        # Prompt card
        prompt_card = create_option_card(
            cards_frame,
            "From a Text Prompt",
            "Describe your character and\nlet AI design them from scratch.",
            selected=False,
            on_click=lambda c: self._select_source_card(c, "prompt"),
            width=260,
            height=140,
        )
        prompt_card.pack(side="left", padx=16)
        self._source_cards.append(prompt_card)

        # Selected image preview (for image mode)
        self._image_preview_frame = tk.Frame(parent, bg=BG_COLOR)
        self._image_preview_frame.pack(pady=(24, 0))

        self._image_preview_label = tk.Label(
            self._image_preview_frame,
            text="No image selected",
            bg=BG_COLOR,
            fg=TEXT_SECONDARY,
            font=SMALL_FONT,
        )
        self._image_preview_label.pack()

        browse_btn = create_secondary_button(
            self._image_preview_frame,
            "Browse for Image...",
            self._browse_image,
            width=18,
        )
        browse_btn.pack(pady=(8, 0))

        # Actual image preview display
        self._preview_image_display = tk.Label(
            self._image_preview_frame,
            bg=BG_COLOR,
        )
        self._preview_image_display.pack(pady=(12, 0))

    def _select_source_card(self, card: OptionCard, mode: str) -> None:
        """Handle source card selection."""
        self.state.source_mode = mode

        # Update card selection states
        for c in self._source_cards:
            c.selected = (c == card)

        # Show/hide image preview based on mode
        if mode == "image":
            self._image_preview_frame.pack(pady=(24, 0))
        else:
            self._image_preview_frame.pack_forget()

    def _browse_image(self) -> None:
        """Open file dialog to select source image."""
        filename = filedialog.askopenfilename(
            title="Choose character source image",
            filetypes=[
                ("Images", "*.png;*.jpg;*.jpeg;*.webp"),
                ("PNG", "*.png"),
                ("JPEG", "*.jpg;*.jpeg"),
                ("WEBP", "*.webp"),
                ("All files", "*.*"),
            ],
        )
        if filename:
            self.state.image_path = Path(filename)
            self._image_preview_label.configure(
                text=f"Selected: {self.state.image_path.name}",
                fg=TEXT_COLOR,
            )
            # Show actual image preview
            self._show_image_preview(Path(filename))

    def _show_image_preview(self, image_path: Path) -> None:
        """Display a thumbnail preview of the selected image."""
        try:
            img = Image.open(image_path).convert("RGBA")
            # Scale to max 250px height while preserving aspect ratio
            max_h = 250
            w, h = img.size
            if h > max_h:
                scale = max_h / h
                img = img.resize((int(w * scale), max_h), Image.LANCZOS)

            self._tk_preview_img = ImageTk.PhotoImage(img)
            self._preview_image_display.configure(image=self._tk_preview_img)
        except Exception as e:
            self._image_preview_label.configure(
                text=f"Error loading preview: {e}",
                fg="#ff5555",
            )

    def validate(self) -> bool:
        if self.state.source_mode == "image" and not self.state.image_path:
            messagebox.showerror("No Image Selected", "Please select a source image.")
            return False
        return True


# =============================================================================
# Step 2: Character Info (Two-Column Layout with Crop)
# =============================================================================

class CharacterStep(WizardStep):
    """Step 2: Collect name, voice, archetype, concept, and handle crop."""

    STEP_ID = "character"
    STEP_TITLE = "Character"
    STEP_HELP = """Character Setup

This step configures your character's identity and prepares the base image.

LEFT SIDE: CHARACTER INFO

Voice (Required)
Click "Girl" or "Boy" to set the character's voice. This determines:
- Which name pool is used for random names
- Which archetypes are available
- Pronoun references in some prompts

Name
A random name is suggested when you pick a voice. You can type any name you want. This appears in the final character.yml file.

Archetype (Required)
Affects the style of generated outfits:
- Young Woman/Man: School-age styling, unlocks "Standard Uniform" option
- Adult Woman/Man: Professional, mature clothing styles
- Motherly/Fatherly: Older character styling

RIGHT SIDE: IMAGE HANDLING

For Image Mode:
Your image is automatically "normalized" when you enter this step:
- Resolution is sharpened if needed
- A black background is added
- The character is kept intact

After normalization, you can optionally modify the character by typing instructions (e.g., "change hair to blue", "add glasses") and clicking "Modify Character".

Use "Reset to Normalized" to undo modifications.

CROP TOOL
Click anywhere on the image to set a horizontal crop line (shown in red). This crops the image at that point - useful for removing feet or adjusting the frame.

- Click "Accept Crop" to apply the crop
- Click "Restore Original" to undo and start over
- The Next button is disabled until you accept

For Text Prompt Mode:
Fill in the "Character Description" box with details about appearance, then click "Generate Character". Once generated, use the crop tool as described above.

Click Next when your character looks right."""

    def __init__(self, wizard, state: WizardState):
        super().__init__(wizard, state)
        self._voice_var: Optional[tk.StringVar] = None
        self._name_var: Optional[tk.StringVar] = None
        self._arch_var: Optional[tk.StringVar] = None
        self._arch_menu: Optional[tk.OptionMenu] = None
        self._concept_text: Optional[tk.Text] = None
        self._concept_frame: Optional[tk.Frame] = None
        self._voice_indicator: Optional[tk.Label] = None
        self._name_entry: Optional[tk.Entry] = None

        # Two-column layout frames
        self._left_col: Optional[tk.Frame] = None
        self._right_col: Optional[tk.Frame] = None

        # Crop-related
        self._crop_frame: Optional[tk.Frame] = None
        self._crop_canvas: Optional[tk.Canvas] = None
        self._crop_image: Optional[ImageTk.PhotoImage] = None
        self._crop_original_img: Optional[Image.Image] = None
        self._crop_guide_line_id: Optional[int] = None
        self._crop_scale: float = 1.0
        self._crop_disp_w: int = 0
        self._crop_disp_h: int = 0
        self._crop_status_label: Optional[tk.Label] = None

        # Crop accept/restore
        self._crop_accepted: bool = False
        self._crop_buttons_frame: Optional[tk.Frame] = None
        self._accept_crop_btn: Optional[tk.Button] = None
        self._restore_btn: Optional[tk.Button] = None
        self._original_image_backup: Optional[Image.Image] = None

        # For prompt mode: generation
        self._generate_btn: Optional[tk.Button] = None
        self._generation_status: Optional[tk.Label] = None
        self._generated_image: Optional[Image.Image] = None

        # For image mode: normalization and modification
        self._image_modify_frame: Optional[tk.Frame] = None
        self._modify_text: Optional[tk.Text] = None
        self._modify_btn: Optional[tk.Button] = None
        self._reset_to_normalized_btn: Optional[tk.Button] = None
        self._image_status: Optional[tk.Label] = None
        self._is_normalizing: bool = False
        self._normalized_image: Optional[Image.Image] = None
        self._content_visible: bool = False  # Track if step content is visible

        # Load name pools
        self._girl_names, self._boy_names = load_name_pool(NAMES_CSV_PATH)

    def build_ui(self, parent: tk.Frame) -> None:
        parent.configure(bg=BG_COLOR)

        # Title
        tk.Label(
            parent,
            text="Character Information",
            bg=BG_COLOR,
            fg=TEXT_COLOR,
            font=PAGE_TITLE_FONT,
        ).pack(pady=(0, 12))

        # Two-column container
        columns = tk.Frame(parent, bg=BG_COLOR)
        columns.pack(fill="both", expand=True, padx=20)

        # === LEFT COLUMN: Form fields ===
        self._left_col = tk.Frame(columns, bg=BG_COLOR)
        self._left_col.pack(side="left", fill="both", expand=True, padx=(0, 20))

        # Voice selection
        voice_frame = tk.Frame(self._left_col, bg=BG_COLOR)
        voice_frame.pack(fill="x", pady=(0, 12))

        tk.Label(
            voice_frame,
            text="Voice:",
            bg=BG_COLOR,
            fg=TEXT_COLOR,
            font=BODY_FONT,
            width=10,
            anchor="e",
        ).pack(side="left", padx=(0, 8))

        self._voice_var = tk.StringVar(value="")

        girl_btn = create_secondary_button(
            voice_frame, "Girl", lambda: self._set_voice("girl"), width=8
        )
        girl_btn.pack(side="left", padx=(0, 6))

        boy_btn = create_secondary_button(
            voice_frame, "Boy", lambda: self._set_voice("boy"), width=8
        )
        boy_btn.pack(side="left")

        self._voice_indicator = tk.Label(
            voice_frame,
            text="",
            bg=BG_COLOR,
            fg=ACCENT_COLOR,
            font=SMALL_FONT,
        )
        self._voice_indicator.pack(side="left", padx=(10, 0))

        # Name entry
        name_frame = tk.Frame(self._left_col, bg=BG_COLOR)
        name_frame.pack(fill="x", pady=(0, 12))

        tk.Label(
            name_frame,
            text="Name:",
            bg=BG_COLOR,
            fg=TEXT_COLOR,
            font=BODY_FONT,
            width=10,
            anchor="e",
        ).pack(side="left", padx=(0, 8))

        self._name_var = tk.StringVar(value="")
        self._name_entry = tk.Entry(
            name_frame,
            textvariable=self._name_var,
            font=BODY_FONT,
            width=20,
            bg="#1E1E1E",
            fg=TEXT_COLOR,
            insertbackground=TEXT_COLOR,
        )
        self._name_entry.pack(side="left")

        # Archetype selection
        arch_frame = tk.Frame(self._left_col, bg=BG_COLOR)
        arch_frame.pack(fill="x", pady=(0, 12))

        tk.Label(
            arch_frame,
            text="Archetype:",
            bg=BG_COLOR,
            fg=TEXT_COLOR,
            font=BODY_FONT,
            width=10,
            anchor="e",
        ).pack(side="left", padx=(0, 8))

        self._arch_var = tk.StringVar(value="")
        self._arch_menu = tk.OptionMenu(arch_frame, self._arch_var, "")
        self._arch_menu.configure(width=16, bg=CARD_BG, fg=TEXT_COLOR)
        self._arch_menu.pack(side="left")

        # Concept text (only shown for prompt mode)
        self._concept_frame = tk.Frame(self._left_col, bg=BG_COLOR)

        tk.Label(
            self._concept_frame,
            text="Character Description:",
            bg=BG_COLOR,
            fg=TEXT_COLOR,
            font=BODY_FONT,
        ).pack(anchor="w", pady=(0, 6))

        tk.Label(
            self._concept_frame,
            text="Describe appearance, style, personality traits, etc.",
            bg=BG_COLOR,
            fg=TEXT_SECONDARY,
            font=SMALL_FONT,
        ).pack(anchor="w", pady=(0, 6))

        # Gemini safety warning
        tk.Label(
            self._concept_frame,
            text="Note: Gemini may refuse to generate characters with certain descriptions. "
                 "If generation fails, try adjusting your description.",
            bg=BG_COLOR,
            fg="#FFB347",  # Warning orange
            font=SMALL_FONT,
            wraplength=350,
            justify="left",
        ).pack(anchor="w", pady=(0, 8))

        self._concept_text = tk.Text(
            self._concept_frame,
            height=5,
            width=40,
            wrap="word",
            bg="#1E1E1E",
            fg=TEXT_COLOR,
            insertbackground=TEXT_COLOR,
            font=BODY_FONT,
        )
        self._concept_text.pack(fill="x")

        # Generate button (prompt mode only)
        self._generate_btn = create_primary_button(
            self._concept_frame,
            "Generate Character",
            self._on_generate_click,
            width=18,
        )
        self._generate_btn.pack(pady=(10, 0))

        self._generation_status = tk.Label(
            self._concept_frame,
            text="",
            bg=BG_COLOR,
            fg=TEXT_SECONDARY,
            font=SMALL_FONT,
        )
        self._generation_status.pack(pady=(6, 0))

        # === RIGHT COLUMN: Image preview / Crop ===
        self._right_col = tk.Frame(columns, bg=BG_COLOR)
        self._right_col.pack(side="left", fill="both", expand=True)

        # Crop section
        self._crop_frame = tk.Frame(self._right_col, bg=BG_COLOR)

        tk.Label(
            self._crop_frame,
            text="Set Crop Line",
            bg=BG_COLOR,
            fg=TEXT_COLOR,
            font=SECTION_FONT,
        ).pack(pady=(0, 6))

        tk.Label(
            self._crop_frame,
            text="Click to set crop line at mid-thigh level, then click Accept Crop.",
            bg=BG_COLOR,
            fg=TEXT_SECONDARY,
            font=SMALL_FONT,
        ).pack(pady=(0, 6))

        # Canvas container
        crop_canvas_container = tk.Frame(self._crop_frame, bg=CARD_BG, padx=2, pady=2)
        crop_canvas_container.pack()

        self._crop_canvas = tk.Canvas(
            crop_canvas_container,
            width=280,
            height=350,
            bg="black",
            highlightthickness=0,
        )
        self._crop_canvas.pack()
        self._crop_canvas.bind("<Motion>", self._on_crop_motion)
        self._crop_canvas.bind("<Button-1>", self._on_crop_click)

        self._crop_status_label = tk.Label(
            self._crop_frame,
            text="",
            bg=BG_COLOR,
            fg=ACCENT_COLOR,
            font=SMALL_FONT,
        )
        self._crop_status_label.pack(pady=(6, 0))

        # Crop buttons (Accept / Restore)
        self._crop_buttons_frame = tk.Frame(self._crop_frame, bg=BG_COLOR)
        self._crop_buttons_frame.pack(pady=(6, 0))

        self._accept_crop_btn = create_primary_button(
            self._crop_buttons_frame,
            "Accept Crop",
            self._on_accept_crop,
            width=12,
        )
        self._accept_crop_btn.pack(side="left", padx=(0, 8))

        self._restore_btn = create_secondary_button(
            self._crop_buttons_frame,
            "Restore Original",
            self._on_restore_original,
            width=14,
        )
        # Restore button starts hidden
        self._restore_btn.pack_forget()

        # === Image Mode: Modify Character Section (shown in image mode only) ===
        self._image_modify_frame = tk.Frame(self._left_col, bg=BG_COLOR)
        # Will be packed in on_enter for image mode

        tk.Label(
            self._image_modify_frame,
            text="Modify Character (Optional)",
            bg=BG_COLOR,
            fg=TEXT_COLOR,
            font=SECTION_FONT,
        ).pack(anchor="w", pady=(0, 6))

        tk.Label(
            self._image_modify_frame,
            text="Describe changes to make (hair, clothes, features, etc.)",
            bg=BG_COLOR,
            fg=TEXT_SECONDARY,
            font=SMALL_FONT,
        ).pack(anchor="w", pady=(0, 6))

        self._modify_text = tk.Text(
            self._image_modify_frame,
            height=3,
            width=40,
            wrap="word",
            bg="#1E1E1E",
            fg=TEXT_COLOR,
            insertbackground=TEXT_COLOR,
            font=BODY_FONT,
        )
        self._modify_text.pack(fill="x")

        # Buttons row for modify and reset
        modify_btns_frame = tk.Frame(self._image_modify_frame, bg=BG_COLOR)
        modify_btns_frame.pack(pady=(8, 0))

        self._modify_btn = create_secondary_button(
            modify_btns_frame,
            "Modify Character",
            self._on_modify_click,
            width=16,
        )
        self._modify_btn.pack(side="left", padx=(0, 8))

        self._reset_to_normalized_btn = create_secondary_button(
            modify_btns_frame,
            "Reset to Normalized",
            self._on_reset_to_normalized,
            width=16,
        )
        self._reset_to_normalized_btn.pack(side="left")
        # Hidden initially until a modification is made
        self._reset_to_normalized_btn.pack_forget()

        self._image_status = tk.Label(
            self._image_modify_frame,
            text="",
            bg=BG_COLOR,
            fg=TEXT_SECONDARY,
            font=SMALL_FONT,
        )
        self._image_status.pack(pady=(6, 0))

    def _set_voice(self, voice: str) -> None:
        """Handle voice selection."""
        self._voice_var.set(voice)
        self.state.voice = voice
        self._voice_indicator.configure(text=f"({voice.capitalize()})")

        # Update archetype menu
        self._update_archetype_menu()

        # Set random name if empty
        if not self._name_var.get().strip():
            name = pick_random_name(voice, self._girl_names, self._boy_names)
            self._name_var.set(name)

        self._name_entry.focus_set()

    def _update_archetype_menu(self) -> None:
        """Update archetype menu based on voice."""
        menu = self._arch_menu["menu"]
        menu.delete(0, "end")

        voice = self._voice_var.get()
        if voice == "girl":
            labels = [label for (label, g) in GENDER_ARCHETYPES if g == "f"]
            self.state.gender_style = "f"
        elif voice == "boy":
            labels = [label for (label, g) in GENDER_ARCHETYPES if g == "m"]
            self.state.gender_style = "m"
        else:
            labels = []
            self.state.gender_style = ""

        self._arch_var.set(labels[0] if labels else "")
        for lbl in labels:
            menu.add_command(label=lbl, command=lambda v=lbl: self._arch_var.set(v))

    def _on_generate_click(self) -> None:
        """Handle Generate button click for prompt mode."""
        # Validate required fields first
        if not self._voice_var.get():
            messagebox.showerror("Missing Voice", "Please select a voice before generating.")
            return
        if not self._arch_var.get():
            messagebox.showerror("Missing Archetype", "Please select an archetype before generating.")
            return
        concept = self._concept_text.get("1.0", "end").strip()
        if not concept:
            messagebox.showerror("Missing Description", "Please describe the character before generating.")
            return

        # Save state
        self.state.voice = self._voice_var.get()
        self.state.display_name = self._name_var.get().strip() or pick_random_name(
            self.state.voice, self._girl_names, self._boy_names
        )
        self.state.archetype_label = self._arch_var.get()
        self.state.concept_text = concept

        # Disable button and show status
        self._generate_btn.configure(state="disabled")
        self._generation_status.configure(text="Generating character...", fg=TEXT_SECONDARY)
        self._crop_frame.winfo_toplevel().update()

        # Run generation in background thread
        import threading
        thread = threading.Thread(target=self._run_generation, daemon=True)
        thread.start()

    def _run_generation(self) -> None:
        """Run character generation in background thread."""
        try:
            from io import BytesIO
            from ...api.gemini_client import get_api_key, call_gemini_text_or_refs
            from ...api.prompt_builders import build_prompt_for_idea
            from ...config import REF_SPRITES_DIR

            # Get API key (should already be set from earlier steps)
            api_key = self.state.api_key or get_api_key(use_gui=True)

            # Build prompt
            prompt = build_prompt_for_idea(
                concept=self.state.concept_text,
                archetype_label=self.state.archetype_label,
                gender_style=self.state.gender_style,
            )

            # Get reference images if available
            ref_images = []
            if REF_SPRITES_DIR.exists():
                for ext in ("*.png", "*.jpg", "*.jpeg"):
                    ref_images.extend(list(REF_SPRITES_DIR.glob(ext))[:3])

            # Generate image (skip background removal - we'll do it later)
            result_bytes = call_gemini_text_or_refs(
                api_key=api_key,
                prompt=prompt,
                ref_images=ref_images if ref_images else None,
                skip_background_removal=True,  # Don't remove BG at this step
            )

            if result_bytes:
                # Convert bytes to PIL Image
                self._generated_image = Image.open(BytesIO(result_bytes)).convert("RGBA")
                # Schedule UI update on main thread
                self._crop_canvas.after(0, self._on_generation_complete)
            else:
                self._crop_canvas.after(0, lambda: self._on_generation_error("No image returned"))

        except Exception as e:
            error_msg = str(e)
            self._crop_canvas.after(0, lambda: self._on_generation_error(error_msg))

    def _on_generation_complete(self) -> None:
        """Handle successful generation."""
        self._generation_status.configure(text="Character generated!", fg=ACCENT_COLOR)
        self._generate_btn.configure(state="normal")

        # Store as original for crop
        self._crop_original_img = self._generated_image.copy()
        self._original_image_backup = self._generated_image.copy()

        # Show crop section
        self._crop_frame.pack(fill="both", expand=True)
        self._display_crop_image()

        # Disable Next until crop is accepted
        self.wizard._next_btn.configure(state="disabled")

    def _on_generation_error(self, error: str) -> None:
        """Handle generation error."""
        self._generation_status.configure(text=f"Error: {error}", fg="#ff5555")
        self._generate_btn.configure(state="normal")

    def _load_crop_image(self) -> None:
        """Load image from file for crop canvas (image mode)."""
        if not self.state.image_path or not self.state.image_path.exists():
            return

        try:
            self._crop_original_img = Image.open(self.state.image_path).convert("RGBA")
            self._original_image_backup = self._crop_original_img.copy()
        except Exception as e:
            self._crop_status_label.configure(text=f"Error loading: {e}", fg="#ff5555")
            return

        self._display_crop_image()

    def _display_crop_image(self) -> None:
        """Display the current image in the crop canvas."""
        if self._crop_original_img is None:
            return

        original_w, original_h = self._crop_original_img.size

        # Get screen size
        self._crop_canvas.update_idletasks()
        parent = self._crop_canvas.winfo_toplevel()
        sw = parent.winfo_screenwidth()
        sh = parent.winfo_screenheight()

        # Compute display size (fit in right column)
        max_w = int(sw * 0.30)
        max_h = int(sh * 0.45)
        scale = min(max_w / original_w, max_h / original_h, 1.0)
        self._crop_disp_w = max(1, int(original_w * scale))
        self._crop_disp_h = max(1, int(original_h * scale))
        self._crop_scale = original_h / max(1, self._crop_disp_h)

        # Resize canvas
        self._crop_canvas.configure(width=self._crop_disp_w, height=self._crop_disp_h)

        # Create display image
        disp_img = self._crop_original_img.resize(
            (self._crop_disp_w, self._crop_disp_h), Image.LANCZOS
        )
        self._crop_image = ImageTk.PhotoImage(disp_img)

        # Draw image
        self._crop_canvas.delete("all")
        self._crop_canvas.create_image(0, 0, anchor="nw", image=self._crop_image)
        self._crop_guide_line_id = None

        # Reset crop state
        self._crop_accepted = False
        self._restore_btn.pack_forget()
        self._accept_crop_btn.pack(side="left", padx=(0, 8))

        # Restore previous crop if exists
        if self.state.crop_y is not None:
            disp_y = int(self.state.crop_y / self._crop_scale)
            self._draw_crop_line(disp_y)
            self._crop_status_label.configure(text=f"Crop at y={self.state.crop_y}. Click to adjust.")
        else:
            self._crop_status_label.configure(text="Click to set crop line, then Accept Crop")

    def _draw_crop_line(self, y: int) -> None:
        """Draw the crop guide line at the given y position."""
        if self._crop_accepted:
            return  # Don't draw line if crop already accepted
        y = max(0, min(int(y), self._crop_disp_h))
        if self._crop_guide_line_id is None:
            self._crop_guide_line_id = self._crop_canvas.create_line(
                0, y, self._crop_disp_w, y,
                fill="#ff5555", width=3
            )
        else:
            self._crop_canvas.coords(self._crop_guide_line_id, 0, y, self._crop_disp_w, y)

    def _on_crop_motion(self, event) -> None:
        """Handle mouse motion over crop canvas."""
        if self._crop_original_img is None or self._crop_accepted:
            return
        self._draw_crop_line(event.y)

    def _on_crop_click(self, event) -> None:
        """Handle click on crop canvas to set crop position."""
        if self._crop_original_img is None or self._crop_accepted:
            return

        disp_y = max(0, min(event.y, self._crop_disp_h))
        self._draw_crop_line(disp_y)

        # Convert to original image coordinates
        real_y = int(disp_y * self._crop_scale)
        original_h = self._crop_original_img.size[1]

        # Store in state
        if real_y >= original_h - 5:
            # Clicked at/below bottom - no crop
            self.state.crop_y = None
            self._crop_status_label.configure(text="No crop (clicked at bottom)")
        else:
            self.state.crop_y = real_y
            self._crop_status_label.configure(text=f"Crop at y={real_y}. Click Accept to apply.")

    def _on_accept_crop(self) -> None:
        """Apply the current crop (or accept as-is if no crop set) and update the image."""
        if self._crop_original_img is None:
            return

        if self.state.crop_y is not None:
            # Apply the crop
            w, h = self._crop_original_img.size
            cropped = self._crop_original_img.crop((0, 0, w, self.state.crop_y))
            self._crop_original_img = cropped
            self._crop_status_label.configure(text="Crop applied. Click Restore to undo.")
        else:
            # Accept as-is without cropping
            self._crop_status_label.configure(text="Image accepted as-is. Click Restore to undo.")

        # Update display
        self._display_crop_image()
        self._crop_accepted = True
        self.state.crop_y = None  # Clear after applying

        # Update buttons
        self._accept_crop_btn.pack_forget()
        self._restore_btn.pack(side="left")

        # Enable wizard's Next button now that crop is accepted
        self.wizard._next_btn.configure(state="normal")

    def _on_restore_original(self) -> None:
        """Restore the original uncropped image."""
        if self._original_image_backup is None:
            return

        self._crop_original_img = self._original_image_backup.copy()
        self._crop_accepted = False

        # Update display
        self._display_crop_image()

        # Update buttons
        self._restore_btn.pack_forget()
        self._accept_crop_btn.pack(side="left", padx=(0, 8))

        self._crop_status_label.configure(text="Original restored. Click to set new crop.")

        # Re-disable Next button since crop needs to be re-accepted
        self.wizard._next_btn.configure(state="disabled")

    def on_enter(self) -> None:
        """Prepare step based on source mode."""
        if self.state.source_mode == "prompt":
            # Hide image modify frame (prompt mode uses concept frame)
            self._image_modify_frame.pack_forget()
            # Show concept frame with generate button
            self._concept_frame.pack(fill="x", pady=(12, 0))
            # Show crop frame (will be empty until generation)
            self._crop_frame.pack(fill="both", expand=True)
            self._content_visible = True
            # Clear canvas if no generated image yet
            if self._generated_image is None:
                self._crop_canvas.delete("all")
                self._crop_canvas.create_text(
                    140, 175,
                    text="Generate a character\nto see preview",
                    fill=TEXT_SECONDARY,
                    font=BODY_FONT,
                    justify="center",
                )
            else:
                # Generated image exists - disable Next until crop accepted
                if not self._crop_accepted:
                    self.wizard._next_btn.configure(state="disabled")
        else:
            # Image mode
            self._concept_frame.pack_forget()

            if self.state.image_path:
                # Auto-normalize if we haven't already
                if self._normalized_image is None and not self._is_normalizing:
                    # Show loading screen and start normalization
                    # Don't show content yet - it will be shown after normalization
                    self._content_visible = False
                    self._start_normalization()
                elif self._normalized_image is not None:
                    # Already normalized - show the content
                    self._show_image_mode_content()
                    self._display_crop_image()
                    if not self._crop_accepted:
                        self.wizard._next_btn.configure(state="disabled")
                else:
                    # Still normalizing - show loading (shouldn't happen normally)
                    self.show_loading("Normalizing image...")
            else:
                self._crop_frame.pack_forget()
                self._image_modify_frame.pack_forget()

    def _show_image_mode_content(self) -> None:
        """Show the image mode content (modify frame and crop frame)."""
        if self._content_visible:
            return
        self._content_visible = True
        self._image_modify_frame.pack(fill="x", pady=(12, 0))
        self._crop_frame.pack(fill="both", expand=True)

    def _start_normalization(self) -> None:
        """Start image normalization in background thread."""
        if self._is_normalizing:
            return

        self._is_normalizing = True
        self.wizard._next_btn.configure(state="disabled")

        # Show loading screen during normalization
        self.show_loading("Normalizing image...")

        # Run normalization in background thread
        import threading
        thread = threading.Thread(target=self._run_normalization, daemon=True)
        thread.start()

    def _run_normalization(self) -> None:
        """Run image normalization in background thread."""
        try:
            from io import BytesIO
            from ...api.gemini_client import get_api_key, call_gemini_image_edit
            from ...api.prompt_builders import build_normalize_image_prompt
            from ...api.gemini_client import load_image_as_base64

            # Get API key
            api_key = self.state.api_key or get_api_key(use_gui=True)

            # Load source image as base64
            image_b64 = load_image_as_base64(self.state.image_path)

            # Build normalization prompt
            prompt = build_normalize_image_prompt()

            # Call Gemini to normalize
            result_bytes = call_gemini_image_edit(
                api_key=api_key,
                prompt=prompt,
                image_b64=image_b64,
                skip_background_removal=True,  # Don't remove BG at this step
            )

            if result_bytes:
                # Convert bytes to PIL Image
                self._normalized_image = Image.open(BytesIO(result_bytes)).convert("RGBA")
                # Schedule UI update on main thread
                self.wizard.root.after(0, self._on_normalization_complete)
            else:
                self.wizard.root.after(0, lambda: self._on_normalization_error("No image returned"))

        except Exception as e:
            error_msg = str(e)
            self.wizard.root.after(0, lambda: self._on_normalization_error(error_msg))

    def _on_normalization_complete(self) -> None:
        """Handle successful normalization."""
        self._is_normalizing = False

        # Hide loading screen and show content
        self.hide_loading()
        self._show_image_mode_content()

        self._image_status.configure(text="Image normalized!", fg=ACCENT_COLOR)
        self._modify_btn.configure(state="normal")
        # Hide reset button (nothing to reset to yet)
        self._reset_to_normalized_btn.pack_forget()

        # Store as original for crop
        self._crop_original_img = self._normalized_image.copy()
        self._original_image_backup = self._normalized_image.copy()

        # Show normalized image
        self._display_crop_image()

        # Disable Next until crop is accepted
        self.wizard._next_btn.configure(state="disabled")

    def _on_normalization_error(self, error: str) -> None:
        """Handle normalization error - fall back to original image."""
        self._is_normalizing = False

        # Hide loading screen and show content
        self.hide_loading()
        self._show_image_mode_content()

        self._image_status.configure(text=f"Normalization skipped: {error[:50]}...", fg="#ff5555")
        self._modify_btn.configure(state="normal")

        # Use original image without normalization
        self._load_crop_image()
        self.wizard._next_btn.configure(state="disabled")

    def _on_modify_click(self) -> None:
        """Handle Modify Character button click."""
        instructions = self._modify_text.get("1.0", "end").strip()
        if not instructions:
            messagebox.showerror("Missing Instructions", "Please describe the changes you want to make.")
            return

        if self._is_normalizing:
            messagebox.showwarning("Please Wait", "Please wait for normalization to complete.")
            return

        # Disable button and show status
        self._modify_btn.configure(state="disabled")
        self._image_status.configure(text="Modifying character...", fg=TEXT_SECONDARY)
        self.wizard._next_btn.configure(state="disabled")

        # Run modification in background thread
        import threading
        thread = threading.Thread(target=lambda: self._run_modification(instructions), daemon=True)
        thread.start()

    def _run_modification(self, instructions: str) -> None:
        """Run character modification in background thread."""
        try:
            from io import BytesIO
            from ...api.gemini_client import get_api_key, call_gemini_image_edit
            from ...api.prompt_builders import build_character_modification_prompt
            from ...api.gemini_client import load_image_as_base64

            # Get API key
            api_key = self.state.api_key or get_api_key(use_gui=True)

            # Use current image (normalized or original)
            if self._crop_original_img is not None:
                # Save current image to temp buffer for base64 encoding
                buffer = BytesIO()
                self._crop_original_img.save(buffer, format="PNG")
                buffer.seek(0)
                import base64
                image_b64 = base64.b64encode(buffer.read()).decode("utf-8")
            else:
                # Fall back to source file
                image_b64 = load_image_as_base64(self.state.image_path)

            # Build modification prompt
            prompt = build_character_modification_prompt(instructions)

            # Call Gemini to modify
            result_bytes = call_gemini_image_edit(
                api_key=api_key,
                prompt=prompt,
                image_b64=image_b64,
                skip_background_removal=True,
            )

            if result_bytes:
                # Convert bytes to PIL Image
                modified_image = Image.open(BytesIO(result_bytes)).convert("RGBA")
                # Schedule UI update on main thread
                self.wizard.root.after(0, lambda img=modified_image: self._on_modification_complete(img))
            else:
                self.wizard.root.after(0, lambda: self._on_modification_error("No image returned"))

        except Exception as e:
            error_msg = str(e)
            self.wizard.root.after(0, lambda: self._on_modification_error(error_msg))

    def _on_modification_complete(self, modified_image: Image.Image) -> None:
        """Handle successful modification."""
        self._image_status.configure(text="Character modified!", fg=ACCENT_COLOR)
        self._modify_btn.configure(state="normal")

        # Update current image (but keep _normalized_image as reset point)
        self._crop_original_img = modified_image.copy()
        # Keep _normalized_image unchanged - it's the reset point

        # Show reset button so user can go back to normalized version
        self._reset_to_normalized_btn.pack(side="left")

        # Show modified image and reset crop state
        self._crop_accepted = False
        self._display_crop_image()

        # Disable Next until crop is accepted
        self.wizard._next_btn.configure(state="disabled")

    def _on_modification_error(self, error: str) -> None:
        """Handle modification error."""
        self._image_status.configure(text=f"Error: {error[:50]}...", fg="#ff5555")
        self._modify_btn.configure(state="normal")

    def _on_reset_to_normalized(self) -> None:
        """Reset to the normalized image (undo modifications)."""
        if self._normalized_image is None:
            return

        # Reset to normalized image
        self._crop_original_img = self._normalized_image.copy()
        self._crop_accepted = False

        # Update display
        self._display_crop_image()

        # Hide reset button
        self._reset_to_normalized_btn.pack_forget()

        self._image_status.configure(text="Reset to normalized image.", fg=ACCENT_COLOR)
        self.wizard._next_btn.configure(state="disabled")

    def validate(self) -> bool:
        if not self._voice_var.get():
            messagebox.showerror("Missing Voice", "Please select a voice (Girl or Boy).")
            return False

        if not self._arch_var.get():
            messagebox.showerror("Missing Archetype", "Please select an archetype.")
            return False

        if self.state.source_mode == "prompt":
            concept = self._concept_text.get("1.0", "end").strip()
            if not concept:
                messagebox.showerror(
                    "Missing Description",
                    "Please describe the character you want to create."
                )
                return False
            self.state.concept_text = concept

            # For prompt mode, require generated image
            if self._generated_image is None:
                messagebox.showerror(
                    "No Character Generated",
                    "Please click 'Generate Character' before continuing."
                )
                return False

            # Store the (possibly cropped) image for next steps
            self.state.generated_character_image = self._crop_original_img

            # Save to temp file for generation steps
            self._save_cropped_image_for_generation()

        # Save data
        self.state.voice = self._voice_var.get()
        self.state.display_name = self._name_var.get().strip() or pick_random_name(
            self.state.voice, self._girl_names, self._boy_names
        )
        self.state.archetype_label = self._arch_var.get()

        # For image mode, store the (possibly cropped) image
        if self.state.source_mode == "image" and self._crop_original_img is not None:
            self.state.source_image = self._crop_original_img
            # Save to temp file for generation steps
            self._save_cropped_image_for_generation()

        return True

    def _save_cropped_image_for_generation(self) -> None:
        """Save the cropped image to a temp path for generation steps."""
        if self._crop_original_img is None:
            return

        import tempfile
        import os

        # Create temp directory if needed
        temp_dir = Path(tempfile.gettempdir()) / "sprite_creator"
        temp_dir.mkdir(exist_ok=True)

        # Save cropped image
        temp_path = temp_dir / f"cropped_{id(self)}.png"
        self._crop_original_img.save(temp_path, format="PNG")
        self.state.cropped_image_path = temp_path


# =============================================================================
# Step 3: Generation Options
# =============================================================================

class OptionsStep(WizardStep):
    """Step 3: Select outfits and expressions to generate."""

    STEP_ID = "options"
    STEP_TITLE = "Options"
    STEP_HELP = """Generation Options

This step selects which outfits and expressions to generate.

INCLUDE BASE IMAGE AS OUTFIT?
Choose whether your original character image (with its current outfit) should be included as one of the final outfits.
- Yes: The base image becomes the "Base" outfit
- No: Only generated outfits are included

OUTFITS (Left Column)
Check the box next to each outfit type you want to generate.

Available types: Casual, Formal, Athletic, Swimsuit, Underwear, Uniform

For each outfit, choose a generation mode:

Random Mode
The AI generates a unique outfit description based on the character's archetype. Each generation produces different results.

Custom Mode
You write the outfit description. A text box appears where you can describe exactly what you want (e.g., "red sundress with white polka dots").

Standard Mode (Uniform only)
Only available for Young Woman/Man archetypes. Uses reference images to generate a consistent school uniform style.

Note: Underwear uses a tiered fallback system due to content filtering. If one description is blocked, the system tries progressively safer alternatives.

CUSTOM OUTFITS
Click "+ Add Custom Outfit" to create additional outfit types with your own name and description. Maximum 15 total outfits.

EXPRESSIONS (Right Column)
Check which expressions to generate for each outfit.

Expression 0 (neutral) is always included. Standard expressions:
1-Happy, 2-Sad, 3-Angry, 4-Surprised, 5-Disgusted, 6-Afraid, 7-Shy, 8-Smug, 9-Embarrassed, 10-Pout, 11-Loving, 12-Determined

CUSTOM EXPRESSIONS
Click "+ Add Custom Expression" to add your own expressions with a description. The system auto-assigns the next available number.

PERFORMANCE NOTE
More outfits and expressions = longer generation time. Each outfit generates all selected expressions, so 6 outfits x 12 expressions = 72 images.

Click Next when you've made your selections."""

    MAX_OUTFITS = 15
    MAX_EXPRESSIONS = 30

    def __init__(self, wizard, state: WizardState):
        super().__init__(wizard, state)
        self._outfit_vars: Dict[str, tk.IntVar] = {}
        self._outfit_mode_vars: Dict[str, tk.StringVar] = {}
        self._outfit_entries: Dict[str, tk.Entry] = {}
        self._expr_vars: Dict[str, tk.IntVar] = {}
        self._uniform_standard_rb: Optional[ttk.Radiobutton] = None
        self._uniform_row: Optional[tk.Frame] = None  # Track uniform row for hiding

        # Base outfit option
        self._use_base_as_outfit_var: Optional[tk.IntVar] = None

        # Custom outfit/expression tracking
        self._custom_outfits: List[Dict] = []  # [{frame, name_entry, desc_entry}]
        self._custom_expressions: List[Dict] = []  # [{frame, key_entry, desc_entry}]
        self._custom_outfits_frame: Optional[tk.Frame] = None
        self._custom_expressions_frame: Optional[tk.Frame] = None
        self._add_outfit_btn: Optional[tk.Button] = None
        self._add_expression_btn: Optional[tk.Button] = None
        self._outfit_scroll_frame: Optional[tk.Frame] = None
        self._expr_inner_frame: Optional[tk.Frame] = None

    def build_ui(self, parent: tk.Frame) -> None:
        parent.configure(bg=BG_COLOR)

        # Title
        tk.Label(
            parent,
            text="Generation Options",
            bg=BG_COLOR,
            fg=TEXT_COLOR,
            font=PAGE_TITLE_FONT,
        ).pack(pady=(0, 16))

        # Two-column layout
        columns = tk.Frame(parent, bg=BG_COLOR)
        columns.pack(fill="both", expand=True)

        # Left column: Outfits
        left_col = tk.Frame(columns, bg=BG_COLOR)
        left_col.pack(side="left", fill="both", expand=True, padx=(0, 10))

        # Include Base Image as Outfit? - highlighted frame
        base_outfit_frame = tk.Frame(left_col, bg=CARD_BG, padx=12, pady=10,
                                     highlightbackground=ACCENT_COLOR, highlightthickness=2)
        base_outfit_frame.pack(fill="x", pady=(0, 12))

        tk.Label(
            base_outfit_frame,
            text="Include Base Image as Outfit?",
            bg=CARD_BG,
            fg=ACCENT_COLOR,
            font=SECTION_FONT,
        ).pack(anchor="w")

        tk.Label(
            base_outfit_frame,
            text="Include the base character image as one of the outfits?",
            bg=CARD_BG,
            fg=TEXT_SECONDARY,
            font=SMALL_FONT,
        ).pack(anchor="w", pady=(2, 6))

        # Yes/No radio buttons
        self._use_base_as_outfit_var = tk.IntVar(value=1)  # Default to Yes
        base_option_btns = tk.Frame(base_outfit_frame, bg=CARD_BG)
        base_option_btns.pack(anchor="w")

        tk.Radiobutton(
            base_option_btns,
            text="Yes - Include as 'Base' outfit",
            variable=self._use_base_as_outfit_var,
            value=1,
            bg=CARD_BG,
            fg=TEXT_COLOR,
            selectcolor=BG_COLOR,
            activebackground=CARD_BG,
            activeforeground=TEXT_COLOR,
            font=BODY_FONT,
        ).pack(side="left", padx=(0, 16))

        tk.Radiobutton(
            base_option_btns,
            text="No - Do not include",
            variable=self._use_base_as_outfit_var,
            value=0,
            bg=CARD_BG,
            fg=TEXT_COLOR,
            selectcolor=BG_COLOR,
            activebackground=CARD_BG,
            activeforeground=TEXT_COLOR,
            font=BODY_FONT,
        ).pack(side="left")

        tk.Label(
            left_col,
            text="Outfits",
            bg=BG_COLOR,
            fg=TEXT_COLOR,
            font=SECTION_FONT,
        ).pack(anchor="w", pady=(0, 8))

        tk.Label(
            left_col,
            text="Select additional outfits to generate",
            bg=BG_COLOR,
            fg=TEXT_SECONDARY,
            font=SMALL_FONT,
        ).pack(anchor="w", pady=(0, 8))

        # Outfit checkboxes with mode selection
        self._outfit_scroll_frame = tk.Frame(left_col, bg=BG_COLOR)
        self._outfit_scroll_frame.pack(fill="both", expand=True)

        for key in ALL_OUTFIT_KEYS:
            self._build_outfit_row(self._outfit_scroll_frame, key)

        # Container for custom outfits
        self._custom_outfits_frame = tk.Frame(self._outfit_scroll_frame, bg=BG_COLOR)
        self._custom_outfits_frame.pack(fill="x", pady=(8, 0))

        # Add custom outfit button
        self._add_outfit_btn = create_secondary_button(
            self._outfit_scroll_frame,
            "+ Add Custom Outfit",
            self._add_custom_outfit,
            width=18,
        )
        self._add_outfit_btn.pack(anchor="w", pady=(8, 0))

        # Right column: Expressions
        right_col = tk.Frame(columns, bg=BG_COLOR)
        right_col.pack(side="left", fill="both", expand=True, padx=(10, 0))

        tk.Label(
            right_col,
            text="Expressions",
            bg=BG_COLOR,
            fg=TEXT_COLOR,
            font=SECTION_FONT,
        ).pack(anchor="w", pady=(0, 8))

        tk.Label(
            right_col,
            text="Neutral (0) is always included",
            bg=BG_COLOR,
            fg=TEXT_SECONDARY,
            font=SMALL_FONT,
        ).pack(anchor="w", pady=(0, 8))

        # Expression checkboxes in scrollable frame
        expr_canvas = tk.Canvas(right_col, bg=BG_COLOR, highlightthickness=0, height=300)
        expr_scrollbar = ttk.Scrollbar(right_col, orient="vertical", command=expr_canvas.yview)
        expr_inner = tk.Frame(expr_canvas, bg=BG_COLOR)

        expr_inner.bind(
            "<Configure>",
            lambda e: expr_canvas.configure(scrollregion=expr_canvas.bbox("all"))
        )
        expr_canvas.create_window((0, 0), window=expr_inner, anchor="nw")
        expr_canvas.configure(yscrollcommand=expr_scrollbar.set)

        expr_canvas.pack(side="left", fill="both", expand=True)
        expr_scrollbar.pack(side="right", fill="y")

        self._expr_inner_frame = expr_inner  # Save reference

        for key, desc in EXPRESSIONS_SEQUENCE:
            if key == "0":
                tk.Label(
                    expr_inner,
                    text=f"0 - {desc} (always)",
                    bg=BG_COLOR,
                    fg=TEXT_SECONDARY,
                    font=SMALL_FONT,
                ).pack(anchor="w", pady=2)
            else:
                var = tk.IntVar(value=1)
                self._expr_vars[key] = var
                chk = ttk.Checkbutton(
                    expr_inner,
                    text=f"{key} - {desc}",
                    variable=var,
                    style="Dark.TCheckbutton",
                )
                chk.pack(anchor="w", pady=2)

        # Container for custom expressions
        self._custom_expressions_frame = tk.Frame(expr_inner, bg=BG_COLOR)
        self._custom_expressions_frame.pack(fill="x", pady=(8, 0))

        # Add custom expression button
        self._add_expression_btn = create_secondary_button(
            expr_inner,
            "+ Add Custom Expression",
            self._add_custom_expression,
            width=20,
        )
        self._add_expression_btn.pack(anchor="w", pady=(8, 0))

    def _build_outfit_row(self, parent: tk.Frame, key: str) -> None:
        """Build a single outfit row with checkbox and mode selection."""
        row = tk.Frame(parent, bg=BG_COLOR)
        row.pack(fill="x", pady=(4, 2))

        # Add separator after each outfit row for visual grouping
        sep = ttk.Separator(parent, orient="horizontal")
        sep.pack(fill="x", pady=(2, 4), padx=(0, 50))

        # Track uniform row for conditional hiding
        if key == "uniform":
            self._uniform_row = row

        # Checkbox
        var = tk.IntVar(value=1 if key in OUTFIT_KEYS else 0)
        self._outfit_vars[key] = var

        chk = ttk.Checkbutton(
            row,
            text=key.capitalize(),
            variable=var,
            style="Dark.TCheckbutton",
            width=10,
        )
        chk.pack(side="left")

        # Mode selection (Random/Custom)
        mode_var = tk.StringVar(value="random")
        self._outfit_mode_vars[key] = mode_var

        mode_frame = tk.Frame(row, bg=BG_COLOR)
        mode_frame.pack(side="left", padx=(8, 0))

        rb_random = ttk.Radiobutton(
            mode_frame,
            text="Random",
            variable=mode_var,
            value="random",
        )
        rb_random.pack(side="left")

        rb_custom = ttk.Radiobutton(
            mode_frame,
            text="Custom",
            variable=mode_var,
            value="custom",
        )
        rb_custom.pack(side="left", padx=(8, 0))

        # Standard uniform option (only for uniform key)
        if key == "uniform":
            self._uniform_standard_rb = ttk.Radiobutton(
                mode_frame,
                text="Standard",
                variable=mode_var,
                value="standard_uniform",
            )
            # Will be packed/unpacked based on archetype

        # Custom prompt entry (only shown when custom mode is selected)
        entry = tk.Entry(
            row,
            width=30,
            bg="#1E1E1E",
            fg=TEXT_COLOR,
            insertbackground=TEXT_COLOR,
            font=SMALL_FONT,
        )
        # Don't pack initially - will be shown/hidden based on mode
        self._outfit_entries[key] = entry

        # Show/hide entry based on mode and checkbox
        def update_entry_visibility(*args):
            if var.get() == 1 and mode_var.get() == "custom":
                entry.pack(side="left", padx=(8, 0))
            else:
                entry.pack_forget()

        var.trace_add("write", update_entry_visibility)
        mode_var.trace_add("write", update_entry_visibility)

    def _get_total_outfit_count(self) -> int:
        """Get total number of selected + custom outfits."""
        selected = sum(1 for v in self._outfit_vars.values() if v.get() == 1)
        return selected + len(self._custom_outfits)

    def _get_total_expression_count(self) -> int:
        """Get total number of selected + custom expressions."""
        selected = 1  # Neutral is always included
        selected += sum(1 for v in self._expr_vars.values() if v.get() == 1)
        return selected + len(self._custom_expressions)

    def _update_add_buttons(self) -> None:
        """Update add button states based on current counts."""
        if self._add_outfit_btn:
            if self._get_total_outfit_count() >= self.MAX_OUTFITS:
                self._add_outfit_btn.configure(state="disabled")
            else:
                self._add_outfit_btn.configure(state="normal")

        if self._add_expression_btn:
            if self._get_total_expression_count() >= self.MAX_EXPRESSIONS:
                self._add_expression_btn.configure(state="disabled")
            else:
                self._add_expression_btn.configure(state="normal")

    def _add_custom_outfit(self) -> None:
        """Add a new custom outfit entry."""
        if self._get_total_outfit_count() >= self.MAX_OUTFITS:
            messagebox.showwarning("Limit Reached", f"Maximum {self.MAX_OUTFITS} outfits allowed.")
            return

        row = tk.Frame(self._custom_outfits_frame, bg=BG_COLOR)
        row.pack(fill="x", pady=2)

        # Name entry
        tk.Label(row, text="Name:", bg=BG_COLOR, fg=TEXT_SECONDARY, font=SMALL_FONT).pack(side="left")
        name_entry = tk.Entry(row, width=12, bg="#1E1E1E", fg=TEXT_COLOR, font=SMALL_FONT)
        name_entry.pack(side="left", padx=(4, 8))

        # Description entry
        tk.Label(row, text="Description:", bg=BG_COLOR, fg=TEXT_SECONDARY, font=SMALL_FONT).pack(side="left")
        desc_entry = tk.Entry(row, width=25, bg="#1E1E1E", fg=TEXT_COLOR, font=SMALL_FONT)
        desc_entry.pack(side="left", padx=(4, 8))

        # Remove button
        entry_data = {"frame": row, "name_entry": name_entry, "desc_entry": desc_entry}
        remove_btn = create_secondary_button(
            row, "-", lambda d=entry_data: self._remove_custom_outfit(d), width=3
        )
        remove_btn.pack(side="left")

        self._custom_outfits.append(entry_data)
        self._update_add_buttons()

    def _remove_custom_outfit(self, entry_data: Dict) -> None:
        """Remove a custom outfit entry."""
        if entry_data in self._custom_outfits:
            self._custom_outfits.remove(entry_data)
            entry_data["frame"].destroy()
            self._update_add_buttons()

    def _add_custom_expression(self) -> None:
        """Add a new custom expression entry with auto-incremented key."""
        if self._get_total_expression_count() >= self.MAX_EXPRESSIONS:
            messagebox.showwarning("Limit Reached", f"Maximum {self.MAX_EXPRESSIONS} expressions allowed.")
            return

        # Calculate next available key (auto-increment from highest used key)
        used_keys = set()
        for key, _ in EXPRESSIONS_SEQUENCE:
            try:
                used_keys.add(int(key))
            except ValueError:
                pass
        for entry_data in self._custom_expressions:
            k = entry_data["key_entry"].get().strip()
            if k:
                try:
                    used_keys.add(int(k))
                except ValueError:
                    pass

        # Find next number starting from 13 (after standard expressions)
        next_key = 13
        while next_key in used_keys:
            next_key += 1

        row = tk.Frame(self._custom_expressions_frame, bg=BG_COLOR)
        row.pack(fill="x", pady=2)

        # Key label (read-only, auto-assigned)
        tk.Label(row, text=f"Key: {next_key}", bg=BG_COLOR, fg=ACCENT_COLOR, font=SMALL_FONT).pack(side="left")

        # Hidden entry to store the key value
        key_entry = tk.Entry(row, width=4)
        key_entry.insert(0, str(next_key))
        # Don't pack - just store the value

        # Description entry
        tk.Label(row, text="Description:", bg=BG_COLOR, fg=TEXT_SECONDARY, font=SMALL_FONT).pack(side="left", padx=(8, 0))
        desc_entry = tk.Entry(row, width=30, bg="#1E1E1E", fg=TEXT_COLOR, font=SMALL_FONT)
        desc_entry.pack(side="left", padx=(4, 8))
        desc_entry.focus_set()

        # Remove button
        entry_data = {"frame": row, "key_entry": key_entry, "desc_entry": desc_entry}
        remove_btn = create_secondary_button(
            row, "-", lambda d=entry_data: self._remove_custom_expression(d), width=3
        )
        remove_btn.pack(side="left")

        self._custom_expressions.append(entry_data)
        self._update_add_buttons()

    def _remove_custom_expression(self, entry_data: Dict) -> None:
        """Remove a custom expression entry."""
        if entry_data in self._custom_expressions:
            self._custom_expressions.remove(entry_data)
            entry_data["frame"].destroy()
            self._update_add_buttons()

    def on_enter(self) -> None:
        """Prepare options step based on archetype."""
        # Show/hide uniform row and standard option based on archetype
        arch_lower = self.state.archetype_label.lower()
        uniform_eligible = (
            (arch_lower == "young woman" and self.state.gender_style == "f")
            or (arch_lower == "young man" and self.state.gender_style == "m")
        )

        # Hide entire uniform row for non-eligible archetypes
        if self._uniform_row:
            if uniform_eligible:
                self._uniform_row.pack(fill="x", pady=4)
            else:
                self._uniform_row.pack_forget()
                # Uncheck uniform if it was selected
                if "uniform" in self._outfit_vars:
                    self._outfit_vars["uniform"].set(0)

        if self._uniform_standard_rb:
            if uniform_eligible:
                self._uniform_standard_rb.pack(side="left", padx=(8, 0))
            else:
                self._uniform_standard_rb.pack_forget()
                # Reset to random if was on standard
                if self._outfit_mode_vars.get("uniform", tk.StringVar()).get() == "standard_uniform":
                    self._outfit_mode_vars["uniform"].set("random")

        # Update add button states
        self._update_add_buttons()

    def validate(self) -> bool:
        # Build selected outfits and config
        selected = []
        config = {}

        for key in ALL_OUTFIT_KEYS:
            if self._outfit_vars[key].get() == 1:
                selected.append(key)
                mode = self._outfit_mode_vars[key].get()

                use_random = mode in ("random", "standard_uniform")
                custom_prompt = None
                use_standard = mode == "standard_uniform"

                if mode == "custom":
                    custom_prompt = self._outfit_entries[key].get().strip()
                    if not custom_prompt:
                        messagebox.showerror(
                            "Missing Custom Prompt",
                            f"Please enter a custom prompt for {key.capitalize()}, "
                            f"or switch to Random mode."
                        )
                        return False

                config[key] = {
                    "use_random": use_random,
                    "custom_prompt": custom_prompt,
                    "use_standard_uniform": use_standard,
                }

        # Add custom outfits
        for entry_data in self._custom_outfits:
            name = entry_data["name_entry"].get().strip()
            desc = entry_data["desc_entry"].get().strip()
            if not name:
                messagebox.showerror("Missing Name", "Please enter a name for all custom outfits.")
                return False
            if not desc:
                messagebox.showerror("Missing Description", f"Please enter a description for custom outfit '{name}'.")
                return False

            # Use sanitized name as key
            key = f"custom_{name.lower().replace(' ', '_')}"
            selected.append(key)
            config[key] = {
                "use_random": False,
                "custom_prompt": desc,
                "use_standard_uniform": False,
            }

        # Build expression sequence
        expr_seq = [EXPRESSIONS_SEQUENCE[0]]  # Always include neutral
        for key, desc in EXPRESSIONS_SEQUENCE[1:]:
            if self._expr_vars.get(key, tk.IntVar(value=0)).get() == 1:
                expr_seq.append((key, desc))

        # Add custom expressions
        for entry_data in self._custom_expressions:
            key = entry_data["key_entry"].get().strip()
            desc = entry_data["desc_entry"].get().strip()
            if not key:
                messagebox.showerror("Missing Key", "Please enter a key (number) for all custom expressions.")
                return False
            if not desc:
                messagebox.showerror("Missing Description", f"Please enter a description for custom expression '{key}'.")
                return False
            expr_seq.append((key, desc))

        self.state.selected_outfits = selected
        self.state.outfit_prompt_config = config
        self.state.expressions_sequence = expr_seq

        # Save base outfit option
        self.state.use_base_as_outfit = bool(self._use_base_as_outfit_var.get())

        return True
