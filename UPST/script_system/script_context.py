from typing import Any, Dict, Optional
from UPST.config import config
from UPST.gui.properties_window import PropertiesWindow
from UPST.gui.texture_window import TextureWindow


class ScriptContextProvider:
    def __init__(self, ui_manager: Any, context_menu: Any):
        self.ui_manager = ui_manager
        self.context_menu = context_menu
        self.clicked_object = None

    def set_clicked_object(self, obj: Any):
        self.clicked_object = obj

    def get_context(self) -> Dict[str, Any]:
        return {
            'ui_manager': self.ui_manager,
            'context_menu': self.context_menu,
            'clicked_object': self.clicked_object,
            'config': config,
            'PropertiesWindow': PropertiesWindow,
            'TextureWindow': TextureWindow,
            'physics_manager': getattr(self.ui_manager, 'physics_manager', None),
            'space': getattr(getattr(self.ui_manager, 'physics_manager', None), 'space', None)
        }