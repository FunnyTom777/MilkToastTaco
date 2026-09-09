"""
MTT Player Controller — free smooth movement, multiplayer-ready

Separated from ascii.py so the renderer is just rendering.

Design for future multiplayer:
- Player is a pure data + simulation object (no pygame dependency).
- Every player has a stable `player_id` (str/int) — local or remote.
- Position is float tile coordinates (continuous), not grid-locked.
- State is serializable via to_dict()/from_dict() for network replication.
- Input is a small dict {"dx": -1..1, "dy": -1..1} that can be sent over the wire;
  PlayerController translates pygame keys -> input dict -> velocity.
- World collision is sampled via world.get_tile(int(floor(x)), int(floor(y))) — no direct coupling to rendering.

Usage (singleplayer, inside ascii.py main loop):
    from player import Player, PlayerController   # or relative import
    player = Player(player_id="local", x=0.0, y=0.0)
    controller = PlayerController(player)
    # each frame:
    keys = pygame.key.get_pressed()
    controller.handle_pygame_input(keys)  # sets velocity
    player.update(dt, world)              # dt in seconds, handles collision + sliding

Multiplayer sketch:
    players = {"local": player, "remote_2": Player("remote_2", 10, 5)}
    # on network tick, apply remote state:
    players["remote_2"].apply_network_state({"x": 10.2, "y": 5.1, "vx": 1.0, "vy": 0.0})
    # or serialize:
    payload = player.to_dict()
"""
from __future__ import annotations

import math
import os
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Tuple, Optional

# Try to import world SAVE_DIR for save/load — fallback to literal
try:
    from . import terrain_generation as _tg  # type: ignore
    _DEFAULT_SAVE_DIR = _tg.SAVE_DIR
except Exception:
    try:
        import terrain_generation as _tg  # type: ignore
        _DEFAULT_SAVE_DIR = _tg.SAVE_DIR
    except Exception:
        _DEFAULT_SAVE_DIR = "saves_world1"


