"""Bank system — now with real cards, limits, and universal pay.

Cards are per-player. Each bank defines per-transaction debit_limit and
credit_limit. Choosing a card at checkout enforces that limit + wallet/credit.

This is the *actual* bank system, not just dashboard code. Any shop can call
`pay_with_card(player_id, card_id, amount, desc)` —vehicle shop, future
property shop, etc. all share the same limits.

Backwards-compat: old `current_bank_member` global is kept as alias to the
first membership; but players can hold cards from multiple banks now.
"""
from __future__ import annotations

import random
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

# Bank config — load from data/banks.xml if present, else fallback
# debit_limit = per-transaction cap for debit; credit_limit = credit line.
BANKS_FALLBACK: Dict[str, Dict[str, Any]] = {
    "Westbank":       {"display": "Westbank",       "debit_limit": 15000, "credit_limit": 35000, "apr": 6.2, "color": "#1e3a8a"},
    "Coastal Credit": {"display": "Coastal Credit", "debit_limit": 8000,  "credit_limit": 50000, "apr": 9.5, "color": "#0e7490"},
    "Outback Trust":  {"display": "Outback Trust",  "debit_limit": 25000, "credit_limit": 20000, "apr": 5.0, "color": "#92400e"},
    "bank1":          {"display": "bank1",          "debit_limit": 10000, "credit_limit": 20000, "apr": 7.0, "color": "#334155"},
}

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_BANKS_PATH = _PROJECT_ROOT / "data" / "banks.xml"

_BANKS: Dict[str, Dict[str, Any]] = {}
_bank_names_cache: List[str] = []

def _load_banks():
    global _BANKS, _bank_names_cache
    if _BANKS:
        return
    # try xml
    try:
        if _BANKS_PATH.exists():
            import xml.etree.ElementTree as ET
            tree = ET.parse(str(_BANKS_PATH))
            root = tree.getroot()
            for b in root.findall("bank"):
                bid = (b.get("id") or b.findtext("id") or "").strip()
                if not bid:
                    continue
                disp = (b.get("display") or b.findtext("display") or bid).strip()
                def _int(txt, fb):
                    try: return int(float((txt or "").strip()))
                    except: return fb
                def _float(txt, fb):
                    try: return float((txt or "").strip())
                    except: return fb
                _BANKS[bid] = {
                    "display": disp,
                    "debit_limit": _int(b.findtext("debit_limit"), 10000),
                    "credit_limit": _int(b.findtext("credit_limit"), 20000),
                    "apr": _float(b.findtext("apr"), 6.2),
                    "color": (b.findtext("color") or "#334155").strip(),
                }
    except Exception:
        pass
    if not _BANKS:
        _BANKS = dict(BANKS_FALLBACK)
    _bank_names_cache = list(_BANKS.keys())
    # keep orchestrator in sync for legacy code
    try:
        import core.systems.orchestrator as _orch
        _orch.bank_names = list(_BANKS.keys())
    except Exception:
        pass

def get_bank_names() -> List[str]:
    _load_banks()
    return list(_BANKS.keys())

def get_bank_config(bank_id: str) -> Optional[Dict[str, Any]]:
    _load_banks()
    if not bank_id:
        return None
    # exact then case-insensitive
    if bank_id in _BANKS:
        return dict(_BANKS[bank_id])
    low = bank_id.strip().lower()
    for k, v in _BANKS.items():
        if k.lower() == low:
            return dict(v)
    return None

def _norm_bank_id(bank_id: str) -> Optional[str]:
    _load_banks()
    if not bank_id:
        return None
    if bank_id in _BANKS:
        return bank_id
    low = bank_id.strip().lower()
    for k in _BANKS:
        if k.lower() == low:
            return k
    return None

