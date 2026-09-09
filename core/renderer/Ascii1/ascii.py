import os
import sys
import math
import random
import xml.etree.ElementTree as ET
import pygame

# --- NOISE FALLBACK ---
try:
    import noise
    HAS_NOISE = True
except ImportError:
    HAS_NOISE = False
    print("Warning: 'noise' library not found. Install via 'pip install noise' for smoother terrain. Using basic fallback.")

# --- CONFIGURATION ---
CHUNK_SIZE = 16          # 16x16 tiles per chunk
FONT_SIZE = 20
SCREEN_WIDTH = 960
SCREEN_HEIGHT = 720
SAVE_DIR = "saves_world1"

# Load/Render Radii (in Chunks)
VIEW_RADIUS_CHUNKS = 2   # Visible range
LOAD_RADIUS_CHUNKS = 4   # Buffer generation range (prevents visual pop-in)

# Colors
COLOR_BG = (15, 15, 20)
COLOR_DARK_GRAY = (40, 40, 50)
COLOR_GROUND = (34, 139, 34)
COLOR_TREE = (0, 100, 0)
COLOR_MOUNTAIN = (139, 137, 137)
COLOR_WATER = (65, 105, 225)
COLOR_PLAYER = (255, 215, 0)
COLOR_TEXT = (220, 220, 220)

# Glyphs
GLYPHS = {'ground': '.', 'tree': 'T', 'mountain': '^', 'water': '~', 'player': '@'}

# --- TILE & CHUNK CLASSES ---
class Tile:
    def __init__(self, char, color, walkable):
        self.char = char
        self.color = color
        self.walkable = walkable

def get_terrain_type(wx, wy):
    """Procedural world terrain derived from coordinates."""
    if HAS_NOISE:
        # Scale controls feature density (mountains, oceans size)
        val = noise.pnoise2(wx * 0.05, wy * 0.05, octaves=3, persistence=0.5, lacunarity=2.0)
    else:
        # Simple math noise fallback if module is missing
        val = (math.sin(wx * 0.1) + math.cos(wy * 0.1)) / 2.0

    if val < -0.15:
        return GLYPHS['water'], COLOR_WATER, False
    elif val < 0.2:
        return GLYPHS['ground'], COLOR_GROUND, True
    elif val < 0.35:
        return GLYPHS['tree'], COLOR_TREE, False
    else:
        return GLYPHS['mountain'], COLOR_MOUNTAIN, False

class Chunk:
    def __init__(self, cx, cy):
        self.cx = cx
        self.cy = cy
        self.tiles = {}  # Relative (x, y) -> Tile
        self.modified = False
        
        if not self.load_from_xml():
            self.generate()

    def generate(self):
        """Generates chunk terrain based on world coordinates."""
        for y in range(CHUNK_SIZE):
            for x in range(CHUNK_SIZE):
                wx = self.cx * CHUNK_SIZE + x
                wy = self.cy * CHUNK_SIZE + y
                char, color, walkable = get_terrain_type(wx, wy)
                self.tiles[(x, y)] = Tile(char, color, walkable)

    def save_to_xml(self):
        """Saves chunk contents to an XML file."""
        if not os.path.exists(SAVE_DIR):
            os.makedirs(SAVE_DIR)

        root = ET.Element("Chunk", cx=str(self.cx), cy=str(self.cy))
        for (x, y), tile in self.tiles.items():
            tile_elem = ET.SubElement(root, "Tile", x=str(x), y=str(y))
            tile_elem.set("char", tile.char)
            tile_elem.set("walkable", str(tile.walkable))
            # Color as comma-separated str
            tile_elem.set("color", f"{tile.color[0]},{tile.color[1]},{tile.color[2]}")

        tree = ET.ElementTree(root)
        filename = os.path.join(SAVE_DIR, f"chunk_{self.cx}_{self.cy}.xml")
        tree.write(filename)

    def load_from_xml(self):
        """Attempts to load chunk state from an existing XML file."""
        filename = os.path.join(SAVE_DIR, f"chunk_{self.cx}_{self.cy}.xml")
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
                self.tiles[(x, y)] = Tile(char, rgb, walkable)
            return True
        except Exception as e:
            print(f"Failed loading chunk ({self.cx}, {self.cy}): {e}")
            return False

# --- WORLD MANAGER ---
class World:
    def __init__(self):
        self.loaded_chunks = {}  # (cx, cy) -> Chunk

    def get_tile(self, wx, wy):
        cx, cy = wx // CHUNK_SIZE, wy // CHUNK_SIZE
        rx, ry = wx % CHUNK_SIZE, wy % CHUNK_SIZE
        chunk = self.get_chunk(cx, cy)
        return chunk.tiles.get((rx, ry))

    def get_chunk(self, cx, cy):
        if (cx, cy) not in self.loaded_chunks:
            self.loaded_chunks[(cx, cy)] = Chunk(cx, cy)
        return self.loaded_chunks[(cx, cy)]

    def update_loaded_chunks(self, player_wx, player_wy):
        """Loads chunks in advance and saves/unloads distant ones."""
        p_cx = player_wx // CHUNK_SIZE
        p_cy = player_wy // CHUNK_SIZE

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
        root = ET.Element("Player", x=str(self.x), y=str(self.y))
        tree = ET.ElementTree(root)
        tree.write(os.path.join(SAVE_DIR, "player.xml"))

    def load_player_xml(self):
        filename = os.path.join(SAVE_DIR, "player.xml")
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
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Infinite ASCII Explorer (XML Saved World)")
    clock = pygame.time.Clock()

    font = pygame.font.SysFont("Courier", FONT_SIZE, bold=True)
    tile_w, tile_h = font.size("@")

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

        # Render Tiles within Screen Viewport
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

        # Status Bar
        p_chunk_x = player.x // CHUNK_SIZE
        p_chunk_y = player.y // CHUNK_SIZE
        status = f" World Pos: ({player.x}, {player.y}) | Chunk: ({p_chunk_x}, {p_chunk_y}) | Loaded Chunks: {len(world.loaded_chunks)} | Esc to Save & Exit"
        status_surf = font.render(status, True, COLOR_TEXT)
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