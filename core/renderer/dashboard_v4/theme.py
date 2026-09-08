"""
MTT Dashboard V4 Theme Engine — Qt Style Sheet (QSS) generator.

Generates custom QSS stylesheets dynamically matching Milk Toast Taco's
themes defined in core.renderer.main_menu.xmb_settings.
"""

from __future__ import annotations

from typing import Dict, Any


THEME_PALETTES: Dict[str, Dict[str, str]] = {
    "default": {
        "name": "Default",
        "bg_base": "#070c18",
        "bg_panel": "#0e172a",
        "bg_card": "#13213c",
        "bg_card_alt": "#182a4d",
        "border": "#21365e",
        "border_focus": "#38bdf8",
        "accent": "#0ea5e9",
        "accent_hover": "#38bdf8",
        "accent_pressed": "#0284c7",
        "text": "#f1f5f9",
        "text_muted": "#94a3b8",
        "text_dim": "#64748b",
        "success": "#22c55e",
        "warning": "#eab308",
        "danger": "#ef4444",
    },
    "dark_purple": {
        "name": "Dark Purple",
        "bg_base": "#0c0617",
        "bg_panel": "#170f2c",
        "bg_card": "#21153e",
        "bg_card_alt": "#2c1c53",
        "border": "#3b266e",
        "border_focus": "#c084fc",
        "accent": "#a855f7",
        "accent_hover": "#c084fc",
        "accent_pressed": "#9333ea",
        "text": "#f8fafc",
        "text_muted": "#cbd5e1",
        "text_dim": "#7e6d9b",
        "success": "#34d399",
        "warning": "#fbbf24",
        "danger": "#f87171",
    },
    "crimson_red": {
        "name": "Crimson Red",
        "bg_base": "#140608",
        "bg_panel": "#260e12",
        "bg_card": "#38151a",
        "bg_card_alt": "#4c1c23",
        "border": "#63252d",
        "border_focus": "#fb7185",
        "accent": "#f43f5e",
        "accent_hover": "#fb7185",
        "accent_pressed": "#e11d48",
        "text": "#fdf2f2",
        "text_muted": "#fca5a5",
        "text_dim": "#a3676c",
        "success": "#4ade80",
        "warning": "#f59e0b",
        "danger": "#ef4444",
    },
    "midnight_green": {
        "name": "Midnight Green",
        "bg_base": "#05140d",
        "bg_panel": "#0a2418",
        "bg_card": "#0e3423",
        "bg_card_alt": "#14452f",
        "border": "#1b5a3d",
        "border_focus": "#4ade80",
        "accent": "#10b981",
        "accent_hover": "#34d399",
        "accent_pressed": "#059669",
        "text": "#f0fdf4",
        "text_muted": "#a7f3d0",
        "text_dim": "#5c8a73",
        "success": "#22c55e",
        "warning": "#fbbf24",
        "danger": "#f87171",
    },
    "ocean_blue": {
        "name": "Ocean Blue",
        "bg_base": "#05131a",
        "bg_panel": "#092430",
        "bg_card": "#0e3445",
        "bg_card_alt": "#14465d",
        "border": "#1c5d7c",
        "border_focus": "#38bdf8",
        "accent": "#06b6d4",
        "accent_hover": "#22d3ee",
        "accent_pressed": "#0891b2",
        "text": "#f0fdfa",
        "text_muted": "#99f6e4",
        "text_dim": "#5b8493",
        "success": "#34d399",
        "warning": "#f59e0b",
        "danger": "#f87171",
    },
}


def get_theme_palette(theme_name: str | None = None) -> Dict[str, str]:
    if not theme_name or theme_name not in THEME_PALETTES:
        theme_name = "default"
    return THEME_PALETTES[theme_name]


