import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
import pygame

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
_RENDER_CONFIG = {"renderer_mode": 1, "tile_size": 32, "zoom": 1.0, "debug": True}
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

def load_renderer_config(path=None):
    """Load config.xml — sets RENDERER_MODE, TILE_SIZE and ZOOM. Returns dict."""
    global RENDERER_MODE, TILE_SIZE, ZOOM, _RENDER_CONFIG
    xml_path = _find_config_xml(path)
    if xml_path is None:
        if path is not None:
            print(f"[ascii] config.xml not found at '{path}', using ASCII mode 1.")
        _RENDER_CONFIG = {"renderer_mode": 1, "tile_size": 32, "zoom": 1.0, "debug": True}
        RENDERER_MODE = 1
        TILE_SIZE = 32
        ZOOM = 1.0
        return _RENDER_CONFIG
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        mode_el = root.find("renderer_mode")
        size_el = root.find("tile_size")
        zoom_el = root.find("zoom")
        debug_el = root.find("debug")
        mode = int(mode_el.text.strip()) if mode_el is not None and mode_el.text else 1
        if mode not in (1, 2):
            print(f"[ascii] Invalid renderer_mode {mode} in {xml_path}, fallback to 1")
            mode = 1
        tile_size = int(size_el.text.strip()) if size_el is not None and size_el.text else 32
        tile_size = max(8, min(128, tile_size))
        zoom = float(zoom_el.text.strip()) if zoom_el is not None and zoom_el.text else 1.0
        zoom = max(0.25, min(4.0, zoom))
        debug = True
        if debug_el is not None and debug_el.text:
            debug = debug_el.text.strip().lower() in ("true", "1", "yes")
        _RENDER_CONFIG = {"renderer_mode": mode, "tile_size": tile_size, "zoom": zoom, "debug": debug, "path": str(xml_path)}
        RENDERER_MODE = mode
        TILE_SIZE = tile_size
        ZOOM = zoom
        return _RENDER_CONFIG
    except Exception as e:
        print(f"[ascii] Failed parsing {xml_path}: {e} — using ASCII mode 1")
        _RENDER_CONFIG = {"renderer_mode": 1, "tile_size": 32, "zoom": 1.0, "debug": True}
        RENDERER_MODE = 1
        TILE_SIZE = 32
        ZOOM = 1.0
        return _RENDER_CONFIG

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
        "forest": base / "tree1.png",
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
            (base / "tree1.png", 100),
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
def main():
    pygame.init()
    # Load renderer config (mode 1 ASCII, 2 Sprites, zoom)
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
    missing_report = []
    if mode == 1:
        eff_font_size = max(8, int(FONT_SIZE * zoom))
        font = pygame.font.SysFont("Courier", eff_font_size, bold=True)
        tile_w, tile_h = font.size("@")
    else:
        # Sprite mode — load PNGs scaled to effective tile size (tile_size * zoom)
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

    world = World()
    # Spawn at tile center (0.5,0.5) for smooth free movement; handles old int saves via load
    player = Player(player_id="local", x=0.5, y=0.5)
    # Try to load old save — converts int 0,0 -> 0.5,0.5 if needed
    loaded = player.load_player_xml()
    if loaded:
        # Old saves stored int tile origin; if player is exactly on integer, nudge to center for smooth mode
        import math as _math
        if float(player.x).is_integer() and float(player.y).is_integer():
            player.x = float(player.x) + 0.5
            player.y = float(player.y) + 0.5
    controller = PlayerController(player)

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
                elif event.key == pygame.K_r:
                    # Hot-reload both generation.xml and config.xml (including zoom)
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
                    # If mode/tile_size/zoom changed, rebuild font/sprites and viewport
                    eff_tile_check = max(8, int(tile_size * zoom)) if mode == 2 else max(8, int(FONT_SIZE * zoom))
                    cur_eff = tile_w  # tile_w already is effective size
                    if mode != old_mode or zoom != old_zoom or eff_tile_check != cur_eff:
                        if mode == 1:
                            eff_font_size = max(8, int(FONT_SIZE * zoom))
                            font = pygame.font.SysFont("Courier", eff_font_size, bold=True)
                            tile_w, tile_h = font.size("@")
                            sprites = {}
                            caption_mode = "ASCII"
                        else:
                            font = None
                            eff_tile = max(8, int(tile_size * zoom))
                            sprites, missing_report = load_sprites(eff_tile)
                            tile_w = tile_h = eff_tile
                            caption_mode = "Sprites"
                            if debug and missing_report:
                                print("[ascii] Missing sprites after reload:")
                                for m in missing_report:
                                    print("  -", m)
                        pygame.display.set_caption(f"Infinite ASCII Explorer ({caption_mode} x{zoom:.2f})")
                        viewport_cols = SCREEN_WIDTH // tile_w
                        viewport_rows = (SCREEN_HEIGHT - 30) // tile_h
                # Note: discrete KEYDOWN movement removed — free movement uses get_pressed() below

        # --- FREE MOVEMENT (smooth, not grid-locked) ---
        # Uses PlayerController -> Player.set_input -> Player.update(dt, world)
        # Supports WASD/arrows/numpad/vi keys; multiplayer-ready via input dict
        import pygame as _pygame
        keys = _pygame.key.get_pressed()
        # Escape already handled via event, but check held state too
        # Controller returns input dict for potential network send
        controller.handle_pygame_input(keys)
        player.update(dt, world)

        # --- UPDATE CHUNKS (float position) ---
        world.update_loaded_chunks(player.x, player.y)

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
            # ===== ASCII MODE (smooth) =====
            # Draw tile underneath player too — player is overlayed afterwards
            for r in range(viewport_rows + 1):  # +1 for fractional edge
                wy = cam_floor_y + r
                for c in range(viewport_cols + 1):
                    wx = cam_floor_x + c
                    tile = world.get_tile(wx, wy)
                    if tile:
                        screen_x = (c - cam_frac_x) * tile_w
                        screen_y = (r - cam_frac_y) * tile_h
                        # Cull off-screen
                        if -tile_w < screen_x < SCREEN_WIDTH and -tile_h < screen_y < SCREEN_HEIGHT:
                            char_surf = font.render(tile.char, True, tile.color)
                            screen.blit(char_surf, (screen_x, screen_y))
            # Render Player centered (smooth, not grid)
            p_screen_x = (player.x - cam_x) * tile_w - tile_w / 2
            p_screen_y = (player.y - cam_y) * tile_h - tile_h / 2
            p_surf = font.render(GLYPHS['player'], True, COLOR_PLAYER)
            screen.blit(p_surf, (p_screen_x, p_screen_y))
        else:
            # ===== SPRITE MODE (smooth) =====
            # Draw tile underneath player too — player sprite is overlayed afterwards
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
            # Player sprite centered
            p_screen_x = (player.x - cam_x) * tile_w - tile_w / 2
            p_screen_y = (player.y - cam_y) * tile_h - tile_h / 2
            p_surf = sprites.get("player")
            if p_surf:
                screen.blit(p_surf, (p_screen_x, p_screen_y))
            else:
                pass  # leave blank — see missing sprites report

        # Status Bar (always ASCII font)
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
        # dt already via clock.tick at top

    # Clean Exit & Save
    print("Saving world XMLs...")
    world.save_all()
    player.save_player_xml()
    print("Save Complete!")
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
