import curses

from presentation.formatting import weapon_damage
from domain import constants

_STAT_LABELS = (
    ("treasures", "Сокровища"),
    ("depth", "Достигнутый этаж"),
    ("enemies_defeated", "Побеждено противников"),
    ("food_eaten", "Съедено еды"),
    ("elixirs_drunk", "Выпито эликсиров"),
    ("scrolls_read", "Прочитано свитков"),
    ("hits_landed", "Нанесено ударов"),
    ("hits_missed", "Пропущено ударов"),
    ("tiles_walked", "Пройдено клеток"),
)

_LOGO = (
    "████   ███  █   █  ███  █████   ",
    "█░░░█ █ ░░█ █░  █░█ ░░░ █░░░░░  ",
    "████░░█░ ░█░█░░ █░█░ ██░████░░░ ",
    "█░░█░ █░░ █░█░░ █░█░░ █░█░░░░   ",
    "█░░░█░ ███ ░░███ ░░███ ░█████░  ",
    " ░░  ░  ░░░ ░ ░░░ ░ ░░░ ░░░░░░  ",
    "  ░   ░  ░░░   ░░░   ░░░  ░░░░░",
)

_FONT = {
    "A": (" ████ ", "██  ██", "██████", "██  ██", "██  ██"),
    "C": (" █████", "██    ", "██    ", "██    ", " █████"),
    "E": ("██████", "██    ", "█████ ", "██    ", "██████"),
    "G": (" █████", "██    ", "██ ███", "██  ██", " █████"),
    "I": ("██████", "  ██  ", "  ██  ", "  ██  ", "██████"),
    "M": ("█    █", "██  ██", "██████", "█ ██ █", "█    █"),
    "O": (" ████ ", "██  ██", "██  ██", "██  ██", " ████ "),
    "R": ("█████ ", "██  ██", "█████ ", "██  ██", "██  ██"),
    "T": ("██████", "  ██  ", "  ██  ", "  ██  ", "  ██  "),
    "V": ("██  ██", "██  ██", "██  ██", " ████ ", "  ██  "),
    "Y": ("██  ██", "██  ██", " ████ ", "  ██  ", "  ██  "),
    " ": ("  ", "  ", "  ", "  ", "  "),
}
_VICTORY_LEFT = ("treasures", "depth", "enemies_defeated", "tiles_walked", "hits_landed")
_VICTORY_RIGHT = ("food_eaten", "elixirs_drunk", "scrolls_read", "hits_missed")
_GOLD = 4
_RED = 2


def _banner(word):
    letters = [" ".join(_FONT[char][row] for char in word) for row in range(5)]
    width, height = len(letters[0]) + 1, len(letters) + 1
    canvas = [[" "] * width for _ in range(height)]
    for y, line in enumerate(letters):
        for x, char in enumerate(line):
            if char != " ":
                canvas[y][x] = char
    for y, line in enumerate(letters):
        for x, char in enumerate(line):
            if char != " " and canvas[y + 1][x + 1] == " ":
                canvas[y + 1][x + 1] = "░"
    return ["".join(row) for row in canvas]


_MENU_ITEMS = (
    "1. Новая игра",
    "2. Продолжить",
    "3. Статистика",
    "4. Выход",
)

# Колонки таблицы лидеров: ключ статистики, заголовок
_LEADERBOARD_COLUMNS = (
    ("treasures", "Сокр"),
    ("depth", "Этаж"),
    ("enemies_defeated", "Убито"),
    ("food_eaten", "Еда"),
    ("elixirs_drunk", "Элик"),
    ("scrolls_read", "Свит"),
    ("hits_landed", "Удары"),
    ("hits_missed", "Получ"),
    ("tiles_walked", "Клетки"),
)
_LEADERBOARD_HEADERS = [title for _, title in _LEADERBOARD_COLUMNS]
_LEADERBOARD_WIDTHS = [max(len(title), 4) for title in _LEADERBOARD_HEADERS]


