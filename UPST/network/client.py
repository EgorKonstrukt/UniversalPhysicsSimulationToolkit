import pygame
import sys
from typing import Dict, Any, List
from UPST.network.Network import NetworkClient

WIDTH = 800
HEIGHT = 600


class Cube:
    def __init__(self, data: Dict[str, Any]):
        self.id = data["id"]
        self.x = float(data.get("x", 0.0))
        self.y = float(data.get("y", 0.0))
        self.size = float(data.get("size", 50.0))
        self.color = tuple(data.get("color", [255, 255, 255]))
        self.behavior = data.get("behavior", "none")
        self.params = data.get("params", {}) or {}
        self.script = data.get("script", "") or ""
        self.script_error = data.get("script_error")

    def update_from_dict(self, data: Dict[str, Any]) -> None:
        self.x = float(data.get("x", self.x))
        self.y = float(data.get("y", self.y))
        self.size = float(data.get("size", self.size))
        self.color = tuple(data.get("color", self.color))
        self.behavior = data.get("behavior", self.behavior)
        self.params = data.get("params", self.params) or self.params
        if "script" in data:
            self.script = data.get("script") or self.script
        if "script_error" in data:
            self.script_error = data.get("script_error")

    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x), int(self.y), int(self.size), int(self.size))

    def draw(self, screen: pygame.Surface, selected: bool = False) -> None:
        rect = self.rect()
        pygame.draw.rect(screen, self.color, rect)
        if selected:
            pygame.draw.rect(screen, (255, 255, 0), rect, 2)


def pick_cube(cubes: Dict[int, Cube], pos) -> int:
    mx, my = pos
    picked_id = None
    for cube in cubes.values():
        if cube.rect().collidepoint(mx, my):
            picked_id = cube.id
    return picked_id


