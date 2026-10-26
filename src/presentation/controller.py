import curses

from domain.models.game_session import GameSession
from presentation.commands import move, unequip_weapon, use_item
from presentation.input_handler import InputHandler
from presentation.menu import MenuView
from presentation.renderer import Renderer


class ControllerState:
    MENU = "menu"
    GAME = "game"
    INVENTORY_FOOD = "inventory_food"
    INVENTORY_ELIXIR = "inventory_elixir"
    INVENTORY_SCROLL = "inventory_scroll"
    INVENTORY_WEAPON = "inventory_weapon"
    STATISTICS = "statistics"
    GAME_OVER = "game_over"


_MOVE = {
    "w": (0, -1),
    "s": (0, 1),
    "a": (-1, 0),
    "d": (1, 0),
}

_INVENTORY_OPEN = {
    "h": (ControllerState.INVENTORY_WEAPON, "Оружие", "weapons", True),
    "j": (ControllerState.INVENTORY_FOOD, "Еда", "food", False),
    "k": (ControllerState.INVENTORY_ELIXIR, "Эликсиры", "elixirs", False),
    "e": (ControllerState.INVENTORY_SCROLL, "Свитки", "scrolls", False),
}

_BACKPACK_KEYS = {
    ControllerState.INVENTORY_FOOD: "food",
    ControllerState.INVENTORY_ELIXIR: "elixirs",
    ControllerState.INVENTORY_SCROLL: "scrolls",
    ControllerState.INVENTORY_WEAPON: "weapons",
}


class Controller:
    def __init__(self, session_factory, save_repository):
        self._session_factory = session_factory
        self._save_repository = save_repository
        self._running = True
        self._state = ControllerState.MENU
        self._screen = None
        self._menu = None
        self._renderer = None
        self._session = None
        self._snapshot = None
        self._inv_title = "Рюкзак"
        self._inv_weapon_slot = False
        self._inv_category = "food"

    def run(self):
        curses.wrapper(self._main_loop)

    def _main_loop(self, screen):
        curses.curs_set(0)
        screen.keypad(True)
        self._screen = screen
        self._menu = MenuView(screen)
        self._renderer = Renderer(screen)
        keyboard = InputHandler(screen)

        while self._running:
            self._draw()
            key = keyboard.read_key()
            self.handle_key(key)

    def _draw(self):
        if self._state == ControllerState.MENU:
            self._menu.render_main_menu()
        elif self._state == ControllerState.STATISTICS:
            if self._session and not self._session.is_game_over():
                stats = self._session.get_run_stats()
                title = "Текущая попытка"
            else:
                stats = GameSession.get_last_run(self._save_repository)
                title = "Последняя попытка"
            self._menu.render_statistics(stats, title=title)
            self._menu.render_leaderboard(GameSession.get_leaderboard(self._save_repository))
        elif self._state == ControllerState.GAME:
            self._renderer.render(self._snapshot)
        elif self._state == ControllerState.GAME_OVER:
            stats = self._session.get_run_stats() if self._session else {}
            victory = self._session.is_game_completed() if self._session else False
            board = GameSession.get_leaderboard(self._save_repository)
            place = board.index(stats) + 1 if stats in board else None
            self._menu.render_game_over(stats, victory=victory, place=place, total=len(board))
        elif self._state in _BACKPACK_KEYS:
            items = self._backpack_items()
            self._menu.render_inventory(
                items,
                title=self._inv_title,
                weapon_slot=self._inv_weapon_slot,
            )

    def _sync_snapshot(self):
        if self._session:
            self._snapshot = self._session.snapshot()

    def handle_key(self, key):
        if self._state == ControllerState.MENU:
            self.handle_menu_key(key)
        elif self._state == ControllerState.STATISTICS:
            if key in ("q", "\x1b", 27):
                self.change_state(ControllerState.MENU)
        elif self._state == ControllerState.GAME_OVER:
            if key in ("q", "\x1b", 27, " "):
                self._session = None
                self.change_state(ControllerState.MENU)
        elif self._state == ControllerState.GAME:
            self.handle_game_key(key)
        elif self._state in _BACKPACK_KEYS:
            self.handle_inventory_key(key)

    def handle_menu_key(self, key):
        if key in ("q", "\x1b", 27, "4"):
            self._running = False
            return
        if key == "1":
            self._menu.notice = ""
            self._session = self._session_factory()
            self._session.start_new_game()
            self._sync_snapshot()
            self.change_state(ControllerState.GAME)
        elif key == "2":
            session = self._session_factory()
            if session.continue_game():
                self._menu.notice = ""
                self._session = session
                self._sync_snapshot()
                self.change_state(ControllerState.GAME)
            else:
                self._menu.notice = "Нет сохранённой игры"
        elif key == "3":
            self.change_state(ControllerState.STATISTICS)

    def handle_game_key(self, key):
        if key in ("q", "\x1b", 27):
            self.change_state(ControllerState.MENU)
            return
        if key in _INVENTORY_OPEN:
            state, title, category, weapon_slot = _INVENTORY_OPEN[key]
            self._inv_title = title
            self._inv_category = category
            self._inv_weapon_slot = weapon_slot
            self.change_state(state)
            return
        if key not in _MOVE or not self._session:
            return
        dx, dy = _MOVE[key]
        self._session.handle(move(dx, dy))
        self._after_session_step()

    def handle_inventory_key(self, key):
        if key in ("q", "\x1b", 27):
            self.change_state(ControllerState.GAME)
            return
        if not isinstance(key, str) or not key.isdigit() or not self._session:
            return
        slot = int(key)
        if self._inv_weapon_slot and slot == 0:
            self._session.handle(unequip_weapon())
        else:
            self._session.handle(use_item(self._inv_category, slot))
        self._after_session_step()
        if self._state != ControllerState.GAME_OVER:
            self.change_state(ControllerState.GAME)

    def _after_session_step(self):
        self._sync_snapshot()
        if self._session.is_game_over():
            self.change_state(ControllerState.GAME_OVER)

    def _backpack_items(self):
        if not self._snapshot:
            return []
        bag = self._snapshot.get("backpack", {})
        field = _BACKPACK_KEYS.get(self._state)
        return list(bag.get(field, []))

    def change_state(self, state):
        self._state = state
