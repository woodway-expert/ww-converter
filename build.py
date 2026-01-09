"""
Build script for creating WoodWay Image & Video Converter executable.
Uses PyInstaller to create a standalone .exe file.

Usage:
    1. Set GEMINI_API_KEY environment variable
    2. Ensure FFmpeg is installed (for video support)
    3. Run: python build.py

FFmpeg Installation:
    - Windows: Download from https://ffmpeg.org/download.html and add to PATH
    - Or use: winget install ffmpeg
    - Or use: choco install ffmpeg
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

# Import version from src package
try:
    from src import __version__
    VERSION = __version__
except ImportError:
    VERSION = "1.0.0"  # Fallback version


def check_ffmpeg() -> bool:
    """Check if FFmpeg is available."""
    return shutil.which("ffmpeg") is not None


def build_exe():
    """Build the executable using PyInstaller."""
    
    # Check for FFmpeg
    if check_ffmpeg():
        ffmpeg_path = shutil.which("ffmpeg")
        print(f"[OK] FFmpeg found: {ffmpeg_path}")
        print("     Video conversion will be available.")
        print("")
    else:
        print("WARNING: FFmpeg not found in PATH.")
        print("     Video conversion will NOT be available in the built application.")
        print("     Install FFmpeg: https://ffmpeg.org/download.html")
        print("")
    
    # Get the root directory
    root_dir = Path(__file__).parent
    
    # Find PyInstaller in the virtual environment
    venv_pyinstaller = root_dir / 'venv' / 'Scripts' / 'pyinstaller.exe'
    if not venv_pyinstaller.exists():
        # Try using python -m PyInstaller as fallback
        pyinstaller_cmd = [sys.executable, '-m', 'PyInstaller']
    else:
        pyinstaller_cmd = [str(venv_pyinstaller)]
    
    # Build executable name with version
    exe_name = f'WoodWayConverter-{VERSION}'
    
    # PyInstaller options
    options = pyinstaller_cmd + [
        f'--name={exe_name}',
        '--onefile',
        '--windowed',  # No console window
        '--noconfirm',  # Overwrite without asking
        f'--add-data={root_dir / "src" / "data" / "categories.json"};src/data',
        f'--add-data={root_dir / "assets" / "icon.png"};assets' if (root_dir / "assets" / "icon.png").exists() else '',
        f'--add-data={root_dir / "assets" / "icon.ico"};assets' if (root_dir / "assets" / "icon.ico").exists() else '',
        f'--icon={root_dir / "assets" / "icon.ico"}' if (root_dir / "assets" / "icon.ico").exists() else '',
        # Hidden imports for PIL and CustomTkinter
        '--hidden-import=PIL._tkinter_finder',
        '--hidden-import=customtkinter',
        '--collect-all=customtkinter',
        # tkinterdnd2 for drag-and-drop support
        '--hidden-import=tkinterdnd2',
        '--collect-all=tkinterdnd2',
        # Google GenAI
        '--hidden-import=google.genai',
        '--collect-submodules=google.genai',
        str(root_dir / 'src' / 'main.py'),
    ]
    
    # Remove empty options
    options = [opt for opt in options if opt]
    
    print("Building executable...")
    print(f"Command: {' '.join(options)}")
    
    try:
        subprocess.run(options, check=True)
        print("\n[SUCCESS] Build successful!")
        print(f"Executable location: {root_dir / 'dist' / f'{exe_name}.exe'}")
        print("")
        print("=== Post-Build Notes ===")
        print("For VIDEO SUPPORT, users must have FFmpeg installed:")
        print("  1. Download FFmpeg from https://ffmpeg.org/download.html")
        print("  2. Add FFmpeg to system PATH")
        print("  3. Restart the application")
        print("")
        print("Without FFmpeg, the application will work for images only.")
        print("")
        print("NOTE: Users can configure their Gemini API key in the application settings.")
    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] Build failed with error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    build_exe()