def edit_script_dialog(screen: pygame.Surface, font: pygame.font.Font, initial_script: str) -> str:
    text = initial_script or ""
    clock = pygame.time.Clock()
    cursor_visible = True
    cursor_timer = 0.0
    while True:
        dt = clock.tick(60) / 1000.0
        cursor_timer += dt
        if cursor_timer >= 0.5:
            cursor_visible = not cursor_visible
            cursor_timer = 0.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return initial_script
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return initial_script
                elif event.key == pygame.K_RETURN:
                    return text
                elif event.key == pygame.K_BACKSPACE:
                    text = text[:-1]
                else:
                    if event.unicode:
                        text += event.unicode
        overlay = pygame.Surface((WIDTH, 120))
        overlay.set_alpha(220)
        overlay.fill((10, 10, 10))
        screen.blit(overlay, (0, HEIGHT // 2 - 60))
        border_rect = pygame.Rect(20, HEIGHT // 2 - 50, WIDTH - 40, 100)
        pygame.draw.rect(screen, (200, 200, 200), border_rect, 2)
        hint1 = "Редактор скрипта куба (одна строка Python)."
        hint2 = "Переменные: x, y, vx, vy, size, dt, params, WORLD_WIDTH, WORLD_HEIGHT."
        hint3 = "Пример: vy += 300*dt; y += vy*dt"
        hint4 = "Enter — сохранить, Esc — отмена."
        y = HEIGHT // 2 - 45
        for line in (hint1, hint2, hint3, hint4):
            surf = font.render(line, True, (220, 220, 220))
            screen.blit(surf, (30, y))
            y += 18
        shown_text = text
        max_chars = 90
        if len(shown_text) > max_chars:
            shown_text = "..." + shown_text[-max_chars:]
        script_surf = font.render(shown_text, True, (255, 255, 0))
        script_pos = (30, HEIGHT // 2 + 20)
        screen.blit(script_surf, script_pos)
        if cursor_visible:
            cursor_x = script_pos[0] + script_surf.get_width() + 3
            cursor_y = script_pos[1]
            pygame.draw.line(
                screen,
                (255, 255, 0),
                (cursor_x, cursor_y),
                (cursor_x, cursor_y + script_surf.get_height()),
                1,
            )
        pygame.display.flip()


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Cube Scene Editor")
    clock = pygame.time.Clock()
    net = NetworkClient()
    try:
        net.connect("127.0.0.1", 9999)
    except OSError as e:
        print("Network error:", e)
        pygame.quit()
        sys.exit(1)
    cubes: Dict[int, Cube] = {}
    selected_id = None
    dragging = False
    drag_offset = (0, 0)
    font = pygame.font.SysFont(None, 20)
    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if selected_id is not None and selected_id in cubes:
                    cube = cubes[selected_id]
                    if event.key == pygame.K_f:
                        cube.behavior = "fall"
                        cube.params.setdefault("vy", 120.0)
                        cube.params.setdefault("gravity", 0.0)
                        net.send(
                            {
                                "type": "edit_cube",
                                "id": cube.id,
                                "behavior": cube.behavior,
                                "params": cube.params,
                            }
                        )
                    elif event.key == pygame.K_b:
                        cube.behavior = "bounce"
                        cube.params.setdefault("vy", -200.0)
                        cube.params.setdefault("gravity", 500.0)
                        net.send(
                            {
                                "type": "edit_cube",
                                "id": cube.id,
                                "behavior": cube.behavior,
                                "params": cube.params,
                            }
                        )
                    elif event.key == pygame.K_n:
                        cube.behavior = "none"
                        net.send({"type": "edit_cube", "id": cube.id, "behavior": cube.behavior})
                    elif event.key == pygame.K_e:
                        screen.fill((30, 30, 30))
                        grid_step = 40
                        for x in range(0, WIDTH, grid_step):
                            pygame.draw.line(screen, (40, 40, 40), (x, 0), (x, HEIGHT))
                        for y in range(0, HEIGHT, grid_step):
                            pygame.draw.line(screen, (40, 40, 40), (0, y), (WIDTH, y))
                        for c in cubes.values():
                            c.draw(screen, selected=(c.id == selected_id))
                        pygame.display.flip()
                        new_script = edit_script_dialog(screen, font, cube.script or "")
                        if new_script != cube.script:
                            cube.script = new_script
                            net.send({"type": "edit_cube", "id": cube.id, "script": cube.script})
                    elif event.key == pygame.K_LEFTBRACKET:
                        vy = float(cube.params.get("vy", 0.0))
                        vy -= 20.0
                        cube.params["vy"] = vy
                        net.send({"type": "edit_cube", "id": cube.id, "params": {"vy": vy}})
                    elif event.key == pygame.K_RIGHTBRACKET:
                        vy = float(cube.params.get("vy", 0.0))
                        vy += 20.0
                        cube.params["vy"] = vy
                        net.send({"type": "edit_cube", "id": cube.id, "params": {"vy": vy}})
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    pos = event.pos
                    pid = pick_cube(cubes, pos)
                    if pid is not None:
                        selected_id = pid
                        cube = cubes[selected_id]
                        dragging = True
                        drag_offset = (cube.x - pos[0], cube.y - pos[1])
                    else:
                        net.send(
                            {
                                "type": "create_cube",
                                "x": pos[0],
                                "y": pos[1],
                                "size": 50.0,
                                "color": [200, 200, 255],
                                "behavior": "none",
                                "params": {},
                                "script": "",
                            }
                        )
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    dragging = False
            elif event.type == pygame.MOUSEMOTION:
                if dragging and selected_id is not None and selected_id in cubes:
                    mx, my = event.pos
                    cube = cubes[selected_id]
                    cube.x = mx + drag_offset[0]
                    cube.y = my + drag_offset[1]
                    net.send({"type": "move_cube", "id": cube.id, "x": cube.x, "y": cube.y})
        msgs: List[Any] = net.poll()
        for msg in msgs:
            if not isinstance(msg, dict):
                continue
            mtype = msg.get("type")
            if mtype in ("init_state", "state"):
                new_map: Dict[int, Cube] = {}
                for obj_data in msg.get("objects", []):
                    oid = obj_data["id"]
                    if oid in cubes:
                        cube = cubes[oid]
                        cube.update_from_dict(obj_data)
                    else:
                        cube = Cube(obj_data)
                    new_map[oid] = cube
                cubes = new_map
                if selected_id is not None and selected_id not in cubes:
                    selected_id = None
            elif mtype == "create":
                obj = msg["object"]
                cubes[obj["id"]] = Cube(obj)
            elif mtype == "update":
                obj = msg["object"]
                oid = obj["id"]
                if oid in cubes:
                    cubes[oid].update_from_dict(obj)
                else:
                    cubes[oid] = Cube(obj)
        screen.fill((30, 30, 30))
        grid_step = 40
        for x in range(0, WIDTH, grid_step):
            pygame.draw.line(screen, (40, 40, 40), (x, 0), (x, HEIGHT))
        for y in range(0, HEIGHT, grid_step):
            pygame.draw.line(screen, (40, 40, 40), (0, y), (WIDTH, y))
        for cube in cubes.values():
            cube.draw(screen, selected=(cube.id == selected_id))
        info_lines = [
            "ЛКМ по пустому — создать куб",
            "ЛКМ по кубу + движение — двигать",
            "F/B/N — fall / bounce / none",
            "[ / ] — изменить vy",
            "E — редактировать кастомный script",
            "ESC — выйти",
        ]
        y = 5
        for line in info_lines:
            text_surf = font.render(line, True, (200, 200, 200))
            screen.blit(text_surf, (5, y))
            y += 18
        if selected_id is not None and selected_id in cubes:
            cube = cubes[selected_id]
            vy = float(cube.params.get("vy", 0.0))
            info = "ID={} | behavior={} | vy={:.1f}".format(cube.id, cube.behavior, vy)
            info_surf = font.render(info, True, (255, 255, 0))
            screen.blit(info_surf, (5, HEIGHT - 40))
            if cube.script:
                script_preview = cube.script
                if len(script_preview) > 60:
                    script_preview = script_preview[:57] + "..."
                script_text = "script: {}".format(script_preview)
                script_surf = font.render(script_text, True, (150, 220, 150))
                screen.blit(script_surf, (5, HEIGHT - 22))
            if cube.script_error:
                err = str(cube.script_error)
                if len(err) > 60:
                    err = err[:57] + "..."
                err_surf = font.render("error: " + err, True, (255, 80, 80))
                screen.blit(err_surf, (5, HEIGHT - 60))
        pygame.display.flip()
    net.close()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
