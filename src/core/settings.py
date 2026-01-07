"""
Settings persistence module for WoodWay Converter.
Handles loading and saving user settings to local appdata.
"""

import os
import json
from pathlib import Path
from typing import Optional


def get_config_path() -> Path:
    """
    Get the path to the configuration file in local appdata.
    
    Returns:
        Path to config.json file
    """
    # Get local appdata directory
    if os.name == 'nt':  # Windows
        appdata = os.getenv('LOCALAPPDATA')
        if not appdata:
            # Fallback to user home directory
            appdata = os.path.expanduser('~')
    else:  # Linux/Mac
        appdata = os.path.expanduser('~/.local/share')
    
    # Create WoodWayConverter directory
    config_dir = Path(appdata) / 'WoodWayConverter'
    config_dir.mkdir(parents=True, exist_ok=True)
    
    return config_dir / 'config.json'


def load_gemini_key() -> Optional[str]:
    """
    Load Gemini API key from local appdata config file.
    
    Returns:
        API key string if found, None otherwise
    """
    config_path = get_config_path()
    
    if not config_path.exists():
        return None
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            return config.get('gemini_api_key')
    except (json.JSONDecodeError, IOError, KeyError):
        return None


def save_gemini_key(key: str) -> bool:
    """
    Save Gemini API key to local appdata config file.
    
    Args:
        key: The API key to save
        
    Returns:
        True if saved successfully, False otherwise
    """
    if not key or not key.strip():
        return False
    
    config_path = get_config_path()
    
    # Load existing config or create new
    config = {}
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except (json.JSONDecodeError, IOError):
            config = {}
    
    # Update API key
    config['gemini_api_key'] = key.strip()
    
    # Save to file
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        return True
    except IOError:
        return False


def has_gemini_key() -> bool:
    """
    Check if a Gemini API key is stored in settings.
    
    Returns:
        True if key exists, False otherwise
    """
    return load_gemini_key() is not None

