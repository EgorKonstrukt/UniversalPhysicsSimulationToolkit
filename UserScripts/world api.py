# demo_api.py — полная демонстрация возможностей world API
def start():
    log("=== Запуск демонстрационного скрипта API ===")

    # 1. Создание объектов
    box = world.create_box(pos=(0, -200), size=(80, 40), mass=2.0, color=(255, 100, 100, 255), name="RedBox")
    circle = world.create_circle(pos=(150, -200), radius=30, mass=1.5, color=(100, 255, 100, 255), name="GreenCircle")
    segment = world.create_segment(a=(-100, -250), b=(100, -250), thickness=5, mass=3.0, color=(100, 100, 255, 255),
                                   name="BlueSegment")

    # Статические объекты
    world.create_static_box(pos=(0, 300), size=(1200, 40), name="Ground")
    world.create_static_circle(pos=(400, 0), radius=50, name="StaticObstacle")
    world.create_static_segment(a=(-300, 100), b=(-100, 100), thickness=4, name="StaticRail")

    # 2. Управление тегами
    world.add_tag(box, "movable")
    world.add_tag(circle, "movable")
    world.add_tag(circle, "round")

    log(f"Теги у circle: {getattr(circle, 'tags', set())}")

    # 3. Поиск объектов
    found = world.find_by_tag("movable")
    log(f"Найдено {len(found)} объектов с тегом 'movable'")

    box_by_name = world.find_by_name("RedBox")
    if box_by_name:
        log("Успешно найден объект по имени: RedBox")

    # 4. Управление физикой и трансформацией
    world.set_mass(box, 5.0)
    world.set_friction(box, 0.9)
    world.set_elasticity(circle, 0.8)
    world.set_color(segment, (200, 100, 255, 200))

    world.apply_impulse(box, (0, -300), point=world.get_position(box))
    world.apply_force(circle, (50, 0))

    # 5. Получение свойств
    log(f"Позиция circle: {world.get_position(circle)}")
    log(f"Угол box: {world.get_angle(box):.2f} рад")
    log(f"Цвет segment: {world.get_color(segment)}")

    # 6. Вложенные скрипты
    child_script_code = '''
def start():
    log("Дочерний скрипт запущен!")
def update(dt):
    if world.get_position(owner)[1] < -500:
        world.delete(owner)
'''
    world.attach_script(box, child_script_code, name="FailsafeScript")

    # 7. Управление симуляцией
    world.set_simulation_speed(1.5)
    log("Скорость симуляции увеличена до 1.5×")

    # 8. Планировщик через PlotterWindow (опционально)
    plotter = PlotterWindow(title="Физические данные", size=(400, 300))
    plotter.add_series("Y-position", lambda: world.get_position(circle)[1])
    plotter.show()


def update(dt):
    circle = world.find_by_name("GreenCircle")
    if circle:
        pos = world.get_position(circle)
        vel = world.get_velocity(circle)
        Gizmos.draw_text(
            position=pos,
            text=f"v: ({vel[0]:.1f}, {vel[1]:.1f})",
            color=(255, 255, 0),
            font_size=20,
            world_space=True,
            duration=2.0
        )


def stop():
    log("=== Демонстрационный скрипт остановлен ===")