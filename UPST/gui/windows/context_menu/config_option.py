class ConfigOption:
    def __init__(self, name, value=None, options=None, handler=None, children=None, is_checkbox=False, get_state=None, set_state=None, icon=None):
        self.name = name
        self.value = value
        self.options = options
        self.handler = handler
        self.children = children or []
        self.is_checkbox = is_checkbox
        self.get_state = get_state
        self.set_state = set_state
        self.icon = icon