"""
MTT Minimap — detail A (2px/tile) + fog-of-war

Detail A: each world tile = minimap_tile_px (default 2) pixels.
Centered on player, shows ~ size/tile_px tiles across (150/2=75).

Fog-of-war (config-driven):
  fog_enabled  — master switch (toggle F in-game)
  fog_radius   — chunks around player that become revealed (0..10)
  fog_persist  — true: discovered stays dimmed when you leave
                 false: only currently-within-radius stays lit, rest snaps to fog
  fog_dim_factor — 0.0..1.0 dim for visited-but-not-visible when persist true
  fog_save     — persist discovered set to saves_world1/fog_discovered.xml

Minimap toggled with M, hot-reload with R picks up config changes.
"""
from __future__ import annotations

import math
import os
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Set, Tuple

try:
    import pygame
except ImportError:
    pygame = None  # type: ignore


# fog colours — dark but not pure black so border still reads
_FOG_COLOR = (10, 10, 14)
_FOG_UNDISCOVERED = (18, 18, 22)
_BORDER_COLOR = (60, 60, 75)
_BORDER_HI = (90, 90, 110)
_VIEW_RECT_COLOR = (255, 255, 255)
_PLAYER_DOT = (255, 215, 0)
_PLAYER_OUTLINE = (20, 20, 20)


def _dim_color(color: Tuple[int, int, int], factor: float) -> Tuple[int, int, int]:
    """Dim an RGB tuple toward dark. factor 1.0 = unchanged, 0.0 = near-black."""
    factor = max(0.0, min(1.0, factor))
    # blend toward _FOG_COLOR slightly so dim isn't just darker but fog-tinted
    # simpler: just scale
    return (
        int(color[0] * factor),
        int(color[1] * factor),
        int(color[2] * factor),
    )


def _fog_save_path(save_dir: str | None = None) -> Path:
    if save_dir:
        return Path(save_dir) / "fog_discovered.xml"
    # try to resolve via terrain_generation SAVE_DIR
    try:
        from . import terrain_generation as _tg
        return Path(_tg.SAVE_DIR) / "fog_discovered.xml"
    except Exception:
        return Path("saves_world1") / "fog_discovered.xml"


