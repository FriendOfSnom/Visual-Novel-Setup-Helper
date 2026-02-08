# Visual Novel Development Toolkit (v2.1.0)

A comprehensive, AI-powered toolkit for creating visual novels with Ren'Py. This suite provides everything needed to create professional VN projects: from project setup and AI character generation to expression sheet creation.

Perfect for game developers, writers, and creators who want to build accessible visual novels with custom character systems.

---

## Three-Tool Workflow

### **Tool 1: Ren'Py Project Scaffolder**

Creates production-ready Ren'Py projects with custom character support.

**What it does:**

-   Downloads Ren'Py SDK 8.5.0 automatically (if missing)
-   Launches official Ren'Py launcher for project creation
-   Injects custom character loading system
-   Adds support for dynamic character positioning and expressions
-   Optionally imports existing character folders
-   Moves project to your chosen location

**Custom Features Added to Projects:**

-   Auto-loads characters from `game/images/characters/` folder
-   Custom position transforms: `centerleft`, `centerright`, `faceleft`, `faceright`
-   Automatic character voice and color support
-   Dynamic outfit and expression swapping
-   Support for character metadata via `character.yml` files

---

### **Tool 2: AI Sprite Creator**

AI-powered character sprite generator using Google Gemini vision models. Features a guided 9-step wizard that walks you through the entire character creation process.

**Wizard Steps:**

1. **Source Selection** - Choose to create from an existing image or text prompt
2. **Character Setup** - Set name, voice, archetype, and crop/modify the base image
3. **Generation Options** - Select outfits (casual, formal, athletic, swimsuit, underwear, uniform) and expressions
4. **Review** - Confirm selections before generation begins
5. **Outfit Review** - Review generated outfits, adjust background removal, regenerate as needed
6. **Expression Review** - Review expressions for each outfit, touch up backgrounds
7. **Eye Line & Color** - Set eye position and pick name color from hair
8. **Scale** - Compare with reference sprites to set in-game scale
9. **Complete** - View summary and launch Sprite Tester

**Key Features:**

-   **Two creation modes**: Start from reference image or text description
-   **Smart background removal**: Automatic rembg processing with tolerance/depth sliders
-   **Manual touch-up**: Click-based flood fill for precise background cleanup
-   **Per-outfit regeneration**: Regenerate individual outfits without starting over
-   **Comprehensive help**: Built-in help button (?) on every step with detailed instructions
-   **Safety handling**: Graceful fallback when Gemini's content filters block certain generations

**Output Format:**

```
character_name/
├── character.yml          # Metadata (voice, scale, eye line, colors)
├── a/                     # Pose folder (one per outfit)
│   ├── a.png              # Outfit image
│   └── faces/
│       └── face/
│           ├── 0.png      # Neutral
│           ├── 1.png      # Happy
│           ├── 2.png      # Sad
│           └── ...        # Additional expressions
├── b/                     # Second outfit pose
│   └── ...
└── expression_sheets/     # Generated sprite sheets for reference
```

**Integration:**
Characters created with Tool 2 are automatically compatible with projects created by Tool 1. Simply copy character folders to `game/images/characters/` and they'll load automatically!

---

### **Tool 3: Visual Scene Editor** (Planned)

A complete GUI-based scene editor for writing visual novels without code.

**What it will do:**

-   Live preview window showing the current scene in real-time
-   Drag-and-drop character positioning on screen
-   Visual selectors for expressions, outfits, backgrounds, and sounds
-   Dialogue editor with character selection dropdown
-   Automatic expression sheet generation and display
-   Preset position buttons (left, centerleft, center, centerright, right)
-   Flip controls (faceleft, faceright)
-   Transition selector for character entrances/exits
-   Forward/back arrows to navigate scene timeline (undo/redo)
-   "Next" button to generate and append Ren'Py code to script.rpy

**Vision:**
This tool will enable non-programmers to create complete visual novels using an intuitive GUI interface, automatically generating proper Ren'Py script code behind the scenes.

