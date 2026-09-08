"""
Settings Tab for Dashboard V4.
Uses default Qt styling — no custom theme handling.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QCheckBox, QMessageBox
)


class SettingsTab(QWidget):
    fullscreen_toggled = pyqtSignal(bool)
    # Kept for backwards compatibility — no longer emitted
    theme_changed = pyqtSignal(str)

    def __init__(self, bridge: Any, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.bridge = bridge

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(14)
        main_layout.setContentsMargins(16, 16, 16, 16)

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
        info_layout.addWidget(QLabel("Styling: Default Qt (native platform theme)"))
        main_layout.addWidget(info_group)

        main_layout.addStretch()

    def refresh(self):
        res = self.bridge.get_xmb_settings()
        if isinstance(res, dict) and res.get("status") == "success":
            settings = res.get("settings", {})
            is_fullscreen = bool(settings.get("fullscreen", False))

            self.check_fullscreen.blockSignals(True)
            self.check_fullscreen.setChecked(is_fullscreen)
            self.check_fullscreen.blockSignals(False)

    def _on_fullscreen_toggled(self, checked: bool):
        self.bridge.set_fullscreen(checked)
        self.fullscreen_toggled.emit(checked)
