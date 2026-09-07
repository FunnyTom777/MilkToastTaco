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
    "Westbank":         {"display": "Westbank",         "debit_limit": 15000, "credit_limit": 35000, "apr": 6.2, "color": "#1e3a8a", "subscription_fee": 0,  "icon": "building-columns", "tier": "starter",  "description": "Friendly neighborhood bank. No monthly fees."},
    "Coastal Credit":   {"display": "Coastal Credit",   "debit_limit": 8000,  "credit_limit": 50000, "apr": 9.5, "color": "#0e7490", "subscription_fee": 25, "icon": "water",            "tier": "standard", "description": "High credit line, $25/mo."},
    "Outback Trust":    {"display": "Outback Trust",    "debit_limit": 25000, "credit_limit": 20000, "apr": 5.0, "color": "#92400e", "subscription_fee": 15, "icon": "tractor",          "tier": "standard", "description": "Biggest debit limits, $15/mo."},
    "Luxe Private":     {"display": "Luxe Private",     "debit_limit": 40000, "credit_limit": 100000,"apr": 4.2, "color": "#6b21a8", "subscription_fee": 75, "icon": "crown",            "tier": "premium",  "description": "Private banking, $75/mo exclusive."},
    "Budget Direct":    {"display": "Budget Direct",    "debit_limit": 5000,  "credit_limit": 10000, "apr": 11.0,"color": "#334155", "subscription_fee": 0,  "icon": "piggy-bank",       "tier": "starter",  "description": "No-frills, no fees."},
    "City Central Bank":{"display": "City Central Bank","debit_limit": 20000, "credit_limit": 40000, "apr": 7.5, "color": "#0f766e", "subscription_fee": 10, "icon": "city",             "tier": "standard", "description": "Balanced limits, $10/mo."},
    "bank1":            {"display": "bank1",            "debit_limit": 10000, "credit_limit": 20000, "apr": 7.0, "color": "#334155", "subscription_fee": 0,  "icon": "building-columns", "tier": "starter",  "description": "Legacy bank."},
}

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_BANKS_PATH = _PROJECT_ROOT / "data" / "banks.xml"

_BANKS: Dict[str, Dict[str, Any]] = {}
_bank_names_cache: List[str] = []

def _load_banks(force: bool = False):
    global _BANKS, _bank_names_cache
    if _BANKS and not force:
        return
    if force:
        _BANKS.clear()
        _bank_names_cache.clear()
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
                    "subscription_fee": _int(b.findtext("subscription_fee"), 0),
                    "icon": (b.findtext("icon") or "building-columns").strip(),
                    "tier": (b.findtext("tier") or "standard").strip(),
                    "description": (b.findtext("description") or "").strip(),
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

def reload_banks() -> Dict[str, Dict[str, Any]]:
    """Force reload from XML (for tests/dev)."""
    _load_banks(force=True)
    return {k: dict(v) for k, v in _BANKS.items()}

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
        d["subscription_fee"] = cfg.get("subscription_fee", 0)
        d["icon"] = cfg.get("icon", "building-columns")
        d["tier"] = cfg.get("tier", "standard")
        d["description"] = cfg.get("description", "")
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
    """Return cards for player WITHOUT auto-creating.

    New players start with 0 cards. Legacy saves still load via _load_bank.
    Previously this auto-created Westbank/bank1 starter cards; that behavior
    is now removed per design (user requested 0 cards on new game).
    """
    _load_banks()
    pid = int(player_id)
    if pid not in _cards:
        _cards[pid] = []
    return _cards[pid]

# alias kept for older code paths that imported _ensure_cards expecting auto-create
def _ensure_cards_legacy(player_id: int) -> List[BankCard]:
    """Legacy helper that would auto-create starter cards. No longer used."""
    return _ensure_cards(player_id)

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

def get_memberships(player_id: int) -> List[Dict[str, Any]]:
    """Return bank memberships for player (banks where they have cards)."""
    _load_banks()
    pid = int(player_id)
    lst = _cards.get(pid, [])
    banks_seen: Dict[str, Dict[str, Any]] = {}
    for c in lst:
        if not c.active:
            continue
        bid = c.bank
        if bid in banks_seen:
            continue
        cfg = _BANKS.get(bid, {})
        # gather card ids for this bank
        cards_for_bank = [x for x in lst if x.bank == bid and x.active]
        banks_seen[bid] = {
            "id": bid,
            "display": cfg.get("display", bid),
            "color": cfg.get("color", "#334155"),
            "icon": cfg.get("icon", "building-columns"),
            "tier": cfg.get("tier", "standard"),
            "description": cfg.get("description", ""),
            "debit_limit": cfg.get("debit_limit", 0),
            "credit_limit": cfg.get("credit_limit", 0),
            "apr": cfg.get("apr", 0),
            "subscription_fee": cfg.get("subscription_fee", 0),
            "card_count": len(cards_for_bank),
            "cards": [x.to_dict() for x in cards_for_bank],
            "debt": sum(float(x.debt) for x in cards_for_bank if x.type == "credit"),
        }
    return list(banks_seen.values())