---

## Quick Start

### First-Time Setup

#### 1. Install Python Dependencies

```bash
# Windows
start-windows.bat

# macOS
./start-mac.command
```

This will create a virtual environment and install all required packages.

#### 2. Download Ren'Py SDK (Required for Tool 1)

The toolkit will prompt you to download the SDK when you first run Tool 1. Alternatively, you can download it manually:

```bash
python download_renpy_sdk.py
```

This downloads Ren'Py SDK 8.5.0 (~150 MB) to the toolkit folder.

---

## Requirements

-   **Python 3.10 or higher**
-   **Google Gemini API Key** (for Tool 2 - Character Creator)
    -   Get your free API key at: https://aistudio.google.com/apikey
    -   Set environment variable: `GEMINI_API_KEY=your_key_here`

### Python Dependencies

Installed automatically via launcher scripts:

```
google-generativeai
pillow>=10.3
pyyaml
requests
beautifulsoup4
pandas
rembg              # Required for automatic background removal
onnxruntime        # Required by rembg for ML model inference
```

---

## Usage

### Running the Toolkit

**Windows:**

```bash
start-windows.bat
```

**macOS:**

```bash
./start-mac.command
```

This launches the main menu where you can select:

1. **Create new Ren'Py project** (Tool 1 - Project Scaffolder)
2. **Create new character sprites** (Tool 2 - AI Sprite Creator)
3. **Generate expression sheets** (Utility tool)
   Q. Quit

**Note:** Tool 3 (Visual Scene Editor) is planned for future implementation.

**Getting Help:**
Every step in the AI Sprite Creator has a **?** button in the footer. Click it to see detailed instructions for that step, including what each control does and how to use it effectively.

---

## Workflow Example

### Creating a Complete Visual Novel Project

1. **Run Tool 1: Create a New Project**

    - Select option 1 from the menu
    - SDK downloads automatically (if not present)
    - Ren'Py launcher opens
    - Create your project with a name, resolution, and theme
    - Close Ren'Py when done
    - Browse to your project location (or let it stay in SDK/projects/)
    - Character system is automatically injected!

