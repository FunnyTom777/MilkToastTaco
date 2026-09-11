"""
MTT ASCII Terrain Generation — data-driven via generation.xml

This module owns all procedural terrain logic that was previously
in ascii.py:get_terrain_type().  Editing `generation.xml` changes
world look without touching code.

Search order for generation.xml:
  1. explicit path passed to load_generation_config()
  2. alongside this file (core/renderer/Ascii1/generation.xml)
  3. data/generation.xml (repo data folder)
  4. ./generation.xml (cwd fallback)
If none found, built-in defaults are used (identical to old hardcoded values).

Exposes:
  Tile, CHUNK_SIZE, SAVE_DIR, GLYPHS, COLORS, PALETTE
  get_terrain_type(wx, wy) -> (char, color, walkable)
  load_generation_config(path=None) / reload_generation_config()
  get_generation_config() / get_biomes() / get_noise_config()
"""
from __future__ import annotations

import math
import os
import random
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# --- noise fallback ---
try:
    import noise  # type: ignore
    HAS_NOISE = True
except ImportError:
    HAS_NOISE = False

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class NoiseConfig:
    scale: float = 0.032
    octaves: int = 3
    persistence: float = 0.42
    lacunarity: float = 2.0
    seed_offset: int = 0
    fallback_scale: float = 0.06

@dataclass
class WheatFieldConfig:
    scale: float = 0.08
    octaves: int = 2
    persistence: float = 0.5
    threshold: float = 0.38
    trampled_chance: float = 0.65
    seed_offset: int = 777
    fallback_scale: float = 0.10

@dataclass
class BiomeRule:
    id: str
    threshold_max: float
    char: str
    color: Tuple[int, int, int]
    walkable: bool
    name: str = ""

@dataclass
class Variant:
    char: str
    weight: float

@dataclass
class ScatterFeature:
    biome: str
    char: str
    color: Tuple[int, int, int]
    chance: float
    walkable: Optional[bool] = None  # None = keep biome walkable

@dataclass
class GroundDetailConfig:
    """Second noise layer that splits base 'ground' into visual sub-biomes.

    Sub-biomes are matched first threshold_max >= detail_value wins.
    The 'plains' entry (id == 'ground') keeps the base look; other ids
    become distinct biome_ids with their own ASCII glyph + sprite.
    """
    scale: float = 0.11
    octaves: int = 2
    persistence: float = 0.5
    seed_offset: int = 1234
    fallback_scale: float = 0.13
    stump_chance: float = 0.02

@dataclass
class GroundSubBiome:
    id: str
    threshold_max: float
    char: str
    color: Tuple[int, int, int]
    walkable: bool
    sprite: str = ""
    name: str = ""

@dataclass
class MesaConfig:
    """Rare LARGE badlands mask on top of base 'ground'.

    When the low-frequency mask noise exceeds `threshold`, the tile becomes
    part of a big terracotta/dirt/gravel mesa instead of the normal ground
    detail patch. Weights control the mix inside the mesa.
    """
    scale: float = 0.025
    octaves: int = 2
    persistence: float = 0.5
    threshold: float = 0.35
    seed_offset: int = 5555
    fallback_scale: float = 0.03
    terracotta_weight: float = 50.0
    dirt_weight: float = 30.0
    gravel_weight: float = 20.0

@dataclass
class GenerationConfig:
    chunk_size: int = 16
    seed: int = 0
    save_dir: str = "saves_world1"
    noise: NoiseConfig = field(default_factory=NoiseConfig)
    wheat: WheatFieldConfig = field(default_factory=WheatFieldConfig)
    ground_detail: GroundDetailConfig = field(default_factory=GroundDetailConfig)
    ground_subbiomes: List[GroundSubBiome] = field(default_factory=list)
    mesa: MesaConfig = field(default_factory=MesaConfig)
    biomes: List[BiomeRule] = field(default_factory=list)
    variants: Dict[str, List[Variant]] = field(default_factory=dict)
    scatter: List[ScatterFeature] = field(default_factory=dict)
    palette: Dict[str, Tuple[int, int, int]] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Defaults (mirrors old ascii.py hardcoded behaviour + small built-in variation)
# ---------------------------------------------------------------------------

_DEFAULT_BIOMES: List[BiomeRule] = [
    BiomeRule("water",    -0.20, "~", (65, 105, 225), False, "Water"),
    BiomeRule("sand",     -0.14, ".", (210, 180, 140), True,  "Sand"),
    BiomeRule("ground",    0.20, ".", (34, 139, 34),  True,  "Plains"),
    BiomeRule("forest",    0.35, "T", (0, 100, 0),    False, "Forest"),
    BiomeRule("mountain",  1.0,  "^", (139, 137, 137), False, "Mountain"),
]

