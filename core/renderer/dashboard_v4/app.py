"""
MTT Dashboard V4 — Dear ImGui app (minimal, controller + KBM).

No custom styling — just basic ImGui menus/elements that Just Work.
Controller (L-stick/D-pad -> nav, A -> activate, B -> cancel) and
keyboard (arrows + Enter/Esc) both drive ImGui nav; mouse stays live.

Run via dashboard_v4.run() or python -m core.renderer.dashboard_v4.dashboard_v4.
"""

from __future__ import annotations

import datetime
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

TABS: List[Tuple[str, str]] = [
    ("home", "Home"),
    ("wallet", "Wallet"),
    ("inventory", "Inventory"),
    ("garage", "Garage"),
    ("estates", "Estates"),
    ("players", "Players"),
    ("phone", "Phone"),
    ("saves", "Saves"),
    ("settings", "Settings"),
]


def fmt_cur(n: Any) -> str:
    try:
        return f"${int(float(n)):,}"
    except Exception:
        return f"${str(n)}"


def fmt_time(iso: Any) -> str:
    if not iso:
        return "—"
    try:
        d = datetime.datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        return d.strftime("%Y-%m-%d %H:%M")
    except Exception:
        try:
            d = datetime.datetime.strptime(str(iso)[:19], "%Y-%m-%dT%H:%M:%S")
            return d.strftime("%Y-%m-%d %H:%M")
        except Exception:
            return str(iso)


class GamepadBridge:
    """Poll pygame joystick -> imgui nav_inputs (D-pad/L-stick + A/B)."""

    def __init__(self, deadzone: float = 0.45, thresh: float = 0.55):
        self.deadzone = deadzone
        self.thresh = thresh
        self.connected: bool = False
        self.name: Optional[str] = None
        self._joys: List[Any] = []

    def refresh(self):
        import pygame

        try:
            pygame.joystick.init()
            count = pygame.joystick.get_count()
            self._joys = [pygame.joystick.Joystick(i) for i in range(count)]
            for j in self._joys:
                try:
                    j.init()
                except Exception:
                    pass
            if count:
                self.connected = True
                try:
                    self.name = self._joys[0].get_name()
                except Exception:
                    self.name = f"pad#{count}"
            else:
                self.connected = False
                self.name = None
        except Exception:
            self.connected = False
            self.name = None

    def poll(self, io) -> None:
        import imgui
        import pygame

        nav = io.nav_inputs
        ax0 = ax1 = 0.0
        btn = lambda idx: False
        hat0 = (0, 0)
        pad = None
        if self._joys:
            try:
                pad = self._joys[0]
                if pad.get_numaxes() >= 2:
                    ax0 = float(pad.get_axis(0))
                    ax1 = float(pad.get_axis(1))
                if pad.get_numhats() >= 1:
                    hat0 = pad.get_hat(0)

                def _btn(i: int) -> bool:
                    try:
                        return bool(pad.get_button(i))
                    except Exception:
                        return False

                btn = _btn
            except Exception:
                hat0 = (0, 0)

        dz = self.deadzone
        if abs(ax0) < dz:
            ax0 = 0.0
        if abs(ax1) < dz:
            ax1 = 0.0
        thr = self.thresh
        a = btn(0)
        b = btn(1)
        x = btn(2)
        start = btn(7) if pad and pad.get_numbuttons() > 7 else False
        d_up = hat0[1] == 1
        d_down = hat0[1] == -1
        d_left = hat0[0] == -1
        d_right = hat0[0] == 1
        l_up = ax1 < -thr
        l_down = ax1 > thr
        l_left = ax0 < -thr
        l_right = ax0 > thr

        try:
            def _set(idx: int, val: bool):
                nav[idx] = 1.0 if val else (nav[idx] if nav[idx] else 0.0)

            _set(imgui.NAV_INPUT_DPAD_LEFT, d_left or l_left)
            _set(imgui.NAV_INPUT_DPAD_RIGHT, d_right or l_right)
            _set(imgui.NAV_INPUT_DPAD_UP, d_up or l_up)
            _set(imgui.NAV_INPUT_DPAD_DOWN, d_down or l_down)
            _set(imgui.NAV_INPUT_L_STICK_LEFT, l_left)
            _set(imgui.NAV_INPUT_L_STICK_RIGHT, l_right)
            _set(imgui.NAV_INPUT_L_STICK_UP, l_up)
            _set(imgui.NAV_INPUT_L_STICK_DOWN, l_down)
            _set(imgui.NAV_INPUT_ACTIVATE, a)
            _set(imgui.NAV_INPUT_CANCEL, b)
            _set(imgui.NAV_INPUT_MENU, start)
            _set(imgui.NAV_INPUT_INPUT, x)
        except Exception:
            pass