# --- Card storage -----------------------------------------------------------
@dataclass
class BankCard:
    card_id: str
    bank: str              # bank id, e.g. Westbank
    type: str              # debit | credit
    number: str            # masked display
    expiry: str            # MM/YY
    debit_limit: int
    credit_limit: int
    # for credit: debt outstanding; for debit: no debt
    debt: float = 0.0
    active: bool = True
    created_at: float = field(default_factory=lambda: time.time())

    def to_dict(self) -> dict:
        d = asdict(self)
        # add derived available for UI convenience
        if self.type == "credit":
            d["available"] = max(0.0, float(self.credit_limit) - float(self.debt))
        else:
            d["available"] = float(self.debit_limit)  # per-txn cap
        # also include config display/color
        cfg = _BANKS.get(self.bank) or {}
        d["display"] = cfg.get("display", self.bank)
        d["color"] = cfg.get("color", "#334155")
        d["apr"] = cfg.get("apr", 6.2)
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "BankCard":
        return cls(
            card_id=str(data.get("card_id","")),
            bank=str(data.get("bank","")),
            type=str(data.get("type","debit")),
            number=str(data.get("number","")),
            expiry=str(data.get("expiry","12/29")),
            debit_limit=int(data.get("debit_limit",0)),
            credit_limit=int(data.get("credit_limit",0)),
            debt=float(data.get("debt",0.0)),
            active=bool(data.get("active", True)),
            created_at=float(data.get("created_at", time.time())),
        )

_cards: Dict[int, List[BankCard]] = {}

def _gen_number() -> str:
    return f"{random.randint(4000,5999)}  ••{random.randint(1000,9999)}  ••{random.randint(1000,9999)}"

def _gen_expiry() -> str:
    # 2-4 years out
    year = 28 + random.randint(0,3)
    mon = random.choice(["03","06","09","12"])
    return f"{mon}/{year:02d}"

def _ensure_cards(player_id: int) -> List[BankCard]:
    _load_banks()
    pid = int(player_id)
    if pid not in _cards:
        _cards[pid] = []
    # if player has no cards but is member of a bank (legacy), create for that bank
    if not _cards[pid]:
        try:
            import core.systems.orchestrator as _orch
            cur = getattr(_orch, "current_bank_member", None)
            if cur and _norm_bank_id(cur):
                _create_cards_for_bank(pid, cur)
        except Exception:
            pass
        # still empty: create Westbank starter (so payment menu always has something)
        if not _cards[pid]:
            _create_cards_for_bank(pid, (get_bank_names() or ["Westbank"])[0])
    return _cards[pid]

def _create_cards_for_bank(player_id: int, bank_id: str) -> List[BankCard]:
    _load_banks()
    bid = _norm_bank_id(bank_id)
    if not bid:
        return []
    cfg = _BANKS[bid]
    pid = int(player_id)
    lst = _cards.setdefault(pid, [])
    # avoid dup: if already has debit+credit for this bank, return existing
    existing = [c for c in lst if c.bank == bid]
    if len(existing) >= 2:
        return existing
    created: List[BankCard] = []
    if not any(c.bank==bid and c.type=="debit" for c in lst):
        c = BankCard(
            card_id=f"card_{pid}_{bid.lower().replace(' ','_')}_debit_{uuid.uuid4().hex[:6]}",
            bank=bid, type="debit", number=_gen_number(), expiry=_gen_expiry(),
            debit_limit=int(cfg["debit_limit"]), credit_limit=int(cfg["credit_limit"]),
        )
        lst.append(c); created.append(c)
    if not any(c.bank==bid and c.type=="credit" for c in lst):
        c = BankCard(
            card_id=f"card_{pid}_{bid.lower().replace(' ','_')}_credit_{uuid.uuid4().hex[:6]}",
            bank=bid, type="credit", number=_gen_number(), expiry=_gen_expiry(),
            debit_limit=int(cfg["debit_limit"]), credit_limit=int(cfg["credit_limit"]),
        )
        lst.append(c); created.append(c)
    return created

def get_cards(player_id: int) -> List[Dict[str, Any]]:
    lst = _ensure_cards(int(player_id))
    return [c.to_dict() for c in lst if c.active]

