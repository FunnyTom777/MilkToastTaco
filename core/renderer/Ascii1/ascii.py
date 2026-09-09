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
_RENDER_CONFIG = {"renderer_mode": 1, "tile_size": 32, "debug": True}
RENDERER_MODE = 1
TILE_SIZE = 32
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
    """Load config.xml — sets RENDERER_MODE and TILE_SIZE. Returns dict."""
    global RENDERER_MODE, TILE_SIZE, _RENDER_CONFIG
    xml_path = _find_config_xml(path)
    if xml_path is None:
        if path is not None:
            print(f"[ascii] config.xml not found at '{path}', using ASCII mode 1.")
        _RENDER_CONFIG = {"renderer_mode": 1, "tile_size": 32, "debug": True}
        RENDERER_MODE = 1
        TILE_SIZE = 32
        return _RENDER_CONFIG
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        mode_el = root.find("renderer_mode")
        size_el = root.find("tile_size")
        debug_el = root.find("debug")
        mode = int(mode_el.text.strip()) if mode_el is not None and mode_el.text else 1
        if mode not in (1, 2):
            print(f"[ascii] Invalid renderer_mode {mode} in {xml_path}, fallback to 1")
            mode = 1
        tile_size = int(size_el.text.strip()) if size_el is not None and size_el.text else 32
        tile_size = max(8, min(128, tile_size))
        debug = True
        if debug_el is not None and debug_el.text:
            debug = debug_el.text.strip().lower() in ("true", "1", "yes")
        _RENDER_CONFIG = {"renderer_mode": mode, "tile_size": tile_size, "debug": debug, "path": str(xml_path)}
        RENDERER_MODE = mode
        TILE_SIZE = tile_size
        # print(f"[ascii] Loaded config.xml mode={mode} tile_size={tile_size} from {xml_path}")
        return _RENDER_CONFIG
    except Exception as e:
        print(f"[ascii] Failed parsing {xml_path}: {e} — using ASCII mode 1")
        _RENDER_CONFIG = {"renderer_mode": 1, "tile_size": 32, "debug": True}
        RENDERER_MODE = 1
        TILE_SIZE = 32
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

def load_sprites(tile_size=None):
    """
    Load PNG sprites for each biome. Returns (sprites dict, missing list).
    - Sprites expected under assets/tiles/nature/
    - Missing entries are left blank per spec and reported.
    """
    global SPRITES, MISSING_SPRITES
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
    }
    sprites = {}
    missing = []
    for biome, path in expected.items():
        if path.is_file():
            try:
                img = pygame.image.load(str(path))
                # keep alpha if present
                try:
                    img = img.convert_alpha()
                except Exception:
                    img = img.convert()
                img = pygame.transform.scale(img, (tile_size, tile_size))
                sprites[biome] = img
            except Exception as e:
                missing.append(f"{biome}: {path.name} (load failed: {e})")
        else:
            missing.append(f"{biome}: {path.name} (missing) -> {path}")
    # Also check for extra nice-to-haves that would improve variation
    nice_to_have = [
        ("ground", base / "grass_with_bush1.png", "grass with bush — used as ground scatter/variant"),
        ("sand", base / "sand2.png", "sand variant"),
        ("water", base / "water2.png", "water variant"),
        ("forest", base / "tree2.png", "tree variant"),
    ]
    for biome, p, desc in nice_to_have:
        if not p.is_file():
            if any(p.name in m for m in missing):
                continue
            missing.append(f"{biome}: {p.name} ({desc}) -> {p}")
    # Deduplicate
    # If sprites were loaded, remove ground plain suggestion if ground already has sprite
    # (keep informative note separate)
    SPRITES = sprites
    MISSING_SPRITES = missing
    return sprites, missing

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
        cs = _tg.CHUNK_SIZE
        cx, cy = wx // cs, wy // cs
        rx, ry = wx % cs, wy % cs
        chunk = self.get_chunk(cx, cy)
        return chunk.tiles.get((rx, ry))

    def get_chunk(self, cx, cy):
        if (cx, cy) not in self.loaded_chunks:
            self.loaded_chunks[(cx, cy)] = Chunk(cx, cy)
        return self.loaded_chunks[(cx, cy)]

    def update_loaded_chunks(self, player_wx, player_wy):
        """Loads chunks in advance and saves/unloads distant ones."""
        cs = _tg.CHUNK_SIZE
        p_cx = player_wx // cs
        p_cy = player_wy // cs

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