_DEFAULT_VARIANTS: Dict[str, List[Variant]] = {
    "ground":   [Variant(".", 70), Variant(",", 15), Variant("`", 10), Variant("'", 5)],
    "sand":     [Variant(".", 60), Variant(",", 20), Variant(":", 10), Variant("`", 10)],
    "forest":   [Variant("T", 60), Variant("t", 25), Variant("*", 15)],
    "mountain": [Variant("^", 65), Variant("M", 20), Variant("A", 15)],
    "water":    [Variant("~", 80), Variant("-", 12), Variant("=", 8)],
}

_DEFAULT_SCATTER: List[ScatterFeature] = [
    ScatterFeature("ground",   "*", (50, 205, 50),  0.015, True),
    ScatterFeature("ground",   "o", (139, 69, 19),  0.008, True),
    ScatterFeature("ground",   "%", (255, 215, 0),  0.005, True),
    ScatterFeature("sand",     "o", (210, 180, 140), 0.012, True),  # shells/pebbles on beach
    ScatterFeature("sand",     "*", (255, 228, 181), 0.006, True),
    ScatterFeature("mountain", "#", (105, 105, 105), 0.02, False),
    ScatterFeature("water",    "=", (0, 191, 255),  0.01,  False),
]

_DEFAULT_PALETTE: Dict[str, Tuple[int, int, int]] = {
    "bg":        (15, 15, 20),
    "dark_gray": (40, 40, 50),
    "player":    (255, 215, 0),
    "text":      (220, 220, 220),
}

# Ground detail sub-biomes — all walkable, only spawn on base "ground".
# Ordered by threshold_max ascending; detail noise is ~ -1..1, center band
# is plains (dominant) so the world still reads as grassland.
# NOTE: terracotta deliberately NOT here — it only spawns inside the rare
# large mesa mask (see MesaConfig) so it stays rare but clustered.
# dark_grass retired (never generates); sprite kept loaded for old saves.
_DEFAULT_GROUND_SUBBIOMES: List["GroundSubBiome"] = [
    GroundSubBiome("clay",        -0.45, "c", (205, 102, 29),  True, "clay1.png",        "Clay"),
    GroundSubBiome("dirt",        -0.15, "d", (139, 69, 19),   True, "dirt1.png",        "Dirt"),
    GroundSubBiome("ground",       0.30, ".", (34, 139, 34),   True, "grass_plain1.png", "Plains"),
    GroundSubBiome("dry_grass",    0.45, "y", (189, 183, 107), True, "dry_grass1.png",   "Dry Grass"),
    GroundSubBiome("muddy",        1.0,  "m", (121, 85, 58),   True, "grass_muddy1.png", "Muddy Grass"),
]
# Stump is a rare single-tile overlay on plains (not a noise band — fields
# of stumps would look wrong). Sprite: grass_plain_with_stump1.png
_DEFAULT_STUMP = GroundSubBiome("stump", 1.0, "o", (139, 69, 19), True, "grass_plain_with_stump1.png", "Old Stump")
# Mesa (badlands) mix — only picked inside the mesa mask, never standalone.
_DEFAULT_MESA_TERRACOTTA = GroundSubBiome("terracotta", 1.0, "r", (165, 42, 42), True, "brown_terracota1.png", "Terracotta")
_DEFAULT_GRAVEL = GroundSubBiome("gravel", 1.0, "v", (150, 145, 135), True, "rocky_dirt1.png", "Gravel")

_DEFAULT_NOISE = NoiseConfig()

# ---------------------------------------------------------------------------
# Module globals (mutable via load_generation_config)
# ---------------------------------------------------------------------------

_CONFIG: GenerationConfig = GenerationConfig(
    chunk_size=16,
    seed=0,
    save_dir="saves_world1",
    noise=NoiseConfig(),
    wheat=WheatFieldConfig(),
    ground_detail=GroundDetailConfig(),
    ground_subbiomes=list(_DEFAULT_GROUND_SUBBIOMES),
    mesa=MesaConfig(),
    biomes=list(_DEFAULT_BIOMES),
    variants=dict(_DEFAULT_VARIANTS),
    scatter=list(_DEFAULT_SCATTER),
    palette=dict(_DEFAULT_PALETTE),
)

# Convenience re-exports for ascii.py compat
CHUNK_SIZE: int = _CONFIG.chunk_size
SAVE_DIR: str = _CONFIG.save_dir
GLYPHS: Dict[str, str] = {b.id: b.char for b in _CONFIG.biomes}
GLYPHS["player"] = "@"
COLORS: Dict[str, Tuple[int, int, int]] = {b.id: b.color for b in _CONFIG.biomes}
PALETTE: Dict[str, Tuple[int, int, int]] = dict(_CONFIG.palette)

