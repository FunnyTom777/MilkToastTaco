"""
torsion.primitives — convenience primitive factories that return Entities.

    from torsion.primitives import Cube, Sphere, Ground

    scene.add(Cube(position=(0,1,0), size=2, color="#ff4422"))
"""

from __future__ import annotations

from .assets import Mesh, Material
from .math import Color
from .scene import Entity
from .transform import Transform


def _mat(color) -> Material:
    if color is None:
        return Material()
    if isinstance(color, str):
        color = Color.from_hex(color)
    if isinstance(color, Color):
        return Material.albedo(color)
    return color  # assume Material


def Cube(position=(0, 0, 0), size=1.0, color=None, **kwargs) -> Entity:
    return Entity(
        name=kwargs.pop("name", "cube"),
        mesh=Mesh.cube(size=size, material=_mat(color)),
        transform=Transform(position=position, rotation=kwargs.pop("rotation", None), scale=kwargs.pop("scale", None)),
        **kwargs,
    )


def Sphere(position=(0, 0, 0), radius=0.5, color=None, **kwargs) -> Entity:
    return Entity(
        name=kwargs.pop("name", "sphere"),
        mesh=Mesh.sphere(radius=radius, material=_mat(color)),
        transform=Transform(position=position),
        **kwargs,
    )


def Ground(size=50.0, color="#3a7d44", **kwargs) -> Entity:
    return Entity(
        name=kwargs.pop("name", "ground"),
        mesh=Mesh.plane(size=size, material=_mat(color)),
        transform=Transform(position=kwargs.pop("position", (0, 0, 0))),
        **kwargs,
    )


def Plane(**kwargs) -> Entity:
    return Ground(**kwargs)