def get_all_banks_for_player(player_id: int) -> List[Dict[str, Any]]:
    """All banks with membership flag for join/membership UI."""
    _load_banks()
    pid = int(player_id)
    lst = _cards.get(pid, [])
    owned = {c.bank for c in lst if c.active}
    out: List[Dict[str, Any]] = []
    for bid, cfg in _BANKS.items():
        out.append({
            "id": bid,
            "display": cfg.get("display", bid),
            "color": cfg.get("color", "#334155"),
            "icon": cfg.get("icon", "building-columns"),
            "tier": cfg.get("tier", "standard"),
            "description": cfg.get("description", ""),
            "debit_limit": cfg.get("debit_limit", 0),
            "credit_limit": cfg.get("credit_limit", 0),
            "apr": cfg.get("apr", 0),
            "subscription_fee": cfg.get("subscription_fee", 0),
            "is_member": bid in owned,
        })
    # sort: members first, then by tier, then name
    tier_order = {"starter": 0, "standard": 1, "premium": 2}
    out.sort(key=lambda b: (not b["is_member"], tier_order.get(b["tier"], 9), b["display"]))
    return out

def leave_bank(player_id: int, bank_id: str) -> dict:
    _load_banks()
    bid = _norm_bank_id(str(bank_id or ""))
    if not bid:
        return {"status": "error", "message": f"Unknown bank '{bank_id}'"}
    pid = int(player_id)
    lst = _cards.get(pid, [])
    # prevent leaving if credit debt remains
    debt = sum(float(c.debt) for c in lst if c.bank == bid and c.type == "credit")
    if debt > 1e-9:
        return {"status": "error", "message": f"Cannot leave {bid}: pay off credit debt ${debt:,.0f} first (bank.pay_debt)"}
    before = len(lst)
    _cards[pid] = [c for c in lst if c.bank != bid]
    after = len(_cards[pid])
    if before == after:
        return {"status": "error", "message": f"Not a member of {bid}"}
    # update legacy current_bank_member if it was this one
    try:
        import core.systems.orchestrator as _orch
        if getattr(_orch, "current_bank_member", None) == bid:
            # set to another membership or None
            remaining = {c.bank for c in _cards[pid] if c.active}
            _orch.current_bank_member = next(iter(remaining), None)
    except Exception:
        pass
    return {"status": "success", "message": f"Left {bid}", "bank": bid, "cards_removed": before - after}

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

@_command("bank.memberships", "List current bank memberships for player", category="player")
def bank_memberships(player_id: int = 1):
    pid = int(player_id) if str(player_id).strip().lstrip("-").isdigit() else 1
    mems = get_memberships(pid)
    total_fee = sum(int(m.get("subscription_fee", 0)) for m in mems)
    return {"status": "success", "player_id": pid, "memberships": mems, "count": len(mems), "total_monthly_fee": total_fee}

@_command("bank.all", "List all banks with membership flag for player (for UI)", category="player")
def bank_all(player_id: int = 1):
    pid = int(player_id) if str(player_id).strip().lstrip("-").isdigit() else 1
    banks = get_all_banks_for_player(pid)
    mems = get_memberships(pid)
    total_fee = sum(int(m.get("subscription_fee", 0)) for m in mems)
    return {"status": "success", "player_id": pid, "banks": banks, "memberships": mems, "total_monthly_fee": total_fee, "count": len(banks)}

@_command("bank.join", "Join a bank (creates debit+credit cards, friendly wrapper for bank.apply)", category="player")
def bank_join(player_id: int = 1, bank_name: str = ""):
    # allow calling as bank.join "Westbank" (single string arg -> treat as bank)
    if isinstance(player_id, str) and not bank_name:
        bank_name = player_id
        player_id = 1
    return apply_bank_membership(int(player_id) if str(player_id).strip().lstrip("-").isdigit() else 1, str(bank_name))

@_command("bank.leave", "Leave a bank (removes cards, must clear debt first)", category="player")
def bank_leave(player_id: int = 1, bank_name: str = ""):
    if isinstance(player_id, str) and not bank_name:
        bank_name = player_id
        player_id = 1
    pid = int(player_id) if str(player_id).strip().lstrip("-").isdigit() else 1
    return leave_bank(pid, str(bank_name))

current_bank_supports_loans = True  # kept for compat

# --- Save / Load -----------------------------------------------------------
def _save_bank():
    out: Dict[str, Any] = {}
    for pid, lst in _cards.items():
        out[str(pid)] = [c.to_dict() for c in lst]
    # also include bank config snapshot + legacy current_member for HUD
    try:
        cur = getattr(_orch2, "current_bank_member", None) if _orch2 else None
    except Exception:
        cur = None
    return {"cards": out, "banks": {k: dict(v) for k, v in _BANKS.items()}, "current_member": cur}

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
    # restore legacy current_bank_member if set, otherwise derive from cards
    try:
        if _orch2 is not None:
            if state.get("current_member"):
                _orch2.current_bank_member = state.get("current_member")
            else:
                # derive: first bank with cards, or None if 0 cards
                found = None
                for pid, lst in _cards.items():
                    if lst:
                        found = lst[0].bank
                        break
                _orch2.current_bank_member = found
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
