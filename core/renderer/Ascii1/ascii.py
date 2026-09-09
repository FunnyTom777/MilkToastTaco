import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
import pygame

# Minimap + HUD — optional, graceful fallback if modules missing (tests / headless)
try:
    from .minimap import Minimap
except ImportError:
    try:
        from core.renderer.Ascii1.minimap import Minimap
    except ImportError:
        try:
            from minimap import Minimap
        except ImportError:
            Minimap = None  # type: ignore

try:
    from .hud import draw_hud
except ImportError:
    try:
        from core.renderer.Ascii1.hud import draw_hud
    except ImportError:
        try:
            from hud import draw_hud
        except ImportError:
            draw_hud = None  # type: ignore

# --- TERRAIN GENERATION (data-driven via generation.xml) ---
# All procedural logic now lives in terrain_generation.py.
# Edit generation.xml to tweak biomes, noise, glyphs without touching code.
# Supports all run modes:
#   python ascii.py                       (inside Ascii1/)
#   python core/renderer/Ascii1/ascii.py  (from repo root)
#   python -m core.renderer.Ascii1.ascii  (as module)
try:
    from .terrain_generation import (
        Tile,
        get_terrain_type,
        get_generation_config,
        reload_generation_config,
        load_generation_config,
    )
    from . import terrain_generation as _tg
    # try to also import biome-aware helper if available
    try:
        from .terrain_generation import get_terrain_with_biome
    except ImportError:
        get_terrain_with_biome = None
except ImportError:
    try:
        from core.renderer.Ascii1.terrain_generation import (
            Tile,
            get_terrain_type,
            get_generation_config,
            reload_generation_config,
            load_generation_config,
        )
        import core.renderer.Ascii1.terrain_generation as _tg
        try:
            from core.renderer.Ascii1.terrain_generation import get_terrain_with_biome
        except ImportError:
            get_terrain_with_biome = None
    except ImportError:
        # Fallback when executed as plain script inside Ascii1/ dir
        import terrain_generation as _tg
        from terrain_generation import (
            Tile,
            get_terrain_type,
            get_generation_config,
            reload_generation_config,
            load_generation_config,
        )
        try:
            from terrain_generation import get_terrain_with_biome
        except ImportError:
            get_terrain_with_biome = None

# Pull live values — note: after a hot-reload these module attrs update,
# but ascii's legacy names are refreshed via _sync_from_tg() below.
CHUNK_SIZE = _tg.CHUNK_SIZE
SAVE_DIR = _tg.SAVE_DIR
GLYPHS = _tg.GLYPHS
COLORS = _tg.COLORS
PALETTE = _tg.PALETTE
COLOR_BG = _tg.COLOR_BG
COLOR_DARK_GRAY = _tg.COLOR_DARK_GRAY
COLOR_GROUND = _tg.COLOR_GROUND
COLOR_SAND = getattr(_tg, "COLOR_SAND", (210, 180, 140))
COLOR_TREE = _tg.COLOR_TREE
COLOR_MOUNTAIN = _tg.COLOR_MOUNTAIN
COLOR_WATER = _tg.COLOR_WATER
COLOR_PLAYER = _tg.COLOR_PLAYER
COLOR_TEXT = _tg.COLOR_TEXT
HAS_NOISE = _tg.HAS_NOISE


def _sync_from_tg():
    """Refresh ascii's legacy globals after generation.xml reload."""
    global CHUNK_SIZE, SAVE_DIR, GLYPHS, COLORS, PALETTE
    global COLOR_BG, COLOR_DARK_GRAY, COLOR_GROUND, COLOR_SAND, COLOR_TREE, COLOR_MOUNTAIN, COLOR_WATER, COLOR_PLAYER, COLOR_TEXT, HAS_NOISE
    CHUNK_SIZE = _tg.CHUNK_SIZE
    SAVE_DIR = _tg.SAVE_DIR
    GLYPHS = _tg.GLYPHS
    COLORS = _tg.COLORS
    PALETTE = _tg.PALETTE
    COLOR_BG = _tg.COLOR_BG
    COLOR_DARK_GRAY = _tg.COLOR_DARK_GRAY
    COLOR_GROUND = _tg.COLOR_GROUND
    COLOR_SAND = getattr(_tg, "COLOR_SAND", (210, 180, 140))
    COLOR_TREE = _tg.COLOR_TREE
    COLOR_MOUNTAIN = _tg.COLOR_MOUNTAIN
    COLOR_WATER = _tg.COLOR_WATER
    COLOR_PLAYER = _tg.COLOR_PLAYER
    COLOR_TEXT = _tg.COLOR_TEXT
    HAS_NOISE = _tg.HAS_NOISE

