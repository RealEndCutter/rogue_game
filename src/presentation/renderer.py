import curses

from presentation import hud

HINT = "WASD ход  h/j/k/e рюкзак  q меню"

from domain.models.enemy import EnemyType
from domain.models.item import ItemType


_ENEMY_COLOR = {
    EnemyType.ZOMBIE: 1,
    EnemyType.VAMPIRE: 2,
    EnemyType.GHOST: 3,
    EnemyType.OGRE: 4,
    EnemyType.SNAKE_MAGE: 3,
}

_KEY_COLOR = {
    "red": 2,
    "yellow": 4,
    "blue": 10,
}
_KEY_GLYPH = "-"
_LOCKED_DOOR_GLYPH = "■"   # запертая дверь; открытая остаётся обычной "+"

_ITEM_COLOR = {
    ItemType.FOOD: 1,
    ItemType.ELIXIR: 5,
    ItemType.SCROLL: 6,
    ItemType.WEAPON: 3,
    ItemType.TREASURE: 4,
}


class Renderer:
    def __init__(self, screen):
        self._screen = screen
        self._colors = False
        self._setup_colors()

    def render(self, snapshot):
        if not snapshot:
            return
        self.clear()
        visible = self._cell_set(snapshot.get("visible"))
        explored = self._cell_set(snapshot.get("explored"))
        self.render_level(snapshot, visible, explored)
        if visible:
            self.render_items(snapshot, visible)
            self.render_enemies(snapshot, visible)
            self.render_player(snapshot, visible)
        self.render_player_panel(snapshot)
        self.render_status(snapshot)
        self.refresh()

    def render_level(self, snapshot, visible, explored):
        locked = {
            (door["x"], door["y"]): door["color"]
            for door in snapshot.get("locked_doors", [])
        }
        for y, row in enumerate(snapshot["tiles"]):
            for x, char in enumerate(row):
                if (x, y) not in explored:
                    continue
                if (x, y) in locked:
                    pair = _KEY_COLOR.get(locked[(x, y)], 3)
                    self._putc(y, x, _LOCKED_DOOR_GLYPH, self._pair(pair) | curses.A_BOLD)
                    continue
                if (x, y) not in visible:
                    if char in ("#", "+"):
                        self._putc(y, x, char, self._pair(7))
                    elif char == "░":
                        self._putc(y, x, char, self._pair(8))
                    continue
                attr = 0
                if char == "#":
                    attr = self._pair(7)
                elif char == "░":
                    attr = self._pair(8)
                elif char == ">":
                    attr = self._pair(4)
                elif char == ".":
                    attr = self._pair(9)   

                self._putc(y, x, char, attr)

    def render_player(self, snapshot, visible):
        player = snapshot["player"]
        pos = (player["x"], player["y"])
        if pos in visible:
            self._putc(player["y"], player["x"], "@", self._pair(3) | curses.A_BOLD)

    def render_enemies(self, snapshot, visible):
        for enemy in snapshot["enemies"]:
            pos = (enemy["x"], enemy["y"])
            ghost_hidden = (enemy["kind"] == EnemyType.GHOST and not enemy["ghost_visible"])
            if pos in visible and not ghost_hidden:
                glyph = enemy["symbol"]

                if enemy["kind"] == EnemyType.MIMIC and enemy["disguised"]:
                    pair = _ITEM_COLOR.get(enemy["disguise_type"], 3)
                else:
                    pair = _ENEMY_COLOR.get(enemy["kind"], 3)

                self._putc(enemy["y"], enemy["x"], glyph, self._pair(pair))

    def render_items(self, snapshot, visible):
        for item in snapshot["items"]:
            pos = (item["x"], item["y"])

            if pos in visible:
                glyph = item["symbol"]

                if item.get("color"):
                    pair = _KEY_COLOR.get(item["color"], 3)
                else:
                    pair = _ITEM_COLOR.get(item["kind"], 3)

                self._putc(item["y"],item["x"],glyph,self._pair(pair))

    def render_status(self, snapshot):
        self._text(len(snapshot["tiles"]), 0, HINT)

    def render_player_panel(self, snapshot):
        height, _ = self._screen.getmaxyx()
        x = len(snapshot["tiles"][0]) + 2
        hud.draw_side_panel(self._text, self._pair, snapshot, x, 1, bottom=height - 1)

    def clear(self):
        self._screen.erase()

    def refresh(self):
        self._screen.refresh()

    @staticmethod
    def _cell_set(entries):
        if not entries:
            return set()
        return {tuple(cell) for cell in entries}

    def _setup_colors(self):
        if not curses.has_colors():
            return
        curses.start_color()
        bg = curses.COLOR_BLACK
        try:
            curses.use_default_colors()
            bg = -1
        except curses.error:
            pass
        for i, fg in enumerate(
            (
                curses.COLOR_GREEN,
                curses.COLOR_RED,
                curses.COLOR_WHITE,
                curses.COLOR_YELLOW,
                curses.COLOR_MAGENTA,
                curses.COLOR_CYAN,
            ),
            start=1,
        ):
            curses.init_pair(i, fg, bg)
        if curses.can_change_color():
            curses.init_color(10, 608, 478, 251)
            curses.init_pair(7, 10, bg)
        else:
            curses.init_pair(7, curses.COLOR_YELLOW, bg)
        if curses.can_change_color():
            curses.init_color(11, 557, 608, 251)
            curses.init_pair(9, 11, bg)
        else:
            curses.init_pair(8, curses.COLOR_WHITE, bg)
        curses.init_pair(8, curses.COLOR_WHITE, bg)    
        curses.init_pair(10, curses.COLOR_BLUE, bg)
        self._colors = True

    def _pair(self, num):
        if not self._colors:
            return 0
        return curses.color_pair(num)

    def _putc(self, y, x, char, attr=0):
        self._text(y, x, char, attr)

    def _text(self, y, x, text, attr=0):
        if not text:
            return
        height, width = self._screen.getmaxyx()
        if y < 0 or x < 0 or y >= height:
            return
        chunk = text[: max(0, width - x - 1)]
        if not chunk:
            return
        try:
            self._screen.addstr(y, x, chunk, attr)
        except curses.error:
            pass
