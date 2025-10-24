import pygame
import pygame_gui
from pygame_gui.elements import UIPanel, UILabel, UITextEntryLine, UIButton, UIDropDownMenu, UIWindow
from UPST.config import config

class NetworkMenu:
    def __init__(self, ui_manager, network_manager, title="Network"):
        self.ui_manager = ui_manager
        self.network_manager = network_manager
        self.panel = UIWindow(
            pygame.Rect(config.app.screen_width-500, config.app.screen_height-500, 330, 190),
            manager=ui_manager,
            window_display_title=title,
        )
        UILabel(pygame.Rect(10, 5, 200, 20), title, manager=ui_manager, container=self.panel)
        UILabel(pygame.Rect(10, 30, 60, 20), "Host", manager=ui_manager, container=self.panel)
        self.entry_host = UITextEntryLine(pygame.Rect(70, 30, 150, 22), manager=ui_manager, container=self.panel)
        self.entry_host.set_text("127.0.0.1")
        UILabel(pygame.Rect(230, 30, 30, 20), "Port", manager=ui_manager, container=self.panel)
        self.entry_port = UITextEntryLine(pygame.Rect(265, 30, 55, 22), manager=ui_manager, container=self.panel)
        self.entry_port.set_text("7777")
        self.btn_host = UIButton(pygame.Rect(10, 60, 120, 26), "Start Host", manager=ui_manager, container=self.panel)
        self.btn_conn = UIButton(pygame.Rect(140, 60, 90, 26), "Connect", manager=ui_manager, container=self.panel)
        self.btn_stop = UIButton(pygame.Rect(240, 60, 80, 26), "Stop", manager=ui_manager, container=self.panel)
        self.entry_chat = UITextEntryLine(pygame.Rect(10, 95, 240, 22), manager=ui_manager, container=self.panel)
        self.btn_chat = UIButton(pygame.Rect(260, 95, 60, 22), "Chat", manager=ui_manager, container=self.panel)
        UILabel(pygame.Rect(10, 125, 80, 20), "Mode", manager=ui_manager, container=self.panel)
        self.drop_mode = UIDropDownMenu(["host", "client"], "host", pygame.Rect(90, 125, 100, 24), manager=ui_manager, container=self.panel)
        self.chk_token = UIButton(pygame.Rect(200, 125, 100, 24), "Auth", manager=ui_manager, container=self.panel, object_id="#auth_toggle")
        self.chk_token.is_checked = False
        self.entry_token = UITextEntryLine(pygame.Rect(10, 155, 310, 22), manager=ui_manager, container=self.panel)

    def process_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.btn_host:
                try:
                    port = int(self.entry_port.get_text() or "7777")
                    if getattr(self.chk_token, 'is_checked', False):
                        self.network_manager.token = self.entry_token.get_text() or None
                    self.network_manager.start_host(port)
                except Exception as e:
                    self.network_manager.log(str(e))
            elif event.ui_element == self.btn_conn:
                try:
                    host = self.entry_host.get_text() or "127.0.0.1"
                    port = int(self.entry_port.get_text() or "7777")
                    if getattr(self.chk_token, 'is_checked', False):
                        self.network_manager.token = self.entry_token.get_text() or None
                    self.network_manager.connect(host, port)
                except Exception as e:
                    self.network_manager.log(str(e))
            elif event.ui_element == self.btn_stop:
                if self.network_manager.role == "host":
                    self.network_manager.stop_host()
                elif self.network_manager.role == "client":
                    self.network_manager.disconnect()
            elif event.ui_element == self.btn_chat:
                txt = self.entry_chat.get_text()
                if txt:
                    self.network_manager.send_chat(txt)
                    self.entry_chat.set_text("")