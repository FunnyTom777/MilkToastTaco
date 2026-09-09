"""
MTT HUD — draws status bar, controls hint, debug overlay

Styles:
  solid       — opaque dark bar at bottom (classic)
  transparent — semi-transparent panel with alpha from config
  minimal     — tiny text, no background (max viewport)

Config-driven via config.xml <hud> + runtime toggles F3 (debug), H (hint).
Works in both ASCII (mode 1) and Sprite (mode 2) — always uses Courier.
"""
from __future__ import annotations

import math
from typing import Optional

try:
    import pygame
except ImportError:
    pygame = None  # type: ignore


_HUD_BG = (22, 22, 28)
_HUD_BG_ALPHA = (22, 22, 28)
_HUD_BORDER = (50, 50, 65)
_TEXT = (220, 220, 220)
_TEXT_DIM = (160, 160, 170)
_TEXT_HI = (255, 215, 0)
_DEBUG_BG = (18, 18, 24, 190)


def _get_font(size: int, bold: bool = True):
    if pygame is None:
        return None
    try:
        return pygame.font.SysFont("Courier", size, bold=bold)
    except Exception:
        return pygame.font.Font(None, size)


def draw_hud(
    screen,
    player,
    world,
    clock,
    tile_w: int,
    tile_h: int,
    viewport_cols: int,
    viewport_rows: int,
    font,  # main font (may be None in sprite mode)
    mode: int,
    zoom: float,
    config: dict,
    minimap_enabled: bool,
    fog_enabled: bool,
    show_debug: bool,
    dt: float,
    chunk_size: int,
):
    if pygame is None or screen is None:
        return

    SCREEN_WIDTH = 960
    SCREEN_HEIGHT = 720
    # allow caller to pass screen size via config or globals — we assume 960x720 per ascii.py
    try:
        sw, sh = screen.get_size()
        SCREEN_WIDTH, SCREEN_HEIGHT = sw, sh
    except Exception:
        pass

    style = config.get("hud_style", "transparent")
    alpha = int(config.get("hud_alpha", 180))
    show_fps = bool(config.get("hud_show_fps", True))
    show_coords = bool(config.get("hud_show_coords", True))
    show_hint = bool(config.get("hud_show_controls_hint", True))

    if font is None:
        # sprite mode — create a readable status font (slightly smaller than main tile)
        base_font = _get_font(14, bold=True)
        small_font = _get_font(11, bold=False)
        debug_font = _get_font(12, bold=False)
    else:
        base_font = font
        small_font = _get_font(11, bold=False)
        debug_font = _get_font(12, bold=False)

    # --- bottom status bar ------------------------------------------------
    bar_h = 28
    bar_y = SCREEN_HEIGHT - bar_h
    if style == "minimal":
        # no bg, just text with shadow
        pass
    elif style == "transparent":
        # semi-transparent panel
        try:
            surf = pygame.Surface((SCREEN_WIDTH, bar_h), pygame.SRCALPHA)
            surf.fill((*_HUD_BG, alpha))
            screen.blit(surf, (0, bar_y))
            pygame.draw.line(screen, _HUD_BORDER, (0, bar_y), (SCREEN_WIDTH, bar_y), 1)
        except Exception:
            pygame.draw.rect(screen, _HUD_BG, (0, bar_y, SCREEN_WIDTH, bar_h))
            pygame.draw.line(screen, _HUD_BORDER, (0, bar_y), (SCREEN_WIDTH, bar_y), 1)
    else:  # solid
        pygame.draw.rect(screen, _HUD_BG, (0, bar_y, SCREEN_WIDTH, bar_h))
        pygame.draw.line(screen, _HUD_BORDER, (0, bar_y), (SCREEN_WIDTH, bar_y), 1)

    # status text assembly
    p_cx = int(math.floor(player.x)) // chunk_size
    p_cy = int(math.floor(player.y)) // chunk_size
    mode_name = "ASCII" if mode == 1 else "SPRITES"
    parts = []
    if show_coords:
        parts.append(f"({player.x:.1f},{player.y:.1f})")
        parts.append(f"CHK {p_cx},{p_cy}")
    parts.append(f"{mode_name} x{zoom:.2f}")
    parts.append(f"LD {len(world.loaded_chunks)}")
    if show_fps:
        try:
            fps = clock.get_fps()
            parts.append(f"{fps:.0f} FPS")
        except Exception:
            pass
    # minimap/fog status
    map_tag = "MAP:ON" if minimap_enabled else "MAP:OFF"
    fog_tag = "FOG:ON" if fog_enabled else "FOG:OFF"
    parts.append(map_tag)
    parts.append(fog_tag)

    status_text = "  |  ".join(parts)

    # draw status with shadow for readability
    try:
        if base_font:
            # Use small font for status if base is huge (zoomed)
            use_font = base_font if base_font.get_height() <= 18 else small_font or base_font
            # shadow
            shadow = use_font.render(status_text, True, (10, 10, 10))
            screen.blit(shadow, (11, bar_y + (bar_h - shadow.get_height()) // 2 + 1))
            surf = use_font.render(status_text, True, _TEXT)
            screen.blit(surf, (10, bar_y + (bar_h - surf.get_height()) // 2))
    except Exception:
        pass

    # --- controls hint (top-left, small, semi-transparent) ----------------
    if show_hint:
        try:
            hint_lines = []
            # compact single-line hint at top
            if style == "minimal":
                hint = "WASD move  |  M map  F fog  F3 debug  R reload  +/- zoom  ESC save"
            else:
                hint = "WASD move  |  M map  F fog  F3 debug  R reload  +/- zoom  ESC save"
            # Render hint with tiny bg when transparent style
            hf = small_font or base_font
            if hf:
                if style != "minimal":
                    # bg behind hint
                    txt_surf = hf.render(hint, True, _TEXT_DIM)
                    bg_pad = 4
                    bg_rect = (6, 6, txt_surf.get_width() + bg_pad * 2, txt_surf.get_height() + bg_pad * 2)
                    if style == "transparent":
                        hs = pygame.Surface((bg_rect[2], bg_rect[3]), pygame.SRCALPHA)
                        hs.fill((*_HUD_BG, min(160, alpha)))
                        screen.blit(hs, (bg_rect[0], bg_rect[1]))
                    else:
                        pygame.draw.rect(screen, _HUD_BG, bg_rect)
                    pygame.draw.rect(screen, _HUD_BORDER, bg_rect, 1)
                    screen.blit(txt_surf, (bg_rect[0] + bg_pad, bg_rect[1] + bg_pad))
                else:
                    txt_surf = hf.render(hint, True, (200, 200, 200))
                    # shadow for minimal
                    sh = hf.render(hint, True, (0, 0, 0))
                    screen.blit(sh, (7, 7))
                    screen.blit(txt_surf, (6, 6))
        except Exception:
            pass

    # --- debug overlay (F3) -------------------------------------------------
    if show_debug:
        try:
            # Gather tile under player
            tile = world.get_tile(player.x, player.y)
            tile_info = "nil"
            if tile:
                tile_info = f"'{tile.char}' {tile.color} walk={tile.walkable} biome={getattr(tile,'biome','')}"
            # Player velocity
            vx = getattr(player, "vx", 0.0)
            vy = getattr(player, "vy", 0.0)
            speed = getattr(player, "speed", 0.0)
            # Build lines
            lines = [
                f"DEBUG  dt={dt*1000:.1f}ms  tile_wh={tile_w}x{tile_h}  vp={viewport_cols}x{viewport_rows}  mode={mode}",
                f"player pos=({player.x:.2f},{player.y:.2f}) vel=({vx:.2f},{vy:.2f}) speed={speed} id={getattr(player,'player_id','')}",
                f"tile under: {tile_info}",
                f"keys: M map ({'ON' if minimap_enabled else 'OFF'})  F fog ({'ON' if fog_enabled else 'OFF'})  R reload  +/- zoom ({zoom:.2f})",
            ]
            # panel rect — top-left under hint, or center if hint off
            panel_x = 6
            panel_y = 30 if show_hint else 6
            line_h = 14
            panel_w = max((debug_font.size(l)[0] if debug_font else 400) for l in lines) + 16
            panel_h = len(lines) * line_h + 10
            # bg
            try:
                ds = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
                ds.fill(_DEBUG_BG)
                screen.blit(ds, (panel_x, panel_y))
            except Exception:
                pygame.draw.rect(screen, (18, 18, 24), (panel_x, panel_y, panel_w, panel_h))
            pygame.draw.rect(screen, (80, 80, 100), (panel_x, panel_y, panel_w, panel_h), 1)
            if debug_font:
                for i, l in enumerate(lines):
                    c = _TEXT_HI if i == 0 else _TEXT
                    s = debug_font.render(l, True, c)
                    screen.blit(s, (panel_x + 8, panel_y + 6 + i * line_h))
        except Exception:
            pass
