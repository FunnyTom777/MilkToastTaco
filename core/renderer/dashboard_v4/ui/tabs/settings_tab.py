"""
Settings Tab for Dashboard V4 (Themes & Display).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QComboBox, QCheckBox, QMessageBox
)

from core.renderer.dashboard_v4.theme import THEME_PALETTES


class SettingsTab(QWidget):
    theme_changed = pyqtSignal(str)
    fullscreen_toggled = pyqtSignal(bool)

    def __init__(self, bridge: Any, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.bridge = bridge

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(14)
        main_layout.setContentsMargins(16, 16, 16, 16)

        # Theme Selector Group
        theme_group = QGroupBox("Visual Theme & Color Palette")
        theme_layout = QVBoxLayout(theme_group)

        row_theme = QHBoxLayout()
        row_theme.addWidget(QLabel("Console Theme:"))
        self.combo_theme = QComboBox()
        for t_id, info in THEME_PALETTES.items():
            self.combo_theme.addItem(f"{info['name']}", t_id)

        self.combo_theme.currentIndexChanged.connect(self._on_theme_selected)
        row_theme.addWidget(self.combo_theme)
        row_theme.addStretch()
        theme_layout.addLayout(row_theme)

        self.lbl_theme_desc = QLabel("Theme description goes here.")
        self.lbl_theme_desc.setStyleSheet("color: #94a3b8; font-size: 12px; margin-top: 6px;")
        theme_layout.addWidget(self.lbl_theme_desc)

        main_layout.addWidget(theme_group)

        # Display & Window Mode Group
        display_group = QGroupBox("Display & Window Mode")
        display_layout = QVBoxLayout(display_group)

        self.check_fullscreen = QCheckBox("Enable Fullscreen Mode")
        self.check_fullscreen.toggled.connect(self._on_fullscreen_toggled)
        display_layout.addWidget(self.check_fullscreen)

        main_layout.addWidget(display_group)

        # System Info Group
        info_group = QGroupBox("Engine & UI Environment")
        info_layout = QVBoxLayout(info_group)
        info_layout.addWidget(QLabel("Milk Toast Taco: Simulation Sandbox"))
        info_layout.addWidget(QLabel("Dashboard V4: Native Desktop UI (PyQt6)"))
        info_layout.addWidget(QLabel("Decoupled via Command Bridge & Auto-Discovery Registry"))
        main_layout.addWidget(info_group)

        main_layout.addStretch()

    def refresh(self):
        res = self.bridge.get_xmb_settings()
        if isinstance(res, dict) and res.get("status") == "success":
            settings = res.get("settings", {})
            current_theme = settings.get("theme", "default")
            is_fullscreen = bool(settings.get("fullscreen", False))

            idx = self.combo_theme.findData(current_theme)
            if idx >= 0:
                self.combo_theme.blockSignals(True)
                self.combo_theme.setCurrentIndex(idx)
                self.combo_theme.blockSignals(False)

            self.check_fullscreen.blockSignals(True)
            self.check_fullscreen.setChecked(is_fullscreen)
            self.check_fullscreen.blockSignals(False)

            self._update_theme_desc(current_theme)

    def _on_theme_selected(self):
        theme_id = self.combo_theme.currentData()
        if not theme_id:
            return

        self.bridge.set_theme(theme_id)
        self._update_theme_desc(theme_id)
        self.theme_changed.emit(theme_id)

    def _update_theme_desc(self, theme_id: str):
        descriptions = {
            "default": "Classic deep-space blue with neon cyan accents.",
            "dark_purple": "Royal void with violet nebula accents.",
            "crimson_red": "Ember core with burning rose horizon.",
            "midnight_green": "Deep forest at midnight with emerald accents.",
            "ocean_blue": "Abyssal teal depths with vivid cyan highlights.",
        }
        self.lbl_theme_desc.setText(descriptions.get(theme_id, "Standard console theme."))

    def _on_fullscreen_toggled(self, checked: bool):
        self.bridge.set_fullscreen(checked)
        self.fullscreen_toggled.emit(checked)
