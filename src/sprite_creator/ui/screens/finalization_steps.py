"""
Finalization wizard steps (Steps 11-13).

These steps handle final character configuration:
- Step 11: Eye Line & Name Color picker
- Step 12: Scale Selector
- Step 13: Final Summary
"""

import os
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from typing import Optional, Dict

import yaml
from PIL import Image, ImageTk

from ...config import (
    BG_COLOR,
    CARD_BG,
    TEXT_COLOR,
    TEXT_SECONDARY,
    ACCENT_COLOR,
    PAGE_TITLE_FONT,
    SECTION_FONT,
    BODY_FONT,
    SMALL_FONT,
    REF_SPRITES_DIR,
)
from ..tk_common import (
    create_primary_button,
    create_secondary_button,
)
from .base import WizardStep, WizardState


# Line color for guides
LINE_COLOR = "#ff5555"


def compute_display_size(
    screen_w: int,
    screen_h: int,
    img_w: int,
    img_h: int,
    max_w_ratio: float = 0.60,
    max_h_ratio: float = 0.60,
) -> tuple:
    """Compute display dimensions that fit within screen ratios."""
    max_w = int(screen_w * max_w_ratio)
    max_h = int(screen_h * max_h_ratio)
    scale = min(max_w / img_w, max_h / img_h, 1.0)
    return max(1, int(img_w * scale)), max(1, int(img_h * scale))


