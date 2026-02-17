import pygame
import pygame_gui
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from UPST.modules.node_graph.node_types import OscillatorNode


class OscillatorConfigWindow(pygame_gui.elements.UIWindow):
    def __init__(self, rect, ui_manager, oscillator_node: 'OscillatorNode', title: str = "Oscillator Settings"):
        super().__init__(rect, ui_manager, window_display_title=title, object_id="#oscillator_config_window")
        self.node = oscillator_node
        self.ui_manager = ui_manager
        self.padding = 10
        self.element_height = 30
        self.label_width = 100

        current_y = self.padding
        self.freq_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(self.padding, current_y, self.label_width, self.element_height),
            text="Frequency:",
            manager=self.ui_manager,
            container=self
        )
        self.freq_entry = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect(self.padding + self.label_width + 5, current_y, 100, self.element_height),
            manager=self.ui_manager,
            container=self
        )
        self.freq_entry.set_text(str(f"{self.node.frequency:.2f}"))
        current_y += self.element_height + 5

        self.amp_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(self.padding, current_y, self.label_width, self.element_height),
            text="Amplitude:",
            manager=self.ui_manager,
            container=self
        )
        self.amp_entry = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect(self.padding + self.label_width + 5, current_y, 100, self.element_height),
            manager=self.ui_manager,
            container=self
        )
        self.amp_entry.set_text(str(f"{self.node.amplitude:.2f}"))
        current_y += self.element_height + 5

        self.offset_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(self.padding, current_y, self.label_width, self.element_height),
            text="Offset:",
            manager=self.ui_manager,
            container=self
        )
        self.offset_entry = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect(self.padding + self.label_width + 5, current_y, 100, self.element_height),
            manager=self.ui_manager,
            container=self
        )
        self.offset_entry.set_text(str(f"{self.node.offset:.2f}"))
        current_y += self.element_height + 10

        self.close_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(self.padding, current_y, 120, self.element_height),
            text="Close",
            manager=self.ui_manager,
            container=self
        )
        self.set_dimensions((250, current_y + self.element_height + 10))

    def process_event(self, event: pygame.event.Event) -> bool:
        consumed = super().process_event(event)
        if event.type == pygame_gui.UI_TEXT_ENTRY_FINISHED:
            if event.ui_element == self.freq_entry:
                try:
                    self.node.frequency = max(0.0, float(event.text))
                except ValueError:
                    pass
            elif event.ui_element == self.amp_entry:
                try:
                    self.node.amplitude = float(event.text)
                except ValueError:
                    pass
            elif event.ui_element == self.offset_entry:
                try:
                    self.node.offset = float(event.text)
                except ValueError:
                    pass
        elif event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.close_button:
                self.kill()
                return True
        return consumed