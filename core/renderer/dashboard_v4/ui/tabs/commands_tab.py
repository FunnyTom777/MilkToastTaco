"""
Dynamic Command Runner & Console Tab for Dashboard V4.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QGroupBox, QLineEdit,
    QComboBox, QTextEdit, QFormLayout, QScrollArea, QSplitter
)


class CommandsTab(QWidget):
    def __init__(self, bridge: Any, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.bridge = bridge
        self.player_id: int = 1

        self._commands_cache: List[Dict[str, Any]] = []
        self._current_spec: Optional[Dict[str, Any]] = None
        self._param_inputs: Dict[str, QLineEdit] = {}

        self._init_ui()

    def set_player_id(self, player_id: int):
        self.player_id = player_id
        # Pre-fill player_id in input fields if active
        if "player_id" in self._param_inputs:
            self._param_inputs["player_id"].setText(str(self.player_id))

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(16, 16, 16, 16)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left Column: Search & Commands List
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        search_layout = QHBoxLayout()
        self.edit_search = QLineEdit()
        self.edit_search.setPlaceholderText("Search commands (e.g. time, bank, player)...")
        self.edit_search.textChanged.connect(self._filter_commands)
        search_layout.addWidget(self.edit_search)

        self.combo_cat = QComboBox()
        self.combo_cat.addItem("All Categories", "all")
        self.combo_cat.addItem("Player", "player")
        self.combo_cat.addItem("Dev", "dev")
        self.combo_cat.addItem("System", "system")
        self.combo_cat.currentIndexChanged.connect(self._filter_commands)
        search_layout.addWidget(self.combo_cat)

        left_layout.addLayout(search_layout)

        self.list_commands = QListWidget()
        self.list_commands.currentItemChanged.connect(self._on_command_selected)
        left_layout.addWidget(self.list_commands)

        btn_refresh = QPushButton("Rescan Registry")
        btn_refresh.clicked.connect(self.refresh)
        left_layout.addWidget(btn_refresh)

        splitter.addWidget(left_widget)

        # Right Column: Parameter Form & Output Inspector
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        # Command Header Info
        self.lbl_cmd_name = QLabel("Select a command to execute")
        right_layout.addWidget(self.lbl_cmd_name)

        self.lbl_cmd_help = QLabel("")
        self.lbl_cmd_help.setWordWrap(True)
        right_layout.addWidget(self.lbl_cmd_help)

        # Form Scroll Area
        self.form_group = QGroupBox("Command Arguments")
        self.form_layout = QFormLayout(self.form_group)
        right_layout.addWidget(self.form_group)

        # Run Button
        self.btn_run = QPushButton("Execute Command")
        self.btn_run.setEnabled(False)
        self.btn_run.clicked.connect(self._run_current_command)
        right_layout.addWidget(self.btn_run)

        # Output Box
        output_group = QGroupBox("Execution Response")
        output_layout = QVBoxLayout(output_group)
        self.text_output = QTextEdit()
        self.text_output.setReadOnly(True)
        output_layout.addWidget(self.text_output)
        right_layout.addWidget(output_group)

        splitter.addWidget(right_widget)
        splitter.setSizes([320, 580])

        main_layout.addWidget(splitter)

    def refresh(self):
        res = self.bridge.list_commands(refresh=True)
        if isinstance(res, dict) and res.get("status") == "success":
            self._commands_cache = res.get("commands", [])
        else:
            self._commands_cache = []

        self._filter_commands()

    def _filter_commands(self):
        query = self.edit_search.text().strip().lower()
        cat = self.combo_cat.currentData()

        self.list_commands.clear()
        for cmd in self._commands_cache:
            c_name = cmd.get("name", "")
            c_cat = cmd.get("category", "")
            c_help = cmd.get("help_text", "")

            if cat != "all" and c_cat != cat:
                continue

            if query and query not in c_name.lower() and query not in c_help.lower():
                continue

            item = QListWidgetItem(f"{c_name} [{c_cat}]")
            item.setData(Qt.ItemDataRole.UserRole, cmd)
            self.list_commands.addItem(item)

    def _on_command_selected(self, current: Optional[QListWidgetItem], previous: Optional[QListWidgetItem] = None):
        if not current:
            self.btn_run.setEnabled(False)
            self.lbl_cmd_name.setText("Select a command to execute")
            self.lbl_cmd_help.setText("")
            self._clear_form()
            return

        cmd = current.data(Qt.ItemDataRole.UserRole)
        if not cmd:
            return

        self._current_spec = cmd
        self.btn_run.setEnabled(True)
        self.lbl_cmd_name.setText(cmd.get("name", ""))
        self.lbl_cmd_help.setText(cmd.get("help_text", "No description provided."))

        self._build_form(cmd.get("params", []))

    def _clear_form(self):
        while self.form_layout.count():
            item = self.form_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._param_inputs.clear()

    def _build_form(self, params: List[Dict[str, Any]]):
        self._clear_form()

        if not params:
            lbl_none = QLabel("No arguments required for this command.")
            self.form_layout.addRow(lbl_none)
            return

        for p in params:
            p_name = p.get("name", "")
            req = p.get("required", False)
            default = p.get("default", "")
            ann = p.get("annotation", "")

            label_text = f"{p_name}{'*' if req else ''}:"
            if ann:
                label_text += f" ({ann})"

            edit = QLineEdit()
            if default != "":
                edit.setText(str(default))
            elif p_name == "player_id":
                edit.setText(str(self.player_id))

            edit.setPlaceholderText("required" if req else "optional")
            self.form_layout.addRow(label_text, edit)
            self._param_inputs[p_name] = edit

    def _run_current_command(self):
        if not self._current_spec:
            return

        cmd_name = self._current_spec.get("name", "")
        args: Dict[str, Any] = {}

        for p_name, edit in self._param_inputs.items():
            val_str = edit.text().strip()
            if not val_str:
                continue

            # Try parsing JSON/number/bool, fallback to raw string
            try:
                val = json.loads(val_str)
            except Exception:
                val = val_str
            args[p_name] = val

        self.text_output.setPlainText(f"Executing: {cmd_name}({args})...\n")

        res = self.bridge.call_command(cmd_name, args if args else None)

        try:
            # Check if result is json serializable
            out_str = json.dumps(res, indent=2, default=str)
        except Exception:
            out_str = str(res)

        self.text_output.setPlainText(out_str)