# Back-compat colour constants that ascii.py used directly
COLOR_BG = PALETTE.get("bg", (15, 15, 20))
COLOR_DARK_GRAY = PALETTE.get("dark_gray", (40, 40, 50))
COLOR_PLAYER = PALETTE.get("player", (255, 215, 0))
COLOR_TEXT = PALETTE.get("text", (220, 220, 220))
# Per-biome colours
COLOR_GROUND = COLORS.get("ground", (34, 139, 34))
COLOR_SAND = COLORS.get("sand", (210, 180, 140))
COLOR_TREE = COLORS.get("forest", (0, 100, 0))
COLOR_MOUNTAIN = COLORS.get("mountain", (139, 137, 137))
COLOR_WATER = COLORS.get("water", (65, 105, 225))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_color(s: str, fallback: Tuple[int, int, int] = (255, 255, 255)) -> Tuple[int, int, int]:
    try:
        parts = [int(x.strip()) for x in s.split(",")]
        if len(parts) == 3:
            return (max(0, min(255, parts[0])), max(0, min(255, parts[1])), max(0, min(255, parts[2])))
    except Exception:
        pass
    return fallback


def _find_generation_xml(explicit: Optional[str | Path] = None) -> Optional[Path]:
    candidates: List[Path] = []
    if explicit:
        candidates.append(Path(explicit))
    # alongside this module
    candidates.append(Path(__file__).with_name("generation.xml"))
    # data/ relative to repo root (two levels up from Ascii1)
    # core/renderer/Ascii1 -> core/renderer -> core -> repo root
    try:
        repo_data = Path(__file__).resolve().parents[3] / "data" / "generation.xml"
        candidates.append(repo_data)
    except Exception:
        pass
    # also try cwd variations
    candidates.append(Path.cwd() / "data" / "generation.xml")
    candidates.append(Path.cwd() / "core" / "renderer" / "Ascii1" / "generation.xml")
    candidates.append(Path.cwd() / "generation.xml")

    for p in candidates:
        try:
            if p.is_file():
                return p
        except Exception:
            continue
    return None


def _sync_module_globals():
    """Push _CONFIG into the legacy module-level constants."""
    global CHUNK_SIZE, SAVE_DIR, GLYPHS, COLORS, PALETTE
    global COLOR_BG, COLOR_DARK_GRAY, COLOR_PLAYER, COLOR_TEXT
    global COLOR_GROUND, COLOR_SAND, COLOR_TREE, COLOR_MOUNTAIN, COLOR_WATER

    CHUNK_SIZE = _CONFIG.chunk_size
    SAVE_DIR = _CONFIG.save_dir
    GLYPHS = {b.id: b.char for b in _CONFIG.biomes}
    GLYPHS["player"] = "@"
    # Add wheat overlay biomes (not in threshold list) for sprite/ASCII mapping
    GLYPHS["wheat"] = "w"
    GLYPHS["wheat_trampled"] = "x"
    # Ground detail sub-biomes (dirt, clay, ...) + mesa-only ones — also mappable
    for sub in _CONFIG.ground_subbiomes:
        GLYPHS[sub.id] = sub.char
    GLYPHS["stump"] = _DEFAULT_STUMP.char
    GLYPHS["terracotta"] = _DEFAULT_MESA_TERRACOTTA.char
    GLYPHS["gravel"] = _DEFAULT_GRAVEL.char
    # dark_grass retired from generation but kept mapped so old saves render
    GLYPHS.setdefault("dark_grass", "g")
    COLORS = {b.id: b.color for b in _CONFIG.biomes}
    COLORS["wheat"] = (255, 215, 0)
    COLORS["wheat_trampled"] = (184, 134, 11)
    for sub in _CONFIG.ground_subbiomes:
        COLORS[sub.id] = sub.color
    COLORS["stump"] = _DEFAULT_STUMP.color
    COLORS["terracotta"] = _DEFAULT_MESA_TERRACOTTA.color
    COLORS["gravel"] = _DEFAULT_GRAVEL.color
    COLORS.setdefault("dark_grass", (34, 100, 34))
    PALETTE = dict(_CONFIG.palette)

    COLOR_BG = PALETTE.get("bg", (15, 15, 20))
    COLOR_DARK_GRAY = PALETTE.get("dark_gray", (40, 40, 50))
    COLOR_PLAYER = PALETTE.get("player", (255, 215, 0))
    COLOR_TEXT = PALETTE.get("text", (220, 220, 220))
    COLOR_GROUND = COLORS.get("ground", COLORS.get("plains", (34, 139, 34)))
    COLOR_SAND = COLORS.get("sand", (210, 180, 140))
    # forest/tree alias
    COLOR_TREE = COLORS.get("forest", COLORS.get("tree", (0, 100, 0)))
    COLOR_MOUNTAIN = COLORS.get("mountain", (139, 137, 137))
    COLOR_WATER = COLORS.get("water", (65, 105, 225))


# ---------------------------------------------------------------------------
# XML loading
# ---------------------------------------------------------------------------

