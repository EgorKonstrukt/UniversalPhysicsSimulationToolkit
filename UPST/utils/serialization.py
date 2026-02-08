import pymunk
import uuid
from typing import List, Dict, Any, Tuple

from UPST.utils.utils import surface_to_bytes


def serialize_shape(shape) -> Dict[str, Any]:
    base = {
        'friction': float(getattr(shape, 'friction', 0.5)),
        'elasticity': float(getattr(shape, 'elasticity', 0.0)),
        'color': getattr(shape, 'color', (200, 200, 200, 255))
    }
    if isinstance(shape, pymunk.Circle):
        return {**base, 'type': 'Circle', 'radius': float(shape.radius), 'offset': tuple(getattr(shape, 'offset', (0.0, 0.0)))}
    elif isinstance(shape, pymunk.Poly):
        return {**base, 'type': 'Poly', 'vertices': [tuple(v) for v in shape.get_vertices()]}
    elif isinstance(shape, pymunk.Segment):
        return {**base, 'type': 'Segment', 'a': tuple(shape.a), 'b': tuple(shape.b), 'radius': float(shape.radius)}
    else:
        raise ValueError(f"Unsupported shape type: {type(shape)}")

def deserialize_shape(data: Dict[str, Any], body=None) -> pymunk.Shape:
    st = data['type']
    if st == 'Circle':
        shp = pymunk.Circle(body, float(data['radius']), tuple(data.get('offset', (0.0, 0.0))))
    elif st == 'Poly':
        shp = pymunk.Poly(body, [pymunk.Vec2d(*v) for v in data['vertices']])
    elif st == 'Segment':
        shp = pymunk.Segment(body, pymunk.Vec2d(*data['a']), pymunk.Vec2d(*data['b']), float(data['radius']))
    else:
        raise ValueError(f"Unknown shape type: {st}")
    shp.friction = float(data.get('friction', 0.5))
    shp.elasticity = float(data.get('elasticity', 0.0))
    shp.color = tuple(data.get('color', (200, 200, 200, 255)))
    return shp

def serialize_body(body, app_renderer=None) -> Dict[str, Any]:
    shapes_data = [serialize_shape(s) for s in body.shapes]
    tex_bytes, tex_size = None, None
    if app_renderer and hasattr(body, 'texture_path'):
        surf = app_renderer._get_texture(getattr(body, 'texture_path', None))
        if surf:
            tex_bytes, tex_size = surface_to_bytes(surf), surf.get_size()
    return {
        '_script_uuid': str(getattr(body, '_script_uuid', uuid.uuid4())),
        'name': str(getattr(body, 'name', 'Body')),
        'color': tuple(getattr(body, 'color', (200, 200, 200, 255))),
        'position': tuple(body.position),
        'angle': float(body.angle),
        'velocity': tuple(body.velocity),
        'angular_velocity': float(body.angular_velocity),
        'mass': float(getattr(body, 'mass', 1.0)),
        'moment': float(getattr(body, 'moment', 1.0)),
        'body_type': int(body.body_type),
        'shapes': shapes_data,
        'texture_path': getattr(body, 'texture_path', None),
        'texture_bytes': tex_bytes,
        'texture_size': tex_size,
        'texture_scale': float(getattr(body, 'texture_scale', 1.0)),
        'stretch_texture': bool(getattr(body, 'stretch_texture', True)),
        'center_of_gravity': tuple(body.center_of_gravity)
    }

def deserialize_body(data: Dict[str, Any]) -> Tuple[pymunk.Body, List[pymunk.Shape]]:
    bt = pymunk.Body(body_type=int(data.get('body_type', pymunk.Body.DYNAMIC)))
    try:
        bt._script_uuid = uuid.UUID(data['_script_uuid'])
    except:
        bt._script_uuid = uuid.uuid4()
    if bt.body_type == pymunk.Body.DYNAMIC:
        bt.mass = float(data.get('mass', 1.0))
        bt.moment = float(data.get('moment', 1.0))
        bt.name = data.get('name', 'Body')
        bt.color = tuple(data.get('color', (255, 255, 255, 255)))
        bt.position = pymunk.Vec2d(*data.get('position', (0.0, 0.0)))
        bt.angle = float(data.get('angle', 0.0))
        bt.velocity = pymunk.Vec2d(*data.get('velocity', (0.0, 0.0)))
        bt.angular_velocity = float(data.get('angular_velocity', 0.0))
        cog = data.get('center_of_gravity')
        if cog:
            bt.center_of_gravity = pymunk.Vec2d(*cog)
        bt.texture_path = data.get('texture_path')
        bt.texture_bytes = data.get('texture_bytes')
        bt.texture_size = data.get('texture_size')
        bt.texture_scale = float(data.get('texture_scale', 1.0))
        bt.stretch_texture = bool(data.get('stretch_texture', True))
    shapes = [deserialize_shape(sd, bt) for sd in data.get('shapes', [])]
    return bt, shapes

def serialize_static_line(line) -> Dict[str, Any]:
    base = {
        'friction': float(getattr(line, 'friction', 0.5)),
        'elasticity': float(getattr(line, 'elasticity', 0.0)),
        'color': getattr(line, 'color', (200, 200, 200, 255))
    }
    if isinstance(line, pymunk.Poly):
        return {**base, 'type': 'Poly', 'vertices': [tuple(v) for v in line.get_vertices()]}
    elif isinstance(line, pymunk.Segment):
        return {**base, 'type': 'Segment', 'a': tuple(line.a), 'b': tuple(line.b), 'radius': float(line.radius)}
    else:
        raise ValueError(f"Unsupported static line type: {type(line)}")

def deserialize_static_line(data: Dict[str, Any], static_body: pymunk.Body) -> pymunk.Shape:
    if data['type'] == 'Poly':
        line = pymunk.Poly(static_body, [pymunk.Vec2d(*v) for v in data['vertices']])
    elif data['type'] == 'Segment':
        line = pymunk.Segment(static_body, pymunk.Vec2d(*data['a']), pymunk.Vec2d(*data['b']), float(data['radius']))
    else:
        raise ValueError(f"Unknown static line type: {data['type']}")
    line.friction = float(data.get('friction', 0.5))
    line.elasticity = float(data.get('elasticity', 0.0))
    line.color = tuple(data.get('color', (200, 200, 200, 255)))
    return line