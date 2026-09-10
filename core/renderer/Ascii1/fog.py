"""
MTT Player Fog-of-War — tile-based memory fog for main viewport

Concept:
  - Fog is centered on the player, radius in *tiles* (default 8).
  - Tiles within radius are fully visible and update the memory.
  - Tiles outside radius show the remembered snapshot dimmed, or solid fog if never seen.
  - Dimming is a color scale (fog_dim_factor 0.0..1.0).
  - Memory persists to saves_world1/fog_memory.xml when fog_save is true.
  - Toggle with F in-game, but only when debug=true (gated in ascii.py).

This replaces the old chunk-based minimap fog. The minimap now draws without fog.
"""
from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Tuple

_FOG_COLOR = (12, 12, 16)
_DIM_FOG_BLEND = (10, 10, 14)  # not used, kept for reference

def _dim_color(color: Tuple[int, int, int], factor: float) -> Tuple[int, int, int]:
    factor = max(0.0, min(1.0, factor))
    return (
        int(color[0] * factor),
        int(color[1] * factor),
        int(color[2] * factor),
    )

def _fog_save_path(save_dir: str | None = None) -> Path:
    if save_dir:
        return Path(save_dir) / "fog_memory.xml"
    try:
        from . import terrain_generation as _tg
        return Path(_tg.SAVE_DIR) / "fog_memory.xml"
    except Exception:
        return Path("saves_world1") / "fog_memory.xml"

# Also check legacy chunk fog file for migration (optional)
def _legacy_fog_path(save_dir: str | None = None) -> Path:
    if save_dir:
        return Path(save_dir) / "fog_discovered.xml"
    try:
        from . import terrain_generation as _tg
        return Path(_tg.SAVE_DIR) / "fog_discovered.xml"
    except Exception:
        return Path("saves_world1") / "fog_discovered.xml"


