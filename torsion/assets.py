"""
torsion.assets — Mesh / Material / Texture abstractions.

Goal: MTT code never touches Panda3D directly.

    mesh = Mesh.cube(size=1)
    mesh = Mesh.from_file("assets/models/truck.glb")
    mat = Material.albedo(Color.from_hex("#cc4444"), roughness=0.6)

Backends lazily convert these to Panda3D objects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .math import Color, Vec3


@dataclass
class Texture:
    path: str
    srgb: bool = True

    @staticmethod
    def from_file(path: str, srgb: bool = True) -> Texture:
        return Texture(path=str(path), srgb=srgb)

    def exists(self) -> bool:
        return Path(self.path).exists()

    def __repr__(self) -> str:
        return f"Texture('{self.path}')"


@dataclass
class Material:
    name: str = "default"
    albedo: Color = field(default_factory=lambda: Color(0.8, 0.8, 0.8, 1))
    roughness: float = 0.5
    metallic: float = 0.0
    emissive: Color = field(default_factory=lambda: Color(0, 0, 0, 1))
    albedo_texture: Optional[Texture] = None
    normal_texture: Optional[Texture] = None

    @staticmethod
    def albedo(color: Color, roughness: float = 0.5, metallic: float = 0.0) -> Material:
        return Material(albedo=color, roughness=roughness, metallic=metallic)

    @staticmethod
    def from_color_hex(hex_str: str) -> Material:
        return Material(albedo=Color.from_hex(hex_str))

    def with_texture(self, texture: Texture | str) -> Material:
        if isinstance(texture, str):
            texture = Texture.from_file(texture)
        self.albedo_texture = texture
        return self

    def __repr__(self) -> str:
        return f"Material('{self.name}', albedo={self.albedo}, rough={self.roughness})"


@dataclass
class Mesh:
    """Geometry handle. No vertex data stored yet — backend loads it."""

    source: str  # file path OR primitive id like "cube:1.0"
    material: Material = field(default_factory=Material)
    cast_shadows: bool = True
    receive_shadows: bool = True

    # -- primitives (instant, no files needed) --
    @staticmethod
    def cube(size: float = 1.0, material: Material | None = None) -> Mesh:
        return Mesh(source=f"cube:{size}", material=material or Material())

    @staticmethod
    def sphere(radius: float = 0.5, material: Material | None = None) -> Mesh:
        return Mesh(source=f"sphere:{radius}", material=material or Material())

    @staticmethod
    def plane(size: float = 10.0, material: Material | None = None) -> Mesh:
        return Mesh(source=f"plane:{size}", material=material or Material())

    @staticmethod
    def from_file(path: str, material: Material | None = None) -> Mesh:
        """Load glTF / .glb / .obj / .bam — extension decides backend loader."""
        return Mesh(source=str(path), material=material or Material())

    def with_material(self, material: Material) -> Mesh:
        self.material = material
        return self

    @property
    def is_primitive(self) -> bool:
        return ":" in self.source and not Path(self.source).exists()

    @property
    def is_file(self) -> bool:
        return not self.is_primitive

    def __repr__(self) -> str:
        return f"Mesh('{self.source}')"