def run_app(api: Any, width: int = 1280, height: int = 800, fullscreen: bool = False, debug: bool = False):
    import pygame
    import OpenGL.GL as gl
    import imgui
    from imgui.integrations.pygame import PygameRenderer

    pygame.init()
    pygame.joystick.init()

    flags = pygame.OPENGL | pygame.DOUBLEBUF | pygame.RESIZABLE
    if fullscreen:
        flags |= pygame.FULLSCREEN
    try:
        pygame.display.set_mode((width, height), flags)
    except Exception as e:
        print(f"[V4] display.set_mode failed: {e}", file=sys.stderr)
        pygame.display.set_mode((width, height), pygame.OPENGL | pygame.DOUBLEBUF)

    pygame.display.set_caption("Milk Toast Taco — Dashboard V4 (ImGui)")

    imgui.create_context()
    io = imgui.get_io()
    io.display_size = (float(width), float(height))
    io.display_fb_scale = (1.0, 1.0)
    io.config_flags |= imgui.CONFIG_NAV_ENABLE_KEYBOARD | imgui.CONFIG_NAV_ENABLE_GAMEPAD
    try:
        saves_dir = Path(__file__).resolve().parents[3] / "saves"
        saves_dir.mkdir(parents=True, exist_ok=True)
        io.ini_file_name = str(saves_dir / "imgui_v4.ini").encode()
    except Exception:
        io.ini_file_name = b"imgui_v4.ini"

    # Use default ImGui style — no custom theming.
    # Keep a tiny touch: a bit of rounding so controller focus ring looks decent.
    style = imgui.get_style()
    style.frame_padding = (8, 4)
    style.window_padding = (8, 8)

    renderer = PygameRenderer()

    # State
    api_state: Dict[str, Any] = {}
    hud: Dict[str, Any] = {}
    systems: Dict[str, Any] = {}
    saves: List[str] = []
    detailed_saves: List[Dict[str, Any]] = []
    selected_save: Optional[str] = None
    current_theme: str = "default"
    fullscreen_enabled = bool(fullscreen)
    last_fetch = 0.0
    toast: Optional[Tuple[str, str, float]] = None
    show_detail: Optional[Dict[str, Any]] = None
    new_save_buf = bytearray(64)
    inv_add_buf = bytearray(b"1")
    inv_qty_buf = bytearray(b"1")
    contact_name_buf = bytearray(64)
    contact_num_buf = bytearray(b"555-0100")

    try:
        r = api.get_xmb_settings()
        if r and r.get("settings"):
            current_theme = str(r["settings"].get("theme", "default"))
            # V4 opens windowed by default — don't sync fullscreen from XMB (slow resize).
            # Toggle via Settings button still works and saves to xmbsettings.xml.
    except Exception:
        pass

    gamepad = GamepadBridge()
    gamepad.refresh()
    last_pad_count = pygame.joystick.get_count()

    def push_toast(msg: str, level: str = "info"):
        nonlocal toast
        toast = (str(msg)[:240], level, time.time() + 3.0)

    def fetch_state(save_name: Optional[str] = None):
        nonlocal api_state, hud, systems, saves, selected_save
        try:
            res = api.get_state(save_name)
            if not res or res.get("status") != "success":
                push_toast(res.get("message", "get_state failed") if res else "no state", "error")
                return res
            api_state = res
            hud = res.get("hud", {})
            systems = res.get("systems", {})
            saves = list(res.get("saves", []))
            if res.get("current_save"):
                selected_save = res.get("current_save")
            return res
        except Exception as e:
            push_toast(str(e), "error")
            return {"status": "error", "message": str(e)}

    def fetch_saves_detailed():
        nonlocal detailed_saves
        try:
            r = api.list_saves_detailed()
            if r and r.get("saves") is not None:
                detailed_saves = list(r.get("saves", []))
        except Exception:
            pass

    fetch_state(None)
    fetch_saves_detailed()

    clock = pygame.time.Clock()
    running = True

    # Simple tab index for TabBar (imgui handles nav inside TabBar automatically)
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                io.display_size = (float(event.w), float(event.h))
                gl.glViewport(0, 0, event.w, event.h)
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                # Close detail popup if open, otherwise hint (don't quit on Esc)
                if show_detail is not None:
                    show_detail = None
                else:
                    push_toast("Esc: Back  •  Alt+F4 / X to quit", "info")
            renderer.process_event(event)

        # Hotplug
        try:
            cur = pygame.joystick.get_count()
            if cur != last_pad_count:
                last_pad_count = cur
                gamepad.refresh()
                push_toast(f"Controller: {gamepad.name}" if gamepad.connected else "Controller disconnected — KBM active", "info")
        except Exception:
            pass

        now = time.time()
        if now - last_fetch > 2.5:
            last_fetch = now
            fetch_state(selected_save)

        io.delta_time = clock.tick(60) / 1000.0
        if io.delta_time <= 0:
            io.delta_time = 1.0 / 60.0

        try:
            gamepad.poll(io)
        except Exception:
            pass

        imgui.new_frame()

        # Fullscreen window — basic, no transparent tricks
        imgui.set_next_window_position(0, 0)
        imgui.set_next_window_size(io.display_size.x, io.display_size.y)
        wflags = imgui.WINDOW_NO_TITLE_BAR | imgui.WINDOW_NO_RESIZE | imgui.WINDOW_NO_MOVE | imgui.WINDOW_NO_COLLAPSE | imgui.WINDOW_MENU_BAR
        imgui.begin("##V4Root", True, wflags)

        # Menu bar (File)
        if imgui.begin_menu_bar():
            if imgui.begin_menu("File", True):
                if imgui.menu_item("Refresh", None, False, True)[0]:
                    fetch_state(selected_save)
                    fetch_saves_detailed()
                    push_toast("Refreshed", "info")
                if imgui.menu_item("New Save...", None, False, True)[0]:
                    imgui.open_popup("New Save")
                if imgui.menu_item("Quit", "Alt+F4", False, True)[0]:
                    running = False
                imgui.end_menu()
            if imgui.begin_menu("Help", True):
                imgui.menu_item(f"Controller: {gamepad.name if gamepad.connected else 'KBM (no pad)'}", None, False, False)
                imgui.menu_item("Arrows/D-pad = move  Enter/A = activate  Esc/B = back", None, False, False)
                imgui.end_menu()
            imgui.end_menu_bar()

        # Header line — plain text
        sel_label = selected_save or (api_state.get("current_save") or "live")
        imgui.text(f"MTT Dashboard V4  |  Save: {sel_label} ({len(saves)} saves)  |  Theme: {current_theme}  |  {'PAD ' + (gamepad.name or '') if gamepad.connected else 'KBM'}")
        imgui.text(f"{datetime.datetime.now().strftime('%I:%M %p')}  |  Arrows/D-pad + Enter/A, Esc/B back, mouse works")
        imgui.separator()

        # Tab bar — ImGui handles keyboard/gamepad nav inside tabs automatically
        if imgui.begin_tab_bar("V4Tabs"):
            for tid, tlabel in TABS:
                opened = imgui.begin_tab_item(tlabel)[0]
                if opened:
                    # --- HOME ---
                    if tid == "home":
                        bal = float(hud.get("wallet_balance", 0) or 0)
                        pid = str(hud.get("wallet_pid", "1"))
                        net = bal + float(hud.get("owned_value", 0) or 0) + float(hud.get("realestate_value", 0) or 0)
                        imgui.text(f"Wallet: {fmt_cur(bal)} (P{pid})  net {fmt_cur(net)}  |  Bank: {hud.get('bank_member') or 'No bank'}")
                        imgui.text(f"Garage: {hud.get('owned_count',0)} cars  {fmt_cur(hud.get('owned_value',0))}  |  Estates: {hud.get('realestate_count',0)} props  {fmt_cur(hud.get('realestate_value',0))}")
                        pos = hud.get("player_pos", [0,0,0])
                        pos_s = ", ".join(f"{float(x):.1f}" for x in pos) if isinstance(pos,(list,tuple)) else str(pos)
                        imgui.text(f"Players: {hud.get('player_count',0)}  pos {pos_s}  |  Inventory: {hud.get('inventory_stacks',0)} stacks {hud.get('inventory_items',0)} items  |  Parking {hud.get('realestate_garage_used',0)}/{hud.get('realestate_garage_cap',0)}")
                        imgui.separator()
                        if imgui.button("Open Garage"):
                            pass  # tab switch handled by user clicking Garage tab
                        imgui.same_line()
                        if imgui.button("Open Estates"):
                            pass
                        imgui.same_line()
                        if imgui.button("Open Saves"):
                            pass
                        imgui.same_line()
                        if imgui.button("Refresh"):
                            fetch_state(selected_save)
                        imgui.spacing()
                        imgui.text(f"Systems ({len(systems)}):")
                        for k, v in list(systems.items())[:10]:
                            sub = ", ".join(list(v.keys())[:3]) if isinstance(v, dict) else (f"{len(v)} entries" if isinstance(v,list) else str(v)[:40])
                            if imgui.selectable(f"{k}: {sub}##sys{k}", False)[0]:
                                show_detail = {"title": k, "body": str(v)[:3000]}
                        if debug:
                            imgui.text(f"FPS {io.framerate:.1f}")

                    # --- WALLET ---
                    elif tid == "wallet":
                        cash = float(hud.get("wallet_balance", 0) or 0)
                        imgui.text(f"Cash: {fmt_cur(cash)}")
                        if imgui.button("Refresh Wallet"):
                            fetch_state(selected_save)
                        imgui.same_line()
                        if imgui.button("Join Bank..."):
                            imgui.open_popup("join_bank")
                        cards = hud.get("bank_cards") or []
                        if not cards:
                            imgui.text("No cards — join a bank.")
                        else:
                            imgui.text("Cards:")
                            for c in cards:
                                is_credit = c.get("type") == "credit"
                                lab = f"{c.get('bank','Bank')} {'CREDIT' if is_credit else 'DEBIT'} {c.get('number','')}  {'debt '+fmt_cur(c.get('debt',0)) if is_credit else 'limit '+fmt_cur(c.get('debit_limit',0))}"
                                if imgui.selectable(lab + f"##card{c.get('card_id','')}", False)[0]:
                                    push_toast(f"Card {c.get('card_id')}", "info")
                        imgui.separator()
                        configs = hud.get("bank_configs") or {}
                        names = hud.get("bank_names") or list(configs.keys())
                        imgui.text("Banks (select to join):")
                        for n in (names or []):
                            cfg = configs.get(n, {}) if isinstance(configs, dict) else {}
                            lab = f"{n} — debit {fmt_cur(cfg.get('debit_limit',0))} credit {fmt_cur(cfg.get('credit_limit',0))}"
                            if imgui.selectable(lab + f"##bank{n}", False)[0]:
                                r = api.call_command("bank.apply", {"player_id":1, "bank_name": n})
                                push_toast(r.get("message","") if r else "", "success" if r and r.get("status")=="success" else "error")
                                if r and r.get("status")=="success":
                                    fetch_state(selected_save)
                        if imgui.begin_popup("join_bank"):
                            imgui.text("Pick a bank:")
                            for n in (names or []):
                                if imgui.selectable(f"{n}##join{n}")[0]:
                                    r = api.call_command("bank.apply", {"player_id":1, "bank_name": n})
                                    push_toast(str(r.get("message","")) if r else "", "success" if r and r.get("status")=="success" else "error")
                                    if r and r.get("status")=="success":
                                        fetch_state(selected_save)
                                    imgui.close_current_popup()
                            imgui.end_popup()

                    # --- INVENTORY ---
                    elif tid == "inventory":
                        inv_res = api.get_inventory(1)
                        if inv_res.get("status") != "success":
                            imgui.text(f"Error: {inv_res.get('message','')}")
                        else:
                            total = float(inv_res.get("total_weight",0) or 0)
                            max_w = float(inv_res.get("max_weight",35) or 35)
                            imgui.text(f"Weight {total:.1f}/{max_w:.1f} kg")
                            frac = max(0.0, min(1.0, total/max_w if max_w else 0))
                            imgui.progress_bar(frac, (300, 16), f"{int(frac*100)}%")
                            if imgui.button("Add Item..."):
                                imgui.open_popup("add_item")
                            stacks = inv_res.get("stacks", [])
                            if not stacks:
                                imgui.text("Empty pack.")
                            else:
                                for s in stacks[:40]:
                                    d = s.get("def") or {}
                                    name = d.get("name") or f"Item {s.get('item_id')}"
                                    lab = f"{name} x{s.get('quantity',1)} — {d.get('category','misc')} {d.get('weight',0)}kg {fmt_cur(d.get('value',0))}"
                                    if imgui.selectable(lab + f"##inv{s.get('item_id')}", False)[0]:
                                        show_detail = {"title": name, "body": f"{d.get('description','')}\nqty {s.get('quantity')} weight {d.get('weight',0)}kg"}
                            if imgui.begin_popup("add_item"):
                                imgui.text("Add item")
                                imgui.input_text("Item ID", inv_add_buf, 16)
                                imgui.input_text("Qty", inv_qty_buf, 16)
                                if imgui.button("Add"):
                                    try:
                                        iid = int(bytes(inv_add_buf).decode().split("\x00")[0].strip() or "1")
                                        qty = int(bytes(inv_qty_buf).decode().split("\x00")[0].strip() or "1")
                                    except Exception:
                                        iid, qty = 1, 1
                                    r = api.call_command("inventory.add", {"player_id":1, "item_id":iid, "quantity":qty})
                                    push_toast(r.get("message","Added") if r else "", "success" if r and r.get("status")=="success" else "error")
                                    if r and r.get("status")=="success":
                                        fetch_state(selected_save)
                                    imgui.close_current_popup()
                                imgui.same_line()
                                if imgui.button("Cancel"):
                                    imgui.close_current_popup()
                                imgui.end_popup()

                    # --- GARAGE ---
                    elif tid == "garage":
                        owned = (systems.get("ownership") or {}).get("vehicles", {}) if isinstance(systems.get("ownership"), dict) else {}
                        items: List[Dict[str,Any]] = []
                        for pid, lst in (owned.items() if isinstance(owned, dict) else []):
                            if isinstance(lst, list):
                                for o in lst:
                                    if isinstance(o, dict):
                                        items.append({**o, "_pid": str(pid)})
                        if not items:
                            imgui.text("Garage empty — acquire vehicles in-game.")
                        else:
                            for o in items[:30]:
                                name = str(o.get("vehicle_id") or o.get("id") or "Vehicle")
                                lab = f"{name}  P{o.get('_pid','')}  {fmt_cur(o.get('price_paid')) if o.get('price_paid') is not None else ''}  {o.get('category','')}"
                                if imgui.selectable(lab + f"##gar{name}{o.get('_pid','')}", False)[0]:
                                    show_detail = {"title": name, "body": str(o)[:2000]}
                        imgui.separator()
                        if imgui.button("Show Catalog..."):
                            try:
                                sc = api.get_shop_catalog()
                                if sc and sc.get("status")=="success":
                                    show_detail = {"title": "Catalog", "body": str(sc.get("catalog"))[:3000]}
                            except Exception as e:
                                push_toast(str(e), "error")

                    # --- ESTATES ---
                    elif tid == "estates":
                        imgui.text(f"Parking {hud.get('realestate_garage_used',0)}/{hud.get('realestate_garage_cap',0)}  value {fmt_cur(hud.get('realestate_value',0))}  owned {hud.get('realestate_owned',0)} rented {hud.get('realestate_rented',0)}")
                        re = (systems.get("realestate") or {}).get("owned", {}) if isinstance(systems.get("realestate"), dict) else {}
                        items2: List[Dict[str,Any]] = []
                        for pid, lst in (re.items() if isinstance(re, dict) else []):
                            if isinstance(lst, list):
                                for o in lst:
                                    if isinstance(o, dict):
                                        items2.append({**o, "_pid": str(pid)})
                        if not items2:
                            imgui.text("No properties.")
                        else:
                            for op in items2[:30]:
                                name = str(op.get("property_id") or op.get("id") or "Property")
                                lab = f"{name}  {op.get('property_type','')}  {op.get('tenure','')}  P{op.get('_pid','')}  {fmt_cur(op.get('price_paid')) if op.get('price_paid') is not None else ''}"
                                if imgui.selectable(lab + f"##est{name}{op.get('_pid','')}", False)[0]:
                                    show_detail = {"title": name, "body": str(op)[:2000]}
                        if imgui.button("Browse Catalog..."):
                            try:
                                rc = api.get_realestate_catalog()
                                if rc and rc.get("status")=="success":
                                    show_detail = {"title": "RealEstate Catalog", "body": str(rc.get("catalog"))[:3000]}
                            except Exception as e:
                                push_toast(str(e), "error")

                    # --- PLAYERS ---
                    elif tid == "players":
                        pd = api.get_players_detail()
                        players = pd.get("players", []) if pd.get("status")=="success" else []
                        imgui.text(f"{len(players)} player(s)")
                        if imgui.button("Add Player..."):
                            imgui.open_popup("add_player")
                        for p in players:
                            pos2 = p.get("pos",[0,0,0])
                            pos_s = ", ".join(f"{float(x):.1f}" for x in pos2) if isinstance(pos2,(list,tuple)) else str(pos2)
                            lab = f"Player {p.get('player_id')}  pos {pos_s}"
                            if imgui.selectable(lab + f"##pl{p.get('player_id')}", False)[0]:
                                show_detail = {"title": f"Player {p.get('player_id')}", "body": f"pos {pos_s}"}
                        if imgui.begin_popup("add_player"):
                            imgui.text("Add player at (10,0,5)")
                            if imgui.button("Create P99"):
                                r = api.call_command("player.add", {"player_id":99, "pos":[10,0,5]})
                                push_toast(r.get("message","") if r else "", "success" if r and r.get("status")=="success" else "error")
                                if r and r.get("status")=="success":
                                    fetch_state(selected_save)
                                imgui.close_current_popup()
                            imgui.same_line()
                            if imgui.button("Cancel"):
                                imgui.close_current_popup()
                            imgui.end_popup()

                    # --- PHONE ---
                    elif tid == "phone":
                        pc = api.get_phone_contacts()
                        contacts = pc.get("contacts", []) if pc.get("status")=="success" else []
                        imgui.text(f"{len(contacts)} contacts")
                        if imgui.button("New Contact..."):
                            imgui.open_popup("add_contact")
                        for c in contacts[:30]:
                            lab = f"{c.get('name','?')} — {c.get('number') or c.get('phone') or ''}"
                            if imgui.selectable(lab + f"##ct{c.get('name','')}", False)[0]:
                                show_detail = {"title": c.get("name",""), "body": f"{c.get('name','')}\n{c.get('number') or c.get('phone') or ''}"}
                        if imgui.begin_popup("add_contact"):
                            imgui.input_text("Name", contact_name_buf, 64)
                            imgui.input_text("Number", contact_num_buf, 32)
                            if imgui.button("Add"):
                                name_s = bytes(contact_name_buf).decode().split("\x00")[0].strip()
                                num_s = bytes(contact_num_buf).decode().split("\x00")[0].strip()
                                if not name_s:
                                    push_toast("Enter name", "warning")
                                else:
                                    r = api.call_command("phone.new_contact", {"contact_name": name_s, "contact_number": num_s or "555-0100"})
                                    push_toast(r.get("message","") if r else "", "success" if r and r.get("status")=="success" else "error")
                                    if r and r.get("status")=="success":
                                        fetch_state(selected_save)
                                    imgui.close_current_popup()
                            imgui.same_line()
                            if imgui.button("Cancel"):
                                imgui.close_current_popup()
                            imgui.end_popup()

                    # --- SAVES ---
                    elif tid == "saves":
                        imgui.text(f"{len(detailed_saves) or len(saves)} saves")
                        if imgui.button("Refresh"):
                            fetch_saves_detailed()
                            fetch_state(selected_save)
                        imgui.same_line()
                        if imgui.button("New Save..."):
                            imgui.open_popup("New Save")
                        # Simple list
                        slots: List[Dict[str,Any]] = []
                        if detailed_saves:
                            slots = sorted(detailed_saves, key=lambda s: s.get("name",""))
                            while len(slots) < 6:
                                slots.append({"name": f"slot{len(slots)+1}", "saved_at": None})
                        else:
                            names2 = saves if saves else []
                            slots = [{"name": n, "saved_at": None} for n in names2]
                            i2 = 1
                            while len(slots) < 6:
                                nm = f"slot{i2}"
                                if nm not in names2:
                                    slots.append({"name": nm, "saved_at": None})
                                i2+=1
                        for sl in slots[:8]:
                            name = sl.get("name","slot")
                            sel = selected_save == name
                            lab = f"{'[x] ' if sel else ''}{name}  {fmt_time(sl.get('saved_at')) if sl.get('saved_at') else '(empty)'}"
                            if imgui.selectable(lab + f"##save{name}", sel)[0]:
                                selected_save = name
                                push_toast(f"Selected {name}", "info")
                        imgui.separator()
                        imgui.text(f"Selected: {selected_save or 'none'}")
                        if imgui.button("Load selected") and selected_save:
                            r = api.load_game(selected_save)
                            if not r or r.get("status")!="success":
                                r = api.load_save(selected_save)
                            if r and r.get("status")=="success":
                                fetch_state(selected_save); fetch_saves_detailed()
                                push_toast(f"Loaded {selected_save}", "success")
                            else:
                                push_toast(r.get("message","load failed") if r else "failed", "error")
                        imgui.same_line()
                        if imgui.button("Save here") and selected_save:
                            r = api.save_game(selected_save)
                            if r and r.get("status")=="success":
                                fetch_state(selected_save); fetch_saves_detailed()
                                push_toast(f"Saved {selected_save}", "success")
                            else:
                                push_toast(r.get("message","save failed") if r else "failed", "error")
                        if imgui.begin_popup("New Save"):
                            imgui.input_text("Name", new_save_buf, 64)
                            if imgui.button("Save"):
                                name_s = bytes(new_save_buf).decode().split("\x00")[0].strip()
                                if not name_s:
                                    push_toast("Enter name", "warning")
                                else:
                                    r = api.save_game(name_s)
                                    if r and r.get("status")=="success":
                                        selected_save = name_s
                                        fetch_state(name_s); fetch_saves_detailed()
                                        push_toast(f"Saved {name_s}", "success")
                                        imgui.close_current_popup()
                                    else:
                                        push_toast(r.get("message","") if r else "", "error")
                            imgui.same_line()
                            if imgui.button("Cancel"):
                                imgui.close_current_popup()
                            imgui.end_popup()

                    # --- SETTINGS ---
                    elif tid == "settings":
                        imgui.text(f"Current: theme={current_theme}  fullscreen={fullscreen_enabled}")
                        imgui.text("New Save location: saves/imgui_v4.ini keeps window/layout")
                        if imgui.button("Toggle Fullscreen"):
                            fullscreen_enabled = not fullscreen_enabled
                            api.set_fullscreen(bool(fullscreen_enabled))
                            try:
                                if fullscreen_enabled:
                                    pygame.display.set_mode((io.display_size.x, io.display_size.y), pygame.OPENGL | pygame.DOUBLEBUF | pygame.FULLSCREEN)
                                else:
                                    pygame.display.set_mode((int(io.display_size.x), int(io.display_size.y)), pygame.OPENGL | pygame.DOUBLEBUF | pygame.RESIZABLE)
                                w2, h2 = pygame.display.get_surface().get_size()
                                io.display_size = (float(w2), float(h2))
                                gl.glViewport(0, 0, w2, h2)
                            except Exception:
                                pass
                            push_toast(f"Fullscreen {'on' if fullscreen_enabled else 'off'}", "info")
                        imgui.same_line()
                        if imgui.button("Quit Dashboard"):
                            running = False
                        imgui.separator()
                        imgui.text("Help: Tab/Arrows/D-pad = move, Enter/A = activate, Esc/B = back, mouse works.")
                        if debug:
                            imgui.text(f"FPS {io.framerate:.1f}  pad={gamepad.name if gamepad.connected else 'KBM'}")

                    imgui.end_tab_item()
            imgui.end_tab_bar()

        # Detail popup — simple modal
        if show_detail is not None:
            imgui.open_popup("Details")
        if imgui.begin_popup_modal("Details", True)[0]:
            d = show_detail if show_detail else {}
            imgui.text(d.get("title","Details"))
            imgui.separator()
            imgui.text_wrapped(str(d.get("body",""))[:4000])
            if imgui.button("Close", 100, 28):
                show_detail = None
                imgui.close_current_popup()
            imgui.end_popup()
        # keep show_detail until closed via button
        if show_detail is not None and not imgui.is_popup_open("Details"):
            # user closed via X — keep until next open
            pass

        # Toast — simple overlay at top-right
        if toast is not None:
            msg, lvl, exp = toast
            if time.time() > exp:
                toast = None
            else:
                w, h = io.display_size.x, io.display_size.y
                imgui.set_next_window_position(w - 380, 36)
                imgui.set_next_window_size(360, 60)
                wflags2 = imgui.WINDOW_NO_TITLE_BAR | imgui.WINDOW_NO_RESIZE | imgui.WINDOW_NO_MOVE | imgui.WINDOW_NO_SCROLLBAR
                imgui.begin("##toast", True, wflags2)
                imgui.text_wrapped(msg)
                imgui.end()

        imgui.end()

        # Render
        gl.glClearColor(0.10, 0.10, 0.12, 1.0)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)
        imgui.render()
        try:
            renderer.render(imgui.get_draw_data())
        except Exception as e:
            if debug:
                print(f"[V4] render error: {e}", file=sys.stderr)
        pygame.display.flip()

        io.mouse_wheel = 0
        io.mouse_wheel_horizontal = 0
        try:
            for idx in (imgui.NAV_INPUT_DPAD_LEFT, imgui.NAV_INPUT_DPAD_RIGHT, imgui.NAV_INPUT_DPAD_UP, imgui.NAV_INPUT_DPAD_DOWN,
                        imgui.NAV_INPUT_L_STICK_LEFT, imgui.NAV_INPUT_L_STICK_RIGHT, imgui.NAV_INPUT_L_STICK_UP, imgui.NAV_INPUT_L_STICK_DOWN,
                        imgui.NAV_INPUT_ACTIVATE, imgui.NAV_INPUT_CANCEL, imgui.NAV_INPUT_MENU, imgui.NAV_INPUT_INPUT):
                io.nav_inputs[idx] = 0.0
        except Exception:
            pass

    try:
        renderer.shutdown()
    except Exception:
        pass
    try:
        pygame.quit()
    except Exception:
        pass
    try:
        imgui.destroy_context()
    except Exception:
        pass
