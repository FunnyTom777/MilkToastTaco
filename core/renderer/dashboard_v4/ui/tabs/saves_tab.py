"""
Save Game Manager Tab for Dashboard V4.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QGroupBox, QLineEdit,
    QMessageBox
)


class SavesTab(QWidget):
    def __init__(self, bridge: Any, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.bridge = bridge
        self.player_id: int = 1

        self._init_ui()

    def set_player_id(self, player_id: int):
        self.player_id = player_id

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(14)
        main_layout.setContentsMargins(16, 16, 16, 16)

        # Existing Saves List
        list_group = QGroupBox("Available Save Games")
        list_layout = QVBoxLayout(list_group)

        self.list_saves = QListWidget()
        list_layout.addWidget(self.list_saves)

        btn_box = QHBoxLayout()
        self.btn_load = QPushButton("Load Selected Save")
        self.btn_load.clicked.connect(self._load_save)
        btn_box.addWidget(self.btn_load)

        self.btn_refresh = QPushButton("Refresh List")
        self.btn_refresh.clicked.connect(self.refresh)
        btn_box.addWidget(self.btn_refresh)

        list_layout.addLayout(btn_box)
        main_layout.addWidget(list_group)

        # Save Current Game Group
        save_group = QGroupBox("Save Current Game")
        save_layout = QHBoxLayout(save_group)

        save_layout.addWidget(QLabel("Save Name:"))
        self.edit_save_name = QLineEdit()
        self.edit_save_name.setPlaceholderText("e.g. career_day_1")
        save_layout.addWidget(self.edit_save_name)

        btn_save = QPushButton("Save Game")
        btn_save.clicked.connect(self._save_game)
        save_layout.addWidget(btn_save)

        main_layout.addWidget(save_group)

    def refresh(self):
        self.list_saves.clear()
        res = self.bridge.list_saves()
        saves = []
        if isinstance(res, dict) and res.get("status") == "success":
            saves = res.get("saves", [])
        elif isinstance(res, list):
            saves = res

        for s in saves:
            s_name = s.get("name", str(s)) if isinstance(s, dict) else str(s)
            item = QListWidgetItem(f"📁 {s_name}")
            item.setData(Qt.ItemDataRole.UserRole, s_name)
            self.list_saves.addItem(item)

    def _load_save(self):
        item = self.list_saves.currentItem()
        if not item:
            QMessageBox.information(self, "Select Save", "Please select a save game from the list.")
            return

        save_name = item.data(Qt.ItemDataRole.UserRole)
        res = self.bridge.load_game(save_name)
        if isinstance(res, dict) and res.get("status") == "success":
            QMessageBox.information(self, "Loaded", f"Successfully loaded '{save_name}'.")
        else:
            msg = res.get("message", "Error loading save") if isinstance(res, dict) else "Error"
            QMessageBox.warning(self, "Load Failed", msg)

    def _save_game(self):
        name = self.edit_save_name.text().strip()
        if not name:
            QMessageBox.information(self, "Missing Name", "Please enter a save name.")
            return

        res = self.bridge.save_game(name)
        if isinstance(res, dict) and res.get("status") == "success":
            QMessageBox.information(self, "Saved", f"Successfully saved game as '{name}'.")
            self.edit_save_name.clear()
            self.refresh()
        else:
            msg = res.get("message", "Error saving game") if isinstance(res, dict) else "Error"
            QMessageBox.warning(self, "Save Failed", msg)
