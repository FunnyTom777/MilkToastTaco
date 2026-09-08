"""
Bank & Economy Tab for Dashboard V4.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QComboBox, QGroupBox, QSpinBox,
    QDoubleSpinBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox
)


def fmt_currency(amount: Any) -> str:
    try:
        val = float(amount)
        return f"${val:,.2f}" if val % 1 else f"${int(val):,}"
    except Exception:
        return f"${amount}"


class BankTab(QWidget):
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

        # Top Wallet Bar
        wallet_group = QGroupBox("Cash Wallet")
        wallet_layout = QHBoxLayout(wallet_group)

        self.lbl_wallet = QLabel("Wallet Balance: $0")
        self.lbl_wallet.setStyleSheet("font-size: 16px; font-weight: 700; color: #38bdf8;")
        wallet_layout.addWidget(self.lbl_wallet)

        wallet_layout.addStretch()

        wallet_layout.addWidget(QLabel("Amount:"))
        self.spin_funds = QDoubleSpinBox()
        self.spin_funds.setRange(1, 1000000)
        self.spin_funds.setValue(1000)
        self.spin_funds.setPrefix("$")
        wallet_layout.addWidget(self.spin_funds)

        btn_add = QPushButton("Deposit Cash")
        btn_add.clicked.connect(self._add_cash)
        wallet_layout.addWidget(btn_add)

        btn_set = QPushButton("Set Balance")
        btn_set.clicked.connect(self._set_cash)
        wallet_layout.addWidget(btn_set)

        main_layout.addWidget(wallet_group)

        # Middle Grid: Cards & Memberships
        mid_layout = QHBoxLayout()

        # Bank Cards Table
        cards_group = QGroupBox("Bank Accounts & Cards")
        cards_layout = QVBoxLayout(cards_group)

        self.table_cards = QTableWidget(0, 4)
        self.table_cards.setHorizontalHeaderLabels(["Bank", "Card Number", "Balance", "Type"])
        self.table_cards.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_cards.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        cards_layout.addWidget(self.table_cards)

        mid_layout.addWidget(cards_group)

        # Bank Memberships Table
        mems_group = QGroupBox("Bank Memberships")
        mems_layout = QVBoxLayout(mems_group)

        self.table_mems = QTableWidget(0, 3)
        self.table_mems.setHorizontalHeaderLabels(["Bank ID", "Monthly Fee", "Status"])
        self.table_mems.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_mems.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        mems_layout.addWidget(self.table_mems)

        # Membership Actions
        mem_act_layout = QHBoxLayout()
        self.combo_banks = QComboBox()
        mem_act_layout.addWidget(self.combo_banks)

        btn_join = QPushButton("Join Bank")
        btn_join.clicked.connect(self._join_bank)
        mem_act_layout.addWidget(btn_join)

        btn_leave = QPushButton("Leave Bank")
        btn_leave.clicked.connect(self._leave_bank)
        mem_act_layout.addWidget(btn_leave)

        mems_layout.addLayout(mem_act_layout)

        mid_layout.addWidget(mems_group)
        main_layout.addLayout(mid_layout)

        # Bottom Grid: Transfers & Loans
        bottom_layout = QHBoxLayout()

        # Money Transfer Box
        transfer_group = QGroupBox("Transfer Funds Between Cards")
        trans_layout = QGridLayout(transfer_group)

        trans_layout.addWidget(QLabel("From Card:"), 0, 0)
        self.combo_from_card = QComboBox()
        trans_layout.addWidget(self.combo_from_card, 0, 1)

        trans_layout.addWidget(QLabel("To Card:"), 1, 0)
        self.combo_to_card = QComboBox()
        trans_layout.addWidget(self.combo_to_card, 1, 1)

        trans_layout.addWidget(QLabel("Amount:"), 2, 0)
        self.spin_trans_amt = QDoubleSpinBox()
        self.spin_trans_amt.setRange(1, 1000000)
        self.spin_trans_amt.setValue(500)
        self.spin_trans_amt.setPrefix("$")
        trans_layout.addWidget(self.spin_trans_amt, 2, 1)

        btn_trans = QPushButton("Send Transfer")
        btn_trans.clicked.connect(self._transfer_funds)
        trans_layout.addWidget(btn_trans, 3, 0, 1, 2)

        bottom_layout.addWidget(transfer_group)

        # Auto Loans Box
        loan_group = QGroupBox("Apply for Bank Loan")
        loan_layout = QGridLayout(loan_group)

        loan_layout.addWidget(QLabel("Bank:"), 0, 0)
        self.combo_loan_bank = QComboBox()
        loan_layout.addWidget(self.combo_loan_bank, 0, 1)

        loan_layout.addWidget(QLabel("Loan Amount:"), 1, 0)
        self.spin_loan_amt = QDoubleSpinBox()
        self.spin_loan_amt.setRange(100, 500000)
        self.spin_loan_amt.setValue(10000)
        self.spin_loan_amt.setPrefix("$")
        loan_layout.addWidget(self.spin_loan_amt, 1, 1)

        loan_layout.addWidget(QLabel("Term:"), 2, 0)
        self.combo_loan_term = QComboBox()
        self.combo_loan_term.addItem("12 Months", 12)
        self.combo_loan_term.addItem("24 Months", 24)
        self.combo_loan_term.addItem("36 Months", 36)
        self.combo_loan_term.addItem("60 Months", 60)
        loan_layout.addWidget(self.combo_loan_term, 2, 1)

        btn_loan = QPushButton("Request Loan")
        btn_loan.clicked.connect(self._request_loan)
        loan_layout.addWidget(btn_loan, 3, 0, 1, 2)

        bottom_layout.addWidget(loan_group)

        main_layout.addLayout(bottom_layout)

    def refresh(self):
        # 1. Wallet Balance via 'economy.balance'
        res_bal = self.bridge.call_command("economy.balance", {"player_id": self.player_id})
        if isinstance(res_bal, dict) and res_bal.get("status") == "success":
            bal = res_bal.get("balance", 0.0)
            self.lbl_wallet.setText(f"Wallet Balance: {fmt_currency(bal)}")
        else:
            self.lbl_wallet.setText("Wallet Balance: $0")

        # 2. Cards via 'bank.list_cards'
        res_cards = self.bridge.call_command("bank.list_cards", {"player_id": self.player_id})
        cards = []
        if isinstance(res_cards, dict) and res_cards.get("status") == "success":
            cards = res_cards.get("cards", [])

        self.table_cards.setRowCount(len(cards))
        self.combo_from_card.clear()
        self.combo_to_card.clear()

        for row, c in enumerate(cards):
            b_name = str(c.get("bank_name", c.get("bank", "Bank")))
            c_num = str(c.get("card_number", "—"))
            c_bal = fmt_currency(c.get("balance", 0))
            c_type = str(c.get("type", "Standard"))

            self.table_cards.setItem(row, 0, QTableWidgetItem(b_name))
            self.table_cards.setItem(row, 1, QTableWidgetItem(c_num))
            self.table_cards.setItem(row, 2, QTableWidgetItem(c_bal))
            self.table_cards.setItem(row, 3, QTableWidgetItem(c_type))

            card_label = f"{b_name} ({c_num}) - {c_bal}"
            self.combo_from_card.addItem(card_label, c_num)
            self.combo_to_card.addItem(card_label, c_num)

        # 3. Memberships via 'bank.memberships'
        res_mems = self.bridge.call_command("bank.memberships", {"player_id": self.player_id})
        mems = []
        if isinstance(res_mems, dict) and res_mems.get("status") == "success":
            mems = res_mems.get("memberships", [])

        self.table_mems.setRowCount(len(mems))
        for row, m in enumerate(mems):
            b_id = str(m.get("bank_id", ""))
            fee = fmt_currency(m.get("subscription_fee", 0))
            status = "Active" if m.get("active", True) else "Inactive"

            self.table_mems.setItem(row, 0, QTableWidgetItem(b_id))
            self.table_mems.setItem(row, 1, QTableWidgetItem(f"{fee}/mo"))
            self.table_mems.setItem(row, 2, QTableWidgetItem(status))

        # 4. Bank list via 'bank.banks'
        res_banks = self.bridge.call_command("bank.banks")
        banks_list = []
        if isinstance(res_banks, dict) and res_banks.get("status") == "success":
            b_data = res_banks.get("banks", {})
            if isinstance(b_data, dict):
                banks_list = list(b_data.keys())
            elif isinstance(b_data, list):
                banks_list = [b.get("id", str(b)) if isinstance(b, dict) else str(b) for b in b_data]

        self.combo_banks.clear()
        self.combo_loan_bank.clear()
        for b in banks_list:
            self.combo_banks.addItem(b.title(), b)
            self.combo_loan_bank.addItem(b.title(), b)

    def _add_cash(self):
        amt = self.spin_funds.value()
        self.bridge.call_command("economy.add_funds", {
            "player_id": self.player_id,
            "amount": amt
        })
        self.refresh()

    def _set_cash(self):
        amt = self.spin_funds.value()
        self.bridge.call_command("economy.set_balance", {
            "player_id": self.player_id,
            "amount": amt
        })
        self.refresh()

    def _join_bank(self):
        bank_id = self.combo_banks.currentData()
        if bank_id:
            res = self.bridge.call_command("bank.join", {
                "player_id": self.player_id,
                "bank_id": bank_id
            })
            self.refresh()

    def _leave_bank(self):
        bank_id = self.combo_banks.currentData()
        if bank_id:
            self.bridge.call_command("bank.leave", {
                "player_id": self.player_id,
                "bank_id": bank_id
            })
            self.refresh()

    def _transfer_funds(self):
        from_c = self.combo_from_card.currentData()
        to_c = self.combo_to_card.currentData()
        amt = self.spin_trans_amt.value()
        if from_c and to_c:
            self.bridge.call_command("bank.transfer", {
                "player_id": self.player_id,
                "from_card": from_c,
                "to_card": to_c,
                "amount": amt
            })
            self.refresh()

    def _request_loan(self):
        bank_id = self.combo_loan_bank.currentData()
        amt = self.spin_loan_amt.value()
        term = self.combo_loan_term.currentData()
        if bank_id:
            self.bridge.call_command("bank.get_loan", {
                "player_id": self.player_id,
                "bank_id": bank_id,
                "amount": amt,
                "term_months": term
            })
            self.refresh()