# --- RENDERER CONFIG (config.xml) ---
# renderer_mode: 1 = ASCII, 2 = Sprites
# zoom: camera multiplier (0.5..3.0)
# Extended with minimap / fog / hud blocks — all optional, backward compat.
_DEFAULT_RENDER_CONFIG = {
    "renderer_mode": 1,
    "tile_size": 32,
    "zoom": 1.0,
    "debug": True,
    # minimap (detail A = 2px/tile)
    "minimap_enabled": True,
    "minimap_size": 150,
    "minimap_tile_px": 2,
    "minimap_position": "top_right",
    "minimap_border": True,
    "minimap_show_view_rect": True,
    # fog-of-war
    "fog_enabled": True,
    "fog_radius": 2,
    "fog_persist": True,
    "fog_dim_factor": 0.45,
    "fog_save": True,
    # hud
    "hud_style": "transparent",  # solid / transparent / minimal
    "hud_alpha": 180,
    "hud_show_fps": True,
    "hud_show_coords": True,
    "hud_show_controls_hint": True,
}
_RENDER_CONFIG = dict(_DEFAULT_RENDER_CONFIG)
RENDERER_MODE = 1
TILE_SIZE = 32
ZOOM = 1.0
SPRITES = {}          # biome_id -> pygame.Surface
MISSING_SPRITES = []  # list of strings for report

def _find_config_xml(explicit=None):
    cands = []
    if explicit:
        cands.append(Path(explicit))
    cands.append(Path(__file__).with_name("config.xml"))
    try:
        repo_data = Path(__file__).resolve().parents[3] / "data" / "config.xml"
        cands.append(repo_data)
    except Exception:
        pass
    cands.append(Path.cwd() / "data" / "config.xml")
    cands.append(Path.cwd() / "core" / "renderer" / "Ascii1" / "config.xml")
    cands.append(Path.cwd() / "config.xml")
    for p in cands:
        try:
            if p.is_file():
                return p
        except Exception:
            continue
    return None

def _parse_bool(text, default=True):
    if text is None:
        return default
    return text.strip().lower() in ("true", "1", "yes", "on")

def load_renderer_config(path=None):
    """Load config.xml — sets RENDERER_MODE, TILE_SIZE, ZOOM + minimap/fog/hud. Returns dict."""
    global RENDERER_MODE, TILE_SIZE, ZOOM, _RENDER_CONFIG
    xml_path = _find_config_xml(path)
    if xml_path is None:
        if path is not None:
            print(f"[ascii] config.xml not found at '{path}', using defaults.")
        _RENDER_CONFIG = dict(_DEFAULT_RENDER_CONFIG)
        RENDERER_MODE = _RENDER_CONFIG["renderer_mode"]
        TILE_SIZE = _RENDER_CONFIG["tile_size"]
        ZOOM = _RENDER_CONFIG["zoom"]
        return dict(_RENDER_CONFIG)
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        def _text(elem_name, default=""):
            el = root.find(elem_name)
            if el is not None and el.text is not None:
                return el.text.strip()
            return default

        def _nested(parent_name, child_name, default=""):
            parent = root.find(parent_name)
            if parent is not None:
                el = parent.find(child_name)
                if el is not None and el.text is not None:
                    return el.text.strip()
            return default

        mode = int(_text("renderer_mode", "1") or "1")
        if mode not in (1, 2):
            print(f"[ascii] Invalid renderer_mode {mode} in {xml_path}, fallback to 1")
            mode = 1
        tile_size = int(_text("tile_size", "32") or "32")
        tile_size = max(8, min(128, tile_size))
        zoom = float(_text("zoom", "1.0") or "1.0")
        zoom = max(0.25, min(4.0, zoom))
        debug_raw = root.find("debug")
        debug = _parse_bool(debug_raw.text if debug_raw is not None and debug_raw.text else "true", True)

        # --- minimap ---
        minimap_enabled = _parse_bool(_nested("minimap", "enabled", "true"), True)
        try:
            minimap_size = int(_nested("minimap", "size", "150") or "150")
        except Exception:
            minimap_size = 150
        minimap_size = max(80, min(400, minimap_size))
        try:
            minimap_tile_px = int(_nested("minimap", "tile_px", "2") or "2")
        except Exception:
            minimap_tile_px = 2
        minimap_tile_px = max(1, min(6, minimap_tile_px))
        minimap_position = _nested("minimap", "position", "top_right") or "top_right"
        if minimap_position not in ("top_right", "top_left", "bottom_right", "bottom_left"):
            minimap_position = "top_right"
        minimap_border = _parse_bool(_nested("minimap", "border", "true"), True)
        minimap_show_view_rect = _parse_bool(_nested("minimap", "show_view_rect", "true"), True)

        # --- fog ---
        fog_enabled = _parse_bool(_nested("fog", "enabled", "true"), True)
        try:
            fog_radius = int(_nested("fog", "radius", "2") or "2")
        except Exception:
            fog_radius = 2
        fog_radius = max(0, min(10, fog_radius))
        fog_persist = _parse_bool(_nested("fog", "persist", "true"), True)
        try:
            fog_dim_factor = float(_nested("fog", "dim_factor", "0.45") or "0.45")
        except Exception:
            fog_dim_factor = 0.45
        fog_dim_factor = max(0.0, min(1.0, fog_dim_factor))
        fog_save = _parse_bool(_nested("fog", "save", "true"), True)

        # --- hud ---
        hud_style = _nested("hud", "style", "transparent") or "transparent"
        if hud_style not in ("solid", "transparent", "minimal"):
            hud_style = "transparent"
        try:
            hud_alpha = int(_nested("hud", "alpha", "180") or "180")
        except Exception:
            hud_alpha = 180
        hud_alpha = max(0, min(255, hud_alpha))
        hud_show_fps = _parse_bool(_nested("hud", "show_fps", "true"), True)
        hud_show_coords = _parse_bool(_nested("hud", "show_coords", "true"), True)
        hud_show_controls_hint = _parse_bool(_nested("hud", "show_controls_hint", "true"), True)

        _RENDER_CONFIG = {
            "renderer_mode": mode,
            "tile_size": tile_size,
            "zoom": zoom,
            "debug": debug,
            "path": str(xml_path),
            "minimap_enabled": minimap_enabled,
            "minimap_size": minimap_size,
            "minimap_tile_px": minimap_tile_px,
            "minimap_position": minimap_position,
            "minimap_border": minimap_border,
            "minimap_show_view_rect": minimap_show_view_rect,
            "fog_enabled": fog_enabled,
            "fog_radius": fog_radius,
            "fog_persist": fog_persist,
            "fog_dim_factor": fog_dim_factor,
            "fog_save": fog_save,
            "hud_style": hud_style,
            "hud_alpha": hud_alpha,
            "hud_show_fps": hud_show_fps,
            "hud_show_coords": hud_show_coords,
            "hud_show_controls_hint": hud_show_controls_hint,
        }
        RENDERER_MODE = mode
        TILE_SIZE = tile_size
        ZOOM = zoom
        return dict(_RENDER_CONFIG)
    except Exception as e:
        print(f"[ascii] Failed parsing {xml_path}: {e} — using defaults")
        _RENDER_CONFIG = dict(_DEFAULT_RENDER_CONFIG)
        _RENDER_CONFIG["path"] = str(xml_path) if 'xml_path' in locals() and xml_path else ""
        RENDERER_MODE = _RENDER_CONFIG["renderer_mode"]
        TILE_SIZE = _RENDER_CONFIG["tile_size"]
        ZOOM = _RENDER_CONFIG["zoom"]
        return dict(_RENDER_CONFIG)

