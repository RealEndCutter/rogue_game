import curses
import json
import math
from pathlib import Path

from domain.models.enemy import EnemyType
from domain.models.item import ItemType
from presentation import hud
from presentation3d import raycaster
from presentation3d.raycaster import compass_index

SPRITES_FILE = Path(__file__).resolve().parents[1] / "data" / "sprites3d.json"
FULL_BLOCK = "█"
UPPER_HALF = "▀"
LOWER_HALF = "▄"
HALF_BLOCK_PIXELS = {
    " ": (None, None),
    FULL_BLOCK: (FULL_BLOCK, FULL_BLOCK),
    UPPER_HALF: (FULL_BLOCK, None),
    LOWER_HALF: (None, FULL_BLOCK),
}
MIN_SPRITE_HEIGHT = 2

MIN_WIDTH = 90
MIN_HEIGHT = 30
HUD_LINES = 2
MINIMAP_WIDTH = hud.PANEL_WIDTH
MINIMAP_HEIGHT = 11

SHADES = ["█", "▓", "▒", "░"]
SHADE_DISTANCES = [2.0, 4.5, 8.0, 13.0]

BRICK_ROW_LEVELS = (4, 2, 1)
BRICKS_PER_CELL = 2
ROWS_PER_BRICK = 3
MIN_BRICK_COLUMNS = 3
MIN_TEXTURE_HEIGHT = 6

FLOOR_SHADES = [(2.0, "~"), (4.0, ":"), (8.0, "."), (13.0, "·")]

LOCKED_DOOR_GLYPH = "■"
PLAYER_ARROWS = ["↑", "↗", "→", "↘", "↓", "↙", "←", "↖"]

GREEN, RED, WHITE, YELLOW, MAGENTA, CYAN, WALL, ROCK, FLOOR, BLUE = range(1, 11)

KEY_COLOR = {"red": RED, "yellow": YELLOW, "blue": BLUE}
ENEMY_COLOR = {
    EnemyType.ZOMBIE: GREEN,
    EnemyType.VAMPIRE: RED,
    EnemyType.GHOST: WHITE,
    EnemyType.OGRE: YELLOW,
    EnemyType.SNAKE_MAGE: WHITE,
    EnemyType.MIMIC: WHITE,
}
ITEM_COLOR = {
    ItemType.FOOD: GREEN,
    ItemType.ELIXIR: MAGENTA,
    ItemType.SCROLL: CYAN,
    ItemType.WEAPON: WHITE,
    ItemType.TREASURE: YELLOW,
}

ENEMY_SCALE = 0.75
ITEM_SCALE = 0.35


