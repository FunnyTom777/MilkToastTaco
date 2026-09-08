"""
torsion.scene — Scene graph + Entity.

Minimal ECS-like scene so MTT gameplay code stays simple:

    scene = Scene(name="farm")
    e = scene.spawn(Mesh.cube(), position=(0,0,0))
    e.transform.translate(Vec3(1,0,0))
    scene.add(PerspectiveCamera(position=(0,5,10)))
    scene.add(DirectionalLight(direction=Vec3(-1,-1,0)))

Scene owns entities; App owns scene + renderer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterator

from .assets import Mesh
from .transform import Transform
from .math import Vec3, Quat
from .camera import Camera
from .light import Light


_next_entity_id = 1


def _alloc_id() -> int:
    global _next_entity_id
    eid = _next_entity_id
    _next_entity_id += 1
    return eid


@dataclass
class Entity:
    name: str = "entity"
    transform: Transform = field(default_factory=Transform)
    mesh: Mesh | None = None
    camera: Camera | None = None
    light: Light | None = None
    tags: set[str] = field(default_factory=set)
    meta: dict[str, Any] = field(default_factory=dict)
    children: list[Entity] = field(default_factory=list)
    parent: Entity | None = field(default=None, repr=False)
    id: int = field(default_factory=_alloc_id)
    visible: bool = True
    _destroyed: bool = field(default=False, repr=False)

    def add_child(self, child: Entity) -> Entity:
        child.parent = self
        self.children.append(child)
        return child

    def remove_child(self, child: Entity) -> None:
        if child in self.children:
            child.parent = None
            self.children.remove(child)

    def destroy(self) -> None:
        self._destroyed = True
        for c in list(self.children):
            c.destroy()
        if self.parent:
            self.parent.remove_child(self)

    def find(self, name: str) -> Entity | None:
        if self.name == name:
            return self
        for c in self.children:
            hit = c.find(name)
            if hit:
                return hit
        return None

    def __repr__(self) -> str:
        kind = "mesh" if self.mesh else "camera" if self.camera else "light" if self.light else "empty"
        return f"Entity#{self.id}('{self.name}', {kind}, pos={self.transform.position})"


class Scene:
    """
    Container for all entities. Keeps flat list + hierarchy.
    """

    def __init__(self, name: str = "scene"):
        self.name = name
        self.entities: list[Entity] = []
        self._by_id: dict[int, Entity] = {}
        # quick access
        self.main_camera: Camera | None = None
        self._ambient_color = None  # set via set_ambient()

    # -- adding ---------------------------------------------------------------
    def add(self, obj: Entity | Mesh | Camera | Light, **kwargs) -> Entity:
        """
        Smart add:
            scene.add(entity)
            scene.add(Mesh.cube())
            scene.add(PerspectiveCamera(...))
            scene.add(DirectionalLight(...))
        Returns the created Entity.
        """
        if isinstance(obj, Entity):
            entity = obj
        elif isinstance(obj, Mesh):
            entity = Entity(
                name=kwargs.pop("name", f"mesh_{obj.source}"),
                mesh=obj,
                transform=kwargs.pop("transform", Transform(
                    position=kwargs.pop("position", None),
                    rotation=kwargs.pop("rotation", None),
                    scale=kwargs.pop("scale", None),
                )),
                tags=set(kwargs.pop("tags", [])),
            )
        elif isinstance(obj, Camera):
            entity = Entity(name=kwargs.pop("name", "camera"), camera=obj, transform=obj.transform)
            if self.main_camera is None:
                self.main_camera = obj
        elif isinstance(obj, Light):
            entity = Entity(name=kwargs.pop("name", "light"), light=obj, transform=obj.transform)
        else:
            raise TypeError(f"Scene.add() got unsupported type {type(obj).__name__}")

        # extra kwargs -> meta
        if kwargs:
            entity.meta.update(kwargs)

        self.entities.append(entity)
        self._by_id[entity.id] = entity
        return entity

    def spawn(
        self,
        mesh: Mesh | None = None,
        *,
        name: str | None = None,
        position: Vec3 | tuple | None = None,
        rotation: Quat | tuple | None = None,
        scale: Vec3 | tuple | None = None,
        parent: Entity | None = None,
        **meta,
    ) -> Entity:
        """Shorthand for creating a mesh entity."""
        t = Transform(position=position, rotation=rotation, scale=scale)
        e = Entity(name=name or f"entity_{_alloc_id()}", transform=t, mesh=mesh, meta=meta)
        if parent:
            parent.add_child(e)
        else:
            self.entities.append(e)
        self._by_id[e.id] = e
        return e

    def create_empty(self, name: str = "empty", **kwargs) -> Entity:
        return self.spawn(None, name=name, **kwargs)

    # -- query ----------------------------------------------------------------
    def get(self, entity_id: int) -> Entity | None:
        return self._by_id.get(entity_id)

    def find(self, name: str) -> Entity | None:
        for e in self.entities:
            hit = e.find(name)
            if hit:
                return hit
        return None

    def with_tag(self, tag: str) -> list[Entity]:
        out: list[Entity] = []
        for e in self.entities:
            stack = [e]
            while stack:
                cur = stack.pop()
                if tag in cur.tags:
                    out.append(cur)
                stack.extend(cur.children)
        return out

    def remove(self, entity: Entity) -> None:
        entity.destroy()
        if entity in self.entities:
            self.entities.remove(entity)
        self._by_id.pop(entity.id, None)

    def clear(self) -> None:
        self.entities.clear()
        self._by_id.clear()
        self.main_camera = None

    # -- iteration ------------------------------------------------------------
    def __iter__(self) -> Iterator[Entity]:
        return iter(self.entities)

    def __len__(self) -> int:
        return len(self.entities)

    def __repr__(self) -> str:
        return f"Scene('{self.name}', {len(self.entities)} entities)"

    # -- ambient --------------------------------------------------------------
    def set_ambient(self, color, intensity: float = 0.3) -> None:
        from .math import Color
        if isinstance(color, str):
            color = Color.from_hex(color)
        self._ambient_color = (color, float(intensity))

    # -- serialization helper (for save system) -------------------------------
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "count": len(self.entities),
            "entities": [
                {"id": e.id, "name": e.name, "pos": e.transform.position.to_tuple()}
                for e in self.entities
            ],
        }
