"""
Bank & Economy Tab for Dashboard V4 — with sub-tabs for friendly navigation.
Mirrors V2's Economy sub-menus (wallet, banks, transfers, loans) but uses
default Qt styling and native QTabWidget nesting.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QComboBox, QGroupBox, QSpinBox,
    QDoubleSpinBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QTabWidget, QMessageBox
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
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(8, 8, 8, 8)

        desc = QLabel("Manage wallet, bank cards, memberships, transfers and loans. Each sub-tab focuses on one task — like V2's Economy menu.")
        desc.setWordWrap(True)
        main_layout.addWidget(desc)

        self.sub_tabs = QTabWidget()

        # --- Sub-tab: Wallet ---
        wallet_page = QWidget()
        wallet_layout = QVBoxLayout(wallet_page)
        wallet_layout.setContentsMargins(12, 12, 12, 12)
        wallet_layout.setSpacing(10)

        wallet_group = QGroupBox("Cash Wallet")
        wlay = QHBoxLayout(wallet_group)
        self.lbl_wallet = QLabel("Wallet Balance: $0")
        wlay.addWidget(self.lbl_wallet)
        wlay.addStretch()
        wlay.addWidget(QLabel("Amount:"))
        self.spin_funds = QDoubleSpinBox()
        self.spin_funds.setRange(1, 1000000)
        self.spin_funds.setValue(1000)
        self.spin_funds.setPrefix("$")
        wlay.addWidget(self.spin_funds)
        btn_add = QPushButton("Deposit Cash")
        btn_add.clicked.connect(self._add_cash)
        wlay.addWidget(btn_add)
        btn_set = QPushButton("Set Balance")
        btn_set.clicked.connect(self._set_cash)
        wlay.addWidget(btn_set)
        wallet_layout.addWidget(wallet_group)
        wallet_layout.addStretch()
        wallet_layout.addWidget(QLabel("Tip: Deposit adds funds, Set overwrites the balance."))
        self.sub_tabs.addTab(wallet_page, "Wallet")

        # --- Sub-tab: Cards & Banks ---
        cards_page = QWidget()
        cards_layout = QVBoxLayout(cards_page)
        cards_layout.setContentsMargins(12, 12, 12, 12)
        cards_layout.setSpacing(10)

        # Cards table
        cards_group = QGroupBox("Bank Accounts & Cards")
        cl = QVBoxLayout(cards_group)
        self.table_cards = QTableWidget(0, 4)
        self.table_cards.setHorizontalHeaderLabels(["Bank", "Card Number", "Balance", "Type"])
        self.table_cards.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_cards.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        cl.addWidget(self.table_cards)
        cards_layout.addWidget(cards_group)

        # Memberships + actions
        mems_group = QGroupBox("Bank Memberships")
        ml = QVBoxLayout(mems_group)
        self.table_mems = QTableWidget(0, 3)
        self.table_mems.setHorizontalHeaderLabels(["Bank ID", "Monthly Fee", "Status"])
        self.table_mems.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_mems.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        ml.addWidget(self.table_mems)

        mem_act_layout = QHBoxLayout()
        self.combo_banks = QComboBox()
        mem_act_layout.addWidget(self.combo_banks)
        btn_join = QPushButton("Join Bank")
        btn_join.clicked.connect(self._join_bank)
        mem_act_layout.addWidget(btn_join)
        btn_leave = QPushButton("Leave Bank")
        btn_leave.clicked.connect(self._leave_bank)
        mem_act_layout.addWidget(btn_leave)
        mem_act_layout.addStretch()
        ml.addLayout(mem_act_layout)
        cards_layout.addWidget(mems_group)
        self.sub_tabs.addTab(cards_page, "Cards & Banks")

        # --- Sub-tab: Transfers ---
        trans_page = QWidget()
        trans_layout_wrap = QVBoxLayout(trans_page)
        trans_layout_wrap.setContentsMargins(12, 12, 12, 12)
        transfer_group = QGroupBox("Transfer Funds Between Cards")
        trans_l = QGridLayout(transfer_group)
        trans_l.addWidget(QLabel("From Card:"), 0, 0)
        self.combo_from_card = QComboBox()
        trans_l.addWidget(self.combo_from_card, 0, 1)
        trans_l.addWidget(QLabel("To Card:"), 1, 0)
        self.combo_to_card = QComboBox()
        trans_l.addWidget(self.combo_to_card, 1, 1)
        trans_l.addWidget(QLabel("Amount:"), 2, 0)
        self.spin_trans_amt = QDoubleSpinBox()
        self.spin_trans_amt.setRange(1, 1000000)
        self.spin_trans_amt.setValue(500)
        self.spin_trans_amt.setPrefix("$")
        trans_l.addWidget(self.spin_trans_amt, 2, 1)
        btn_trans = QPushButton("Send Transfer")
        btn_trans.clicked.connect(self._transfer_funds)
        trans_l.addWidget(btn_trans, 3, 0, 1, 2)
        trans_layout_wrap.addWidget(transfer_group)
        trans_layout_wrap.addWidget(QLabel("Transfers move money between your own cards at the same or different banks."))
        trans_layout_wrap.addStretch()
        self.sub_tabs.addTab(trans_page, "Transfers")

        # --- Sub-tab: Loans ---
        loan_page = QWidget()
        loan_wrap = QVBoxLayout(loan_page)
        loan_wrap.setContentsMargins(12, 12, 12, 12)
        loan_group = QGroupBox("Apply for Bank Loan")
        loan_l = QGridLayout(loan_group)
        loan_l.addWidget(QLabel("Bank:"), 0, 0)
        self.combo_loan_bank = QComboBox()
        loan_l.addWidget(self.combo_loan_bank, 0, 1)
        loan_l.addWidget(QLabel("Loan Amount:"), 1, 0)
        self.spin_loan_amt = QDoubleSpinBox()
        self.spin_loan_amt.setRange(100, 500000)
        self.spin_loan_amt.setValue(10000)
        self.spin_loan_amt.setPrefix("$")
        loan_l.addWidget(self.spin_loan_amt, 1, 1)
        loan_l.addWidget(QLabel("Term:"), 2, 0)
        self.combo_loan_term = QComboBox()
        self.combo_loan_term.addItem("12 Months", 12)
        self.combo_loan_term.addItem("24 Months", 24)
        self.combo_loan_term.addItem("36 Months", 36)
        self.combo_loan_term.addItem("60 Months", 60)
        loan_l.addWidget(self.combo_loan_term, 2, 1)
        btn_loan = QPushButton("Request Loan")
        btn_loan.clicked.connect(self._request_loan)
        loan_l.addWidget(btn_loan, 3, 0, 1, 2)
        loan_wrap.addWidget(loan_group)
        loan_wrap.addWidget(QLabel("Loans are per-bank and add a monthly repayment. Check memberships for active loans/fees."))
        loan_wrap.addStretch()
        self.sub_tabs.addTab(loan_page, "Loans")

        main_layout.addWidget(self.sub_tabs)

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