class MenuView:
    def __init__(self, screen):
        self._screen = screen
        self.notice = ""

    def render_main_menu(self):
        self._screen.erase()

        width = constants.SCREEN_WIDTH

        logo_top = 1
        logo_width = max(len(line) for line in _LOGO)
        logo_x = (width-logo_width) // 2
        for i, line in enumerate(_LOGO):
            self._draw(logo_top + i, logo_x, line, curses.A_BOLD)

        menu_top = logo_top + len(_LOGO) + 1
        inner_width = max(len(item) for item in _MENU_ITEMS)
        if self.notice:
            inner_width = max(inner_width, len(self.notice))

        box_width = inner_width + 4
        box_height = len(_MENU_ITEMS) + 2

        box_x = (width - box_width) // 2
        box_y = menu_top

        self._draw(box_y, box_x,"|" + "▓" * (box_width-2) + "|")
        self._draw(box_y + box_height - 1, box_x, "|" + "▓" * (box_width-2) + "|")

        for row in range(box_y + 1, box_y + box_height - 1):
            self._draw(row, box_x, "|")
            self._draw(row, box_x + box_width - 1, "|")

        text_x = box_x + (box_width - inner_width) // 2
        row = box_y + 1
        for item in _MENU_ITEMS:
            self._draw(row, text_x, item)
            row += 1
        if self.notice:
            self._draw(row, text_x, self.notice)

        self._screen.refresh()

    def render_statistics(self, statistics, title="Статистика попытки"):
        self._screen.erase()
        self._draw(2, 2, title, curses.A_BOLD)
        stats = statistics or {}
        row = 4
        for key, label in _STAT_LABELS:
            self._draw(row, 2, f"{label}: {stats.get(key, 0)}")
            row += 1
        self._screen.refresh()

    def render_inventory(self, items, title="Рюкзак", weapon_slot=False):
        self._screen.erase()
        width = constants.SCREEN_WIDTH
        content = []

        if weapon_slot:
            content.append("0. Убрать оружие из рук")

        if items:
            for index, item in enumerate(items, start=1):
                line = f"{index}. {item['name']}"
                effects = []

                if item.get("health"):
                    effects.append(f"+{item['health']} HP")
                if item.get("max_health"):
                    effects.append(f"+{item['max_health']} max HP")
                if item.get("dice"):
                    effects.append("урон " + weapon_damage(item["dice"], item.get("strength", 0)))
                elif item.get("strength"):
                    effects.append(f"+{item['strength']} силы")
                if item.get("agility"):
                    effects.append(f"+{item['agility']} ловкости")
                if item.get("duration"):
                    effects.append(f"{item['duration']} ходов")
                if effects:
                    line += " — " + ", ".join(effects)

                content.append(line)

        else:
            content.append("Пусто")

        hint = "Цифра - выбрать    q - назад к игре"
        inner_width = max(len(title), len(hint), max(len(line) for line in content))
        box_width = inner_width + 6
        box_height = len(content) + 6

        box_x = (width - box_width) // 2
        box_y = 2
        self._draw(box_y, box_x, "|" + "▓" * (box_width - 2) + "|")

        self._draw(box_y + box_height - 1, box_x, "|" + "▓" * (box_width - 2) + "|")

        for row in range(box_y + 1, box_y + box_height - 1):
            self._draw(row, box_x, "|")
            self._draw(row, box_x + box_width - 1, "|")

        title_x = box_x + (box_width - len(title)) // 2
        self._draw(box_y + 1, title_x, title.upper(), curses.A_BOLD)
        row = box_y + 3

        for line in content:
            self._draw(row, box_x + 3,line)
            row += 1

        hint_x = box_x + (box_width - len(hint)) // 2
        self._draw(box_y + box_height - 2, hint_x,hint)
        self._screen.refresh()

    def render_leaderboard(self, records):
        start = 14
        self._draw(start, 2, "Таблица лидеров (по сокровищам)", curses.A_BOLD)
        self._draw(start + 1, 2, self._leaderboard_row("#", _LEADERBOARD_HEADERS))
        # Сколько строк влезает: от заголовка до подсказки внизу экрана
        height, _ = self._screen.getmaxyx()
        max_rows = max(1, height - start - 4)
        if not records:
            self._draw(start + 2, 2, "пока пусто")
        else:
            for index, record in enumerate(records[:max_rows], start=1):
                values = [record.get(key, 0) for key, _ in _LEADERBOARD_COLUMNS]
                self._draw(start + 1 + index, 2, self._leaderboard_row(index, values))
        self._draw(height - 2, 2, "q - в меню")

    @staticmethod
    def _leaderboard_row(index, values):
        cells = [f"{value:>{width}}" for value, width in zip(values, _LEADERBOARD_WIDTHS)]
        return f"{index:>2} " + " ".join(cells)

    def render_game_over(self, statistics, victory=False, place=None, total=None):
        stats = statistics or {}
        if victory:
            subtitle = f"Вы прошли все {constants.LEVELS_COUNT} уровень подземелья"
            self._render_final("VICTORY", _GOLD, subtitle, stats, place, total)
        else:
            subtitle = f"Вы погибли на {stats.get('depth', 1)} уровне подземелья"
            self._render_final("GAME OVER", _RED, subtitle, stats, place, total)

    def _render_final(self, title, color, subtitle, stats, place, total):
        self._screen.erase()
        _, width = self._screen.getmaxyx()
        gold = curses.color_pair(_GOLD) if curses.has_colors() else 0
        accent = curses.color_pair(color) if curses.has_colors() else 0
        labels = dict(_STAT_LABELS)

        def centered(row, text, attr=0):
            self._draw(row, max(0, (width - len(text)) // 2), text, attr)

        row = 1
        for line in _banner(title):
            centered(row, line, accent | curses.A_BOLD)
            row += 1
        centered(row + 1, subtitle, curses.A_BOLD)
        row += 3

        cell_width = 30
        two_columns = width >= cell_width * 2 + 12
        if two_columns:
            columns = [_VICTORY_LEFT, _VICTORY_RIGHT]
        else:
            columns = [_VICTORY_LEFT + _VICTORY_RIGHT]
        inner_width = cell_width * len(columns) + 4 * (len(columns) - 1)
        box_width = inner_width + 6
        box_x = max(0, (width - box_width) // 2)
        border = "|" + "▓" * (box_width - 2) + "|"

        def cell(key):
            if key is None:
                return " " * cell_width
            label, value = labels[key], str(stats.get(key, 0))
            return f"{label} {'.' * (cell_width - len(label) - len(value) - 2)} {value}"

        self._draw(row, box_x, border)
        rows = max(len(column) for column in columns)
        for offset in range(rows):
            keys = [column[offset] if offset < len(column) else None for column in columns]
            line = "|  " + "    ".join(cell(key) for key in keys) + "  |"
            self._draw(row + 1 + offset, box_x, line)
            if "treasures" in keys:
                x = box_x + 3 + keys.index("treasures") * (cell_width + 4)
                self._draw(row + 1 + offset, x, cell("treasures"), gold | curses.A_BOLD)
        row += rows + 1
        self._draw(row, box_x, border)
        row += 2

        if place is not None:
            centered(row, f"Место в таблице рекордов: {place} из {total}", gold | curses.A_BOLD if place == 1 else 0)
            row += 2
        centered(row, "пробел или q - в главное меню")
        self._screen.refresh()

    def _draw(self, y, x, text, attr=0):
        height, width = self._screen.getmaxyx()
        if not 0 <= y < height or x >= width:
            return
        text = text[: width - x - 1]
        try:
            self._screen.addstr(y, x, text, attr)
        except curses.error:
            pass