def get_renderer_config():
    return dict(_RENDER_CONFIG)

# Auto-load on import (so tests see defaults)
try:
    load_renderer_config()
except Exception:
    pass

def _get_assets_base():
    """Repo assets base — resolves to MilkToastTaco/assets"""
    try:
        return Path(__file__).resolve().parents[3] / "assets"
    except Exception:
        return Path.cwd() / "assets"

SPRITE_VARIANTS = {}  # biome -> list[(Surface, weight)]

def _load_img(path, tile_size):
    img = pygame.image.load(str(path))
    try:
        img = img.convert_alpha()
    except Exception:
        img = img.convert()
    return pygame.transform.scale(img, (tile_size, tile_size))

def load_sprites(tile_size=None):
    """
    Load PNG sprites for each biome. Returns (sprites dict, missing list).
    - Sprites expected under assets/tiles/nature/
    - Missing entries are left blank per spec and reported.
    - Variant sprites (grass_plain2, flowers, rocky_dirt, wheat) are auto-detected and
      used for deterministic per-tile variation in sprite mode.
    """
    global SPRITES, MISSING_SPRITES, SPRITE_VARIANTS
    if tile_size is None:
        tile_size = TILE_SIZE
    base = _get_assets_base() / "tiles" / "nature"
    # Mapping biome -> expected filename (user can rename/add)
    expected = {
        "water":  base / "water1.png",
        "sand":   base / "sand1.png",
        "ground": base / "grass_plain1.png",
        "forest": base / "forest_denser1.png",
        "mountain": base / "mountain1.png",
        "player": base / "player1.png",
        "wheat": base / "wheat1.png",
        "wheat_trampled": base / "wheat1_trampled.png",
    }
    sprites = {}
    missing = []
    for biome, path in expected.items():
        if path.is_file():
            try:
                sprites[biome] = _load_img(path, tile_size)
            except Exception as e:
                missing.append(f"{biome}: {path.name} (load failed: {e})")
        else:
            missing.append(f"{biome}: {path.name} (missing) -> {path}")

    # ---- Variant sprites — deterministic per-tile variation ----
    # Each entry: biome -> list of (path, weight)
    # Wheat is now a field clump, not a random ground variant — separated biomes
    variant_defs = {
        "ground": [
            (base / "grass_plain1.png", 40),
            (base / "grass_plain2.png", 30),
            (base / "grass_plain_with_flowers1.png", 18),
            (base / "grass_with_bush1.png", 12),
        ],
        "mountain": [
            (base / "mountain1.png", 60),
            (base / "rocky_dirt1.png", 40),
        ],
        "forest": [
            (base / "forest_denser1.png", 60),
            (base / "tree1.png", 40),
        ],
        "sand": [
            (base / "sand1.png", 100),
        ],
        "water": [
            (base / "water1.png", 100),
        ],
        "wheat": [
            (base / "wheat1.png", 100),
        ],
        "wheat_trampled": [
            (base / "wheat1_trampled.png", 100),
        ],
    }
    sprite_variants = {}
    for biome, lst in variant_defs.items():
        loaded = []
        total_w = 0
        for p, w in lst:
            if p.is_file():
                try:
                    loaded.append((_load_img(p, tile_size), w))
                    total_w += w
                except Exception:
                    pass
            else:
                # Only report as missing if it's an expected variant the user might want
                if p.name not in ("grass_plain1.png", "tree1.png", "sand1.png", "water1.png", "mountain1.png"):
                    # Don't clutter with every variant missing — only core expected already reported
                    pass
        if loaded:
            sprite_variants[biome] = loaded
            # Also ensure base sprites dict has at least one (for fallback)
            if biome not in sprites and loaded:
                sprites[biome] = loaded[0][0]

    # Also check for extra nice-to-haves that would improve variation (truly missing)
    nice_to_have = [
        ("sand", base / "sand2.png", "sand variant"),
        ("water", base / "water2.png", "water variant"),
        ("forest", base / "tree2.png", "tree variant"),
    ]
    for biome, p, desc in nice_to_have:
        if not p.is_file():
            if any(p.name in m for m in missing):
                continue
            missing.append(f"{biome}: {p.name} ({desc}) -> {p}")

    SPRITES = sprites
    SPRITE_VARIANTS = sprite_variants
    MISSING_SPRITES = missing
    return sprites, missing

