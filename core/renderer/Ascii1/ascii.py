import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
import zlib
import pygame

# Minimap + HUD + Fog — optional, graceful fallback if modules missing (tests / headless)
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
    from .fog import PlayerFog
except ImportError:
    try:
        from core.renderer.Ascii1.fog import PlayerFog
    except ImportError:
        try:
            from fog import PlayerFog
        except ImportError:
            PlayerFog = None  # type: ignore

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

# Multiplayer + Menu — optional (LAN)
try:
    from .multiplayer import Discovery, HostSession, ClientSession, get_local_ip
except ImportError:
    try:
        from core.renderer.Ascii1.multiplayer import Discovery, HostSession, ClientSession, get_local_ip
    except ImportError:
        try:
            from multiplayer import Discovery, HostSession, ClientSession, get_local_ip
        except ImportError:
            Discovery = HostSession = ClientSession = get_local_ip = None  # type: ignore

try:
    from .menu import MTTMenu
except ImportError:
    try:
        from core.renderer.Ascii1.menu import MTTMenu
    except ImportError:
        try:
            from menu import MTTMenu
        except ImportError:
            MTTMenu = None  # type: ignore

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
    # fog-of-war (player-centered, tile radius, memory dim)
    "fog_enabled": True,
    "fog_radius": 8,
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

        # --- fog (player-centered, tile radius 8) ---
        fog_enabled = _parse_bool(_nested("fog", "enabled", "true"), True)
        try:
            fog_radius = int(_nested("fog", "radius", "8") or "8")
        except Exception:
            fog_radius = 8
        fog_radius = max(0, min(32, fog_radius))
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
PLAYER_SKINS = {}  # player skin name -> Surface (e.g. player1, player2_red, player3_blue, player_old)

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
    global SPRITES, MISSING_SPRITES, SPRITE_VARIANTS, PLAYER_SKINS
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

    # ---- Player skins for multiplayer (player1, player2_red, player3_blue, playerold) ----
    PLAYER_SKINS.clear()
    skin_files = {
        "player1": base / "player1.png",
        "player2_red": base / "player2_red.png",
        "player3_blue": base / "player3_blue.png",
        "player_old": base / "playerold.png",
    }
    for skin_name, path in skin_files.items():
        if path.is_file():
            try:
                PLAYER_SKINS[skin_name] = _load_img(path, tile_size)
            except Exception as e:
                missing.append(f"player_skin {skin_name}: {path.name} (load failed: {e})")
        else:
            # only report if not the optional old/red/blue skins
            if skin_name == "player1":
                missing.append(f"player_skin {skin_name}: {path.name} (missing) -> {path}")
    # ensure fallback: if we have any skin, make sure 'player' key exists in sprites (already)
    if "player" not in sprites and PLAYER_SKINS:
        # use first available
        sprites["player"] = next(iter(PLAYER_SKINS.values()))

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
    # Use stable crc32 for biome (hash() is randomized per process → inconsistent across LAN)
    try:
        biome_h = zlib.crc32(str(biome).encode("utf-8")) & 0xFFFF
    except Exception:
        biome_h = 0
    h = (int(wx) * 73856093) ^ (int(wy) * 19349663) ^ (seed * 83492791) ^ biome_h
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

def _get_player_sprite(pid: str, registry=None):
    """Deterministic skin per player_id. Uses sorted registry for distinct sequential assignment."""
    if PLAYER_SKINS:
        order = ["player1", "player2_red", "player3_blue", "player_old"]
        available = [k for k in order if k in PLAYER_SKINS]
        if not available:
            available = list(PLAYER_SKINS.keys())
        # Prefer sequential based on sorted pids (consistent across peers, distinct for first N)
        if registry is not None:
            try:
                sorted_pids = sorted(registry.players.keys())
                if pid in sorted_pids:
                    idx = sorted_pids.index(pid) % len(available)
                    return PLAYER_SKINS[available[idx]]
            except Exception:
                pass
        # Fallback stable crc32 (hash() is randomized per process)
        try:
            h = zlib.crc32(str(pid).encode("utf-8")) & 0xFFFFFFFF
            idx = h % len(available)
            return PLAYER_SKINS[available[idx]]
        except Exception:
            return PLAYER_SKINS[available[0]]
    return SPRITES.get("player")

