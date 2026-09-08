"""
Main Window for Dashboard V4 (PyQt6).
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QTabWidget, QStatusBar
)

from core.renderer.dashboard_v4.theme import get_theme_qss
from core.renderer.dashboard_v4.ui.tabs.home_tab import HomeTab
from core.renderer.dashboard_v4.ui.tabs.bank_tab import BankTab
from core.renderer.dashboard_v4.ui.tabs.inventory_tab import InventoryTab
from core.renderer.dashboard_v4.ui.tabs.garage_tab import GarageTab
from core.renderer.dashboard_v4.ui.tabs.realestate_tab import RealEstateTab
from core.renderer.dashboard_v4.ui.tabs.player_tab import PlayerTab
from core.renderer.dashboard_v4.ui.tabs.phone_tab import PhoneTab
from core.renderer.dashboard_v4.ui.tabs.commands_tab import CommandsTab
from core.renderer.dashboard_v4.ui.tabs.saves_tab import SavesTab
from core.renderer.dashboard_v4.ui.tabs.settings_tab import SettingsTab


class DashboardV4MainWindow(QMainWindow):
    def __init__(self, bridge: Any, player_id: int = 1, initial_theme: str = "default", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.bridge = bridge
        self.current_player_id: int = player_id
        self.current_theme: str = initial_theme

        self.setWindowTitle("Milk Toast Taco — Dashboard V4 (PyQt6)")
        self.resize(1280, 840)
        self.setMinimumSize(960, 640)

        self._init_ui()
        self.apply_theme(self.current_theme)

        # Periodic timer to update Gametime in header (every 5 seconds)
        self._gametime_timer = QTimer(self)
        self._gametime_timer.setInterval(5000)
        self._gametime_timer.timeout.connect(self._update_header_gametime)
        self._gametime_timer.start()

        # Initial data refresh
        self._update_header_gametime()
        self.home_tab.refresh()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Header Bar
        header = QWidget()
        header.setObjectName("panel")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 10, 16, 10)
        header_layout.setSpacing(12)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        lbl_title = QLabel("MILK TOAST TACO")
        lbl_title.setStyleSheet("font-size: 17px; font-weight: 800; letter-spacing: 1px; color: #f1f5f9;")
        lbl_subtitle = QLabel("Console Dashboard V4 • Native Qt Hub")
        lbl_subtitle.setStyleSheet("font-size: 11px; color: #94a3b8; font-weight: 500;")
        title_box.addWidget(lbl_title)
        title_box.addWidget(lbl_subtitle)
        header_layout.addLayout(title_box)

        header_layout.addStretch()

        # Live Gametime in Header
        self.lbl_header_time = QLabel("Game Time: —")
        self.lbl_header_time.setStyleSheet("font-weight: 600; color: #38bdf8; padding: 4px 10px; background: rgba(255,255,255,0.05); border-radius: 4px;")
        header_layout.addWidget(self.lbl_header_time)

        # Active Player Selector
        header_layout.addWidget(QLabel("Active Player:"))
        self.combo_player = QComboBox()
        for pid in range(1, 9):
            self.combo_player.addItem(f"Player {pid}", pid)
        self.combo_player.setCurrentIndex(self.current_player_id - 1)
        self.combo_player.currentIndexChanged.connect(self._on_player_changed)
        header_layout.addWidget(self.combo_player)

        # Refresh Active Tab Button
        self.btn_refresh = QPushButton("Refresh View")
        self.btn_refresh.clicked.connect(self._refresh_active_tab)
        header_layout.addWidget(self.btn_refresh)

        layout.addWidget(header)

        # Main Tabs Container
        self.tabs = QTabWidget()
        self.tabs.currentChanged.connect(self._on_tab_changed)

        # Instantiate Tabs
        self.home_tab = HomeTab(self.bridge, self)
        self.bank_tab = BankTab(self.bridge, self)
        self.inventory_tab = InventoryTab(self.bridge, self)
        self.garage_tab = GarageTab(self.bridge, self)
        self.realestate_tab = RealEstateTab(self.bridge, self)
        self.player_tab = PlayerTab(self.bridge, self)
        self.phone_tab = PhoneTab(self.bridge, self)
        self.commands_tab = CommandsTab(self.bridge, self)
        self.saves_tab = SavesTab(self.bridge, self)
        self.settings_tab = SettingsTab(self.bridge, self)

        # Connect Settings Signals
        self.settings_tab.theme_changed.connect(self.apply_theme)
        self.settings_tab.fullscreen_toggled.connect(self.toggle_fullscreen)

        # Add Tabs
        self.tabs.addTab(self.home_tab, "🏠 Home")
        self.tabs.addTab(self.bank_tab, "💰 Banking")
        self.tabs.addTab(self.inventory_tab, "🎒 Inventory")
        self.tabs.addTab(self.garage_tab, "🚗 Garage")
        self.tabs.addTab(self.realestate_tab, "🏡 Real Estate")
        self.tabs.addTab(self.player_tab, "👥 Player")
        self.tabs.addTab(self.phone_tab, "📱 Phone")
        self.tabs.addTab(self.commands_tab, "⚡ Commands")
        self.tabs.addTab(self.saves_tab, "💾 Saves")
        self.tabs.addTab(self.settings_tab, "⚙️ Settings")

        layout.addWidget(self.tabs)

        # Status Bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage(f"Dashboard V4 Ready • Active: Player {self.current_player_id}")

    def apply_theme(self, theme_name: str):
        self.current_theme = theme_name
        qss = get_theme_qss(theme_name)
        self.setStyleSheet(qss)
        self.statusBar.showMessage(f"Theme switched to '{theme_name}' • Player {self.current_player_id}")

    def toggle_fullscreen(self, enabled: bool):
        if enabled:
            self.showFullScreen()
        else:
            self.showNormal()

    def _on_player_changed(self, index: int):
        self.current_player_id = self.combo_player.currentData()
        # Propagate to all tabs
        for tab in [
            self.home_tab, self.bank_tab, self.inventory_tab,
            self.garage_tab, self.realestate_tab, self.player_tab,
            self.phone_tab, self.commands_tab, self.saves_tab
        ]:
            if hasattr(tab, "set_player_id"):
                tab.set_player_id(self.current_player_id)

        self._refresh_active_tab()
        self.statusBar.showMessage(f"Switched active player to Player {self.current_player_id}")

    def _on_tab_changed(self, index: int):
        self._refresh_active_tab()

    def _refresh_active_tab(self):
        current_widget = self.tabs.currentWidget()
        if hasattr(current_widget, "refresh"):
            current_widget.refresh()
        self._update_header_gametime()

    def _update_header_gametime(self):
        res = self.bridge.call_command("time.now")
        if isinstance(res, dict) and res.get("status") == "success":
            fmt = res.get("formatted", "")
            scale = res.get("time_scale_label", "1x")
            self.lbl_header_time.setText(f"Game Time: {fmt} ({scale})")
        else:
            self.lbl_header_time.setText("Game Time: —")