def _pick_variant_sprite(biome, wx, wy):
    """Deterministic variant pick for sprite mode (like terrain variants)."""
    variants = SPRITE_VARIANTS.get(biome)
    if not variants:
        return SPRITES.get(biome)
    # Use same hash as terrain_generation for determinism (needs _tg seed)
    try:
        seed = _tg.get_generation_config().seed if hasattr(_tg, "get_generation_config") else 0
    except Exception:
        seed = 0
    import random as _rnd
    h = (int(wx) * 73856093) ^ (int(wy) * 19349663) ^ (seed * 83492791) ^ (hash(biome) & 0xFFFF)
    rng = _rnd.Random(h & 0xFFFFFFFF)
    total = sum(w for _, w in variants)
    r = rng.random() * total
    acc = 0
    for surf, w in variants:
        acc += w
        if r < acc:
            return surf
    return variants[-1][0]

def get_missing_sprites_report():
    """Return list of missing sprite suggestions (call after load_sprites)."""
    return list(MISSING_SPRITES)

# --- CONFIGURATION (rendering only — terrain is in generation.xml) ---
FONT_SIZE = 20
SCREEN_WIDTH = 960
SCREEN_HEIGHT = 720

# Load/Render Radii (in Chunks)
VIEW_RADIUS_CHUNKS = 2   # Visible range
LOAD_RADIUS_CHUNKS = 4   # Buffer generation range (prevents visual pop-in)

# --- TILE & CHUNK CLASSES ---
# Tile is imported from terrain_generation; re-exported above for compat.

