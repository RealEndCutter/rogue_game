import math
from dataclasses import dataclass

NORTH = (0, -1)
EAST = (1, 0)
SOUTH = (0, 1)
WEST = (-1, 0)

CARDINALS = [NORTH, EAST, SOUTH, WEST]
COMPASS_NAMES = [
    "Север", "Северо-восток", "Восток", "Юго-восток",
    "Юг", "Юго-запад", "Запад", "Северо-запад",
]

TURN_STEP = 15

CAMERA_PLANE = 0.66
MAX_DISTANCE = 20.0

WALL_CHAR = "#"
ROCK_CHAR = " "


def turn(angle, degrees):
    return (angle + degrees) % 360


def step_direction(angle):
    return CARDINALS[round(angle / 90) % 4]


def compass_index(angle):
    return round(angle / 45) % 8


def compass_name(angle):
    return COMPASS_NAMES[compass_index(angle)]


@dataclass
class WallHit:
    distance: float
    side: int
    cell: tuple
    wall_x: float
    along: float
    kind: str
    color: str | None


def blocking_kind(tiles, locked, x, y):
    if y < 0 or y >= len(tiles) or x < 0 or x >= len(tiles[y]):
        return "rock"
    if (x, y) in locked:
        return "locked"
    char = tiles[y][x]
    if char == WALL_CHAR:
        return "wall"
    if char == ROCK_CHAR:
        return "rock"
    return None


def camera(angle):
    radians = math.radians(angle)
    dir_x, dir_y = math.sin(radians), -math.cos(radians)
    plane_x, plane_y = -dir_y * CAMERA_PLANE, dir_x * CAMERA_PLANE
    return dir_x, dir_y, plane_x, plane_y


def cast_ray(tiles, locked, pos, ray):
    pos_x, pos_y = pos
    ray_x, ray_y = ray
    map_x, map_y = int(pos_x), int(pos_y)

    delta_x = abs(1 / ray_x) if ray_x != 0 else math.inf
    delta_y = abs(1 / ray_y) if ray_y != 0 else math.inf

    if ray_x < 0:
        step_x, side_x = -1, (pos_x - map_x) * delta_x
    else:
        step_x, side_x = 1, (map_x + 1 - pos_x) * delta_x
    if ray_y < 0:
        step_y, side_y = -1, (pos_y - map_y) * delta_y
    else:
        step_y, side_y = 1, (map_y + 1 - pos_y) * delta_y

    while True:
        if side_x < side_y:
            side_x += delta_x
            map_x += step_x
            side = 0
        else:
            side_y += delta_y
            map_y += step_y
            side = 1

        distance = (side_x - delta_x) if side == 0 else (side_y - delta_y)
        kind = blocking_kind(tiles, locked, map_x, map_y)
        if kind is not None or distance > MAX_DISTANCE:
            break

    if side == 0:
        along = pos_y + distance * ray_y
    else:
        along = pos_x + distance * ray_x
    wall_x = along - math.floor(along)

    return WallHit(
        distance=max(distance, 0.05),
        side=side,
        cell=(map_x, map_y),
        wall_x=wall_x,
        along=along,
        kind=kind or "rock",
        color=locked.get((map_x, map_y)),
    )


def cast_all(tiles, locked, player, angle, width):
    pos = (player[0] + 0.5, player[1] + 0.5)
    dir_x, dir_y, plane_x, plane_y = camera(angle)
    hits = []
    for column in range(width):
        camera_x = 2 * column / width - 1
        ray = (dir_x + plane_x * camera_x, dir_y + plane_y * camera_x)
        hits.append(cast_ray(tiles, locked, pos, ray))
    return hits


def project(player, angle, target, width):
    dir_x, dir_y, plane_x, plane_y = camera(angle)
    rel_x = target[0] - player[0]
    rel_y = target[1] - player[1]

    inv_det = 1 / (plane_x * dir_y - dir_x * plane_y)
    transform_x = inv_det * (dir_y * rel_x - dir_x * rel_y)
    depth = inv_det * (-plane_y * rel_x + plane_x * rel_y)
    if depth <= 0.2:
        return None

    screen_x = int((width / 2) * (1 + transform_x / depth))
    return screen_x, depth