def load_generation_config(path: Optional[str | Path] = None) -> GenerationConfig:
    """
    Load generation.xml (or use defaults).  Called automatically on import.
    Returns the active GenerationConfig.
    """
    global _CONFIG

    xml_path = _find_generation_xml(path)
    if xml_path is None:
        # No file — keep defaults but ensure globals are synced
        if path is not None:
            print(f"[terrain_generation] generation.xml not found at '{path}', using defaults.")
        _sync_module_globals()
        return _CONFIG

    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except Exception as e:
        print(f"[terrain_generation] Failed parsing {xml_path}: {e} — using defaults.")
        _sync_module_globals()
        return _CONFIG

    cfg = GenerationConfig()
    # keep defaults as fallback, override what XML provides

    # -- settings --
    settings = root.find("settings")
    if settings is not None:
        try:
            cfg.chunk_size = int(settings.get("chunk_size", cfg.chunk_size))
        except Exception:
            pass
        try:
            cfg.seed = int(settings.get("seed", cfg.seed))
        except Exception:
            pass
        cfg.save_dir = settings.get("save_dir", cfg.save_dir) or cfg.save_dir

    # -- noise --
    noise_cfg = NoiseConfig()
    n_elem = root.find("noise")
    if n_elem is not None:
        try:
            noise_cfg.scale = float(n_elem.get("scale", noise_cfg.scale))
            noise_cfg.octaves = int(n_elem.get("octaves", noise_cfg.octaves))
            noise_cfg.persistence = float(n_elem.get("persistence", noise_cfg.persistence))
            noise_cfg.lacunarity = float(n_elem.get("lacunarity", noise_cfg.lacunarity))
            noise_cfg.seed_offset = int(n_elem.get("seed_offset", noise_cfg.seed_offset))
        except Exception as e:
            print(f"[terrain_generation] noise parse warning: {e}")
    fb = root.find("fallback")
    if fb is not None:
        try:
            noise_cfg.fallback_scale = float(fb.get("scale", noise_cfg.fallback_scale))
        except Exception:
            pass
    cfg.noise = noise_cfg

    # -- wheat fields (clumps with trampled ring) --
    wheat_cfg = WheatFieldConfig()
    w_elem = root.find("wheat_fields")
    if w_elem is None:
        w_elem = root.find("wheat")  # alias
    if w_elem is not None:
        try:
            wheat_cfg.scale = float(w_elem.get("scale", wheat_cfg.scale))
            wheat_cfg.octaves = int(w_elem.get("octaves", wheat_cfg.octaves))
            wheat_cfg.threshold = float(w_elem.get("threshold", wheat_cfg.threshold))
            wheat_cfg.trampled_chance = float(w_elem.get("trampled_chance", wheat_cfg.trampled_chance))
            wheat_cfg.seed_offset = int(w_elem.get("seed_offset", wheat_cfg.seed_offset))
            # fallback scale optional
            fb = w_elem.get("fallback_scale")
            if fb is not None:
                wheat_cfg.fallback_scale = float(fb)
        except Exception as e:
            print(f"[terrain_generation] wheat_fields parse warning: {e}")
    cfg.wheat = wheat_cfg

    # -- ground detail (second noise layer splitting ground into sub-biomes) --
    ground_cfg = GroundDetailConfig()
    gd_elem = root.find("ground_detail")
    if gd_elem is not None:
        try:
            ground_cfg.scale = float(gd_elem.get("scale", ground_cfg.scale))
            ground_cfg.octaves = int(gd_elem.get("octaves", ground_cfg.octaves))
            ground_cfg.persistence = float(gd_elem.get("persistence", ground_cfg.persistence))
            ground_cfg.seed_offset = int(gd_elem.get("seed_offset", ground_cfg.seed_offset))
            ground_cfg.stump_chance = float(gd_elem.get("stump_chance", ground_cfg.stump_chance))
            fb_val = gd_elem.get("fallback_scale")
            if fb_val is not None:
                ground_cfg.fallback_scale = float(fb_val)
        except Exception as e:
            print(f"[terrain_generation] ground_detail parse warning: {e}")
        subs: List[GroundSubBiome] = []
        for s in gd_elem.findall("subbiome"):
            try:
                sid = s.get("id")
                if not sid:
                    continue
                tmax = float(s.get("threshold_max", "1.0"))
                ch = s.get("char", ".")
                col = _parse_color(s.get("color", "255,255,255"))
                w_raw = s.get("walkable", "true").lower()
                walkable = w_raw in ("true", "1", "yes")
                sprite = s.get("sprite", "")
                name = s.get("name", sid)
                subs.append(GroundSubBiome(sid, tmax, ch, col, walkable, sprite, name))
            except Exception as e:
                print(f"[terrain_generation] ground subbiome parse warning: {e}")
        if subs:
            subs.sort(key=lambda r: r.threshold_max)
            cfg.ground_subbiomes = subs
        else:
            cfg.ground_subbiomes = list(_DEFAULT_GROUND_SUBBIOMES)
    else:
        cfg.ground_subbiomes = list(_DEFAULT_GROUND_SUBBIOMES)
    cfg.ground_detail = ground_cfg

    # -- mesa / badlands (rare large terracotta+dirt+gravel mask) --
    mesa_cfg = MesaConfig()
    mesa_elem = root.find("mesa")
    if mesa_elem is None:
        mesa_elem = root.find("mesa_biome")  # alias
    if mesa_elem is not None:
        try:
            mesa_cfg.scale = float(mesa_elem.get("scale", mesa_cfg.scale))
            mesa_cfg.octaves = int(mesa_elem.get("octaves", mesa_cfg.octaves))
            mesa_cfg.persistence = float(mesa_elem.get("persistence", mesa_cfg.persistence))
            mesa_cfg.threshold = float(mesa_elem.get("threshold", mesa_cfg.threshold))
            mesa_cfg.seed_offset = int(mesa_elem.get("seed_offset", mesa_cfg.seed_offset))
            mesa_cfg.terracotta_weight = float(mesa_elem.get("terracotta_weight", mesa_cfg.terracotta_weight))
            mesa_cfg.dirt_weight = float(mesa_elem.get("dirt_weight", mesa_cfg.dirt_weight))
            mesa_cfg.gravel_weight = float(mesa_elem.get("gravel_weight", mesa_cfg.gravel_weight))
            fb_val = mesa_elem.get("fallback_scale")
            if fb_val is not None:
                mesa_cfg.fallback_scale = float(fb_val)
        except Exception as e:
            print(f"[terrain_generation] mesa parse warning: {e}")
    cfg.mesa = mesa_cfg

    # -- palette --
    palette: Dict[str, Tuple[int, int, int]] = dict(_DEFAULT_PALETTE)
    pal_elem = root.find("palette")
    if pal_elem is not None:
        for c in pal_elem.findall("color"):
            cid = c.get("id")
            val = c.get("value")
            if cid and val:
                palette[cid] = _parse_color(val, palette.get(cid, (255, 255, 255)))
    cfg.palette = palette

    # -- terrain biomes --
    biomes: List[BiomeRule] = []
    terrain = root.find("terrain")
    if terrain is not None:
        for b in terrain.findall("biome"):
            try:
                bid = b.get("id")
                if not bid:
                    continue
                tmax = float(b.get("threshold_max", "1.0"))
                char = b.get("char", "?")
                color = _parse_color(b.get("color", "255,255,255"))
                walk_raw = b.get("walkable", "true").lower()
                walkable = walk_raw in ("true", "1", "yes")
                name = b.get("name", bid)
                biomes.append(BiomeRule(bid, tmax, char, color, walkable, name))
            except Exception as e:
                print(f"[terrain_generation] biome parse warning: {e}")
    if biomes:
        # sort ascending so first match wins
        biomes.sort(key=lambda r: r.threshold_max)
        cfg.biomes = biomes
    else:
        cfg.biomes = list(_DEFAULT_BIOMES)

    # -- variants --
    variants: Dict[str, List[Variant]] = {}
    var_root = root.find("variants")
    if var_root is not None:
        for bv in var_root.findall("biome_variants"):
            biome_id = bv.get("biome")
            if not biome_id:
                continue
            lst: List[Variant] = []
            for v in bv.findall("variant"):
                try:
                    ch = v.get("char", ".")
                    w = float(v.get("weight", "1"))
                    if w <= 0:
                        continue
                    lst.append(Variant(ch, w))
                except Exception:
                    continue
            if lst:
                variants[biome_id] = lst
    # If <variants> block exists, use exactly what it defines (may be empty = no variation).
    # If missing, treat as no variants — keeps custom biome chars intact.
    # Shipped generation.xml explicitly defines variants, so defaults only apply via fallback path below.
    if var_root is not None:
        cfg.variants = variants  # may be empty dict if no entries
    else:
        cfg.variants = {}

    # -- scatter --
    scatter: List[ScatterFeature] = []
    scatter_root = root.find("scatter")
    if scatter_root is not None:
        for f in scatter_root.findall("feature"):
            try:
                biome = f.get("biome")
                if not biome:
                    continue
                ch = f.get("char", "*")
                col = _parse_color(f.get("color", "255,255,255"))
                chance = float(f.get("chance", "0.01"))
                chance = max(0.0, min(1.0, chance))
                w_raw = f.get("walkable")
                walkable: Optional[bool] = None
                if w_raw is not None:
                    walkable = w_raw.lower() in ("true", "1", "yes")
                scatter.append(ScatterFeature(biome, ch, col, chance, walkable))
            except Exception as e:
                print(f"[terrain_generation] scatter parse warning: {e}")
        cfg.scatter = scatter
    else:
        cfg.scatter = []

    # Fallback defaults when XML is essentially empty (no terrain/variants/scatter):
    # use built-in defaults so an empty <generation/> still works.
    if terrain is None and var_root is None and scatter_root is None:
        # Only settings/palette present — inject built-in terrain + variation for a playable world
        if not cfg.biomes or cfg.biomes == list(_DEFAULT_BIOMES):
            # cfg.biomes already set to defaults above; ensure variants/scatter also default
            cfg.variants = dict(_DEFAULT_VARIANTS)
            cfg.scatter = list(_DEFAULT_SCATTER)

    _CONFIG = cfg
    _sync_module_globals()
    # print(f"[terrain_generation] Loaded {xml_path} — {len(cfg.biomes)} biomes, {len(cfg.variants)} variant groups, {len(cfg.scatter)} scatter rules.")
    return _CONFIG


