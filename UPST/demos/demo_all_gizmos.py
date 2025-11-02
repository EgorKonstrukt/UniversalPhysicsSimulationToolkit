from UPST.gizmos.gizmos_manager import Gizmos

def start():
    print("Starting")


def update(dt):
    Gizmos.draw_text(owner.position, "Hello Gizmos! "+str(dt), color='white', background_color=(0, 0, 0, 180),
                     font_size=20, collision=True, duration=0.1)


    # POINT
    Gizmos.draw_point((0, 0), color='red', size=5, duration=0.1)

    # LINE
    Gizmos.draw_line((-50, -50), (50, 50), color='green', thickness=2, duration=0.1)

    # CIRCLE
    Gizmos.draw_circle((100, 0), radius=30, color='blue', filled=False, thickness=3, duration=0.1)

    # RECT
    Gizmos.draw_rect((-100, 0), width=60, height=40, color='yellow', filled=True, duration=0.1)

    # ARROW
    Gizmos.draw_arrow((100, 100), (100, 150), color='magenta', thickness=2, duration=0.1)

    # CROSS
    Gizmos.draw_cross((0, -100), size=20, color='cyan', thickness=2, duration=-0.1)

    # TEXT
    Gizmos.draw_text((150, 100), "Hello Gizmos!", color='white', background_color=(0, 0, 0, 180),
                     font_size=20, collision=True, duration=0.1)

