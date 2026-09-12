"""
Wallet — thin wrapper over core.systems.state for Vehicle Shop (and future economy).

All money + save/load lives in state.py now. This module keeps the old
`wallet` API / economy.* commands working so shops, bank, and HUD don't break.
"""

from __future__ import annotations

from core.command_registry import command
from core.systems import state as _state

DEFAULT_BALANCE = _state.DEFAULT_MONEY


def get_balance(player_id: int) -> float:
    return _state.get_balance(player_id)


def set_balance(player_id: int, amount: float) -> float:
    return _state.set_balance(player_id, amount)


def add_funds(player_id: int, amount: float) -> float:
    return _state.add_funds(player_id, amount)


def deduct_funds(player_id: int, amount: float) -> bool:
    return _state.deduct_funds(player_id, amount)


def can_afford(player_id: int, amount: float) -> bool:
    return _state.can_afford(player_id, amount)


@command("economy.balance", "Get player balance", category="player")
def economy_balance(player_id: int = 1) -> dict:
    bal = get_balance(int(player_id))
    return {"status": "success", "player_id": int(player_id), "balance": bal}

@command("economy.add_funds", "Add funds to player (dev)", category="dev")
def economy_add_funds(player_id: int, amount: float) -> dict:
    new_bal = add_funds(int(player_id), float(amount))
    return {"status": "success", "player_id": int(player_id), "balance": new_bal, "added": float(amount)}

@command("economy.set_balance", "Set player balance (dev)", category="dev")
def economy_set_balance(player_id: int, amount: float) -> dict:
    new_bal = set_balance(int(player_id), float(amount))
    return {"status": "success", "player_id": int(player_id), "balance": new_bal}

@command("economy.can_afford", "Check if player can afford amount", category="player")
def economy_can_afford(player_id: int, amount: float) -> dict:
    ok = can_afford(int(player_id), float(amount))
    bal = get_balance(int(player_id))
    return {"status": "success", "player_id": int(player_id), "balance": bal, "amount": float(amount), "can_afford": ok}

__all__ = ["get_balance", "set_balance", "add_funds", "deduct_funds", "can_afford", "DEFAULT_BALANCE"]
