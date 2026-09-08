"""
MTT Dashboard V4 Theme Engine — DEPRECATED.

Previously generated custom QSS stylesheets matching Milk Toast Taco themes.
Now intentionally returns empty styles to use default Qt styling/theming.

Kept as a stub for backwards compatibility — imports remain valid but
no custom styling is applied.
"""

from __future__ import annotations

from typing import Dict, Any


# Minimal stub — kept so existing imports don't break.
THEME_PALETTES: Dict[str, Dict[str, str]] = {
    "default": {
        "name": "Default",
    },
}


def get_theme_palette(theme_name: str | None = None) -> Dict[str, str]:
    """Return default palette stub (no custom colors)."""
    return THEME_PALETTES["default"]


def get_theme_qss(theme_name: str | None = None) -> str:
    """Return empty QSS — use default Qt styling."""
    return ""
