import pymunk

def serialize_body(body):
    shapes = []
    for shape in body.shapes:
        if isinstance(shape, pymunk.Circle):
            shapes.append({
                'type': 'circle',
                'radius': shape.radius,
                'offset': tuple(shape.offset),
                'friction': shape.friction,
                'elasticity': shape.elasticity
            })
        elif isinstance(shape, pymunk.Poly):
            shapes.append({
                'type': 'poly',
                'vertices': [tuple(v) for v in shape.get_vertices()],
                'friction': shape.friction,
                'elasticity': shape.elasticity
            })
    return {
        'position': tuple(body.position),
        'angle': body.angle,
        'velocity': tuple(body.velocity),
        'angular_velocity': body.angular_velocity,
        'mass': body.mass,
        'moment': body.moment,
        'body_type': body.body_type,
        'name': getattr(body, 'name', ''),
        'tags': list(getattr(body, 'tags', [])),
        'scripts': getattr(body, '_scripts', []),
        'shapes': shapes
    }

def deserialize_body(data):
    shapes = []
    for s in data['shapes']:
        if s['type'] == 'circle':
            shape = pymunk.Circle(None, s['radius'], s['offset'])
        elif s['type'] == 'poly':
            shape = pymunk.Poly(None, s['vertices'])
        else:
            continue
        shape.friction = s['friction']
        shape.elasticity = s['elasticity']
        shapes.append(shape)
    body = pymunk.Body(data['mass'], data['moment'], body_type=data['body_type'])
    body.position = data['position']
    body.angle = data['angle']
    body.velocity = data['velocity']
    body.angular_velocity = data['angular_velocity']
    for shape in shapes:
        shape.body = body
    body.name = data['name']
    body.tags = set(data['tags'])
    body._scripts = data['scripts']
    return body