"""
Player & World Tab for Dashboard V4.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QDoubleSpinBox, QGroupBox,
    QComboBox, QMessageBox
)


class PlayerTab(QWidget):
    def __init__(self, bridge: Any, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.bridge = bridge
        self.player_id: int = 1

        self._init_ui()

    def set_player_id(self, player_id: int):
        self.player_id = player_id
        self.refresh()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(14)
        main_layout.setContentsMargins(16, 16, 16, 16)

        # Position Card
        pos_group = QGroupBox("Player World Position")
        pos_layout = QVBoxLayout(pos_group)

        self.lbl_current_pos = QLabel("Current Position: X: 0.0, Y: 0.0, Z: 0.0")
        self.lbl_current_pos.setStyleSheet("font-size: 18px; font-weight: 700; color: #38bdf8;")
        pos_layout.addWidget(self.lbl_current_pos)

        main_layout.addWidget(pos_group)

        # Move / Teleport Box
        move_group = QGroupBox("Set Player Coordinates")
        move_layout = QGridLayout(move_group)

        move_layout.addWidget(QLabel("X Coordinate:"), 0, 0)
        self.spin_x = QDoubleSpinBox()
        self.spin_x.setRange(-100000, 100000)
        self.spin_x.setValue(0)
        move_layout.addWidget(self.spin_x, 0, 1)

        move_layout.addWidget(QLabel("Y Coordinate:"), 1, 0)
        self.spin_y = QDoubleSpinBox()
        self.spin_y.setRange(-1000, 10000)
        self.spin_y.setValue(0)
        move_layout.addWidget(self.spin_y, 1, 1)

        move_layout.addWidget(QLabel("Z Coordinate:"), 2, 0)
        self.spin_z = QDoubleSpinBox()
        self.spin_z.setRange(-100000, 100000)
        self.spin_z.setValue(0)
        move_layout.addWidget(self.spin_z, 2, 1)

        btn_move = QPushButton("Move / Teleport Player")
        btn_move.clicked.connect(self._move_player)
        move_layout.addWidget(btn_move, 3, 0, 1, 2)

        main_layout.addWidget(move_group)

        # Quick Landmarks
        land_group = QGroupBox("Fast Travel Landmarks")
        land_layout = QHBoxLayout(land_group)

        landmarks = [
            ("Origin / Hub", [0, 0, 0]),
            ("Downtown Center", [500, 0, 300]),
            ("West Farm", [150, 0, -200]),
            ("Maple District", [100, 0, 50]),
            ("Industrial Port", [-400, 0, 600]),
        ]

        for name, coords in landmarks:
            btn = QPushButton(name)
            btn.clicked.connect(lambda _, c=coords: self._teleport_to(c))
            land_layout.addWidget(btn)

        main_layout.addWidget(land_group)

        main_layout.addStretch()

    def refresh(self):
        res = self.bridge.call_command("player.get", {"player_id": self.player_id})
        pos = (0, 0, 0)
        if isinstance(res, dict) and res.get("status") == "success":
            pos = res.get("result", (0, 0, 0))
            if isinstance(pos, (list, tuple)) and len(pos) >= 3:
                self.lbl_current_pos.setText(f"Current Position: X: {pos[0]:.1f}, Y: {pos[1]:.1f}, Z: {pos[2]:.1f}")
                self.spin_x.setValue(float(pos[0]))
                self.spin_y.setValue(float(pos[1]))
                self.spin_z.setValue(float(pos[2]))
                return
        self.lbl_current_pos.setText("Current Position: X: 0.0, Y: 0.0, Z: 0.0")

    def _move_player(self):
        x = self.spin_x.value()
        y = self.spin_y.value()
        z = self.spin_z.value()
        self.bridge.call_command("player.move", {
            "player_id": self.player_id,
            "pos": [x, y, z]
        })
        self.refresh()

    def _teleport_to(self, coords: List[float]):
        self.bridge.call_command("player.move", {
            "player_id": self.player_id,
            "pos": coords
        })
        self.refresh()
