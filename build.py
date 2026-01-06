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


def check_ffmpeg() -> bool:
    """Check if FFmpeg is available."""
    return shutil.which("ffmpeg") is not None


def build_exe():
    """Build the executable using PyInstaller."""
    
    # Load environment variables from .env file
    from dotenv import load_dotenv
    load_dotenv()
    
    # Check for API key
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("WARNING: GEMINI_API_KEY not set. AI features will be disabled in the build.")
        print("Set it with: set GEMINI_API_KEY=your_key (Windows)")
        print("")
    else:
        print(f"[OK] Using API key from .env: {api_key[:20]}...{api_key[-4:]}")
        print("")
    
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
    
    # PyInstaller options
    options = pyinstaller_cmd + [
        '--name=WoodWayConverter',
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
    
    # Create a temporary spec file with the API key baked in
    if api_key:
        # Create a wrapper script that sets the key
        wrapper_content = f'''
import os
os.environ['GEMINI_API_KEY'] = '{api_key}'

from src.gui.app import run_app
run_app()
'''
        wrapper_path = root_dir / '_build_entry.py'
        wrapper_path.write_text(wrapper_content)
        
        # Update options to use wrapper
        options[-1] = str(wrapper_path)
    
    print("Building executable...")
    print(f"Command: {' '.join(options)}")
    
    try:
        subprocess.run(options, check=True)
        print("\n[SUCCESS] Build successful!")
        print(f"Executable location: {root_dir / 'dist' / 'WoodWayConverter.exe'}")
        print("")
        print("=== Post-Build Notes ===")
        print("For VIDEO SUPPORT, users must have FFmpeg installed:")
        print("  1. Download FFmpeg from https://ffmpeg.org/download.html")
        print("  2. Add FFmpeg to system PATH")
        print("  3. Restart the application")
        print("")
        print("Without FFmpeg, the application will work for images only.")
    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] Build failed with error: {e}")
        sys.exit(1)
    finally:
        # Clean up wrapper
        if api_key and wrapper_path.exists():
            wrapper_path.unlink()


if __name__ == '__main__':
    build_exe()