class Minimap:
    def __init__(self, config: dict | None = None):
        cfg = config or {}
        self.enabled: bool = bool(cfg.get("minimap_enabled", True))
        self.size: int = int(cfg.get("minimap_size", 150))
        self.tile_px: int = int(cfg.get("minimap_tile_px", 2))
        self.position: str = str(cfg.get("minimap_position", "top_right"))
        self.border: bool = bool(cfg.get("minimap_border", True))
        self.show_view_rect: bool = bool(cfg.get("minimap_show_view_rect", True))

        self.fog_enabled: bool = bool(cfg.get("fog_enabled", True))
        self.fog_radius: int = int(cfg.get("fog_radius", 2))
        self.fog_persist: bool = bool(cfg.get("fog_persist", True))
        self.fog_dim_factor: float = float(cfg.get("fog_dim_factor", 0.45))
        self.fog_save: bool = bool(cfg.get("fog_save", True))

        self.pad: int = 10
        # discovered chunks — shared across sessions if fog_save
        self.discovered: Set[Tuple[int, int]] = set()
        self._save_dir: str | None = None
        # try to load
        self._load()

    # ------------------------------------------------------------------ config
    def apply_config(self, cfg: dict):
        """Hot-reload from new config (R key). Preserves discovered set."""
        self.enabled = bool(cfg.get("minimap_enabled", self.enabled))
        self.size = int(cfg.get("minimap_size", self.size))
        self.tile_px = int(cfg.get("minimap_tile_px", self.tile_px))
        self.position = str(cfg.get("minimap_position", self.position))
        self.border = bool(cfg.get("minimap_border", self.border))
        self.show_view_rect = bool(cfg.get("minimap_show_view_rect", self.show_view_rect))
        self.fog_enabled = bool(cfg.get("fog_enabled", self.fog_enabled))
        self.fog_radius = int(cfg.get("fog_radius", self.fog_radius))
        self.fog_persist = bool(cfg.get("fog_persist", self.fog_persist))
        self.fog_dim_factor = float(cfg.get("fog_dim_factor", self.fog_dim_factor))
        self.fog_save = bool(cfg.get("fog_save", self.fog_save))
        # clamp
        self.size = max(80, min(400, self.size))
        self.tile_px = max(1, min(6, self.tile_px))
        self.fog_radius = max(0, min(10, self.fog_radius))
        self.fog_dim_factor = max(0.0, min(1.0, self.fog_dim_factor))

    # ------------------------------------------------------------------ fog I/O
    def _load(self):
        if not self.fog_save:
            return
        path = _fog_save_path(self._save_dir)
        if not path.is_file():
            # also try absolute SAVE_DIR from terrain_generation
            try:
                from . import terrain_generation as _tg
                alt = Path(_tg.SAVE_DIR) / "fog_discovered.xml"
                if alt.is_file():
                    path = alt
                else:
                    return
            except Exception:
                return
        try:
            tree = ET.parse(path)
            root = tree.getroot()
            for el in root.findall("Chunk"):
                try:
                    cx = int(el.get("cx", "0"))
                    cy = int(el.get("cy", "0"))
                    self.discovered.add((cx, cy))
                except Exception:
                    continue
        except Exception:
            pass

    def save(self, save_dir: str | None = None):
        if not self.fog_save:
            return
        path = _fog_save_path(save_dir or self._save_dir)
        try:
            if not path.parent.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
            root = ET.Element("Fog", version="1")
            for cx, cy in sorted(self.discovered):
                ET.SubElement(root, "Chunk", cx=str(cx), cy=str(cy))
            ET.ElementTree(root).write(str(path), encoding="utf-8", xml_declaration=True)
        except Exception as e:
            print(f"[minimap] fog save failed: {e}")

    def set_save_dir(self, save_dir: str):
        self._save_dir = save_dir
        # reload from new location if exists and we have nothing yet
        if not self.discovered:
            self._load()

    # ------------------------------------------------------------------ discovery
    def update_discovery(self, player_x: float, player_y: float, chunk_size: int):
        """Reveal chunks within fog_radius of player. No-op if fog disabled."""
        if not self.fog_enabled:
            return
        # player chunk with floor handling for negatives
        pcx = int(math.floor(player_x)) // chunk_size
        pcy = int(math.floor(player_y)) // chunk_size
        # Python // does floor for negatives, but floor(player_x) already
        # so this is correct. Keep explicit for clarity using math.floor quotient
        # The above works because int(math.floor()) is already exact.
        r = self.fog_radius
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                # Chebyshev radius (square) — feels better for chunk grid than euclidean
                # If you want circle, use dx*dx+dy*dy <= r*r
                self.discovered.add((pcx + dx, pcy + dy))

    def _is_visible_now(self, cx: int, cy: int, player_cx: int, player_cy: int) -> bool:
        return abs(cx - player_cx) <= self.fog_radius and abs(cy - player_cy) <= self.fog_radius

    # ------------------------------------------------------------------ geometry
    def _panel_rect(self, screen_w: int, screen_h: int) -> Tuple[int, int, int, int]:
        """Return (x, y, w, h) for minimap panel."""
        s = self.size
        pad = self.pad
        if self.position == "top_left":
            return (pad, pad, s, s)
        if self.position == "bottom_right":
            return (screen_w - s - pad, screen_h - s - pad - 30, s, s)  # -30 for status bar
        if self.position == "bottom_left":
            return (pad, screen_h - s - pad - 30, s, s)
        # top_right default
        return (screen_w - s - pad, pad, s, s)

    # ------------------------------------------------------------------ draw
    def draw(self, screen, world, player, viewport_cols: int, viewport_rows: int,
             cam_x: float, cam_y: float, chunk_size: int, screen_w: int, screen_h: int):
        if pygame is None or not self.enabled:
            return
        if screen is None:
            return

        panel_x, panel_y, panel_w, panel_h = self._panel_rect(screen_w, screen_h)

        # panel background
        bg = (22, 22, 28)
        pygame.draw.rect(screen, bg, (panel_x, panel_y, panel_w, panel_h))
        if self.border:
            pygame.draw.rect(screen, _BORDER_COLOR, (panel_x, panel_y, panel_w, panel_h), 2)
            # inner bevel
            pygame.draw.rect(screen, _BORDER_HI, (panel_x, panel_y, panel_w, panel_h), 1)

        # clip to interior
        inner_x = panel_x + 2
        inner_y = panel_y + 2
        inner_w = panel_w - 4
        inner_h = panel_h - 4

        # Use a subsurface / clip via drawing bounds check
        half_tiles = inner_w // self.tile_px // 2
        # Also handle non-square inner; approximate same half for y
        half_tiles_y = inner_h // self.tile_px // 2
        # Center on player's floored tile but account for fractional for smoothness
        # Player tile center
        p_tx = int(math.floor(player.x))
        p_ty = int(math.floor(player.y))
        # minimap world origin (top-left world tile shown at inner_x, inner_y)
        origin_wx = p_tx - half_tiles
        origin_wy = p_ty - half_tiles_y

        # player chunk for fog visibility
        p_cx = int(math.floor(player.x)) // chunk_size
        p_cy = int(math.floor(player.y)) // chunk_size

        # draw tiles row by row
        tpx = self.tile_px
        # Iterate over tiles that land inside inner rect
        cols = inner_w // tpx
        rows = inner_h // tpx
        # shift to exactly center (account for remainder)
        # Recompute origin so player dot is exactly centered
        # Center pixel of panel
        center_px = inner_x + inner_w // 2
        center_py = inner_y + inner_h // 2
        # Instead of origin method, compute each tile's screen pos as center + delta*tpx
        # This keeps player dot pixel-perfect centered even with odd sizes.
        for dy in range(-half_tiles_y - 1, half_tiles_y + 2):
            wy = p_ty + dy
            for dx in range(-half_tiles - 1, half_tiles + 2):
                wx = p_tx + dx
                # screen pos for this tile's top-left
                sx = center_px + dx * tpx - tpx // 2
                sy = center_py + dy * tpx - tpx // 2

                # clip
                if sx + tpx < inner_x or sx >= inner_x + inner_w:
                    continue
                if sy + tpx < inner_y or sy >= inner_y + inner_h:
                    continue

                tile = None
                try:
                    tile = world.get_tile(wx, wy)
                except Exception:
                    tile = None

                if tile is None:
                    # undiscovered void — fog
                    col = _FOG_UNDISCOVERED
                else:
                    base = tile.color
                    if not self.fog_enabled:
                        col = base
                    else:
                        # chunk for this tile
                        cx = int(math.floor(wx)) // chunk_size
                        cy = int(math.floor(wy)) // chunk_size
                        discovered = (cx, cy) in self.discovered
                        visible = self._is_visible_now(cx, cy, p_cx, p_cy)
                        if not discovered:
                            col = _FOG_UNDISCOVERED
                        elif not visible:
                            if self.fog_persist:
                                # dimmed — already visited but not currently in radius
                                col = _dim_color(base, self.fog_dim_factor)
                            else:
                                col = _FOG_UNDISCOVERED
                        else:
                            col = base
                # draw tile pixel
                # Clip to inner rect precise (avoid border overflow)
                draw_x = max(sx, inner_x)
                draw_y = max(sy, inner_y)
                draw_w = min(tpx, inner_x + inner_w - draw_x, sx + tpx - draw_x)
                draw_h = min(tpx, inner_y + inner_h - draw_y, sy + tpx - draw_y)
                if draw_w > 0 and draw_h > 0:
                    pygame.draw.rect(screen, col, (draw_x, draw_y, draw_w, draw_h))

        # view rect — where the main camera is looking
        if self.show_view_rect:
            # cam_x/cam_y is top-left world float of viewport
            # Convert viewport rect corners to minimap pixels
            # Use same center+delta mapping as tiles
            # cam origin relative to player tile center
            # viewport covers cam_x .. cam_x+viewport_cols, cam_y .. cam_y+viewport_rows
            # player at (player.x, player.y) world float
            view_x = center_px + (cam_x - p_tx) * tpx - tpx // 2
            # p_ty is floor(player.y), but center_py is at floor — need same offset as tiles
            view_y = center_py + (cam_y - p_ty) * tpx - tpx // 2
            view_w = viewport_cols * tpx
            view_h = viewport_rows * tpx
            # Clip to inner
            # Draw as hollow rect (1px white with slight alpha via solid white)
            # Use pygame.draw.rect with width=1
            try:
                # Clamp rect to inner for clean edge
                rx = int(view_x)
                ry = int(view_y)
                rw = int(view_w)
                rh = int(view_h)
                # Only draw if at least partially inside
                if rx < inner_x + inner_w and rx + rw > inner_x and ry < inner_y + inner_h and ry + rh > inner_y:
                    pygame.draw.rect(screen, _VIEW_RECT_COLOR, (rx, ry, rw, rh), 1)
            except Exception:
                pass

        # player dot — centered, with outline
        try:
            # Fractional sub-tile smoothing: offset dot by frac(player)
            frac_x = player.x - math.floor(player.x) - 0.5
            frac_y = player.y - math.floor(player.y) - 0.5
            dot_x = center_px + int(round(frac_x * tpx))
            dot_y = center_py + int(round(frac_y * tpx))
            # dot size ~ 3px or 4px depending on tile_px
            dot_r = 3 if tpx <= 2 else 4
            # outline first
            pygame.draw.circle(screen, _PLAYER_OUTLINE, (dot_x, dot_y), dot_r + 1)
            pygame.draw.circle(screen, _PLAYER_DOT, (dot_x, dot_y), dot_r)
            # center pixel white
            pygame.draw.circle(screen, (255, 255, 255), (dot_x, dot_y), 1)
        except Exception:
            pass

        # small label "MAP" bottom center, and fog hint
        try:
            font = pygame.font.SysFont("Courier", 10, bold=True)
            label = font.render("MAP", True, (200, 200, 200))
            screen.blit(label, (inner_x + inner_w // 2 - label.get_width() // 2, inner_y + inner_h - 11))
            if self.fog_enabled:
                fog_lbl = font.render(f"FOG:{self.fog_radius}", True, (150, 150, 160))
                screen.blit(fog_lbl, (inner_x + 3, inner_y + inner_h - 11))
        except Exception:
            pass
