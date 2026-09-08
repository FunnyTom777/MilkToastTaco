"""
Real Estate Tab for Dashboard V4 — with friendly sub-tabs.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox,
    QComboBox, QTabWidget, QMessageBox
)


def fmt_currency(amount: Any) -> str:
    try:
        val = float(amount)
        return f"${val:,.2f}" if val % 1 else f"${int(val):,}"
    except Exception:
        return f"${amount}"


class RealEstateTab(QWidget):
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
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(8, 8, 8, 8)

        desc = QLabel("Browse the property market and manage what you own. Like V2, this is split into My Properties and Market — pick a sub-tab.")
        desc.setWordWrap(True)
        main_layout.addWidget(desc)

        self.sub_tabs = QTabWidget()

        # --- Sub-tab: Owned / Rented ---
        owned_page = QWidget()
        owned_v = QVBoxLayout(owned_page)
        owned_v.setContentsMargins(12, 12, 12, 12)
        owned_v.setSpacing(10)
        owned_group = QGroupBox("My Properties (Owned & Rented)")
        owned_l = QVBoxLayout(owned_group)
        self.table_owned = QTableWidget(0, 6)
        self.table_owned.setHorizontalHeaderLabels(["ID", "Name", "Type", "Tenure", "Price/Rent", "Action"])
        self.table_owned.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_owned.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        owned_l.addWidget(self.table_owned)
        owned_v.addWidget(owned_group)
        owned_v.addWidget(QLabel("Rentals can be cancelled here; owned properties stay with you permanently."))
        self.sub_tabs.addTab(owned_page, "My Properties")

        # --- Sub-tab: Catalog / Market ---
        cat_page = QWidget()
        cat_v = QVBoxLayout(cat_page)
        cat_v.setContentsMargins(12, 12, 12, 12)
        cat_v.setSpacing(10)
        cat_group = QGroupBox("Property Market Catalog")
        cl = QVBoxLayout(cat_group)

        # Filter bar
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Type Filter:"))
        self.combo_type = QComboBox()
        self.combo_type.addItem("All Types", "all")
        self.combo_type.addItem("Houses", "house")
        self.combo_type.addItem("Apartments", "apartment")
        self.combo_type.addItem("Farms", "farm")
        self.combo_type.addItem("Commercial / Business", "business")
        self.combo_type.addItem("Vacant Land", "vacant_land")
        self.combo_type.currentIndexChanged.connect(self._filter_catalog)
        filter_layout.addWidget(self.combo_type)
        filter_layout.addStretch()
        cl.addLayout(filter_layout)

        # Catalog Table
        self.table_catalog = QTableWidget(0, 7)
        self.table_catalog.setHorizontalHeaderLabels(["ID", "Name", "Type", "Location", "Price", "Rent/mo", "Action"])
        self.table_catalog.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_catalog.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        cl.addWidget(self.table_catalog)
        cat_v.addWidget(cat_group)
        cat_v.addWidget(QLabel("Tip: Houses and apartments are best for sleeping/waking; farms and businesses earn more long term."))
        self.sub_tabs.addTab(cat_page, "Market")

        # Future placeholder hint like V2 agents/garages
        self._all_catalog_properties: List[Dict[str, Any]] = []
        main_layout.addWidget(self.sub_tabs)

    def refresh(self):
        # 1. Owned Properties via 'realestate.owned'
        res_owned = self.bridge.call_command("realestate.owned", {"player_id": self.player_id})
        props = []
        if isinstance(res_owned, dict) and res_owned.get("status") == "success":
            props = res_owned.get("properties") or res_owned.get("owned") or []

        self.table_owned.setRowCount(len(props))
        for row, p in enumerate(props):
            pid = str(p.get("property_id", p.get("id", "—")))
            name = str(p.get("name", pid))
            ptype = str(p.get("type", "—")).title()
            tenure = str(p.get("tenure", "owned")).title()
            cost = fmt_currency(p.get("price_paid", p.get("fee_paid", 0)))

            self.table_owned.setItem(row, 0, QTableWidgetItem(pid))
            self.table_owned.setItem(row, 1, QTableWidgetItem(name))
            self.table_owned.setItem(row, 2, QTableWidgetItem(ptype))
            self.table_owned.setItem(row, 3, QTableWidgetItem(tenure))
            self.table_owned.setItem(row, 4, QTableWidgetItem(cost))

            if tenure.lower() == "rented":
                btn_action = QPushButton("Cancel Rent")
                btn_action.clicked.connect(lambda _, prop_id=pid: self._cancel_rent(prop_id))
            else:
                btn_action = QPushButton("Owned")
                btn_action.setEnabled(False)
            self.table_owned.setCellWidget(row, 5, btn_action)

        # 2. Catalog via 'realestate.get_catalog'
        res_cat = self.bridge.call_command("realestate.get_catalog")
        catalog_props = []
        if isinstance(res_cat, dict) and res_cat.get("status") == "success":
            c_data = res_cat.get("catalog", {})
            if isinstance(c_data, dict):
                catalog_props = c_data.get("properties", [])

        self._all_catalog_properties = catalog_props
        self._filter_catalog()

    def _filter_catalog(self):
        selected_type = self.combo_type.currentData()
        filtered = []
        for p in self._all_catalog_properties:
            if selected_type == "all" or str(p.get("type", "")).lower() == selected_type:
                filtered.append(p)

        self.table_catalog.setRowCount(len(filtered))
        for row, p in enumerate(filtered):
            pid = str(p.get("id", "—"))
            name = str(p.get("name", pid))
            ptype = str(p.get("type", "—")).title()
            loc = str(p.get("location", "—"))
            price = fmt_currency(p.get("price", 0)) if p.get("for_sale") else "Not for sale"
            rent = f"{fmt_currency(p.get('rent_price', 0))}/mo" if p.get("for_rent") else "—"

            self.table_catalog.setItem(row, 0, QTableWidgetItem(pid))
            self.table_catalog.setItem(row, 1, QTableWidgetItem(name))
            self.table_catalog.setItem(row, 2, QTableWidgetItem(ptype))
            self.table_catalog.setItem(row, 3, QTableWidgetItem(loc))
            self.table_catalog.setItem(row, 4, QTableWidgetItem(price))
            self.table_catalog.setItem(row, 5, QTableWidgetItem(rent))

            btn_box = QWidget()
            btn_layout = QHBoxLayout(btn_box)
            btn_layout.setContentsMargins(2, 2, 2, 2)
            btn_layout.setSpacing(4)

            if p.get("for_sale"):
                btn_buy = QPushButton("Buy")
                btn_buy.setFixedWidth(55)
                btn_buy.clicked.connect(lambda _, prop_id=pid: self._buy_property(prop_id))
                btn_layout.addWidget(btn_buy)

            if p.get("for_rent"):
                btn_rent = QPushButton("Rent")
                btn_rent.setFixedWidth(55)
                btn_rent.clicked.connect(lambda _, prop_id=pid: self._rent_property(prop_id))
                btn_layout.addWidget(btn_rent)

            self.table_catalog.setCellWidget(row, 6, btn_box)

    def _buy_property(self, property_id: str):
        res = self.bridge.call_command("realestate.buy", {
            "player_id": self.player_id,
            "property_id": property_id
        })
        if isinstance(res, dict) and res.get("status") == "error":
            QMessageBox.warning(self, "Purchase Failed", res.get("message", "Unable to buy property."))
        self.refresh()

    def _rent_property(self, property_id: str):
        res = self.bridge.call_command("realestate.rent", {
            "player_id": self.player_id,
            "property_id": property_id
        })
        if isinstance(res, dict) and res.get("status") == "error":
            QMessageBox.warning(self, "Rental Failed", res.get("message", "Unable to rent property."))
        self.refresh()

    def _cancel_rent(self, property_id: str):
        res = self.bridge.call_command("realestate.cancel_rent", {
            "player_id": self.player_id,
            "property_id": property_id
        })
        if isinstance(res, dict) and res.get("status") == "error":
            QMessageBox.warning(self, "Cancel Rent Failed", res.get("message", "Unable to cancel rental."))
        self.refresh()