class Chunk:
    def __init__(self, cx, cy):
        self.cx = cx
        self.cy = cy
        self.tiles = {}  # Relative (x, y) -> Tile
        self.modified = False
        
        if not self.load_from_xml():
            self.generate()

    def generate(self):
        """Generates chunk terrain based on world coordinates (via terrain_generation)."""
        # Use live CHUNK_SIZE from terrain_generation in case generation.xml changed it
        cs = _tg.CHUNK_SIZE
        # Prefer biome-aware helper for sprite mapping
        use_biome = get_terrain_with_biome is not None
        for y in range(cs):
            for x in range(cs):
                wx = self.cx * cs + x
                wy = self.cy * cs + y
                if use_biome:
                    char, color, walkable, biome = get_terrain_with_biome(wx, wy)
                    self.tiles[(x, y)] = Tile(char, color, walkable, biome)
                else:
                    char, color, walkable = get_terrain_type(wx, wy)
                    # Fallback: infer biome from color if we can't get it
                    biome = ""
                    for bid, col in _tg.COLORS.items():
                        if col == color:
                            biome = bid
                            break
                    self.tiles[(x, y)] = Tile(char, color, walkable, biome)

    def save_to_xml(self):
        """Saves chunk contents to an XML file."""
        save_dir = _tg.SAVE_DIR
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        root = ET.Element("Chunk", cx=str(self.cx), cy=str(self.cy))
        for (x, y), tile in self.tiles.items():
            tile_elem = ET.SubElement(root, "Tile", x=str(x), y=str(y))
            tile_elem.set("char", tile.char)
            tile_elem.set("walkable", str(tile.walkable))
            # Color as comma-separated str
            tile_elem.set("color", f"{tile.color[0]},{tile.color[1]},{tile.color[2]}")
            # Persist biome for sprite mode (backward compat: old files lack this)
            if getattr(tile, "biome", ""):
                tile_elem.set("biome", tile.biome)

        tree = ET.ElementTree(root)
        filename = os.path.join(save_dir, f"chunk_{self.cx}_{self.cy}.xml")
        tree.write(filename)

    def load_from_xml(self):
        """Attempts to load chunk state from an existing XML file."""
        save_dir = _tg.SAVE_DIR
        filename = os.path.join(save_dir, f"chunk_{self.cx}_{self.cy}.xml")
        if not os.path.exists(filename):
            return False

        try:
            tree = ET.parse(filename)
            root = tree.getroot()
            for tile_elem in root.findall("Tile"):
                x = int(tile_elem.attrib["x"])
                y = int(tile_elem.attrib["y"])
                char = tile_elem.attrib["char"]
                walkable = tile_elem.attrib["walkable"] == "True"
                rgb = tuple(map(int, tile_elem.attrib["color"].split(",")))
                biome = tile_elem.attrib.get("biome", "")
                # Backward compat: infer biome from color if missing
                if not biome:
                    for bid, col in _tg.COLORS.items():
                        if col == rgb:
                            biome = bid
                            break
                    # Fallback for old saves that stored scatter colors
                    if not biome:
                        # Map known scatter colors to base biomes
                        # e.g. shell colors on sand -> sand
                        if rgb in [(205,170,125), (255,228,181)]:
                            biome = "sand"
                        elif rgb in [(50,205,50), (139,69,19), (255,215,0)]:
                            biome = "ground"
                        elif rgb == (0,191,255):
                            biome = "water"
                        elif rgb == (105,105,105):
                            biome = "mountain"
                self.tiles[(x, y)] = Tile(char, rgb, walkable, biome)
            return True
        except Exception as e:
            print(f"Failed loading chunk ({self.cx}, {self.cy}): {e}")
            return False

# --- WORLD MANAGER ---
class World:
    def __init__(self):
        self.loaded_chunks = {}  # (cx, cy) -> Chunk

    def get_tile(self, wx, wy):
        # wx/wy are int tile coords; also handles float by flooring (for free movement)
        import math as _math
        wx_i = int(_math.floor(wx))
        wy_i = int(_math.floor(wy))
        cs = _tg.CHUNK_SIZE
        cx, cy = wx_i // cs, wy_i // cs
        rx, ry = wx_i % cs, wy_i % cs
        chunk = self.get_chunk(cx, cy)
        return chunk.tiles.get((rx, ry))

    def get_chunk(self, cx, cy):
        if (cx, cy) not in self.loaded_chunks:
            self.loaded_chunks[(cx, cy)] = Chunk(cx, cy)
        return self.loaded_chunks[(cx, cy)]

    def update_loaded_chunks(self, player_wx, player_wy):
        """Loads chunks in advance and saves/unloads distant ones."""
        import math as _math
        cs = _tg.CHUNK_SIZE
        p_cx = int(_math.floor(player_wx)) // cs
        p_cy = int(_math.floor(player_wy)) // cs

        # 1. Load/Generate required buffer chunks
        for cy in range(p_cy - LOAD_RADIUS_CHUNKS, p_cy + LOAD_RADIUS_CHUNKS + 1):
            for cx in range(p_cx - LOAD_RADIUS_CHUNKS, p_cx + LOAD_RADIUS_CHUNKS + 1):
                if (cx, cy) not in self.loaded_chunks:
                    self.loaded_chunks[(cx, cy)] = Chunk(cx, cy)

        # 2. Unload & Save chunks far out of range
        to_unload = []
        for (cx, cy), chunk in self.loaded_chunks.items():
            if abs(cx - p_cx) > LOAD_RADIUS_CHUNKS + 1 or abs(cy - p_cy) > LOAD_RADIUS_CHUNKS + 1:
                chunk.save_to_xml()
                to_unload.append((cx, cy))

        for key in to_unload:
            del self.loaded_chunks[key]

    def save_all(self):
        for chunk in self.loaded_chunks.values():
            chunk.save_to_xml()