def find_card(player_id: int, card_id: str) -> Optional[BankCard]:
    if not card_id:
        return None
    pid = int(player_id)
    lst = _cards.get(pid, [])
    cid = str(card_id).strip()
    for c in lst:
        if c.card_id == cid:
            return c
        # also allow short id prefix match
        if c.card_id.lower() == cid.lower():
            return c
    # allow bank+type shorthand like "Westbank_debit"
    low = cid.lower()
    for c in lst:
        if f"{c.bank.lower()}_{c.type}" == low:
            return c
        if c.bank.lower() == low and c.type=='debit':
            return c
    return None

def _wallet_balance(pid: int) -> float:
    try:
        from core.systems.economy.wallet import get_balance
        return float(get_balance(int(pid)))
    except Exception:
        return 0.0

def can_pay(player_id: int, card_id: str, amount: float) -> tuple[bool, str]:
    """Check if card can pay amount. Returns (ok, reason)."""
    if amount <= 0:
        return False, "Amount must be > 0"
    pid = int(player_id)
    card = find_card(pid, card_id)
    if not card:
        return False, f"Card '{card_id}' not found. Use bank.list_cards"
    if not card.active:
        return False, "Card is inactive"
    amt = float(amount)
    if card.type == "debit":
        # per-transaction limit
        if amt - 1e-9 > float(card.debit_limit):
            return False, f"Transaction Failed — {card.bank} debit limit is ${card.debit_limit:,} per transaction (tried ${amt:,.0f})"
        # also need wallet funds
        bal = _wallet_balance(pid)
        if bal + 1e-9 < amt:
            return False, f"Transaction Failed — insufficient cash ${bal:,.0f} < ${amt:,.0f}"
        return True, "ok"
    else:  # credit
        avail = float(card.credit_limit) - float(card.debt)
        if amt - 1e-9 > float(card.credit_limit):
            return False, f"Transaction Failed — {card.bank} credit limit is ${card.credit_limit:,} (tried ${amt:,.0f})"
        if amt - 1e-9 > avail:
            return False, f"Transaction Failed — {card.bank} credit available ${avail:,.0f} < ${amt:,.0f} (limit ${card.credit_limit:,}, debt ${card.debt:,.0f})"
        return True, "ok"

