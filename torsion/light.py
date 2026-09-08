"""
torsion.light — Light components.

    sun = DirectionalLight(direction=Vec3(-0.5, -1, -0.3), intensity=1.0)
    bulb = PointLight(position=Vec3(0,3,0), radius=10, color=Color.WHITE)
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .math import Vec3, Color
from .transform import Transform


@dataclass
class Light:
    color: Color = field(default_factory=lambda: Color.WHITE)
    intensity: float = 1.0
    cast_shadows: bool = True
    transform: Transform = field(default_factory=Transform)


@dataclass
class DirectionalLight(Light):
    direction: Vec3 = field(default_factory=lambda: Vec3(0, -1, 0))

    def __init__(
        self,
        direction: Vec3 | tuple = (0, -1, 0),
        color: Color | None = None,
        intensity: float = 1.0,
        cast_shadows: bool = True,
    ):
        super().__init__(color=color or Color.WHITE, intensity=intensity, cast_shadows=cast_shadows)
        self.direction = direction if isinstance(direction, Vec3) else Vec3(*direction)
        # keep transform in sync for backends that use it
        if self.direction.length_squared() > 0:
            # point transform to look along direction
            self.transform.look_at(self.transform.position + self.direction)

    def __repr__(self) -> str:
        return f"DirectionalLight(dir={self.direction}, intensity={self.intensity})"


@dataclass
class PointLight(Light):
    radius: float = 10.0
    position: Vec3 = field(default_factory=Vec3.zero)

    def __init__(
        self,
        position: Vec3 | tuple = (0, 0, 0),
        radius: float = 10.0,
        color: Color | None = None,
        intensity: float = 1.0,
        cast_shadows: bool = False,
    ):
        super().__init__(color=color or Color.WHITE, intensity=intensity, cast_shadows=cast_shadows)
        self.position = position if isinstance(position, Vec3) else Vec3(*position)
        self.radius = float(radius)
        self.transform.position = self.position

    def __repr__(self) -> str:
        return f"PointLight(pos={self.position}, radius={self.radius})"


@dataclass
class SpotLight(Light):
    position: Vec3 = field(default_factory=Vec3.zero)
    direction: Vec3 = field(default_factory=lambda: Vec3(0, -1, 0))
    inner_angle_deg: float = 20.0
    outer_angle_deg: float = 30.0
    radius: float = 20.0

    def __init__(
        self,
        position: Vec3 | tuple = (0, 0, 0),
        direction: Vec3 | tuple = (0, -1, 0),
        inner_angle_deg: float = 20.0,
        outer_angle_deg: float = 30.0,
        radius: float = 20.0,
        color: Color | None = None,
        intensity: float = 1.0,
    ):
        super().__init__(color=color or Color.WHITE, intensity=intensity)
        self.position = position if isinstance(position, Vec3) else Vec3(*position)
        self.direction = direction if isinstance(direction, Vec3) else Vec3(*direction)
        self.inner_angle_deg = float(inner_angle_deg)
        self.outer_angle_deg = float(outer_angle_deg)
        self.radius = float(radius)
        self.transform.position = self.position

    def __repr__(self) -> str:
        return f"SpotLight(pos={self.position}, dir={self.direction})"