def reload_generation_config(path: Optional[str | Path] = None) -> GenerationConfig:
    """Hot-reload generation.xml (useful for debug tools / hotkey)."""
    return load_generation_config(path)


def get_generation_config() -> GenerationConfig:
    return _CONFIG

def get_biomes() -> List[BiomeRule]:
    return list(_CONFIG.biomes)

def get_noise_config() -> NoiseConfig:
    return _CONFIG.noise
def get_variants() -> Dict[str, List[Variant]]:
    return dict(_CONFIG.variants)


def get_scatter() -> List[ScatterFeature]:
    return list(_CONFIG.scatter)


def get_ground_subbiomes() -> List[GroundSubBiome]:
    return list(_CONFIG.ground_subbiomes)


def get_ground_detail_config() -> GroundDetailConfig:
    return _CONFIG.ground_detail


def get_mesa_config() -> MesaConfig:
    return _CONFIG.mesa


# ---------------------------------------------------------------------------
# Core generation
# ---------------------------------------------------------------------------

def _sample_noise(wx: int, wy: int) -> float:
    cfg = _CONFIG.noise
    if HAS_NOISE:
        # noise.pnoise2 expects floats; seed offset via extra offset
        # Use deterministic offset so seed matters
        off = cfg.seed_offset + _CONFIG.seed
        # Shift coords by large offset to avoid symmetry at 0,0
        return noise.pnoise2(
            (wx + off * 1000) * cfg.scale,
            (wy + off * 1000) * cfg.scale,
            octaves=cfg.octaves,
            persistence=cfg.persistence,
            lacunarity=cfg.lacunarity,
        )
    else:
        s = cfg.fallback_scale
        # include seed in fallback for determinism
        return (math.sin((wx + _CONFIG.seed) * s) + math.cos((wy + _CONFIG.seed) * s)) / 2.0


