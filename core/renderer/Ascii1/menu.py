"""
MTT Pause Menu — Tab main menu + multiplayer submenu

Tab opens overlay with:
  Main: Save Game / Multiplayer / Quit / Resume
  Multiplayer: Host New LAN Game / active games list (UDP discovery) / Back

Uses pygame for overlay rendering and mouse/keyboard handling.
Keeps pending actions for ascii.py to consume.

Integrates with multiplayer.Discovery / HostSession / ClientSession externally.
"""
from __future__ import annotations

import time
from typing import List, Optional, Tuple

try:
    import pygame
except ImportError:
    pygame = None  # type: ignore

# Colors
_BG = (12, 12, 18, 210)
_PANEL_BG = (30, 30, 40)
_BTN_BG = (50, 50, 70)
_BTN_HOVER = (70, 70, 110)
_BTN_ACTIVE = (90, 90, 160)
_TEXT = (220, 220, 220)
_TEXT_DIM = (170, 170, 180)
_ACCENT = (255, 215, 0)
_BORDER = (70, 70, 90)

class MTTMenu:
    def __init__(self, screen_w=960, screen_h=720):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.is_open = False
        self.state = "main"  # main | multiplayer
        self.pending_action: Optional[str] = None  # ascii consumes via consume_action()
        # keyboard nav
        self.selected = 0
        # multiplayer list cache
        self.discovery = None
        self._hosts_cache: List = []
        self._last_discovery_poll = 0.0
        # mp sessions references (set by ascii)
        self.host_session = None
        self.client_session = None
        # button rects for click detection (populated in draw)
        self._btn_rects: List[Tuple[pygame.Rect, str]] = []
        # host list rects
        self._host_rects: List[Tuple[pygame.Rect, str]] = []
        # MP player name editing (visible in multiplayer menu)
        self.player_name: str = "Player"
        self.editing_name: bool = False
        self.name_rect: Optional[pygame.Rect] = None

    def set_discovery(self, disc):
        self.discovery = disc

    def set_sessions(self, host_session, client_session):
        self.host_session = host_session
        self.client_session = client_session

    def toggle(self):
        self.is_open = not self.is_open
        if self.is_open:
            self.state = "main"
            self.selected = 0

    def open(self):
        self.is_open = True
        self.state = "main"
        self.selected = 0

    def close(self):
        self.is_open = False

    def consume_action(self) -> Optional[str]:
        a = self.pending_action
        self.pending_action = None
        return a

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------
    def handle_event(self, event) -> bool:
        """Return True if event consumed (when menu open). Handles KB/Mouse + Xbox controller (D-Pad + A/B)."""
        if pygame is None:
            return False
        # --- Xbox controller handling (always check, alongside KB/Mouse) ---
        # Menu navigation via D-Pad (hat) and A/B buttons
        try:
            if event.type == pygame.JOYHATMOTION and self.is_open:
                # DPAD: hat y 1=up, -1=down; x ignored for vertical menu but support left/right as well
                if self.editing_name:
                    return True  # block nav while editing
                hx, hy = event.value if hasattr(event, 'value') else (0, 0)
                # pygame hat: only hat 0 matters for Xbox
                if getattr(event, 'hat', 0) == 0:
                    if hy == 1:
                        self._nav(-1)
                        return True
                    elif hy == -1:
                        self._nav(1)
                        return True
                    elif hx == 1 or hx == -1:
                        # horizontal nudge? ignore or also nav
                        pass
            elif event.type == pygame.JOYBUTTONDOWN:
                # Xbox: 0=A(South), 1=B(East), 7=Start/Menu, 6=Back/View
                btn = getattr(event, 'button', -1)
                if btn == 0 and self.is_open:  # A -> activate
                    if self.editing_name:
                        self.editing_name = False
                        return True
                    self._activate()
                    return True
                elif btn == 1 and self.is_open:  # B -> back / close (like ESC)
                    if self.editing_name:
                        self.editing_name = False
                        return True
                    if self.state == "multiplayer":
                        self.state = "main"
                        self.selected = 1
                    else:
                        self.close()
                    return True
                elif btn in (7, 6):  # Start or Back toggles menu (handled in ascii main too, but allow here)
                    # let ascii main toggle; consume if menu open
                    if self.is_open and self.editing_name:
                        self.editing_name = False
                    # don't consume here, let main toggle - but prevent double
                    pass
        except Exception:
            pass
        # Tab toggles open/close from ascii main - but also handle here
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_TAB:
                if self.is_open:
                    if self.editing_name:
                        self.editing_name = False
                    self.close()
                    return True
                else:
                    return False
            if not self.is_open:
                return False
            # If editing name, handle text input first (modal)
            if self.editing_name:
                if event.key == pygame.K_ESCAPE:
                    self.editing_name = False
                    return True
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self.editing_name = False
                    return True
                elif event.key == pygame.K_BACKSPACE:
                    self.player_name = self.player_name[:-1]
                    return True
                else:
                    ch = getattr(event, 'unicode', '')
                    if ch and ch.isprintable() and len(self.player_name) < 16:
                        # filter control chars
                        if ch not in ('\n', '\r', '\t'):
                            self.player_name += ch
                        return True
                    # allow navigation keys to be ignored while editing? consume others
                    return True
            # Menu is open: handle nav (not editing)
            if event.key in (pygame.K_ESCAPE,):
                if self.state == "multiplayer":
                    self.state = "main"
                    self.selected = 1  # multiplayer index
                else:
                    self.close()
                return True
            elif event.key in (pygame.K_UP, pygame.K_w):
                self._nav(-1)
                return True
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self._nav(1)
                return True
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self._activate()
                return True
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.is_open:
            pos = event.pos
            # Name field has priority when in multiplayer state
            if self.state == "multiplayer" and self.name_rect is not None and self.name_rect.collidepoint(pos):
                self.editing_name = True
                return True
            # if editing and click elsewhere, exit editing
            if self.editing_name:
                self.editing_name = False
                # fall through to allow clicking buttons after exiting edit
            # check btn rects
            for rect, act in self._btn_rects:
                if rect.collidepoint(pos):
                    self._trigger(act)
                    return True
            for rect, act in self._host_rects:
                if rect.collidepoint(pos):
                    self.pending_action = act  # e.g. "join:ip:port"
                    return True
        elif event.type == pygame.MOUSEMOTION and self.is_open:
            if self.editing_name:
                return True
            # hover update for keyboard selection
            pos = event.pos
            for i, (rect, _) in enumerate(self._btn_rects):
                if rect.collidepoint(pos):
                    self.selected = i
                    break
        return False if not self.is_open else True

    def _nav(self, delta):
        n = len(self._current_actions())
        if n == 0:
            return
        self.selected = (self.selected + delta) % n

    def _current_actions(self) -> List[str]:
        if self.state == "main":
            return ["save", "multiplayer", "quit", "resume"]
        else:
            acts = ["host"]
            # Disconnect option when hosting or connected as client
            try:
                hosting = self.host_session is not None and getattr(self.host_session, "is_running", lambda: False)()
                connected = self.client_session is not None and getattr(self.client_session, "is_connected", lambda: False)()
                if hosting or connected:
                    acts.append("disconnect")
            except Exception:
                pass
            # add dynamic hosts
            for h in self._hosts_cache:
                acts.append(f"join:{h.ip}:{h.port}")
            acts.append("back")
            return acts

    def _activate(self):
        acts = self._current_actions()
        if not acts:
            return
        act = acts[self.selected % len(acts)]
        self._trigger(act)

    def _trigger(self, act: str):
        if act == "resume":
            self.close()
        elif act == "save":
            self.pending_action = "save"
        elif act == "quit":
            self.pending_action = "quit"
        elif act == "multiplayer":
            self.state = "multiplayer"
            self.selected = 0
            self._poll_discovery(force=True)
        elif act == "host":
            self.pending_action = "host"
        elif act == "disconnect":
            self.pending_action = "disconnect"
        elif act == "back":
            self.state = "main"
            self.selected = 1
        elif act.startswith("join:"):
            self.pending_action = act

    # ------------------------------------------------------------------
    # Discovery polling
    # ------------------------------------------------------------------
    def _poll_discovery(self, force=False):
        if self.discovery is None:
            return
        now = time.time()
        if not force and now - self._last_discovery_poll < 0.5:
            return
        self._last_discovery_poll = now
        try:
            self._hosts_cache = self.discovery.get_hosts()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------
    def draw(self, screen):
        if pygame is None or not self.is_open or screen is None:
            return
        # poll discovery when in mp state
        if self.state == "multiplayer":
            self._poll_discovery()

        # overlay
        try:
            overlay = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
            overlay.fill(_BG)
            screen.blit(overlay, (0, 0))
        except Exception:
            pass

        # panel (taller for name field)
        panel_w = 520
        panel_h = 500
        panel_x = (self.screen_w - panel_w) // 2
        panel_y = (self.screen_h - panel_h) // 2
        panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
        try:
            pygame.draw.rect(screen, _PANEL_BG, panel_rect, border_radius=12)
            pygame.draw.rect(screen, _BORDER, panel_rect, 2, border_radius=12)
        except Exception:
            pygame.draw.rect(screen, _PANEL_BG, panel_rect)

        # fonts
        try:
            title_font = pygame.font.SysFont("Courier", 24, bold=True)
            btn_font = pygame.font.SysFont("Courier", 16, bold=True)
            small_font = pygame.font.SysFont("Courier", 12, bold=False)
            tiny_font = pygame.font.SysFont("Courier", 11, bold=False)
        except Exception:
            title_font = pygame.font.Font(None, 24)
            btn_font = pygame.font.Font(None, 18)
            small_font = pygame.font.Font(None, 14)
            tiny_font = pygame.font.Font(None, 12)

        # title
        title = "PAUSED — TAB to resume" if self.state == "main" else "MULTIPLAYER — LAN"
        if title_font:
            ts = title_font.render(title, True, _ACCENT)
            screen.blit(ts, (panel_x + 20, panel_y + 14))

        # subtitle hint - KB/Mouse + Xbox controller
        if small_font:
            # Show controller hints alongside KB
            try:
                has_pad = pygame.joystick.get_count() > 0
            except Exception:
                has_pad = False
            if has_pad:
                hint = "W/S/↑↓/D-Pad, Enter/A select • ESC/B, TAB/Start close"
            else:
                hint = "W/S or Up/Down, Enter to select • ESC / TAB to close (Xbox pad supported)"
            hs = small_font.render(hint, True, _TEXT_DIM)
            screen.blit(hs, (panel_x + 20, panel_y + 44))

        self._btn_rects = []
        self._host_rects = []

        if self.state == "main":
            labels = [("Save Game", "save"), ("Multiplayer", "multiplayer"), ("Quit", "quit"), ("Resume", "resume")]
            btn_w = panel_w - 60
            btn_h = 48
            start_y = panel_y + 80
            for i, (lbl, act) in enumerate(labels):
                y = start_y + i * (btn_h + 12)
                rect = pygame.Rect(panel_x + 30, y, btn_w, btn_h)
                hover = (i == self.selected)
                # click detection
                self._btn_rects.append((rect, act))
                color = _BTN_HOVER if hover else _BTN_BG
                if act == "quit":
                    color = (90, 40, 40) if hover else (70, 30, 30)
                try:
                    pygame.draw.rect(screen, color, rect, border_radius=8)
                    pygame.draw.rect(screen, _BORDER, rect, 1, border_radius=8)
                except Exception:
                    pygame.draw.rect(screen, color, rect)
                if btn_font:
                    ls = btn_font.render(lbl, True, _TEXT)
                    screen.blit(ls, (rect.x + 16, rect.y + (btn_h - ls.get_height()) // 2))
                    if hover:
                        arrow = btn_font.render(">", True, _ACCENT)
                        screen.blit(arrow, (rect.right - 20, rect.y + (btn_h - arrow.get_height()) // 2))
        else:  # multiplayer
            # ---- Player name edit (new option) ----
            btn_w = panel_w - 60
            hx = panel_x + 30
            name_y = panel_y + 72
            name_rect = pygame.Rect(hx, name_y, btn_w, 30)
            self.name_rect = name_rect
            # background for name field
            name_bg = (60, 60, 80) if self.editing_name else (40, 40, 60)
            border_col = _ACCENT if self.editing_name else _BORDER
            try:
                pygame.draw.rect(screen, name_bg, name_rect, border_radius=6)
                pygame.draw.rect(screen, border_col, name_rect, 2, border_radius=6)
            except Exception:
                pygame.draw.rect(screen, name_bg, name_rect)
            if small_font:
                # label + value + cursor
                val = self.player_name if self.player_name else " "
                # blink cursor when editing
                if self.editing_name and int(time.time() * 2) % 2 == 0:
                    val = val + "_"
                txt = f"Your Name: {val}"
                if self.editing_name:
                    txt += "  (typing… Enter to confirm)"
                else:
                    txt += "  (click to edit)"
                ts = small_font.render(txt, True, _TEXT if not self.editing_name else _ACCENT)
                screen.blit(ts, (name_rect.x + 8, name_rect.y + (name_rect.height - ts.get_height()) // 2))
            # Host button below name field
            btn_h = 46
            hy = name_y + 34 + 6
            host_rect = pygame.Rect(hx, hy, btn_w, btn_h)
            hover = (self.selected == 0)
            self._btn_rects.append((host_rect, "host"))
            # If already hosting, show different label
            hosting = self.host_session is not None and getattr(self.host_session, "is_running", lambda: False)()
            connected = self.client_session is not None and getattr(self.client_session, "is_connected", lambda: False)()
            has_disconnect = hosting or connected
            label = "Hosting — Stop" if hosting else "Host New LAN Game"
            color = _BTN_ACTIVE if hover else (40, 90, 50) if not hosting else (80, 70, 40)
            try:
                pygame.draw.rect(screen, color, host_rect, border_radius=8)
                pygame.draw.rect(screen, _BORDER, host_rect, 1, border_radius=8)
            except Exception:
                pygame.draw.rect(screen, color, host_rect)
            if btn_font:
                ls = btn_font.render(label, True, _TEXT)
                screen.blit(ls, (host_rect.x + 16, host_rect.y + (btn_h - ls.get_height()) // 2))

            # Disconnect button (only when hosting or connected)
            disconnect_rect = None
            if has_disconnect:
                dh = 38
                disconnect_rect = pygame.Rect(hx, hy + btn_h + 6, btn_w, dh)
                disc_sel_idx = 1
                hover_disc = (self.selected == disc_sel_idx)
                self._btn_rects.append((disconnect_rect, "disconnect"))
                dcol = (110, 40, 40) if hover_disc else (70, 30, 30)
                try:
                    pygame.draw.rect(screen, dcol, disconnect_rect, border_radius=8)
                    pygame.draw.rect(screen, _BORDER, disconnect_rect, 1, border_radius=8)
                except Exception:
                    pygame.draw.rect(screen, dcol, disconnect_rect)
                if btn_font:
                    dlabel = "Disconnect" + (" (Stop Host)" if hosting else " (Leave Game)")
                    dls = btn_font.render(dlabel, True, _TEXT)
                    screen.blit(dls, (disconnect_rect.x + 16, disconnect_rect.y + (dh - dls.get_height()) // 2))
                status_y = disconnect_rect.bottom + 8
            else:
                status_y = hy + btn_h + 8
            if small_font:
                if hosting:
                    try:
                        ip = getattr(self.host_session, "tcp_port", "?")
                        try:
                            from .multiplayer import get_local_ip as _gli
                        except Exception:
                            try:
                                from core.renderer.Ascii1.multiplayer import get_local_ip as _gli
                            except Exception:
                                from multiplayer import get_local_ip as _gli
                        lip = _gli()
                    except Exception:
                        lip = "?"
                        ip = "?"
                    st = small_font.render(f"Hosting on {lip}:{self.host_session.tcp_port}  players={1+len(self.host_session.clients)}", True, _TEXT_DIM)
                    screen.blit(st, (hx, status_y))
                    status_y += 16
                elif connected:
                    st = small_font.render(f"Connected to {self.client_session.host_ip}:{self.client_session.host_port} as {self.client_session.my_id}", True, _TEXT_DIM)
                    screen.blit(st, (hx, status_y))
                    status_y += 16
                else:
                    st = small_font.render("Scanning LAN for active games … (UDP broadcast)", True, _TEXT_DIM)
                    screen.blit(st, (hx, status_y))
                    status_y += 16

            # Host list title
            list_title_y = status_y + 6
            if small_font:
                lt = small_font.render("Active LAN Games:", True, _TEXT)
                screen.blit(lt, (hx, list_title_y))
            list_y = list_title_y + 20
            list_h = 140
            list_rect = pygame.Rect(hx, list_y, btn_w, list_h)
            try:
                pygame.draw.rect(screen, (22, 22, 28), list_rect, border_radius=6)
                pygame.draw.rect(screen, _BORDER, list_rect, 1, border_radius=6)
            except Exception:
                pygame.draw.rect(screen, (22, 22, 28), list_rect)

            # Host entries — rebuild _btn_rects correctly with disconnect offset
            # Preserve host + disconnect rects already added
            base_btns = list(self._btn_rects)
            self._host_rects = []
            # offset for hosts selection index
            host_offset = 1 + (1 if has_disconnect else 0)
            hosts = self._hosts_cache
            if not hosts:
                if tiny_font:
                    ns = tiny_font.render("No games found. Host one or check firewall.", True, _TEXT_DIM)
                    screen.blit(ns, (hx + 10, list_y + 10))
            else:
                entry_h = 30
                for idx, h in enumerate(hosts[:4]):  # show max 4
                    ey = list_y + 6 + idx * (entry_h + 4)
                    if ey + entry_h > list_y + list_h - 6:
                        break
                    erect = pygame.Rect(hx + 6, ey, btn_w - 12, entry_h)
                    act = f"join:{h.ip}:{h.port}"
                    sel_idx = host_offset + idx
                    hover = (self.selected == sel_idx)
                    self._host_rects.append((erect, act))
                    col = _BTN_HOVER if hover else (35, 35, 50)
                    try:
                        pygame.draw.rect(screen, col, erect, border_radius=6)
                        pygame.draw.rect(screen, _BORDER, erect, 1, border_radius=6)
                    except Exception:
                        pygame.draw.rect(screen, col, erect)
                    if tiny_font:
                        txt = f"{h.host_name}  {h.ip}:{h.port}  ({h.players} plyrs)"
                        ts = tiny_font.render(txt, True, _TEXT)
                        screen.blit(ts, (erect.x + 8, erect.y + 6))
                        ago = int(time.time() - h.last_seen)
                        age = tiny_font.render(f"{ago}s ago", True, _TEXT_DIM)
                        screen.blit(age, (erect.right - age.get_width() - 8, erect.y + 6))

            # Back button at bottom
            back_w = btn_w
            back_h = 38
            back_y = panel_y + panel_h - back_h - 18
            back_rect = pygame.Rect(panel_x + 30, back_y, back_w, back_h)
            back_sel_idx = host_offset + len(hosts)
            hover_back = (self.selected == back_sel_idx)
            self._btn_rects.append((back_rect, "back"))
            bcol = _BTN_HOVER if hover_back else _BTN_BG
            try:
                pygame.draw.rect(screen, bcol, back_rect, border_radius=8)
                pygame.draw.rect(screen, _BORDER, back_rect, 1, border_radius=8)
            except Exception:
                pygame.draw.rect(screen, bcol, back_rect)
            if btn_font:
                ls = btn_font.render("Back", True, _TEXT)
                screen.blit(ls, (back_rect.x + 16, back_rect.y + (back_h - ls.get_height()) // 2))

        # footer help
        if tiny_font:
            ft = tiny_font.render("Tab reopens menu • Save is host-only in MP (clients don't save)", True, _TEXT_DIM)
            screen.blit(ft, (panel_x + 20, panel_y + panel_h - 12))