# --- PLAYER SYSTEM (separate module, multiplayer-ready) ---
# Player is now free-moving (float) with smooth velocity; see player.py
# Import with fallback for all run modes (module / script inside Ascii1)
try:
    from .player import Player, PlayerController  # type: ignore
except ImportError:
    try:
        from core.renderer.Ascii1.player import Player, PlayerController  # type: ignore
    except ImportError:
        from player import Player, PlayerController  # type: ignore  # direct script in Ascii1/

# --- ENGINE ---
def _rebuild_render_assets(mode, tile_size, zoom, font, sprites, debug):
    """Rebuild font/sprites after zoom/mode change. Returns (font, sprites, tile_w, tile_h, caption_mode)."""
    if mode == 1:
        eff_font_size = max(8, int(FONT_SIZE * zoom))
        font = pygame.font.SysFont("Courier", eff_font_size, bold=True)
        tile_w, tile_h = font.size("@")
        sprites = {}
        caption_mode = "ASCII"
        missing = []
    else:
        font = None
        eff_tile = max(8, int(tile_size * zoom))
        sprites, missing = load_sprites(eff_tile)
        tile_w = tile_h = eff_tile
        caption_mode = "Sprites"
        if debug and missing:
            print("[ascii] Missing sprites after rebuild:")
            for m in missing:
                print("  -", m)
    return font, sprites, tile_w, tile_h, caption_mode, missing


