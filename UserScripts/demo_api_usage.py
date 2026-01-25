# demo_api_usage.py

def start():
    if world is None:
        log("ERROR: 'world' API is not available!")
        return
    log("API demo script started.")
    box = world.create_box(pos=(0, 5), size=(2, 2), mass=1.0, color=(255, 100, 100, 255))
    circle = world.create_circle(pos=(-3, 8), radius=1.0, mass=0.5, color=(100, 255, 100, 255))
    segment = world.create_segment(a=(2, 4), b=(5, 6), thickness=0.2, mass=2.0, color=(100, 100, 255, 255))

    world.add_tag(box, "demo")
    world.add_tag(circle, "demo")
    world.add_tag(segment, "demo")

    world.apply_force(box, (0, -20))
    world.apply_impulse(circle, (15, 0))

    ground = world.create_static_box(pos=(0, -5), size=(20, 1), color=(150, 150, 150, 255))
    wall = world.create_static_segment(a=(-10, -4), b=(-10, 10), thickness=0.3)

    attach_script_to_box(box)

def update(dt):
    if world is None:
        return
    bodies = world.find_by_tag("demo")
    for b in bodies:
        try:
            pos = world.get_position(b)
            if pos[1] < -10:
                world.set_transform(b, pos=(random.uniform(-5, 5), 10))
                world.set_velocity(b, (0, 0))
                world.set_angular_velocity(b, 0)
        except Exception as e:
            log(f"Error updating body: {e}")
            continue

def stop():
    log("API demo script stopped. Cleaning up...")
    for obj in world.find_by_tag("demo"):
        world.delete(obj)
    # Статические объекты не удаляются автоматически — можно оставить или удалить вручную при необходимости

def attach_script_to_box(box):
    code = '''
def start():
    self.color_cycle = 0

def update(dt):
    self.color_cycle += dt
    r = int(128 + 127 * math.sin(self.color_cycle))
    g = int(128 + 127 * math.sin(self.color_cycle + 2))
    b = int(128 + 127 * math.sin(self.color_cycle + 4))
    world.set_color(owner, (r, g, b, 255))
'''
    world.attach_script(box, code, name="ColorPulse")