"""
Phone Tab for Dashboard V4.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox,
    QLineEdit, QMessageBox
)


class PhoneTab(QWidget):
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

        # Contacts Table Group
        contacts_group = QGroupBox("Saved Phone Contacts")
        contacts_layout = QVBoxLayout(contacts_group)

        self.table_contacts = QTableWidget(0, 3)
        self.table_contacts.setHorizontalHeaderLabels(["Contact Name", "Phone Number", "Action"])
        self.table_contacts.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_contacts.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        contacts_layout.addWidget(self.table_contacts)

        main_layout.addWidget(contacts_group)

        # Add Contact Box
        add_group = QGroupBox("Add New Contact")
        add_layout = QHBoxLayout(add_group)

        add_layout.addWidget(QLabel("Name:"))
        self.edit_name = QLineEdit()
        self.edit_name.setPlaceholderText("e.g. Sunny Realty")
        add_layout.addWidget(self.edit_name)

        add_layout.addWidget(QLabel("Number:"))
        self.edit_num = QLineEdit()
        self.edit_num.setPlaceholderText("e.g. 555-0199")
        add_layout.addWidget(self.edit_num)

        btn_add = QPushButton("Save Contact")
        btn_add.clicked.connect(self._add_contact)
        add_layout.addWidget(btn_add)

        main_layout.addWidget(add_group)

    def refresh(self):
        res = self.bridge.call_command("phone.get_contacts")
        contacts = {}
        if isinstance(res, dict) and res.get("status") == "success":
            contacts = res.get("result", {})
            if not isinstance(contacts, dict):
                contacts = res.get("contacts", {})

        items = list(contacts.items()) if isinstance(contacts, dict) else []
        self.table_contacts.setRowCount(len(items))

        for row, (name, num) in enumerate(items):
            phone_str = str(num.get("number", num) if isinstance(num, dict) else num)
            self.table_contacts.setItem(row, 0, QTableWidgetItem(str(name)))
            self.table_contacts.setItem(row, 1, QTableWidgetItem(phone_str))

            btn_del = QPushButton("Delete")
            btn_del.setFixedWidth(75)
            btn_del.clicked.connect(lambda _, contact_name=name: self._delete_contact(contact_name))
            self.table_contacts.setCellWidget(row, 2, btn_del)

    def _add_contact(self):
        name = self.edit_name.text().strip()
        num = self.edit_num.text().strip()
        if not name or not num:
            QMessageBox.information(self, "Missing Info", "Please enter both contact name and number.")
            return

        self.bridge.call_command("phone.new_contact", {
            "contact_name": name,
            "contact_number": num
        })
        self.edit_name.clear()
        self.edit_num.clear()
        self.refresh()

    def _delete_contact(self, name: str):
        self.bridge.call_command("phone.delete_contact", {
            "contact_name": name
        })
        self.refresh()
