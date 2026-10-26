import curses

from presentation.commands import move
from presentation.controller import Controller, ControllerState
from presentation.input_handler import InputHandler
from presentation.menu import MenuView
from presentation3d.raycaster import TURN_STEP, step_direction, turn
from presentation3d.renderer3d import Renderer3D


class Controller3D(Controller):
    def __init__(self, session_factory, save_repository):
        super().__init__(session_factory, save_repository)
        self._angle = 0              

    def _main_loop(self, screen):
        curses.curs_set(0)
        screen.keypad(True)
        self._screen = screen
        self._menu = MenuView(screen)
        self._renderer = Renderer3D(screen)
        keyboard = InputHandler(screen)

        while self._running:
            self._draw()
            key = keyboard.read_key()
            self.handle_key(key)

    def _draw(self):
        if self._state == ControllerState.GAME:
            self._renderer.render(self._snapshot, self._angle)
        else:
            super()._draw()

    def handle_menu_key(self, key):
        if key in ("1", "2"):
            self._angle = 0            
        super().handle_menu_key(key)

    def handle_game_key(self, key):
        if key == "a":
            self._angle = turn(self._angle, -TURN_STEP)
        elif key == "d":
            self._angle = turn(self._angle, TURN_STEP)
        elif key in ("w", "s") and self._session:
            dx, dy = step_direction(self._angle)
            if key == "s":
                dx, dy = -dx, -dy
            self._session.handle(move(dx, dy))
            self._after_session_step()
        else:
            super().handle_game_key(key)
