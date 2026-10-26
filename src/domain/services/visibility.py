WALL_CHARS = {"#", " "}

def bresenham_line(start, end):
    x0, y0 = start
    x1, y1 = end
    points = []
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    x, y = x0, y0
    while True:
        points.append((x, y))
        if x == x1 and y == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x += sx
        if e2 < dx:
            err += dx
            y += sy
    return points


def _blocks_sight(tiles, x, y):
    if y < 0 or y >= len(tiles):
        return True
    row = tiles[y]
    if x < 0 or x >= len(row):
        return True
    return row[x] in WALL_CHARS


def cast_ray(tiles, start, end):
    line = bresenham_line(start, end)
    for x, y in line[1:-1]:
        if _blocks_sight(tiles, x, y):
            return False
    return True


def get_visible_cells(player, level, tiles, view_range=12):
    px, py = player.x, player.y
    height = len(tiles)
    if height == 0:
        return set()
    width = len(tiles[0])
    visible = set()
    for y in range(height):
        for x in range(width):
            if tiles[y][x] == " ":
                continue
            if abs(x - px) + abs(y - py) > view_range:
                continue
            if cast_ray(tiles, (px, py), (x, y)):
                visible.add((x, y))
    visible = _add_player_room_visibility(level, px, py, visible)
    return visible


def _add_player_room_visibility(level, player_x, player_y, visible):
    for room in level.rooms:
        inside = room.x <= player_x <= room.end_x and room.y <= player_y <= room.end_y
        if inside:
            for y in range(room.y, room.end_y + 1):
                for x in range(room.x, room.end_x + 1):
                    visible.add((x, y))
            break
    return visible


def update_explored_area(explored, visible_cells):
    explored |= visible_cells
    return explored
