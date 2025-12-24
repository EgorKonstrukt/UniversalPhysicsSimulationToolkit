# UPST/modules/hierarchy.py
import pymunk
from typing import Optional, List, Any

class HierarchyNode:
    def __init__(self, name: str = "Object", body: Optional[pymunk.Body] = None):
        self.name = name
        self.body = body
        self.parent: Optional['HierarchyNode'] = None
        self.children: List['HierarchyNode'] = []
        self._local_position = pymunk.Vec2d(0, 0)
        self._local_angle = 0.0

    @property
    def local_position(self) -> pymunk.Vec2d:
        return self._local_position

    @local_position.setter
    def local_position(self, value: pymunk.Vec2d):
        self._local_position = pymunk.Vec2d(*value)
        self._update_world_transform()

    @property
    def local_angle(self) -> float:
        return self._local_angle

    @local_angle.setter
    def local_angle(self, value: float):
        self._local_angle = float(value)
        self._update_world_transform()

    def _update_world_transform(self):
        if self.parent:
            parent_pos = self.parent.body.position if self.parent.body else pymunk.Vec2d(0, 0)
            parent_angle = self.parent.body.angle if self.parent.body else 0.0
            rot = pymunk.Transform.rotation(parent_angle)
            world_pos = parent_pos + rot @ self._local_position
            world_angle = parent_angle + self._local_angle
            if self.body:
                self.body.position = world_pos
                self.body.angle = world_angle
        else:
            if self.body:
                self.body.position = self._local_position
                self.body.angle = self._local_angle

    def set_parent(self, new_parent: Optional['HierarchyNode']):
        if self.parent:
            self.parent.children.remove(self)
        self.parent = new_parent
        if new_parent:
            new_parent.children.append(self)
        self._update_world_transform()

    def world_position(self) -> pymunk.Vec2d:
        return self.body.position if self.body else self._local_position

    def world_angle(self) -> float:
        return self.body.angle if self.body else self._local_angle