class PlayerFog:
    """
    Tile-based fog with memory.

    memory: Dict[(wx, wy)] -> (char, color, biome)
    """
    def __init__(self, config: dict | None = None):
        cfg = config or {}
        self.enabled: bool = bool(cfg.get("fog_enabled", True))
        # radius now in tiles (was chunks). Default 8 per spec.
        try:
            r = int(cfg.get("fog_radius", 8))
        except Exception:
            r = 8
        # Clamp to sensible tile range 0..32 (previously 0..10 for chunks)
        self.radius: int = max(0, min(32, r))
        # If legacy config had small radius 1..2 (chunks), treat as tiles *4? Keep as-is to avoid surprise.
        # But if radius was loaded from old 2-chunk config, 2 tiles is very tight — user can bump to 8 via config.
        self.dim_factor: float = float(cfg.get("fog_dim_factor", 0.45))
        self.dim_factor = max(0.0, min(1.0, self.dim_factor))
        self.fog_save: bool = bool(cfg.get("fog_save", True))
        self.fog_persist: bool = bool(cfg.get("fog_persist", True))
        # memory
        self.memory: Dict[Tuple[int, int], Tuple[str, Tuple[int, int, int], str]] = {}
        self._save_dir: str | None = None
        self._load()

    # ------------------------------------------------------------------ config
    def apply_config(self, cfg: dict):
        """Hot-reload from new config (R key). Preserves memory."""
        self.enabled = bool(cfg.get("fog_enabled", self.enabled))
        try:
            r = int(cfg.get("fog_radius", self.radius))
        except Exception:
            r = self.radius
        self.radius = max(0, min(32, r))
        try:
            df = float(cfg.get("fog_dim_factor", self.dim_factor))
        except Exception:
            df = self.dim_factor
        self.dim_factor = max(0.0, min(1.0, df))
        self.fog_save = bool(cfg.get("fog_save", self.fog_save))
        self.fog_persist = bool(cfg.get("fog_persist", self.fog_persist))

    # ------------------------------------------------------------------ persistence
    def _load(self):
        if not self.fog_save:
            return
        # Prefer new fog_memory.xml, fallback to legacy fog_discovered for migration? No tile data there.
        path = _fog_save_path(self._save_dir)
        legacy = _legacy_fog_path(self._save_dir)
        # Try primary
        loaded = False
        if path.is_file():
            try:
                tree = ET.parse(path)
                root = tree.getroot()
                for el in root.findall("Tile"):
                    try:
                        wx = int(el.get("x", "0"))
                        wy = int(el.get("y", "0"))
                        char = el.get("char", ".")
                        col_s = el.get("color", "18,18,22")
                        biome = el.get("biome", "")
                        rgb = tuple(int(x.strip()) for x in col_s.split(","))
                        if len(rgb) != 3:
                            continue
                        rgb = (max(0, min(255, rgb[0])), max(0, min(255, rgb[1])), max(0, min(255, rgb[2])))
                        self.memory[(wx, wy)] = (char, rgb, biome)
                    except Exception:
                        continue
                loaded = True
            except Exception:
                pass
        if not loaded and legacy.is_file():
            # Legacy file only has chunk discovery — cannot reconstruct tile memory, so ignore.
            # But we can try alternative SAVE_DIR
            try:
                from . import terrain_generation as _tg
                alt = Path(_tg.SAVE_DIR) / "fog_memory.xml"
                if alt.is_file() and alt != path:
                    try:
                        tree = ET.parse(alt)
                        root = tree.getroot()
                        for el in root.findall("Tile"):
                            wx = int(el.get("x", "0"))
                            wy = int(el.get("y", "0"))
                            char = el.get("char", ".")
                            col_s = el.get("color", "18,18,22")
                            biome = el.get("biome", "")
                            rgb = tuple(int(x.strip()) for x in col_s.split(","))
                            if len(rgb) == 3:
                                self.memory[(wx, wy)] = (char, (rgb[0], rgb[1], rgb[2]), biome)
                    except Exception:
                        pass
            except Exception:
                pass

    def save(self, save_dir: str | None = None):
        if not self.fog_save:
            return
        path = _fog_save_path(save_dir or self._save_dir)
        try:
            if not path.parent.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
            root = ET.Element("FogMemory", version="1")
            # Sort for deterministic diff
            for (wx, wy), (char, col, biome) in sorted(self.memory.items()):
                el = ET.SubElement(root, "Tile", x=str(wx), y=str(wy), char=char, color=f"{col[0]},{col[1]},{col[2]}")
                if biome:
                    el.set("biome", biome)
            ET.ElementTree(root).write(str(path), encoding="utf-8", xml_declaration=True)
        except Exception as e:
            print(f"[fog] save failed: {e}")

    def set_save_dir(self, save_dir: str):
        self._save_dir = save_dir
        if not self.memory:
            self._load()

    # ------------------------------------------------------------------ logic
    def is_visible(self, wx: int, wy: int, player_x: float, player_y: float) -> bool:
        """Euclidean distance check — visible if within radius tiles of player center."""
        # Player position is float; compare tile integer coord to player float pos.
        # Use Euclidean distance from tile center? Simple: distance from (wx+0.5, wy+0.5) vs player?
        # Spec says 8 blocks away — treat tile coordinate distance. Use player floored center vs tile?
        # We'll use distance from player.x/y to tile center approx. Use hypot(wx - px, wy - py).
        # This gives a circular fog.
        dx = (wx + 0.5) - player_x
        dy = (wy + 0.5) - player_y
        # Alternative: tile origin distance: hypot(wx - player_x, wy - player_y) — similar
        # Use tile center vs player pos for smoother circle.
        return math.hypot(dx, dy) <= self.radius + 1e-9

    def remember(self, wx: int, wy: int, tile):
        """Store snapshot of live tile into memory."""
        try:
            char = getattr(tile, "char", ".")
            color = getattr(tile, "color", (255, 255, 255))
            biome = getattr(tile, "biome", "")
            # Normalize color
            if isinstance(color, (list, tuple)) and len(color) == 3:
                color = (int(color[0]), int(color[1]), int(color[2]))
            else:
                color = (255, 255, 255)
            self.memory[(wx, wy)] = (char, color, biome)
        except Exception:
            pass

    def get_display(self, wx: int, wy: int, live_tile, player_x: float, player_y: float):
        """
        Returns (char, color, biome, is_memory) for display.
        - If fog disabled: returns live directly.
        - If visible: updates memory and returns live.
        - If not visible but memory exists and persist true: returns dimmed memory.
        - If not visible and no memory or persist false: returns fogged (dark).
        """
        if not self.enabled:
            if live_tile is None:
                return (".", _FOG_COLOR, "", False)
            return (live_tile.char, live_tile.color, getattr(live_tile, "biome", ""), False)

        visible = self.is_visible(wx, wy, player_x, player_y)
        if visible:
            if live_tile is not None:
                self.remember(wx, wy, live_tile)
                return (live_tile.char, live_tile.color, getattr(live_tile, "biome", ""), False)
            else:
                return (".", _FOG_COLOR, "", False)
        else:
            # outside radius
            if self.fog_persist and (wx, wy) in self.memory:
                ch, col, bio = self.memory[(wx, wy)]
                dim = _dim_color(col, self.dim_factor)
                return (ch, dim, bio, True)
            else:
                # Never seen or persist false -> dark fog
                # If we have memory but persist false, show dark instead of dim
                # Show remembered char but heavily dark? Spec says darken not black, but undiscovered should be dark.
                # We'll return dark fog color with maybe stored char dimmed heavily?
                # For unseen, show fog color block
                if (wx, wy) in self.memory and not self.fog_persist:
                    # snap to fog if persist false
                    return (self.memory[(wx, wy)][0], _FOG_COLOR, self.memory[(wx, wy)][2], True)
                # If never seen, show live char but dark? But that would reveal world — better fog color.
                # Use fog color and live char dimmed to near-black to hint but not reveal? Let's use fog color.
                # Return fog char as live if available else dot.
                if (wx, wy) in self.memory:
                    # Should have been handled above, but keep
                    ch, col, bio = self.memory[(wx, wy)]
                    return (ch, _dim_color(col, self.dim_factor), bio, True)
                # Unseen — show fog solid
                return (".", _FOG_COLOR, "", True)

    def toggle(self):
        self.enabled = not self.enabled
        return self.enabled
