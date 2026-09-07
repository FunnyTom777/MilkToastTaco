"""
Wallet — simple per-player money for Vehicle Shop (and future economy).

Provides balance, add/deduct, and save/load. Separate from bank membership.
"""

from __future__ import annotations
from typing import Dict

from core.command_registry import command

try:
    from core.systems.orchestrator import warning as _warn
except ImportError:
    def _warn(m): print(m)

try:
    from core.output import success as _success, warning as _out_warn, info as _info
except ImportError:
    def _success(*a, **k): pass
    def _out_warn(*a, **k): pass
    def _info(*a, **k): pass

DEFAULT_BALANCE = 0  # was 75000 — now debit cards start empty until you transfer, so wallet starts at 0

_balances: Dict[int, float] = {}

def _ensure(player_id: int) -> float:
    pid = int(player_id)
    if pid not in _balances:
        _balances[pid] = float(DEFAULT_BALANCE)
        # ensure inventory etc exists too — best effort
    return _balances[pid]

def get_balance(player_id: int) -> float:
    pid = int(player_id)
    if pid not in _balances:
        _ensure(pid)
    return float(_balances[pid])

def set_balance(player_id: int, amount: float) -> float:
    if amount < 0:
        raise ValueError("amount must be >= 0")
    pid = int(player_id)
    _balances[pid] = float(amount)
    return float(amount)

def add_funds(player_id: int, amount: float) -> float:
    if amount <= 0:
        raise ValueError("amount must be > 0")
    pid = int(player_id)
    _ensure(pid)
    _balances[pid] = float(_balances[pid] + amount)
    return float(_balances[pid])

def deduct_funds(player_id: int, amount: float) -> bool:
    """Deduct if enough funds. Returns True on success, False if insufficient."""
    if amount <= 0:
        raise ValueError("amount must be > 0")
    pid = int(player_id)
    _ensure(pid)
    if _balances[pid] + 1e-9 < amount:
        return False
    _balances[pid] = float(_balances[pid] - amount)
    return True

def can_afford(player_id: int, amount: float) -> bool:
    return get_balance(player_id) + 1e-9 >= amount

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

# Save / Load
def _save_wallet():
    return {str(pid): float(bal) for pid, bal in _balances.items()}

def _load_wallet(state):
    if not isinstance(state, dict):
        _warn(f"_load_wallet: expected dict, got {type(state).__name__}")
        return
    _balances.clear()
    for k, v in state.items():
        try:
            pid = int(k)
            _balances[pid] = float(v)
        except Exception as e:
            _warn(f"_load_wallet for '{k}': {e}")

try:
    from core.systems.save.registry import register_save_provider as _reg
    _reg("wallet", _save_wallet, _load_wallet)
    _reg("economy", _save_wallet, _load_wallet)  # alias for HUD expects economy key
except Exception:
    pass

__all__ = ["get_balance", "set_balance", "add_funds", "deduct_funds", "can_afford", "DEFAULT_BALANCE"]
