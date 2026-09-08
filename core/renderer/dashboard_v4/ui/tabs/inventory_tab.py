"""
Inventory Tab for Dashboard V4 — with friendly sub-tabs.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QTableWidget, QTableWidgetItem, QHeaderView,
    QGroupBox, QSpinBox, QDoubleSpinBox, QTabWidget
)


class InventoryTab(QWidget):
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

        desc = QLabel("Track carry weight and manage item stacks. Split into focused sub-tabs so it's not one crowded page.")
        desc.setWordWrap(True)
        main_layout.addWidget(desc)

        self.sub_tabs = QTabWidget()

        # --- Sub-tab: Capacity ---
        cap_page = QWidget()
        cap_v = QVBoxLayout(cap_page)
        cap_v.setContentsMargins(12, 12, 12, 12)
        cap_v.setSpacing(10)
        cap_group = QGroupBox("Carry Capacity")
        cap_l = QVBoxLayout(cap_group)

        cap_info_layout = QHBoxLayout()
        self.lbl_weight = QLabel("Load: 0.0 / 35.0 kg (0%)")
        cap_info_layout.addWidget(self.lbl_weight)
        cap_info_layout.addStretch()
        cap_info_layout.addWidget(QLabel("Max Weight:"))
        self.spin_max_weight = QDoubleSpinBox()
        self.spin_max_weight.setRange(5, 500)
        self.spin_max_weight.setValue(35)
        self.spin_max_weight.setSuffix(" kg")
        cap_info_layout.addWidget(self.spin_max_weight)
        btn_set_cap = QPushButton("Update Max")
        btn_set_cap.clicked.connect(self._set_max_capacity)
        cap_info_layout.addWidget(btn_set_cap)
        cap_l.addLayout(cap_info_layout)

        self.progress_weight = QProgressBar()
        self.progress_weight.setRange(0, 100)
        self.progress_weight.setValue(0)
        cap_l.addWidget(self.progress_weight)
        cap_l.addWidget(QLabel("Capacity limits how much you can carry. Increase max if you unlock perks / backpacks."))
        cap_v.addWidget(cap_group)
        cap_v.addStretch()
        self.sub_tabs.addTab(cap_page, "Capacity")

        # --- Sub-tab: Items ---
        items_page = QWidget()
        items_v = QVBoxLayout(items_page)
        items_v.setContentsMargins(12, 12, 12, 12)
        items_v.setSpacing(10)
        table_group = QGroupBox("Inventory Stacks")
        table_l = QVBoxLayout(table_group)
        self.table_items = QTableWidget(0, 4)
        self.table_items.setHorizontalHeaderLabels(["Item ID", "Quantity", "Acquired At", "Actions"])
        self.table_items.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_items.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table_l.addWidget(self.table_items)
        items_v.addWidget(table_group)
        items_v.addWidget(QLabel("Each row is a stack. Use 'Drop 1' for quick removal or the Operations tab for bulk."))
        self.sub_tabs.addTab(items_page, "Items")

        # --- Sub-tab: Operations ---
        ops_page = QWidget()
        ops_v = QVBoxLayout(ops_page)
        ops_v.setContentsMargins(12, 12, 12, 12)
        ops_v.setSpacing(10)
        act_group = QGroupBox("Item Operations")
        act_l = QHBoxLayout(act_group)
        act_l.addWidget(QLabel("Item ID:"))
        self.spin_item_id = QSpinBox()
        self.spin_item_id.setRange(1, 9999)
        self.spin_item_id.setValue(1)
        act_l.addWidget(self.spin_item_id)
        act_l.addWidget(QLabel("Qty:"))
        self.spin_item_qty = QSpinBox()
        self.spin_item_qty.setRange(1, 1000)
        self.spin_item_qty.setValue(1)
        act_l.addWidget(self.spin_item_qty)
        btn_add = QPushButton("Add Item")
        btn_add.clicked.connect(self._add_item)
        act_l.addWidget(btn_add)
        btn_remove = QPushButton("Remove Item")
        btn_remove.clicked.connect(self._remove_item)
        act_l.addWidget(btn_remove)
        act_l.addStretch()
        ops_v.addWidget(act_group)

        # Clear all row
        clear_group = QGroupBox("Danger Zone")
        clear_l = QHBoxLayout(clear_group)
        clear_l.addWidget(QLabel("Remove everything from this player's inventory."))
        clear_l.addStretch()
        btn_clear = QPushButton("Clear All Items")
        btn_clear.clicked.connect(self._clear_all)
        clear_l.addWidget(btn_clear)
        ops_v.addWidget(clear_group)
        ops_v.addStretch()
        self.sub_tabs.addTab(ops_page, "Operations")

        main_layout.addWidget(self.sub_tabs)

    def refresh(self):
        res = self.bridge.call_command("inventory.list", {"player_id": self.player_id})
        data = {}
        if isinstance(res, dict) and res.get("status") == "success":
            data = res.get("result", {})
        elif isinstance(res, dict) and "stacks" in res:
            data = res

        stacks = data.get("stacks", []) if isinstance(data, dict) else []
        max_w = float(data.get("max_weight", 35.0)) if isinstance(data, dict) else 35.0

        # Query full inventory object or estimate weight
        res_get = self.bridge.call_command("inventory.get", {"player_id": self.player_id})
        tot_w = 0.0
        if isinstance(res_get, dict) and res_get.get("status") == "success":
            inv_obj = res_get.get("result")
            if hasattr(inv_obj, "total_weight"):
                try:
                    tot_w = float(inv_obj.total_weight())
                except Exception:
                    tot_w = 0.0

        pct = min(100, int((tot_w / max_w * 100) if max_w > 0 else 0))
        self.progress_weight.setValue(pct)
        self.lbl_weight.setText(f"Load: {tot_w:.1f} / {max_w:.1f} kg ({pct}%)")
        self.spin_max_weight.setValue(max_w)

        self.table_items.setRowCount(len(stacks))
        for row, s in enumerate(stacks):
            iid = str(s.get("item_id", "—"))
            qty = str(s.get("quantity", "0"))
            acq = str(s.get("acquired_at", "—"))

            self.table_items.setItem(row, 0, QTableWidgetItem(f"Item #{iid}"))
            self.table_items.setItem(row, 1, QTableWidgetItem(f"x{qty}"))
            self.table_items.setItem(row, 2, QTableWidgetItem(acq))

            btn_del = QPushButton("Drop 1")
            btn_del.setFixedWidth(70)
            btn_del.clicked.connect(lambda _, item_id=int(s.get("item_id", 0)): self._drop_one(item_id))
            self.table_items.setCellWidget(row, 3, btn_del)

    def _set_max_capacity(self):
        new_max = self.spin_max_weight.value()
        self.bridge.call_command("inventory.set_max_weight", {
            "player_id": self.player_id,
            "new_max": new_max
        })
        self.refresh()

    def _add_item(self):
        iid = self.spin_item_id.value()
        qty = self.spin_item_qty.value()
        self.bridge.call_command("inventory.add", {
            "player_id": self.player_id,
            "item_id": iid,
            "quantity": qty
        })
        self.refresh()

    def _remove_item(self):
        iid = self.spin_item_id.value()
        qty = self.spin_item_qty.value()
        self.bridge.call_command("inventory.remove_item", {
            "player_id": self.player_id,
            "item_id": iid,
            "quantity": qty
        })
        self.refresh()

    def _drop_one(self, item_id: int):
        self.bridge.call_command("inventory.remove_item", {
            "player_id": self.player_id,
            "item_id": item_id,
            "quantity": 1
        })
        self.refresh()

    def _clear_all(self):
        self.bridge.call_command("inventory.clear_all")
        self.refresh()