def get_theme_qss(theme_name: str | None = None) -> str:
    """Return complete QSS stylesheet matching the theme palette."""
    p = get_theme_palette(theme_name)

    return f"""
    /* MTT Dashboard V4 Global Styles */
    QMainWindow, QWidget {{
        background-color: {p["bg_base"]};
        color: {p["text"]};
        font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
        font-size: 13px;
    }}

    /* Panels & Containers */
    QFrame#panel, QWidget#panel {{
        background-color: {p["bg_panel"]};
        border-radius: 8px;
        border: 1px solid {p["border"]};
    }}

    QGroupBox {{
        background-color: {p["bg_panel"]};
        border: 1px solid {p["border"]};
        border-radius: 8px;
        margin-top: 18px;
        padding: 14px 10px 10px 10px;
        font-weight: 600;
        font-size: 13px;
    }}

    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 2px 8px;
        left: 12px;
        color: {p["accent"]};
    }}

    /* Tabs */
    QTabWidget::pane {{
        border: 1px solid {p["border"]};
        background-color: {p["bg_panel"]};
        border-radius: 8px;
        top: -1px;
    }}

    QTabBar::tab {{
        background-color: {p["bg_base"]};
        color: {p["text_muted"]};
        padding: 9px 16px;
        margin-right: 4px;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        border: 1px solid {p["border"]};
        border-bottom: none;
        font-weight: 500;
    }}

    QTabBar::tab:hover {{
        background-color: {p["bg_card"]};
        color: {p["text"]};
    }}

    QTabBar::tab:selected {{
        background-color: {p["bg_panel"]};
        color: {p["accent"]};
        border-bottom: 2px solid {p["accent"]};
        font-weight: 600;
    }}

    /* Buttons */
    QPushButton {{
        background-color: {p["accent"]};
        color: #ffffff;
        border: none;
        border-radius: 5px;
        padding: 7px 14px;
        font-weight: 600;
    }}

    QPushButton:hover {{
        background-color: {p["accent_hover"]};
    }}

    QPushButton:pressed {{
        background-color: {p["accent_pressed"]};
    }}

    QPushButton:disabled {{
        background-color: {p["border"]};
        color: {p["text_dim"]};
    }}

    /* Inputs */
    QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
        background-color: {p["bg_card"]};
        color: {p["text"]};
        border: 1px solid {p["border"]};
        border-radius: 5px;
        padding: 6px 10px;
        selection-background-color: {p["accent"]};
    }}

    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QComboBox:focus {{
        border: 1px solid {p["border_focus"]};
    }}

    QComboBox::drop-down {{
        border: none;
        padding-right: 8px;
    }}

    QComboBox QAbstractItemView {{
        background-color: {p["bg_panel"]};
        color: {p["text"]};
        border: 1px solid {p["border"]};
        selection-background-color: {p["accent"]};
        selection-color: #ffffff;
    }}

    /* Tables & Trees */
    QTableWidget, QTreeWidget {{
        background-color: {p["bg_panel"]};
        color: {p["text"]};
        border: 1px solid {p["border"]};
        border-radius: 6px;
        gridline-color: {p["border"]};
    }}

    QTableWidget::item:selected, QTreeWidget::item:selected {{
        background-color: {p["accent_pressed"]};
        color: #ffffff;
    }}

    QHeaderView::section {{
        background-color: {p["bg_card"]};
        color: {p["text_muted"]};
        padding: 6px 8px;
        border: none;
        border-bottom: 1px solid {p["border"]};
        border-right: 1px solid {p["border"]};
        font-weight: 600;
        font-size: 12px;
    }}

    /* Progress Bar */
    QProgressBar {{
        border: 1px solid {p["border"]};
        border-radius: 4px;
        text-align: center;
        background-color: {p["bg_card"]};
        color: {p["text"]};
        font-weight: 600;
        height: 18px;
    }}

    QProgressBar::chunk {{
        background-color: {p["accent"]};
        border-radius: 3px;
    }}

    /* Sliders */
    QSlider::groove:horizontal {{
        height: 6px;
        background: {p["border"]};
        border-radius: 3px;
    }}

    QSlider::sub-page:horizontal {{
        background: {p["accent"]};
        border-radius: 3px;
    }}

    QSlider::handle:horizontal {{
        background: {p["text"]};
        border: 2px solid {p["accent"]};
        width: 14px;
        margin-top: -4px;
        margin-bottom: -4px;
        border-radius: 7px;
    }}

    /* Scrollbars */
    QScrollBar:vertical {{
        background: {p["bg_base"]};
        width: 10px;
        margin: 0px;
    }}

    QScrollBar:handle:vertical {{
        background: {p["border"]};
        min-height: 20px;
        border-radius: 5px;
    }}

    QScrollBar:handle:vertical:hover {{
        background: {p["accent"]};
    }}

    QScrollBar:add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}

    QScrollBar:horizontal {{
        background: {p["bg_base"]};
        height: 10px;
        margin: 0px;
    }}

    QScrollBar:handle:horizontal {{
        background: {p["border"]};
        min-width: 20px;
        border-radius: 5px;
    }}

    QScrollBar:handle:horizontal:hover {{
        background: {p["accent"]};
    }}

    QScrollBar:add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0px;
    }}

    /* Status Bar */
    QStatusBar {{
        background-color: {p["bg_base"]};
        color: {p["text_muted"]};
        border-top: 1px solid {p["border"]};
        font-size: 12px;
    }}
    """