class Player:
    """
    Continuous player entity.

    Attributes:
        player_id: stable id for multiplayer (e.g. "local", "host", "peer_7")
        x, y: float tile coordinates (0.0 = origin tile, 0.5 = center of tile 0)
        vx, vy: float velocity in tiles/sec
        speed: max speed in tiles/sec
        radius: collision radius in tiles (0.3 = 30% of tile, allows 0.2 gap to walls)
        walkable check samples 5 points (center + 4 cardinal offsets) to prevent clipping corners.
    """

    def __init__(self, player_id: str = "local", x: float = 0.0, y: float = 0.0, speed: float = 4.5, radius: float = 0.30):
        self.player_id: str = str(player_id)
        self.x: float = float(x)
        self.y: float = float(y)
        self.vx: float = 0.0
        self.vy: float = 0.0
        self.speed: float = float(speed)
        self.radius: float = float(radius)

    # ---- helpers ----
    @property
    def tile_pos(self) -> Tuple[int, int]:
        return (int(math.floor(self.x)), int(math.floor(self.y)))

    def _is_walkable(self, world, wx: float, wy: float) -> bool:
        """Sample world walkability at continuous (wx, wy)."""
        try:
            # world.get_tile expects int tile coords
            tile = world.get_tile(int(math.floor(wx)), int(math.floor(wy)))
            if tile is None:
                return False
            return bool(tile.walkable)
        except Exception:
            return False

    def can_move_to(self, world, nx: float, ny: float) -> bool:
        """Check if player center + radius at (nx, ny) would be walkable on all sampled points."""
        r = self.radius
        # 5-point check: center + N/S/E/W offsets (covers cardinal clipping; corners covered by radius)
        points = [
            (nx, ny),
            (nx + r, ny),
            (nx - r, ny),
            (nx, ny + r),
            (nx, ny - r),
        ]
        # Also check diagonal corners slightly inset to prevent corner tunneling
        diag = r * 0.7
        points.extend([(nx + diag, ny + diag), (nx - diag, ny + diag), (nx + diag, ny - diag), (nx - diag, ny - diag)])
        for px, py in points:
            if not self._is_walkable(world, px, py):
                return False
        return True

    # ---- input -> velocity ----
    def set_input(self, dx: float, dy: float):
        """
        Set movement input vector (-1..1 each). Normalizes diagonal to keep speed consistent.
        Called by PlayerController or network.
        """
        # deadzone
        if abs(dx) < 0.01:
            dx = 0.0
        if abs(dy) < 0.01:
            dy = 0.0
        mag = math.hypot(dx, dy)
        if mag > 1.0:
            dx /= mag
            dy /= mag
        self.vx = dx * self.speed
        self.vy = dy * self.speed

    def stop(self):
        self.vx = 0.0
        self.vy = 0.0

    # ---- simulation ----
    def update(self, dt: float, world):
        """
        Move by velocity * dt with collision + axis sliding.
        dt: seconds since last frame (e.g. 1/60).
        """
        if dt <= 0:
            return
        # Clamp dt to avoid teleport on lag spike
        dt = min(dt, 0.05)
        dx = self.vx * dt
        dy = self.vy * dt
        if dx == 0 and dy == 0:
            return

        # Try full move first
        nx = self.x + dx
        ny = self.y + dy
        if self.can_move_to(world, nx, ny):
            self.x, self.y = nx, ny
            return
        # Slide: try X only
        if dx != 0 and self.can_move_to(world, self.x + dx, self.y):
            self.x += dx
            # still try Y after X slide for diagonal
            if dy != 0 and self.can_move_to(world, self.x, self.y + dy):
                self.y += dy
            return
        # Slide: try Y only
        if dy != 0 and self.can_move_to(world, self.x, self.y + dy):
            self.y += dy
            return
        # Blocked — stay

    # ---- legacy grid API (compat for old ascii.py code that called player.move(dx,dy,world)) ----
    def move(self, dx: int, dy: int, world):
        """Discrete 1-tile step for compat."""
        try:
            tx = int(math.floor(self.x)) + int(dx)
            ty = int(math.floor(self.y)) + int(dy)
            tile = world.get_tile(tx, ty)
            if tile and tile.walkable:
                # Snap to center of target tile for grid-compat callers
                self.x = float(tx) + 0.5
                self.y = float(ty) + 0.5
                self.vx = self.vy = 0.0
        except Exception:
            pass

    # ---- serialization (multiplayer) ----
    def to_dict(self) -> Dict:
        return {"player_id": self.player_id, "x": self.x, "y": self.y, "vx": self.vx, "vy": self.vy, "speed": self.speed}

    def apply_network_state(self, state: Dict):
        """Apply authoritative state from server (interpolate in real client)."""
        if "x" in state:
            self.x = float(state["x"])
        if "y" in state:
            self.y = float(state["y"])
        if "vx" in state:
            self.vx = float(state["vx"])
        if "vy" in state:
            self.vy = float(state["vy"])

    @classmethod
    def from_dict(cls, data: Dict) -> "Player":
        p = cls(player_id=data.get("player_id", "local"), x=float(data.get("x", 0)), y=float(data.get("y", 0)))
        p.vx = float(data.get("vx", 0))
        p.vy = float(data.get("vy", 0))
        if "speed" in data:
            p.speed = float(data["speed"])
        return p

    # ---- persistence ----
    def save_player_xml(self, save_dir: Optional[str] = None):
        if save_dir is None:
            try:
                save_dir = _tg.SAVE_DIR
            except Exception:
                save_dir = _DEFAULT_SAVE_DIR
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        root = ET.Element("Player", x=str(self.x), y=str(self.y), player_id=str(self.player_id))
        # also store velocity for completeness (not required)
        root.set("vx", str(self.vx))
        root.set("vy", str(self.vy))
        tree = ET.ElementTree(root)
        tree.write(os.path.join(save_dir, "player.xml"))

    def load_player_xml(self, save_dir: Optional[str] = None) -> bool:
        if save_dir is None:
            try:
                save_dir = _tg.SAVE_DIR
            except Exception:
                save_dir = _DEFAULT_SAVE_DIR
        filename = os.path.join(save_dir, "player.xml")
        if not os.path.exists(filename):
            return False
        try:
            tree = ET.parse(filename)
            root = tree.getroot()
            # Support both old int and new float formats
            self.x = float(root.attrib.get("x", self.x))
            self.y = float(root.attrib.get("y", self.y))
            self.player_id = root.attrib.get("player_id", self.player_id)
            if "vx" in root.attrib:
                try:
                    self.vx = float(root.attrib["vx"])
                except Exception:
                    pass
            if "vy" in root.attrib:
                try:
                    self.vy = float(root.attrib["vy"])
                except Exception:
                    pass
            return True
        except Exception:
            return False

    def __repr__(self):
        return f"Player(id={self.player_id!r}, x={self.x:.2f}, y={self.y:.2f}, vx={self.vx:.2f}, vy={self.vy:.2f})"


