"""
SDK Download Utilities for Sprite Tester

Provides functions to download and extract the Ren'Py SDK when not present.
Extracted from src/renpy_scaffolder/sdk_downloader.py for self-containment.
"""

import os
import platform
import shutil
import sys
import tarfile
import zipfile
from pathlib import Path
from urllib.request import urlretrieve

# Ren'Py SDK configuration
SDK_VERSION = "8.5.0"
SDK_FOLDER_NAME = f"renpy-{SDK_VERSION}-sdk"

# Platform-specific download URLs
SDK_URLS = {
    "Windows": "https://www.renpy.org/dl/8.5.0/renpy-8.5.0-sdk.zip",
    "Darwin": "https://www.renpy.org/dl/8.5.0/renpy-8.5.0-sdk.tar.bz2",  # macOS
    "Linux": "https://www.renpy.org/dl/8.5.0/renpy-8.5.0-sdk.tar.bz2",
}


def get_platform() -> str | None:
    """Detect the current platform. Returns None if unsupported."""
    system = platform.system()
    if system in SDK_URLS:
        return system
    print(f"[ERROR] Unsupported platform: {system}")
    print("Supported platforms: Windows, macOS (Darwin), Linux")
    return None


def show_progress(block_num: int, block_size: int, total_size: int) -> None:
    """Display download progress to stdout."""
    downloaded = block_num * block_size
    if total_size > 0:
        percent = min(downloaded * 100 / total_size, 100)
        bar_length = 50
        filled = int(bar_length * percent / 100)
        bar = '=' * filled + '-' * (bar_length - filled)

        size_mb = total_size / (1024 * 1024)
        downloaded_mb = downloaded / (1024 * 1024)

        sys.stdout.write(f'\r[{bar}] {percent:.1f}% ({downloaded_mb:.1f}/{size_mb:.1f} MB)')
        sys.stdout.flush()


def download_sdk(url: str, output_path: Path) -> bool:
    """
    Download the SDK from the given URL.

    Args:
        url: The download URL
        output_path: Where to save the downloaded file

    Returns:
        True if successful, False otherwise
    """
    print(f"[INFO] Downloading Ren'Py SDK {SDK_VERSION}...")
    print(f"[INFO] URL: {url}")
    print(f"[INFO] Destination: {output_path}\n")

    try:
        urlretrieve(str(url), str(output_path), reporthook=show_progress)
        print("\n[INFO] Download complete!")
        return True
    except Exception as e:
        print(f"\n[ERROR] Download failed: {e}")
        return False


def extract_zip(zip_path: Path, extract_to: Path) -> bool:
    """Extract a ZIP file with progress."""
    print(f"\n[INFO] Extracting ZIP archive...")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            members = zip_ref.namelist()
            total = len(members)

            for i, member in enumerate(members):
                zip_ref.extract(member, extract_to)
                percent = (i + 1) * 100 / total
                sys.stdout.write(f'\rExtracting: {percent:.1f}% ({i + 1}/{total} files)')
                sys.stdout.flush()

        print("\n[INFO] Extraction complete!")
        return True
    except Exception as e:
        print(f"\n[ERROR] Extraction failed: {e}")
        return False


def extract_tar(tar_path: Path, extract_to: Path) -> bool:
    """Extract a TAR.BZ2 file with progress."""
    print(f"\n[INFO] Extracting TAR.BZ2 archive...")
    try:
        with tarfile.open(tar_path, 'r:bz2') as tar_ref:
            members = tar_ref.getmembers()
            total = len(members)

            for i, member in enumerate(members):
                tar_ref.extract(member, extract_to)
                percent = (i + 1) * 100 / total
                sys.stdout.write(f'\rExtracting: {percent:.1f}% ({i + 1}/{total} files)')
                sys.stdout.flush()

        print("\n[INFO] Extraction complete!")
        return True
    except Exception as e:
        print(f"\n[ERROR] Extraction failed: {e}")
        return False


def verify_sdk(sdk_path: Path) -> bool:
    """
    Verify that the SDK was extracted correctly.

    Args:
        sdk_path: Path to the extracted SDK folder

    Returns:
        True if verification passes, False otherwise
    """
    print(f"\n[INFO] Verifying SDK installation...")

    required_items = ["renpy.py", "launcher"]
    missing = [item for item in required_items if not (sdk_path / item).exists()]

    if missing:
        print(f"[WARN] Some expected files/folders are missing: {', '.join(missing)}")
        return False

    print("[INFO] SDK verification passed!")
    return True


def download_and_setup_sdk(install_dir: Path) -> bool:
    """
    Download and set up the Ren'Py SDK.

    This is the main entry point for SDK installation.

    Args:
        install_dir: Where to install the SDK (e.g., PROJECT_ROOT/renpy-8.5.0-sdk)

    Returns:
        True if successful, False otherwise
    """
    # Get platform
    platform_name = get_platform()
    if not platform_name:
        return False

    print(f"[INFO] Detected platform: {platform_name}")

    # Get download URL and file extension
    download_url = SDK_URLS[platform_name]
    file_extension = ".zip" if platform_name == "Windows" else ".tar.bz2"
    download_filename = f"renpy-{SDK_VERSION}-sdk{file_extension}"

    # The parent directory where we'll extract (SDK folder goes inside)
    parent_dir = install_dir.parent
    download_path = parent_dir / download_filename

    # Ensure parent directory exists
    try:
        parent_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"[ERROR] Could not create SDK parent directory {parent_dir}: {e}")
        return False

    # Check if SDK already exists
    if install_dir.exists():
        print(f"[INFO] SDK already exists at {install_dir}")
        return True

    # Download
    if not download_sdk(download_url, download_path):
        return False

    # Extract
    if file_extension == ".zip":
        success = extract_zip(download_path, parent_dir)
    else:
        success = extract_tar(download_path, parent_dir)

    if not success:
        return False

    # Verify
    if not verify_sdk(install_dir):
        print("\n[WARN] SDK verification failed, but extraction completed")
        # Continue anyway - might still work

    # Cleanup downloaded archive
    print(f"\n[INFO] Cleaning up downloaded archive...")
    try:
        download_path.unlink()
        print(f"[INFO] Deleted: {download_filename}")
    except Exception as e:
        print(f"[WARN] Could not delete archive: {e}")

    print("\n[INFO] Ren'Py SDK setup complete!")
    return True