def _deterministic_rng(wx: int, wy: int, salt: int = 0) -> random.Random:
    """
    Seeded RNG that is deterministic per world coordinate.
    Uses a hash mixing wx/wy/seed so same tile always gets same variant.
    """
    # Simple integer hash — fast, stable across runs
    h = (wx * 73856093) ^ (wy * 19349663) ^ (_CONFIG.seed * 83492791) ^ (salt * 1376312589)
    # Keep within 32-bit seed range for random.Random
    h = h & 0xFFFFFFFF
    return random.Random(h)


def _pick_variant(biome_id: str, wx: int, wy: int) -> Optional[str]:
    variants = _CONFIG.variants.get(biome_id)
    if not variants:
        return None
    total = sum(v.weight for v in variants)
    if total <= 0:
        return None
    rng = _deterministic_rng(wx, wy, salt=1)
    r = rng.random() * total
    acc = 0.0
    for v in variants:
        acc += v.weight
        if r < acc:
            return v.char
    return variants[-1].char


def _maybe_scatter(biome_id: str, wx: int, wy: int) -> Optional[ScatterFeature]:
    """Return a scatter feature that should override this tile, or None."""
    # Collect candidates for this biome
    candidates = [s for s in _CONFIG.scatter if s.biome == biome_id]
    if not candidates:
        return None
    rng = _deterministic_rng(wx, wy, salt=99)
    # Roll per feature — first winner wins (deterministic order)
    for feat in candidates:
        if rng.random() < feat.chance:
            return feat
    return None


# ---------------------------------------------------------------------------
# Public API expected by ascii.py
# ---------------------------------------------------------------------------

class Tile:
    """Single world tile — kept here so Chunk can import it."""
    def __init__(self, char: str, color: Tuple[int, int, int], walkable: bool, biome: str = ""):
        self.char = char
        self.color = color
        self.walkable = walkable
        self.biome = biome  # e.g. "ground", "water", "sand" — used for sprite mapping

    def __repr__(self):
        return f"Tile({self.char!r}, {self.color}, walkable={self.walkable}, biome={self.biome!r})"


def _is_adjacent_to_water(wx: int, wy: int, water_threshold: float) -> bool:
    """Check 8 neighbors for water — used to keep sand only around water edges."""
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            if _sample_noise(wx + dx, wy + dy) <= water_threshold:
                return True
    return False


