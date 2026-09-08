"""
Garage & Vehicle Dealership Tab for Dashboard V4.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox,
    QComboBox, QMessageBox
)


def fmt_currency(amount: Any) -> str:
    try:
        val = float(amount)
        return f"${val:,.2f}" if val % 1 else f"${int(val):,}"
    except Exception:
        return f"${amount}"


class GarageTab(QWidget):
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

        # Top Group: Owned Vehicles
        owned_group = QGroupBox("Player Garage (Owned Vehicles)")
        owned_layout = QVBoxLayout(owned_group)

        self.table_owned = QTableWidget(0, 5)
        self.table_owned.setHorizontalHeaderLabels(["Vehicle ID", "Name", "Category", "Paid Price", "Actions"])
        self.table_owned.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_owned.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        owned_layout.addWidget(self.table_owned)

        main_layout.addWidget(owned_group)

        # Bottom Group: Dealership Catalog
        cat_group = QGroupBox("Vehicle Dealership Catalog")
        cat_layout = QVBoxLayout(cat_group)

        # Filter bar
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Category Filter:"))
        self.combo_cat = QComboBox()
        self.combo_cat.addItem("All Categories", "all")
        self.combo_cat.currentIndexChanged.connect(self._filter_catalog)
        filter_layout.addWidget(self.combo_cat)

        filter_layout.addStretch()
        cat_layout.addLayout(filter_layout)

        # Catalog Table
        self.table_catalog = QTableWidget(0, 6)
        self.table_catalog.setHorizontalHeaderLabels(["ID", "Name", "Category", "Price", "Top Speed", "Action"])
        self.table_catalog.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_catalog.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        cat_layout.addWidget(self.table_catalog)

        main_layout.addWidget(cat_group)

        self._all_catalog_vehicles: List[Dict[str, Any]] = []

    def refresh(self):
        # 1. Owned Vehicles via 'vehicleshop.owned'
        res_owned = self.bridge.call_command("vehicleshop.owned", {"player_id": self.player_id})
        owned = []
        if isinstance(res_owned, dict) and res_owned.get("status") == "success":
            owned = res_owned.get("vehicles") or res_owned.get("result") or []

        self.table_owned.setRowCount(len(owned))
        for row, v in enumerate(owned):
            vid = str(v.get("id", v.get("vehicle_id", "—")))
            name = str(v.get("name", vid))
            cat = str(v.get("category", "General"))
            price = fmt_currency(v.get("price_paid", v.get("price", 0)))

            self.table_owned.setItem(row, 0, QTableWidgetItem(vid))
            self.table_owned.setItem(row, 1, QTableWidgetItem(name))
            self.table_owned.setItem(row, 2, QTableWidgetItem(cat.title()))
            self.table_owned.setItem(row, 3, QTableWidgetItem(price))

            btn_sell = QPushButton("Sell")
            btn_sell.setFixedWidth(70)
            btn_sell.clicked.connect(lambda _, vehicle_id=vid: self._sell_vehicle(vehicle_id))
            self.table_owned.setCellWidget(row, 4, btn_sell)

        # 2. Catalog via 'vehicleshop.get_catalog'
        res_cat = self.bridge.call_command("vehicleshop.get_catalog")
        vehicles = []
        if isinstance(res_cat, dict) and res_cat.get("status") == "success":
            c_data = res_cat.get("catalog", {})
            if isinstance(c_data, dict):
                vehicles = c_data.get("vehicles", [])
                categories = c_data.get("categories", [])
                # update category filter items if needed
                if self.combo_cat.count() <= 1:
                    for cat_item in categories:
                        cid = cat_item.get("id", "")
                        cname = cat_item.get("name", cid.title())
                        self.combo_cat.addItem(cname, cid)

        self._all_catalog_vehicles = vehicles
        self._filter_catalog()

    def _filter_catalog(self):
        selected_cat = self.combo_cat.currentData()
        filtered = []
        for v in self._all_catalog_vehicles:
            if selected_cat == "all" or v.get("category") == selected_cat:
                filtered.append(v)

        self.table_catalog.setRowCount(len(filtered))
        for row, v in enumerate(filtered):
            vid = str(v.get("id", "—"))
            name = str(v.get("name", vid))
            cat = str(v.get("category", "—"))
            price = fmt_currency(v.get("price", 0))
            stats = v.get("stats", {}) if isinstance(v.get("stats"), dict) else {}
            speed = f"{stats.get('top_speed', '—')} km/h" if "top_speed" in stats else "—"

            self.table_catalog.setItem(row, 0, QTableWidgetItem(vid))
            self.table_catalog.setItem(row, 1, QTableWidgetItem(name))
            self.table_catalog.setItem(row, 2, QTableWidgetItem(cat.title()))
            self.table_catalog.setItem(row, 3, QTableWidgetItem(price))
            self.table_catalog.setItem(row, 4, QTableWidgetItem(speed))

            btn_buy = QPushButton("Buy")
            btn_buy.setFixedWidth(70)
            btn_buy.clicked.connect(lambda _, vehicle_id=vid: self._buy_vehicle(vehicle_id))
            self.table_catalog.setCellWidget(row, 5, btn_buy)

    def _buy_vehicle(self, vehicle_id: str):
        res = self.bridge.call_command("vehicleshop.buy", {
            "player_id": self.player_id,
            "vehicle_id": vehicle_id
        })
        if isinstance(res, dict) and res.get("status") == "error":
            QMessageBox.warning(self, "Purchase Failed", res.get("message", "Unable to buy vehicle."))
        self.refresh()

    def _sell_vehicle(self, vehicle_id: str):
        res = self.bridge.call_command("vehicleshop.sell", {
            "player_id": self.player_id,
            "vehicle_id": vehicle_id
        })
        if isinstance(res, dict) and res.get("status") == "error":
            QMessageBox.warning(self, "Sale Failed", res.get("message", "Unable to sell vehicle."))
        self.refresh()
