"""
Gemini API client for sprite generation.

Handles authentication, API calls, retries, and response parsing for Google Gemini.
"""

import base64
import json
import os
import webbrowser
from io import BytesIO
from pathlib import Path
from typing import List, Optional

import requests
from PIL import Image

from ..constants import CONFIG_PATH, GEMINI_API_URL


# =============================================================================
# Configuration Management
# =============================================================================

def load_config() -> dict:
    """
    Load configuration from ~/.st_gemini_config.json if present.

    Returns:
        Dictionary containing configuration, or empty dict if not found.
    """
    if CONFIG_PATH.is_file():
        try:
            with CONFIG_PATH.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_config(config: dict) -> None:
    """
    Save configuration dictionary to CONFIG_PATH.

    Sets file permissions to 0o600 for security (API keys).

    Args:
        config: Configuration dictionary to save.
    """
    CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")
    try:
        os.chmod(CONFIG_PATH, 0o600)
    except Exception:
        pass  # Permissions may not be supported on all platforms


def interactive_api_key_setup() -> str:
    """
    Prompt user for Gemini API key and save it to config.

    Opens browser to API key page and prompts for input.

    Returns:
        The API key entered by the user.

    Raises:
        SystemExit: If no API key is entered.
    """
    print("\nIt looks like you haven't configured a Gemini API key yet.")
    print("To use Google Gemini's image model, we need an API key.")
    print("I will open the Gemini API key page in your browser.")
    input("Press Enter to open the Gemini API key page in your browser...")

    key_page_url = "https://aistudio.google.com/app/apikey"
    try:
        webbrowser.open(key_page_url)
    except Exception as e:
        print(f"Warning: could not open browser automatically: {e}")
        print(f"Please open this URL manually in your browser: {key_page_url}")

    api_key = input("\nPaste your Gemini API key here and press Enter:\n> ").strip()
    if not api_key:
        raise SystemExit("No API key entered. Please rerun the script when you have a key.")

    config = load_config()
    config["api_key"] = api_key
    save_config(config)
    print(f"Saved API key to {CONFIG_PATH}.")
    return api_key


def get_api_key() -> str:
    """
    Return Gemini API key from environment variable or config file.

    Checks GEMINI_API_KEY environment variable first, then config file.
    If neither exists, prompts user interactively.

    Returns:
        Valid Gemini API key.
    """
    # Check environment variable first
    env_key = os.environ.get("GEMINI_API_KEY")
    if env_key:
        return env_key

    # Check config file
    config = load_config()
    if config.get("api_key"):
        return config["api_key"]

    # Interactive setup if neither exists
    return interactive_api_key_setup()


# =============================================================================
# Image Utilities
# =============================================================================

def load_image_as_base64(path: Path) -> str:
    """
    Load image from disk, re-encode as PNG, return base64 string.

    Ensures consistent format for Gemini API regardless of source format.

    Args:
        path: Path to image file.

    Returns:
        Base64-encoded PNG image data.
    """
    img = Image.open(path).convert("RGBA")
    buffer = BytesIO()
    img.save(buffer, format="PNG", compress_level=0, optimize=False)
    raw_bytes = buffer.getvalue()
    return base64.b64encode(raw_bytes).decode("utf-8")


def _extract_inline_image_from_response(data: dict) -> Optional[bytes]:
    """
    Extract the first inline image bytes from a Gemini JSON response.

    Handles both 'inlineData' and 'inline_data' field naming.

    Args:
        data: Parsed JSON response from Gemini API.

    Returns:
        Decoded image bytes, or None if no image found.
    """
    candidates = data.get("candidates", [])
    for candidate in candidates:
        content = candidate.get("content", {})
        for part in content.get("parts", []):
            # Handle both naming conventions
            blob = part.get("inlineData") or part.get("inline_data")
            if blob and "data" in blob:
                return base64.b64decode(blob["data"])
    return None


# =============================================================================
# Background Removal (ML-Based)
# =============================================================================

def strip_background(image_bytes: bytes) -> bytes:
    """
    Strip a flat-ish magenta background.
    Strategy:
      1) Load RGBA.
      2) Collect all opaque border pixels.
      3) Estimate background color as the average of those border pixels.
      4) Clear any pixel sufficiently close to that background color.
    """
    BG_CLEAR_THRESH = 56  # tweak this if it's too aggressive or too gentle

    try:
        img = Image.open(BytesIO(image_bytes)).convert("RGBA")
        w, h = img.size
        pixels = img.load()

        border_samples = []

        # top and bottom rows
        for x in range(w):
            for y in (0, h - 1):
                r, g, b, a = pixels[x, y]
                if a <= 0:
                    continue
                border_samples.append((r, g, b))

        # left and right columns
        for y in range(h):
            for x in (0, w - 1):
                r, g, b, a = pixels[x, y]
                if a <= 0:
                    continue
                border_samples.append((r, g, b))

        if not border_samples:
            # Nothing to go on; just return original
            return image_bytes

        n = float(len(border_samples))
        bg_r = sum(r for r, _, _ in border_samples) / n
        bg_g = sum(g for _, g, _ in border_samples) / n
        bg_b = sum(b for _, _, b in border_samples) / n

        bg_clear_thresh_sq = BG_CLEAR_THRESH * BG_CLEAR_THRESH

        def is_bg(r, g, b):
            dr = r - bg_r
            dg = g - bg_g
            db = b - bg_b
            return (dr * dr + dg * dg + db * db) <= bg_clear_thresh_sq

        out = Image.new("RGBA", (w, h))
        out_pixels = out.load()

        for y in range(h):
            for x in range(w):
                r, g, b, a = pixels[x, y]
                if a <= 0:
                    out_pixels[x, y] = (r, g, b, 0)
                elif is_bg(r, g, b):
                    out_pixels[x, y] = (r, g, b, 0)
                else:
                    out_pixels[x, y] = (r, g, b, a)

        buf = BytesIO()
        out.save(buf, format="PNG", compress_level=0, optimize=False)
        return buf.getvalue()

    except Exception as e:
        print(f"  [WARN] strip_background failed, returning original bytes: {e}")
        return image_bytes