class Renderer3D:
    def __init__(self, screen):
        self._screen = screen
        self._colors = False
        self._backdrop = set()
        self._sprites = self._load_sprites()
        self._setup_colors()

    @staticmethod
    def _load_sprites():
        with open(SPRITES_FILE, encoding="utf-8") as file:
            sprites = json.load(file)
        for sprite in sprites.values():
            sprite["pixels"] = Renderer3D._to_pixels(sprite["art"])
        return sprites

    @staticmethod
    def _to_pixels(art):
        pixels = []
        for line in art:
            top, bottom = [], []
            for char in line:
                upper, lower = HALF_BLOCK_PIXELS.get(char, (char, char))
                top.append(upper)
                bottom.append(lower)
            pixels.append(top)
            pixels.append(bottom)
        return pixels

    @staticmethod
    def _is_hole(pixels, y, x):
        row = pixels[y]
        return 0 < x < len(row) - 1 and row[x - 1] is not None and row[x + 1] is not None

    @staticmethod
    def _cell_glyph(upper, lower):
        if upper and lower:
            return upper if upper == lower else FULL_BLOCK
        if upper:
            return UPPER_HALF if upper == FULL_BLOCK else upper
        if lower:
            return LOWER_HALF if lower == FULL_BLOCK else lower
        return None

    def render(self, snapshot, angle):
        if not snapshot:
            return
        self._screen.erase()
        self._backdrop = set()
        height, width = self._screen.getmaxyx()
        if width < MIN_WIDTH or height < MIN_HEIGHT:
            self._text(0, 0, f"3D-режиму нужен терминал не меньше {MIN_WIDTH}x{MIN_HEIGHT}")
            self._screen.refresh()
            return

        panel_x = width - hud.PANEL_WIDTH - 1
        view_width = panel_x - 1
        view_height = height - HUD_LINES
        player = (snapshot["player"]["x"], snapshot["player"]["y"])
        locked = {(d["x"], d["y"]): d["color"] for d in snapshot.get("locked_doors", [])}

        hits = raycaster.cast_all(snapshot["tiles"], locked, player, angle, view_width)
        self._render_view(hits, view_width, view_height)
        self._render_sprites(snapshot, player, angle, hits, view_width, view_height)
        self._render_minimap(snapshot, player, angle, panel_x)
        hud.draw_side_panel(
            self._text, self._pair, snapshot, panel_x, MINIMAP_HEIGHT + 1,
            bottom=view_height,
        )
        self._text(view_height, 0, "─" * (width - 1), self._pair(WHITE))
        self._text(
            view_height + 1, 0,
            f"W/S шаг  A/D поворот на {raycaster.TURN_STEP}°  h/j/k/e рюкзак  q меню",
        )
        self._screen.refresh()


    def _render_view(self, hits, view_width, view_height):
        horizon = view_height / 2
        previous = None
        for column, hit in enumerate(hits):
            wall_height = view_height / hit.distance
            wall_top = horizon - wall_height / 2
            brick_rows = next(
                (rows for rows in BRICK_ROW_LEVELS if wall_height >= rows * ROWS_PER_BRICK), 1
            )

            first_row = max(0, math.floor(wall_top))
            last_row = min(view_height, math.ceil(wall_top + wall_height))
            floor_start = last_row
            for row in range(first_row, last_row):
                v = (row + 0.5 - wall_top) / wall_height
                if v < 0:
                    continue
                if v >= 1:
                    floor_start = row
                    break
                brick_row = math.floor(v * brick_rows)
                v_above = (row - 0.5 - wall_top) / wall_height
                row_start = v_above >= 0 and math.floor(v_above * brick_rows) != brick_row
                glyph, attr = self._wall_glyph(hit, previous, brick_row, row_start, wall_height)
                if glyph != " ":
                    self._putc(row, column, glyph, attr)
                    self._backdrop.add((row, column))

            for row in range(max(floor_start, math.ceil(horizon)), view_height):
                distance = horizon / max(row + 0.5 - horizon, 0.5)
                glyph = self._floor_glyph(distance)
                if glyph:
                    self._putc(row, column, glyph, self._pair(FLOOR))
            previous = hit

    @staticmethod
    def _same_plane(hit, previous):
        if previous is None or previous.side != hit.side or previous.kind != hit.kind:
            return False
        axis = 0 if hit.side == 0 else 1
        return previous.cell[axis] == hit.cell[axis]

    def _wall_glyph(self, hit, previous, brick_row, row_start, line_height):
        level = next((i for i, d in enumerate(SHADE_DISTANCES) if hit.distance < d), len(SHADES) - 1)
        same_plane = previous is None or self._same_plane(hit, previous)
        if previous is None:
            previous = hit
        textured = line_height >= MIN_TEXTURE_HEIGHT

        if hit.kind == "locked":
            frame = textured and not same_plane
            glyph = SHADES[min(level + 1, len(SHADES) - 1)] if frame else LOCKED_DOOR_GLYPH
            return glyph, self._pair(KEY_COLOR.get(hit.color, WHITE)) | curses.A_BOLD

        step = abs(hit.along - previous.along)
        cell_columns = 1 / step if step > 0 else math.inf

        if hit.kind == "wall":
            shift = 0.5 if brick_row % 2 else 0.0
            brick = math.floor(hit.along * BRICKS_PER_CELL + shift)
            new_brick = brick != math.floor(previous.along * BRICKS_PER_CELL + shift)
            wide_enough = cell_columns / BRICKS_PER_CELL >= MIN_BRICK_COLUMNS
            mortar = textured and (row_start or not same_plane or (new_brick and wide_enough))
            color = WALL
        else:
            new_cell = math.floor(hit.along) != math.floor(previous.along)
            wide_enough = cell_columns >= MIN_BRICK_COLUMNS
            mortar = textured and (not same_plane or (new_cell and wide_enough))
            color = ROCK

        if mortar:
            level = min(level + 1, len(SHADES) - 1)
        attr = self._pair(color)
        if hit.side == 1:
            attr |= curses.A_DIM
        return SHADES[level], attr

    @staticmethod
    def _floor_glyph(distance):
        for limit, glyph in FLOOR_SHADES:
            if distance < limit:
                return glyph
        return None


    def _render_sprites(self, snapshot, player, angle, hits, view_width, view_height):
        visible = {tuple(cell) for cell in snapshot.get("visible", [])}
        sprites = []
        for enemy in snapshot["enemies"]:
            if enemy["kind"] == EnemyType.GHOST and not enemy["ghost_visible"]:
                continue
            if enemy["kind"] == EnemyType.MIMIC and enemy["disguised"]:
                color = ITEM_COLOR.get(enemy["disguise_type"], WHITE)
                sprites.append((enemy["x"], enemy["y"], enemy["symbol"], color, enemy["disguise_type"], ITEM_SCALE))
            else:
                color = ENEMY_COLOR.get(enemy["kind"], WHITE)
                sprites.append((enemy["x"], enemy["y"], enemy["symbol"], color, enemy["kind"], ENEMY_SCALE))
        for item in snapshot["items"]:
            if item.get("color"):
                color = KEY_COLOR.get(item["color"], WHITE)
            else:
                color = ITEM_COLOR.get(item["kind"], WHITE)
            sprites.append((item["x"], item["y"], item["symbol"], color, item["kind"], ITEM_SCALE))
        exit_cell = self._find_exit(snapshot["tiles"])
        if exit_cell:
            sprites.append((*exit_cell, ">", YELLOW, "exit", ITEM_SCALE))

        projected = []
        for x, y, glyph, color, kind, scale in sprites:
            if (x, y) not in visible or (x, y) == player:
                continue
            result = raycaster.project(player, angle, (x, y), view_width)
            if result is not None:
                screen_x, depth = result
                projected.append((depth, screen_x, glyph, color, kind, scale))

        horizon = view_height / 2
        for depth, center, glyph, color, kind, scale in sorted(projected, key=lambda p: -p[0]):
            sprite = self._sprites.get(kind)
            if sprite:
                scale = sprite["scale"]
            wall_height = view_height / depth
            floor_row = min(view_height - 1, int(horizon + wall_height / 2))
            height = max(1, int(wall_height * scale))
            if sprite and height >= MIN_SPRITE_HEIGHT:
                self._draw_art(sprite["pixels"], center, floor_row, height, depth, hits, view_width, view_height, color)
            else:
                attr = self._pair(color) | curses.A_BOLD
                self._draw_block(glyph, center, floor_row, height, depth, hits, view_width, view_height, attr)

    def _draw_art(self, pixels, center, floor_row, height, depth, hits, view_width, view_height, color):
        pixel_height, pixel_width = len(pixels), len(pixels[0])
        width = max(1, round(height * 2 * pixel_width / pixel_height))
        left = center - width // 2
        top = floor_row - height + 1
        for dx in range(width):
            column = left + dx
            if not 0 <= column < view_width or depth >= hits[column].distance:
                continue
            pixel_x = dx * pixel_width // width
            for dy in range(height):
                row = top + dy
                if not 0 <= row < view_height:
                    continue
                upper_y = (2 * dy) * pixel_height // (2 * height)
                lower_y = (2 * dy + 1) * pixel_height // (2 * height)
                upper, lower = pixels[upper_y][pixel_x], pixels[lower_y][pixel_x]
                glyph = self._cell_glyph(upper, lower)
                if not glyph:
                    continue
                if glyph in (UPPER_HALF, LOWER_HALF) and (row, column) in self._backdrop:
                    empty_y = lower_y if glyph == UPPER_HALF else upper_y
                    if not self._is_hole(pixels, empty_y, pixel_x):
                        glyph = FULL_BLOCK
                self._putc(row, column, glyph, self._pair(color) | curses.A_BOLD)

    def _draw_block(self, glyph, center, floor_row, height, depth, hits, view_width, view_height, attr):
        left = center - height // 2
        for column in range(left, left + height):
            if not 0 <= column < view_width or depth >= hits[column].distance:
                continue
            for row in range(floor_row - height + 1, floor_row + 1):
                if 0 <= row < view_height:
                    self._putc(row, column, glyph, attr)

    @staticmethod
    def _find_exit(tiles):
        for y, row in enumerate(tiles):
            x = row.find(">")
            if x != -1:
                return (x, y)
        return None


    def _render_minimap(self, snapshot, player, angle, left):
        inner_width = MINIMAP_WIDTH - 2
        inner_height = MINIMAP_HEIGHT - 2
        border = self._pair(WHITE)

        self._text(0, left, "┌" + "─" * inner_width + "┐", border)
        for row in range(1, MINIMAP_HEIGHT - 1):
            self._text(row, left, "│" + " " * inner_width + "│", border)
        self._text(MINIMAP_HEIGHT - 1, left, "└" + "─" * inner_width + "┘", border)

        tiles = snapshot["tiles"]
        visible = {tuple(cell) for cell in snapshot.get("visible", [])}
        explored = {tuple(cell) for cell in snapshot.get("explored", [])}
        locked = {(d["x"], d["y"]): d["color"] for d in snapshot.get("locked_doors", [])}
        enemies = {(e["x"], e["y"]): e for e in snapshot["enemies"]
                   if not (e["kind"] == EnemyType.GHOST and not e["ghost_visible"])}
        items = {(i["x"], i["y"]): i for i in snapshot["items"]}

        start_x = player[0] - inner_width // 2
        start_y = player[1] - inner_height // 2
        for dy in range(inner_height):
            for dx in range(inner_width):
                cell = (start_x + dx, start_y + dy)
                glyph, attr = self._minimap_cell(cell, tiles, visible, explored, locked, enemies, items)
                if glyph != " ":
                    self._putc(1 + dy, left + 1 + dx, glyph, attr)

        center_row = 1 + inner_height // 2
        center_col = left + 1 + inner_width // 2
        arrow = PLAYER_ARROWS[compass_index(angle)]
        self._putc(center_row, center_col, arrow, self._pair(WHITE) | curses.A_BOLD)

    def _minimap_cell(self, cell, tiles, visible, explored, locked, enemies, items):
        x, y = cell
        if not (0 <= y < len(tiles) and 0 <= x < len(tiles[y])) or cell not in explored:
            return " ", 0
        if cell in locked:
            return LOCKED_DOOR_GLYPH, self._pair(KEY_COLOR.get(locked[cell], WHITE)) | curses.A_BOLD
        char = tiles[y][x]
        if cell not in visible:
            if char in ("#", "+"):
                return char, self._pair(WALL)
            if char == "░":
                return char, self._pair(ROCK)
            return " ", 0
        if cell in enemies:
            enemy = enemies[cell]
            if enemy["kind"] == EnemyType.MIMIC and enemy["disguised"]:
                return enemy["symbol"], self._pair(ITEM_COLOR.get(enemy["disguise_type"], WHITE))
            return enemy["symbol"], self._pair(ENEMY_COLOR.get(enemy["kind"], WHITE))
        if cell in items:
            item = items[cell]
            color = KEY_COLOR.get(item["color"]) if item.get("color") else ITEM_COLOR.get(item["kind"])
            return item["symbol"], self._pair(color or WHITE)
        colors = {"#": WALL, "░": ROCK, ".": FLOOR, ">": YELLOW}
        return char, self._pair(colors.get(char, WHITE))


    def _setup_colors(self):
        if not curses.has_colors():
            return
        curses.start_color()
        background = curses.COLOR_BLACK
        try:
            curses.use_default_colors()
            background = -1
        except curses.error:
            pass
        palette = {
            GREEN: curses.COLOR_GREEN,
            RED: curses.COLOR_RED,
            WHITE: curses.COLOR_WHITE,
            YELLOW: curses.COLOR_YELLOW,
            MAGENTA: curses.COLOR_MAGENTA,
            CYAN: curses.COLOR_CYAN,
            WALL: curses.COLOR_YELLOW,
            ROCK: curses.COLOR_WHITE,
            FLOOR: curses.COLOR_CYAN,
            BLUE: curses.COLOR_BLUE,
        }
        for pair, color in palette.items():
            curses.init_pair(pair, color, background)
        self._colors = True

    def _pair(self, number):
        return curses.color_pair(number) if self._colors else 0

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
