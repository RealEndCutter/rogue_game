import textwrap

import curses

from domain import constants
from presentation.formatting import weapon_damage

PANEL_WIDTH = 25

RED = 2
WHITE = 3
YELLOW = 4
BLUE = 10
KEY_COLORS = {"red": RED, "yellow": YELLOW, "blue": BLUE}
KEY_GLYPH = "-"
HEALTH_BAR_WIDTH = 10

def health_bar(health, max_health):
    filled = round(health / max_health * HEALTH_BAR_WIDTH) if max_health > 0 else 0
    filled = max(0, min(HEALTH_BAR_WIDTH, filled))
    return "[" + "█" * filled + " " * (HEALTH_BAR_WIDTH - filled) + "]"


def draw_side_panel(text, pair, snapshot, x, y, extra_lines=(), bottom=None):
    player = snapshot["player"]

    def line(row, value, attr=None):
        text(row, x, value, pair(WHITE) if attr is None else attr)

    title = "ИГРОК"
    text(y, x + (PANEL_WIDTH - len(title)) // 2, title, curses.A_BOLD)

    bar = health_bar(player["health"], player["max_health"])
    text(y + 2, x, bar, pair(RED))
    text(y + 2, x + len(bar) + 1, f"{player['health']}/{player['max_health']}", pair(WHITE))

    line(y + 3, f"Этаж: {snapshot['level_index']} из {constants.LEVELS_COUNT}")

    weapon = player.get("weapon")
    if weapon:
        damage = weapon_damage(weapon.get("dice", ""), weapon["strength"])
        line(y + 4, f"Оружие: {weapon['name']} {damage}".rstrip())
    else:
        line(y + 4, "Оружие: кулаки")

    line(y + 5, f"Сила: {player['strength']}")
    line(y + 6, f"Ловкость: {player['agility']}")
    line(y + 7, f"Сокровища: {snapshot['treasures']}")

    keys = snapshot.get("keys", [])
    label = "Ключи: "
    line(y + 8, label + ("" if keys else "нет"))
    for index, color in enumerate(keys):
        text(y + 8, x + len(label) + index * 2, KEY_GLYPH, pair(KEY_COLORS.get(color, WHITE)) | curses.A_BOLD)

    row = y + 9
    for extra in extra_lines:
        line(row, extra)
        row += 1

    row += 1
    title = "СОБЫТИЯ"
    text(row, x + (PANEL_WIDTH - len(title)) // 2, title, curses.A_BOLD)
    row += 2
    for message in (snapshot.get("player_message"), snapshot.get("enemy_message")):
        if not message:
            continue
        for part in textwrap.wrap(message, PANEL_WIDTH):
            if bottom is not None and row >= bottom:
                return
            line(row, part)
            row += 1
        row += 1