def pay_with_card(player_id: int, card_id: str, amount: float, description: str = "") -> dict:
    """Attempt to pay amount with card. Returns status dict.
    On debit: deducts wallet. On credit: increases debt.
    Emits output bus for UI toasts.
    """
    _load_banks()
    pid = int(player_id)
    amt = float(amount)
    card = find_card(pid, card_id)
    if not card:
        return {"status": "error", "message": f"Card '{card_id}' not found"}
    ok, reason = can_pay(pid, card_id, amt)
    if not ok:
        try:
            from core.output import warning as _warn
            _warn(reason, channel="toast", source="bank")
        except Exception:
            pass
        return {"status": "error", "message": reason, "card": card.to_dict(), "amount": amt}

    # perform deduction
    try:
        if card.type == "debit":
            from core.systems.economy.wallet import deduct_funds, get_balance
            if not deduct_funds(pid, amt):
                return {"status": "error", "message": f"Transaction Failed — could not deduct ${amt:,.0f}"}
            bal = get_balance(pid)
            card_info = card.to_dict()
            try:
                from core.output import success as _suc
                _suc(f"Paid ${amt:,.0f} with {card.bank} debit • {card.number} — {description}" if description else f"Paid ${amt:,.0f} with {card.bank} debit", source="bank")
            except Exception:
                pass
            return {"status": "success", "message": f"Paid ${amt:,.0f} with {card.bank} debit", "card": card_info, "balance": bal, "amount": amt, "type": "debit"}
        else:
            card.debt = float(card.debt) + amt
            try:
                from core.output import success as _suc
                _suc(f"Charged ${amt:,.0f} to {card.bank} credit • {card.number} — debt ${card.debt:,.0f}/{card.credit_limit:,}" + (f" — {description}" if description else ""), source="bank")
            except Exception:
                pass
            return {"status": "success", "message": f"Charged ${amt:,.0f} to {card.bank} credit", "card": card.to_dict(), "debt": card.debt, "available": float(card.credit_limit)-float(card.debt), "amount": amt, "type": "credit"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def pay_debt(player_id: int, card_id: str, amount: float) -> dict:
    """Pay down credit debt (from wallet)."""
    pid = int(player_id)
    card = find_card(pid, card_id)
    if not card:
        return {"status": "error", "message": "Card not found"}
    if card.type != "credit":
        return {"status": "error", "message": "Only credit cards have debt"}
    if amount <=0:
        return {"status": "error", "message": "Amount must be >0"}
    if card.debt + 1e-9 < amount:
        amount = float(card.debt)
    # need wallet funds
    bal = _wallet_balance(pid)
    if bal + 1e-9 < amount:
        return {"status": "error", "message": f"Insufficient cash ${bal:,.0f} < ${amount:,.0f}"}
    try:
        from core.systems.economy.wallet import deduct_funds
        if not deduct_funds(pid, float(amount)):
            return {"status": "error", "message": "Deduct failed"}
        card.debt = max(0.0, float(card.debt) - float(amount))
        return {"status": "success", "message": f"Paid ${amount:,.0f} toward {card.bank} credit", "card": card.to_dict()}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Legacy orchestrator sync
try:
    import core.systems.orchestrator as _orch
    # keep bank_names in sync
    _load_banks()
    _orch.bank_names = get_bank_names()
except Exception:
    pass

# --- Commands --------------------------------------------------------------
try:
    from core.command_registry import command as _command
except ImportError:
    def _command(*a, **k):
        def _d(fn): return fn
        return _d

try:
    from core.systems.orchestrator import inform_player as _infp, warning as _warn2
    import core.systems.orchestrator as _orch2
except ImportError:
    try:
        from orchestrator import inform_player as _infp, warning as _warn2
        import orchestrator as _orch2
    except Exception:
        def _infp(m): print(m)
        def _warn2(m): print(m)
        _orch2 = None

@_command("bank.apply", "Apply for bank membership (creates debit+credit cards)", category="player")
def apply_bank_membership(player_id, bank_name):
    _load_banks()
    bid = _norm_bank_id(str(bank_name or ""))
    if not bid:
        _warn2(f"Bank '{bank_name}' does not exist. Available: {get_bank_names()}")
        return {"status": "error", "message": f"Unknown bank '{bank_name}'"}
    pid = int(player_id) if str(player_id).strip().isdigit() or isinstance(player_id, int) else 1
    # handle string-first calling style (bank.apply bank1)
    if isinstance(player_id, str) and not str(bank_name).strip():
        # called as apply(bank_name) via positional
        pid = 1
        bid = _norm_bank_id(str(player_id))
        if not bid:
            return {"status": "error", "message": f"Unknown bank '{player_id}'"}
    # for backward compat, if bank_name empty and player_id is bank string
    if isinstance(player_id, str) and bank_name in ("", None):
        # try interpret player_id as bank
        maybe = _norm_bank_id(str(player_id))
        if maybe:
            bid = maybe
            pid = 1
    bid = _norm_bank_id(bid) or bid
    # legacy global membership keeps first bank for HUD
    try:
        if _orch2 is not None and getattr(_orch2, "current_bank_member", None) is None:
            _orch2.current_bank_member = bid
    except Exception:
        pass
    created = _create_cards_for_bank(pid, bid)
    try:
        from core.output import success as _suc
        if created:
            _suc(f"Joined {bid} — issued {len(created)} card(s) for player {pid}", source="bank")
        else:
            _suc(f"Already member of {bid} (player {pid})", source="bank")
    except Exception:
        pass
    cards = get_cards(pid)
    return {"status": "success", "message": f"Member of {bid}", "bank": bid, "cards_created": [c.to_dict() for c in created], "cards": cards}

@_command("bank.get_loan", "Request a bank loan (placeholder — use payment menu for real credit)", category="player")
def get_bank_loan(player_id: int = 1, amount: float = 0, term: int = 12, bank: str = ""):
    # keep placeholder but now also supports amount/term
    if amount and float(amount) > 0:
        # delegate to apply-like check
        bid = _norm_bank_id(bank or (get_bank_names()[0] if get_bank_names() else "Westbank"))
        return {"status": "success", "message": f"Loan request ${float(amount):,.0f} over {int(term)}mo @ {bid} — use the Payment Menu for full preview (cards enforce limits).", "bank": bid, "amount": float(amount), "term": int(term)}
    try:
        from core.systems.orchestrator import request_player_input as _rpi
        _rpi("This Bank Supports loans! Though i havent implemented the loan system yet... check back later :D")
    except Exception:
        pass
    return {"status": "success", "message": "Loan placeholder — use Economy Menu → Loans → Get a Loan (UI has slider + preview, backed by bank pay limits)."}

@_command("bank.list_cards", "List active bank cards with limits (debit/credit)", category="player")
def list_active_cards(player_id: int = 1):
    pid = int(player_id) if isinstance(player_id, (int, str)) and str(player_id).strip().lstrip("-").isdigit() else 1
    # flexible: if called as list_cards("Westbank") treat as player 1
    if isinstance(player_id, str) and not str(player_id).strip().isdigit():
        # maybe they passed bank filter? ignore, return all for player 1
        pid = 1
    cards = get_cards(pid)
    return {"status": "success", "cards": cards, "count": len(cards), "player_id": pid, "banks": get_bank_names()}

@_command("bank.pay", "Pay amount with a specific card (enforces per-transaction limit)", category="player")
def bank_pay(player_id: int, card_id: str, amount: float, description: str = ""):
    """Generic pay: bank.pay player_id=1 card_id=card_... amount=5000"""
    return pay_with_card(int(player_id), str(card_id), float(amount), str(description or ""))

@_command("bank.pay_debt", "Pay down credit card debt from wallet", category="player")
def bank_pay_debt(player_id: int, card_id: str, amount: float):
    return pay_debt(int(player_id), str(card_id), float(amount))

@_command("bank.banks", "List available banks and their limits", category="player")
def bank_list_banks():
    _load_banks()
    return {"status": "success", "banks": {k: dict(v) for k, v in _BANKS.items()}}

current_bank_supports_loans = True  # kept for compat

# --- Save / Load -----------------------------------------------------------
def _save_bank():
    out: Dict[str, Any] = {}
    for pid, lst in _cards.items():
        out[str(pid)] = [c.to_dict() for c in lst]
    # also include bank config snapshot? not needed
    return {"cards": out, "banks": {k: dict(v) for k, v in _BANKS.items()}}

def _load_bank(state):
    if not isinstance(state, dict):
        return
    # support both {"cards": {...}} and flat {pid: [cards]}
    src = state.get("cards") if isinstance(state.get("cards"), dict) else state
    if not isinstance(src, dict):
        return
    _cards.clear()
    for k, lst in src.items():
        try:
            pid = int(k)
            if not isinstance(lst, list):
                continue
            _cards[pid] = [BankCard.from_dict(d) for d in lst if isinstance(d, dict)]
        except Exception:
            continue
    # also restore legacy current_bank_member if set
    try:
        if _orch2 is not None and state.get("current_member"):
            _orch2.current_bank_member = state.get("current_member")
    except Exception:
        pass

# public alias for HUD code (dashboard imports BANKS)
BANKS = _BANKS

try:
    from core.systems.save.registry import register_save_provider as _reg
    _reg("bank", _save_bank, _load_bank)
    _reg("bank_cards", _save_bank, _load_bank)  # alias
except Exception:
    pass