def _sample_wheat_noise(wx: int, wy: int) -> float:
    cfg = _CONFIG.wheat
    if HAS_NOISE:
        off = cfg.seed_offset + _CONFIG.seed
        return noise.pnoise2(
            (wx + off * 1000) * cfg.scale,
            (wy + off * 1000) * cfg.scale,
            octaves=cfg.octaves,
            persistence=cfg.persistence,
            lacunarity=2.0,
        )
    else:
        s = cfg.fallback_scale
        return (math.sin((wx + _CONFIG.seed + cfg.seed_offset) * s) + math.cos((wy + _CONFIG.seed + cfg.seed_offset) * s)) / 2.0


def _is_inside_wheat_field(wx: int, wy: int) -> bool:
    return _sample_wheat_noise(wx, wy) > _CONFIG.wheat.threshold


def _is_wheat_edge(wx: int, wy: int) -> bool:
    """Edge if any 8-neighbor is outside wheat field."""
    if not _is_inside_wheat_field(wx, wy):
        return False
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            if not _is_inside_wheat_field(wx + dx, wy + dy):
                return True
    return False


def _sample_ground_detail(wx: int, wy: int) -> float:
    cfg = _CONFIG.ground_detail
    if HAS_NOISE:
        off = cfg.seed_offset + _CONFIG.seed
        return noise.pnoise2(
            (wx + off * 1000) * cfg.scale,
            (wy + off * 1000) * cfg.scale,
            octaves=cfg.octaves,
            persistence=cfg.persistence,
            lacunarity=2.0,
        )
    s = cfg.fallback_scale
    return (math.sin((wx + _CONFIG.seed + cfg.seed_offset) * s) + math.cos((wy + _CONFIG.seed + cfg.seed_offset) * s)) / 2.0


def _maybe_ground_detail(wx: int, wy: int) -> Optional[GroundSubBiome]:
    """Pick a ground sub-biome via detail noise. None = keep base look.

    Returns the 'ground' (plains) entry as None so callers keep existing
    char/color/biome — only non-plains entries override.
    """
    subs = _CONFIG.ground_subbiomes
    if not subs:
        return None
    val = _sample_ground_detail(wx, wy)
    picked: Optional[GroundSubBiome] = None
    for sub in subs:
        if val <= sub.threshold_max:
            picked = sub
            break
    if picked is None:
        picked = subs[-1]
    if picked.id == "ground":
        # Rare stump overlay on plains — single tiles, not fields
        chance = _CONFIG.ground_detail.stump_chance
        if chance > 0 and _deterministic_rng(wx, wy, salt=55).random() < chance:
            return _DEFAULT_STUMP
        return None
    if picked.id == "dark_grass":
        # Retired tile — old configs may still list it; treat as plains.
        # (Stump roll above already handled when band id is exactly ground.)
        chance = _CONFIG.ground_detail.stump_chance
        if chance > 0 and _deterministic_rng(wx, wy, salt=55).random() < chance:
            return _DEFAULT_STUMP
        return None
    return picked


def _sample_mesa_noise(wx: int, wy: int) -> float:
    cfg = _CONFIG.mesa
    if HAS_NOISE:
        off = cfg.seed_offset + _CONFIG.seed
        return noise.pnoise2(
            (wx + off * 1000) * cfg.scale,
            (wy + off * 1000) * cfg.scale,
            octaves=cfg.octaves,
            persistence=cfg.persistence,
            lacunarity=2.0,
        )
    s = cfg.fallback_scale
    return (math.sin((wx + _CONFIG.seed + cfg.seed_offset) * s) + math.cos((wy + _CONFIG.seed + cfg.seed_offset) * s)) / 2.0


def _is_inside_mesa(wx: int, wy: int) -> bool:
    return _sample_mesa_noise(wx, wy) > _CONFIG.mesa.threshold


def _maybe_mesa_tile(wx: int, wy: int) -> Optional[GroundSubBiome]:
    """Weighted terracotta/dirt/gravel pick inside a mesa. None = outside mesa."""
    if not _is_inside_mesa(wx, wy):
        return None
    cfg = _CONFIG.mesa
    total = cfg.terracotta_weight + cfg.dirt_weight + cfg.gravel_weight
    if total <= 0:
        return _DEFAULT_MESA_TERRACOTTA
    r = _deterministic_rng(wx, wy, salt=58).random() * total
    if r < cfg.terracotta_weight:
        return _DEFAULT_MESA_TERRACOTTA
    if r < cfg.terracotta_weight + cfg.dirt_weight:
        # Mesa dirt reuses the normal dirt look
        for sub in _CONFIG.ground_subbiomes:
            if sub.id == "dirt":
                return sub
        return GroundSubBiome("dirt", 1.0, "d", (139, 69, 19), True, "dirt1.png", "Dirt")
    return _DEFAULT_GRAVEL