2. **Run Tool 2: Create Characters**

    - Select option 2 from the menu
    - Choose output folder (e.g., Desktop or project's `game/images/characters/`)
    - Follow the 9-step wizard:
      - Select source (image upload or text prompt)
      - Set character name, voice, and archetype
      - Choose which outfits and expressions to generate
      - Review and accept your selections
      - Review generated outfits (adjust backgrounds, regenerate if needed)
      - Review expressions for each outfit
      - Set eye line and name color
      - Adjust scale relative to reference sprites
    - Character folder is automatically created with all files

3. **Copy Characters to Project** (if needed)

    - If you didn't save directly to the project, copy character folders to:
      `YourProject/game/images/characters/`

4. **Generate Expression Sheets** (optional)

    - Select option 3 from the menu
    - Choose the folder containing your character folders
    - Expression sheets are generated for reference

5. **Write Your Story**

    - Option A: Use Tool 3 (Visual Scene Editor) when available - GUI-based scene creation
    - Option B: Edit script.rpy manually in your preferred text editor

6. **Launch Your Project in Ren'Py**
    - Open Ren'Py SDK
    - Select your project
    - Click "Launch Project"
    - Characters are automatically loaded and ready to use!

### Using Characters in Your Script

```renpy
label start:
    scene bg room

    # Show character with outfit and expression
    show alice casual happy at centerright
    alice "Hello! Nice to meet you!"

    # Change expression
    show alice casual sad
    alice "I'm feeling a bit down today..."

    # Flip character to face left
    show alice at faceleft
    alice "Looking this way!"

    # Change outfit
    show alice uniform neutral at centerleft
    alice "Ready for school!"
```

---

## Running Your Game

### Method 1: Using Ren'Py SDK Launcher (Recommended)

1. **Open the Ren'Py SDK:**

    - Navigate to: `renpy-8.5.0-sdk/`
    - Windows: Double-click `renpy.exe`
    - Mac/Linux: Run `./renpy.sh`

2. **Select Your Project:**

    - Your project will appear in the left panel
    - Click on your project name to select it

3. **Launch the Game:**
    - Click the **"Launch Project"** button
    - Your game will start in a new window

### During Development

**Testing Changes:**

-   Save your script file
-   Press **Shift+R** in the running game to reload
-   Or restart the game from the SDK launcher

**Common Shortcuts in Game:**

-   `Shift+R` - Reload game (after script changes)
-   `Shift+D` - Developer menu
-   `Shift+O` - Console
-   `Esc` - Main menu

### Building for Distribution

Once your game is complete:

1. Open Ren'Py SDK
2. Select your project
3. Click **"Build Distributions"**
4. Select platforms (Windows, Mac, Linux, etc.)
5. Click "Build"

This creates standalone executables in `YourProject-dists/` that players can run without Ren'Py.

---

## Project Structure

```
Visual-Novel-Development-Toolkit/
├── src/                           # Source code
│   ├── main.py                    # Main launcher (menu system)
│   │
│   ├── renpy_scaffolder/          # Tool 1: Project Scaffolder
│   │   ├── scaffolder.py          # Main scaffolder logic
│   │   ├── sdk_downloader.py      # SDK download helper
│   │   └── templates/             # Character system template files
│   │       ├── character.py       # Character loading system
│   │       ├── body.py            # Body/Pose/Expression classes
│   │       ├── char_sprites.py    # Person/Ghost sprite classes
│   │       ├── pymage_size.py     # Image utilities
│   │       └── effects.rpy        # Custom transforms & animations
│   │
│   ├── sprite_creator/            # Tool 2: AI Sprite Creator
│   │   ├── __main__.py            # Entry point for standalone mode
│   │   ├── config.py              # Configuration and constants
│   │   ├── api/                   # Gemini API integration
│   │   │   ├── gemini_client.py   # API calls, background removal
│   │   │   └── prompt_builders.py # Prompt generation for outfits/expressions
│   │   ├── core/                  # Core data models
│   │   │   └── models.py          # WizardState and data classes
│   │   ├── processing/            # Image processing workflows
│   │   │   ├── pose_processor.py  # Outfit generation
│   │   │   ├── expression_generator.py  # Expression generation
│   │   │   └── character_finalizer.py   # Final file creation
│   │   ├── ui/                    # Tkinter UI components
│   │   │   ├── full_wizard.py     # Main wizard window
│   │   │   ├── screens/           # Individual wizard steps
│   │   │   ├── tk_common.py       # Shared UI components
│   │   │   └── review_windows.py  # Manual BG removal tool
│   │   ├── tools/                 # Sub-tools
│   │   │   └── tester/            # Sprite Tester preview tool
│   │   └── data/                  # Data files
│   │       ├── names.csv          # Name pools for random generation
│   │       └── reference_sprites/ # Reference characters for scaling
│   │
│   └── vn_writer/                 # Tool 3: VN Writer (Scene Editor)
│       └── editor.py              # Visual scene editor (planned)
│
├── renpy-8.5.0-sdk/               # Ren'Py SDK (downloaded automatically)
├── requirements.txt               # Python dependencies
├── start-windows.bat              # Windows launcher
├── start-mac.command              # macOS launcher
└── README.md                      # This file
```

---

## Academic Use

This toolkit was developed as a graduation project to make visual novel development more accessible. It demonstrates:

-   **AI Integration**: Leveraging Google Gemini for creative asset generation
-   **Automated Workflows**: Streamlining game development pipelines
-   **Accessibility**: Enabling non-programmers to create professional VNs
-   **Modular Architecture**: Clean separation of tools and responsibilities

**Perfect for:**

-   Computer Science capstone projects
-   Game development portfolios
-   Independent VN creators
-   Accessibility technology research

---

## Advanced Configuration

### Character System Features

Projects created with Tool 1 include a powerful character system:

**Position Transforms:**

-   `left`, `centerleft`, `center`, `centerright`, `right` - Screen positions
-   `faceleft`, `faceright` - Flip character sprites horizontally

**Character Methods (in script.rpy):**

```python
# Access character objects
alice.outfit = "uniform"           # Change outfit
alice.add_accessory("glasses")     # Add accessory
alice.remove_accessory("hat")      # Remove accessory
```

**Character YAML Format:**

```yaml
display_name: "Alice"
name_color: "#ff69b4"
scale: 0.85
voice: "girl"
eye_line: 0.42
default_outfit: "casual"
```

---

## Troubleshooting

### "Ren'Py SDK not found!"

-   Run Tool 1 and select "Yes" when prompted to download the SDK
-   Or manually run: `python download_renpy_sdk.py`

### "GEMINI_API_KEY not set"

-   Get your API key from https://aistudio.google.com/apikey
-   Set environment variable before running:

    ```bash
    # Windows (CMD)
    set GEMINI_API_KEY=your_key_here

    # Windows (PowerShell)
    $env:GEMINI_API_KEY="your_key_here"

    # macOS/Linux
    export GEMINI_API_KEY=your_key_here
    ```

### Characters not loading in game

-   Verify folder structure matches Tool 2 output format
-   Check that characters are in `game/images/characters/`
-   Ensure `character.yml` exists in character folder
-   Launch game and check console for error messages

### Tkinter errors on macOS

-   Ensure you're using Homebrew Python (not system Python)
-   The `start-mac.command` script handles this automatically

### Outfit or expression generation blocked

-   Gemini's safety filters may block certain content
-   The wizard will skip blocked items and continue with others
-   Try regenerating with "Regen New Outfit" for a different style
-   Custom prompts are more likely to be blocked than random ones
-   Underwear uses a tiered fallback system automatically

### Background removal looks wrong

-   Adjust Tolerance slider: higher values remove more aggressively
-   Adjust Depth slider: higher values clean edges more thoroughly
-   Switch to Manual mode for precise click-based removal
-   Use "Touch Up BG" on expression review for fine adjustments

### Help button shows ? but no text

-   Click the ? button in the wizard footer to see step-specific help
-   Each step has detailed instructions for all controls
-   Scroll within the help modal to see full content

### Next button is disabled

-   On Character step: Fill in Voice, Name, and Archetype, then click "Accept Crop"
-   On Review step: Check the acknowledgment box if warning is shown
-   On Expression Review: Navigate through all outfits (Prev/Next) before continuing
-   During generation: Wait for the loading screen to complete

### Where are the log files?

-   Logs are saved to `logs/sprite_creator.log` next to the executable (or project root in development)
-   The log file is wiped on each restart
-   Useful for debugging issues - include log contents when reporting bugs

---

## Changelog

### v2.1.0 (Current Release)

**Complete Wizard Redesign:**
-   New 9-step guided wizard for character creation
-   Streamlined workflow: Source → Character → Options → Review → Outfits → Expressions → Eye Line → Scale → Complete
-   Comprehensive help system with detailed instructions on every step (click the ? button)
-   Image normalization and modification within the wizard (no separate tools needed)
-   Integrated crop tool in character setup step

**Launcher Improvements:**
-   API Settings button to configure Gemini API key
-   View API Usage button opens Google AI Studio dashboard in browser
-   Better error handling for API key validation

**Required Fields Validation:**
-   Voice, Name, and Archetype now required before proceeding on Character step
-   Accept Crop and Generate buttons disabled until all fields are filled
-   Clear tip messages guide users to complete required fields first

**Safety & Content Handling:**
-   Age enforcement in image normalization (characters appear 18+)
-   Warning system for content that may trigger Gemini's safety filters
-   Acknowledgment checkbox for custom outfits, underwear, and custom expressions
-   Graceful skipping when content is blocked (wizard continues with successful items)
-   Removed unreliable "Regen Same Outfit" button for underwear

**Outfit System Overhaul:**
-   Added **underwear** as a new outfit option for all character archetypes
-   Multi-tier fallback system for sensitive content:
    -   Tier 0-4 progressively safer descriptions when filters block content
    -   Athletic wear alternatives as final fallback
-   Random, Custom, and Standard (uniform only) generation modes
-   Custom outfit support with user-defined names and descriptions
-   ST Style toggle: Enable/disable Student Transfer style references

**Background Removal Improvements:**
-   Tolerance (0-150) and Depth (0-50) sliders for fine-tuned edge cleanup
-   Per-outfit background mode selection (auto vs manual)
-   Manual mode: Click-based flood fill with adjustable threshold
-   Touch Up BG / Remove BG buttons on expression review
-   Background preview dropdown (Black/White/Game backgrounds)
-   Fixed manual BG removal not saving/displaying correctly

**Expression Generation:**
-   Must review all outfits before proceeding (prevents missed issues)
-   Per-expression regeneration
-   Expression 0 (neutral) uses outfit directly (not regeneratable)
-   Custom expression support with auto-assigned numbers

**Finalization:**
-   Eye line picker with visual guide (for dialogue positioning)
-   Eye line now spans both reference and user canvases for easier comparison
-   Name color picker (samples from hair)
-   Side-by-side scale comparison with 77 reference sprites from Student Transfer
-   **Apply scale to images** checkbox: Optionally resize all images on disk (saves space)
-   Automatic character.yml and expression sheet generation

**Error Handling & Debugging:**
-   Copyable error messages with "Copy to Clipboard" button
-   File-based logging to `logs/sprite_creator.log` (next to .exe or project root)
-   Log file wipes on each restart for clean debugging
-   Uncaught exceptions logged automatically

**UI/UX Polish:**
-   Help modal scroll fix (no longer scrolls content behind on outfit/expression steps)
-   Larger help modal (500x450) for better readability
-   State preservation for slider positions between regenerations
-   Loading screens during API operations
-   Disabled navigation buttons during generation
-   Consistent orange (💡) tip styling across all wizard pages
-   Prominent help buttons (?) on all wizard steps

**Bug Fixes:**
-   API Setup dialog now works properly from launcher (threading fix)
-   Finish button now opens character folder and closes app
-   Fixed navigation crash when going back from Complete step
-   Fixed Sprite Tester folder creation on first run

**Code Cleanup:**
-   Removed dead code (PromptGenerationStep, unused prompt builders)
-   Centralized WizardState in core/models.py
-   Cleaner module organization
-   Added logging_utils module for structured logging

### v2.0.0

-   **Complete toolkit redesign** for academic use
-   **Tool 1: Ren'Py Project Scaffolder** - Create projects with custom character system
-   **Tool 2: Gemini Character Creator** - AI-powered sprite generation
-   **Tool 3: Visual Scene Editor** - Planned GUI-based scene creation tool
-   Expression sheet generator utility
-   Removed all project-specific references
-   Automatic Ren'Py SDK download and setup
-   Integrated workflow across all tools
-   Clean, production-ready character system injection
-   Updated to Ren'Py 8.5.0
-   Comprehensive documentation and examples

### v1.1.1 (Legacy)

-   Original sprite pipeline with 5-step workflow
-   Manual sorting and organization tools
-   Bulk downscaler with gamma-aware processing
-   Expression sheet improvements

### v1.0.0 (Legacy)

-   Initial release of sprite pipeline tool

---

## License

This toolkit is provided as-is for educational and personal use.

## Contributing

This is a graduation project, but feedback and suggestions are welcome! Please open an issue on GitHub with any bugs, feature requests, or questions.

---

**Developed as a graduation project in Computer Science**
_Making visual novel development accessible to everyone_
