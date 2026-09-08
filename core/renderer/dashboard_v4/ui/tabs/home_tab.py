"""
Home / Overview Tab for Dashboard V4.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QComboBox, QGroupBox, QSpinBox
)


def fmt_currency(amount: Any) -> str:
    try:
        val = float(amount)
        return f"${val:,.2f}" if val % 1 else f"${int(val):,}"
    except Exception:
        return f"${amount}"


class HomeTab(QWidget):
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

        # Top Stats Row (Grid)
        stats_group = QGroupBox("Overview Metrics")
        stats_layout = QGridLayout(stats_group)
        stats_layout.setSpacing(12)

        # Metric 1: Cash Balance
        self.lbl_balance = QLabel("$0")
        self.lbl_balance.setStyleSheet("font-size: 22px; font-weight: 700; color: #38bdf8;")
        lbl_bal_title = QLabel("Cash Balance")
        lbl_bal_title.setStyleSheet("font-size: 11px; text-transform: uppercase; color: #94a3b8;")
        box1 = QVBoxLayout()
        box1.addWidget(lbl_bal_title)
        box1.addWidget(self.lbl_balance)
        stats_layout.addLayout(box1, 0, 0)

        # Metric 2: Vehicles Owned
        self.lbl_vehicles = QLabel("0")
        self.lbl_vehicles.setStyleSheet("font-size: 22px; font-weight: 700; color: #38bdf8;")
        lbl_veh_title = QLabel("Vehicles Owned")
        lbl_veh_title.setStyleSheet("font-size: 11px; text-transform: uppercase; color: #94a3b8;")
        box2 = QVBoxLayout()
        box2.addWidget(lbl_veh_title)
        box2.addWidget(self.lbl_vehicles)
        stats_layout.addLayout(box2, 0, 1)

        # Metric 3: Properties Owned
        self.lbl_properties = QLabel("0")
        self.lbl_properties.setStyleSheet("font-size: 22px; font-weight: 700; color: #38bdf8;")
        lbl_prop_title = QLabel("Properties Owned")
        lbl_prop_title.setStyleSheet("font-size: 11px; text-transform: uppercase; color: #94a3b8;")
        box3 = QVBoxLayout()
        box3.addWidget(lbl_prop_title)
        box3.addWidget(self.lbl_properties)
        stats_layout.addLayout(box3, 0, 2)

        # Metric 4: Inventory Weight
        self.lbl_inventory = QLabel("0.0 / 0.0 kg")
        self.lbl_inventory.setStyleSheet("font-size: 22px; font-weight: 700; color: #38bdf8;")
        lbl_inv_title = QLabel("Inventory Load")
        lbl_inv_title.setStyleSheet("font-size: 11px; text-transform: uppercase; color: #94a3b8;")
        box4 = QVBoxLayout()
        box4.addWidget(lbl_inv_title)
        box4.addWidget(self.lbl_inventory)
        stats_layout.addLayout(box4, 0, 3)

        main_layout.addWidget(stats_group)

        # Gametime & Controls Group
        time_group = QGroupBox("Game Time & Day-Night System")
        time_layout = QVBoxLayout(time_group)
        time_layout.setSpacing(10)

        # Current Time Display
        time_header_box = QHBoxLayout()
        self.lbl_gametime = QLabel("Game Time: —")
        self.lbl_gametime.setStyleSheet("font-size: 18px; font-weight: 600; color: #f1f5f9;")
        time_header_box.addWidget(self.lbl_gametime)
        time_header_box.addStretch()

        self.btn_pause = QPushButton("Pause / Play")
        self.btn_pause.clicked.connect(self._toggle_pause)
        time_header_box.addWidget(self.btn_pause)

        time_layout.addLayout(time_header_box)

        # Timescale Presets (1x, 3x, 5x, 7x, 15x, 25x)
        scale_box = QHBoxLayout()
        scale_box.addWidget(QLabel("Timescale:"))
        for scale in [1, 3, 5, 7, 15, 25]:
            btn = QPushButton(f"{scale}x")
            btn.setFixedWidth(50)
            btn.clicked.connect(lambda _, s=scale: self._set_scale(s))
            scale_box.addWidget(btn)

        scale_box.addSpacing(16)
        scale_box.addWidget(QLabel("Advance:"))
        btn_1h = QPushButton("+1 Hour")
        btn_1h.clicked.connect(lambda: self._advance_time(hours=1))
        scale_box.addWidget(btn_1h)

        btn_1d = QPushButton("+1 Day")
        btn_1d.clicked.connect(lambda: self._advance_time(days=1))
        scale_box.addWidget(btn_1d)

        scale_box.addStretch()
        time_layout.addLayout(scale_box)

        main_layout.addWidget(time_group)

        # Sleep System Group
        sleep_group = QGroupBox("Sleep at Owned Property")
        sleep_layout = QHBoxLayout(sleep_group)

        sleep_layout.addWidget(QLabel("Select House:"))
        self.combo_sleep_houses = QComboBox()
        self.combo_sleep_houses.setMinimumWidth(260)
        sleep_layout.addWidget(self.combo_sleep_houses)

        sleep_layout.addWidget(QLabel("Wake Hour:"))
        self.spin_wake_hour = QSpinBox()
        self.spin_wake_hour.setRange(0, 23)
        self.spin_wake_hour.setValue(7)
        self.spin_wake_hour.setSuffix(":00")
        sleep_layout.addWidget(self.spin_wake_hour)

        self.btn_sleep = QPushButton("Sleep Until Wake Time")
        self.btn_sleep.clicked.connect(self._on_sleep_clicked)
        sleep_layout.addWidget(self.btn_sleep)

        sleep_layout.addStretch()
        main_layout.addWidget(sleep_group)

        # Quick Actions Group
        actions_group = QGroupBox("Quick Player Operations")
        actions_layout = QHBoxLayout(actions_group)

        btn_add_1k = QPushButton("+$1,000 Cash")
        btn_add_1k.clicked.connect(lambda: self._add_funds(1000))
        actions_layout.addWidget(btn_add_1k)

        btn_add_10k = QPushButton("+$10,000 Cash")
        btn_add_10k.clicked.connect(lambda: self._add_funds(10000))
        actions_layout.addWidget(btn_add_10k)

        btn_clear_inv = QPushButton("Clear Inventory")
        btn_clear_inv.clicked.connect(self._clear_inventory)
        actions_layout.addWidget(btn_clear_inv)

        actions_layout.addStretch()
        main_layout.addWidget(actions_group)

        main_layout.addStretch()

    def refresh(self):
        # 1. Gametime via 'time.now' or 'time.get'
        res_time = self.bridge.call_command("time.now")
        if isinstance(res_time, dict) and res_time.get("status") == "success":
            fmt = res_time.get("formatted", "")
            scale = res_time.get("time_scale_label", "1x")
            paused = " [PAUSED]" if res_time.get("paused") else ""
            self.lbl_gametime.setText(f"Game Time: {fmt} ({scale}){paused}")
        else:
            self.lbl_gametime.setText("Game Time: —")

        # 2. Balance via 'economy.balance'
        res_bal = self.bridge.call_command("economy.balance", {"player_id": self.player_id})
        if isinstance(res_bal, dict) and res_bal.get("status") == "success":
            bal = res_bal.get("balance", 0.0)
            self.lbl_balance.setText(fmt_currency(bal))
        else:
            self.lbl_balance.setText("$0")

        # 3. Vehicles owned via 'vehicleshop.owned'
        res_veh = self.bridge.call_command("vehicleshop.owned", {"player_id": self.player_id})
        if isinstance(res_veh, dict) and res_veh.get("status") == "success":
            v_list = res_veh.get("result") or res_veh.get("vehicles") or []
            self.lbl_vehicles.setText(str(len(v_list)))
        else:
            self.lbl_vehicles.setText("0")

        # 4. Properties owned via 'realestate.owned'
        res_re = self.bridge.call_command("realestate.owned", {"player_id": self.player_id})
        houses_list = []
        if isinstance(res_re, dict) and res_re.get("status") == "success":
            props = res_re.get("properties") or res_re.get("owned") or []
            self.lbl_properties.setText(str(len(props)))
            # Populate sleep houses
            self.combo_sleep_houses.clear()
            for p in props:
                name = p.get("name", p.get("property_id", "Property"))
                pid = p.get("property_id", "")
                self.combo_sleep_houses.addItem(f"{name} ({pid})", pid)
        else:
            self.lbl_properties.setText("0")
            self.combo_sleep_houses.clear()

        # 5. Inventory weight via 'inventory.get'
        res_inv = self.bridge.call_command("inventory.get", {"player_id": self.player_id})
        if isinstance(res_inv, dict) and res_inv.get("status") == "success":
            tot = res_inv.get("total_weight", 0.0)
            mx = res_inv.get("max_weight", 0.0)
            self.lbl_inventory.setText(f"{tot:.1f} / {mx:.1f} kg")
        else:
            self.lbl_inventory.setText("0.0 / 0.0 kg")

    def _set_scale(self, scale: int):
        self.bridge.call_command("time.scale", {"scale": scale})
        self.refresh()

    def _toggle_pause(self):
        self.bridge.call_command("time.pause")
        self.refresh()

    def _advance_time(self, hours: int = 0, days: int = 0):
        if hours:
            self.bridge.call_command("time.add_hours", {"hours": hours})
        if days:
            self.bridge.call_command("time.add_days", {"days": days})
        self.refresh()

    def _on_sleep_clicked(self):
        prop_id = self.combo_sleep_houses.currentData()
        wake_h = self.spin_wake_hour.value()
        self.bridge.call_command("time.sleep", {
            "wake_hour": wake_h,
            "wake_minute": 0
        })
        self.refresh()

    def _add_funds(self, amount: float):
        self.bridge.call_command("economy.add_funds", {
            "player_id": self.player_id,
            "amount": amount
        })
        self.refresh()

    def _clear_inventory(self):
        self.bridge.call_command("inventory.clear_all", {
            "player_id": self.player_id
        })
        self.refresh()
