
def start():
    self.phase=0.0

def update(dt):
    position=owner.position

    self.phase += dt
    cx, cy = position
    angle_xy = self.phase * 0.3
    angle_xz = self.phase * 0.4
    angle_xw = self.phase * 0.5
    angle_yz = self.phase * 0.6
    angle_yw = self.phase * 0.7
    angle_zw = self.phase * 0.8

    vertices = []
    for w in [-1, 1]:
        for z in [-1, 1]:
            for y in [-1, 1]:
                for x in [-1, 1]:
                    vertices.append([x, y, z, w])

    def rotate(p, a, b, angle):
        c, s = math.cos(angle), math.sin(angle)
        pa, pb = p[a], p[b]
        p[a] = pa * c - pb * s
        p[b] = pa * s + pb * c

    def project_4d_to_2d(point):
        p = point[:]
        rotate(p, 0, 1, angle_xy)
        rotate(p, 0, 2, angle_xz)
        rotate(p, 0, 3, angle_xw)
        rotate(p, 1, 2, angle_yz)
        rotate(p, 1, 3, angle_yw)
        rotate(p, 2, 3, angle_zw)

        x, y, z, w = p
        scale = 500 / (4 - w)
        sx = (x * scale) + cx
        sy = (y * scale) + cy
        sz = (z * scale)
        return (sx, sy, sz)

    projected = [project_4d_to_2d(v) for v in vertices]

    edges = []
    for i in range(len(vertices)):
        for j in range(i + 1, len(vertices)):
            diff = sum(abs(vertices[i][k] - vertices[j][k]) for k in range(4))
            if diff == 2:
                edges.append((i, j))

    for a, b in edges:
        x1, y1, z1 = projected[a]
        x2, y2, z2 = projected[b]

        depth = (z1 + z2) / 2
        brightness = max(0.3, 1.0 - abs(depth) / 200)

        if vertices[a][3] == vertices[b][3]:
            if vertices[a][3] == 1:
                color = (int(255 * brightness), int(100 * brightness), int(100 * brightness))
            else:
                color = (int(100 * brightness), int(100 * brightness), int(255 * brightness))
        else:
            color = (int(100 * brightness), int(255 * brightness), int(100 * brightness))

        thickness = max(6, int(10 * brightness))

        Gizmos.draw_line((x1, y1), (x2, y2), color=color, thickness=thickness, duration=0.1)

    for i, (x, y, z) in enumerate(projected):
        w_coord = vertices[i][3]
        if w_coord == 1:
            vertex_color = (255, 150, 150)
        else:
            vertex_color = (150, 150, 255)

        depth_factor = max(0.4, 1.0 - abs(z) / 200)
        radius = int(16 * depth_factor)

        adjusted_color = (
            int(vertex_color[0] * depth_factor),
            int(vertex_color[1] * depth_factor),
            int(vertex_color[2] * depth_factor)
        )

        Gizmos.draw_circle((x, y), radius, color=adjusted_color, duration=0.1)