def get_terrain_with_biome(wx: int, wy: int) -> Tuple[str, Tuple[int, int, int], bool, str]:
    """
    Like get_terrain_type but also returns biome id.
    Returns (char, color, walkable, biome_id). Deterministic.
    """
    val = _sample_noise(wx, wy)

    # Find biome (first threshold_max >= val)
    biome: Optional[BiomeRule] = None
    for b in _CONFIG.biomes:
        if val <= b.threshold_max:
            biome = b
            break
    if biome is None:
        biome = _CONFIG.biomes[-1]

    # Sand adjacency enforcement: sand (tan '.') only appears around water.
    if biome.id == "sand":
        water_thresh = None
        ground_biome = None
        for b in _CONFIG.biomes:
            if b.id == "water":
                water_thresh = b.threshold_max
            if b.id == "ground":
                ground_biome = b
        if water_thresh is not None and not _is_adjacent_to_water(wx, wy, water_thresh):
            if ground_biome is not None:
                biome = ground_biome

    # Base char/color/walkable from biome
    char = biome.char
    color = biome.color
    walkable = biome.walkable
    biome_id = biome.id

    # --- Wheat field clumps (only on ground) ---
    # Center = normal wheat "w" gold, edge ring = trampled "x" brown with chance
    # Wheat wins over ground detail so fields stay visible.
    if biome_id == "ground" and _is_inside_wheat_field(wx, wy):
        is_edge = _is_wheat_edge(wx, wy)
        if is_edge and _deterministic_rng(wx, wy, salt=77).random() < _CONFIG.wheat.trampled_chance:
            # Sometimes keep normal wheat on edge too — chance to be trampled
            char = "x"
            color = (184, 134, 11)  # trampled wheat / dry
            biome_id = "wheat_trampled"
            walkable = True
        else:
            char = "w"
            color = (255, 215, 0)  # wheat gold
            biome_id = "wheat"
            walkable = True
        return char, color, walkable, biome_id

    # --- Mesa badlands (rare + LARGE terracotta/dirt/gravel blobs) ---
    # Checked before ground detail so mesas stay solid instead of speckled.
    if biome_id == "ground":
        mesa_tile = _maybe_mesa_tile(wx, wy)
        if mesa_tile is not None:
            return mesa_tile.char, mesa_tile.color, mesa_tile.walkable, mesa_tile.id

    # --- Ground detail sub-biomes (dirt, clay, dry grass, ...) ---
    # Only applies to base ground; gives new tiles real gameplay presence
    # with distinct ASCII glyphs + sprites. Deterministic per coord.
    if biome_id == "ground":
        sub = _maybe_ground_detail(wx, wy)
        if sub is not None:
            return sub.char, sub.color, sub.walkable, sub.id

    # Variant glyph (keeps color/walkable, not biome)
    var_char = _pick_variant(biome_id, wx, wy)
    if var_char is not None:
        char = var_char

    # Scatter override — may change char/color/walkable but keep base biome for sprite
    scatter = _maybe_scatter(biome_id, wx, wy)
    if scatter is not None:
        char = scatter.char
        color = scatter.color
        if scatter.walkable is not None:
            walkable = scatter.walkable
        # Note: biome_id stays as base biome so sprite still draws underlying terrain

    return char, color, walkable, biome_id


def get_terrain_type(wx: int, wy: int) -> Tuple[str, Tuple[int, int, int], bool]:
    """
    Procedural terrain for world coord (wx, wy).
    Returns (char, color, walkable).
    Deterministic — same coords always give same result for same config.
    Kept for backwards compat — wraps get_terrain_with_biome.
    """
    char, color, walkable, _ = get_terrain_with_biome(wx, wy)
    return char, color, walkable


# Legacy glyph map for code that does GLYPHS['ground'] etc.
# We map old keys to new biome ids for compat
def _build_legacy_glyphs() -> Dict[str, str]:
    base = {b.id: b.char for b in _CONFIG.biomes}
    # aliases: tree -> forest, ground stays
    if "forest" in base and "tree" not in base:
        base["tree"] = base["forest"]
    if "ground" not in base and "plains" in base:
        base["ground"] = base["plains"]
    base.setdefault("player", "@")
    base["wheat"] = "w"
    base["wheat_trampled"] = "x"
    for sub in _CONFIG.ground_subbiomes:
        base[sub.id] = sub.char
    base["stump"] = _DEFAULT_STUMP.char
    base["terracotta"] = _DEFAULT_MESA_TERRACOTTA.char
    base["gravel"] = _DEFAULT_GRAVEL.char
    base.setdefault("dark_grass", "g")  # retired; old saves only
    return base

# Keep GLYPHS in sync after load (already done in _sync, but also ensure legacy aliases)
GLYPHS = _build_legacy_glyphs()

# ---------------------------------------------------------------------------
# Auto-load on import
# ---------------------------------------------------------------------------
try:
    load_generation_config()
except Exception as _e:
    print(f"[terrain_generation] auto-load failed: {_e}")
    _sync_module_globals()
