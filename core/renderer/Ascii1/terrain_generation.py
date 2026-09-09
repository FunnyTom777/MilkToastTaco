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
    scale: float = 0.05
    octaves: int = 3
    persistence: float = 0.5
    lacunarity: float = 2.0
    seed_offset: int = 0
    fallback_scale: float = 0.1

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
class GenerationConfig:
    chunk_size: int = 16
    seed: int = 0
    save_dir: str = "saves_world1"
    noise: NoiseConfig = field(default_factory=NoiseConfig)
    biomes: List[BiomeRule] = field(default_factory=list)
    variants: Dict[str, List[Variant]] = field(default_factory=dict)
    scatter: List[ScatterFeature] = field(default_factory=list)
    palette: Dict[str, Tuple[int, int, int]] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Defaults (mirrors old ascii.py hardcoded behaviour + small built-in variation)
# ---------------------------------------------------------------------------

_DEFAULT_BIOMES: List[BiomeRule] = [
    BiomeRule("water",    -0.15, "~", (65, 105, 225), False, "Water"),
    BiomeRule("ground",    0.20, ".", (34, 139, 34),  True,  "Plains"),
    BiomeRule("forest",    0.35, "T", (0, 100, 0),    False, "Forest"),
    BiomeRule("mountain",  1.0,  "^", (139, 137, 137), False, "Mountain"),
]

_DEFAULT_VARIANTS: Dict[str, List[Variant]] = {
    "ground":   [Variant(".", 70), Variant(",", 15), Variant("`", 10), Variant("'", 5)],
    "forest":   [Variant("T", 60), Variant("t", 25), Variant("*", 15)],
    "mountain": [Variant("^", 65), Variant("M", 20), Variant("A", 15)],
    "water":    [Variant("~", 80), Variant("-", 12), Variant("=", 8)],
}

_DEFAULT_SCATTER: List[ScatterFeature] = [
    ScatterFeature("ground",   "*", (50, 205, 50),  0.015, True),
    ScatterFeature("ground",   "o", (139, 69, 19),  0.008, True),
    ScatterFeature("ground",   "%", (255, 215, 0),  0.005, True),
    ScatterFeature("mountain", "#", (105, 105, 105), 0.02, False),
    ScatterFeature("water",    "=", (0, 191, 255),  0.01,  False),
]

_DEFAULT_PALETTE: Dict[str, Tuple[int, int, int]] = {
    "bg":        (15, 15, 20),
    "dark_gray": (40, 40, 50),
    "player":    (255, 215, 0),
    "text":      (220, 220, 220),
}

_DEFAULT_NOISE = NoiseConfig()

# ---------------------------------------------------------------------------
# Module globals (mutable via load_generation_config)
# ---------------------------------------------------------------------------

_CONFIG: GenerationConfig = GenerationConfig(
    chunk_size=16,
    seed=0,
    save_dir="saves_world1",
    noise=NoiseConfig(),
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
    global COLOR_GROUND, COLOR_TREE, COLOR_MOUNTAIN, COLOR_WATER

    CHUNK_SIZE = _CONFIG.chunk_size
    SAVE_DIR = _CONFIG.save_dir
    GLYPHS = {b.id: b.char for b in _CONFIG.biomes}
    GLYPHS["player"] = "@"
    COLORS = {b.id: b.color for b in _CONFIG.biomes}
    PALETTE = dict(_CONFIG.palette)

    COLOR_BG = PALETTE.get("bg", (15, 15, 20))
    COLOR_DARK_GRAY = PALETTE.get("dark_gray", (40, 40, 50))
    COLOR_PLAYER = PALETTE.get("player", (255, 215, 0))
    COLOR_TEXT = PALETTE.get("text", (220, 220, 220))
    COLOR_GROUND = COLORS.get("ground", COLORS.get("plains", (34, 139, 34)))
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
    def __init__(self, char: str, color: Tuple[int, int, int], walkable: bool):
        self.char = char
        self.color = color
        self.walkable = walkable

    def __repr__(self):
        return f"Tile({self.char!r}, {self.color}, walkable={self.walkable})"


def get_terrain_type(wx: int, wy: int) -> Tuple[str, Tuple[int, int, int], bool]:
    """
    Procedural terrain for world coord (wx, wy).
    Returns (char, color, walkable).
    Deterministic — same coords always give same result for same config.
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

    # Base char/color/walkable from biome
    char = biome.char
    color = biome.color
    walkable = biome.walkable

    # Variant glyph (keeps color/walkable)
    var_char = _pick_variant(biome.id, wx, wy)
    if var_char is not None:
        char = var_char

    # Scatter override — may change char/color/walkable
    scatter = _maybe_scatter(biome.id, wx, wy)
    if scatter is not None:
        char = scatter.char
        color = scatter.color
        if scatter.walkable is not None:
            walkable = scatter.walkable

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