class EyeLineStep(WizardStep):
    """
    Step 11: Eye Line & Name Color picker.

    Two-click interaction:
    1. Click to set eye line (horizontal guide)
    2. Click to pick name color from hair
    """

    STEP_ID = "eye_line"
    STEP_TITLE = "Finalize"
    STEP_HELP = """Eye Line & Name Color

This step sets two values used by visual novel engines.

STEP 1: EYE LINE
A red horizontal line follows your mouse. Click on the character's eyes to record the position.

What it's for:
The eye line ratio tells the engine where the character's eyes are. This is used to:
- Align multiple characters in conversation
- Position the character's head at a consistent height
- Adjust vertical positioning in dialogue scenes

How to set it:
Move your mouse until the red line is at eye level, then click. The line should pass through the center of both eyes.

After clicking, the step automatically advances to color picking.

STEP 2: NAME COLOR
A crosshair follows your mouse. Click on the character's hair to sample a color.

What it's for:
This color is used when the character's name appears in dialogue boxes. Picking a hair color creates visual consistency.

How to set it:
Click on the most prominent hair color. The sampled color appears in a preview box below.

Tips:
- Avoid clicking on highlights or shadows
- If you click a transparent area, a default brown is used
- You can click again to change the color

AFTER BOTH ARE SET
The status shows both values. Click Next to continue.

If you need to redo:
- You can click again to change the name color
- To redo the eye line, you'll need to go Back and return"""

    def __init__(self, wizard, state: WizardState):
        super().__init__(wizard, state)
        self._canvas: Optional[tk.Canvas] = None
        self._tk_img: Optional[ImageTk.PhotoImage] = None
        self._original_img: Optional[Image.Image] = None
        self._instruction_label: Optional[tk.Label] = None
        self._status_label: Optional[tk.Label] = None
        self._guide_line_id: Optional[int] = None
        self._reticle_h_id: Optional[int] = None
        self._reticle_v_id: Optional[int] = None
        self._disp_w: int = 0
        self._disp_h: int = 0
        self._scale_x: float = 1.0
        self._scale_y: float = 1.0
        self._step: int = 1  # 1=eye line, 2=name color
        self._color_preview: Optional[tk.Label] = None

    def build_ui(self, parent: tk.Frame) -> None:
        parent.configure(bg=BG_COLOR)

        # Title
        tk.Label(
            parent,
            text="Eye Line & Name Color",
            bg=BG_COLOR,
            fg=TEXT_COLOR,
            font=PAGE_TITLE_FONT,
        ).pack(pady=(0, 8))

        # Instructions
        self._instruction_label = tk.Label(
            parent,
            text="Step 1: Click on the character's eyes to set the eye line.",
            bg=BG_COLOR,
            fg=TEXT_SECONDARY,
            font=BODY_FONT,
            justify="center",
        )
        self._instruction_label.pack(pady=(0, 12))

        # Canvas container
        canvas_container = tk.Frame(parent, bg=CARD_BG, padx=4, pady=4)
        canvas_container.pack(expand=True)

        self._canvas = tk.Canvas(
            canvas_container,
            width=400,
            height=500,
            bg="black",
            highlightthickness=0,
        )
        self._canvas.pack()

        # Bind events
        self._canvas.bind("<Motion>", self._on_motion)
        self._canvas.bind("<Button-1>", self._on_click)

        # Bottom controls
        bottom_frame = tk.Frame(parent, bg=BG_COLOR)
        bottom_frame.pack(fill="x", pady=(12, 0))

        # Status and color preview
        status_row = tk.Frame(bottom_frame, bg=BG_COLOR)
        status_row.pack()

        self._status_label = tk.Label(
            status_row,
            text="",
            bg=BG_COLOR,
            fg=ACCENT_COLOR,
            font=BODY_FONT,
        )
        self._status_label.pack(side="left")

        self._color_preview = tk.Label(
            status_row,
            text="   ",
            width=4,
            height=1,
            bg=BG_COLOR,
            relief="solid",
            borderwidth=1,
        )
        # Hidden until color is selected

    def on_enter(self) -> None:
        """Load the character image when step becomes active."""
        # Find the best image to use (base pose or final outfit)
        image_path = None
        if self.state.base_pose_path and self.state.base_pose_path.exists():
            image_path = self.state.base_pose_path

        if not image_path:
            self._instruction_label.configure(
                text="No character image available.",
                fg="#ff5555",
            )
            return

        try:
            self._original_img = Image.open(image_path).convert("RGBA")
        except Exception as e:
            self._instruction_label.configure(
                text=f"Error loading image: {e}",
                fg="#ff5555",
            )
            return

        original_w, original_h = self._original_img.size

        # Get screen dimensions
        parent = self._canvas.winfo_toplevel()
        sw = parent.winfo_screenwidth()
        sh = parent.winfo_screenheight()

        # Compute display size (larger for better picking accuracy)
        self._disp_w, self._disp_h = compute_display_size(
            sw, sh, original_w, original_h,
            max_w_ratio=0.55, max_h_ratio=0.65
        )

        self._scale_x = original_w / max(1, self._disp_w)
        self._scale_y = original_h / max(1, self._disp_h)

        # Resize canvas
        self._canvas.configure(width=self._disp_w, height=self._disp_h)

        # Display image
        disp_img = self._original_img.resize((self._disp_w, self._disp_h), Image.LANCZOS)
        self._tk_img = ImageTk.PhotoImage(disp_img)
        self._canvas.delete("all")
        self._canvas.create_image(0, 0, anchor="nw", image=self._tk_img)

        # Reset state
        self._step = 1
        self._guide_line_id = None
        self._reticle_h_id = None
        self._reticle_v_id = None

        # Restore previous values if exists
        if self.state.eye_line_ratio is not None:
            disp_y = int(self.state.eye_line_ratio * self._disp_h)
            self._draw_eye_line(disp_y)
            self._step = 2
            self._instruction_label.configure(
                text="Step 2: Click on the hair to pick the name color."
            )

        if self.state.name_color:
            self._color_preview.configure(bg=self.state.name_color)
            self._color_preview.pack(side="left", padx=(8, 0))
            self._status_label.configure(
                text=f"Eye line: {self.state.eye_line_ratio:.3f}, Color: {self.state.name_color}"
            )

    def _draw_eye_line(self, y: int) -> None:
        """Draw horizontal eye line guide."""
        y = max(0, min(int(y), self._disp_h))
        if self._guide_line_id is None:
            self._guide_line_id = self._canvas.create_line(
                0, y, self._disp_w, y,
                fill=LINE_COLOR, width=3
            )
        else:
            self._canvas.coords(self._guide_line_id, 0, y, self._disp_w, y)

    def _clear_eye_line(self) -> None:
        """Clear the eye line guide."""
        if self._guide_line_id is not None:
            self._canvas.delete(self._guide_line_id)
            self._guide_line_id = None

    def _draw_reticle(self, x: int, y: int, arm: int = 16) -> None:
        """Draw crosshair reticle for color picking."""
        x = max(0, min(int(x), self._disp_w))
        y = max(0, min(int(y), self._disp_h))
        if self._reticle_h_id is None:
            self._reticle_h_id = self._canvas.create_line(
                x - arm, y, x + arm, y,
                fill=LINE_COLOR, width=2
            )
            self._reticle_v_id = self._canvas.create_line(
                x, y - arm, x, y + arm,
                fill=LINE_COLOR, width=2
            )
        else:
            self._canvas.coords(self._reticle_h_id, x - arm, y, x + arm, y)
            self._canvas.coords(self._reticle_v_id, x, y - arm, x, y + arm)

    def _clear_reticle(self) -> None:
        """Clear the reticle."""
        if self._reticle_h_id is not None:
            self._canvas.delete(self._reticle_h_id)
            self._canvas.delete(self._reticle_v_id)
            self._reticle_h_id = None
            self._reticle_v_id = None

    def _on_motion(self, event) -> None:
        """Handle mouse motion."""
        if self._original_img is None:
            return

        if self._step == 1:
            self._draw_eye_line(event.y)
        elif self._step == 2:
            self._draw_reticle(event.x, event.y)

    def _on_click(self, event) -> None:
        """Handle mouse click."""
        if self._original_img is None:
            return

        if self._step == 1:
            # Record eye line
            real_y = event.y * self._scale_y
            original_h = self._original_img.size[1]
            self.state.eye_line_ratio = real_y / original_h

            self._clear_eye_line()
            self._instruction_label.configure(
                text="Eye line recorded. Step 2: Click on the hair to pick the name color."
            )
            self._step = 2
            self._draw_reticle(event.x, event.y)
            self._status_label.configure(text=f"Eye line: {self.state.eye_line_ratio:.3f}")

        elif self._step == 2:
            # Record name color
            rx = min(max(int(event.x * self._scale_x), 0), self._original_img.size[0] - 1)
            ry = min(max(int(event.y * self._scale_y), 0), self._original_img.size[1] - 1)
            px = self._original_img.getpixel((rx, ry))

            # Check for transparent pixel
            if len(px) == 4 and px[3] < 10:
                color = "#915f40"  # Default brown
            else:
                color = f"#{px[0]:02x}{px[1]:02x}{px[2]:02x}"

            self.state.name_color = color
            self._clear_reticle()

            # Show color preview
            self._color_preview.configure(bg=color)
            self._color_preview.pack(side="left", padx=(8, 0))

            self._status_label.configure(
                text=f"Eye line: {self.state.eye_line_ratio:.3f}, Color: {color}"
            )
            self._instruction_label.configure(
                text="Done! Click 'Next' to continue, or click again to change the color."
            )

    def validate(self) -> bool:
        """Validate that both values are set."""
        if self.state.eye_line_ratio is None:
            messagebox.showerror("Missing Eye Line", "Please click on the character's eyes to set the eye line.")
            return False
        if not self.state.name_color:
            messagebox.showerror("Missing Name Color", "Please click on the hair to pick the name color.")
            return False
        return True


