"""
XMB Settings persistence for Milk Toast Taco.

Separate from the game save system (core/systems/save/). Stores XMB-specific
preferences like fullscreen and theme in xmbsettings.xml at the project root
(gitignored).
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict

# Project root: core/renderer/main_menu/xmb_settings.py -> parents[3] -> MilkToastTaco/
PROJECT_ROOT = Path(__file__).resolve().parents[3]
SETTINGS_PATH = PROJECT_ROOT / "xmbsettings.xml"

# Available themes - id -> metadata
THEMES: Dict[str, Dict[str, str]] = {
    "default": {
        "name": "Default",
        "desc": "Classic deep-space blue",
        "bg": "#050914",
        "bg_gradient_to": "#0a1128",
        "wave1": "rgba(30, 80, 150, 0.15)",
        "wave2": "rgba(80, 30, 150, 0.1)",
    },
    "dark_purple": {
        "name": "Dark Purple",
        "desc": "Royal void with violet nebula",
        "bg": "#0d0514",
        "bg_gradient_to": "#1a0a2e",
        "wave1": "rgba(120, 40, 180, 0.18)",
        "wave2": "rgba(60, 20, 120, 0.12)",
    },
    "crimson_red": {
        "name": "Crimson Red",
        "desc": "Ember core with burning horizon",
        "bg": "#140505",
        "bg_gradient_to": "#2e0a0a",
        "wave1": "rgba(180, 30, 30, 0.16)",
        "wave2": "rgba(120, 20, 60, 0.12)",
    },
    "midnight_green": {
        "name": "Midnight Green",
        "desc": "Deep forest at midnight",
        "bg": "#05140a",
        "bg_gradient_to": "#0a2814",
        "wave1": "rgba(30, 150, 80, 0.14)",
        "wave2": "rgba(20, 100, 60, 0.11)",
    },
    "ocean_blue": {
        "name": "Ocean Blue",
        "desc": "Abyssal teal depths",
        "bg": "#05141a",
        "bg_gradient_to": "#0a2830",
        "wave1": "rgba(20, 140, 160, 0.16)",
        "wave2": "rgba(30, 80, 150, 0.11)",
    },
    "sunset_orange": {
        "name": "Sunset Orange",
        "desc": "Dusk ember over the horizon",
        "bg": "#140a05",
        "bg_gradient_to": "#2e1a0a",
        "wave1": "rgba(200, 90, 20, 0.15)",
        "wave2": "rgba(160, 40, 80, 0.11)",
    },
}

DEFAULT_SETTINGS = {
    "fullscreen": False,
    "theme": "default",
}

VALID_THEMES = set(THEMES.keys())


def load_settings(path: Path | str | None = None) -> Dict[str, object]:
    """Load XMB settings from XML. Returns defaults on missing/corrupt file."""
    settings = dict(DEFAULT_SETTINGS)
    file_path = Path(path) if path else SETTINGS_PATH
    if not file_path.exists():
        return settings
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        # Expect <xmb_settings><fullscreen>true</fullscreen><theme>dark_purple</theme></xmb_settings>
        fs_el = root.find("fullscreen")
        if fs_el is not None and fs_el.text is not None:
            val = fs_el.text.strip().lower()
            settings["fullscreen"] = val in ("true", "1", "yes", "on")
        theme_el = root.find("theme")
        if theme_el is not None and theme_el.text is not None:
            t = theme_el.text.strip()
            if t in VALID_THEMES:
                settings["theme"] = t
    except ET.ParseError:
        # corrupt -> return defaults
        pass
    except Exception:
        pass
    return settings


def save_settings(settings: Dict[str, object], path: Path | str | None = None) -> str:
    """Save XMB settings to XML. Returns path written."""
    file_path = Path(path) if path else SETTINGS_PATH
    # Validate/normalize
    fullscreen = bool(settings.get("fullscreen", DEFAULT_SETTINGS["fullscreen"]))
    theme = str(settings.get("theme", DEFAULT_SETTINGS["theme"]))
    if theme not in VALID_THEMES:
        theme = DEFAULT_SETTINGS["theme"]

    root = ET.Element("xmb_settings")
    fs_el = ET.SubElement(root, "fullscreen")
    fs_el.text = "true" if fullscreen else "false"
    theme_el = ET.SubElement(root, "theme")
    theme_el.text = theme

    ET.indent(root, space="  ")
    tree = ET.ElementTree(root)
    # atomic write
    import os as _os
    tmp = file_path.with_suffix(".xml.tmp")
    tree.write(tmp, encoding="utf-8", xml_declaration=True)
    _os.replace(tmp, file_path)
    return str(file_path)


def get_available_themes() -> Dict[str, Dict[str, str]]:
    """Return copy of THEMES dict for API exposure."""
    return dict(THEMES)
