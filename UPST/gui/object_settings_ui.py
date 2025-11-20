import pygame
import pygame_gui

class ObjectSettingsUI:
    def __init__(self, manager):
        self.manager = manager
        self.rect_win = self._create_window("Rectangle Settings", "sprites/gui/spawn/rectangle.png")
        self.circle_win = self._create_window("Circle Settings", "sprites/gui/spawn/circle.png")
        self.tri_win = self._create_window("Triangle Settings", "sprites/gui/spawn/triangle.png")
        self.poly_win = self._create_window("Polyhedron Settings", "sprites/gui/spawn/polyhedron.png")
        self._create_rectangle_inputs()
        self._create_circle_inputs()
        self._create_triangle_inputs()
        self._create_polyhedron_inputs()
        self._create_color_controls()
        # Initialize private attributes first
        self._rect_color_btn = None
        self._circle_color_btn = None
        self._tri_color_btn = None
        self._poly_color_btn = None
        self._rect_rand_cb = None
        self._circle_rand_cb = None
        self._tri_rand_cb = None
        self._poly_rand_cb = None
        self._rect_rand_img = None
        self._circle_rand_img = None
        self._tri_rand_img = None
        self._poly_rand_img = None
        # Create color controls after initializing private attributes
        self._create_color_controls()
        # Expose attributes for UIManager compatibility
        self.rect_color_btn = self._rect_color_btn
        self.circle_color_btn = self._circle_color_btn
        self.tri_color_btn = self._tri_color_btn
        self.poly_color_btn = self._poly_color_btn
        self.rect_rand_cb = self._rect_rand_cb
        self.circle_rand_cb = self._circle_rand_cb
        self.tri_rand_cb = self._tri_rand_cb
        self.poly_rand_cb = self._poly_rand_cb
        self.rect_rand_img = self._rect_rand_img
        self.circle_rand_img = self._circle_rand_img
        self.tri_rand_img = self._tri_rand_img
        self.poly_rand_img = self._poly_rand_img

    def _create_window(self, title, img_path):
        window = pygame_gui.elements.UIWindow(pygame.Rect(200,10,400,300), manager=self.manager, window_display_title=title)
        pygame_gui.elements.UIImage(relative_rect=pygame.Rect(215,5,50,50), image_surface=pygame.image.load(img_path), container=window, manager=self.manager)
        return window

    def _create_common_inputs(self, window):
        inputs = {}
        inputs['friction_label'] = pygame_gui.elements.UILabel(relative_rect=pygame.Rect(5,55,80,20), text="Friction:", container=window, manager=self.manager)
        inputs['friction_entry'] = pygame_gui.elements.UITextEntryLine(initial_text="0.7", relative_rect=pygame.Rect(80,55,100,20), container=window, manager=self.manager)
        inputs['elasticity_label'] = pygame_gui.elements.UILabel(relative_rect=pygame.Rect(5,75,85,20), text="Elasticity:", container=window, manager=self.manager)
        inputs['elasticity_entry'] = pygame_gui.elements.UITextEntryLine(initial_text="0.5", relative_rect=pygame.Rect(90,75,105,20), container=window, manager=self.manager)
        return inputs

    def _create_rectangle_inputs(self):
        self.rect_inputs = self._create_common_inputs(self.rect_win)
        self.rect_inputs['size_x_label'] = pygame_gui.elements.UILabel(relative_rect=pygame.Rect(10,10,20,20), text="X:", container=self.rect_win, manager=self.manager)
        self.rect_inputs['size_x_entry'] = pygame_gui.elements.UITextEntryLine(initial_text="30", relative_rect=pygame.Rect(30,10,100,20), container=self.rect_win, manager=self.manager)
        self.rect_inputs['size_y_label'] = pygame_gui.elements.UILabel(relative_rect=pygame.Rect(10,30,20,20), text="Y:", container=self.rect_win, manager=self.manager)
        self.rect_inputs['size_y_entry'] = pygame_gui.elements.UITextEntryLine(initial_text="30", relative_rect=pygame.Rect(30,30,100,20), container=self.rect_win, manager=self.manager)

    def _create_circle_inputs(self):
        self.circle_inputs = self._create_common_inputs(self.circle_win)
        self.circle_inputs['radius_label'] = pygame_gui.elements.UILabel(relative_rect=pygame.Rect(10,10,20,20), text="R:", container=self.circle_win, manager=self.manager)
        self.circle_inputs['radius_entry'] = pygame_gui.elements.UITextEntryLine(initial_text="30", relative_rect=pygame.Rect(30,10,100,20), container=self.circle_win, manager=self.manager)

    def _create_triangle_inputs(self):
        self.tri_inputs = self._create_common_inputs(self.tri_win)
        self.tri_inputs['size_label'] = pygame_gui.elements.UILabel(relative_rect=pygame.Rect(10,10,50,20), text="Size:", container=self.tri_win, manager=self.manager)
        self.tri_inputs['size_entry'] = pygame_gui.elements.UITextEntryLine(initial_text="30", relative_rect=pygame.Rect(60,10,100,20), container=self.tri_win, manager=self.manager)

    def _create_polyhedron_inputs(self):
        self.poly_inputs = self._create_common_inputs(self.poly_win)
        self.poly_inputs['size_label'] = pygame_gui.elements.UILabel(relative_rect=pygame.Rect(10,10,50,20), text="Size:", container=self.poly_win, manager=self.manager)
        self.poly_inputs['size_entry'] = pygame_gui.elements.UITextEntryLine(initial_text="30", relative_rect=pygame.Rect(60,10,100,20), container=self.poly_win, manager=self.manager)
        self.poly_inputs['faces_label'] = pygame_gui.elements.UILabel(relative_rect=pygame.Rect(10,30,50,20), text="Faces:", container=self.poly_win, manager=self.manager)
        self.poly_inputs['faces_entry'] = pygame_gui.elements.UITextEntryLine(initial_text="6", relative_rect=pygame.Rect(60,30,100,20), container=self.poly_win, manager=self.manager)

    def _create_color_controls(self):
        shapes = [('rectangle', self.rect_win), ('circle', self.circle_win), ('triangle', self.tri_win), ('polyhedron', self.poly_win)]
        for shape, window in shapes:
            panel = pygame_gui.elements.UIPanel(relative_rect=pygame.Rect(5,100,200,60), manager=self.manager, container=window)
            btn = pygame_gui.elements.UIButton(relative_rect=pygame.Rect(5,5,100,25), text="Pick Color", manager=self.manager, container=panel)
            cb = pygame_gui.elements.UIButton(relative_rect=pygame.Rect(5,32,20,20), text="", manager=self.manager, container=panel, tool_tip_text="Random color")
            pygame_gui.elements.UILabel(relative_rect=pygame.Rect(28,32,100,20), text="Random", container=panel, manager=self.manager)
            img = pygame_gui.elements.UIImage(relative_rect=pygame.Rect(5,32,20,20), image_surface=pygame.image.load("sprites/gui/checkbox_true.png"), container=panel, manager=self.manager)
            # Set private attributes to avoid naming conflicts
            setattr(self, f"_{shape}_color_btn", btn)
            setattr(self, f"_{shape}_rand_cb", cb)
            setattr(self, f"_{shape}_rand_img", img)