# --- PLAYER SYSTEM ---
class Player:
    def __init__(self, x=0, y=0):
        self.x = x
        self.y = y

    def move(self, dx, dy, world):
        target_tile = world.get_tile(self.x + dx, self.y + dy)
        if target_tile and target_tile.walkable:
            self.x += dx
            self.y += dy

    def save_player_xml(self):
        save_dir = _tg.SAVE_DIR
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        root = ET.Element("Player", x=str(self.x), y=str(self.y))
        tree = ET.ElementTree(root)
        tree.write(os.path.join(save_dir, "player.xml"))

    def load_player_xml(self):
        save_dir = _tg.SAVE_DIR
        filename = os.path.join(save_dir, "player.xml")
        if os.path.exists(filename):
            try:
                tree = ET.parse(filename)
                root = tree.getroot()
                self.x = int(root.attrib["x"])
                self.y = int(root.attrib["y"])
            except Exception:
                pass

# --- ENGINE ---
def main():
    pygame.init()
    # Load renderer config (mode 1 ASCII, 2 Sprites)
    cfg = load_renderer_config()
    mode = cfg["renderer_mode"]
    tile_size = cfg["tile_size"]
    debug = cfg.get("debug", True)

    # Prepare display and font / sprites depending on mode
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    caption_mode = "ASCII" if mode == 1 else "Sprites"
    pygame.display.set_caption(f"Infinite ASCII Explorer ({caption_mode})")
    clock = pygame.time.Clock()

    font = None
    tile_w = tile_h = tile_size
    sprites = {}
    missing_report = []
    if mode == 1:
        font = pygame.font.SysFont("Courier", FONT_SIZE, bold=True)
        tile_w, tile_h = font.size("@")
    else:
        # Sprite mode — load PNGs
        # Need display already init for convert_alpha
        sprites, missing_report = load_sprites(tile_size)
        tile_w = tile_h = tile_size
        if debug:
            print(f"[ascii] Renderer mode 2 (Sprites) tile_size={tile_size}")
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
    player = Player(0, 0)
    player.load_player_xml()

    running = True
    while running:
        # --- INPUT ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_r:
                    # Hot-reload both generation.xml and config.xml
                    reload_generation_config()
                    _sync_from_tg()
                    old_mode = mode
                    cfg = load_renderer_config()
                    mode = cfg["renderer_mode"]
                    tile_size = cfg["tile_size"]
                    debug = cfg.get("debug", True)
                    print(f"[ascii] Reloaded generation.xml — {len(_tg.get_biomes())} biomes active. Config mode={mode}")
                    # If mode or tile_size changed, rebuild font/sprites and viewport
                    if mode != old_mode or tile_size != tile_w:
                        if mode == 1:
                            font = pygame.font.SysFont("Courier", FONT_SIZE, bold=True)
                            tile_w, tile_h = font.size("@")
                            sprites = {}
                            caption_mode = "ASCII"
                        else:
                            font = None
                            sprites, missing_report = load_sprites(tile_size)
                            tile_w = tile_h = tile_size
                            caption_mode = "Sprites"
                            if debug and missing_report:
                                print("[ascii] Missing sprites after reload:")
                                for m in missing_report:
                                    print("  -", m)
                        pygame.display.set_caption(f"Infinite ASCII Explorer ({caption_mode})")
                        viewport_cols = SCREEN_WIDTH // tile_w
                        viewport_rows = (SCREEN_HEIGHT - 30) // tile_h

                dx, dy = 0, 0
                if event.key in (pygame.K_LEFT, pygame.K_h, pygame.K_KP4):
                    dx = -1
                elif event.key in (pygame.K_RIGHT, pygame.K_l, pygame.K_KP6):
                    dx = 1
                elif event.key in (pygame.K_UP, pygame.K_k, pygame.K_KP8):
                    dy = -1
                elif event.key in (pygame.K_DOWN, pygame.K_j, pygame.K_KP2):
                    dy = 1
                elif event.key in (pygame.K_y, pygame.K_KP7):
                    dx, dy = -1, -1
                elif event.key in (pygame.K_u, pygame.K_KP9):
                    dx, dy = 1, -1
                elif event.key in (pygame.K_b, pygame.K_KP1):
                    dx, dy = -1, 1
                elif event.key in (pygame.K_n, pygame.K_KP3):
                    dx, dy = 1, 1

                if dx != 0 or dy != 0:
                    player.move(dx, dy, world)

        # --- UPDATE CHUNKS ---
        world.update_loaded_chunks(player.x, player.y)

        # --- CAMERA PLACEMENT ---
        cam_x = player.x - viewport_cols // 2
        cam_y = player.y - viewport_rows // 2

        # --- RENDER ---
        screen.fill(COLOR_BG)

        if mode == 1:
            # ===== ASCII MODE =====
            for r in range(viewport_rows):
                wy = cam_y + r
                for c in range(viewport_cols):
                    wx = cam_x + c
                    
                    # Player render position override
                    if wx == player.x and wy == player.y:
                        continue

                    tile = world.get_tile(wx, wy)
                    if tile:
                        screen_x = c * tile_w
                        screen_y = r * tile_h
                        char_surf = font.render(tile.char, True, tile.color)
                        screen.blit(char_surf, (screen_x, screen_y))

            # Render Player centered
            p_screen_x = (player.x - cam_x) * tile_w
            p_screen_y = (player.y - cam_y) * tile_h
            p_surf = font.render(GLYPHS['player'], True, COLOR_PLAYER)
            screen.blit(p_surf, (p_screen_x, p_screen_y))
        else:
            # ===== SPRITE MODE =====
            for r in range(viewport_rows):
                wy = cam_y + r
                for c in range(viewport_cols):
                    wx = cam_x + c
                    if wx == player.x and wy == player.y:
                        continue
                    tile = world.get_tile(wx, wy)
                    if tile:
                        biome = getattr(tile, "biome", "")
                        # Fallback: infer from color if biome missing (old saves)
                        if not biome:
                            for bid, col in _tg.COLORS.items():
                                if col == tile.color:
                                    biome = bid
                                    break
                        surf = sprites.get(biome)
                        if surf:
                            screen_x = c * tile_w
                            screen_y = r * tile_h
                            screen.blit(surf, (screen_x, screen_y))
                        else:
                            # Leave blank per spec — just background
                            pass
            # Player sprite (blank if missing per spec)
            p_screen_x = (player.x - cam_x) * tile_w
            p_screen_y = (player.y - cam_y) * tile_h
            p_surf = sprites.get("player")
            if p_surf:
                screen.blit(p_surf, (p_screen_x, p_screen_y))
            else:
                pass  # leave blank — see missing sprites report

        # Status Bar (always ASCII font)
        if font is None:
            # need font for status even in sprite mode
            status_font = pygame.font.SysFont("Courier", FONT_SIZE, bold=True)
        else:
            status_font = font
        cs = _tg.CHUNK_SIZE
        p_chunk_x = player.x // cs
        p_chunk_y = player.y // cs
        mode_name = "ASCII" if mode == 1 else "SPRITES"
        status = f" World Pos: ({player.x}, {player.y}) | Chunk: ({p_chunk_x}, {p_chunk_y}) | Loaded: {len(world.loaded_chunks)} | Mode:{mode_name} R=Reload Esc=Save"
        status_surf = status_font.render(status, True, COLOR_TEXT)
        screen.blit(status_surf, (10, SCREEN_HEIGHT - 25))

        pygame.display.flip()
        clock.tick(30)

    # Clean Exit & Save
    print("Saving world XMLs...")
    world.save_all()
    player.save_player_xml()
    print("Save Complete!")
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
