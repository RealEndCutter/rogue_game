class InputHandler:
    def __init__(self, screen):
        self._screen = screen

    def read_key(self):
        raw = self._screen.get_wch()
        if isinstance(raw, str):
            return raw.lower()
        return raw