def main():
    pygame.init()
    # Load renderer config (mode 1 ASCII, 2 Sprites, zoom + minimap/fog/hud)
    cfg = load_renderer_config()
    mode = cfg["renderer_mode"]
    tile_size = cfg["tile_size"]
    zoom = cfg.get("zoom", 1.0)
    debug = cfg.get("debug", True)

    # Prepare display and font / sprites depending on mode
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    caption_mode = "ASCII" if mode == 1 else "Sprites"
    pygame.display.set_caption(f"Infinite ASCII Explorer ({caption_mode} x{zoom:.2f})")
    clock = pygame.time.Clock()

    font = None
    tile_w = tile_h = tile_size
    sprites = {}
    missing_report: list = []
    if mode == 1:
        eff_font_size = max(8, int(FONT_SIZE * zoom))
        font = pygame.font.SysFont("Courier", eff_font_size, bold=True)
        tile_w, tile_h = font.size("@")
    else:
        eff_tile = max(8, int(tile_size * zoom))
        sprites, missing_report = load_sprites(eff_tile)
        tile_w = tile_h = eff_tile
        if debug:
            print(f"[ascii] Renderer mode 2 (Sprites) tile_size={tile_size} zoom={zoom:.2f} eff={eff_tile}")
            print(f"[ascii] Loaded sprites for biomes: {list(sprites.keys())}")
            if missing_report:
                print("[ascii] Missing sprites (left blank):")
                for m in missing_report:
                    print("  -", m)
                print("[ascii] Suggestion: add these PNGs under assets/tiles/nature/ to fill blanks")
            else:
                print("[ascii] All sprites present")

    viewport_cols = SCREEN_WIDTH // tile_w
    viewport_rows = (SCREEN_HEIGHT - 30) // tile_h

    # Minimap + fog (config-driven, detail A = 2px/tile)
    minimap = None
    if Minimap is not None:
        try:
            minimap = Minimap(cfg)
            # Ensure save dir matches current SAVE_DIR
            try:
                minimap.set_save_dir(_tg.SAVE_DIR)
            except Exception:
                pass
            if debug:
                print(f"[ascii] Minimap {'ON' if minimap.enabled else 'OFF'} size={minimap.size} tile_px={minimap.tile_px} fog={'ON' if minimap.fog_enabled else 'OFF'} radius={minimap.fog_radius} persist={minimap.fog_persist} dim={minimap.fog_dim_factor}")
                if minimap.discovered:
                    print(f"[ascii] Fog discovered chunks loaded: {len(minimap.discovered)}")
        except Exception as e:
            print(f"[ascii] Minimap init failed: {e}")
            minimap = None

    hud_enabled = draw_hud is not None
    show_debug = False

    world = World()
    player = Player(player_id="local", x=0.5, y=0.5)
    loaded = player.load_player_xml()
    if loaded:
        import math as _math
        if float(player.x).is_integer() and float(player.y).is_integer():
            player.x = float(player.x) + 0.5
            player.y = float(player.y) + 0.5
    controller = PlayerController(player)

    # Initial discovery
    if minimap is not None:
        try:
            minimap.update_discovery(player.x, player.y, _tg.CHUNK_SIZE)
        except Exception:
            pass

    running = True
    while running:
        dt = clock.tick(30) / 1000.0
        # --- INPUT (events) ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_F3:
                    show_debug = not show_debug
                    print(f"[ascii] Debug {'ON' if show_debug else 'OFF'}")
                elif event.key == pygame.K_m:
                    if minimap is not None:
                        minimap.enabled = not minimap.enabled
                        print(f"[ascii] Minimap {'ON' if minimap.enabled else 'OFF'} (M)")
                elif event.key == pygame.K_f:
                    if minimap is not None:
                        minimap.fog_enabled = not minimap.fog_enabled
                        print(f"[ascii] Fog {'ON' if minimap.fog_enabled else 'OFF'} (F) radius={minimap.fog_radius}")
                elif event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                    new_zoom = min(4.0, round(zoom + 0.25, 2))
                    if new_zoom != zoom:
                        zoom = new_zoom
                        font, sprites, tile_w, tile_h, caption_mode, missing_report = _rebuild_render_assets(mode, tile_size, zoom, font, sprites, debug)
                        pygame.display.set_caption(f"Infinite ASCII Explorer ({caption_mode} x{zoom:.2f})")
                        viewport_cols = SCREEN_WIDTH // tile_w
                        viewport_rows = (SCREEN_HEIGHT - 30) // tile_h
                        print(f"[ascii] Zoom -> {zoom:.2f}")
                elif event.key in (pygame.K_MINUS, pygame.K_UNDERSCORE, pygame.K_KP_MINUS):
                    new_zoom = max(0.25, round(zoom - 0.25, 2))
                    if new_zoom != zoom:
                        zoom = new_zoom
                        font, sprites, tile_w, tile_h, caption_mode, missing_report = _rebuild_render_assets(mode, tile_size, zoom, font, sprites, debug)
                        pygame.display.set_caption(f"Infinite ASCII Explorer ({caption_mode} x{zoom:.2f})")
                        viewport_cols = SCREEN_WIDTH // tile_w
                        viewport_rows = (SCREEN_HEIGHT - 30) // tile_h
                        print(f"[ascii] Zoom -> {zoom:.2f}")
                elif event.key == pygame.K_r:
                    reload_generation_config()
                    _sync_from_tg()
                    old_mode = mode
                    old_zoom = zoom
                    cfg = load_renderer_config()
                    mode = cfg["renderer_mode"]
                    tile_size = cfg["tile_size"]
                    zoom = cfg.get("zoom", 1.0)
                    debug = cfg.get("debug", True)
                    print(f"[ascii] Reloaded generation.xml — {len(_tg.get_biomes())} biomes active. Config mode={mode} zoom={zoom:.2f}")
                    # Reapply minimap/hud config live
                    if minimap is not None:
                        try:
                            minimap.apply_config(cfg)
                            print(f"[ascii] Minimap config reloaded: enabled={minimap.enabled} fog={minimap.fog_enabled} radius={minimap.fog_radius} persist={minimap.fog_persist}")
                        except Exception as e:
                            print(f"[ascii] Minimap apply_config failed: {e}")
                    eff_tile_check = max(8, int(tile_size * zoom)) if mode == 2 else max(8, int(FONT_SIZE * zoom))
                    cur_eff = tile_w
                    if mode != old_mode or zoom != old_zoom or eff_tile_check != cur_eff:
                        font, sprites, tile_w, tile_h, caption_mode, missing_report = _rebuild_render_assets(mode, tile_size, zoom, font, sprites, debug)
                        pygame.display.set_caption(f"Infinite ASCII Explorer ({caption_mode} x{zoom:.2f})")
                        viewport_cols = SCREEN_WIDTH // tile_w
                        viewport_rows = (SCREEN_HEIGHT - 30) // tile_h

        # --- FREE MOVEMENT (smooth, not grid-locked) ---
        import pygame as _pygame
        keys = _pygame.key.get_pressed()
        controller.handle_pygame_input(keys)
        player.update(dt, world)

        # --- UPDATE CHUNKS (float position) ---
        world.update_loaded_chunks(player.x, player.y)

        # --- FOG DISCOVERY ---
        if minimap is not None and minimap.fog_enabled:
            try:
                minimap.update_discovery(player.x, player.y, _tg.CHUNK_SIZE)
            except Exception:
                pass

        # --- CAMERA PLACEMENT (float, smooth) ---
        cam_x = player.x - viewport_cols / 2
        cam_y = player.y - viewport_rows / 2

        # --- RENDER (sub-pixel smooth) ---
        screen.fill(COLOR_BG)
        import math as _math
        cam_floor_x = _math.floor(cam_x)
        cam_floor_y = _math.floor(cam_y)
        cam_frac_x = cam_x - cam_floor_x
        cam_frac_y = cam_y - cam_floor_y

        if mode == 1:
            for r in range(viewport_rows + 1):
                wy = cam_floor_y + r
                for c in range(viewport_cols + 1):
                    wx = cam_floor_x + c
                    tile = world.get_tile(wx, wy)
                    if tile:
                        screen_x = (c - cam_frac_x) * tile_w
                        screen_y = (r - cam_frac_y) * tile_h
                        if -tile_w < screen_x < SCREEN_WIDTH and -tile_h < screen_y < SCREEN_HEIGHT:
                            char_surf = font.render(tile.char, True, tile.color)
                            screen.blit(char_surf, (screen_x, screen_y))
            p_screen_x = (player.x - cam_x) * tile_w - tile_w / 2
            p_screen_y = (player.y - cam_y) * tile_h - tile_h / 2
            p_surf = font.render(GLYPHS['player'], True, COLOR_PLAYER)
            screen.blit(p_surf, (p_screen_x, p_screen_y))
        else:
            for r in range(viewport_rows + 1):
                wy = cam_floor_y + r
                for c in range(viewport_cols + 1):
                    wx = cam_floor_x + c
                    tile = world.get_tile(wx, wy)
                    if tile:
                        biome = getattr(tile, "biome", "")
                        if not biome:
                            for bid, col in _tg.COLORS.items():
                                if col == tile.color:
                                    biome = bid
                                    break
                        surf = _pick_variant_sprite(biome, wx, wy)
                        if surf:
                            screen_x = (c - cam_frac_x) * tile_w
                            screen_y = (r - cam_frac_y) * tile_h
                            if -tile_w < screen_x < SCREEN_WIDTH and -tile_h < screen_y < SCREEN_HEIGHT:
                                screen.blit(surf, (screen_x, screen_y))
            p_screen_x = (player.x - cam_x) * tile_w - tile_w / 2
            p_screen_y = (player.y - cam_y) * tile_h - tile_h / 2
            p_surf = sprites.get("player")
            if p_surf:
                screen.blit(p_surf, (p_screen_x, p_screen_y))

        # --- MINIMAP (detail A) ---
        if minimap is not None and minimap.enabled:
            try:
                minimap.draw(screen, world, player, viewport_cols, viewport_rows, cam_x, cam_y, _tg.CHUNK_SIZE, SCREEN_WIDTH, SCREEN_HEIGHT)
            except Exception as e:
                if debug:
                    print(f"[minimap] draw failed: {e}")

        # --- HUD (replaces old single-line status bar) ---
        if hud_enabled and draw_hud is not None:
            try:
                # minimap fog flags for HUD
                mm_on = minimap.enabled if minimap is not None else False
                fog_on = minimap.fog_enabled if minimap is not None else False
                draw_hud(screen, player, world, clock, tile_w, tile_h, viewport_cols, viewport_rows, font, mode, zoom, cfg, mm_on, fog_on, show_debug, dt, _tg.CHUNK_SIZE)
            except Exception as e:
                if debug:
                    print(f"[hud] draw failed: {e}")
                # Fallback old status bar
                if font is None:
                    status_font = pygame.font.SysFont("Courier", FONT_SIZE, bold=True)
                else:
                    status_font = font
                cs = _tg.CHUNK_SIZE
                import math as _math2
                p_chunk_x = int(_math2.floor(player.x)) // cs
                p_chunk_y = int(_math2.floor(player.y)) // cs
                mode_name = "ASCII" if mode == 1 else "SPRITES"
                status = f" World Pos: ({player.x:.2f}, {player.y:.2f}) | Chunk: ({p_chunk_x}, {p_chunk_y}) | Loaded: {len(world.loaded_chunks)} | Mode:{mode_name} R=Reload Esc=Save"
                status_surf = status_font.render(status, True, COLOR_TEXT)
                screen.blit(status_surf, (10, SCREEN_HEIGHT - 25))
        else:
            # Legacy status bar
            if font is None:
                status_font = pygame.font.SysFont("Courier", FONT_SIZE, bold=True)
            else:
                status_font = font
            cs = _tg.CHUNK_SIZE
            import math as _math2
            p_chunk_x = int(_math2.floor(player.x)) // cs
            p_chunk_y = int(_math2.floor(player.y)) // cs
            mode_name = "ASCII" if mode == 1 else "SPRITES"
            status = f" World Pos: ({player.x:.2f}, {player.y:.2f}) | Chunk: ({p_chunk_x}, {p_chunk_y}) | Loaded: {len(world.loaded_chunks)} | Mode:{mode_name} R=Reload Esc=Save"
            status_surf = status_font.render(status, True, COLOR_TEXT)
            screen.blit(status_surf, (10, SCREEN_HEIGHT - 25))

        pygame.display.flip()

    # Clean Exit & Save
    print("Saving world XMLs...")
    world.save_all()
    player.save_player_xml()
    if minimap is not None:
        try:
            minimap.save(_tg.SAVE_DIR)
            print(f"[minimap] Fog discovered: {len(minimap.discovered)} chunks saved")
        except Exception as e:
            print(f"[minimap] save failed: {e}")
    print("Save Complete!")
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