# =============================================================================
# Gemini API Calls
# =============================================================================

def _call_gemini_with_parts(
    api_key: str,
    parts: List[dict],
    context: str,
    strip_bg: bool = True,
) -> bytes:
    """
    Call Gemini API with custom parts array and retry logic.

    Handles retries for transient errors (429, 500, 502, 503, 504).
    Optionally strips background from returned image.

    Args:
        api_key: Google Gemini API key.
        parts: List of content parts (text, images, etc.).
        context: Description of the operation for error messages.
        strip_bg: Whether to strip background (True for automatic mode, False for manual mode).

    Returns:
        Image bytes, optionally with background stripped.

    Raises:
        RuntimeError: If API call fails after all retries.
    """
    payload = {"contents": [{"parts": parts}]}
    headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}
    max_retries = 3
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(
                GEMINI_API_URL,
                headers=headers,
                data=json.dumps(payload)
            )

            # Handle retryable errors
            if not response.ok:
                if response.status_code in (429, 500, 502, 503, 504) and attempt < max_retries:
                    print(
                        f"[WARN] Gemini API error {response.status_code} ({context}) "
                        f"attempt {attempt}; retrying..."
                    )
                    last_error = f"Gemini API error {response.status_code}: {response.text}"
                    continue
                raise RuntimeError(f"Gemini API error {response.status_code}: {response.text}")

            data = response.json()
            raw_bytes = _extract_inline_image_from_response(data)

            if raw_bytes is not None:
                # Only strip background if in automatic mode
                if strip_bg:
                    return strip_background(raw_bytes)
                else:
                    return raw_bytes

            # Log the full response to diagnose why there's no image
            print(f"[DEBUG] Gemini response without image data:")
            print(f"[DEBUG] Full response: {json.dumps(data, indent=2)}")

            last_error = f"No image data in Gemini response ({context})."
            if attempt < max_retries:
                print(
                    f"[WARN] Gemini response missing image ({context}) "
                    f"attempt {attempt}; retrying..."
                )
                continue
            raise RuntimeError(last_error)

        except Exception as e:
            last_error = str(e)
            if attempt < max_retries:
                print(
                    f"[WARN] Gemini call failed ({context}) "
                    f"attempt {attempt}; retrying: {e}"
                )
                continue
            raise RuntimeError(
                f"Gemini call failed after {max_retries} attempts ({context}): {last_error}"
            )


def call_gemini_image_edit(api_key: str, prompt: str, image_b64: str, strip_bg: bool = True) -> bytes:
    """
    Call Gemini image model with an input image and text prompt for editing.

    Args:
        api_key: Google Gemini API key.
        prompt: Text prompt describing the desired edit.
        image_b64: Base64-encoded input image.
        strip_bg: Whether to strip background (True for automatic mode, False for manual mode).

    Returns:
        Generated/edited image bytes.
    """
    parts: List[dict] = [
        {"text": prompt},
        {"inline_data": {"mime_type": "image/png", "data": image_b64}},
    ]
    return _call_gemini_with_parts(api_key, parts, "image_edit", strip_bg)


def call_gemini_text_or_refs(
    api_key: str,
    prompt: str,
    ref_images: Optional[List[Path]] = None,
    strip_bg: bool = True,
) -> bytes:
    """
    Call Gemini with a text prompt and optional reference images.

    Used for generating new characters from text descriptions with
    style references.

    Args:
        api_key: Google Gemini API key.
        prompt: Text prompt describing what to generate.
        ref_images: Optional list of reference image paths for style guidance.
        strip_bg: Whether to strip background (True for automatic mode, False for manual mode).

    Returns:
        Generated image bytes.
    """
    parts: List[dict] = [{"text": prompt}]

    # Add reference images if provided
    if ref_images:
        for ref_path in ref_images:
            try:
                ref_b64 = load_image_as_base64(ref_path)
                parts.append({
                    "inline_data": {"mime_type": "image/png", "data": ref_b64}
                })
            except Exception as e:
                print(f"[WARN] Could not load reference image {ref_path}: {e}")

    return _call_gemini_with_parts(api_key, parts, "text_or_refs", strip_bg)