class ScaleStep(WizardStep):
    """
    Step 12: Scale Selector.

    Side-by-side comparison with reference sprites to set character scale.
    """

    STEP_ID = "scale"
    STEP_TITLE = "Scale"
    STEP_HELP = """Character Scale

This step sets how large your character appears in-game.

HOW IT WORKS
The left canvas shows a reference character at their defined scale.
The right canvas shows your character at the current slider value.

Both are rendered as they would appear in the game engine, anchored at the bottom (standing on the same ground).

REFERENCE DROPDOWN
Select a reference character to compare against. Choose one that matches your character's age/archetype for best results.

Reference characters have pre-defined scales in their .yml files.

SCALE SLIDER
Drag to adjust your character's scale:
- 1.0 = Original image size (no scaling)
- Below 1.0 = Character appears smaller
- Above 1.0 = Character appears larger

The red line on your character shows the eye line position (if set in the previous step). Use this to help match eye levels between characters.

RECOMMENDED APPROACH
1. Pick a reference character of similar type
2. Match the top of your character's head to the reference
3. Or match shoulder heights for more consistent framing
4. Fine-tune with the slider (0.01 increments)

COMMON VALUES
- 0.8 - 1.0: Typical for most characters
- 0.6 - 0.8: Shorter/younger characters
- 1.0 - 1.2: Taller characters

The exact value depends on your game's art style and existing characters.

Click Next when the scale looks right."""

    def __init__(self, wizard, state: WizardState):
        super().__init__(wizard, state)
        self._ref_canvas: Optional[tk.Canvas] = None
        self._user_canvas: Optional[tk.Canvas] = None
        self._scale_var: Optional[tk.DoubleVar] = None
        self._ref_var: Optional[tk.StringVar] = None
        self._references: Dict[str, dict] = {}
        self._user_img: Optional[Image.Image] = None
        self._img_refs: dict = {"ref": None, "usr": None}
        self._canv_w: int = 360
        self._canv_h: int = 360

    def build_ui(self, parent: tk.Frame) -> None:
        parent.configure(bg=BG_COLOR)

        # Title
        tk.Label(
            parent,
            text="Adjust Character Scale",
            bg=BG_COLOR,
            fg=TEXT_COLOR,
            font=PAGE_TITLE_FONT,
        ).pack(pady=(0, 8))

        # Instructions
        tk.Label(
            parent,
            text="1) Choose a reference (left). 2) Adjust your scale (right). 3) Click Next when done.",
            bg=BG_COLOR,
            fg=TEXT_SECONDARY,
            font=SMALL_FONT,
        ).pack(pady=(0, 12))

        # Reference selector
        ref_frame = tk.Frame(parent, bg=BG_COLOR)
        ref_frame.pack(pady=(0, 8))

        tk.Label(
            ref_frame,
            text="Reference:",
            bg=BG_COLOR,
            fg=TEXT_COLOR,
            font=BODY_FONT,
        ).pack(side="left", padx=(0, 8))

        self._ref_var = tk.StringVar(value="")
        self._ref_menu = tk.OptionMenu(ref_frame, self._ref_var, "")
        self._ref_menu.configure(width=20, bg=CARD_BG, fg=TEXT_COLOR)
        self._ref_menu.pack(side="left")

        # Canvas row
        canvas_frame = tk.Frame(parent, bg=BG_COLOR)
        canvas_frame.pack(fill="both", expand=True, pady=(8, 8))

        # Reference canvas (left)
        left_col = tk.Frame(canvas_frame, bg=BG_COLOR)
        left_col.pack(side="left", fill="both", expand=True, padx=(0, 8))

        tk.Label(
            left_col,
            text="Reference",
            bg=BG_COLOR,
            fg=TEXT_SECONDARY,
            font=SMALL_FONT,
        ).pack()

        self._ref_canvas = tk.Canvas(
            left_col,
            width=self._canv_w,
            height=self._canv_h,
            bg="black",
            highlightthickness=0,
        )
        self._ref_canvas.pack()

        # User canvas (right)
        right_col = tk.Frame(canvas_frame, bg=BG_COLOR)
        right_col.pack(side="left", fill="both", expand=True, padx=(8, 0))

        tk.Label(
            right_col,
            text="Your Character",
            bg=BG_COLOR,
            fg=TEXT_SECONDARY,
            font=SMALL_FONT,
        ).pack()

        self._user_canvas = tk.Canvas(
            right_col,
            width=self._canv_w,
            height=self._canv_h,
            bg="black",
            highlightthickness=0,
        )
        self._user_canvas.pack()

        # Scale slider
        self._scale_var = tk.DoubleVar(value=1.0)
        slider_frame = tk.Frame(parent, bg=BG_COLOR)
        slider_frame.pack(fill="x", pady=(8, 0))

        tk.Label(
            slider_frame,
            text="Scale:",
            bg=BG_COLOR,
            fg=TEXT_COLOR,
            font=BODY_FONT,
        ).pack(side="left", padx=(0, 8))

        self._scale_slider = tk.Scale(
            slider_frame,
            from_=0.1,
            to=2.5,
            resolution=0.01,
            orient=tk.HORIZONTAL,
            variable=self._scale_var,
            length=400,
            bg=BG_COLOR,
            fg=TEXT_COLOR,
            highlightthickness=0,
            command=lambda _: self._redraw(),
        )
        self._scale_slider.pack(side="left", fill="x", expand=True)

        # Scale value label
        self._scale_label = tk.Label(
            slider_frame,
            text="1.00",
            bg=BG_COLOR,
            fg=ACCENT_COLOR,
            font=BODY_FONT,
            width=6,
        )
        self._scale_label.pack(side="left", padx=(8, 0))

    def on_enter(self) -> None:
        """Load references and user image when step becomes active."""
        # Load reference sprites
        self._load_references()

        if not self._references:
            messagebox.showwarning(
                "No References",
                "No reference sprites found. You can still set a scale manually."
            )

        # Update dropdown
        menu = self._ref_menu["menu"]
        menu.delete(0, "end")
        names = sorted(self._references.keys())
        if names:
            self._ref_var.set(names[0])
            for name in names:
                menu.add_command(label=name, command=lambda n=name: self._on_ref_change(n))

        # Load user image
        image_path = self.state.base_pose_path
        if image_path and image_path.exists():
            try:
                self._user_img = Image.open(image_path).convert("RGBA")
            except Exception:
                self._user_img = None

        # Restore previous scale
        if self.state.scale_factor:
            self._scale_var.set(self.state.scale_factor)

        # Update canvas sizes based on screen (larger for better accuracy)
        parent = self._ref_canvas.winfo_toplevel()
        sw = parent.winfo_screenwidth()
        sh = parent.winfo_screenheight()
        self._canv_w = max(int((sw - 100) // 2.2), 350)
        self._canv_h = max(int(sh * 0.55), 350)

        self._ref_canvas.configure(width=self._canv_w, height=self._canv_h)
        self._user_canvas.configure(width=self._canv_w, height=self._canv_h)

        # Initial draw
        self._redraw()

    def _load_references(self) -> None:
        """Load reference sprites from directory."""
        self._references = {}

        if not REF_SPRITES_DIR.is_dir():
            return

        for fn in os.listdir(REF_SPRITES_DIR):
            if not fn.lower().endswith(".png"):
                continue

            name = os.path.splitext(fn)[0]
            img_path = REF_SPRITES_DIR / fn
            yml_path = REF_SPRITES_DIR / (name + ".yml")

            ref_scale = 1.0
            if yml_path.exists():
                try:
                    with yml_path.open("r", encoding="utf-8") as f:
                        meta = yaml.safe_load(f) or {}
                    ref_scale = float(meta.get("scale", 1.0))
                except Exception:
                    pass

            try:
                img = Image.open(img_path).convert("RGBA")
                self._references[name] = {"image": img, "scale": ref_scale}
            except Exception:
                pass

    def _on_ref_change(self, name: str) -> None:
        """Handle reference selection change."""
        self._ref_var.set(name)
        self._redraw()

    def _redraw(self, *args) -> None:
        """Redraw both canvases."""
        self._ref_canvas.delete("all")
        self._user_canvas.delete("all")

        current_scale = self._scale_var.get()
        self._scale_label.configure(text=f"{current_scale:.2f}")

        # Get reference
        ref_name = self._ref_var.get()
        if not ref_name or ref_name not in self._references:
            return

        r_meta = self._references[ref_name]
        rimg = r_meta["image"]
        r_scale = r_meta["scale"]

        # Calculate engine dimensions
        r_engine_w = rimg.width * r_scale
        r_engine_h = rimg.height * r_scale

        if self._user_img:
            u_engine_w = self._user_img.width * current_scale
            u_engine_h = self._user_img.height * current_scale
        else:
            u_engine_w = u_engine_h = 0

        # Calculate view scale to fit both in canvases
        max_w = max(r_engine_w, u_engine_w, 1)
        max_h = max(r_engine_h, u_engine_h, 1)
        view_scale = min(self._canv_w / max_w, self._canv_h / max_h, 1.0)

        # Draw reference
        r_disp_w = max(1, int(r_engine_w * view_scale))
        r_disp_h = max(1, int(r_engine_h * view_scale))
        r_resized = rimg.resize((r_disp_w, r_disp_h), Image.LANCZOS)
        self._img_refs["ref"] = ImageTk.PhotoImage(r_resized)
        self._ref_canvas.create_image(
            self._canv_w // 2, self._canv_h,
            anchor="s",
            image=self._img_refs["ref"]
        )

        # Draw user
        if self._user_img:
            u_disp_w = max(1, int(u_engine_w * view_scale))
            u_disp_h = max(1, int(u_engine_h * view_scale))
            u_resized = self._user_img.resize((u_disp_w, u_disp_h), Image.LANCZOS)
            self._img_refs["usr"] = ImageTk.PhotoImage(u_resized)
            self._user_canvas.create_image(
                self._canv_w // 2, self._canv_h,
                anchor="s",
                image=self._img_refs["usr"]
            )

            # Draw eye line if available
            if self.state.eye_line_ratio is not None:
                img_top = self._canv_h - u_disp_h
                y_inside = int(u_disp_h * self.state.eye_line_ratio)
                y_canvas = img_top + y_inside
                self._user_canvas.create_line(
                    0, y_canvas, self._canv_w, y_canvas,
                    fill=LINE_COLOR, width=2
                )

    def validate(self) -> bool:
        """Save scale and validate."""
        self.state.scale_factor = float(self._scale_var.get())
        return True


class SummaryStep(WizardStep):
    """
    Step 13: Final Summary.

    Shows completion status and output location.
    """

    STEP_ID = "summary"
    STEP_TITLE = "Complete"
    STEP_HELP = """Character Complete!

Your character has been created and all files are saved.

FILES CREATED
Your character folder contains:

character.yml
Configuration file with name, voice, scale, eye line, and pose mappings. Used by visual novel engines to display the character correctly.

Pose Folders (a/, b/, etc.)
Each outfit becomes a "pose" folder containing:
- The outfit image
- A faces/ subfolder with all expressions

Expression Sheets
Automatically generated sprite sheets combining all expressions for each pose. These are optimized for game engines.

WHAT TO DO NEXT

Open Sprite Tester
Launches an interactive preview tool. You can:
- View all poses and expressions
- Test different backgrounds
- See how the character will look in-game

Open Output Folder
Opens the character folder in your file explorer. From here you can:
- Copy files to your game project
- Review individual images
- Make manual adjustments if needed

USING IN REN'PY
Copy the entire character folder to your game's images directory. The character.yml file contains all the metadata Ren'Py needs.

MAKING CHANGES
If you need to regenerate or modify anything, you'll need to run the wizard again. The existing character folder will be preserved (a new one is created with a unique name).

Click Finish to close the wizard."""

    def __init__(self, wizard, state: WizardState):
        super().__init__(wizard, state)
        self._summary_frame: Optional[tk.Frame] = None
        self._actions_frame: Optional[tk.Frame] = None

    def build_ui(self, parent: tk.Frame) -> None:
        parent.configure(bg=BG_COLOR)

        # Title
        tk.Label(
            parent,
            text="Character Creation Complete!",
            bg=BG_COLOR,
            fg=ACCENT_COLOR,
            font=PAGE_TITLE_FONT,
        ).pack(pady=(0, 24))

        # Success icon/message
        tk.Label(
            parent,
            text="✓",
            bg=BG_COLOR,
            fg="#44bb44",
            font=("", 48),
        ).pack()

        # Two-column layout
        content_frame = tk.Frame(parent, bg=BG_COLOR)
        content_frame.pack(fill="both", expand=True, padx=40, pady=(24, 0))

        # Left column - Summary info
        left_col = tk.Frame(content_frame, bg=BG_COLOR)
        left_col.pack(side="left", fill="both", expand=True, padx=(0, 16))

        self._summary_frame = tk.Frame(left_col, bg=CARD_BG, padx=24, pady=16)
        self._summary_frame.pack(fill="both", expand=True)

        # Right column - Action buttons
        right_col = tk.Frame(content_frame, bg=BG_COLOR)
        right_col.pack(side="right", fill="y", padx=(16, 0))

        self._actions_frame = tk.Frame(right_col, bg=CARD_BG, padx=24, pady=16)
        self._actions_frame.pack(fill="x")

    def on_enter(self) -> None:
        """Populate summary when step becomes active and finalize character."""
        # Perform finalization on entering this step
        self._finalize_character()

        # Clear existing summary content
        for widget in self._summary_frame.winfo_children():
            widget.destroy()

        # Clear existing action buttons
        for widget in self._actions_frame.winfo_children():
            widget.destroy()

        # === LEFT COLUMN: Summary Info ===
        tk.Label(
            self._summary_frame,
            text="Character Summary",
            bg=CARD_BG,
            fg=TEXT_COLOR,
            font=SECTION_FONT,
        ).pack(anchor="w", pady=(0, 12))

        # Character info
        self._add_row("Character Name:", self.state.display_name)
        self._add_row("Voice:", self.state.voice.capitalize())
        self._add_row("Archetype:", self.state.archetype_label)

        # Generation stats - use generated_outfit_keys for accurate count
        # (includes only outfits that succeeded, already includes base if applicable)
        outfit_count = len(self.state.generated_outfit_keys) if self.state.generated_outfit_keys else 0
        expr_count = len(self.state.expressions_sequence)
        self._add_row("Outfits Generated:", str(outfit_count))
        self._add_row("Expressions per Outfit:", str(expr_count))

        # Scale info
        if self.state.scale_factor:
            self._add_row("Scale:", f"{self.state.scale_factor:.2f}")

        # Name/Hair color with swatch
        if self.state.name_color:
            self._add_color_row("Name Color:", self.state.name_color)

        # Output location
        if self.state.character_folder:
            self._add_row("Output Folder:", str(self.state.character_folder))

        # Final message
        tk.Label(
            self._summary_frame,
            text="\nClick 'Finish' to close the wizard.",
            bg=CARD_BG,
            fg=TEXT_SECONDARY,
            font=BODY_FONT,
        ).pack(anchor="w", pady=(16, 0))

        # === RIGHT COLUMN: Action Buttons ===
        tk.Label(
            self._actions_frame,
            text="Actions",
            bg=CARD_BG,
            fg=TEXT_COLOR,
            font=SECTION_FONT,
        ).pack(anchor="w", pady=(0, 16))

        # Open Sprite Tester button
        create_primary_button(
            self._actions_frame,
            "Open Sprite Tester",
            self._open_sprite_tester,
            width=20,
        ).pack(pady=(0, 12))

        # Open Output Folder button
        create_secondary_button(
            self._actions_frame,
            "Open Output Folder",
            self._open_output_folder,
            width=20,
        ).pack(pady=(0, 8))

    def _add_row(self, label: str, value: str) -> None:
        """Add a summary row."""
        row = tk.Frame(self._summary_frame, bg=CARD_BG)
        row.pack(fill="x", pady=4)

        tk.Label(
            row,
            text=label,
            bg=CARD_BG,
            fg=TEXT_SECONDARY,
            font=SMALL_FONT,
            width=20,
            anchor="w",
        ).pack(side="left")

        tk.Label(
            row,
            text=value,
            bg=CARD_BG,
            fg=TEXT_COLOR,
            font=BODY_FONT,
            anchor="w",
        ).pack(side="left", fill="x", expand=True)

    def _add_color_row(self, label: str, color: str) -> None:
        """Add a summary row with a color swatch."""
        row = tk.Frame(self._summary_frame, bg=CARD_BG)
        row.pack(fill="x", pady=4)

        tk.Label(
            row,
            text=label,
            bg=CARD_BG,
            fg=TEXT_SECONDARY,
            font=SMALL_FONT,
            width=20,
            anchor="w",
        ).pack(side="left")

        # Color swatch
        swatch = tk.Label(
            row,
            text="   ",
            bg=color,
            width=3,
            relief="solid",
            borderwidth=1,
        )
        swatch.pack(side="left", padx=(0, 8))

        # Color hex value
        tk.Label(
            row,
            text=color,
            bg=CARD_BG,
            fg=TEXT_COLOR,
            font=BODY_FONT,
            anchor="w",
        ).pack(side="left")

    def _open_sprite_tester(self) -> None:
        """Launch the sprite tester for this character."""
        if not self.state.character_folder:
            messagebox.showerror("Error", "No character folder available.")
            return

        try:
            from ...tools.tester import launch_sprite_tester
            launch_sprite_tester(self.state.character_folder)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch sprite tester:\n{e}")

    def _open_output_folder(self) -> None:
        """Open the character output folder in the file explorer."""
        if not self.state.character_folder:
            messagebox.showerror("Error", "No character folder available.")
            return

        folder_path = self.state.character_folder
        if not folder_path.exists():
            messagebox.showerror("Error", f"Folder not found:\n{folder_path}")
            return

        try:
            import subprocess
            import platform

            if platform.system() == "Windows":
                os.startfile(str(folder_path))
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", str(folder_path)], check=False)
            else:  # Linux
                subprocess.run(["xdg-open", str(folder_path)], check=False)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open folder:\n{e}")

    def _finalize_character(self) -> None:
        """Finalize character: create character.yml and expression sheets."""
        from ...processing.pose_processor import flatten_pose_outfits_to_letter_poses, write_character_yml
        from ...processing import generate_expression_sheets_for_root

        if not self.state.character_folder:
            return

        char_dir = self.state.character_folder

        try:
            # Flatten pose/outfit combinations into letter poses
            print("[INFO] Flattening pose/outfit combinations into letter poses...")
            final_pose_letters = flatten_pose_outfits_to_letter_poses(char_dir)
            if not final_pose_letters:
                print("[WARN] Flattening produced no poses; using existing letter folders.")
                final_pose_letters = sorted(
                    [
                        p.name
                        for p in char_dir.iterdir()
                        if p.is_dir() and len(p.name) == 1 and p.name.isalpha()
                    ]
                )

            # Build poses yaml
            poses_yaml = {letter: {"facing": "right"} for letter in final_pose_letters}

            # Write character.yml with values from wizard state
            yml_path = char_dir / "character.yml"
            write_character_yml(
                yml_path,
                self.state.display_name,
                self.state.voice,
                self.state.eye_line_ratio or 0.3,
                self.state.name_color or "#915f40",
                self.state.scale_factor or 1.0,
                poses_yaml,
                game=None,
            )
            print(f"[INFO] Created character.yml for {self.state.display_name}")

            # Generate expression sheets
            generate_expression_sheets_for_root(char_dir)
            print(f"[INFO] Generated expression sheets for {self.state.display_name}")

        except Exception as e:
            print(f"[ERROR] Finalization error: {e}")
            import traceback
            traceback.print_exc()

    def validate(self) -> bool:
        """Always valid - just a summary screen."""
        return True