# nametag font cache (tile_h -> font) to avoid per-frame SysFont creation
_NAMETAG_FONTS = {}

def _get_nametag_font(tile_h: int):
    key = max(10, tile_h // 2)
    f = _NAMETAG_FONTS.get(key)
    if f is None:
        try:
            f = pygame.font.SysFont("Courier", key, bold=True)
            _NAMETAG_FONTS[key] = f
        except Exception:
            try:
                f = pygame.font.Font(None, key)
                _NAMETAG_FONTS[key] = f
            except Exception:
                return None
    return f

def _draw_nametag(screen, x: float, y: float, name: str, tile_h: int):
    """Draw name tag just above player position (x,y = screen top-left of sprite). Centered."""
    if not name or not screen:
        return
    try:
        font = _get_nametag_font(tile_h)
        if font is None:
            return
        # truncate
        name = str(name)[:16]
        surf = font.render(name, True, (255, 255, 255))
        # background pill
        pad_x, pad_y = 4, 2
        bg_w = surf.get_width() + pad_x * 2
        bg_h = surf.get_height() + pad_y * 2
        bg_x = int(x + tile_h // 2 - bg_w // 2)  # center over sprite (assume square tile)
        bg_y = int(y - bg_h - 2)
        # clamp to screen
        bg = pygame.Surface((bg_w, bg_h), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 160))
        screen.blit(bg, (bg_x, bg_y))
        pygame.draw.rect(screen, (80, 80, 100), (bg_x, bg_y, bg_w, bg_h), 1)
        screen.blit(surf, (bg_x + pad_x, bg_y + pad_y))
    except Exception:
        pass

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
    def __init__(self, save_enabled: bool = True):
        self.loaded_chunks = {}  # (cx, cy) -> Chunk
        self.save_enabled = save_enabled  # false for clients (host-authoritative)

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
        """Loads chunks in advance and saves/unloads distant ones (single focus)."""
        self.update_loaded_chunks_multi([(player_wx, player_wy)])

    def update_loaded_chunks_multi(self, points):
        """
        Load/unload for multiple focus points (e.g. all MP players).
        Loads union of buffers, unloads only chunks far from ALL points.
        Avoids thrashing when players are far apart (was calling update per-player).
        """
        import math as _math
        cs = _tg.CHUNK_SIZE
        if not points:
            return
        # 1. Compute chunk centers for each point
        centers = []
        required = set()
        for (px, py) in points:
            p_cx = int(_math.floor(px)) // cs
            p_cy = int(_math.floor(py)) // cs
            centers.append((p_cx, p_cy))
            for dy in range(-LOAD_RADIUS_CHUNKS, LOAD_RADIUS_CHUNKS + 1):
                for dx in range(-LOAD_RADIUS_CHUNKS, LOAD_RADIUS_CHUNKS + 1):
                    required.add((p_cx + dx, p_cy + dy))
        # 1b. Load union
        for (cx, cy) in required:
            if (cx, cy) not in self.loaded_chunks:
                self.loaded_chunks[(cx, cy)] = Chunk(cx, cy)

        # 2. Unload only if far from ALL centers (host only saves)
        limit = LOAD_RADIUS_CHUNKS + 1
        to_unload = []
        for (cx, cy), chunk in list(self.loaded_chunks.items()):
            far_from_all = True
            for (p_cx, p_cy) in centers:
                if abs(cx - p_cx) <= limit and abs(cy - p_cy) <= limit:
                    far_from_all = False
                    break
            if far_from_all:
                if self.save_enabled:
                    try:
                        chunk.save_to_xml()
                    except Exception:
                        pass
                to_unload.append((cx, cy))
        for key in to_unload:
            self.loaded_chunks.pop(key, None)

    def save_all(self):
        if not self.save_enabled:
            return
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

    # Minimap (detail A = 2px/tile) — no fog
    minimap = None
    if Minimap is not None:
        try:
            minimap = Minimap(cfg)
            try:
                minimap.set_save_dir(_tg.SAVE_DIR)
            except Exception:
                pass
            if debug:
                print(f"[ascii] Minimap {'ON' if minimap.enabled else 'OFF'} size={minimap.size} tile_px={minimap.tile_px}")
        except Exception as e:
            print(f"[ascii] Minimap init failed: {e}")
            minimap = None

    # Player fog (tile-based memory, radius 8, dimmed outside)
    player_fog = None
    if PlayerFog is not None:
        try:
            player_fog = PlayerFog(cfg)
            try:
                player_fog.set_save_dir(_tg.SAVE_DIR)
            except Exception:
                pass
            if debug:
                print(f"[ascii] PlayerFog {'ON' if player_fog.enabled else 'OFF'} radius={player_fog.radius} dim={player_fog.dim_factor} persist={player_fog.fog_persist}")
                if player_fog.memory:
                    print(f"[ascii] Fog memory loaded: {len(player_fog.memory)} tiles")
        except Exception as e:
            print(f"[ascii] PlayerFog init failed: {e}")
            player_fog = None

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
    # Load persistent MP display name (host-authoritative saves handle world, but name is personal per install)
    try:
        import pathlib
        npath = pathlib.Path(_tg.SAVE_DIR) / "player_name.txt"
        if npath.is_file():
            txt = npath.read_text(encoding='utf-8').strip()[:16]
            if txt:
                player.name = txt
    except Exception:
        pass
    controller = PlayerController(player)

    # --- Multiplayer + Pause Menu (Tab) ---
    # PlayerRegistry for remote players
    try:
        from .player import PlayerRegistry as _PlayerRegistry
    except ImportError:
        try:
            from core.renderer.Ascii1.player import PlayerRegistry as _PlayerRegistry
        except ImportError:
            from player import PlayerRegistry as _PlayerRegistry  # type: ignore
    mp_registry = _PlayerRegistry()
    mp_registry.players[player.player_id] = player

    discovery = None
    host_session = None
    client_session = None
    menu = None
    if Discovery is not None:
        try:
            discovery = Discovery()
            discovery.start()
            print(f"[mp] Discovery listening on UDP {discovery.listen_port}")
        except Exception as e:
            print(f"[mp] Discovery start failed: {e}")
            discovery = None
    if MTTMenu is not None:
        try:
            menu = MTTMenu(SCREEN_WIDTH, SCREEN_HEIGHT)
            if discovery:
                menu.set_discovery(discovery)
            # sync player name to menu
            try:
                menu.player_name = str(getattr(player, 'name', 'Player'))[:16]
            except Exception:
                pass
            print("[mp] Menu (TAB) ready — Save / Multiplayer / Quit")
        except Exception as e:
            print(f"[mp] Menu init failed: {e}")
            menu = None

    def _is_host():
        return host_session is not None and getattr(host_session, "is_running", lambda: False)()

    def _is_client():
        return client_session is not None and getattr(client_session, "is_connected", lambda: False)()

    def _is_multiplayer():
        return _is_host() or _is_client()

    running = True
    while running:
        dt = clock.tick(30) / 1000.0
        # --- INPUT (events) ---
        # Handle menu first (it may consume events)
        for event in pygame.event.get():
            # let menu handle Tab/ESC/mouse when open
            if menu is not None and menu.handle_event(event):
                continue
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_TAB:
                    if menu is not None:
                        menu.toggle()
                        if menu:
                            menu.set_sessions(host_session, client_session)
                    continue
                if menu is not None and menu.is_open:
                    # menu open: ignore other keys (except Tab handled)
                    continue
                if event.key == pygame.K_ESCAPE:
                    # If in MP client, ESC shouldn't quit? Keep quit for now but allow menu to handle
                    running = False
                elif event.key == pygame.K_F3:
                    show_debug = not show_debug
                    print(f"[ascii] Debug {'ON' if show_debug else 'OFF'}")
                elif event.key == pygame.K_m:
                    if minimap is not None:
                        minimap.enabled = not minimap.enabled
                        print(f"[ascii] Minimap {'ON' if minimap.enabled else 'OFF'} (M)")
                elif event.key == pygame.K_f:
                    # Fog toggle only when debug enabled per spec
                    if not cfg.get("debug", False):
                        if debug:
                            print("[ascii] Fog toggle blocked — debug is off (enable <debug>true</debug> in config.xml)")
                    else:
                        if player_fog is not None:
                            player_fog.toggle()
                            print(f"[ascii] Fog {'ON' if player_fog.enabled else 'OFF'} (F) radius={player_fog.radius}")
                        elif debug:
                            print("[ascii] PlayerFog unavailable")
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
                    # Reapply minimap + fog config live
                    if minimap is not None:
                        try:
                            minimap.apply_config(cfg)
                            print(f"[ascii] Minimap config reloaded: enabled={minimap.enabled}")
                        except Exception as e:
                            print(f"[ascii] Minimap apply_config failed: {e}")
                    if player_fog is not None:
                        try:
                            player_fog.apply_config(cfg)
                            print(f"[ascii] PlayerFog config reloaded: enabled={player_fog.enabled} radius={player_fog.radius} dim={player_fog.dim_factor}")
                        except Exception as e:
                            print(f"[ascii] PlayerFog apply_config failed: {e}")
                    eff_tile_check = max(8, int(tile_size * zoom)) if mode == 2 else max(8, int(FONT_SIZE * zoom))
                    cur_eff = tile_w
                    if mode != old_mode or zoom != old_zoom or eff_tile_check != cur_eff:
                        font, sprites, tile_w, tile_h, caption_mode, missing_report = _rebuild_render_assets(mode, tile_size, zoom, font, sprites, debug)
                        pygame.display.set_caption(f"Infinite ASCII Explorer ({caption_mode} x{zoom:.2f})")
                        viewport_cols = SCREEN_WIDTH // tile_w
                        viewport_rows = (SCREEN_HEIGHT - 30) // tile_h

        # --- MENU ACTIONS (consume pending from PauseMenu) ---
        if menu is not None:
            # ensure menu knows current sessions for display
            try:
                menu.set_sessions(host_session, client_session)
            except Exception:
                pass
            act = menu.consume_action()
            if act:
                if act == "save":
                    if _is_client():
                        print("[mp] Save blocked — clients don't save (host only)")
                    else:
                        print("[menu] Saving…")
                        world.save_all()
                        player.save_player_xml()
                        if player_fog is not None:
                            try:
                                player_fog.save(_tg.SAVE_DIR)
                            except Exception:
                                pass
                        print("[menu] Save complete")
                elif act == "quit":
                    running = False
                elif act == "host":
                    # toggle host
                    if _is_host():
                        try:
                            host_session.stop()
                        except Exception:
                            pass
                        host_session = None
                        # remove remote players from registry keep only local
                        try:
                            keep = {player.player_id: player}
                            mp_registry.players = keep
                        except Exception:
                            pass
                        print("[mp] Stopped hosting")
                    elif _is_client():
                        print("[mp] Disconnect client before hosting")
                    else:
                        try:
                            if HostSession is None:
                                raise ImportError("HostSession not available")
                            host_session = HostSession(world, player, host_name=getattr(player, 'name', 'Host'))
                            host_session.start()
                            # registry already has host
                            lip = get_local_ip() if get_local_ip else "?"
                            print(f"[mp] Hosting on {lip}:{host_session.tcp_port} as {getattr(player, 'name', player.player_id)}")
                        except Exception as e:
                            print(f"[mp] Host start failed: {e}")
                            host_session = None
                    if menu:
                        menu.set_sessions(host_session, client_session)
                elif act.startswith("join:"):
                    # act is join:ip:port
                    try:
                        _, jip, jport_s = act.split(":")
                        jport = int(jport_s)
                    except Exception:
                        jip, jport = None, None
                    if jip:
                        if _is_host():
                            print("[mp] Stop host before joining as client")
                        elif _is_client():
                            try:
                                client_session.disconnect()
                            except Exception:
                                pass
                            client_session = None
                        try:
                            if ClientSession is None:
                                raise ImportError("ClientSession not available")
                            cs = ClientSession(jip, jport, player, player_name=getattr(player, 'name', 'Player'))
                            ok = cs.connect(timeout=4.0)
                            if ok:
                                client_session = cs
                                # reset registry to local + will be filled via state
                                try:
                                    mp_registry.players = {player.player_id: player}
                                except Exception:
                                    pass
                                print(f"[mp] Joined {jip}:{jport} as {cs.my_id}")
                            else:
                                print(f"[mp] Join failed {jip}:{jport}")
                                client_session = None
                        except Exception as e:
                            print(f"[mp] Join error: {e}")
                            client_session = None
                        if menu:
                            menu.set_sessions(host_session, client_session)

            # Sync MP display name from menu to player (editable in multiplayer menu)
            if menu is not None:
                try:
                    mname = str(getattr(menu, 'player_name', '') or '').strip()[:16]
                    if mname and mname != getattr(player, 'name', ''):
                        player.name = mname
                        if player.player_id in mp_registry.players:
                            mp_registry.players[player.player_id].name = mname
                        # keep host beacon name in sync
                        if host_session is not None:
                            try:
                                host_session.host_name = mname
                                host_session.beacon.host_name = mname
                            except Exception:
                                pass
                        # persist locally (personal, not world-save)
                        try:
                            import pathlib
                            npath = pathlib.Path(_tg.SAVE_DIR) / "player_name.txt"
                            npath.parent.mkdir(parents=True, exist_ok=True)
                            npath.write_text(mname, encoding='utf-8')
                        except Exception:
                            pass
                except Exception:
                    pass

        # --- FREE MOVEMENT + MULTIPLAYER TICK ---
        import pygame as _pygame
        # If menu open, pause movement
        is_paused = menu is not None and menu.is_open
        if not is_paused:
            keys = _pygame.key.get_pressed()
            inp = controller.handle_pygame_input(keys)  # returns dx,dy
            # Client: send input to server
            if _is_client() and client_session is not None:
                try:
                    client_session.send_input(float(inp.get("dx", 0)), float(inp.get("dy", 0)))
                except Exception:
                    pass
            # Singleplayer or Host: update local player directly
            if not _is_client():
                player.update(dt, world)
        else:
            # when paused, stop movement
            player.stop()

        # Host authoritative: apply remote inputs + update remote players + broadcast
        if _is_host() and host_session is not None:
            try:
                inputs = host_session.consume_inputs()
                for pid, info in inputs.items():
                    p = info.get("player_obj")
                    if p is None:
                        continue
                    # register if not in registry
                    if pid not in mp_registry.players:
                        mp_registry.players[pid] = p
                    # apply input
                    try:
                        p.set_input(float(info.get("dx", 0)), float(info.get("dy", 0)))
                    except Exception:
                        pass
                    # simulate remote players
                    if not is_paused:
                        p.update(dt, world)
                # Now build authoritative state snapshot for all players (include name for nametag)
                all_state = {}
                for pid, p in mp_registry.players.items():
                    try:
                        all_state[pid] = {"x": float(p.x), "y": float(p.y), "vx": float(p.vx), "vy": float(p.vy), "name": str(getattr(p, 'name', pid))}
                    except Exception:
                        pass
                host_session.broadcast_state(all_state)
            except Exception as e:
                if debug:
                    print(f"[mp] host tick error: {e}")
        elif _is_client() and client_session is not None:
            # Client: poll authoritative state
            try:
                st = client_session.poll_state()
                if st and "players" in st:
                    # apply to registry
                    for pid, pdata in st["players"].items():
                        if pid == player.player_id:
                            # authoritative correction for local (interpolate lightly)
                            try:
                                player.x = float(pdata.get("x", player.x))
                                player.y = float(pdata.get("y", player.y))
                                player.vx = float(pdata.get("vx", player.vx))
                                player.vy = float(pdata.get("vy", player.vy))
                            except Exception:
                                pass
                        else:
                            # remote (including host)
                            if pid not in mp_registry.players:
                                try:
                                    from player import Player as _P
                                except Exception:
                                    try:
                                        from core.renderer.Ascii1.player import Player as _P
                                    except Exception:
                                        _P = None
                                if _P:
                                    np = _P(player_id=pid, x=float(pdata.get("x", 0)), y=float(pdata.get("y", 0)))
                                    mp_registry.players[pid] = np
                            if pid in mp_registry.players:
                                try:
                                    mp_registry.players[pid].apply_network_state(pdata)
                                except Exception:
                                    pass
                    # remove disconnected players
                    state_ids = set(st["players"].keys())
                    for pid in list(mp_registry.players.keys()):
                        if pid not in state_ids and pid != player.player_id:
                            # keep for now? Remove if not in state for a while - simple immediate
                            pass
                # Detect disconnect
                if not client_session.is_connected():
                    print("[mp] Disconnected from host")
                    client_session = None
                    if menu:
                        menu.set_sessions(host_session, client_session)
                    # keep only local in registry
                    try:
                        mp_registry.players = {player.player_id: player}
                    except Exception:
                        pass
            except Exception as e:
                if debug:
                    print(f"[mp] client tick error: {e}")

        # --- UPDATE CHUNKS (float position) ---
        # Clients don't save (host authoritative)
        try:
            world.save_enabled = not _is_client()
        except Exception:
            pass
        # Use multi-point update to avoid thrashing when players far apart
        try:
            pts = [(player.x, player.y)]
            if _is_multiplayer():
                for pid2, rp2 in list(mp_registry.players.items()):
                    if pid2 == player.player_id:
                        continue
                    try:
                        pts.append((float(rp2.x), float(rp2.y)))
                    except Exception:
                        pass
            world.update_loaded_chunks_multi(pts)
        except Exception:
            try:
                world.update_loaded_chunks(player.x, player.y)
            except Exception:
                pass

        # Player fog memory is updated during render via get_display(); no separate discovery step needed.
        # Keep this hook in case PlayerFog needs periodic priming (currently handled lazily).

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

        # Precompute fog overlay for sprites (single surface reused)
        fog_overlay = None
        fog_overlay_alpha = 0
        if player_fog is not None and player_fog.enabled and mode == 2:
            fog_overlay_alpha = int((1.0 - player_fog.dim_factor) * 170)
            fog_overlay_alpha = max(0, min(255, fog_overlay_alpha))
            if fog_overlay_alpha > 0:
                try:
                    fog_overlay = pygame.Surface((tile_w, tile_h), pygame.SRCALPHA)
                    fog_overlay.fill((0, 0, 0, fog_overlay_alpha))
                except Exception:
                    fog_overlay = None

        if mode == 1:
            for r in range(viewport_rows + 1):
                wy = cam_floor_y + r
                for c in range(viewport_cols + 1):
                    wx = cam_floor_x + c
                    tile = world.get_tile(wx, wy)
                    if tile:
                        # Fog: darken + memory
                        if player_fog is not None and player_fog.enabled:
                            disp_char, disp_color, _disp_biome, _is_mem = player_fog.get_display(wx, wy, tile, player.x, player.y)
                        else:
                            disp_char, disp_color = tile.char, tile.color
                        screen_x = (c - cam_frac_x) * tile_w
                        screen_y = (r - cam_frac_y) * tile_h
                        if -tile_w < screen_x < SCREEN_WIDTH and -tile_h < screen_y < SCREEN_HEIGHT:
                            char_surf = font.render(disp_char, True, disp_color)
                            screen.blit(char_surf, (screen_x, screen_y))
            # local player
            p_screen_x = (player.x - cam_x) * tile_w - tile_w / 2
            p_screen_y = (player.y - cam_y) * tile_h - tile_h / 2
            p_surf = font.render(GLYPHS['player'], True, COLOR_PLAYER)
            screen.blit(p_surf, (p_screen_x, p_screen_y))
            if _is_multiplayer():
                try:
                    _draw_nametag(screen, p_screen_x, p_screen_y, getattr(player, 'name', player.player_id), tile_h)
                except Exception:
                    pass
            # remote players (MP)
            if _is_multiplayer():
                try:
                    for pid, rp in list(mp_registry.players.items()):
                        if pid == player.player_id:
                            continue
                        rx = (rp.x - cam_x) * tile_w - tile_w / 2
                        ry = (rp.y - cam_y) * tile_h - tile_h / 2
                        # cull off-screen
                        if -tile_w <= rx <= SCREEN_WIDTH and -tile_h <= ry <= SCREEN_HEIGHT:
                            rsurf = font.render(GLYPHS.get('player','@'), True, (255, 100, 100))
                            screen.blit(rsurf, (rx, ry))
                            try:
                                _draw_nametag(screen, rx, ry, getattr(rp, 'name', pid), tile_h)
                            except Exception:
                                pass
                except Exception:
                    pass
        else:
            for r in range(viewport_rows + 1):
                wy = cam_floor_y + r
                for c in range(viewport_cols + 1):
                    wx = cam_floor_x + c
                    tile = world.get_tile(wx, wy)
                    if tile:
                        disp_biome = getattr(tile, "biome", "")
                        is_mem = False
                        disp_color_for_unseen = None
                        if player_fog is not None and player_fog.enabled:
                            _disp_char, disp_col, _disp_biome_mem, is_mem = player_fog.get_display(wx, wy, tile, player.x, player.y)
                            disp_biome = _disp_biome_mem if _disp_biome_mem else disp_biome
                            # Unseen fog (no memory) is encoded as color (12,12,16) with empty biome and is_mem True
                            if is_mem and _disp_biome_mem == "" and disp_col == (12, 12, 16):
                                # Draw solid fog tile
                                screen_x = (c - cam_frac_x) * tile_w
                                screen_y = (r - cam_frac_y) * tile_h
                                if -tile_w < screen_x < SCREEN_WIDTH and -tile_h < screen_y < SCREEN_HEIGHT:
                                    pygame.draw.rect(screen, (12, 12, 16), (screen_x, screen_y, tile_w, tile_h))
                                continue
                            # For remembered tiles, we want remembered biome sprite
                            if not disp_biome:
                                for bid, col in _tg.COLORS.items():
                                    if col == tile.color:
                                        disp_biome = bid
                                        break
                        else:
                            if not disp_biome:
                                for bid, col in _tg.COLORS.items():
                                    if col == tile.color:
                                        disp_biome = bid
                                        break
                        surf = _pick_variant_sprite(disp_biome, wx, wy) if disp_biome else None
                        # Fallback to live biome if remembered lookup failed
                        if surf is None and disp_biome:
                            surf = SPRITES.get(disp_biome)
                        if surf:
                            screen_x = (c - cam_frac_x) * tile_w
                            screen_y = (r - cam_frac_y) * tile_h
                            if -tile_w < screen_x < SCREEN_WIDTH and -tile_h < screen_y < SCREEN_HEIGHT:
                                screen.blit(surf, (screen_x, screen_y))
                                if is_mem and fog_overlay is not None:
                                    screen.blit(fog_overlay, (screen_x, screen_y))
            p_screen_x = (player.x - cam_x) * tile_w - tile_w / 2
            p_screen_y = (player.y - cam_y) * tile_h - tile_h / 2
            p_surf = _get_player_sprite(player.player_id, mp_registry)
            if p_surf is None:
                p_surf = sprites.get("player")
            if p_surf:
                screen.blit(p_surf, (p_screen_x, p_screen_y))
            if _is_multiplayer():
                try:
                    _draw_nametag(screen, p_screen_x, p_screen_y, getattr(player, 'name', player.player_id), tile_h)
                except Exception:
                    pass
            # remote players sprites
            if _is_multiplayer():
                try:
                    for pid, rp in list(mp_registry.players.items()):
                        if pid == player.player_id:
                            continue
                        rx = (rp.x - cam_x) * tile_w - tile_w / 2
                        ry = (rp.y - cam_y) * tile_h - tile_h / 2
                        if -tile_w <= rx <= SCREEN_WIDTH and -tile_h <= ry <= SCREEN_HEIGHT:
                            rs = _get_player_sprite(pid, mp_registry)
                            if rs is None:
                                rs = sprites.get("player")
                            if rs:
                                screen.blit(rs, (rx, ry))
                            else:
                                pygame.draw.rect(screen, (255,80,80), (rx, ry, tile_w, tile_h))
                            try:
                                _draw_nametag(screen, rx, ry, getattr(rp, 'name', pid), tile_h)
                            except Exception:
                                pass
                except Exception:
                    pass

        # --- MINIMAP (detail A) ---
        if minimap is not None and minimap.enabled:
            try:
                minimap.draw(screen, world, player, viewport_cols, viewport_rows, cam_x, cam_y, _tg.CHUNK_SIZE, SCREEN_WIDTH, SCREEN_HEIGHT)
                # Draw remote players on minimap (small red dots)
                if _is_multiplayer():
                    try:
                        import math as _mmath
                        # reuse minimap panel geometry
                        panel_x, panel_y, panel_w, panel_h = minimap._panel_rect(SCREEN_WIDTH, SCREEN_HEIGHT)
                        inner_x = panel_x + 2
                        inner_y = panel_y + 2
                        inner_w = panel_w - 4
                        inner_h = panel_h - 4
                        center_px = inner_x + inner_w // 2
                        center_py = inner_y + inner_h // 2
                        tpx = minimap.tile_px
                        p_tx = int(_mmath.floor(player.x))
                        p_ty = int(_mmath.floor(player.y))
                        for pid, rp in list(mp_registry.players.items()):
                            if pid == player.player_id:
                                continue
                            dx = int(_mmath.floor(rp.x)) - p_tx
                            dy = int(_mmath.floor(rp.y)) - p_ty
                            dot_x = center_px + dx * tpx - tpx // 2 + tpx // 2
                            dot_y = center_py + dy * tpx - tpx // 2 + tpx // 2
                            # fractional
                            frac_x = rp.x - _mmath.floor(rp.x) - 0.5
                            frac_y = rp.y - _mmath.floor(rp.y) - 0.5
                            dot_x += int(round(frac_x * tpx))
                            dot_y += int(round(frac_y * tpx))
                            if inner_x <= dot_x <= inner_x+inner_w and inner_y <= dot_y <= inner_y+inner_h:
                                pygame.draw.circle(screen, (255,80,80), (dot_x, dot_y), 2)
                    except Exception:
                        pass
            except Exception as e:
                if debug:
                    print(f"[minimap] draw failed: {e}")

        # --- HUD (replaces old single-line status bar) ---
        if hud_enabled and draw_hud is not None:
            try:
                mm_on = minimap.enabled if minimap is not None else False
                fog_on = player_fog.enabled if player_fog is not None else False
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

        # --- MENU OVERLAY ---
        if menu is not None and menu.is_open:
            try:
                # keep screen_w/h in sync if zoom changes
                menu.screen_w, menu.screen_h = screen.get_size()
                menu.draw(screen)
            except Exception as e:
                if debug:
                    print(f"[menu] draw failed: {e}")

        pygame.display.flip()

    # Clean Exit & Save (host only — clients don't save per spec)
    is_client_at_exit = client_session is not None and getattr(client_session, "is_connected", lambda: False)()
    if is_client_at_exit:
        print("[mp] Client exit — not saving (host authoritative)")
    else:
        print("Saving world XMLs...")
        world.save_all()
        player.save_player_xml()
        if player_fog is not None:
            try:
                player_fog.save(_tg.SAVE_DIR)
                print(f"[fog] Memory saved: {len(player_fog.memory)} tiles")
            except Exception as e:
                print(f"[fog] save failed: {e}")
        print("Save Complete!")
    # cleanup MP
    try:
        if host_session:
            host_session.stop()
    except Exception:
        pass
    try:
        if client_session:
            client_session.disconnect()
    except Exception:
        pass
    try:
        if discovery:
            discovery.stop()
    except Exception:
        pass
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