class PlayerController:
    """
    Translates input into Player velocity. Separated for testability & multiplayer.
    - Local: call handle_pygame_input(pygame.key.get_pressed())
    - Network: call handle_network_input({"dx": 0.7, "dy": -0.3})
    - Owns no pygame state; Player is pure.
    """

    def __init__(self, player: Player):
        self.player = player

    def handle_pygame_input(self, keys) -> Dict[str, float]:
        """
        Read pygame key state (from pygame.key.get_pressed() or event keys).
        Returns input dict {"dx": float, "dy": float} for networking.
        Supports WASD + arrows + numpad + vi keys.
        """
        # keys may be sequence (get_pressed) or dict
        def is_down(k):
            try:
                return bool(keys[k])
            except Exception:
                return False

        # Import pygame key constants lazily to avoid hard dep in tests
        try:
            import pygame
            left = is_down(pygame.K_LEFT) or is_down(pygame.K_a) or is_down(pygame.K_h) or is_down(pygame.K_KP4)
            right = is_down(pygame.K_RIGHT) or is_down(pygame.K_d) or is_down(pygame.K_l) or is_down(pygame.K_KP6)
            up = is_down(pygame.K_UP) or is_down(pygame.K_w) or is_down(pygame.K_k) or is_down(pygame.K_KP8)
            down = is_down(pygame.K_DOWN) or is_down(pygame.K_s) or is_down(pygame.K_j) or is_down(pygame.K_KP2)
            # Diagonals vi-style
            if is_down(pygame.K_y) or is_down(pygame.K_KP7):
                left = True; up = True
            if is_down(pygame.K_u) or is_down(pygame.K_KP9):
                right = True; up = True
            if is_down(pygame.K_b) or is_down(pygame.K_KP1):
                left = True; down = True
            if is_down(pygame.K_n) or is_down(pygame.K_KP3):
                right = True; down = True
        except Exception:
            left = right = up = down = False

        dx = (1 if right else 0) - (1 if left else 0)
        dy = (1 if down else 0) - (1 if up else 0)
        self.player.set_input(float(dx), float(dy))
        return {"dx": float(dx), "dy": float(dy)}

    def handle_network_input(self, inp: Dict):
        """Apply network input dict {"dx": float, "dy": float}."""
        dx = float(inp.get("dx", 0))
        dy = float(inp.get("dy", 0))
        self.player.set_input(dx, dy)

    def handle_discrete_input(self, dx: int, dy: int):
        """Compat for old KEYDOWN discrete handling."""
        self.player.set_input(float(dx), float(dy))


# Registry for multiplayer — holds all known players by id
class PlayerRegistry:
    def __init__(self):
        self.players: Dict[str, Player] = {}

    def get_or_create(self, player_id: str, **kwargs) -> Player:
        if player_id not in self.players:
            self.players[player_id] = Player(player_id=player_id, **kwargs)
        return self.players[player_id]

    def update_from_network(self, states: Dict[str, Dict]):
        for pid, st in states.items():
            p = self.get_or_create(pid)
            p.apply_network_state(st)

    def to_dict(self) -> Dict[str, Dict]:
        return {pid: p.to_dict() for pid, p in self.players.items()}

    def remove(self, player_id: str):
        self.players.pop(player_id, None)
